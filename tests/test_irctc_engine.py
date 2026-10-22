import unittest
from datetime import date, timedelta
from app import create_app
from models import db, User, Station, Train, Booking, Passenger, CoachQuotaConfig
from services.booking_service import search_trains, get_class_availability, calculate_fare, book_ticket
from services.cancellation_service import cancel_passengers, promote_rac_and_wl
from services.chart_service import prepare_reservation_chart
from services.ticket_service import get_coach_bay_matrix, get_ticket_summary

class TestIRCTCEngine(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        db.drop_all()
        db.create_all()
        self._seed_test_data()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _seed_test_data(self):
        # Create User
        u = User(username='testuser', email='test@user.com', full_name='Test User', role='user')
        u.set_password('password')
        db.session.add(u)

        # Create Stations
        s1 = Station(code='NDLS', name='New Delhi', city='Delhi', state='Delhi')
        s2 = Station(code='CNB', name='Kanpur Central', city='Kanpur', state='UP')
        s3 = Station(code='PRYJ', name='Prayagraj', city='Prayagraj', state='UP')
        db.session.add_all([s1, s2, s3])
        db.session.commit()

        # Create Train
        t = Train(train_number='12345', name='Express Special', source_station_id=s1.id, destination_station_id=s3.id)
        db.session.add(t)
        db.session.flush()

        # Create Routes (NDLS -> CNB -> PRYJ)
        from models import RouteStation
        r1 = RouteStation(train_id=t.id, station_id=s1.id, stop_number=1, distance_km=0.0, departure_time='06:00')
        r2 = RouteStation(train_id=t.id, station_id=s2.id, stop_number=2, distance_km=440.0, arrival_time='11:00', departure_time='11:05')
        r3 = RouteStation(train_id=t.id, station_id=s3.id, stop_number=3, distance_km=630.0, arrival_time='14:00')
        db.session.add_all([r1, r2, r3])

        # Create Low Capacity Quotas: 4 CNF, 1 RAC, 1 WL for testing
        q = CoachQuotaConfig(train_id=t.id, travel_class='3A', total_cnf_seats=4, total_rac_seats=1, total_wl_seats=1, base_fare_per_km=1.8)
        db.session.add(q)
        db.session.commit()

        self.train_id = t.id
        self.user_id = u.id
        self.s1_id = s1.id
        self.s3_id = s3.id

    def test_search_trains(self):
        journey_date = date.today() + timedelta(days=2)
        results, from_st, to_st = search_trains('NDLS', 'PRYJ', journey_date)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['distance_km'], 630.0)
        self.assertIn('3A', results[0]['classes'])

    def test_fare_calculation(self):
        fare_info = calculate_fare(distance_km=630.0, travel_class='3A', quota='GN')
        self.assertGreater(fare_info['base_fare'], 1000.0)
        self.assertGreater(fare_info['gst'], 0.0)
        self.assertGreater(fare_info['total_per_passenger'], fare_info['base_fare'])

    def test_seat_allocation_cnf_rac_wl_sequence(self):
        journey_date = date.today() + timedelta(days=2)

        # 1. Book 2 passengers -> should get CNF
        success1, b1 = book_ticket(
            self.user_id, self.train_id, self.s1_id, self.s3_id, journey_date, '3A', 'GN',
            [{'name': 'P1', 'age': 30, 'gender': 'Male'}, {'name': 'P2', 'age': 28, 'gender': 'Female'}]
        )
        self.assertTrue(success1)
        self.assertEqual(b1.passengers[0].current_status, 'CNF')
        self.assertEqual(b1.passengers[1].current_status, 'CNF')

    def test_berth_preference_matching(self):
        journey_date = date.today() + timedelta(days=2)

        # Book senior citizen requesting Lower berth
        success, b = book_ticket(
            self.user_id, self.train_id, self.s1_id, self.s3_id, journey_date, '3A', 'GN',
            [{'name': 'Senior Citizen', 'age': 65, 'gender': 'Male', 'berth_preference': 'Lower'}]
        )
        self.assertTrue(success)
        self.assertEqual(b.passengers[0].berth_type, 'Lower')

    def test_visual_coach_bay_matrix(self):
        matrix = get_coach_bay_matrix('3A', 4)
        self.assertIsNotNone(matrix)
        self.assertEqual(matrix['bay_number'], 1)
        self.assertEqual(len(matrix['layout']), 8)
        allocated_seats = [s for s in matrix['layout'] if s['is_allocated']]
        self.assertEqual(len(allocated_seats), 1)
        self.assertEqual(allocated_seats[0]['seat_no'], 4)

    def test_cancellation_and_auto_promotion_cascade(self):
        journey_date = date.today() + timedelta(days=3)

        # Book 4 CNF, 1 RAC, 1 WL
        _, b1 = book_ticket(self.user_id, self.train_id, self.s1_id, self.s3_id, journey_date, '3A', 'GN', [{'name': 'P1', 'age': 30, 'gender': 'Male'}, {'name': 'P2', 'age': 30, 'gender': 'Male'}, {'name': 'P3', 'age': 30, 'gender': 'Male'}, {'name': 'P4', 'age': 30, 'gender': 'Male'}])
        _, b5 = book_ticket(self.user_id, self.train_id, self.s1_id, self.s3_id, journey_date, '3A', 'GN', [{'name': 'P5', 'age': 40, 'gender': 'Male'}]) # RAC 1
        _, b6 = book_ticket(self.user_id, self.train_id, self.s1_id, self.s3_id, journey_date, '3A', 'GN', [{'name': 'P6', 'age': 25, 'gender': 'Female'}]) # WL 1

        p1_id = b1.passengers[0].id
        p5 = b5.passengers[0]
        p6 = b6.passengers[0]

        self.assertEqual(p5.current_status, 'RAC')
        self.assertEqual(p6.current_status, 'WL')

        # Cancel P1 (CNF passenger)
        success_cancel, msg, refund = cancel_passengers(b1.id, [p1_id])
        self.assertTrue(success_cancel)
        self.assertGreater(refund, 0.0)

        # Refresh objects from DB
        db.session.refresh(p5)
        db.session.refresh(p6)

        # Verify P5 (was RAC 1) is now PROMOTED to CNF!
        self.assertEqual(p5.current_status, 'CNF')
        self.assertIsNotNone(p5.coach_no)
        self.assertIsNotNone(p5.seat_no)

        # Verify P6 (was WL 1) is now PROMOTED to RAC!
        self.assertEqual(p6.current_status, 'RAC')
        self.assertEqual(p6.rac_wl_number, 1)

    def test_train_schedule_lookup(self):
        response = self.client.get('/train-schedule/12345')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Express Special', response.data)
        self.assertIn(b'New Delhi', response.data)
        self.assertIn(b'Prayagraj', response.data)

if __name__ == '__main__':
    unittest.main()

