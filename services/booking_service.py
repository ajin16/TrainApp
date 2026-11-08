import random
import string
from datetime import datetime, date, timedelta, time, timezone
from models import db, Train, RouteStation, Station, CoachQuotaConfig, Booking, Passenger, utcnow

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

def archive_or_purge_old_transactions(retention_days=5, purge=True):
    """
    5-Day Transaction Retention Policy:
    Permanently purges or archives booking transaction records older than retention_days.
    Returns count of affected records.
    """
    cutoff = utcnow() - timedelta(days=retention_days)
    if purge:
        old_bookings = Booking.query.filter(Booking.booking_time < cutoff).all()
        count = len(old_bookings)
        if count > 0:
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
        if count > 0:
            now = utcnow()
            for b in old_bookings:
                b.is_archived = True
                b.archived_at = now
            db.session.commit()
        return count

def delete_old_booking_history(days=5):
    """
    Requirement 1: Automatically delete the history from database which is older than 5 days.
    Permanently purges expired bookings and cascading passenger records.
    """
    return archive_or_purge_old_transactions(retention_days=days, purge=True)

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

def get_class_availability(train_id, journey_date, travel_class, quota='GN'):
    """
    Compute real-time CNF, RAC, WL seat availability for a train, date, class, and quota.
    Strictly reserves 30% of total CNF seats for Tatkal quota (TQ).
    Optimized with single aggregate query to eliminate N+1 queries.
    """
    config = CoachQuotaConfig.query.filter_by(train_id=train_id, travel_class=travel_class).first()
    if not config:
        return {
            'status': 'NAV',
            'display': 'NOT AVAILABLE',
            'cnf_left': 0, 'rac_left': 0, 'wl_left': 0,
            'total_cnf': 0, 'total_rac': 0, 'total_wl': 0
        }
        
    # 30% seats reserved for Tatkal quota
    tatkal_cnf_seats = max(1, round(config.total_cnf_seats * 0.30))
    general_cnf_seats = max(0, config.total_cnf_seats - tatkal_cnf_seats)
    tatkal_wl_seats = max(1, round(config.total_wl_seats * 0.30))
    
    # Fast single SQL query with GROUP BY instead of loading and looping all ORM objects
    counts = db.session.query(
        Booking.quota, Passenger.current_status, db.func.count(Passenger.id)
    ).join(Booking, Passenger.booking_id == Booking.id).filter(
        Booking.train_id == train_id,
        Booking.journey_date == journey_date,
        Booking.travel_class == travel_class,
        Passenger.is_cancelled == False
    ).group_by(Booking.quota, Passenger.current_status).all()
    
    tatkal_cnf_count = sum(cnt for q, st, cnt in counts if q == 'TQ' and st == 'CNF')
    general_cnf_count = sum(cnt for q, st, cnt in counts if q != 'TQ' and st == 'CNF')
    tatkal_wl_count = sum(cnt for q, st, cnt in counts if q == 'TQ' and st == 'WL')
    general_rac_count = sum(cnt for q, st, cnt in counts if q != 'TQ' and st == 'RAC')
    general_wl_count = sum(cnt for q, st, cnt in counts if q != 'TQ' and st == 'WL')
    
    if quota == 'TQ':
        cnf_left = max(0, tatkal_cnf_seats - tatkal_cnf_count)
        rac_left = 0
        wl_left = max(0, tatkal_wl_seats - tatkal_wl_count)
        
        if cnf_left > 0:
            display = f"TATKAL - {cnf_left}"
            status_code = 'AVAILABLE'
        elif wl_left > 0:
            display = f"TQWL {tatkal_wl_count + 1}"
            status_code = 'WL'
        else:
            display = "REGRET / TATKAL FULL"
            status_code = 'NAV'
            
        return {
            'status': status_code,
            'display': display,
            'cnf_left': cnf_left,
            'rac_left': rac_left,
            'wl_left': wl_left,
            'total_cnf': tatkal_cnf_seats,
            'total_rac': 0,
            'total_wl': tatkal_wl_seats,
            'cnf_count': tatkal_cnf_count,
            'rac_count': 0,
            'wl_count': tatkal_wl_count,
            'base_fare_per_km': config.base_fare_per_km,
            'tatkal_reserved_seats': tatkal_cnf_seats,
            'general_quota_seats': general_cnf_seats
        }
    else:
        cnf_left = max(0, general_cnf_seats - general_cnf_count)
        rac_left = max(0, config.total_rac_seats - general_rac_count)
        wl_left = max(0, config.total_wl_seats - general_wl_count)
        
        if cnf_left > 0:
            display = f"AVAILABLE - {cnf_left}"
            status_code = 'AVAILABLE'
        elif rac_left > 0:
            rac_number = general_rac_count + 1
            display = f"RAC {rac_number}"
            status_code = 'RAC'
        elif wl_left > 0:
            wl_number = general_wl_count + 1
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
            'total_cnf': general_cnf_seats,
            'total_rac': config.total_rac_seats,
            'total_wl': config.total_wl_seats,
            'cnf_count': general_cnf_count,
            'rac_count': general_rac_count,
            'wl_count': general_wl_count,
            'base_fare_per_km': config.base_fare_per_km,
            'tatkal_reserved_seats': tatkal_cnf_seats,
            'general_quota_seats': general_cnf_seats
        }

