import os
import sys
import random
from datetime import datetime, date, timedelta, time
from werkzeug.security import generate_password_hash
from models import db, User, Station, Train, RouteStation, CoachQuotaConfig, Booking, Passenger, ChartLog

def is_database_seeded():
    """
    Check if the database has already been seeded.
    Returns True if stations, trains, and at least one admin account already exist.
    """
    try:
        has_stations = Station.query.first() is not None
        has_trains = Train.query.first() is not None
        has_admin = User.query.filter_by(role='admin').first() is not None
        has_bookings = Booking.query.first() is not None
        return has_stations and has_trains and has_admin and has_bookings
    except Exception:
        return False

def seed_if_empty(app=None):
    """
    Safe entry point for application startup.
    Only runs seeding if the database is completely uninitialized.
    Never drops tables and never overwrites existing records.
    """
    if not is_database_seeded():
        print("[Database Init] Empty or partially seeded database detected. Running initial safe seed...")
        return seed(app=app, force=False)
    else:
        print("[Database Init] Database already initialized. Skipping redundant seed.")
        return False

def seed(app=None, force=False):
    if not force and is_database_seeded():
        print("[Database Init] Database already seeded. Skipping redundant seed.")
        return True
    return build_data(app=app, force=force)


def build_data(app=None, force=False):
    if app is None:
        try:
            from flask import current_app
            if current_app:
                app = current_app._get_current_object()
        except Exception:
            pass

    if app is None:
        from app import create_app
        app = create_app()

    with app.app_context():
        print(f"Connecting to database: {db.engine.url}")
        
        # 1. Wipe all existing data ONLY if force=True
        if force:
            print("--> Force mode active: Deleting all existing data currently in database...")
            if db.engine.name == 'sqlite':
                db.session.execute(db.text("PRAGMA foreign_keys = OFF;"))
                for table in ['chart_logs', 'passengers', 'bookings', 'coach_quota_configs', 'route_stations', 'trains', 'stations', 'users']:
                    db.session.execute(db.text(f"DELETE FROM {table};"))
                db.session.execute(db.text("PRAGMA foreign_keys = ON;"))
            else:
                db.session.execute(db.text("SET FOREIGN_KEY_CHECKS = 0;"))
                for table in ['chart_logs', 'passengers', 'bookings', 'coach_quota_configs', 'route_stations', 'trains', 'stations', 'users']:
                    db.session.execute(db.text(f"TRUNCATE TABLE {table};"))
                db.session.execute(db.text("SET FOREIGN_KEY_CHECKS = 1;"))
            db.session.commit()
            print("--> Database wiped successfully.")

        # 2. Seed Users (Requirement 7: Admin password 'qwertyuiop')
        print("--> Requirement 7: Seeding admin accounts with password 'qwertyuiop'...")
        admin_hash = generate_password_hash('qwertyuiop')
        user_hash = generate_password_hash('user123')

        users = [
            User(username='admin', email='admin@irctc.gov.in', password_hash=admin_hash, full_name='IRCTC Chief Administrator', phone='9811001122', role='admin'),
            User(username='south_admin', email='admin.sr@indianrail.gov.in', password_hash=admin_hash, full_name='Southern Railway Principal Chief Operations Manager', phone='044-25353142', role='admin'),
            User(username='anand', email='anand.s@gmail.com', password_hash=user_hash, full_name='Anand Subramanian', phone='9840123456', role='user'),
            User(username='karthik', email='karthik.r@gmail.com', password_hash=user_hash, full_name='Karthik Ramanathan', phone='9443123456', role='user'),
            User(username='lakshmi', email='lakshmi.nair@gmail.com', password_hash=user_hash, full_name='Lakshmi Nair', phone='9847123456', role='user'),
            User(username='passenger', email='user@gmail.com', password_hash=user_hash, full_name='Rahul Sharma', phone='9876543210', role='user'),
            User(username='priya', email='priya.v@gmail.com', password_hash=user_hash, full_name='Priya Verma', phone='9876500112', role='user'),
            User(username='suresh', email='suresh.m@gmail.com', password_hash=user_hash, full_name='Suresh Menon', phone='9846100223', role='user'),
            User(username='divya', email='divya.k@gmail.com', password_hash=user_hash, full_name='Divya Krishnan', phone='9444200334', role='user'),
            User(username='venkat', email='venkat.r@gmail.com', password_hash=user_hash, full_name='Venkatesh Rao', phone='9880300445', role='user'),
            User(username='meena', email='meena.b@gmail.com', password_hash=user_hash, full_name='Meenakshi Sundaram', phone='9842400556', role='user'),
        ]
        user_map = {}
        for u in users:
            existing = User.query.filter_by(username=u.username).first()
            if not existing:
                db.session.add(u)
                user_map[u.username] = u
            else:
                existing.password_hash = u.password_hash
                user_map[u.username] = existing
        db.session.commit()
        print(f"--> Seeded/Verified {len(users)} users.")

        # 3. Seed Stations (Requirement 9: South Indian Network)
        print("--> Requirement 9: Seeding expanded South Indian railway stations...")
        stations_data = [
            # Tamil Nadu
            ('MAS', 'MGR Chennai Central', 'Chennai', 'Tamil Nadu'),
            ('MS', 'Chennai Egmore', 'Chennai', 'Tamil Nadu'),
            ('TBM', 'Tambaram', 'Chennai', 'Tamil Nadu'),
            ('CGL', 'Chengalpattu Junction', 'Chengalpattu', 'Tamil Nadu'),
            ('VM', 'Villupuram Junction', 'Villupuram', 'Tamil Nadu'),
            ('KPD', 'Katpadi Junction (Vellore)', 'Vellore', 'Tamil Nadu'),
            ('JTJ', 'Jolarpettai Junction', 'Jolarpettai', 'Tamil Nadu'),
            ('SA', 'Salem Junction', 'Salem', 'Tamil Nadu'),
            ('ED', 'Erode Junction', 'Erode', 'Tamil Nadu'),
            ('TUP', 'Tiruppur', 'Tiruppur', 'Tamil Nadu'),
            ('CBE', 'Coimbatore Junction', 'Coimbatore', 'Tamil Nadu'),
            ('MTP', 'Mettupalayam', 'Mettupalayam', 'Tamil Nadu'),
            ('TPJ', 'Tiruchchirappalli Junction', 'Tiruchchirappalli', 'Tamil Nadu'),
            ('TJ', 'Thanjavur Junction', 'Thanjavur', 'Tamil Nadu'),
            ('KMU', 'Kumbakonam', 'Kumbakonam', 'Tamil Nadu'),
            ('MV', 'Mayiladuthurai Junction', 'Mayiladuthurai', 'Tamil Nadu'),
            ('DG', 'Dindigul Junction', 'Dindigul', 'Tamil Nadu'),
            ('MDU', 'Madurai Junction', 'Madurai', 'Tamil Nadu'),
            ('VPT', 'Virudhunagar Junction', 'Virudhunagar', 'Tamil Nadu'),
            ('CVP', 'Kovilpatti', 'Kovilpatti', 'Tamil Nadu'),
            ('TEN', 'Tirunelveli Junction', 'Tirunelveli', 'Tamil Nadu'),
            ('NCJ', 'Nagercoil Junction', 'Nagercoil', 'Tamil Nadu'),
            ('CAPE', 'Kanniyakumari', 'Kanniyakumari', 'Tamil Nadu'),
            ('TN', 'Thoothukudi', 'Thoothukudi', 'Tamil Nadu'),
            ('RMM', 'Rameswaram', 'Rameswaram', 'Tamil Nadu'),
            ('MNM', 'Manamadurai Junction', 'Manamadurai', 'Tamil Nadu'),

            # Kerala
            ('TVC', 'Thiruvananthapuram Central', 'Thiruvananthapuram', 'Kerala'),
            ('QLN', 'Kollam Junction (Quilon)', 'Kollam', 'Kerala'),
            ('ALLP', 'Alappuzha (Alleppey)', 'Alappuzha', 'Kerala'),
            ('KTYM', 'Kottayam', 'Kottayam', 'Kerala'),
            ('ERS', 'Ernakulam Junction (South)', 'Kochi', 'Kerala'),
            ('ERN', 'Ernakulam Town (North)', 'Kochi', 'Kerala'),
            ('AWY', 'Aluva', 'Aluva', 'Kerala'),
            ('TCR', 'Thrissur', 'Thrissur', 'Kerala'),
            ('SRR', 'Shoranur Junction', 'Shoranur', 'Kerala'),
            ('PGT', 'Palakkad Junction', 'Palakkad', 'Kerala'),
            ('TIR', 'Tirur', 'Tirur', 'Kerala'),
            ('CLT', 'Kozhikode Main (Calicut)', 'Kozhikode', 'Kerala'),
            ('BDJ', 'Vadakara', 'Vadakara', 'Kerala'),
            ('TLY', 'Thalassery', 'Thalassery', 'Kerala'),
            ('CAN', 'Kannur', 'Kannur', 'Kerala'),
            ('PAY', 'Payyanur', 'Payyanur', 'Kerala'),
            ('KGQ', 'Kasaragod', 'Kasaragod', 'Kerala'),
            ('GUV', 'Guruvayur', 'Guruvayur', 'Kerala'),

            # Karnataka
            ('SBC', 'KSR Bengaluru City', 'Bengaluru', 'Karnataka'),
            ('YPR', 'Yesvantpur Junction', 'Bengaluru', 'Karnataka'),
            ('SMVB', 'SMVT Bengaluru', 'Bengaluru', 'Karnataka'),
            ('BNC', 'Bengaluru Cantt', 'Bengaluru', 'Karnataka'),
            ('KJM', 'Krishnarajapuram', 'Bengaluru', 'Karnataka'),
            ('BWT', 'Bangarapet', 'Bangarapet', 'Karnataka'),
            ('MYS', 'Mysuru Junction', 'Mysuru', 'Karnataka'),
            ('HAS', 'Hassan Junction', 'Hassan', 'Karnataka'),
            ('ASK', 'Arsikere Junction', 'Arsikere', 'Karnataka'),
            ('DVG', 'Davangere', 'Davangere', 'Karnataka'),
            ('UBL', 'SSS Hubballi Junction', 'Hubballi', 'Karnataka'),
            ('DWR', 'Dharwad', 'Dharwad', 'Karnataka'),
            ('BGM', 'Belagavi (Belgaum)', 'Belagavi', 'Karnataka'),
            ('MAQ', 'Mangaluru Central', 'Mangaluru', 'Karnataka'),
            ('MAJN', 'Mangaluru Junction', 'Mangaluru', 'Karnataka'),
            ('UD', 'Udupi', 'Udupi', 'Karnataka'),
            ('KUDA', 'Kundapura', 'Kundapura', 'Karnataka'),
            ('BYNR', 'Byndoor Mookambika Road', 'Byndoor', 'Karnataka'),
            ('KT', 'Kumta', 'Kumta', 'Karnataka'),
            ('KAWR', 'Karwar', 'Karwar', 'Karnataka'),

            # Andhra Pradesh & Telangana
            ('SC', 'Secunderabad Junction', 'Hyderabad', 'Telangana'),
            ('HYB', 'Hyderabad Deccan (Nampally)', 'Hyderabad', 'Telangana'),
            ('KCG', 'Kacheguda', 'Hyderabad', 'Telangana'),
            ('KZJ', 'Kazipet Junction', 'Kazipet', 'Telangana'),
            ('WL', 'Warangal', 'Warangal', 'Telangana'),
            ('KMT', 'Khammam', 'Khammam', 'Telangana'),
            ('BZA', 'Vijayawada Junction', 'Vijayawada', 'Andhra Pradesh'),
            ('EE', 'Eluru', 'Eluru', 'Andhra Pradesh'),
            ('RJY', 'Rajahmundry', 'Rajahmundry', 'Andhra Pradesh'),
            ('SLO', 'Samalkot Junction', 'Samalkot', 'Andhra Pradesh'),
            ('AKP', 'Anakapalle', 'Anakapalle', 'Andhra Pradesh'),
            ('VSKP', 'Visakhapatnam Junction', 'Visakhapatnam', 'Andhra Pradesh'),
            ('GNT', 'Guntur Junction', 'Guntur', 'Andhra Pradesh'),
            ('TEL', 'Tenali Junction', 'Tenali', 'Andhra Pradesh'),
            ('OGL', 'Ongole', 'Ongole', 'Andhra Pradesh'),
            ('NLR', 'Nellore', 'Nellore', 'Andhra Pradesh'),
            ('GDR', 'Gudur Junction', 'Gudur', 'Andhra Pradesh'),
            ('RU', 'Renigunta Junction', 'Renigunta', 'Andhra Pradesh'),
            ('TPTY', 'Tirupati Main', 'Tirupati', 'Andhra Pradesh'),
            ('GY', 'Gooty Junction', 'Gooty', 'Andhra Pradesh'),
            ('GTL', 'Guntakal Junction', 'Guntakal', 'Andhra Pradesh'),
            ('KRNT', 'Kurnool City', 'Kurnool', 'Andhra Pradesh'),
            ('MBNR', 'Mahbubnagar', 'Mahbubnagar', 'Telangana'),

            # National Connecting Hubs
            ('NDLS', 'New Delhi', 'New Delhi', 'Delhi'),
            ('MMCT', 'Mumbai Central', 'Mumbai', 'Maharashtra'),
            ('HWH', 'Howrah Junction', 'Kolkata', 'West Bengal')
        ]

        for code, name, city, state in stations_data:
            existing = Station.query.filter_by(code=code).first()
            if not existing:
                st = Station(code=code, name=name, city=city, state=state)
                db.session.add(st)
        db.session.commit()
        st_map = {s.code: s for s in Station.query.all()}
        print(f"--> Seeded/Verified {len(st_map)} stations across South India.")

        # 4. Seed 50 Real South Indian Trains & Schedules (Requirement 9)
        print("--> Requirement 9: Seeding 50 real South Indian trains, routes, and coach configurations...")

        trains_def = [
            # 1 & 2: Chennai - Mysuru Vande Bharat
            ('20607', 'Chennai - Mysuru Vande Bharat Express', 'MAS', 'MYS', 'Mon,Tue,Thu,Fri,Sat,Sun', [
                ('MAS', 1, 0.0, '--:--', '05:50', 1),
                ('KPD', 2, 130.0, '07:13', '07:15', 1),
                ('SBC', 3, 360.0, '10:15', '10:20', 1),
                ('MYS', 4, 500.0, '12:20', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.8), ('1A', 4, 1, 4, 3.4)]),

            ('20608', 'Mysuru - Chennai Vande Bharat Express', 'MYS', 'MAS', 'Mon,Tue,Thu,Fri,Sat,Sun', [
                ('MYS', 1, 0.0, '--:--', '13:05', 1),
                ('SBC', 2, 140.0, '14:50', '14:55', 1),
                ('KPD', 3, 370.0, '17:58', '18:00', 1),
                ('MAS', 4, 500.0, '19:20', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.8), ('1A', 4, 1, 4, 3.4)]),

            # 3 & 4: Chennai - Coimbatore Vande Bharat
            ('20643', 'Chennai - Coimbatore Vande Bharat Express', 'MAS', 'CBE', 'Mon,Tue,Thu,Fri,Sat,Sun', [
                ('MAS', 1, 0.0, '--:--', '14:15', 1),
                ('SA', 2, 335.0, '17:48', '17:50', 1),
                ('ED', 3, 395.0, '18:32', '18:35', 1),
                ('TUP', 4, 445.0, '19:13', '19:15', 1),
                ('CBE', 5, 495.0, '20:15', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.8), ('1A', 4, 1, 4, 3.4)]),

            ('20644', 'Coimbatore - Chennai Vande Bharat Express', 'CBE', 'MAS', 'Mon,Tue,Thu,Fri,Sat,Sun', [
                ('CBE', 1, 0.0, '--:--', '06:00', 1),
                ('TUP', 2, 50.0, '06:35', '06:37', 1),
                ('ED', 3, 100.0, '07:12', '07:15', 1),
                ('SA', 4, 160.0, '07:58', '08:00', 1),
                ('MAS', 5, 495.0, '11:50', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.8), ('1A', 4, 1, 4, 3.4)]),

            # 5 & 6: Kasaragod - Thiruvananthapuram Vande Bharat
            ('20631', 'Kasaragod - Thiruvananthapuram Vande Bharat Express', 'KGQ', 'TVC', 'Mon,Tue,Wed,Fri,Sat,Sun', [
                ('KGQ', 1, 0.0, '--:--', '07:00', 1),
                ('CAN', 2, 86.0, '07:55', '07:57', 1),
                ('CLT', 3, 175.0, '08:57', '08:59', 1),
                ('SRR', 4, 261.0, '09:58', '10:00', 1),
                ('TCR', 5, 294.0, '10:38', '10:40', 1),
                ('ERN', 6, 365.0, '11:45', '11:48', 1),
                ('ALLP', 7, 422.0, '12:38', '12:40', 1),
                ('QLN', 8, 507.0, '13:40', '13:42', 1),
                ('TVC', 9, 572.0, '15:05', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.8), ('1A', 4, 1, 4, 3.4)]),

            ('20632', 'Thiruvananthapuram - Kasaragod Vande Bharat Express', 'TVC', 'KGQ', 'Mon,Tue,Wed,Fri,Sat,Sun', [
                ('TVC', 1, 0.0, '--:--', '16:05', 1),
                ('QLN', 2, 65.0, '16:53', '16:55', 1),
                ('ALLP', 3, 150.0, '17:55', '17:57', 1),
                ('ERN', 4, 207.0, '18:35', '18:38', 1),
                ('TCR', 5, 278.0, '19:40', '19:42', 1),
                ('SRR', 6, 311.0, '20:15', '20:17', 1),
                ('CLT', 7, 397.0, '21:14', '21:16', 1),
                ('CAN', 8, 486.0, '22:12', '22:14', 1),
                ('KGQ', 9, 572.0, '23:58', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.8), ('1A', 4, 1, 4, 3.4)]),

            # 7 & 8: Bengaluru - Dharwad Vande Bharat
            ('20661', 'Bengaluru - Dharwad Vande Bharat Express', 'SBC', 'DWR', 'Mon,Wed,Thu,Fri,Sat,Sun', [
                ('SBC', 1, 0.0, '--:--', '05:45', 1),
                ('YPR', 2, 6.0, '05:55', '05:57', 1),
                ('DVG', 3, 326.0, '09:15', '09:17', 1),
                ('UBL', 4, 470.0, '11:00', '11:05', 1),
                ('DWR', 5, 490.0, '11:35', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.8), ('1A', 4, 1, 4, 3.4)]),

            ('20662', 'Dharwad - Bengaluru Vande Bharat Express', 'DWR', 'SBC', 'Mon,Wed,Thu,Fri,Sat,Sun', [
                ('DWR', 1, 0.0, '--:--', '13:15', 1),
                ('UBL', 2, 20.0, '13:35', '13:40', 1),
                ('DVG', 3, 164.0, '14:58', '15:00', 1),
                ('YPR', 4, 484.0, '18:50', '18:52', 1),
                ('SBC', 5, 490.0, '19:10', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.8), ('1A', 4, 1, 4, 3.4)]),

            # 9 & 10: Secunderabad - Tirupati Vande Bharat
            ('20701', 'Secunderabad - Tirupati Vande Bharat Express', 'SC', 'TPTY', 'Mon,Wed,Thu,Fri,Sat,Sun', [
                ('SC', 1, 0.0, '--:--', '06:15', 1),
                ('GNT', 2, 281.0, '09:30', '09:35', 1),
                ('OGL', 3, 404.0, '11:00', '11:02', 1),
                ('NLR', 4, 521.0, '12:28', '12:30', 1),
                ('TPTY', 5, 661.0, '14:30', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.8), ('1A', 4, 1, 4, 3.4)]),

            ('20702', 'Tirupati - Secunderabad Vande Bharat Express', 'TPTY', 'SC', 'Mon,Wed,Thu,Fri,Sat,Sun', [
                ('TPTY', 1, 0.0, '--:--', '15:15', 1),
                ('NLR', 2, 140.0, '16:54', '16:55', 1),
                ('OGL', 3, 257.0, '18:08', '18:10', 1),
                ('GNT', 4, 380.0, '19:45', '19:50', 1),
                ('SC', 5, 661.0, '23:30', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.8), ('1A', 4, 1, 4, 3.4)]),

            # 11 & 12: Kovai Superfast Express (MAS - CBE)
            ('12675', 'Kovai Superfast Express', 'MAS', 'CBE', 'Daily', [
                ('MAS', 1, 0.0, '--:--', '06:10', 1),
                ('KPD', 2, 130.0, '07:53', '07:55', 1),
                ('SA', 3, 335.0, '10:52', '10:55', 1),
                ('ED', 4, 395.0, '11:50', '11:55', 1),
                ('TUP', 5, 445.0, '12:38', '12:40', 1),
                ('CBE', 6, 495.0, '14:05', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.5), ('2S', 10, 2, 10, 0.6)]),

            ('12676', 'Kovai Superfast Express Return', 'CBE', 'MAS', 'Daily', [
                ('CBE', 1, 0.0, '--:--', '15:15', 1),
                ('TUP', 2, 50.0, '15:53', '15:55', 1),
                ('ED', 3, 100.0, '16:40', '16:45', 1),
                ('SA', 4, 160.0, '17:37', '17:40', 1),
                ('KPD', 5, 365.0, '20:38', '20:40', 1),
                ('MAS', 6, 495.0, '22:50', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.5), ('2S', 10, 2, 10, 0.6)]),

            # 13 & 14: Vaigai Superfast Express (MS - MDU)
            ('12635', 'Vaigai Superfast Express', 'MS', 'MDU', 'Daily', [
                ('MS', 1, 0.0, '--:--', '13:50', 1),
                ('TBM', 2, 25.0, '14:18', '14:20', 1),
                ('CGL', 3, 56.0, '14:48', '14:50', 1),
                ('VM', 4, 159.0, '16:00', '16:05', 1),
                ('TPJ', 5, 336.0, '18:50', '18:55', 1),
                ('DG', 6, 431.0, '19:58', '20:00', 1),
                ('MDU', 7, 497.0, '21:30', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.5), ('2S', 10, 2, 10, 0.6)]),

            ('12636', 'Vaigai Superfast Express Return', 'MDU', 'MS', 'Daily', [
                ('MDU', 1, 0.0, '--:--', '07:10', 1),
                ('DG', 2, 66.0, '07:58', '08:00', 1),
                ('TPJ', 3, 161.0, '09:00', '09:05', 1),
                ('VM', 4, 338.0, '11:45', '11:50', 1),
                ('CGL', 5, 441.0, '13:08', '13:10', 1),
                ('TBM', 6, 472.0, '13:38', '13:40', 1),
                ('MS', 7, 497.0, '14:30', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.5), ('2S', 10, 2, 10, 0.6)]),

            # 15 & 16: Pandian Superfast Express (MS - MDU)
            ('12637', 'Pandian Superfast Express', 'MS', 'MDU', 'Daily', [
                ('MS', 1, 0.0, '--:--', '21:40', 1),
                ('TBM', 2, 25.0, '22:08', '22:10', 1),
                ('CGL', 3, 56.0, '22:38', '22:40', 1),
                ('VM', 4, 159.0, '00:05', '00:10', 2),
                ('TPJ', 5, 336.0, '02:45', '02:50', 2),
                ('DG', 6, 431.0, '04:02', '04:05', 2),
                ('MDU', 7, 497.0, '05:25', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            ('12638', 'Pandian Superfast Express Return', 'MDU', 'MS', 'Daily', [
                ('MDU', 1, 0.0, '--:--', '21:20', 1),
                ('DG', 2, 66.0, '22:08', '22:10', 1),
                ('TPJ', 3, 161.0, '23:25', '23:30', 1),
                ('VM', 4, 338.0, '02:08', '02:10', 2),
                ('CGL', 5, 441.0, '03:28', '03:30', 2),
                ('TBM', 6, 472.0, '04:08', '04:10', 2),
                ('MS', 7, 497.0, '05:10', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            # 17 & 18: Nilgiri Superfast Express (Blue Mountain) (MAS - MTP)
            ('12671', 'Nilgiri Superfast Express', 'MAS', 'MTP', 'Daily', [
                ('MAS', 1, 0.0, '--:--', '21:05', 1),
                ('KPD', 2, 130.0, '22:48', '22:50', 1),
                ('SA', 3, 335.0, '01:52', '01:55', 2),
                ('ED', 4, 395.0, '02:50', '02:55', 2),
                ('TUP', 5, 445.0, '03:43', '03:45', 2),
                ('CBE', 6, 495.0, '04:35', '04:40', 2),
                ('MTP', 7, 532.0, '06:15', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            ('12672', 'Nilgiri Superfast Express Return', 'MTP', 'MAS', 'Daily', [
                ('MTP', 1, 0.0, '--:--', '21:20', 1),
                ('CBE', 2, 37.0, '22:15', '22:20', 1),
                ('TUP', 3, 87.0, '23:03', '23:05', 1),
                ('ED', 4, 137.0, '23:55', '00:00', 2),
                ('SA', 5, 197.0, '00:52', '00:55', 2),
                ('KPD', 6, 402.0, '03:48', '03:50', 2),
                ('MAS', 7, 532.0, '06:25', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            # 19 & 20: Cheran Superfast Express (MAS - CBE)
            ('12673', 'Cheran Superfast Express', 'MAS', 'CBE', 'Daily', [
                ('MAS', 1, 0.0, '--:--', '22:00', 1),
                ('KPD', 2, 130.0, '23:43', '23:45', 1),
                ('JTJ', 3, 214.0, '00:58', '01:00', 2),
                ('SA', 4, 335.0, '02:37', '02:40', 2),
                ('ED', 5, 395.0, '03:40', '03:45', 2),
                ('TUP', 6, 445.0, '04:33', '04:35', 2),
                ('CBE', 7, 495.0, '06:00', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            ('12674', 'Cheran Superfast Express Return', 'CBE', 'MAS', 'Daily', [
                ('CBE', 1, 0.0, '--:--', '22:50', 1),
                ('TUP', 2, 50.0, '23:33', '23:35', 1),
                ('ED', 3, 100.0, '00:25', '00:30', 2),
                ('SA', 4, 160.0, '01:27', '01:30', 2),
                ('JTJ', 5, 281.0, '03:13', '03:15', 2),
                ('KPD', 6, 365.0, '04:23', '04:25', 2),
                ('MAS', 7, 495.0, '07:00', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            # 21 & 22: Pearl City Superfast Express (MS - TN)
            ('12693', 'Pearl City Superfast Express', 'MS', 'TN', 'Daily', [
                ('MS', 1, 0.0, '--:--', '19:30', 1),
                ('TBM', 2, 25.0, '19:58', '20:00', 1),
                ('VM', 3, 159.0, '22:15', '22:20', 1),
                ('TPJ', 4, 336.0, '01:00', '01:05', 2),
                ('DG', 5, 431.0, '02:12', '02:15', 2),
                ('MDU', 6, 497.0, '03:20', '03:25', 2),
                ('VPT', 7, 540.0, '04:08', '04:10', 2),
                ('CVP', 8, 588.0, '04:48', '04:50', 2),
                ('TN', 9, 656.0, '06:30', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            ('12694', 'Pearl City Superfast Express Return', 'TN', 'MS', 'Daily', [
                ('TN', 1, 0.0, '--:--', '20:20', 1),
                ('CVP', 2, 68.0, '21:18', '21:20', 1),
                ('VPT', 3, 116.0, '21:58', '22:00', 1),
                ('MDU', 4, 159.0, '23:00', '23:05', 1),
                ('DG', 5, 225.0, '00:12', '00:15', 2),
                ('TPJ', 6, 320.0, '01:30', '01:35', 2),
                ('VM', 7, 497.0, '04:25', '04:30', 2),
                ('TBM', 8, 631.0, '06:28', '06:30', 2),
                ('MS', 9, 656.0, '07:35', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            # 23 & 24: Nellai Superfast Express (MS - TEN)
            ('12631', 'Nellai Superfast Express', 'MS', 'TEN', 'Daily', [
                ('MS', 1, 0.0, '--:--', '20:10', 1),
                ('TBM', 2, 25.0, '20:38', '20:40', 1),
                ('CGL', 3, 56.0, '21:08', '21:10', 1),
                ('VM', 4, 159.0, '22:48', '22:50', 1),
                ('TPJ', 5, 336.0, '01:35', '01:40', 2),
                ('DG', 6, 431.0, '02:47', '02:50', 2),
                ('MDU', 7, 497.0, '03:55', '04:00', 2),
                ('VPT', 8, 540.0, '04:43', '04:45', 2),
                ('CVP', 9, 588.0, '05:23', '05:25', 2),
                ('TEN', 10, 653.0, '06:40', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            ('12632', 'Nellai Superfast Express Return', 'TEN', 'MS', 'Daily', [
                ('TEN', 1, 0.0, '--:--', '20:05', 1),
                ('CVP', 2, 65.0, '20:58', '21:00', 1),
                ('VPT', 3, 113.0, '21:38', '21:40', 1),
                ('MDU', 4, 156.0, '22:35', '22:40', 1),
                ('DG', 5, 222.0, '23:42', '23:45', 1),
                ('TPJ', 6, 317.0, '00:55', '01:00', 2),
                ('VM', 7, 494.0, '03:45', '03:50', 2),
                ('CGL', 8, 597.0, '05:08', '05:10', 2),
                ('TBM', 9, 628.0, '05:38', '05:40', 2),
                ('MS', 10, 653.0, '06:35', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            # 25 & 26: Rockfort Superfast Express (MS - TPJ)
            ('12653', 'Rockfort Superfast Express', 'MS', 'TPJ', 'Daily', [
                ('MS', 1, 0.0, '--:--', '23:35', 1),
                ('TBM', 2, 25.0, '00:03', '00:05', 2),
                ('CGL', 3, 56.0, '00:33', '00:35', 2),
                ('VM', 4, 159.0, '02:08', '02:10', 2),
                ('TPJ', 5, 336.0, '04:55', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            ('12654', 'Rockfort Superfast Express Return', 'TPJ', 'MS', 'Daily', [
                ('TPJ', 1, 0.0, '--:--', '22:50', 1),
                ('VM', 2, 177.0, '01:25', '01:30', 2),
                ('CGL', 3, 280.0, '02:48', '02:50', 2),
                ('TBM', 4, 311.0, '03:18', '03:20', 2),
                ('MS', 5, 336.0, '04:10', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            # 27 & 28: Chennai - Thiruvananthapuram Mail (MAS - TVC)
            ('12623', 'Chennai - Thiruvananthapuram Mail', 'MAS', 'TVC', 'Daily', [
                ('MAS', 1, 0.0, '--:--', '19:45', 1),
                ('KPD', 2, 130.0, '21:28', '21:30', 1),
                ('SA', 3, 335.0, '00:32', '00:35', 2),
                ('ED', 4, 395.0, '01:35', '01:40', 2),
                ('PGT', 5, 495.0, '03:52', '03:55', 2),
                ('TCR', 6, 570.0, '05:00', '05:03', 2),
                ('ERN', 7, 642.0, '06:20', '06:25', 2),
                ('KTYM', 8, 702.0, '07:32', '07:35', 2),
                ('QLN', 9, 798.0, '09:25', '09:30', 2),
                ('TVC', 10, 863.0, '11:45', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            ('12624', 'Thiruvananthapuram - Chennai Mail', 'TVC', 'MAS', 'Daily', [
                ('TVC', 1, 0.0, '--:--', '15:00', 1),
                ('QLN', 2, 65.0, '15:52', '15:55', 1),
                ('KTYM', 3, 161.0, '17:25', '17:28', 1),
                ('ERN', 4, 221.0, '18:40', '18:45', 1),
                ('TCR', 5, 293.0, '19:52', '19:55', 1),
                ('PGT', 6, 368.0, '21:12', '21:15', 1),
                ('ED', 7, 468.0, '23:30', '23:35', 1),
                ('SA', 8, 528.0, '00:27', '00:30', 2),
                ('KPD', 9, 733.0, '03:48', '03:50', 2),
                ('MAS', 10, 863.0, '07:45', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            # 29 & 30: Venad Express (SRR - TVC)
            ('16301', 'Venad Express', 'SRR', 'TVC', 'Daily', [
                ('SRR', 1, 0.0, '--:--', '14:35', 1),
                ('TCR', 2, 33.0, '15:11', '15:13', 1),
                ('ERN', 3, 105.0, '16:43', '16:45', 1),
                ('ALLP', 4, 162.0, '17:48', '17:50', 1),
                ('QLN', 5, 247.0, '19:35', '19:37', 1),
                ('TVC', 6, 312.0, '22:15', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.5), ('2S', 12, 3, 12, 0.6)]),

            ('16302', 'Venad Express Return', 'TVC', 'SRR', 'Daily', [
                ('TVC', 1, 0.0, '--:--', '05:25', 1),
                ('QLN', 2, 65.0, '06:30', '06:33', 1),
                ('ALLP', 3, 150.0, '07:58', '08:00', 1),
                ('ERN', 4, 207.0, '09:18', '09:20', 1),
                ('TCR', 5, 279.0, '10:53', '10:55', 1),
                ('SRR', 6, 312.0, '12:45', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.5), ('2S', 12, 3, 12, 0.6)]),

            # 31 & 32: Parasuram Express (MAQ - NCJ)
            ('16649', 'Parasuram Express', 'MAQ', 'NCJ', 'Daily', [
                ('MAQ', 1, 0.0, '--:--', '05:05', 1),
                ('CAN', 2, 132.0, '07:08', '07:10', 1),
                ('CLT', 3, 221.0, '08:37', '08:40', 1),
                ('SRR', 4, 307.0, '10:55', '11:00', 1),
                ('TCR', 5, 340.0, '11:40', '11:42', 1),
                ('ERN', 6, 412.0, '13:00', '13:05', 1),
                ('KTYM', 7, 472.0, '14:20', '14:23', 1),
                ('QLN', 8, 568.0, '16:42', '16:45', 1),
                ('TVC', 9, 633.0, '18:40', '18:45', 1),
                ('NCJ', 10, 704.0, '20:55', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.5), ('2S', 12, 3, 12, 0.6)]),

            ('16650', 'Parasuram Express Return', 'NCJ', 'MAQ', 'Daily', [
                ('NCJ', 1, 0.0, '--:--', '04:15', 1),
                ('TVC', 2, 71.0, '06:05', '06:10', 1),
                ('QLN', 3, 136.0, '07:22', '07:25', 1),
                ('KTYM', 4, 232.0, '09:20', '09:23', 1),
                ('ERN', 5, 292.0, '10:55', '11:00', 1),
                ('TCR', 6, 364.0, '12:15', '12:17', 1),
                ('SRR', 7, 397.0, '13:30', '13:35', 1),
                ('CLT', 8, 483.0, '14:57', '15:00', 1),
                ('CAN', 9, 572.0, '16:55', '17:00', 1),
                ('MAQ', 10, 704.0, '20:40', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.5), ('2S', 12, 3, 12, 0.6)]),

            # 33 & 34: Chennai - Bengaluru Intercity Express (MAS - SBC)
            ('12609', 'Chennai - Bengaluru Intercity Express', 'MAS', 'SBC', 'Daily', [
                ('MAS', 1, 0.0, '--:--', '13:35', 1),
                ('KPD', 2, 130.0, '15:18', '15:20', 1),
                ('JTJ', 3, 214.0, '16:38', '16:40', 1),
                ('BWT', 4, 289.0, '17:44', '17:45', 1),
                ('KJM', 5, 345.0, '18:56', '18:58', 1),
                ('BNC', 6, 355.0, '19:10', '19:12', 1),
                ('SBC', 7, 360.0, '19:45', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.5), ('2S', 12, 3, 12, 0.6)]),

            ('12610', 'Bengaluru - Chennai Intercity Express', 'SBC', 'MAS', 'Daily', [
                ('SBC', 1, 0.0, '--:--', '08:00', 1),
                ('BNC', 2, 5.0, '08:11', '08:12', 1),
                ('KJM', 3, 15.0, '08:24', '08:25', 1),
                ('BWT', 4, 71.0, '09:20', '09:21', 1),
                ('JTJ', 5, 146.0, '10:58', '11:00', 1),
                ('KPD', 6, 230.0, '12:08', '12:10', 1),
                ('MAS', 7, 360.0, '14:30', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.5), ('2S', 12, 3, 12, 0.6)]),

            # 35 & 36: Rani Chennamma Express (SBC - BGM)
            ('16589', 'Rani Chennamma Express', 'SBC', 'BGM', 'Daily', [
                ('SBC', 1, 0.0, '--:--', '23:00', 1),
                ('YPR', 2, 6.0, '23:11', '23:12', 1),
                ('ASK', 3, 166.0, '01:50', '01:53', 2),
                ('DVG', 4, 326.0, '03:58', '04:00', 2),
                ('UBL', 5, 470.0, '06:00', '06:10', 2),
                ('DWR', 6, 490.0, '06:33', '06:35', 2),
                ('BGM', 7, 612.0, '08:30', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            ('16590', 'Rani Chennamma Express Return', 'BGM', 'SBC', 'Daily', [
                ('BGM', 1, 0.0, '--:--', '18:50', 1),
                ('DWR', 2, 122.0, '20:53', '20:55', 1),
                ('UBL', 3, 142.0, '21:30', '21:40', 1),
                ('DVG', 4, 286.0, '23:33', '23:35', 1),
                ('ASK', 5, 446.0, '01:45', '01:48', 2),
                ('YPR', 6, 606.0, '05:40', '05:42', 2),
                ('SBC', 7, 612.0, '06:15', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            # 37 & 38: Panchaganga Express (SBC - KAWR)
            ('16595', 'Panchaganga Express', 'SBC', 'KAWR', 'Daily', [
                ('SBC', 1, 0.0, '--:--', '18:50', 1),
                ('YPR', 2, 6.0, '19:01', '19:02', 1),
                ('HAS', 3, 192.0, '22:15', '22:20', 1),
                ('MAJN', 4, 351.0, '03:15', '03:20', 2),
                ('UD', 5, 413.0, '04:30', '04:32', 2),
                ('KUDA', 6, 445.0, '05:00', '05:02', 2),
                ('BYNR', 7, 479.0, '05:32', '05:34', 2),
                ('KT', 8, 549.0, '06:36', '06:38', 2),
                ('KAWR', 9, 609.0, '08:25', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            ('16596', 'Panchaganga Express Return', 'KAWR', 'SBC', 'Daily', [
                ('KAWR', 1, 0.0, '--:--', '18:00', 1),
                ('KT', 2, 60.0, '18:48', '18:50', 1),
                ('BYNR', 3, 130.0, '19:50', '19:52', 1),
                ('KUDA', 4, 164.0, '20:18', '20:20', 1),
                ('UD', 5, 196.0, '20:50', '20:52', 1),
                ('MAJN', 6, 258.0, '22:30', '22:35', 1),
                ('HAS', 7, 417.0, '03:20', '03:25', 2),
                ('YPR', 8, 603.0, '06:43', '06:45', 2),
                ('SBC', 9, 609.0, '07:15', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            # 39 & 40: Godavari Superfast Express (HYB - VSKP)
            ('12727', 'Godavari Superfast Express', 'HYB', 'VSKP', 'Daily', [
                ('HYB', 1, 0.0, '--:--', '17:05', 1),
                ('SC', 2, 10.0, '17:25', '17:30', 1),
                ('KZJ', 3, 142.0, '19:28', '19:30', 1),
                ('WL', 4, 152.0, '19:43', '19:45', 1),
                ('KMT', 5, 260.0, '21:09', '21:10', 1),
                ('BZA', 6, 359.0, '23:05', '23:20', 1),
                ('EE', 7, 418.0, '00:13', '00:15', 2),
                ('RJY', 8, 508.0, '01:38', '01:40', 2),
                ('SLO', 9, 558.0, '02:28', '02:30', 2),
                ('AKP', 10, 672.0, '04:03', '04:05', 2),
                ('VSKP', 11, 710.0, '05:25', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            ('12728', 'Godavari Superfast Express Return', 'VSKP', 'HYB', 'Daily', [
                ('VSKP', 1, 0.0, '--:--', '17:20', 1),
                ('AKP', 2, 38.0, '17:58', '18:00', 1),
                ('SLO', 3, 152.0, '19:28', '19:30', 1),
                ('RJY', 4, 202.0, '20:18', '20:20', 1),
                ('EE', 5, 292.0, '21:38', '21:40', 1),
                ('BZA', 6, 351.0, '23:00', '23:15', 1),
                ('KMT', 7, 450.0, '00:44', '00:45', 2),
                ('WL', 8, 558.0, '02:08', '02:10', 2),
                ('KZJ', 9, 568.0, '02:28', '02:30', 2),
                ('SC', 10, 700.0, '05:10', '05:15', 2),
                ('HYB', 11, 710.0, '06:15', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            # 41 & 42: Charminar Express (HYB - TBM)
            ('12759', 'Charminar Express', 'HYB', 'TBM', 'Daily', [
                ('HYB', 1, 0.0, '--:--', '18:00', 1),
                ('SC', 2, 10.0, '18:20', '18:25', 1),
                ('KZJ', 3, 142.0, '20:18', '20:20', 1),
                ('WL', 4, 152.0, '20:33', '20:35', 1),
                ('KMT', 5, 260.0, '21:58', '22:00', 1),
                ('BZA', 6, 359.0, '00:05', '00:15', 2),
                ('TEL', 7, 390.0, '00:48', '00:50', 2),
                ('OGL', 8, 497.0, '02:08', '02:10', 2),
                ('NLR', 9, 614.0, '03:33', '03:35', 2),
                ('GDR', 10, 652.0, '04:38', '04:40', 2),
                ('MS', 11, 794.0, '07:05', '07:10', 2),
                ('TBM', 12, 819.0, '08:00', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            ('12760', 'Charminar Express Return', 'TBM', 'HYB', 'Daily', [
                ('TBM', 1, 0.0, '--:--', '17:30', 1),
                ('MS', 2, 25.0, '18:00', '18:05', 1),
                ('GDR', 3, 167.0, '20:53', '20:55', 1),
                ('NLR', 4, 205.0, '21:28', '21:30', 1),
                ('OGL', 5, 322.0, '22:58', '23:00', 1),
                ('TEL', 6, 429.0, '00:33', '00:35', 2),
                ('BZA', 7, 460.0, '01:25', '01:35', 2),
                ('KMT', 8, 559.0, '03:03', '03:05', 2),
                ('WL', 9, 667.0, '04:38', '04:40', 2),
                ('KZJ', 10, 677.0, '04:58', '05:00', 2),
                ('SC', 11, 809.0, '07:20', '07:25', 2),
                ('HYB', 12, 819.0, '08:00', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            # 43 & 44: Chennai - Mangaluru Superfast Express (MAS - MAQ)
            ('12685', 'Chennai - Mangaluru Superfast Express', 'MAS', 'MAQ', 'Daily', [
                ('MAS', 1, 0.0, '--:--', '17:00', 1),
                ('KPD', 2, 130.0, '18:38', '18:40', 1),
                ('SA', 3, 335.0, '21:32', '21:35', 1),
                ('ED', 4, 395.0, '22:30', '22:35', 1),
                ('PGT', 5, 495.0, '00:47', '00:50', 2),
                ('SRR', 6, 539.0, '01:40', '01:45', 2),
                ('TIR', 7, 584.0, '02:24', '02:25', 2),
                ('CLT', 8, 625.0, '03:07', '03:10', 2),
                ('BDJ', 9, 672.0, '03:49', '03:50', 2),
                ('TLY', 10, 694.0, '04:09', '04:10', 2),
                ('CAN', 11, 715.0, '04:37', '04:40', 2),
                ('PAY', 12, 748.0, '05:09', '05:10', 2),
                ('KGQ', 13, 800.0, '05:54', '05:55', 2),
                ('MAQ', 14, 847.0, '07:20', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            ('12686', 'Mangaluru - Chennai Superfast Express', 'MAQ', 'MAS', 'Daily', [
                ('MAQ', 1, 0.0, '--:--', '16:55', 1),
                ('KGQ', 2, 47.0, '17:34', '17:35', 1),
                ('PAY', 3, 99.0, '18:14', '18:15', 1),
                ('CAN', 4, 132.0, '18:57', '19:00', 1),
                ('TLY', 5, 153.0, '19:19', '19:20', 1),
                ('BDJ', 6, 175.0, '19:39', '19:40', 1),
                ('CLT', 7, 222.0, '20:27', '20:30', 1),
                ('TIR', 8, 263.0, '21:09', '21:10', 1),
                ('SRR', 9, 308.0, '22:15', '22:20', 1),
                ('PGT', 10, 352.0, '23:17', '23:20', 1),
                ('ED', 11, 452.0, '01:40', '01:45', 2),
                ('SA', 12, 512.0, '02:37', '02:40', 2),
                ('KPD', 13, 717.0, '05:33', '05:35', 2),
                ('MAS', 14, 847.0, '08:05', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            # 45 & 46: Guruvayur Express (MS - GUV via TVC)
            ('16127', 'Guruvayur Express', 'MS', 'GUV', 'Daily', [
                ('MS', 1, 0.0, '--:--', '09:45', 1),
                ('TBM', 2, 25.0, '10:13', '10:15', 1),
                ('VM', 3, 159.0, '12:15', '12:20', 1),
                ('TPJ', 4, 336.0, '14:50', '14:55', 1),
                ('DG', 5, 431.0, '16:02', '16:05', 1),
                ('MDU', 6, 497.0, '17:25', '17:30', 1),
                ('VPT', 7, 540.0, '18:13', '18:15', 1),
                ('TEN', 8, 653.0, '20:40', '20:45', 1),
                ('NCJ', 9, 726.0, '22:15', '22:20', 1),
                ('TVC', 10, 797.0, '23:55', '00:05', 2),
                ('QLN', 11, 862.0, '01:10', '01:15', 2),
                ('ALLP', 12, 947.0, '02:22', '02:25', 2),
                ('ERS', 13, 1004.0, '03:45', '03:50', 2),
                ('TCR', 14, 1078.0, '05:15', '05:18', 2),
                ('GUV', 15, 1101.0, '06:40', '--:--', 2),
            ], [('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0), ('2S', 12, 3, 12, 0.6)]),

            ('16128', 'Guruvayur Express Return', 'GUV', 'MS', 'Daily', [
                ('GUV', 1, 0.0, '--:--', '23:15', 1),
                ('TCR', 2, 23.0, '23:40', '23:43', 1),
                ('ERS', 3, 97.0, '01:15', '01:20', 2),
                ('ALLP', 4, 154.0, '02:17', '02:20', 2),
                ('QLN', 5, 239.0, '03:32', '03:35', 2),
                ('TVC', 6, 304.0, '05:10', '05:15', 2),
                ('NCJ', 7, 375.0, '06:50', '06:55', 2),
                ('TEN', 8, 448.0, '08:35', '08:40', 2),
                ('VPT', 9, 561.0, '10:08', '10:10', 2),
                ('MDU', 10, 604.0, '11:15', '11:20', 2),
                ('DG', 11, 670.0, '12:17', '12:20', 2),
                ('TPJ', 12, 765.0, '13:40', '13:45', 2),
                ('VM', 13, 942.0, '16:55', '17:00', 2),
                ('TBM', 14, 1076.0, '19:28', '19:30', 2),
                ('MS', 15, 1101.0, '20:35', '--:--', 2),
            ], [('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0), ('2S', 12, 3, 12, 0.6)]),

            # 47 & 48: Padmavati Superfast Express (TPTY - SC)
            ('12763', 'Padmavati Superfast Express', 'TPTY', 'SC', 'Daily', [
                ('TPTY', 1, 0.0, '--:--', '16:55', 1),
                ('RU', 2, 10.0, '17:15', '17:17', 1),
                ('GTL', 3, 312.0, '22:10', '22:15', 1),
                ('KRNT', 4, 434.0, '00:18', '00:20', 2),
                ('MBNR', 5, 565.0, '02:08', '02:10', 2),
                ('KCG', 6, 671.0, '04:58', '05:00', 2),
                ('SC', 7, 678.0, '05:55', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            ('12764', 'Padmavati Superfast Express Return', 'SC', 'TPTY', 'Daily', [
                ('SC', 1, 0.0, '--:--', '18:40', 1),
                ('KCG', 2, 7.0, '18:55', '18:57', 1),
                ('MBNR', 3, 113.0, '20:28', '20:30', 1),
                ('KRNT', 4, 244.0, '22:48', '22:50', 1),
                ('GTL', 5, 366.0, '01:05', '01:10', 2),
                ('RU', 6, 668.0, '06:08', '06:10', 2),
                ('TPTY', 7, 678.0, '06:55', '--:--', 2),
            ], [('1A', 4, 1, 4, 3.5), ('2A', 6, 2, 6, 2.5), ('3A', 8, 2, 8, 1.8), ('SL', 12, 3, 12, 1.0)]),

            # 49 & 50: Chennai - Mysuru Shatabdi Express (MAS - MYS)
            ('12007', 'Chennai - Mysuru Shatabdi Express', 'MAS', 'MYS', 'Mon,Tue,Wed,Fri,Sat,Sun', [
                ('MAS', 1, 0.0, '--:--', '06:00', 1),
                ('KPD', 2, 130.0, '07:38', '07:40', 1),
                ('SBC', 3, 360.0, '10:55', '11:00', 1),
                ('MYS', 4, 500.0, '13:00', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.8), ('1A', 4, 1, 4, 3.5)]),

            ('12008', 'Mysuru - Chennai Shatabdi Express', 'MYS', 'MAS', 'Mon,Tue,Wed,Fri,Sat,Sun', [
                ('MYS', 1, 0.0, '--:--', '14:15', 1),
                ('SBC', 2, 140.0, '16:15', '16:20', 1),
                ('KPD', 3, 370.0, '19:33', '19:35', 1),
                ('MAS', 4, 500.0, '21:30', '--:--', 1),
            ], [('CC', 8, 2, 8, 1.8), ('1A', 4, 1, 4, 3.5)]),
        ]

        route_objs = []
        quota_objs = []

        for t_num, t_name, src, dst, days, routes, quotas in trains_def:
            src_st = st_map.get(src)
            dst_st = st_map.get(dst)
            if not src_st or not dst_st:
                continue

            tr = Train.query.filter_by(train_number=t_num).first()
            if not tr:
                tr = Train(
                    train_number=t_num,
                    name=t_name,
                    source_station_id=src_st.id,
                    destination_station_id=dst_st.id,
                    operating_days=days,
                    is_active=True
                )
                db.session.add(tr)
                db.session.flush()

                for st_code, stop_num, dist, arr, dep, day_num in routes:
                    st = st_map.get(st_code)
                    if st:
                        route_objs.append(RouteStation(
                            train_id=tr.id,
                            station_id=st.id,
                            stop_number=stop_num,
                            distance_km=dist,
                            arrival_time=arr,
                            departure_time=dep,
                            day_number=day_num
                        ))

                for travel_class, total_cnf, total_rac, total_wl, base_fare in quotas:
                    quota_objs.append(CoachQuotaConfig(
                        train_id=tr.id,
                        travel_class=travel_class,
                        total_cnf_seats=total_cnf,
                        total_rac_seats=total_rac,
                        total_wl_seats=total_wl,
                        base_fare_per_km=base_fare
                    ))

        if route_objs:
            db.session.add_all(route_objs)
        if quota_objs:
            db.session.add_all(quota_objs)
        db.session.commit()
        print(f"--> Successfully seeded {len(trains_def)} trains, {len(route_objs)} route stations, and {len(quota_objs)} coach configurations.")

        # 5. Requirement 3 & 4: Maximum Booking Data for next 2 weeks with WAITING LIST (WL)
        print("--> Requirement 3 & 4: Seeding bookings for next 2 weeks (spilling into Waiting List)...")

        train_by_num = {t.train_number: t for t in Train.query.all()}
        user_list = [u for u in users if u.role == 'user']
        
        passenger_names = [
            ('Ramesh Kumar', 34, 'Male', 'Lower'),
            ('Sita Raman', 29, 'Female', 'Upper'),
            ('Venkatesan G', 62, 'Male', 'Lower'),
            ('Subhashree V', 58, 'Female', 'Lower'),
            ('Ganesh Babu', 41, 'Male', 'Middle'),
            ('Meena Kumari', 38, 'Female', 'Side Lower'),
            ('Arunachalam S', 27, 'Male', 'Side Upper'),
            ('Deepika Rajan', 25, 'Female', 'Window'),
            ('Muruganathan P', 52, 'Male', 'Lower'),
            ('Kavitha Murugan', 48, 'Female', 'Middle'),
            ('Harish Kalyan', 23, 'Male', 'Upper'),
            ('Swathi Menon', 31, 'Female', 'Side Lower'),
            ('Praveen Kumar', 36, 'Male', 'Lower'),
            ('Revathi Praveen', 32, 'Female', 'Upper'),
            ('Sridharan K', 68, 'Male', 'Lower'),
            ('Janaki Sridhar', 64, 'Female', 'Lower'),
        ]

        def get_berth_type(t_class, seat_no):
            if t_class in ['SL', '3A']:
                types = ['Lower', 'Middle', 'Upper', 'Lower', 'Middle', 'Upper', 'Side Lower', 'Side Upper']
                return types[(seat_no - 1) % 8]
            elif t_class == '2A':
                types = ['Lower', 'Upper', 'Lower', 'Upper', 'Side Lower', 'Side Upper']
                return types[(seat_no - 1) % 6]
            elif t_class in ['CC', '2S']:
                types = ['Window', 'Middle', 'Aisle', 'Aisle', 'Window']
                return types[(seat_no - 1) % 5]
            elif t_class == '1A':
                return 'Cabin' if seat_no % 2 == 1 else 'Coupe'
            return 'Lower'

        def get_coach_prefix(t_class):
            prefixes = {'1A': 'H', '2A': 'A', '3A': 'B', 'SL': 'S', 'CC': 'C', '2S': 'D'}
            return prefixes.get(t_class, 'S')

        if Booking.query.first() is not None:
            print("--> Bookings already exist in database. Skipping redundant booking generation.")
            return True

        # Select 12 trunk line popular trains for extensive 2-week waitlist bookings
        focus_trains = [
            '12637', '12638', '12675', '12676', '12673', '12671',
            '12693', '12631', '12623', '12685', '16595', '12727'
        ]

        total_booked_pax = 0
        total_wl_pax = 0
        total_rac_pax = 0
        total_cnf_pax = 0
        booking_counter = 4210000000

        # Loop through all 14 upcoming journey dates
        for day_offset in range(1, 15):
            journey_date = date.today() + timedelta(days=day_offset)
            # Timestamp strictly between 1 and 3 days ago (< 5 days, so NEVER purged by 5-day deletion)
            days_ago = min(3, max(1, (14 - day_offset) // 4 + 1))
            booking_time = datetime.combine(date.today() - timedelta(days=days_ago), time(random.randint(9, 18), random.randint(10, 50)))

            day_bookings = []
            day_passengers = []

            for t_num in focus_trains:
                tr = train_by_num.get(t_num)
                if not tr:
                    continue

                routes = sorted(tr.routes, key=lambda r: r.stop_number)
                src_r = routes[0]
                dst_r = routes[-1]
                distance = dst_r.distance_km - src_r.distance_km

                for cfg in tr.configs:
                    t_class = cfg.travel_class
                    total_cnf = cfg.total_cnf_seats
                    total_rac = cfg.total_rac_seats
                    total_wl = cfg.total_wl_seats

                    # 30% Tatkal Reservation (Requirement 4)
                    tatkal_cnf_seats = max(1, round(total_cnf * 0.30))
                    general_cnf_seats = max(0, total_cnf - tatkal_cnf_seats)

                    # Number of General quota passengers to book:
                    # Fill all general CNF + all RAC + 2 to 4 Waiting List (WL) passengers!
                    wl_count_target = 3
                    gn_total_pax = general_cnf_seats + total_rac + wl_count_target

                    # Create bookings for this train class:
                    # Booking 1: Confirmed group
                    # Booking 2: RAC group
                    # Booking 3 & 4: Waiting List (WL 1, WL 2, WL 3)
                    pax_allocated = 0
                    gn_cnf_count = 0
                    gn_rac_count = 0
                    gn_wl_count = 0

                    while pax_allocated < gn_total_pax:
                        chunk_size = min(2, gn_total_pax - pax_allocated)
                        booking_counter += 1
                        pnr_str = str(booking_counter)
                        assigned_user = random.choice(user_list)

                        fare_per_pax = round(max(60.0, distance * cfg.base_fare_per_km), 2)
                        b_fare = round(fare_per_pax * chunk_size, 2)

                        b_obj = Booking(
                            user_id=assigned_user.id,
                            train_id=tr.id,
                            from_station_id=src_r.station_id,
                            to_station_id=dst_r.station_id,
                            journey_date=journey_date,
                            travel_class=t_class,
                            quota='GN',
                            pnr=pnr_str,
                            booking_time=booking_time,
                            total_fare=b_fare,
                            status='CONFIRMED',
                            is_archived=False,
                            chart_prepared=False
                        )
                        db.session.add(b_obj)
                        db.session.flush()

                        for _ in range(chunk_size):
                            pname, page, pgen, ppref = passenger_names[(pax_allocated) % len(passenger_names)]
                            pax_allocated += 1
                            total_booked_pax += 1

                            if gn_cnf_count < general_cnf_seats:
                                gn_cnf_count += 1
                                total_cnf_pax += 1
                                seat_no = gn_cnf_count
                                coach_no = f"{get_coach_prefix(t_class)}1"
                                b_status = 'CNF'
                                cur_status = 'CNF'
                                berth_t = get_berth_type(t_class, seat_no)
                                rac_wl_num = None
                            elif gn_rac_count < total_rac:
                                gn_rac_count += 1
                                total_rac_pax += 1
                                seat_no = (gn_rac_count + 1) // 2
                                coach_no = 'RAC'
                                b_status = f"RAC {gn_rac_count}"
                                cur_status = 'RAC'
                                berth_t = 'Side Lower (Shared)'
                                rac_wl_num = gn_rac_count
                            else:
                                gn_wl_count += 1
                                total_wl_pax += 1
                                seat_no = None
                                coach_no = 'WL'
                                b_status = f"WL {gn_wl_count}"
                                cur_status = 'WL'
                                berth_t = 'No Berth Allocated'
                                rac_wl_num = gn_wl_count

                            pass_obj = Passenger(
                                booking_id=b_obj.id,
                                name=pname,
                                age=page,
                                gender=pgen,
                                berth_preference=ppref,
                                booking_status=b_status,
                                current_status=cur_status,
                                coach_no=coach_no,
                                seat_no=seat_no,
                                berth_type=berth_t,
                                rac_wl_number=rac_wl_num,
                                is_cancelled=False
                            )
                            db.session.add(pass_obj)

            db.session.commit()
            print(f"    Committed Day +{day_offset} ({journey_date}).")

        print("--> Complete 2-Week Seeding Finished Successfully!")
        print(f"--> Total Passengers: {total_booked_pax} | CNF: {total_cnf_pax} | RAC: {total_rac_pax} | WAITING LIST (WL): {total_wl_pax}")

if __name__ == '__main__':
    build_data()
