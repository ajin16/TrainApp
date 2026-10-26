import os
from datetime import datetime, date, timedelta, time
from models import db, Booking, Passenger, ChartLog, Train, RouteStation

# IRCTC 12-Hour Auto-Charting Constant
AUTO_CHART_HOURS_BEFORE = 12

def prepare_reservation_chart(train_id, journey_date, trigger_type='MANUAL'):
    """
    Simulates IRCTC Reservation Chart Preparation:
    - Triggered automatically 12 hours before origin departure (or manually by admin).
    - Checks if chart is already prepared (idempotent).
    - Locks all bookings for this train run (chart_prepared = True).
    - Finalizes seat assignments for RAC passengers.
    - Auto-cancels remaining Waitlisted (WL) passengers with full refund minus nominal clerkage.
    - Records execution in ChartLog.
    """
    train = Train.query.get(train_id)
    if not train:
        return False, "Train not found.", None

    # 1. Idempotency check: if chart is already prepared, return existing record
    existing_log = ChartLog.query.filter_by(train_id=train_id, journey_date=journey_date).first()
    if existing_log:
        return True, f"Reservation chart for Train {train.train_number} on {journey_date.strftime('%d-%b-%Y')} is already prepared.", {
            'chart_log_id': existing_log.id,
            'train_id': train.id,
            'train_number': train.train_number,
            'train_name': train.name,
            'journey_date': journey_date.strftime('%Y-%m-%d'),
            'total_passengers': existing_log.total_passengers,
            'cnf_count': existing_log.cnf_count,
            'rac_count': existing_log.rac_count,
            'wl_count': existing_log.wl_count,
            'auto_cancelled_wl': existing_log.auto_cancelled_wl_count,
            'prepared_at': existing_log.prepared_at,
            'already_prepared': True
        }

    bookings = Booking.query.filter_by(train_id=train_id, journey_date=journey_date).all()

    total_passengers = 0
    cnf_count = 0
    rac_count = 0
    wl_count = 0
    auto_cancelled_wl = 0

    # 2. Process bookings and passenger status
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
                    # Finalize RAC seat assignment: allocate shared side-lower berth
                    p.seat_no = (p.rac_wl_number + 1) // 2 if p.rac_wl_number else 1
                    p.coach_no = 'RAC'
                    p.berth_type = 'Side Lower (Shared)'
            elif p.current_status == 'WL':
                wl_count += 1
                # IRCTC Rule: E-ticket waitlist passengers not confirmed after charting are auto-cancelled
                p.is_cancelled = True
                p.current_status = 'AUTO_CANCELLED_WL'
                # Full refund for auto-cancelled WL minus nominal clerkage (Rs. 60)
                fare_share = booking.total_fare / max(1, len(booking.passengers))
                p.refund_amount = max(0.0, fare_share - 60.0)
                p.cancelled_at = datetime.utcnow()
                auto_cancelled_wl += 1

    # 3. Create ChartLog record
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
        'chart_log_id': chart_log.id,
        'train_id': train.id,
        'train_number': train.train_number,
        'train_name': train.name,
        'journey_date': journey_date.strftime('%Y-%m-%d'),
        'total_passengers': total_passengers,
        'cnf_count': cnf_count,
        'rac_count': rac_count,
        'wl_count': wl_count,
        'auto_cancelled_wl': auto_cancelled_wl,
        'prepared_at': chart_log.prepared_at,
        'already_prepared': False,
        'trigger_type': trigger_type
    }
    return True, f"Reservation chart prepared successfully for Train {train.train_number} ({total_passengers} passengers processed).", report


def get_train_origin_departure_time(train):
    """Get the scheduled departure time string from the origin station (stop 1)."""
    origin_route = next((r for r in train.routes if r.stop_number == 1), None)
    if origin_route and origin_route.departure_time and origin_route.departure_time != '--:--':
        return origin_route.departure_time
    return '06:00'


