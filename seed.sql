-- =====================================================================
-- IRCTC Train Booking App - Idempotent Seed Data Script
-- Database: TrainApp
-- Safe to run repeatedly (uses INSERT IGNORE)
-- =====================================================================

USE `TrainApp`;

-- 1. Users (Admins and Passengers)
INSERT IGNORE INTO `users` (`id`, `username`, `email`, `password_hash`, `full_name`, `phone`, `role`, `created_at`)
VALUES
  (1, 'admin', 'admin@irctc.gov.in', 'scrypt:32768:8:1$w3AdYRM1hxNS15Qb$191b10bb746f233f42a921f2d81bbe64270d05c417bd620730af95a839e55f2ea4185acc79d109135b2f8f9496bea7904f7bac0a687d9742c41f3c02962553ff', 'IRCTC Chief Administrator', '9811001122', 'admin', '2026-10-22 18:47:43'),
  (2, 'south_admin', 'admin.sr@indianrail.gov.in', 'scrypt:32768:8:1$5eqiF0SvcO3EZN1M$db49e57ac97543d0d722cb8a75a583ca039629f38f890cb6a40598432abd3e0176ea5395c7113ec30c0e1c14f49f4e2594b2ffb5c65b3f3bba62d46958d24aa6', 'Southern Railway Principal Chief Operations Manager', '044-25353142', 'admin', '2026-10-22 18:47:43'),
  (3, 'anand', 'anand.s@gmail.com', 'scrypt:32768:8:1$7rUzFM61DCilUZ5b$814b46fd6d7acc3646c2b8c42c77fdfada932aca4208a2df1d1229d1d9bbabd503f1b40fe248ca7914c98e4b3abbde285c21155fcb0669ebeda62132073401d3', 'Anand Subramanian', '9840123456', 'user', '2026-10-22 18:47:43'),
  (4, 'karthik', 'karthik.r@gmail.com', 'scrypt:32768:8:1$KzO96Wo8Ux8ImyWq$d816a76e6cef8083be9a16267e9e6167eb0b6cbfe19c6ad5506024ccde3f97e030c05918b99fabdf8419b72e9daedce83bf43c532da1de4378479cf503dae0cf', 'Karthik Ramanathan', '9443123456', 'user', '2026-10-22 18:47:43'),
  (5, 'lakshmi', 'lakshmi.nair@gmail.com', 'scrypt:32768:8:1$mE2dppD43kiiv24x$3c783d58eeb8f09a764a6081dac1b4d776c6f59e81e27b70e08257a62d937c4d5b7ebcb4dd13ba5d70d3e19389a4815e9dc9bb581ecdc9a2a4c92ac79febd701', 'Lakshmi Nair', '9847123456', 'user', '2026-10-22 18:47:43'),
  (6, 'passenger', 'user@gmail.com', 'scrypt:32768:8:1$CIIGHlPJIS05fogt$694d30fdca10684a27741d1d80ae36ec226c79811037f527583bedb4fbb5ad195efa7e5fa45a856bf1b90d88b7332b58716270eb0c2dde37ac41cf71ea3ccec3', 'Rahul Sharma', '9876543210', 'user', '2026-10-22 18:47:44'),
  (7, 'priya', 'priya.v@gmail.com', 'scrypt:32768:8:1$4Vt09WLZ1UrLdkp6$341bee9c965f324b1d456ef7c4f21a0800bb0d12e3c955b60ef03b8976d8a98d3971b55cdc99b4dfa5886f6d1ad372f8137180be8558ee0e644dffe56c0c6078', 'Priya Verma', '9876500112', 'user', '2026-10-22 18:47:44');

-- 2. Stations (South Indian Railway & Hubs)
INSERT IGNORE INTO `stations` (`id`, `code`, `name`, `city`, `state`)
VALUES
  (1, 'MAS', 'MGR Chennai Central', 'Chennai', 'Tamil Nadu'),
  (2, 'MS', 'Chennai Egmore', 'Chennai', 'Tamil Nadu'),
  (3, 'CBE', 'Coimbatore Junction', 'Coimbatore', 'Tamil Nadu'),
  (4, 'MDU', 'Madurai Junction', 'Madurai', 'Tamil Nadu'),
  (5, 'TPJ', 'Tiruchchirappalli Junction', 'Tiruchchirappalli', 'Tamil Nadu'),
  (6, 'SA', 'Salem Junction', 'Salem', 'Tamil Nadu'),
  (7, 'ED', 'Erode Junction', 'Erode', 'Tamil Nadu'),
  (8, 'KPD', 'Katpadi Junction (Vellore)', 'Vellore', 'Tamil Nadu'),
  (9, 'TEN', 'Tirunelveli Junction', 'Tirunelveli', 'Tamil Nadu'),
  (10, 'TVC', 'Thiruvananthapuram Central', 'Thiruvananthapuram', 'Kerala'),
  (11, 'ERS', 'Ernakulam Junction (South)', 'Kochi', 'Kerala'),
  (12, 'CLT', 'Kozhikode Main (Calicut)', 'Kozhikode', 'Kerala'),
  (13, 'CAN', 'Kannur', 'Kannur', 'Kerala'),
  (14, 'TCR', 'Thrissur', 'Thrissur', 'Kerala'),
  (15, 'PGT', 'Palakkad Junction', 'Palakkad', 'Kerala'),
  (16, 'SBC', 'KSR Bengaluru City', 'Bengaluru', 'Karnataka'),
  (17, 'MYS', 'Mysuru Junction', 'Mysuru', 'Karnataka'),
  (18, 'SC', 'Secunderabad Junction (Hyderabad)', 'Hyderabad', 'Telangana'),
  (19, 'BZA', 'Vijayawada Junction', 'Vijayawada', 'Andhra Pradesh'),
  (20, 'TPTY', 'Tirupati Main', 'Tirupati', 'Andhra Pradesh'),
  (21, 'NDLS', 'New Delhi', 'New Delhi', 'Delhi'),
  (22, 'MMCT', 'Mumbai Central', 'Mumbai', 'Maharashtra'),
  (23, 'HWH', 'Howrah Junction (Kolkata)', 'Kolkata', 'West Bengal');

