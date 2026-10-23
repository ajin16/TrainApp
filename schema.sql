-- =====================================================================
-- IRCTC Train Booking Application - MySQL Database Schema
-- Database: TrainApp
-- Target: MySQL 8.0+ / Aiven Cloud MySQL
-- =====================================================================

CREATE DATABASE IF NOT EXISTS `TrainApp` 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE `TrainApp`;

-- ---------------------------------------------------------------------
-- 1. Table: users
-- Stores registered passengers and administrator accounts
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(80) NOT NULL,
  `email` VARCHAR(120) NOT NULL,
  `password_hash` VARCHAR(256) NOT NULL,
  `full_name` VARCHAR(120) NOT NULL,
  `phone` VARCHAR(20) DEFAULT NULL,
  `role` VARCHAR(20) DEFAULT 'user',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_users_username` (`username`),
  UNIQUE KEY `uq_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 2. Table: stations
-- Stores all Indian Railway stations and their codes
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `stations` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `code` VARCHAR(10) NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `city` VARCHAR(100) NOT NULL,
  `state` VARCHAR(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_stations_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 3. Table: trains
-- Stores train information, source and destination stations
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `trains` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `train_number` VARCHAR(20) NOT NULL,
  `name` VARCHAR(120) NOT NULL,
  `source_station_id` INT NOT NULL,
  `destination_station_id` INT NOT NULL,
  `operating_days` VARCHAR(100) DEFAULT 'Mon,Tue,Wed,Thu,Fri,Sat,Sun',
  `is_active` TINYINT(1) DEFAULT 1,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_trains_train_number` (`train_number`),
  KEY `idx_trains_source_station` (`source_station_id`),
  KEY `idx_trains_dest_station` (`destination_station_id`),
  CONSTRAINT `fk_trains_source_station` FOREIGN KEY (`source_station_id`) REFERENCES `stations` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_trains_dest_station` FOREIGN KEY (`destination_station_id`) REFERENCES `stations` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 4. Table: route_stations
-- Route timetable, halts, arrival/departure schedules, and cumulative distance
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `route_stations` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `train_id` INT NOT NULL,
  `station_id` INT NOT NULL,
  `stop_number` INT NOT NULL,
  `distance_km` FLOAT NOT NULL DEFAULT 0.0,
  `arrival_time` VARCHAR(10) NOT NULL DEFAULT '--:--',
  `departure_time` VARCHAR(10) NOT NULL DEFAULT '--:--',
  `day_number` INT NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `idx_route_train_id` (`train_id`),
  KEY `idx_route_station_id` (`station_id`),
  CONSTRAINT `fk_route_train` FOREIGN KEY (`train_id`) REFERENCES `trains` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_route_station` FOREIGN KEY (`station_id`) REFERENCES `stations` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 5. Table: coach_quota_configs
-- Configures class-wise CNF, RAC, and WL limits and base fares per km
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `coach_quota_configs` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `train_id` INT NOT NULL,
  `travel_class` VARCHAR(10) NOT NULL,
  `total_cnf_seats` INT NOT NULL DEFAULT 30,
  `total_rac_seats` INT NOT NULL DEFAULT 10,
  `total_wl_seats` INT NOT NULL DEFAULT 15,
  `base_fare_per_km` FLOAT NOT NULL DEFAULT 1.5,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_train_class` (`train_id`, `travel_class`),
  CONSTRAINT `fk_quota_train` FOREIGN KEY (`train_id`) REFERENCES `trains` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 6. Table: bookings
-- Stores ticket booking headers with 10-digit unique PNR
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `bookings` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `pnr` VARCHAR(10) NOT NULL,
  `user_id` INT NOT NULL,
  `train_id` INT NOT NULL,
  `from_station_id` INT NOT NULL,
  `to_station_id` INT NOT NULL,
  `journey_date` DATE NOT NULL,
  `travel_class` VARCHAR(10) NOT NULL,
  `quota` VARCHAR(10) DEFAULT 'GN',
  `total_fare` FLOAT NOT NULL DEFAULT 0.0,
  `booking_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `status` VARCHAR(30) DEFAULT 'BOOKED',
  `chart_prepared` TINYINT(1) DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_bookings_pnr` (`pnr`),
  KEY `idx_bookings_user_id` (`user_id`),
  KEY `idx_bookings_train_id` (`train_id`),
  KEY `idx_bookings_from_station` (`from_station_id`),
  KEY `idx_bookings_to_station` (`to_station_id`),
  CONSTRAINT `fk_bookings_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_bookings_train` FOREIGN KEY (`train_id`) REFERENCES `trains` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_bookings_from_station` FOREIGN KEY (`from_station_id`) REFERENCES `stations` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_bookings_to_station` FOREIGN KEY (`to_station_id`) REFERENCES `stations` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 7. Table: passengers
-- Stores individual passenger details, allocated berth, and CNF/RAC/WL statuses
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `passengers` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `booking_id` INT NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `age` INT NOT NULL,
  `gender` VARCHAR(10) NOT NULL,
  `berth_preference` VARCHAR(20) DEFAULT 'No Preference',
  `booking_status` VARCHAR(20) NOT NULL,
  `current_status` VARCHAR(20) NOT NULL,
  `coach_no` VARCHAR(10) DEFAULT NULL,
  `seat_no` INT DEFAULT NULL,
  `berth_type` VARCHAR(20) DEFAULT NULL,
  `rac_wl_number` INT DEFAULT NULL,
  `is_cancelled` TINYINT(1) DEFAULT 0,
  `refund_amount` FLOAT DEFAULT 0.0,
  `cancelled_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_passengers_booking_id` (`booking_id`),
  CONSTRAINT `fk_passengers_booking` FOREIGN KEY (`booking_id`) REFERENCES `bookings` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 8. Table: chart_logs
-- Logs reservation charting execution, RAC finalization, and auto-refunded WL counts
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `chart_logs` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `train_id` INT NOT NULL,
  `journey_date` DATE NOT NULL,
  `prepared_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `total_passengers` INT DEFAULT 0,
  `cnf_count` INT DEFAULT 0,
  `rac_count` INT DEFAULT 0,
  `wl_count` INT DEFAULT 0,
  `auto_cancelled_wl_count` INT DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_chart_logs_train_id` (`train_id`),
  CONSTRAINT `fk_chart_logs_train` FOREIGN KEY (`train_id`) REFERENCES `trains` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