def check_and_auto_prepare_charts(hours_before=AUTO_CHART_HOURS_BEFORE, now=None):
    """
    Automated Charting Engine:
    Scans upcoming train departures and automatically creates reservation charts
    for any train departing within the next `hours_before` hours (default 12 hours)
    that has not yet been charted.
    
    Returns a dict with execution timestamp, count, and reports of charts created.
    """
    if now is None:
        now = datetime.now()

    charts_created = []
    
    # Check candidates for today, tomorrow, and day after tomorrow
    candidate_dates = [
        now.date(),
        now.date() + timedelta(days=1),
        now.date() + timedelta(days=2)
    ]

    active_trains = Train.query.filter_by(is_active=True).all()

    for train in active_trains:
        for j_date in candidate_dates:
            # 1. Check if train operates on this day of week
            day_name = j_date.strftime('%a')  # Mon, Tue, Wed, etc.
            operates = (
                'Daily' in (train.operating_days or '') or
                day_name in (train.operating_days or '')
            )
            if not operates:
                continue

            # 2. Get origin departure time
            dep_time_str = get_train_origin_departure_time(train)
            try:
                dep_t = datetime.strptime(dep_time_str, '%H:%M').time()
            except ValueError:
                dep_t = time(6, 0)

            scheduled_departure_dt = datetime.combine(j_date, dep_t)

            # 3. Check if departure is within `hours_before` hours and not older than 2 days
            diff_hours = (scheduled_departure_dt - now).total_seconds() / 3600.0

            # Condition: departure is within 12 hours (diff_hours <= hours_before)
            # and departure is not older than 48 hours ago
            if diff_hours <= hours_before and diff_hours >= -48.0:
                # 4. Check if chart has already been prepared
                existing = ChartLog.query.filter_by(train_id=train.id, journey_date=j_date).first()
                if not existing:
                    success, msg, report = prepare_reservation_chart(
                        train.id,
                        j_date,
                        trigger_type=f'AUTO_{hours_before}H'
                    )
                    if success and report:
                        report['scheduled_departure'] = scheduled_departure_dt.strftime('%d-%b-%Y %H:%M')
                        report['hours_before_departure'] = round(diff_hours, 1)
                        charts_created.append(report)

    return {
        'checked_at': now,
        'hours_before': hours_before,
        'count': len(charts_created),
        'charts_created': charts_created
    }


def get_upcoming_train_chart_statuses(hours_before=AUTO_CHART_HOURS_BEFORE, lookahead_days=2, now=None):
    """
    Build a comprehensive live monitoring list of upcoming train runs (today and next N days)
    with their departure times, countdowns, occupancy, and 12-hour auto-charting status.
    """
    if now is None:
        now = datetime.now()

    today = now.date()
    dates_to_check = [today + timedelta(days=i) for i in range(lookahead_days + 1)]

    active_trains = Train.query.filter_by(is_active=True).order_by(Train.train_number).all()
    schedules = []

    for train in active_trains:
        for j_date in dates_to_check:
            day_name = j_date.strftime('%a')
            operates = (
                'Daily' in (train.operating_days or '') or
                day_name in (train.operating_days or '')
            )
            if not operates:
                continue

            dep_time_str = get_train_origin_departure_time(train)
            try:
                dep_t = datetime.strptime(dep_time_str, '%H:%M').time()
            except ValueError:
                dep_t = time(6, 0)

            scheduled_departure_dt = datetime.combine(j_date, dep_t)
            time_until_dep_seconds = (scheduled_departure_dt - now).total_seconds()
            time_until_dep_hours = time_until_dep_seconds / 3600.0

            # Find existing ChartLog
            chart_log = ChartLog.query.filter_by(train_id=train.id, journey_date=j_date).first()

            # Passenger & booking counts for this run
            bookings = Booking.query.filter_by(train_id=train.id, journey_date=j_date).all()
            active_passengers = [p for b in bookings for p in b.passengers if not p.is_cancelled]
            cnf_count = sum(1 for p in active_passengers if p.current_status == 'CNF')
            rac_count = sum(1 for p in active_passengers if p.current_status == 'RAC')
            wl_count = sum(1 for p in active_passengers if p.current_status == 'WL')

            # Status determination
            if chart_log:
                status_code = 'CHARTED'
                status_label = 'Chart Prepared'
                badge_class = 'bg-success'
                can_prepare = False
            elif time_until_dep_hours <= hours_before and time_until_dep_hours >= -12.0:
                status_code = 'DUE_NOW'
                status_label = f'Due for Charting (<{hours_before}h)'
                badge_class = 'bg-warning text-dark'
                can_prepare = True
            elif time_until_dep_hours < -12.0:
                status_code = 'DEPARTED'
                status_label = 'Departed / Past'
                badge_class = 'bg-secondary'
                can_prepare = False
            else:
                status_code = 'SCHEDULED'
                hours_until_auto = max(0, time_until_dep_hours - hours_before)
                status_label = f'Auto-Charts in {int(hours_until_auto)}h {int((hours_until_auto % 1) * 60)}m'
                badge_class = 'bg-info text-dark'
                can_prepare = True

            # Format countdown display
            if time_until_dep_hours > 0:
                h = int(time_until_dep_hours)
                m = int((time_until_dep_hours % 1) * 60)
                countdown_str = f"in {h}h {m}m"
            else:
                countdown_str = "Departed"

            schedules.append({
                'train_id': train.id,
                'train_number': train.train_number,
                'train_name': train.name,
                'source_code': train.source_station.code,
                'dest_code': train.destination_station.code,
                'journey_date': j_date,
                'journey_date_str': j_date.strftime('%Y-%m-%d'),
                'departure_time': dep_time_str,
                'scheduled_departure_dt': scheduled_departure_dt,
                'countdown_str': countdown_str,
                'time_until_dep_hours': time_until_dep_hours,
                'status_code': status_code,
                'status_label': status_label,
                'badge_class': badge_class,
                'can_prepare': can_prepare,
                'chart_log': chart_log,
                'cnf_count': cnf_count,
                'rac_count': rac_count,
                'wl_count': wl_count,
                'total_passengers': len(active_passengers)
            })

    # Sort schedules by scheduled departure time ascending
    schedules.sort(key=lambda s: s['scheduled_departure_dt'])
    return schedules


