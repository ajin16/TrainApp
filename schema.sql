-- ==============================================================================
-- IRCTC Railway Ticketing & Operations System - Database Schema (DDL)
-- Generated for MySQL 8.0+ / Aiven Cloud / Production
-- ==============================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    phone VARCHAR(20),
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS stations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL,
    city VARCHAR(80) NOT NULL,
    state VARCHAR(80) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS trains (
    id INT AUTO_INCREMENT PRIMARY KEY,
    train_number VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL,
    source_station_id INT NOT NULL,
    destination_station_id INT NOT NULL,
    operating_days VARCHAR(50) DEFAULT 'Daily',
    is_active BOOLEAN NOT NULL DEFAULT 1,
    FOREIGN KEY (source_station_id) REFERENCES stations(id) ON DELETE CASCADE,
    FOREIGN KEY (destination_station_id) REFERENCES stations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS route_stations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    train_id INT NOT NULL,
    station_id INT NOT NULL,
    stop_number INT NOT NULL,
    distance_km FLOAT NOT NULL DEFAULT 0.0,
    arrival_time VARCHAR(10) DEFAULT '--:--',
    departure_time VARCHAR(10) DEFAULT '--:--',
    day_number INT NOT NULL DEFAULT 1,
    FOREIGN KEY (train_id) REFERENCES trains(id) ON DELETE CASCADE,
    FOREIGN KEY (station_id) REFERENCES stations(id) ON DELETE CASCADE,
    UNIQUE KEY uq_train_stop (train_id, stop_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS coach_quota_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    train_id INT NOT NULL,
    travel_class VARCHAR(10) NOT NULL,
    total_cnf_seats INT NOT NULL DEFAULT 72,
    total_rac_seats INT NOT NULL DEFAULT 10,
    total_wl_seats INT NOT NULL DEFAULT 20,
    base_fare_per_km FLOAT NOT NULL DEFAULT 1.0,
    FOREIGN KEY (train_id) REFERENCES trains(id) ON DELETE CASCADE,
    UNIQUE KEY uq_train_class (train_id, travel_class)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    train_id INT NOT NULL,
    from_station_id INT NOT NULL,
    to_station_id INT NOT NULL,
    journey_date DATE NOT NULL,
    travel_class VARCHAR(10) NOT NULL,
    quota VARCHAR(10) NOT NULL DEFAULT 'GN',
    pnr VARCHAR(12) NOT NULL UNIQUE,
    booking_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_fare FLOAT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'CONFIRMED',
    is_archived BOOLEAN NOT NULL DEFAULT 0,
    archived_at DATETIME NULL,
    chart_prepared BOOLEAN NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (train_id) REFERENCES trains(id) ON DELETE CASCADE,
    FOREIGN KEY (from_station_id) REFERENCES stations(id) ON DELETE CASCADE,
    FOREIGN KEY (to_station_id) REFERENCES stations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS passengers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    age INT NOT NULL,
    gender VARCHAR(10) NOT NULL,
    berth_preference VARCHAR(20) DEFAULT 'No Preference',
    booking_status VARCHAR(20) NOT NULL,
    current_status VARCHAR(20) NOT NULL,
    coach_no VARCHAR(10),
    seat_no INT,
    berth_type VARCHAR(25),
    rac_wl_number INT,
    is_cancelled BOOLEAN NOT NULL DEFAULT 0,
    cancelled_at DATETIME NULL,
    refund_amount FLOAT NOT NULL DEFAULT 0.0,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chart_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    train_id INT NOT NULL,
    journey_date DATE NOT NULL,
    prepared_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_passengers INT NOT NULL DEFAULT 0,
    cnf_count INT NOT NULL DEFAULT 0,
    rac_count INT NOT NULL DEFAULT 0,
    wl_count INT NOT NULL DEFAULT 0,
    auto_cancelled_wl_count INT NOT NULL DEFAULT 0,
    FOREIGN KEY (train_id) REFERENCES trains(id) ON DELETE CASCADE,
    UNIQUE KEY uq_train_chart (train_id, journey_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
