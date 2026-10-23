from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, date, timedelta, time
from models import db, Station, Train, Booking, Passenger
from services.booking_service import (
    search_trains,
    get_class_availability,
    calculate_fare,
    book_ticket,
    validate_advance_reservation_period,
    validate_tatkal_eligibility,
    archive_or_purge_old_transactions,
    MAX_ADVANCE_BOOKING_DAYS
)
from services.cancellation_service import cancel_passengers, calculate_cancellation_refund
from services.ticket_service import get_ticket_summary

user_bp = Blueprint('user', __name__)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@user_bp.route('/')
def index():
    stations = Station.query.order_by(Station.name).all()
    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    max_date_str = (today + timedelta(days=MAX_ADVANCE_BOOKING_DAYS)).strftime('%Y-%m-%d')
    tomorrow_str = (today + timedelta(days=1)).strftime('%Y-%m-%d')
    is_tatkal_open = datetime.now().time() >= time(10, 0)
    return render_template(
        'user/index.html',
        stations=stations,
        today_str=today_str,
        max_date_str=max_date_str,
        tomorrow_str=tomorrow_str,
        is_tatkal_open=is_tatkal_open,
        arp_days=MAX_ADVANCE_BOOKING_DAYS
    )

@user_bp.route('/search', methods=['GET'])
def search():
    from_code = request.args.get('from_station', '').strip()
    to_code = request.args.get('to_station', '').strip()
    journey_date_str = request.args.get('journey_date', '').strip()
    quota = request.args.get('quota', 'GN').strip()
    
    if not from_code or not to_code or not journey_date_str:
        flash("Please select Source, Destination, and Journey Date.", "warning")
        return redirect(url_for('user.index'))

    try:
        journey_date = datetime.strptime(journey_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Invalid date format.", "danger")
        return redirect(url_for('user.index'))

    # 1. Enforce 14-Day Advance Reservation Period (ARP)
    is_arp_valid, arp_err = validate_advance_reservation_period(journey_date)
    if not is_arp_valid:
        flash(arp_err, "warning")
        return redirect(url_for('user.index'))

    # 2. Check Tatkal Quota Rules if TQ selected
    tatkal_warning = None
    if quota == 'TQ':
        is_tatkal_valid, tatkal_err = validate_tatkal_eligibility(journey_date, quota)
        if not is_tatkal_valid:
            tatkal_warning = tatkal_err
            flash(tatkal_err, "warning")

    results, from_st, to_st = search_trains(from_code, to_code, journey_date, quota=quota)
    stations = Station.query.order_by(Station.name).all()

    today = date.today()
    max_date_str = (today + timedelta(days=MAX_ADVANCE_BOOKING_DAYS)).strftime('%Y-%m-%d')

    return render_template(
        'user/search_results.html',
        results=results,
        from_st=from_st,
        to_st=to_st,
        journey_date=journey_date_str,
        journey_date_obj=journey_date,
        quota=quota,
        stations=stations,
        tatkal_warning=tatkal_warning,
        max_date_str=max_date_str
    )

@user_bp.route('/book/<int:train_id>', methods=['GET', 'POST'])
@login_required
def book_form(train_id):
    from_code = request.args.get('from', '')
    to_code = request.args.get('to', '')
    j_date_str = request.args.get('date', '')
    travel_class = request.args.get('class', 'SL')
    quota = request.args.get('quota', 'GN')

    train = Train.query.get_or_404(train_id)
    from_st = Station.query.filter_by(code=from_code).first_or_404()
    to_st = Station.query.filter_by(code=to_code).first_or_404()

    try:
        journey_date = datetime.strptime(j_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Invalid journey date.", "danger")
        return redirect(url_for('user.index'))

    # Validate 14-day ARP window
    is_arp_valid, arp_err = validate_advance_reservation_period(journey_date)
    if not is_arp_valid:
        flash(arp_err, "danger")
        return redirect(url_for('user.search', from_station=from_code, to_station=to_code, journey_date=date.today().strftime('%Y-%m-%d')))

    avail = get_class_availability(train_id, journey_date, travel_class)
    
    # Calculate distance
    src_r = None
    dst_r = None
    for r in train.routes:
        if r.station_id == from_st.id: src_r = r
        elif r.station_id == to_st.id: dst_r = r
    distance = dst_r.distance_km - src_r.distance_km if (src_r and dst_r) else 100.0

    fare_info = calculate_fare(distance, travel_class, quota=quota)

    if request.method == 'POST':
        selected_quota = request.form.get('quota', quota)
        names = request.form.getlist('p_name[]')
        ages = request.form.getlist('p_age[]')
        genders = request.form.getlist('p_gender[]')
        berths = request.form.getlist('p_berth[]')

        # Strictly validate Tatkal rules if Tatkal quota chosen
        if selected_quota == 'TQ':
            is_tatkal_valid, tatkal_err = validate_tatkal_eligibility(journey_date, selected_quota)
            if not is_tatkal_valid:
                flash(tatkal_err, "danger")
                return render_template(
                    'user/book_ticket.html',
                    train=train, from_st=from_st, to_st=to_st, journey_date=journey_date,
                    travel_class=travel_class, quota=selected_quota, avail=avail, fare_info=fare_info, distance=distance
                )

        passengers_data = []
        for i in range(len(names)):
            if names[i].strip():
                passengers_data.append({
                    'name': names[i].strip(),
                    'age': int(ages[i]) if ages[i].isdigit() else 25,
                    'gender': genders[i],
                    'berth_preference': berths[i] if i < len(berths) else 'No Preference'
                })

        if not passengers_data:
            flash("Please add at least one passenger.", "warning")
            return render_template(
                'user/book_ticket.html',
                train=train, from_st=from_st, to_st=to_st, journey_date=journey_date,
                travel_class=travel_class, quota=selected_quota, avail=avail, fare_info=fare_info, distance=distance
            )

        # Recalculate fare for the final selected quota
        final_fare_info = calculate_fare(distance, travel_class, quota=selected_quota)

        # Store booking data in session and redirect to payment gateway simulation
        session['pending_booking'] = {
            'train_id': train_id,
            'from_station_id': from_st.id,
            'to_station_id': to_st.id,
            'journey_date': j_date_str,
            'travel_class': travel_class,
            'quota': selected_quota,
            'passengers_data': passengers_data,
            'distance': distance,
            'fare_info': final_fare_info,
            'total_fare': final_fare_info['total_per_passenger'] * len(passengers_data)
        }
        return redirect(url_for('user.payment_mock'))

    return render_template(
        'user/book_ticket.html',
        train=train,
        from_st=from_st,
        to_st=to_st,
        journey_date=journey_date,
        travel_class=travel_class,
        quota=quota,
        avail=avail,
        fare_info=fare_info,
        distance=distance
    )

@user_bp.route('/payment', methods=['GET', 'POST'])
@login_required
def payment_mock():
    pending = session.get('pending_booking')
    if not pending:
        flash("No active booking session found.", "warning")
        return redirect(url_for('user.index'))

    train = Train.query.get(pending['train_id'])
    from_st = Station.query.get(pending['from_station_id'])
    to_st = Station.query.get(pending['to_station_id'])

    if request.method == 'POST':
        # Process booking with full validations (ARP and Tatkal)
        j_date = datetime.strptime(pending['journey_date'], '%Y-%m-%d').date()
        success, res = book_ticket(
            user_id=session['user_id'],
            train_id=pending['train_id'],
            from_station_id=pending['from_station_id'],
            to_station_id=pending['to_station_id'],
            journey_date=j_date,
            travel_class=pending['travel_class'],
            quota=pending['quota'],
            passengers_data=pending['passengers_data'],
            server_now=datetime.now()
        )

        session.pop('pending_booking', None)

        if success:
            flash(f"Ticket Booked Successfully! PNR: {res.pnr}", "success")
            return redirect(url_for('user.ticket_detail', booking_id=res.id))
        else:
            flash(f"Booking Failed: {res}", "danger")
            return redirect(url_for('user.index'))

    return render_template('user/payment_mock.html', pending=pending, train=train, from_st=from_st, to_st=to_st)

@user_bp.route('/pnr', methods=['GET', 'POST'])
def pnr_status():
    pnr_query = request.args.get('pnr', '').strip() or request.form.get('pnr', '').strip()
    booking_summary = None
    error_msg = None

    if pnr_query:
        booking = Booking.query.filter_by(pnr=pnr_query).first()
        if booking:
            booking_summary = get_ticket_summary(booking)
        else:
            error_msg = f"No booking found for PNR: '{pnr_query}'."

    return render_template('user/pnr_status.html', pnr_query=pnr_query, summary=booking_summary, error_msg=error_msg)

@user_bp.route('/my-bookings')
@login_required
def my_bookings():
    # 5-Day Transaction Retention Policy:
    # 1. Run automatic background archiving for any records older than 5 days
    archive_or_purge_old_transactions(retention_days=5, purge=False)

    filter_type = request.args.get('filter', 'recent').strip().lower()
    cutoff_5_days = datetime.utcnow() - timedelta(days=5)

    base_query = Booking.query.filter_by(user_id=session['user_id'])
    
    # Calculate counts for tabs
    recent_count = base_query.filter(
        Booking.is_archived == False,
        Booking.booking_time >= cutoff_5_days
    ).count()

    archived_count = base_query.filter(
        (Booking.is_archived == True) | (Booking.booking_time < cutoff_5_days)
    ).count()

    total_count = base_query.count()

    if filter_type == 'archived':
        bookings = base_query.filter(
            (Booking.is_archived == True) | (Booking.booking_time < cutoff_5_days)
        ).order_by(Booking.booking_time.desc()).all()
    elif filter_type == 'all':
        bookings = base_query.order_by(Booking.booking_time.desc()).all()
    else:  # 'recent' default (<= 5 days)
        filter_type = 'recent'
        bookings = base_query.filter(
            Booking.is_archived == False,
            Booking.booking_time >= cutoff_5_days
        ).order_by(Booking.booking_time.desc()).all()

    summaries = [get_ticket_summary(b) for b in bookings]
    return render_template(
        'user/my_bookings.html',
        summaries=summaries,
        filter_type=filter_type,
        recent_count=recent_count,
        archived_count=archived_count,
        total_count=total_count,
        retention_days=5
    )

@user_bp.route('/ticket/<int:booking_id>')
@login_required
def ticket_detail(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != session['user_id'] and session.get('role') != 'admin':
        flash("Unauthorized access to ticket.", "danger")
        return redirect(url_for('user.my_bookings'))

    summary = get_ticket_summary(booking)
    return render_template('user/ticket_detail.html', summary=summary)

@user_bp.route('/cancel/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def cancel_ticket_form(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != session['user_id'] and session.get('role') != 'admin':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('user.my_bookings'))

    if booking.status == 'CANCELLED':
        flash("This booking is already fully cancelled.", "info")
        return redirect(url_for('user.ticket_detail', booking_id=booking_id))

    if booking.chart_prepared:
        flash("Cannot cancel tickets after chart preparation.", "warning")
        return redirect(url_for('user.ticket_detail', booking_id=booking_id))

    fare_per_passenger = booking.total_fare / len(booking.passengers)
    active_passengers = [p for p in booking.passengers if not p.is_cancelled]

    if request.method == 'POST':
        p_ids = request.form.getlist('passenger_ids')
        p_ids = [int(pid) for pid in p_ids if pid.isdigit()]

        if not p_ids:
            flash("Please select at least one passenger to cancel.", "warning")
            return redirect(url_for('user.cancel_ticket_form', booking_id=booking_id))

        success, msg, total_refund = cancel_passengers(booking_id, p_ids)
        if success:
            flash(msg, "success")
        else:
            flash(msg, "danger")

        return redirect(url_for('user.ticket_detail', booking_id=booking_id))

    passenger_refund_previews = []
    for p in active_passengers:
        fee, refund = calculate_cancellation_refund(booking.travel_class, p.current_status, fare_per_passenger)
        passenger_refund_previews.append({
            'passenger': p,
            'fee': fee,
            'refund': refund
        })

    return render_template(
        'user/cancel_ticket.html',
        booking=booking,
        previews=passenger_refund_previews
    )

@user_bp.route('/train-schedule', methods=['GET'])
@user_bp.route('/train-schedule/<string:train_number>', methods=['GET'])
def train_schedule(train_number=None):
    query_num = train_number or request.args.get('train_number', '').strip()
    selected_train = None
    schedule_details = []
    error_msg = None

    all_trains = Train.query.filter_by(is_active=True).order_by(Train.train_number).all()

    if query_num:
        selected_train = Train.query.filter(
            (Train.train_number == query_num) | (Train.name.ilike(f"%{query_num}%"))
        ).first()

        if selected_train:
            for route in selected_train.routes:
                halt_mins = "--"
                if route.arrival_time != '--:--' and route.departure_time != '--:--':
                    try:
                        arr_t = datetime.strptime(route.arrival_time, '%H:%M')
                        dep_t = datetime.strptime(route.departure_time, '%H:%M')
                        diff = int((dep_t - arr_t).total_seconds() / 60)
                        halt_mins = f"{diff} min" if diff > 0 else "1 min"
                    except Exception:
                        halt_mins = "--"
                elif route.stop_number == 1:
                    halt_mins = "Origin"
                elif route.stop_number == len(selected_train.routes):
                    halt_mins = "Destination"

                schedule_details.append({
                    'stop_number': route.stop_number,
                    'station_code': route.station.code,
                    'station_name': route.station.name,
                    'city': route.station.city,
                    'arrival_time': route.arrival_time,
                    'departure_time': route.departure_time,
                    'halt_mins': halt_mins,
                    'distance_km': route.distance_km,
                    'day_number': route.day_number
                })
        else:
            error_msg = f"No train found matching query: '{query_num}'."

    return render_template(
        'user/train_schedule.html',
        all_trains=all_trains,
        selected_train=selected_train,
        schedule_details=schedule_details,
        query_num=query_num,
        error_msg=error_msg
    )

