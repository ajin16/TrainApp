from datetime import datetime
from models import db, Booking, Passenger, ChartLog, Train

def prepare_reservation_chart(train_id, journey_date):
    """
    Simulates IRCTC Chart Preparation (run ~4 hours before train departure):
    - Lock all bookings for this train run.
    - Finalize seat assignments for RAC passengers.
    - Auto-cancel any remaining Waitlisted (WL) passengers with full refund.
    - Record execution in ChartLog.
    """
    train = Train.query.get(train_id)
    if not train:
        return False, "Train not found.", None

    bookings = Booking.query.filter_by(train_id=train_id, journey_date=journey_date).all()
    if not bookings:
        return False, "No bookings found for this train on the specified date.", None

    total_passengers = 0
    cnf_count = 0
    rac_count = 0
    wl_count = 0
    auto_cancelled_wl = 0

    for booking in bookings:
        booking.chart_prepared = True
        for p in booking.passengers:
            if p.is_cancelled:
                continue

            total_passengers += 1
            if p.current_status == 'CNF':
                cnf_count += 1
            elif p.current_status == 'RAC':
                rac_count += 1
                if not p.seat_no:
                    p.seat_no = (p.rac_wl_number + 1) // 2
                    p.coach_no = 'RAC'
            elif p.current_status == 'WL':
                wl_count += 1
                # IRCTC Rule: E-ticket waitlist passengers not confirmed after charting are auto-cancelled
                p.is_cancelled = True
                p.current_status = 'AUTO_CANCELLED_WL'
                # Full refund for auto-cancelled WL minus nominal clerkage
                fare_share = booking.total_fare / len(booking.passengers)
                p.refund_amount = max(0.0, fare_share - 60.0)
                p.cancelled_at = datetime.utcnow()
                auto_cancelled_wl += 1

    chart_log = ChartLog(
        train_id=train_id,
        journey_date=journey_date,
        prepared_at=datetime.utcnow(),
        total_passengers=total_passengers,
        cnf_count=cnf_count,
        rac_count=rac_count,
        wl_count=wl_count,
        auto_cancelled_wl_count=auto_cancelled_wl
    )
    db.session.add(chart_log)
    db.session.commit()

    report = {
        'train_number': train.train_number,
        'train_name': train.name,
        'journey_date': journey_date.strftime('%Y-%m-%d'),
        'total_passengers': total_passengers,
        'cnf_count': cnf_count,
        'rac_count': rac_count,
        'wl_count': wl_count,
        'auto_cancelled_wl': auto_cancelled_wl
    }
    return True, "Reservation chart prepared successfully!", report
