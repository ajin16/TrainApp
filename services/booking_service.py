import random
import string
from datetime import datetime, date, timedelta, time
from models import db, Train, RouteStation, Station, CoachQuotaConfig, Booking, Passenger

BERTH_TYPES_SLEEPER_3AC = ['Lower', 'Middle', 'Upper', 'Lower', 'Middle', 'Upper', 'Side Lower', 'Side Upper']
BERTH_TYPES_2AC = ['Lower', 'Upper', 'Lower', 'Upper', 'Side Lower', 'Side Upper']
BERTH_TYPES_CHAIR = ['Window', 'Middle', 'Aisle', 'Aisle', 'Window']

COACH_PREFIXES = {
    '1A': 'H',
    '2A': 'A',
    '3A': 'B',
    'SL': 'S',
    'CC': 'C',
    '2S': 'D'
}

# 14-Day Advance Reservation Period (ARP) Constant
MAX_ADVANCE_BOOKING_DAYS = 14
TATKAL_OPEN_TIME = time(10, 0, 0)  # 10:00 AM server time

def validate_advance_reservation_period(journey_date, max_days=MAX_ADVANCE_BOOKING_DAYS):
    """
    Validate that the journey date is within the allowed 14-day booking window.
    Returns (is_valid: bool, error_msg: str | None).
    """
    today = date.today()
    max_date = today + timedelta(days=max_days)

    if journey_date < today:
        return False, f"Journey date ({journey_date.strftime('%d-%b-%Y')}) cannot be in the past."

    if journey_date > max_date:
        return False, (
            f"Advance Reservation Period (ARP) violation: Bookings are restricted up to {max_days} days in advance. "
            f"Allowed booking range: {today.strftime('%d-%b-%Y')} to {max_date.strftime('%d-%b-%Y')}."
        )

    return True, None

def validate_tatkal_eligibility(journey_date, quota, server_now=None):
    """
    Validate Tatkal booking constraints:
    1. Quota is TQ.
    2. Opens daily at exactly 10:00 AM local server time.
    3. Strictly allows ticket booking ONLY for the immediate next day (today + 1 day).
    Returns (is_valid: bool, error_msg: str | None).
    """
    if quota != 'TQ':
        return True, None

    if server_now is None:
        server_now = datetime.now()

    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Date constraint: strictly immediate next day
    if journey_date != tomorrow:
        return False, (
            f"Tatkal quota restriction: Tatkal bookings are strictly permitted ONLY for tomorrow's travel "
            f"({tomorrow.strftime('%d-%b-%Y')}). Selected date: {journey_date.strftime('%d-%b-%Y')} is not eligible for Tatkal."
        )

    # Time constraint: opens at exactly 10:00 AM server time
    if server_now.time() < TATKAL_OPEN_TIME:
        return False, (
            f"Tatkal booking opens daily at exactly 10:00 AM local server time. "
            f"Current server time is {server_now.strftime('%I:%M:%S %p')}. Tatkal booking window is currently CLOSED."
        )

    return True, None

def archive_or_purge_old_transactions(retention_days=5, purge=False):
    """
    5-Day Transaction Retention Policy:
    Archives or permanently purges booking transaction records older than retention_days.
    Returns count of affected records.
    """
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    if purge:
        old_bookings = Booking.query.filter(Booking.booking_time < cutoff).all()
        count = len(old_bookings)
        for b in old_bookings:
            db.session.delete(b)
        db.session.commit()
        return count
    else:
        old_bookings = Booking.query.filter(
            Booking.booking_time < cutoff,
            Booking.is_archived == False
        ).all()
        count = len(old_bookings)
        now = datetime.utcnow()
        for b in old_bookings:
            b.is_archived = True
            b.archived_at = now
        db.session.commit()
        return count

def generate_pnr():
    """Generate a unique 10-digit PNR string."""
    while True:
        first_digit = random.choice('2468')
        remaining = ''.join(random.choices(string.digits, k=9))
        pnr = first_digit + remaining
        if not Booking.query.filter_by(pnr=pnr).first():
            return pnr

