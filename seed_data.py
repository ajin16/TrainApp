from datetime import date, datetime, timedelta
from app import create_app
from models import db, User, Station, Train, RouteStation, CoachQuotaConfig, Booking, Passenger
from services.booking_service import book_ticket

def seed():
    app = create_app()
    with app.app_context():
        # Clear existing tables
        db.drop_all()
        db.create_all()

        print("--> Seeding Users...")
        admin = User(username='admin', email='admin@irctc.gov.in', full_name='IRCTC Chief Administrator', role='admin')
        admin.set_password('admin123')

        passenger1 = User(username='passenger', email='user@gmail.com', full_name='Rahul Sharma', phone='9876543210', role='user')
        passenger1.set_password('user123')

        passenger2 = User(username='priya', email='priya@gmail.com', full_name='Priya Verma', phone='9876500112', role='user')
        passenger2.set_password('user123')

        passenger3 = User(username='amit', email='amit@gmail.com', full_name='Amitabh Kumar', phone='9812345678', role='user')
        passenger3.set_password('user123')

        db.session.add_all([admin, passenger1, passenger2, passenger3])
        db.session.commit()

        print("--> Seeding 16 Real-World Indian Railway Stations...")
        stations_data = [
            {'code': 'NDLS', 'name': 'New Delhi', 'city': 'New Delhi', 'state': 'Delhi'},
            {'code': 'MMCT', 'name': 'Mumbai Central', 'city': 'Mumbai', 'state': 'Maharashtra'},
            {'code': 'CSMT', 'name': 'Mumbai CSMT', 'city': 'Mumbai', 'state': 'Maharashtra'},
            {'code': 'HWH', 'name': 'Howrah Junction', 'city': 'Kolkata', 'state': 'West Bengal'},
            {'code': 'SDAH', 'name': 'Sealdah', 'city': 'Kolkata', 'state': 'West Bengal'},
            {'code': 'MAS', 'name': 'Chennai Central', 'city': 'Chennai', 'state': 'Tamil Nadu'},
            {'code': 'SBC', 'name': 'KSR Bengaluru', 'city': 'Bengaluru', 'state': 'Karnataka'},
            {'code': 'ADI', 'name': 'Ahmedabad Junction', 'city': 'Ahmedabad', 'state': 'Gujarat'},
            {'code': 'JP', 'name': 'Jaipur Junction', 'city': 'Jaipur', 'state': 'Rajasthan'},
            {'code': 'PNBE', 'name': 'Patna Junction', 'city': 'Patna', 'state': 'Bihar'},
            {'code': 'CNB', 'name': 'Kanpur Central', 'city': 'Kanpur', 'state': 'Uttar Pradesh'},
            {'code': 'AGC', 'name': 'Agra Cantt', 'city': 'Agra', 'state': 'Uttar Pradesh'},
            {'code': 'ST', 'name': 'Surat', 'city': 'Surat', 'state': 'Gujarat'},
            {'code': 'BRC', 'name': 'Vadodara Junction', 'city': 'Vadodara', 'state': 'Gujarat'},
            {'code': 'BSB', 'name': 'Varanasi Junction', 'city': 'Varanasi', 'state': 'Uttar Pradesh'},
            {'code': 'BPL', 'name': 'Rani Kamlapati (Bhopal)', 'city': 'Bhopal', 'state': 'Madhya Pradesh'}
        ]

        station_objs = {}
        for s in stations_data:
            st = Station(code=s['code'], name=s['name'], city=s['city'], state=s['state'])
            db.session.add(st)
            station_objs[s['code']] = st

        db.session.commit()

        print("--> Seeding 10 Real-World Trains & Routes...")

        # 1. Mumbai Rajdhani Express (12952)
        rajdhani = Train(train_number='12952', name='Mumbai Rajdhani Express', source_station_id=station_objs['NDLS'].id, destination_station_id=station_objs['MMCT'].id, operating_days='Daily', is_active=True)
        db.session.add(rajdhani); db.session.flush()
        db.session.add_all([
            RouteStation(train_id=rajdhani.id, station_id=station_objs['NDLS'].id, stop_number=1, distance_km=0.0, departure_time='16:55', day_number=1),
            RouteStation(train_id=rajdhani.id, station_id=station_objs['AGC'].id, stop_number=2, distance_km=195.0, arrival_time='18:45', departure_time='18:47', day_number=1),
            RouteStation(train_id=rajdhani.id, station_id=station_objs['CNB'].id, stop_number=3, distance_km=440.0, arrival_time='21:30', departure_time='21:35', day_number=1),
            RouteStation(train_id=rajdhani.id, station_id=station_objs['BRC'].id, stop_number=4, distance_km=992.0, arrival_time='04:20', departure_time='04:30', day_number=2),
            RouteStation(train_id=rajdhani.id, station_id=station_objs['ST'].id, stop_number=5, distance_km=1122.0, arrival_time='05:50', departure_time='05:55', day_number=2),
            RouteStation(train_id=rajdhani.id, station_id=station_objs['MMCT'].id, stop_number=6, distance_km=1384.0, arrival_time='08:35', departure_time='--:--', day_number=2),
        ])
        db.session.add_all([
            CoachQuotaConfig(train_id=rajdhani.id, travel_class='1A', total_cnf_seats=4, total_rac_seats=2, total_wl_seats=2, base_fare_per_km=3.5),
            CoachQuotaConfig(train_id=rajdhani.id, travel_class='2A', total_cnf_seats=4, total_rac_seats=2, total_wl_seats=2, base_fare_per_km=2.5),
            CoachQuotaConfig(train_id=rajdhani.id, travel_class='3A', total_cnf_seats=3, total_rac_seats=2, total_wl_seats=2, base_fare_per_km=1.8),
        ])

        # 2. Vande Bharat Express (22436)
        vande = Train(train_number='22436', name='Vande Bharat Express', source_station_id=station_objs['NDLS'].id, destination_station_id=station_objs['HWH'].id, operating_days='Mon,Wed,Thu,Fri,Sat,Sun', is_active=True)
        db.session.add(vande); db.session.flush()
        db.session.add_all([
            RouteStation(train_id=vande.id, station_id=station_objs['NDLS'].id, stop_number=1, distance_km=0.0, departure_time='06:00', day_number=1),
            RouteStation(train_id=vande.id, station_id=station_objs['CNB'].id, stop_number=2, distance_km=440.0, arrival_time='09:30', departure_time='09:35', day_number=1),
            RouteStation(train_id=vande.id, station_id=station_objs['BSB'].id, stop_number=3, distance_km=755.0, arrival_time='12:30', departure_time='12:35', day_number=1),
            RouteStation(train_id=vande.id, station_id=station_objs['PNBE'].id, stop_number=4, distance_km=998.0, arrival_time='14:15', departure_time='14:20', day_number=1),
            RouteStation(train_id=vande.id, station_id=station_objs['HWH'].id, stop_number=5, distance_km=1530.0, arrival_time='19:30', departure_time='--:--', day_number=1),
        ])
        db.session.add_all([
            CoachQuotaConfig(train_id=vande.id, travel_class='CC', total_cnf_seats=5, total_rac_seats=2, total_wl_seats=2, base_fare_per_km=1.6),
            CoachQuotaConfig(train_id=vande.id, travel_class='1A', total_cnf_seats=3, total_rac_seats=1, total_wl_seats=1, base_fare_per_km=3.2),
        ])

        # 3. Howrah Rajdhani Express (12301)
        hwh_raj = Train(train_number='12301', name='Howrah Rajdhani Express', source_station_id=station_objs['HWH'].id, destination_station_id=station_objs['NDLS'].id, operating_days='Daily', is_active=True)
        db.session.add(hwh_raj); db.session.flush()
        db.session.add_all([
            RouteStation(train_id=hwh_raj.id, station_id=station_objs['HWH'].id, stop_number=1, distance_km=0.0, departure_time='16:50', day_number=1),
            RouteStation(train_id=hwh_raj.id, station_id=station_objs['PNBE'].id, stop_number=2, distance_km=532.0, arrival_time='22:40', departure_time='22:50', day_number=1),
            RouteStation(train_id=hwh_raj.id, station_id=station_objs['CNB'].id, stop_number=3, distance_km=1090.0, arrival_time='04:45', departure_time='04:50', day_number=2),
            RouteStation(train_id=hwh_raj.id, station_id=station_objs['NDLS'].id, stop_number=4, distance_km=1530.0, arrival_time='10:05', departure_time='--:--', day_number=2),
        ])
        db.session.add_all([
            CoachQuotaConfig(train_id=hwh_raj.id, travel_class='1A', total_cnf_seats=4, total_rac_seats=2, total_wl_seats=2, base_fare_per_km=3.5),
            CoachQuotaConfig(train_id=hwh_raj.id, travel_class='2A', total_cnf_seats=4, total_rac_seats=2, total_wl_seats=2, base_fare_per_km=2.5),
            CoachQuotaConfig(train_id=hwh_raj.id, travel_class='3A', total_cnf_seats=4, total_rac_seats=2, total_wl_seats=2, base_fare_per_km=1.8),
        ])

        # 4. Rani Kamlapati (Bhopal) Shatabdi (12002)
        shatabdi = Train(train_number='12002', name='Bhopal Shatabdi Express', source_station_id=station_objs['NDLS'].id, destination_station_id=station_objs['BPL'].id, operating_days='Daily', is_active=True)
        db.session.add(shatabdi); db.session.flush()
        db.session.add_all([
            RouteStation(train_id=shatabdi.id, station_id=station_objs['NDLS'].id, stop_number=1, distance_km=0.0, departure_time='06:00', day_number=1),
            RouteStation(train_id=shatabdi.id, station_id=station_objs['AGC'].id, stop_number=2, distance_km=195.0, arrival_time='07:50', departure_time='07:55', day_number=1),
            RouteStation(train_id=shatabdi.id, station_id=station_objs['BPL'].id, stop_number=3, distance_km=707.0, arrival_time='14:05', departure_time='--:--', day_number=1),
        ])
        db.session.add_all([
            CoachQuotaConfig(train_id=shatabdi.id, travel_class='CC', total_cnf_seats=6, total_rac_seats=2, total_wl_seats=2, base_fare_per_km=1.5),
            CoachQuotaConfig(train_id=shatabdi.id, travel_class='1A', total_cnf_seats=3, total_rac_seats=1, total_wl_seats=1, base_fare_per_km=3.0),
        ])

        # 5. Kerala Superfast Express (12626)
        kerala = Train(train_number='12626', name='Kerala Superfast Express', source_station_id=station_objs['NDLS'].id, destination_station_id=station_objs['MAS'].id, operating_days='Daily', is_active=True)
        db.session.add(kerala); db.session.flush()
        db.session.add_all([
            RouteStation(train_id=kerala.id, station_id=station_objs['NDLS'].id, stop_number=1, distance_km=0.0, departure_time='20:10', day_number=1),
            RouteStation(train_id=kerala.id, station_id=station_objs['AGC'].id, stop_number=2, distance_km=195.0, arrival_time='22:20', departure_time='22:25', day_number=1),
            RouteStation(train_id=kerala.id, station_id=station_objs['BPL'].id, stop_number=3, distance_km=707.0, arrival_time='05:10', departure_time='05:15', day_number=2),
            RouteStation(train_id=kerala.id, station_id=station_objs['SBC'].id, stop_number=4, distance_km=2060.0, arrival_time='04:30', departure_time='04:45', day_number=3),
            RouteStation(train_id=kerala.id, station_id=station_objs['MAS'].id, stop_number=5, distance_km=2180.0, arrival_time='07:15', departure_time='--:--', day_number=3),
        ])
        db.session.add_all([
            CoachQuotaConfig(train_id=kerala.id, travel_class='SL', total_cnf_seats=4, total_rac_seats=2, total_wl_seats=2, base_fare_per_km=1.0),
            CoachQuotaConfig(train_id=kerala.id, travel_class='3A', total_cnf_seats=3, total_rac_seats=2, total_wl_seats=2, base_fare_per_km=1.8),
        ])

        # 6. Sealdah Duronto Express (12260)
        duronto = Train(train_number='12260', name='Sealdah Duronto Express', source_station_id=station_objs['NDLS'].id, destination_station_id=station_objs['SDAH'].id, operating_days='Tue,Fri', is_active=True)
        db.session.add(duronto); db.session.flush()
        db.session.add_all([
            RouteStation(train_id=duronto.id, station_id=station_objs['NDLS'].id, stop_number=1, distance_km=0.0, departure_time='19:45', day_number=1),
            RouteStation(train_id=duronto.id, station_id=station_objs['CNB'].id, stop_number=2, distance_km=440.0, arrival_time='00:25', departure_time='00:30', day_number=2),
            RouteStation(train_id=duronto.id, station_id=station_objs['SDAH'].id, stop_number=3, distance_km=1450.0, arrival_time='12:25', departure_time='--:--', day_number=2),
        ])
        db.session.add_all([
            CoachQuotaConfig(train_id=duronto.id, travel_class='2A', total_cnf_seats=4, total_rac_seats=2, total_wl_seats=2, base_fare_per_km=2.4),
            CoachQuotaConfig(train_id=duronto.id, travel_class='3A', total_cnf_seats=4, total_rac_seats=2, total_wl_seats=2, base_fare_per_km=1.7),
        ])

        # 7. Swarna Jayanti Rajdhani Express (12958)
        swarna = Train(train_number='12958', name='Swarna Jayanti Rajdhani', source_station_id=station_objs['NDLS'].id, destination_station_id=station_objs['ADI'].id, operating_days='Daily', is_active=True)
        db.session.add(swarna); db.session.flush()
        db.session.add_all([
            RouteStation(train_id=swarna.id, station_id=station_objs['NDLS'].id, stop_number=1, distance_km=0.0, departure_time='19:55', day_number=1),
            RouteStation(train_id=swarna.id, station_id=station_objs['JP'].id, stop_number=2, distance_km=308.0, arrival_time='00:05', departure_time='00:15', day_number=2),
            RouteStation(train_id=swarna.id, station_id=station_objs['ADI'].id, stop_number=3, distance_km=934.0, arrival_time='08:25', departure_time='--:--', day_number=2),
        ])
        db.session.add_all([
            CoachQuotaConfig(train_id=swarna.id, travel_class='1A', total_cnf_seats=3, total_rac_seats=1, total_wl_seats=1, base_fare_per_km=3.3),
            CoachQuotaConfig(train_id=swarna.id, travel_class='3A', total_cnf_seats=4, total_rac_seats=2, total_wl_seats=2, base_fare_per_km=1.8),
        ])

        # 8. Ahmedabad Shatabdi Express (12010)
        adi_shat = Train(train_number='12010', name='Ahmedabad Shatabdi Express', source_station_id=station_objs['MMCT'].id, destination_station_id=station_objs['ADI'].id, operating_days='Mon,Tue,Wed,Thu,Fri,Sat', is_active=True)
        db.session.add(adi_shat); db.session.flush()
        db.session.add_all([
            RouteStation(train_id=adi_shat.id, station_id=station_objs['MMCT'].id, stop_number=1, distance_km=0.0, departure_time='06:10', day_number=1),
            RouteStation(train_id=adi_shat.id, station_id=station_objs['ST'].id, stop_number=2, distance_km=263.0, arrival_time='09:20', departure_time='09:25', day_number=1),
            RouteStation(train_id=adi_shat.id, station_id=station_objs['BRC'].id, stop_number=3, distance_km=392.0, arrival_time='11:00', departure_time='11:05', day_number=1),
            RouteStation(train_id=adi_shat.id, station_id=station_objs['ADI'].id, stop_number=4, distance_km=493.0, arrival_time='12:45', departure_time='--:--', day_number=1),
        ])
        db.session.add_all([
            CoachQuotaConfig(train_id=adi_shat.id, travel_class='CC', total_cnf_seats=5, total_rac_seats=2, total_wl_seats=2, base_fare_per_km=1.5),
        ])

        # 9. Tamil Nadu Superfast Express (12622)
        tn_exp = Train(train_number='12622', name='Tamil Nadu Superfast Express', source_station_id=station_objs['NDLS'].id, destination_station_id=station_objs['MAS'].id, operating_days='Daily', is_active=True)
        db.session.add(tn_exp); db.session.flush()
        db.session.add_all([
            RouteStation(train_id=tn_exp.id, station_id=station_objs['NDLS'].id, stop_number=1, distance_km=0.0, departure_time='21:05', day_number=1),
            RouteStation(train_id=tn_exp.id, station_id=station_objs['AGC'].id, stop_number=2, distance_km=195.0, arrival_time='23:28', departure_time='23:30', day_number=1),
            RouteStation(train_id=tn_exp.id, station_id=station_objs['BPL'].id, stop_number=3, distance_km=707.0, arrival_time='06:45', departure_time='06:50', day_number=2),
            RouteStation(train_id=tn_exp.id, station_id=station_objs['MAS'].id, stop_number=4, distance_km=2182.0, arrival_time='06:15', departure_time='--:--', day_number=3),
        ])
        db.session.add_all([
            CoachQuotaConfig(train_id=tn_exp.id, travel_class='SL', total_cnf_seats=4, total_rac_seats=2, total_wl_seats=2, base_fare_per_km=1.0),
            CoachQuotaConfig(train_id=tn_exp.id, travel_class='3A', total_cnf_seats=3, total_rac_seats=2, total_wl_seats=2, base_fare_per_km=1.8),
        ])

        # 10. Punjab Mail (12138)
        punjab = Train(train_number='12138', name='Punjab Mail', source_station_id=station_objs['NDLS'].id, destination_station_id=station_objs['CSMT'].id, operating_days='Daily', is_active=True)
        db.session.add(punjab); db.session.flush()
        db.session.add_all([
            RouteStation(train_id=punjab.id, station_id=station_objs['NDLS'].id, stop_number=1, distance_km=0.0, departure_time='05:15', day_number=1),
            RouteStation(train_id=punjab.id, station_id=station_objs['AGC'].id, stop_number=2, distance_km=195.0, arrival_time='07:35', departure_time='07:40', day_number=1),
            RouteStation(train_id=punjab.id, station_id=station_objs['BPL'].id, stop_number=3, distance_km=707.0, arrival_time='14:25', departure_time='14:30', day_number=1),
            RouteStation(train_id=punjab.id, station_id=station_objs['CSMT'].id, stop_number=4, distance_km=1543.0, arrival_time='07:35', departure_time='--:--', day_number=2),
        ])
        db.session.add_all([
            CoachQuotaConfig(train_id=punjab.id, travel_class='SL', total_cnf_seats=4, total_rac_seats=2, total_wl_seats=2, base_fare_per_km=0.9),
            CoachQuotaConfig(train_id=punjab.id, travel_class='3A', total_cnf_seats=3, total_rac_seats=2, total_wl_seats=2, base_fare_per_km=1.7),
        ])

        db.session.commit()

        print("--> Generating High-Occupancy Seed Bookings for OCTOBER 2026 (CNF, RAC, WL)...")

        # Generate realistic travel dates for NEXT MONTH (October 2026)
        october_dates = [
            date(2026, 10, 5),
            date(2026, 10, 10),
            date(2026, 10, 15),
            date(2026, 10, 20),
            date(2026, 10, 25),
        ]

        passenger_names = [
            ('Rahul Sharma', 32, 'Male', 'Lower'),
            ('Sunita Sharma', 29, 'Female', 'Upper'),
            ('Amitabh Kumar', 62, 'Male', 'Lower'),
            ('Priya Verma', 27, 'Female', 'Side Lower'),
            ('Vikram Singh', 45, 'Male', 'Middle'),
            ('Neha Singh', 41, 'Female', 'Upper'),
            ('Karan Johar', 52, 'Male', 'Side Upper'),
            ('Rohan Das', 23, 'Male', 'Lower')
        ]

        # Seed bookings across trains and dates to create authentic RAC and WL states
        for target_date in october_dates:
            
            # 1. Fill Mumbai Rajdhani 3A (3 CNF, 2 RAC, 2 WL)
            book_ticket(
                user_id=passenger1.id, train_id=rajdhani.id, from_station_id=station_objs['NDLS'].id, to_station_id=station_objs['MMCT'].id,
                journey_date=target_date, travel_class='3A', quota='GN',
                passengers_data=[
                    {'name': passenger_names[0][0], 'age': passenger_names[0][1], 'gender': passenger_names[0][2], 'berth_preference': passenger_names[0][3]},
                    {'name': passenger_names[1][0], 'age': passenger_names[1][1], 'gender': passenger_names[1][2], 'berth_preference': passenger_names[1][3]},
                    {'name': passenger_names[2][0], 'age': passenger_names[2][1], 'gender': passenger_names[2][2], 'berth_preference': passenger_names[2][3]}
                ]
            )
            # Add RAC bookings
            book_ticket(
                user_id=passenger2.id, train_id=rajdhani.id, from_station_id=station_objs['NDLS'].id, to_station_id=station_objs['MMCT'].id,
                journey_date=target_date, travel_class='3A', quota='GN',
                passengers_data=[
                    {'name': passenger_names[3][0], 'age': passenger_names[3][1], 'gender': passenger_names[3][2], 'berth_preference': passenger_names[3][3]},
                    {'name': passenger_names[4][0], 'age': passenger_names[4][1], 'gender': passenger_names[4][2], 'berth_preference': passenger_names[4][3]}
                ]
            )
            # Add WL bookings
            book_ticket(
                user_id=passenger3.id, train_id=rajdhani.id, from_station_id=station_objs['NDLS'].id, to_station_id=station_objs['MMCT'].id,
                journey_date=target_date, travel_class='3A', quota='GN',
                passengers_data=[
                    {'name': passenger_names[5][0], 'age': passenger_names[5][1], 'gender': passenger_names[5][2], 'berth_preference': passenger_names[5][3]},
                    {'name': passenger_names[6][0], 'age': passenger_names[6][1], 'gender': passenger_names[6][2], 'berth_preference': passenger_names[6][3]}
                ]
            )

            # 2. Fill Vande Bharat Express CC
            book_ticket(
                user_id=passenger1.id, train_id=vande.id, from_station_id=station_objs['NDLS'].id, to_station_id=station_objs['HWH'].id,
                journey_date=target_date, travel_class='CC', quota='GN',
                passengers_data=[
                    {'name': 'Ramesh Chandra', 'age': 65, 'gender': 'Male', 'berth_preference': 'Window'},
                    {'name': 'Sita Devi', 'age': 60, 'gender': 'Female', 'berth_preference': 'Window'},
                    {'name': 'Anil Kapoor', 'age': 35, 'gender': 'Male', 'berth_preference': 'Aisle'}
                ]
            )

            # 3. Fill Howrah Rajdhani 3A
            book_ticket(
                user_id=passenger2.id, train_id=hwh_raj.id, from_station_id=station_objs['HWH'].id, to_station_id=station_objs['NDLS'].id,
                journey_date=target_date, travel_class='3A', quota='GN',
                passengers_data=[
                    {'name': 'Subhash Bose', 'age': 45, 'gender': 'Male', 'berth_preference': 'Lower'},
                    {'name': 'Meena Bose', 'age': 42, 'gender': 'Female', 'berth_preference': 'Upper'},
                    {'name': 'Debashish Roy', 'age': 29, 'gender': 'Male', 'berth_preference': 'Side Lower'}
                ]
            )

        print(f"--> Database Seeded Successfully with October 2026 Real-World Datasets!")
        print(f"Default Credentials:")
        print(f"  Admin: username='admin', password='admin123'")
        print(f"  Passenger: username='passenger', password='user123'")
        print(f"  Seeded Dates for October 2026: 2026-10-05, 2026-10-10, 2026-10-15, 2026-10-20, 2026-10-25")

if __name__ == '__main__':
    seed()
