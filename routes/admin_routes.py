from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, date, timedelta, time
from models import db, Train, Station, RouteStation, CoachQuotaConfig, Booking, Passenger, ChartLog, User
from services.chart_service import (
    prepare_reservation_chart,
    check_and_auto_prepare_charts,
    get_upcoming_train_chart_statuses,
    get_full_passenger_chart,
    AUTO_CHART_HOURS_BEFORE
)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash("Administrator credentials required to access Control Center.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    # 1. Trigger automated 12-hour chart check on dashboard load
    auto_result = check_and_auto_prepare_charts(hours_before=AUTO_CHART_HOURS_BEFORE)

    # 2. Key system analytics
    total_trains = Train.query.filter_by(is_active=True).count()
    total_stations = Station.query.count()
    total_users = User.query.filter_by(role='user').count()
    total_bookings = Booking.query.count()
    
    all_bookings = Booking.query.all()
    total_revenue = sum(b.total_fare for b in all_bookings if b.status != 'CANCELLED')
    
    total_cnf = Passenger.query.filter_by(current_status='CNF', is_cancelled=False).count()
    total_rac = Passenger.query.filter_by(current_status='RAC', is_cancelled=False).count()
    total_wl = Passenger.query.filter_by(current_status='WL', is_cancelled=False).count()

    today_start = datetime.combine(date.today(), time.min)
    charts_prepared_today = ChartLog.query.filter(ChartLog.prepared_at >= today_start).count()

    # 3. Live 12-Hour Upcoming Train Departures & Charting Status
    upcoming_schedules = get_upcoming_train_chart_statuses(hours_before=AUTO_CHART_HOURS_BEFORE, lookahead_days=2)
    due_for_charting_count = sum(1 for s in upcoming_schedules if s['status_code'] == 'DUE_NOW')

    recent_bookings = Booking.query.order_by(Booking.booking_time.desc()).limit(8).all()
    recent_chart_logs = ChartLog.query.order_by(ChartLog.prepared_at.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        total_trains=total_trains,
        total_stations=total_stations,
        total_users=total_users,
        total_bookings=total_bookings,
        total_revenue=total_revenue,
        total_cnf=total_cnf,
        total_rac=total_rac,
        total_wl=total_wl,
        charts_prepared_today=charts_prepared_today,
        due_for_charting_count=due_for_charting_count,
        auto_chart_hours=AUTO_CHART_HOURS_BEFORE,
        upcoming_schedules=upcoming_schedules[:8],
        recent_bookings=recent_bookings,
        recent_chart_logs=recent_chart_logs,
        auto_result=auto_result
    )

@admin_bp.route('/auto-chart', methods=['GET', 'POST'])
@admin_required
def trigger_auto_chart():
    """Manual trigger to run the 12-Hour Auto-Charting Engine immediately."""
    result = check_and_auto_prepare_charts(hours_before=AUTO_CHART_HOURS_BEFORE)
    count = result['count']

    if count > 0:
        flash(
            f"⚡ 12-Hour Auto-Charting Engine Triggered: Successfully generated {count} reservation "
            f"chart(s) for upcoming departures!",
            "success"
        )
    else:
        flash(
            f"12-Hour Auto-Charting Engine checked: All upcoming trains departing within {AUTO_CHART_HOURS_BEFORE} "
            f"hours already have finalized reservation charts.",
            "info"
        )

    # Return to previous page or dashboard
    ref = request.referrer
    if ref and ('/admin/' in ref):
        return redirect(ref)
    return redirect(url_for('admin.chart_prepare'))

@admin_bp.route('/chart', methods=['GET', 'POST'])
@admin_required
def chart_prepare():
    trains = Train.query.filter_by(is_active=True).order_by(Train.train_number).all()
    report = None

    # Run check for upcoming trains
    check_and_auto_prepare_charts(hours_before=AUTO_CHART_HOURS_BEFORE)

    if request.method == 'POST':
        train_id = request.form.get('train_id')
        j_date_str = request.form.get('journey_date')

        if not train_id or not j_date_str:
            flash("Please select train and journey date.", "warning")
            return redirect(url_for('admin.chart_prepare'))

        try:
            j_date = datetime.strptime(j_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format. Use YYYY-MM-DD.", "danger")
            return redirect(url_for('admin.chart_prepare'))

        success, msg, report = prepare_reservation_chart(int(train_id), j_date, trigger_type='ADMIN_MANUAL')
        if success:
            flash(msg, "success")
        else:
            flash(msg, "warning")

    # Fetch live upcoming schedule monitor and history logs
    upcoming_schedules = get_upcoming_train_chart_statuses(hours_before=AUTO_CHART_HOURS_BEFORE, lookahead_days=2)
    chart_logs = ChartLog.query.order_by(ChartLog.prepared_at.desc()).limit(30).all()

    return render_template(
        'admin/chart_prepare.html',
        trains=trains,
        chart_logs=chart_logs,
        report=report,
        upcoming_schedules=upcoming_schedules,
        auto_chart_hours=AUTO_CHART_HOURS_BEFORE
    )

@admin_bp.route('/chart/view/<int:chart_log_id>')
@admin_required
def chart_view(chart_log_id):
    """View official IRCTC Station Passenger Reservation Chart Slip."""
    chart_data = get_full_passenger_chart(chart_log_id)
    if not chart_data:
        flash("Reservation chart log not found.", "danger")
        return redirect(url_for('admin.chart_prepare'))

    return render_template('admin/chart_view.html', data=chart_data)

@admin_bp.route('/trains', methods=['GET', 'POST'])
@admin_required
def trains():
    stations = Station.query.order_by(Station.name).all()

    if request.method == 'POST':
        train_number = request.form.get('train_number', '').strip()
        name = request.form.get('name', '').strip()
        source_id = request.form.get('source_station_id')
        dest_id = request.form.get('destination_station_id')
        operating_days = request.form.get('operating_days', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun')
        dep_time = request.form.get('departure_time', '06:00')
        arr_time = request.form.get('arrival_time', '14:00')
        distance = float(request.form.get('distance_km', 500.0))

        if not train_number or not name or not source_id or not dest_id:
            flash("Please fill in all required train details.", "warning")
            return redirect(url_for('admin.trains'))

        if Train.query.filter_by(train_number=train_number).first():
            flash(f"Train number '{train_number}' already exists.", "danger")
            return redirect(url_for('admin.trains'))

        train = Train(
            train_number=train_number,
            name=name,
            source_station_id=int(source_id),
            destination_station_id=int(dest_id),
            operating_days=operating_days,
            is_active=True
        )
        db.session.add(train)
        db.session.flush()

        # Add Source Station as Stop 1
        r1 = RouteStation(
            train_id=train.id,
            station_id=int(source_id),
            stop_number=1,
            distance_km=0.0,
            arrival_time='--:--',
            departure_time=dep_time,
            day_number=1
        )
        # Add Destination Station as Stop 2
        r2 = RouteStation(
            train_id=train.id,
            station_id=int(dest_id),
            stop_number=2,
            distance_km=distance,
            arrival_time=arr_time,
            departure_time='--:--',
            day_number=1
        )
        db.session.add_all([r1, r2])

        # Add Coach Quota Configs for 3A and SL
        c1 = CoachQuotaConfig(train_id=train.id, travel_class='3A', total_cnf_seats=30, total_rac_seats=10, total_wl_seats=10, base_fare_per_km=1.8)
        c2 = CoachQuotaConfig(train_id=train.id, travel_class='SL', total_cnf_seats=50, total_rac_seats=15, total_wl_seats=15, base_fare_per_km=1.0)
        db.session.add_all([c1, c2])

        db.session.commit()
        flash(f"Train '{train_number} - {name}' added successfully with initial stops and quotas!", "success")
        return redirect(url_for('admin.train_detail', train_id=train.id))

    search_q = request.args.get('q', '').strip()
    query = Train.query
    if search_q:
        query = query.filter((Train.train_number.like(f"%{search_q}%")) | (Train.name.ilike(f"%{search_q}%")))
    all_trains = query.order_by(Train.train_number).all()

    return render_template('admin/trains.html', trains=all_trains, stations=stations, search_q=search_q)

@admin_bp.route('/train/<int:train_id>', methods=['GET', 'POST'])
@admin_required
def train_detail(train_id):
    train = Train.query.get_or_404(train_id)
    stations = Station.query.order_by(Station.name).all()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_route':
            st_id = request.form.get('station_id')
            arr = request.form.get('arrival_time', '12:00')
            dep = request.form.get('departure_time', '12:05')
            dist = float(request.form.get('distance_km', 100))
            day_no = int(request.form.get('day_number', 1))

            stop_no = len(train.routes) + 1
            route = RouteStation(
                train_id=train.id,
                station_id=int(st_id),
                stop_number=stop_no,
                distance_km=dist,
                arrival_time=arr,
                departure_time=dep,
                day_number=day_no
            )
            db.session.add(route)
            db.session.commit()
            flash("Route station added successfully.", "success")

        elif action == 'save_quota':
            t_class = request.form.get('travel_class')
            cnf = int(request.form.get('total_cnf_seats', 30))
            rac = int(request.form.get('total_rac_seats', 10))
            wl = int(request.form.get('total_wl_seats', 10))
            fare = float(request.form.get('base_fare_per_km', 1.5))

            cfg = CoachQuotaConfig.query.filter_by(train_id=train.id, travel_class=t_class).first()
            if not cfg:
                cfg = CoachQuotaConfig(train_id=train.id, travel_class=t_class)
                db.session.add(cfg)

            cfg.total_cnf_seats = cnf
            cfg.total_rac_seats = rac
            cfg.total_wl_seats = wl
            cfg.base_fare_per_km = fare

            db.session.commit()
            flash(f"Coach quota config for class '{t_class}' updated successfully.", "success")

        return redirect(url_for('admin.train_detail', train_id=train_id))

    return render_template('admin/train_detail.html', train=train, stations=stations)

@admin_bp.route('/train/<int:train_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_train_status(train_id):
    train = Train.query.get_or_404(train_id)
    train.is_active = not train.is_active
    db.session.commit()
    state_str = "activated" if train.is_active else "deactivated"
    flash(f"Train {train.train_number} ({train.name}) has been {state_str}.", "info")
    return redirect(url_for('admin.trains'))

@admin_bp.route('/bookings')
@admin_required
def bookings_list():
    pnr_query = request.args.get('pnr', '').strip()
    status_filter = request.args.get('status', '').strip()
    class_filter = request.args.get('travel_class', '').strip()

    query = Booking.query.order_by(Booking.booking_time.desc())
    if pnr_query:
        query = query.filter(Booking.pnr.like(f"%{pnr_query}%"))
    if status_filter:
        query = query.filter_by(status=status_filter)
    if class_filter:
        query = query.filter_by(travel_class=class_filter)

    bookings = query.all()
    return render_template(
        'admin/bookings_list.html',
        bookings=bookings,
        pnr_query=pnr_query,
        status_filter=status_filter,
        class_filter=class_filter
    )