def calculate_fare(distance_km, travel_class, quota='GN'):
    """Calculate detailed fare breakdown per passenger."""
    class_multipliers = {
        '1A': 3.5,
        '2A': 2.5,
        '3A': 1.8,
        'SL': 1.0,
        'CC': 1.5,
        '2S': 0.6
    }
    
    multiplier = class_multipliers.get(travel_class, 1.0)
    base_fare = round(distance_km * multiplier, 2)
    if base_fare < 50:
        base_fare = 50.0  # Minimum distance charge
        
    reservation_fee = 40.0 if travel_class in ['1A', '2A', '3A'] else 20.0
    superfast_charge = 45.0 if travel_class in ['1A', '2A', '3A'] else 30.0
    
    subtotal = base_fare + reservation_fee + superfast_charge
    
    tatkal_surcharge = 0.0
    if quota == 'TQ':
        if travel_class in ['1A', '2A']:
            tatkal_surcharge = max(400.0, round(base_fare * 0.30, 2))
        elif travel_class in ['3A', 'CC']:
            tatkal_surcharge = max(300.0, round(base_fare * 0.30, 2))
        elif travel_class == 'SL':
            tatkal_surcharge = max(100.0, round(base_fare * 0.20, 2))
        else:  # 2S
            tatkal_surcharge = max(15.0, round(base_fare * 0.10, 2))
        
    gst = 0.0
    if travel_class in ['1A', '2A', '3A', 'CC']:
        gst = round((subtotal + tatkal_surcharge) * 0.05, 2)
        
    total_per_passenger = round(subtotal + tatkal_surcharge + gst, 2)
    
    return {
        'base_fare': base_fare,
        'reservation_fee': reservation_fee,
        'superfast_charge': superfast_charge,
        'tatkal_surcharge': tatkal_surcharge,
        'gst': gst,
        'total_per_passenger': total_per_passenger
    }

def get_class_availability(train_id, journey_date, travel_class):
    """
    Compute real-time CNF, RAC, WL seat availability for a train, date, and class.
    Returns dict with count breakdown and display status string.
    """
    config = CoachQuotaConfig.query.filter_by(train_id=train_id, travel_class=travel_class).first()
    if not config:
        return {
            'status': 'NAV',
            'display': 'NOT AVAILABLE',
            'cnf_left': 0, 'rac_left': 0, 'wl_left': 0,
            'total_cnf': 0, 'total_rac': 0, 'total_wl': 0
        }
        
    # Count active passengers booked for this train, journey_date, class
    active_passengers = Passenger.query.join(Booking).filter(
        Booking.train_id == train_id,
        Booking.journey_date == journey_date,
        Booking.travel_class == travel_class,
        Passenger.is_cancelled == False
    ).all()
    
    cnf_count = sum(1 for p in active_passengers if p.current_status == 'CNF')
    rac_count = sum(1 for p in active_passengers if p.current_status == 'RAC')
    wl_count = sum(1 for p in active_passengers if p.current_status == 'WL')
    
    cnf_left = max(0, config.total_cnf_seats - cnf_count)
    rac_left = max(0, config.total_rac_seats - rac_count)
    wl_left = max(0, config.total_wl_seats - wl_count)
    
    if cnf_left > 0:
        display = f"AVAILABLE - {cnf_left}"
        status_code = 'AVAILABLE'
    elif rac_left > 0:
        rac_number = rac_count + 1
        display = f"RAC {rac_number}"
        status_code = 'RAC'
    elif wl_left > 0:
        wl_number = wl_count + 1
        display = f"WL {wl_number}"
        status_code = 'WL'
    else:
        display = "REGRET / NOT AVAILABLE"
        status_code = 'NAV'
        
    return {
        'status': status_code,
        'display': display,
        'cnf_left': cnf_left,
        'rac_left': rac_left,
        'wl_left': wl_left,
        'total_cnf': config.total_cnf_seats,
        'total_rac': config.total_rac_seats,
        'total_wl': config.total_wl_seats,
        'cnf_count': cnf_count,
        'rac_count': rac_count,
        'wl_count': wl_count,
        'base_fare_per_km': config.base_fare_per_km
    }

