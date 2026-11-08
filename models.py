from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

def utcnow():
    """Return naive UTC datetime compatible with SQLite/MySQL without deprecation warnings."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), default='user')  # 'user' or 'admin'
    created_at = db.Column(db.DateTime, default=utcnow)
    
    bookings = db.relationship('Booking', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Station(db.Model):
    __tablename__ = 'stations'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False, index=True)  # e.g., NDLS
    name = db.Column(db.String(100), nullable=False, index=True)  # e.g., New Delhi
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<Station {self.code} - {self.name}>"


class Train(db.Model):
    __tablename__ = 'trains'
    
    id = db.Column(db.Integer, primary_key=True)
    train_number = db.Column(db.String(20), unique=True, nullable=False, index=True)  # e.g., 12952
    name = db.Column(db.String(120), nullable=False)  # e.g., Mumbai Rajdhani Express
    source_station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)
    destination_station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)
    operating_days = db.Column(db.String(100), default='Mon,Tue,Wed,Thu,Fri,Sat,Sun')
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    source_station = db.relationship('Station', foreign_keys=[source_station_id])
    destination_station = db.relationship('Station', foreign_keys=[destination_station_id])
    routes = db.relationship('RouteStation', backref='train', lazy=True, cascade='all, delete-orphan', order_by='RouteStation.stop_number')
    configs = db.relationship('CoachQuotaConfig', backref='train', lazy=True, cascade='all, delete-orphan')
    bookings = db.relationship('Booking', backref='train', lazy=True)


class RouteStation(db.Model):
    __tablename__ = 'route_stations'
    
    id = db.Column(db.Integer, primary_key=True)
    train_id = db.Column(db.Integer, db.ForeignKey('trains.id'), nullable=False, index=True)
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False, index=True)
    stop_number = db.Column(db.Integer, nullable=False)  # Sequence index: 1, 2, 3...
    distance_km = db.Column(db.Float, nullable=False, default=0.0)
    arrival_time = db.Column(db.String(10), nullable=False, default='--:--')  # e.g. 16:55
    departure_time = db.Column(db.String(10), nullable=False, default='--:--')  # e.g. 17:00
    day_number = db.Column(db.Integer, nullable=False, default=1)  # Day 1, Day 2

    station = db.relationship('Station', lazy='joined')

    __table_args__ = (
        db.Index('idx_route_train_station', 'train_id', 'station_id'),
    )


class CoachQuotaConfig(db.Model):
    __tablename__ = 'coach_quota_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    train_id = db.Column(db.Integer, db.ForeignKey('trains.id'), nullable=False, index=True)
    travel_class = db.Column(db.String(10), nullable=False)  # 1A, 2A, 3A, SL, CC, 2S
    total_cnf_seats = db.Column(db.Integer, nullable=False, default=30)
    total_rac_seats = db.Column(db.Integer, nullable=False, default=10)
    total_wl_seats = db.Column(db.Integer, nullable=False, default=15)
    base_fare_per_km = db.Column(db.Float, nullable=False, default=1.5)

    __table_args__ = (db.UniqueConstraint('train_id', 'travel_class', name='_train_class_uc'),)


class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    pnr = db.Column(db.String(10), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    train_id = db.Column(db.Integer, db.ForeignKey('trains.id'), nullable=False, index=True)
    from_station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)
    to_station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)
    journey_date = db.Column(db.Date, nullable=False, index=True)
    travel_class = db.Column(db.String(10), nullable=False)
    quota = db.Column(db.String(10), default='GN')  # GN, TQ, LD, SS
    total_fare = db.Column(db.Float, nullable=False, default=0.0)
    booking_time = db.Column(db.DateTime, default=utcnow, index=True)
    status = db.Column(db.String(30), default='BOOKED', index=True)  # BOOKED, CANCELLED, PARTIALLY_CANCELLED
    chart_prepared = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False, nullable=False, index=True)
    archived_at = db.Column(db.DateTime, nullable=True)

    from_station = db.relationship('Station', foreign_keys=[from_station_id])
    to_station = db.relationship('Station', foreign_keys=[to_station_id])
    passengers = db.relationship('Passenger', backref='booking', lazy=True, cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('idx_booking_train_date_class', 'train_id', 'journey_date', 'travel_class'),
    )


class Passenger(db.Model):
    __tablename__ = 'passengers'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    berth_preference = db.Column(db.String(20), default='No Preference')
    
    booking_status = db.Column(db.String(20), nullable=False)  # Status at purchase: CNF, RAC, WL
    current_status = db.Column(db.String(20), nullable=False, index=True)  # Real-time status: CNF, RAC, WL, CANCELLED
    
    coach_no = db.Column(db.String(10), nullable=True)  # e.g., B1, S2, A1
    seat_no = db.Column(db.Integer, nullable=True)     # e.g., 24
    berth_type = db.Column(db.String(20), nullable=True) # Lower, Middle, Upper, Side Lower, Side Upper
    rac_wl_number = db.Column(db.Integer, nullable=True) # For RAC 1 or WL 5
    
    is_cancelled = db.Column(db.Boolean, default=False, index=True)
    refund_amount = db.Column(db.Float, default=0.0)
    cancelled_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.Index('idx_passenger_status_cancelled', 'current_status', 'is_cancelled'),
    )


class ChartLog(db.Model):
    __tablename__ = 'chart_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    train_id = db.Column(db.Integer, db.ForeignKey('trains.id'), nullable=False, index=True)
    journey_date = db.Column(db.Date, nullable=False, index=True)
    prepared_at = db.Column(db.DateTime, default=utcnow)
    total_passengers = db.Column(db.Integer, default=0)
    cnf_count = db.Column(db.Integer, default=0)
    rac_count = db.Column(db.Integer, default=0)
    wl_count = db.Column(db.Integer, default=0)
    auto_cancelled_wl_count = db.Column(db.Integer, default=0)

    train = db.relationship('Train')

    __table_args__ = (
        db.Index('idx_chart_train_date', 'train_id', 'journey_date'),
    )