-- 3. Trains
INSERT IGNORE INTO `trains` (`id`, `train_number`, `name`, `source_station_id`, `destination_station_id`, `operating_days`, `is_active`, `created_at`)
VALUES
  (1, '20607', 'Chennai - Mysuru Vande Bharat Express', 1, 17, 'Mon,Tue,Thu,Fri,Sat,Sun', 1, '2026-10-22 18:47:45'),
  (2, '12675', 'Kovai Superfast Express', 1, 3, 'Daily', 1, '2026-10-22 18:47:45'),
  (3, '12635', 'Vaigai Superfast Express', 2, 4, 'Daily', 1, '2026-10-22 18:47:45'),
  (4, '20633', 'Kerala Vande Bharat Express', 13, 10, 'Mon,Tue,Wed,Fri,Sat,Sun', 1, '2026-10-22 18:47:45'),
  (5, '12624', 'Trivandrum - Chennai Mail', 10, 1, 'Daily', 1, '2026-10-22 18:47:45'),
  (6, '12695', 'Chennai - Trivandrum Superfast Express', 1, 10, 'Daily', 1, '2026-10-22 18:47:45'),
  (7, '12637', 'Pandian Superfast Express', 2, 4, 'Daily', 1, '2026-10-22 18:47:45'),
  (8, '16525', 'Island Express (Kanyakumari - Bengaluru)', 10, 16, 'Daily', 1, '2026-10-22 18:47:45'),
  (9, '12759', 'Charminar Superfast Express', 1, 18, 'Daily', 1, '2026-10-22 18:47:46'),
  (10, '12626', 'Kerala Superfast Express', 21, 10, 'Daily', 1, '2026-10-22 18:47:46');