def search_trains(from_station_code, to_station_code, journey_date, quota='GN'):
    """
    Find trains running between source and destination stations on given date.
    Returns list of dicts with train info, route details, and class availability.
    """
    from_st = Station.query.filter_by(code=from_station_code.upper()).first()
    to_st = Station.query.filter_by(code=to_station_code.upper()).first()
    
    if not from_st or not to_st or from_st.id == to_st.id:
        return [], from_st, to_st

    results = []
    # Find all trains having both stations in their route
    trains = Train.query.filter_by(is_active=True).all()
    
    for train in trains:
        src_route = None
        dst_route = None
        
        for r in train.routes:
            if r.station_id == from_st.id:
                src_route = r
            elif r.station_id == to_st.id:
                dst_route = r
                
        # Must pass from_st BEFORE to_st
        if src_route and dst_route and src_route.stop_number < dst_route.stop_number:
            distance = round(dst_route.distance_km - src_route.distance_km, 1)
            
            # Class availability details
            availabilities = {}
            for cfg in train.configs:
                avail = get_class_availability(train.id, journey_date, cfg.travel_class)
                fare_info = calculate_fare(distance, cfg.travel_class, quota=quota)
                availabilities[cfg.travel_class] = {
                    'availability': avail,
                    'fare': fare_info['total_per_passenger']
                }
                
            results.append({
                'train': train,
                'src_route': src_route,
                'dst_route': dst_route,
                'distance_km': distance,
                'classes': availabilities
            })
            
    return results, from_st, to_st

def assign_berth_type(travel_class, seat_no):
    """Determine berth/seat type based on seat number and travel class."""
    if travel_class in ['3A', 'SL']:
        mod = (seat_no - 1) % 8
        return BERTH_TYPES_SLEEPER_3AC[mod]
    elif travel_class == '2A':
        mod = (seat_no - 1) % 6
        return BERTH_TYPES_2AC[mod]
    elif travel_class in ['CC', '2S']:
        mod = (seat_no - 1) % 5
        return BERTH_TYPES_CHAIR[mod]
    elif travel_class == '1A':
        return 'Cabin' if seat_no % 2 == 1 else 'Coupe'
    return 'Lower'

def find_preferred_seat_number(travel_class, current_cnf_count, preference, passenger_age):
    """
    Intelligent Berth Preference Allocator:
    Finds a seat number matching the requested preference (Lower, Middle, Upper, Side Lower, Side Upper, Window),
    or defaults to next sequential seat.
    Senior citizens (age >= 60) automatically get Lower berth priority if available.
    """
    total_capacity = 72
    # Determine target berth type
    target_pref = preference
    if passenger_age >= 60 and preference in ['No Preference', 'Lower']:
        target_pref = 'Lower'
        
    start_seat = current_cnf_count + 1
    
    # Try up to next 16 seat candidates to match requested berth type
    for check_seat in range(start_seat, min(start_seat + 16, total_capacity + 1)):
        b_type = assign_berth_type(travel_class, check_seat)
        if target_pref != 'No Preference' and b_type.lower() == target_pref.lower():
            return check_seat, b_type

    # Fallback to default next seat
    fallback_seat = start_seat
    fallback_berth = assign_berth_type(travel_class, fallback_seat)
    return fallback_seat, fallback_berth

