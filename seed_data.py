import os
import sys
from datetime import date, datetime, timedelta
from models import db, User, Station, Train, RouteStation, CoachQuotaConfig, Booking, Passenger
from services.booking_service import book_ticket

def is_database_seeded():
    """
    Check if the database has already been seeded.
    Returns True if stations, trains, and at least one admin account already exist.
    """
    try:
        has_stations = Station.query.first() is not None
        has_trains = Train.query.first() is not None
        has_admin = User.query.filter_by(role='admin').first() is not None
        return has_stations and has_trains and has_admin
    except Exception as e:
        # If tables do not exist yet, treat as not seeded
        return False

def seed_if_empty(app=None):
    """
    Safe entry point for application startup.
    Only runs seeding if the database is completely uninitialized.
    Never drops tables and never overwrites existing records.
    """
    if not is_database_seeded():
        print("[Database Init] Empty database detected. Running initial safe seed...")
        return seed(app=app, force=False)
    else:
        print("[Database Init] Database already initialized. Skipping redundant seed.")
        return False

def seed(app=None, force=False):
    """
    Idempotent seeding routine.
    - If force=False: Preserves existing data, checks if already seeded, and uses IF NOT EXISTS logic.
    - If force=True: Explicitly drops all tables and re-seeds from scratch (manual CLI override only).
    """
    if app is None:
        from app import create_app
        app = create_app()

    with app.app_context():
        if force:
            print("[Database Init] FORCE mode active. Dropping and recreating all tables...")
            db.drop_all()
            db.create_all()
        else:
            db.create_all()
            if is_database_seeded():
                st_count = Station.query.count()
                tr_count = Train.query.count()
                u_count = User.query.count()
                print(f"[Database Init] Database already seeded ({st_count} stations, {tr_count} trains, {u_count} users).")
                print("[Database Init] Skipping seeding to protect existing user data and performance.")
                return True

        print("--> Seeding Users (with Administrator Privileges)...")
        # 1. Primary IRCTC Chief Administrator
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@irctc.gov.in',
                full_name='IRCTC Chief Administrator',
                phone='9811001122',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)

        # 2. Southern Railway Administrator (Dedicated Admin for South Indian Railways)
        sr_admin = User.query.filter_by(username='south_admin').first()
        if not sr_admin:
            sr_admin = User(
                username='south_admin',
                email='admin.sr@indianrail.gov.in',
                full_name='Southern Railway Principal Chief Operations Manager',
                phone='044-25353142',
                role='admin'
            )
            sr_admin.set_password('admin123')
            db.session.add(sr_admin)

        # Passenger accounts
        passengers_meta = [
            ('anand', 'anand.s@gmail.com', 'Anand Subramanian', '9840123456'),
            ('karthik', 'karthik.r@gmail.com', 'Karthik Ramanathan', '9443123456'),
            ('lakshmi', 'lakshmi.nair@gmail.com', 'Lakshmi Nair', '9847123456'),
            ('passenger', 'user@gmail.com', 'Rahul Sharma', '9876543210'),
            ('priya', 'priya.v@gmail.com', 'Priya Verma', '9876500112'),
        ]
        user_objs = {}
        for uname, uemail, ufullname, uphone in passengers_meta:
            existing_u = User.query.filter_by(username=uname).first()
            if not existing_u:
                existing_u = User(username=uname, email=uemail, full_name=ufullname, phone=uphone, role='user')
                existing_u.set_password('user123')
                db.session.add(existing_u)
            user_objs[uname] = existing_u

        db.session.commit()

        print("--> Seeding Real-World South Indian Railway Stations & Major Hubs...")
        stations_data = [
            # Tamil Nadu (Southern Railway)
            {'code': 'MAS', 'name': 'MGR Chennai Central', 'city': 'Chennai', 'state': 'Tamil Nadu'},
            {'code': 'MS', 'name': 'Chennai Egmore', 'city': 'Chennai', 'state': 'Tamil Nadu'},
            {'code': 'CBE', 'name': 'Coimbatore Junction', 'city': 'Coimbatore', 'state': 'Tamil Nadu'},
            {'code': 'MDU', 'name': 'Madurai Junction', 'city': 'Madurai', 'state': 'Tamil Nadu'},
            {'code': 'TPJ', 'name': 'Tiruchchirappalli Junction', 'city': 'Tiruchchirappalli', 'state': 'Tamil Nadu'},
            {'code': 'SA', 'name': 'Salem Junction', 'city': 'Salem', 'state': 'Tamil Nadu'},
            {'code': 'ED', 'name': 'Erode Junction', 'city': 'Erode', 'state': 'Tamil Nadu'},
            {'code': 'KPD', 'name': 'Katpadi Junction (Vellore)', 'city': 'Vellore', 'state': 'Tamil Nadu'},
            {'code': 'TEN', 'name': 'Tirunelveli Junction', 'city': 'Tirunelveli', 'state': 'Tamil Nadu'},

            # Kerala (Southern Railway)
            {'code': 'TVC', 'name': 'Thiruvananthapuram Central', 'city': 'Thiruvananthapuram', 'state': 'Kerala'},
            {'code': 'ERS', 'name': 'Ernakulam Junction (South)', 'city': 'Kochi', 'state': 'Kerala'},
            {'code': 'CLT', 'name': 'Kozhikode Main (Calicut)', 'city': 'Kozhikode', 'state': 'Kerala'},
            {'code': 'CAN', 'name': 'Kannur', 'city': 'Kannur', 'state': 'Kerala'},
            {'code': 'TCR', 'name': 'Thrissur', 'city': 'Thrissur', 'state': 'Kerala'},
            {'code': 'PGT', 'name': 'Palakkad Junction', 'city': 'Palakkad', 'state': 'Kerala'},

            # Karnataka (South Western Railway)
            {'code': 'SBC', 'name': 'KSR Bengaluru City', 'city': 'Bengaluru', 'state': 'Karnataka'},
            {'code': 'MYS', 'name': 'Mysuru Junction', 'city': 'Mysuru', 'state': 'Karnataka'},

            # Andhra Pradesh & Telangana (South Central Railway)
            {'code': 'SC', 'name': 'Secunderabad Junction (Hyderabad)', 'city': 'Hyderabad', 'state': 'Telangana'},
            {'code': 'BZA', 'name': 'Vijayawada Junction', 'city': 'Vijayawada', 'state': 'Andhra Pradesh'},
            {'code': 'TPTY', 'name': 'Tirupati Main', 'city': 'Tirupati', 'state': 'Andhra Pradesh'},

            # National Connecting Hubs
            {'code': 'NDLS', 'name': 'New Delhi', 'city': 'New Delhi', 'state': 'Delhi'},
            {'code': 'MMCT', 'name': 'Mumbai Central', 'city': 'Mumbai', 'state': 'Maharashtra'},
            {'code': 'HWH', 'name': 'Howrah Junction (Kolkata)', 'city': 'Kolkata', 'state': 'West Bengal'}
        ]

        station_objs = {}
        for s in stations_data:
            existing_st = Station.query.filter_by(code=s['code']).first()
            if not existing_st:
                existing_st = Station(code=s['code'], name=s['name'], city=s['city'], state=s['state'])
                db.session.add(existing_st)
            station_objs[s['code']] = existing_st

        db.session.commit()

        print("--> Seeding Real-World South Indian Trains & Schedules...")

        trains_data = [
            {
                'train_number': '20607',
                'name': 'Chennai - Mysuru Vande Bharat Express',
                'source': 'MAS',
                'dest': 'MYS',
                'days': 'Mon,Tue,Thu,Fri,Sat,Sun',
                'routes': [
                    ('MAS', 1, 0.0, '--:--', '05:50', 1),
                    ('KPD', 2, 130.0, '07:13', '07:15', 1),
                    ('SBC', 3, 360.0, '10:15', '10:20', 1),
                    ('MYS', 4, 500.0, '12:20', '--:--', 1),
                ],
                'quotas': [('CC', 5, 2, 2, 1.8), ('1A', 3, 1, 1, 3.4)]
            },
            {
                'train_number': '12675',
                'name': 'Kovai Superfast Express',
                'source': 'MAS',
                'dest': 'CBE',
                'days': 'Daily',
                'routes': [
                    ('MAS', 1, 0.0, '--:--', '06:10', 1),
                    ('KPD', 2, 130.0, '07:53', '07:55', 1),
                    ('SA', 3, 335.0, '10:52', '10:55', 1),
                    ('ED', 4, 395.0, '11:50', '11:55', 1),
                    ('CBE', 5, 495.0, '14:05', '--:--', 1),
                ],
                'quotas': [('CC', 5, 2, 2, 1.5), ('2S', 6, 2, 2, 0.6)]
            },
            {
                'train_number': '12635',
                'name': 'Vaigai Superfast Express',
                'source': 'MS',
                'dest': 'MDU',
                'days': 'Daily',
                'routes': [
                    ('MS', 1, 0.0, '--:--', '13:50', 1),
                    ('TPJ', 2, 336.0, '19:45', '19:50', 1),
                    ('MDU', 3, 497.0, '21:30', '--:--', 1),
                ],
                'quotas': [('CC', 5, 2, 2, 1.5), ('2S', 6, 2, 2, 0.6)]
            },
            {
                'train_number': '20633',
                'name': 'Kerala Vande Bharat Express',
                'source': 'CAN',
                'dest': 'TVC',
                'days': 'Mon,Tue,Wed,Fri,Sat,Sun',
                'routes': [
                    ('CAN', 1, 0.0, '--:--', '15:28', 1),
                    ('CLT', 2, 89.0, '16:28', '16:30', 1),
                    ('TCR', 3, 208.0, '18:10', '18:12', 1),
                    ('ERS', 4, 282.0, '19:17', '19:20', 1),
                    ('TVC', 5, 501.0, '22:40', '--:--', 1),
                ],
                'quotas': [('CC', 5, 2, 2, 1.8), ('1A', 3, 1, 1, 3.4)]
            },
            {
                'train_number': '12624',
                'name': 'Trivandrum - Chennai Mail',
                'source': 'TVC',
                'dest': 'MAS',
                'days': 'Daily',
                'routes': [
                    ('TVC', 1, 0.0, '--:--', '15:00', 1),
                    ('TCR', 2, 292.0, '20:40', '20:43', 1),
                    ('PGT', 3, 368.0, '22:15', '22:20', 1),
                    ('CBE', 4, 423.0, '23:45', '23:50', 1),
                    ('ED', 5, 524.0, '01:15', '01:20', 2),
                    ('SA', 6, 584.0, '02:12', '02:15', 2),
                    ('KPD', 7, 788.0, '04:43', '04:45', 2),
                    ('MAS', 8, 918.0, '07:45', '--:--', 2),
                ],
                'quotas': [('1A', 3, 1, 1, 3.2), ('2A', 4, 2, 2, 2.4), ('3A', 4, 2, 2, 1.8), ('SL', 5, 2, 2, 1.0)]
            },
            {
                'train_number': '12695',
                'name': 'Chennai - Trivandrum Superfast Express',
                'source': 'MAS',
                'dest': 'TVC',
                'days': 'Daily',
                'routes': [
                    ('MAS', 1, 0.0, '--:--', '15:20', 1),
                    ('KPD', 2, 130.0, '17:08', '17:10', 1),
                    ('SA', 3, 335.0, '20:02', '20:05', 1),
                    ('ED', 4, 395.0, '21:05', '21:10', 1),
                    ('CBE', 5, 495.0, '22:50', '22:55', 1),
                    ('PGT', 6, 551.0, '00:05', '00:10', 2),
                    ('TCR', 7, 626.0, '01:30', '01:33', 2),
                    ('ERS', 8, 700.0, '02:50', '02:55', 2),
                    ('TVC', 9, 924.0, '07:45', '--:--', 2),
                ],
                'quotas': [('2A', 4, 2, 2, 2.4), ('3A', 4, 2, 2, 1.8), ('SL', 5, 2, 2, 1.0)]
            },
            {
                'train_number': '12637',
                'name': 'Pandian Superfast Express',
                'source': 'MS',
                'dest': 'MDU',
                'days': 'Daily',
                'routes': [
                    ('MS', 1, 0.0, '--:--', '21:40', 1),
                    ('TPJ', 2, 336.0, '03:30', '03:35', 2),
                    ('MDU', 3, 497.0, '05:35', '--:--', 2),
                ],
                'quotas': [('1A', 3, 1, 1, 3.2), ('2A', 4, 2, 2, 2.4), ('3A', 4, 2, 2, 1.8), ('SL', 5, 2, 2, 1.0)]
            },
            {
                'train_number': '16525',
                'name': 'Island Express (Kanyakumari - Bengaluru)',
                'source': 'TVC',
                'dest': 'SBC',
                'days': 'Daily',
                'routes': [
                    ('TVC', 1, 0.0, '--:--', '12:40', 1),
                    ('ERS', 2, 220.0, '17:10', '17:15', 1),
                    ('TCR', 3, 294.0, '18:20', '18:23', 1),
                    ('PGT', 4, 370.0, '19:50', '19:55', 1),
                    ('CBE', 5, 425.0, '22:15', '22:20', 1),
                    ('ED', 6, 526.0, '00:05', '00:10', 2),
                    ('SA', 7, 586.0, '01:05', '01:10', 2),
                    ('SBC', 8, 944.0, '06:40', '--:--', 2),
                ],
                'quotas': [('2A', 4, 2, 2, 2.2), ('3A', 4, 2, 2, 1.7), ('SL', 5, 2, 2, 0.9)]
            },
            {
                'train_number': '12759',
                'name': 'Charminar Superfast Express',
                'source': 'MAS',
                'dest': 'SC',
                'days': 'Daily',
                'routes': [
                    ('MAS', 1, 0.0, '--:--', '17:30', 1),
                    ('BZA', 2, 431.0, '00:45', '00:55', 2),
                    ('SC', 3, 790.0, '07:30', '--:--', 2),
                ],
                'quotas': [('1A', 3, 1, 1, 3.2), ('2A', 4, 2, 2, 2.3), ('3A', 4, 2, 2, 1.7), ('SL', 5, 2, 2, 0.9)]
            },
            {
                'train_number': '12626',
                'name': 'Kerala Superfast Express',
                'source': 'NDLS',
                'dest': 'TVC',
                'days': 'Daily',
                'routes': [
                    ('NDLS', 1, 0.0, '--:--', '20:10', 1),
                    ('BZA', 2, 1778.0, '04:15', '04:25', 3),
                    ('TPTY', 3, 2160.0, '06:45', '06:50', 3),
                    ('KPD', 4, 2265.0, '09:10', '09:15', 3),
                    ('SA', 5, 2470.0, '12:15', '12:20', 3),
                    ('ED', 6, 2530.0, '13:15', '13:20', 3),
                    ('CBE', 7, 2631.0, '14:55', '15:00', 3),
                    ('PGT', 8, 2687.0, '16:05', '16:10', 3),
                    ('TCR', 9, 2762.0, '17:20', '17:23', 3),
                    ('ERS', 10, 2836.0, '18:50', '18:55', 3),
                    ('TVC', 11, 3030.0, '22:10', '--:--', 3),
                ],
                'quotas': [('2A', 4, 2, 2, 2.3), ('3A', 4, 2, 2, 1.7), ('SL', 5, 2, 2, 0.9)]
            }
        ]

        for t_info in trains_data:
            existing_train = Train.query.filter_by(train_number=t_info['train_number']).first()
            if not existing_train:
                existing_train = Train(
                    train_number=t_info['train_number'],
                    name=t_info['name'],
                    source_station_id=station_objs[t_info['source']].id,
                    destination_station_id=station_objs[t_info['dest']].id,
                    operating_days=t_info['days'],
                    is_active=True
                )
                db.session.add(existing_train)
                db.session.flush()

                for st_code, stop_num, dist, arr, dep, day in t_info['routes']:
                    db.session.add(RouteStation(
                        train_id=existing_train.id,
                        station_id=station_objs[st_code].id,
                        stop_number=stop_num,
                        distance_km=dist,
                        arrival_time=arr,
                        departure_time=dep,
                        day_number=day
                    ))

                for t_class, cnf_s, rac_s, wl_s, fare in t_info['quotas']:
                    db.session.add(CoachQuotaConfig(
                        train_id=existing_train.id,
                        travel_class=t_class,
                        total_cnf_seats=cnf_s,
                        total_rac_seats=rac_s,
                        total_wl_seats=wl_s,
                        base_fare_per_km=fare
                    ))

        db.session.commit()

        print("--> Generating Realistic High-Occupancy Bookings on South Indian Routes (CNF, RAC, WL)...")
        # Upcoming travel dates
        upcoming_dates = [
            date(2026, 10, 25),
            date(2026, 10, 28),
            date(2026, 11, 2),
            date(2026, 11, 5),
            date(2026, 11, 10),
            date(2026, 11, 15)
        ]

        south_passengers = [
            ('Anand Subramanian', 34, 'Male', 'Lower'),
            ('Deepa Subramanian', 31, 'Female', 'Middle'),
            ('S. Ramanathan', 68, 'Male', 'Lower'),       # Senior citizen auto-lower priority
            ('Karthik Ramanathan', 38, 'Male', 'Side Lower'),
            ('Meenakshi Sundaram', 42, 'Female', 'Upper'),
            ('Lakshmi Nair', 29, 'Female', 'Window'),
            ('Unnikrishnan Namboothiri', 64, 'Male', 'Lower'),
            ('Gopalan Nair', 55, 'Male', 'Side Upper')
        ]

        t1_obj = Train.query.filter_by(train_number='20607').first()
        t2_obj = Train.query.filter_by(train_number='12675').first()
        t5_obj = Train.query.filter_by(train_number='12624').first()
        t7_obj = Train.query.filter_by(train_number='12637').first()

        for target_date in upcoming_dates:
            # Check if bookings already exist for this date to maintain idempotency
            existing_booking_count = Booking.query.filter_by(journey_date=target_date).count()
            if existing_booking_count > 0:
                continue

            if t1_obj:
                # 1. Chennai Central -> Mysuru (Vande Bharat 20607 CC): CNF, RAC, WL
                book_ticket(
                    user_id=user_objs['anand'].id, train_id=t1_obj.id,
                    from_station_id=station_objs['MAS'].id, to_station_id=station_objs['SBC'].id,
                    journey_date=target_date, travel_class='CC', quota='GN',
                    passengers_data=[
                        {'name': south_passengers[0][0], 'age': south_passengers[0][1], 'gender': south_passengers[0][2], 'berth_preference': south_passengers[0][3]},
                        {'name': south_passengers[1][0], 'age': south_passengers[1][1], 'gender': south_passengers[1][2], 'berth_preference': south_passengers[1][3]},
                        {'name': south_passengers[2][0], 'age': south_passengers[2][1], 'gender': south_passengers[2][2], 'berth_preference': south_passengers[2][3]}
                    ]
                )
                book_ticket(
                    user_id=user_objs['karthik'].id, train_id=t1_obj.id,
                    from_station_id=station_objs['MAS'].id, to_station_id=station_objs['MYS'].id,
                    journey_date=target_date, travel_class='CC', quota='GN',
                    passengers_data=[
                        {'name': south_passengers[3][0], 'age': south_passengers[3][1], 'gender': south_passengers[3][2], 'berth_preference': south_passengers[3][3]},
                        {'name': south_passengers[4][0], 'age': south_passengers[4][1], 'gender': south_passengers[4][2], 'berth_preference': south_passengers[4][3]}
                    ]
                )
                book_ticket(
                    user_id=user_objs['lakshmi'].id, train_id=t1_obj.id,
                    from_station_id=station_objs['MAS'].id, to_station_id=station_objs['SBC'].id,
                    journey_date=target_date, travel_class='CC', quota='GN',
                    passengers_data=[
                        {'name': south_passengers[5][0], 'age': south_passengers[5][1], 'gender': south_passengers[5][2], 'berth_preference': south_passengers[5][3]},
                        {'name': south_passengers[6][0], 'age': south_passengers[6][1], 'gender': south_passengers[6][2], 'berth_preference': south_passengers[6][3]}
                    ]
                )

            if t2_obj:
                # 2. Chennai Central -> Coimbatore (Kovai Express 12675 CC): Bookings
                book_ticket(
                    user_id=user_objs['karthik'].id, train_id=t2_obj.id,
                    from_station_id=station_objs['MAS'].id, to_station_id=station_objs['CBE'].id,
                    journey_date=target_date, travel_class='CC', quota='GN',
                    passengers_data=[
                        {'name': 'Balaji Srinivasan', 'age': 45, 'gender': 'Male', 'berth_preference': 'Window'},
                        {'name': 'Kavitha Balaji', 'age': 40, 'gender': 'Female', 'berth_preference': 'Aisle'},
                        {'name': 'Suresh Kumar', 'age': 28, 'gender': 'Male', 'berth_preference': 'Window'}
                    ]
                )

            if t5_obj:
                # 3. Trivandrum -> Chennai Mail (12624 3A): CNF & RAC bookings
                book_ticket(
                    user_id=user_objs['lakshmi'].id, train_id=t5_obj.id,
                    from_station_id=station_objs['TVC'].id, to_station_id=station_objs['MAS'].id,
                    journey_date=target_date, travel_class='3A', quota='GN',
                    passengers_data=[
                        {'name': 'Madhavan Nair', 'age': 52, 'gender': 'Male', 'berth_preference': 'Lower'},
                        {'name': 'Geetha Nair', 'age': 48, 'gender': 'Female', 'berth_preference': 'Upper'},
                        {'name': 'Vishnu Madhavan', 'age': 22, 'gender': 'Male', 'berth_preference': 'Side Lower'}
                    ]
                )

            if t7_obj:
                # 4. Chennai Egmore -> Madurai (Pandian Express 12637 SL):
                book_ticket(
                    user_id=user_objs['priya'].id, train_id=t7_obj.id,
                    from_station_id=station_objs['MS'].id, to_station_id=station_objs['MDU'].id,
                    journey_date=target_date, travel_class='SL', quota='GN',
                    passengers_data=[
                        {'name': 'Murugan Pandian', 'age': 38, 'gender': 'Male', 'berth_preference': 'Lower'},
                        {'name': 'Selvi Murugan', 'age': 34, 'gender': 'Female', 'berth_preference': 'Middle'}
                    ]
                )

        print("\n========================================================")
        print("--> DATABASE SEEDING ROUTINE COMPLETED SUCCESSFULLY!")
        print("========================================================")
        print("ADMIN ACCOUNTS WITH FULL PRIVILEGES:")
        print("  1. Primary Admin:   username='admin',       password='admin123'")
        print("  2. Southern Admin:  username='south_admin', password='admin123'")
        print("========================================================")
        return True

if __name__ == '__main__':
    force_run = '--force' in sys.argv or '-f' in sys.argv
    seed(force=force_run)