def get_full_passenger_chart(chart_log_id):
    """
    Generate the official Railway Station Reservation Chart Display:
    - Lists all confirmed passengers grouped by Coach & Seat Number.
    - Lists RAC finalized passengers.
    - Lists Auto-Cancelled & Refunded Waitlisted passengers.
    """
    chart_log = ChartLog.query.get(chart_log_id)
    if not chart_log:
        return None

    train = chart_log.train
    bookings = Booking.query.filter_by(
        train_id=chart_log.train_id,
        journey_date=chart_log.journey_date
    ).all()

    confirmed_list = []
    rac_list = []
    cancelled_wl_list = []
    other_cancelled_list = []

    for b in bookings:
        for p in b.passengers:
            p_dict = {
                'id': p.id,
                'name': p.name,
                'age': p.age,
                'gender': p.gender,
                'pnr': b.pnr,
                'travel_class': b.travel_class,
                'quota': b.quota,
                'from_station': b.from_station.code,
                'to_station': b.to_station.code,
                'coach_no': p.coach_no or '--',
                'seat_no': p.seat_no or '--',
                'berth_type': p.berth_type or 'Berth',
                'status': p.current_status,
                'booking_status': p.booking_status,
                'refund_amount': p.refund_amount
            }

            if p.current_status == 'CNF':
                confirmed_list.append(p_dict)
            elif p.current_status == 'RAC':
                rac_list.append(p_dict)
            elif p.current_status == 'AUTO_CANCELLED_WL':
                cancelled_wl_list.append(p_dict)
            elif p.is_cancelled:
                other_cancelled_list.append(p_dict)

    # Sort confirmed passengers by Coach then Seat
    confirmed_list.sort(key=lambda x: (str(x['coach_no']), int(x['seat_no']) if str(x['seat_no']).isdigit() else 999))

    return {
        'chart_log': chart_log,
        'train': train,
        'journey_date': chart_log.journey_date,
        'prepared_at': chart_log.prepared_at,
        'confirmed_passengers': confirmed_list,
        'rac_passengers': rac_list,
        'cancelled_wl_passengers': cancelled_wl_list,
        'other_cancelled_passengers': other_cancelled_list,
        'total_confirmed': len(confirmed_list),
        'total_rac': len(rac_list),
        'total_auto_refunded': len(cancelled_wl_list)
    }