def resolve_station(query_str):
    """
    Intelligently resolve a Station object from code, full name, city, or formatted 'Name (CODE)' string.
    Supports case-insensitive matching and partial searches.
    """
    if not query_str:
        return None
    query_str = str(query_str).strip()
    if not query_str:
        return None

    import re
    # 1. Match code inside parentheses e.g. "Salem (SA)" or "New Delhi (NDLS)"
    match = re.search(r'\(([A-Za-z0-9]+)\)', query_str)
    if match:
        st = Station.query.filter_by(code=match.group(1).upper()).first()
        if st:
            return st

    # 2. Direct code match (e.g. "NDLS", "MAS", "SA")
    st = Station.query.filter_by(code=query_str.upper()).first()
    if st:
        return st

    # 3. Exact name match (case-insensitive)
    st = Station.query.filter(Station.name.ilike(query_str)).first()
    if st:
        return st

    # 4. Prefix or substring name/city match
    st = Station.query.filter(
        (Station.name.ilike(f"{query_str}%")) |
        (Station.city.ilike(f"{query_str}%")) |
        (Station.name.ilike(f"%{query_str}%"))
    ).first()
    return st

def search_trains(from_station_code, to_station_code, journey_date, quota='GN'):
    """
    Find trains running between source and destination stations on given date.
    Fully supports intermediate-to-intermediate, origin-to-intermediate, and intermediate-to-destination searches.
    Validates train operating days against journey date.
    Calculates segment distance, intermediate halts count, journey duration, and class availability.
    """
    from_st = resolve_station(from_station_code)
    to_st = resolve_station(to_station_code)
    
    if not from_st or not to_st or from_st.id == to_st.id:
        return [], from_st, to_st

    results = []
    # Eager load routes, stations, and configs for high throughput
    trains = Train.query.filter_by(is_active=True).options(
        db.joinedload(Train.routes).joinedload(RouteStation.station),
        db.joinedload(Train.configs),
        db.joinedload(Train.source_station),
        db.joinedload(Train.destination_station)
    ).all()
    
    day_name_short = journey_date.strftime('%a')  # 'Mon', 'Tue', etc.
    day_name_long = journey_date.strftime('%A')   # 'Monday', 'Tuesday', etc.
    
    for train in trains:
        # Validate train operating days for journey date
        op_days = train.operating_days or 'Daily'
        operates = (
            'Daily' in op_days or
            day_name_short in op_days or
            day_name_long in op_days
        )
        if not operates:
            continue

        src_route = None
        dst_route = None
        
        # Sort train routes by stop_number to guarantee exact sequence order
        sorted_routes = sorted(train.routes, key=lambda r: r.stop_number)
        
        for r in sorted_routes:
            if r.station_id == from_st.id:
                src_route = r
            elif r.station_id == to_st.id:
                dst_route = r
                
        # Train must pass from_st BEFORE to_st
        if src_route and dst_route and src_route.stop_number < dst_route.stop_number:
            distance = max(1.0, round(dst_route.distance_km - src_route.distance_km, 1))
            
            # Intermediate halts calculation
            intermediate_halts = max(0, dst_route.stop_number - src_route.stop_number - 1)
            
            # Journey duration calculation between selected stations
            duration_str = "--"
            if src_route.departure_time != '--:--' and dst_route.arrival_time != '--:--':
                try:
                    dep_parts = [int(x) for x in src_route.departure_time.split(':')]
                    arr_parts = [int(x) for x in dst_route.arrival_time.split(':')]
                    dep_mins = (src_route.day_number - 1) * 1440 + dep_parts[0] * 60 + dep_parts[1]
                    arr_mins = (dst_route.day_number - 1) * 1440 + arr_parts[0] * 60 + arr_parts[1]
                    diff_mins = arr_mins - dep_mins
                    if diff_mins < 0:
                        diff_mins += 1440
                    h = diff_mins // 60
                    m = diff_mins % 60
                    duration_str = f"{h}h {m:02d}m"
                except Exception:
                    duration_str = "--"
            
            # Determine if this is an intermediate station search
            is_intermediate_boarding = (src_route.stop_number > 1)
            is_intermediate_deboarding = (dst_route.stop_number < len(sorted_routes))
            is_intermediate = is_intermediate_boarding or is_intermediate_deboarding
            
            # Extract names of intermediate halt stations for route preview
            halt_stations = [
                r.station.name for r in sorted_routes 
                if src_route.stop_number < r.stop_number < dst_route.stop_number
            ]
            
            # Class availability details
            availabilities = {}
            for cfg in train.configs:
                avail = get_class_availability(train.id, journey_date, cfg.travel_class, quota=quota)
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
                'intermediate_halts': intermediate_halts,
                'halt_stations': halt_stations,
                'duration_str': duration_str,
                'is_intermediate': is_intermediate,
                'is_intermediate_boarding': is_intermediate_boarding,
                'is_intermediate_deboarding': is_intermediate_deboarding,
                'origin_station': train.source_station,
                'final_destination': train.destination_station,
                'all_stops': sorted_routes,
                'classes': availabilities
            })
            
    # Sort results by scheduled departure time ascending
    results.sort(key=lambda item: item['src_route'].departure_time if item['src_route'].departure_time != '--:--' else '99:99')
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