def book_ticket(user_id, train_id, from_station_id, to_station_id, journey_date, travel_class, quota, passengers_data, server_now=None):
    """
    Process ticket booking for multiple passengers.
    Allocates CNF/RAC/WL sequentially, matching berth preferences for CNF seats.
    Strictly validates 14-day Advance Reservation Period and 10:00 AM Tatkal window.
    """
    # 1. Validate Advance Reservation Period (14 Days)
    is_arp_valid, arp_err = validate_advance_reservation_period(journey_date)
    if not is_arp_valid:
        return False, arp_err

    # 2. Validate Tatkal Quota Rules (10:00 AM server time and Tomorrow's date only)
    is_tatkal_valid, tatkal_err = validate_tatkal_eligibility(journey_date, quota, server_now=server_now)
    if not is_tatkal_valid:
        return False, tatkal_err

    train = Train.query.get(train_id)
    from_st = Station.query.get(from_station_id)
    to_st = Station.query.get(to_station_id)
    
    if not train or not from_st or not to_st:
        return False, "Invalid train or station selected."
        
    src_r = RouteStation.query.filter_by(train_id=train_id, station_id=from_station_id).first()
    dst_r = RouteStation.query.filter_by(train_id=train_id, station_id=to_station_id).first()
    if not src_r or not dst_r or src_r.stop_number >= dst_r.stop_number:
        return False, "Invalid station sequence for selected train."

    distance = dst_r.distance_km - src_r.distance_km
    fare_info = calculate_fare(distance, travel_class, quota)
    total_fare = fare_info['total_per_passenger'] * len(passengers_data)
    
    avail = get_class_availability(train_id, journey_date, travel_class)
    
    total_passengers = len(passengers_data)
    available_total_capacity = avail['cnf_left'] + avail['rac_left'] + avail['wl_left']
    if total_passengers > available_total_capacity:
        return False, f"Not enough seats available. Max available: {available_total_capacity}"
        
    pnr = generate_pnr()
    booking = Booking(
        pnr=pnr,
        user_id=user_id,
        train_id=train_id,
        from_station_id=from_station_id,
        to_station_id=to_station_id,
        journey_date=journey_date,
        travel_class=travel_class,
        quota=quota,
        total_fare=total_fare,
        status='BOOKED'
    )
    db.session.add(booking)
    db.session.flush()
    
    coach_prefix = COACH_PREFIXES.get(travel_class, 'B')
    
    for p_idx, p_data in enumerate(passengers_data):
        current_avail = get_class_availability(train_id, journey_date, travel_class)
        
        status = ''
        coach_no = None
        seat_no = None
        berth_type = None
        rac_wl_num = None
        
        p_age = int(p_data.get('age', 30))
        p_pref = p_data.get('berth_preference', 'No Preference')
        
        if current_avail['cnf_left'] > 0:
            status = 'CNF'
            allocated_seat_index = current_avail['cnf_count']
            
            # Find preferred berth type seat
            seat_no, berth_type = find_preferred_seat_number(travel_class, allocated_seat_index, p_pref, p_age)
            coach_num = ((seat_no - 1) // 72) + 1
            coach_no = f"{coach_prefix}{coach_num}"
        elif current_avail['rac_left'] > 0:
            status = 'RAC'
            rac_wl_num = current_avail['rac_count'] + 1
            coach_no = 'RAC'
            seat_no = (rac_wl_num + 1) // 2
            berth_type = 'Side Lower (Shared)'
        else:
            status = 'WL'
            rac_wl_num = current_avail['wl_count'] + 1
            coach_no = 'WL'
            seat_no = None
            berth_type = 'No Berth Allocated'
            
        passenger = Passenger(
            booking_id=booking.id,
            name=p_data['name'],
            age=p_age,
            gender=p_data['gender'],
            berth_preference=p_pref,
            booking_status=f"{status} / {rac_wl_num}" if rac_wl_num else "CNF",
            current_status=status,
            coach_no=coach_no,
            seat_no=seat_no,
            berth_type=berth_type,
            rac_wl_number=rac_wl_num,
            is_cancelled=False
        )
        db.session.add(passenger)
        
    db.session.commit()
    return True, booking
