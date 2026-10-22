from datetime import datetime
from models import db, Booking, Passenger, CoachQuotaConfig, Train
from services.booking_service import COACH_PREFIXES, assign_berth_type

def calculate_cancellation_refund(travel_class, status, original_passenger_fare):
    """
    Calculate cancellation charges and net refund amount according to IRCTC rules.
    - Confirmed AC Class (1A, 2A, 3A, CC): flat ₹240 / ₹200 fee.
    - Confirmed Sleeper (SL) / 2S: flat ₹120 / ₹60 fee.
    - RAC / Waiting List: flat clerkage fee ₹60.
    """
    if status == 'CNF':
        if travel_class == '1A':
            fee = 240.0
        elif travel_class in ['2A', '3A', 'CC']:
            fee = 180.0
        elif travel_class == 'SL':
            fee = 120.0
        else:
            fee = 60.0
    else:  # RAC or WL
        fee = 60.0
        
    refund = max(0.0, original_passenger_fare - fee)
    return round(fee, 2), round(refund, 2)

def promote_rac_and_wl(train_id, journey_date, travel_class):
    """
    Core IRCTC Promotion Engine:
    1. Upgrades RAC 1 -> CNF when a CNF berth becomes vacant, allocating coach & seat.
    2. Upgrades WL 1 -> RAC when an RAC berth becomes vacant.
    3. Re-indexes remaining RAC & WL position numbers.
    """
    config = CoachQuotaConfig.query.filter_by(train_id=train_id, travel_class=travel_class).first()
    if not config:
        return

    # Fetch all non-cancelled passengers for this train run
    all_passengers = Passenger.query.join(Booking).filter(
        Booking.train_id == train_id,
        Booking.journey_date == journey_date,
        Booking.travel_class == travel_class,
        Passenger.is_cancelled == False
    ).all()
    
    cnf_passengers = [p for p in all_passengers if p.current_status == 'CNF']
    rac_passengers = sorted([p for p in all_passengers if p.current_status == 'RAC'], key=lambda x: x.rac_wl_number or 9999)
    wl_passengers = sorted([p for p in all_passengers if p.current_status == 'WL'], key=lambda x: x.rac_wl_number or 9999)
    
    coach_prefix = COACH_PREFIXES.get(travel_class, 'B')
    
    # 1. Check if CNF seats are available to promote RAC passengers
    while len(cnf_passengers) < config.total_cnf_seats and rac_passengers:
        promoted = rac_passengers.pop(0)
        promoted.current_status = 'CNF'
        
        # Determine next available coach and seat
        new_cnf_index = len(cnf_passengers) + 1
        coach_num = ((new_cnf_index - 1) // 72) + 1
        promoted.coach_no = f"{coach_prefix}{coach_num}"
        promoted.seat_no = ((new_cnf_index - 1) % 72) + 1
        promoted.berth_type = assign_berth_type(travel_class, promoted.seat_no)
        promoted.rac_wl_number = None
        
        cnf_passengers.append(promoted)
        
    # 2. Check if RAC slots are available to promote WL passengers
    while len(rac_passengers) < config.total_rac_seats and wl_passengers:
        promoted = wl_passengers.pop(0)
        promoted.current_status = 'RAC'
        promoted.coach_no = 'RAC'
        promoted.berth_type = 'Side Lower (Shared)'
        promoted.seat_no = None  # Seat number assigned at chart time
        rac_passengers.append(promoted)

    # 3. Update RAC position numbers (RAC 1, RAC 2...)
    for idx, p in enumerate(rac_passengers, start=1):
        p.rac_wl_number = idx
        p.seat_no = (idx + 1) // 2

    # 4. Update WL position numbers (WL 1, WL 2...)
    for idx, p in enumerate(wl_passengers, start=1):
        p.rac_wl_number = idx

def cancel_passengers(booking_id, passenger_ids_to_cancel):
    """
    Cancel specified passengers for a booking, calculate refunds,
    and trigger RAC -> CNF & WL -> RAC cascading promotions.
    """
    booking = Booking.query.get(booking_id)
    if not booking:
        return False, "Booking not found", 0.0

    if booking.chart_prepared:
        return False, "Cannot cancel ticket after Reservation Chart has been prepared.", 0.0

    total_refund = 0.0
    passengers = Passenger.query.filter(
        Passenger.booking_id == booking_id,
        Passenger.id.in_(passenger_ids_to_cancel),
        Passenger.is_cancelled == False
    ).all()

    if not passengers:
        return False, "No valid active passengers selected for cancellation.", 0.0

    fare_per_passenger = booking.total_fare / len(booking.passengers)

    for p in passengers:
        fee, refund = calculate_cancellation_refund(booking.travel_class, p.current_status, fare_per_passenger)
        p.is_cancelled = True
        p.current_status = 'CANCELLED'
        p.refund_amount = refund
        p.cancelled_at = datetime.utcnow()
        p.coach_no = None
        p.seat_no = None
        p.rac_wl_number = None
        total_refund += refund

    # Check if all passengers are cancelled
    active_remaining = Passenger.query.filter_by(booking_id=booking_id, is_cancelled=False).count()
    if active_remaining == 0:
        booking.status = 'CANCELLED'
    else:
        booking.status = 'PARTIALLY_CANCELLED'

    db.session.flush()

    # Trigger automatic promotion cascade
    promote_rac_and_wl(booking.train_id, booking.journey_date, booking.travel_class)

    db.session.commit()
    return True, f"Successfully cancelled {len(passengers)} passenger(s). Total Refund: ₹{total_refund:.2f}", total_refund