def get_occupied_seat_numbers(train_id, journey_date, travel_class):
    """Return set of seat numbers currently occupied by active CNF passengers for this train run."""
    occupied = db.session.query(Passenger.seat_no).join(Booking).filter(
        Booking.train_id == train_id,
        Booking.journey_date == journey_date,
        Booking.travel_class == travel_class,
        Passenger.current_status == 'CNF',
        Passenger.is_cancelled == False,
        Passenger.seat_no.isnot(None)
    ).all()
    return {s[0] for s in occupied}

def find_available_seat_number(travel_class, occupied_seats, min_seat, max_seat, preference, passenger_age):
    """
    Find an unoccupied seat number between min_seat and max_seat without collision.
    Matches berth preference if a free matching seat exists; otherwise allocates next free sequential seat.
    Senior citizens (age >= 60) prioritize Lower berth.
    """
    target_pref = preference
    if passenger_age >= 60 and preference in ['No Preference', 'Lower']:
        target_pref = 'Lower'

    # Collect free candidate seats in quota range
    free_seats = [s for s in range(min_seat, max_seat + 1) if s not in occupied_seats]
    if not free_seats:
        # Fallback beyond max_seat if needed
        free_seats = [s for s in range(1, 500) if s not in occupied_seats]
        if not free_seats:
            return 1, assign_berth_type(travel_class, 1)

    # Search for preference match among free seats
    if target_pref and target_pref != 'No Preference':
        for s in free_seats:
            b_type = assign_berth_type(travel_class, s)
            if b_type.lower() == target_pref.lower():
                return s, b_type

    chosen = free_seats[0]
    return chosen, assign_berth_type(travel_class, chosen)

def find_preferred_seat_number(travel_class, current_cnf_count, preference, passenger_age):
    """
    Intelligent Berth Preference Allocator (backward-compatible wrapper).
    """
    total_capacity = 72
    target_pref = preference
    if passenger_age >= 60 and preference in ['No Preference', 'Lower']:
        target_pref = 'Lower'
        
    start_seat = current_cnf_count + 1
    
    for check_seat in range(start_seat, min(start_seat + 16, total_capacity + 1)):
        b_type = assign_berth_type(travel_class, check_seat)
        if target_pref != 'No Preference' and b_type.lower() == target_pref.lower():
            return check_seat, b_type

    fallback_seat = start_seat
    fallback_berth = assign_berth_type(travel_class, fallback_seat)
    return fallback_seat, fallback_berth