-- 4. Route Stations (Timetables and Halts)
INSERT IGNORE INTO `route_stations` (`id`, `train_id`, `station_id`, `stop_number`, `distance_km`, `arrival_time`, `departure_time`, `day_number`)
VALUES
  (1, 1, 1, 1, 0.0, '--:--', '05:50', 1),
  (2, 1, 8, 2, 130.0, '07:13', '07:15', 1),
  (3, 1, 16, 3, 360.0, '10:15', '10:20', 1),
  (4, 1, 17, 4, 500.0, '12:20', '--:--', 1),
  (5, 2, 1, 1, 0.0, '--:--', '06:10', 1),
  (6, 2, 8, 2, 130.0, '07:53', '07:55', 1),
  (7, 2, 6, 3, 335.0, '10:52', '10:55', 1),
  (8, 2, 7, 4, 395.0, '11:50', '11:55', 1),
  (9, 2, 3, 5, 495.0, '14:05', '--:--', 1),
  (10, 3, 2, 1, 0.0, '--:--', '13:50', 1),
  (11, 3, 5, 2, 336.0, '19:45', '19:50', 1),
  (12, 3, 4, 3, 497.0, '21:30', '--:--', 1),
  (13, 4, 13, 1, 0.0, '--:--', '15:28', 1),
  (14, 4, 12, 2, 89.0, '16:28', '16:30', 1),
  (15, 4, 14, 3, 208.0, '18:10', '18:12', 1),
  (16, 4, 11, 4, 282.0, '19:17', '19:20', 1),
  (17, 4, 10, 5, 501.0, '22:40', '--:--', 1),
  (18, 5, 10, 1, 0.0, '--:--', '15:00', 1),
  (19, 5, 14, 2, 292.0, '20:40', '20:43', 1),
  (20, 5, 15, 3, 368.0, '22:15', '22:20', 1),
  (21, 5, 3, 4, 423.0, '23:45', '23:50', 1),
  (22, 5, 7, 5, 524.0, '01:15', '01:20', 2),
  (23, 5, 6, 6, 584.0, '02:12', '02:15', 2),
  (24, 5, 8, 7, 788.0, '04:43', '04:45', 2),
  (25, 5, 1, 8, 918.0, '07:45', '--:--', 2),
  (26, 6, 1, 1, 0.0, '--:--', '15:20', 1),
  (27, 6, 8, 2, 130.0, '17:08', '17:10', 1),
  (28, 6, 6, 3, 335.0, '20:02', '20:05', 1),
  (29, 6, 7, 4, 395.0, '21:05', '21:10', 1),
  (30, 6, 3, 5, 495.0, '22:50', '22:55', 1),
  (31, 6, 15, 6, 551.0, '00:05', '00:10', 2),
  (32, 6, 14, 7, 626.0, '01:30', '01:33', 2),
  (33, 6, 11, 8, 700.0, '02:50', '02:55', 2),
  (34, 6, 10, 9, 924.0, '07:45', '--:--', 2),
  (35, 7, 2, 1, 0.0, '--:--', '21:40', 1),
  (36, 7, 5, 2, 336.0, '03:30', '03:35', 2),
  (37, 7, 4, 3, 497.0, '05:35', '--:--', 2),
  (38, 8, 10, 1, 0.0, '--:--', '12:40', 1),
  (39, 8, 11, 2, 220.0, '17:10', '17:15', 1),
  (40, 8, 14, 3, 294.0, '18:20', '18:23', 1),
  (41, 8, 15, 4, 370.0, '19:50', '19:55', 1),
  (42, 8, 3, 5, 425.0, '22:15', '22:20', 1),
  (43, 8, 7, 6, 526.0, '00:05', '00:10', 2),
  (44, 8, 6, 7, 586.0, '01:05', '01:10', 2),
  (45, 8, 16, 8, 944.0, '06:40', '--:--', 2),
  (46, 9, 1, 1, 0.0, '--:--', '17:30', 1),
  (47, 9, 19, 2, 431.0, '00:45', '00:55', 2),
  (48, 9, 18, 3, 790.0, '07:30', '--:--', 2),
  (49, 10, 21, 1, 0.0, '--:--', '20:10', 1),
  (50, 10, 19, 2, 1778.0, '04:15', '04:25', 3),
  (51, 10, 20, 3, 2160.0, '06:45', '06:50', 3),
  (52, 10, 8, 4, 2265.0, '09:10', '09:15', 3),
  (53, 10, 6, 5, 2470.0, '12:15', '12:20', 3),
  (54, 10, 7, 6, 2530.0, '13:15', '13:20', 3),
  (55, 10, 3, 7, 2631.0, '14:55', '15:00', 3),
  (56, 10, 15, 8, 2687.0, '16:05', '16:10', 3),
  (57, 10, 14, 9, 2762.0, '17:20', '17:23', 3),
  (58, 10, 11, 10, 2836.0, '18:50', '18:55', 3),
  (59, 10, 10, 11, 3030.0, '22:10', '--:--', 3);

-- 5. Coach Quota Configurations (Capacities & Base Fares)
INSERT IGNORE INTO `coach_quota_configs` (`id`, `train_id`, `travel_class`, `total_cnf_seats`, `total_rac_seats`, `total_wl_seats`, `base_fare_per_km`)
VALUES
  (1, 1, 'CC', 5, 2, 2, 1.8),
  (2, 1, '1A', 3, 1, 1, 3.4),
  (3, 2, 'CC', 5, 2, 2, 1.5),
  (4, 2, '2S', 6, 2, 2, 0.6),
  (5, 3, 'CC', 5, 2, 2, 1.5),
  (6, 3, '2S', 6, 2, 2, 0.6),
  (7, 4, 'CC', 5, 2, 2, 1.8),
  (8, 4, '1A', 3, 1, 1, 3.4),
  (9, 5, '1A', 3, 1, 1, 3.2),
  (10, 5, '2A', 4, 2, 2, 2.4),
  (11, 5, '3A', 4, 2, 2, 1.8),
  (12, 5, 'SL', 5, 2, 2, 1.0),
  (13, 6, '2A', 4, 2, 2, 2.4),
  (14, 6, '3A', 4, 2, 2, 1.8),
  (15, 6, 'SL', 5, 2, 2, 1.0),
  (16, 7, '1A', 3, 1, 1, 3.2),
  (17, 7, '2A', 4, 2, 2, 2.4),
  (18, 7, '3A', 4, 2, 2, 1.8),
  (19, 7, 'SL', 5, 2, 2, 1.0),
  (20, 8, '2A', 4, 2, 2, 2.2),
  (21, 8, '3A', 4, 2, 2, 1.7),
  (22, 8, 'SL', 5, 2, 2, 0.9),
  (23, 9, '1A', 3, 1, 1, 3.2),
  (24, 9, '2A', 4, 2, 2, 2.3),
  (25, 9, '3A', 4, 2, 2, 1.7),
  (26, 9, 'SL', 5, 2, 2, 0.9),
  (27, 10, '2A', 4, 2, 2, 2.3),
  (28, 10, '3A', 4, 2, 2, 1.7),
  (29, 10, 'SL', 5, 2, 2, 0.9);