def book_ticket(user_id, train_id, from_station_id, to_station_id, journey_date, travel_class, quota, passengers_data, server_now=None):
    """
    Process ticket booking for multiple passengers.
    Allocates CNF/RAC/WL sequentially, matching berth preferences for CNF seats.
    Strictly validates 14-day Advance Reservation Period and 10:00 AM Tatkal window.
    Guarantees zero duplicate seat numbers.
    """
    # 1. Validate Advance Reservation Period (14 Days)
    is_arp_valid, arp_err = validate_advance_reservation_period(journey_date)
    if not is_arp_valid:
        return False, arp_err

    # 2. Validate Tatkal Quota Rules (10:00 AM server time and Tomorrow's date only)
    is_tatkal_valid, tatkal_err = validate_tatkal_eligibility(journey_date, quota, server_now=server_now)
    if not is_tatkal_valid:
        return False, tatkal_err

    train = db.session.get(Train, train_id)
    from_st = db.session.get(Station, from_station_id)
    to_st = db.session.get(Station, to_station_id)
    
    if not train or not from_st or not to_st:
        return False, "Invalid train or station selected."
        
    src_r = RouteStation.query.filter_by(train_id=train_id, station_id=from_station_id).first()
    dst_r = RouteStation.query.filter_by(train_id=train_id, station_id=to_station_id).first()
    if not src_r or not dst_r or src_r.stop_number >= dst_r.stop_number:
        return False, "Invalid station sequence for selected train."

    distance = max(1.0, round(dst_r.distance_km - src_r.distance_km, 1))
    fare_info = calculate_fare(distance, travel_class, quota)
    total_fare = fare_info['total_per_passenger'] * len(passengers_data)
    
    avail = get_class_availability(train_id, journey_date, travel_class, quota=quota)
    
    total_passengers = len(passengers_data)
    available_total_capacity = avail['cnf_left'] + avail['rac_left'] + avail['wl_left']
    if total_passengers > available_total_capacity:
        quota_label = "Tatkal" if quota == 'TQ' else "General"
        return False, f"Not enough seats available in {quota_label} quota. Max available: {available_total_capacity}"
        
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
    occupied_seats = get_occupied_seat_numbers(train_id, journey_date, travel_class)
    cfg = CoachQuotaConfig.query.filter_by(train_id=train_id, travel_class=travel_class).first()
    tatkal_cnf_seats = max(1, round(cfg.total_cnf_seats * 0.30)) if cfg else 10
    general_cnf_seats = max(0, cfg.total_cnf_seats - tatkal_cnf_seats) if cfg else 20
    
    for p_idx, p_data in enumerate(passengers_data):
        current_avail = get_class_availability(train_id, journey_date, travel_class, quota=quota)
        
        status = ''
        coach_no = None
        seat_no = None
        berth_type = None
        rac_wl_num = None
        
        p_age = int(p_data.get('age', 30))
        p_pref = p_data.get('berth_preference', 'No Preference')
        
        if current_avail['cnf_left'] > 0:
            status = 'CNF'
            if quota == 'TQ':
                min_s = general_cnf_seats + 1
                max_s = cfg.total_cnf_seats if cfg else 30
            else:
                min_s = 1
                max_s = general_cnf_seats
                
            seat_no, berth_type = find_available_seat_number(travel_class, occupied_seats, min_s, max_s, p_pref, p_age)
            occupied_seats.add(seat_no)
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
            coach_no = 'TQWL' if quota == 'TQ' else 'WL'
            seat_no = None
            berth_type = 'No Berth Allocated'
            
        b_status_str = f"TQWL / {rac_wl_num}" if (quota == 'TQ' and status == 'WL') else (f"{status} / {rac_wl_num}" if rac_wl_num else "CNF")
        passenger = Passenger(
            booking_id=booking.id,
            name=p_data['name'],
            age=p_age,
            gender=p_data['gender'],
            berth_preference=p_pref,
            booking_status=b_status_str,
            current_status=status,
            coach_no=coach_no,
            seat_no=seat_no,
            berth_type=berth_type,
            rac_wl_number=rac_wl_num,
            is_cancelled=False
        )
        db.session.add(passenger)
        db.session.flush()
        
    db.session.commit()
    return True, booking
