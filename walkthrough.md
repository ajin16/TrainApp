# Walkthrough - IRCTC Web App (South Indian Railways & Admin Privileges)

The **IRCTC Indian Railways Train Booking Web Application** has been updated with real-world **South Indian Railways** data (Southern Railway - SR, South Western Railway - SWR, South Central Railway - SCR) and seeded with dedicated administrator accounts possessing full administrative privileges.

---

## 1. Administrator Accounts (Full Admin Privileges)

Two administrator accounts with `role='admin'` are configured in the database:

| Username | Password | Role | Full Name | Email | Privileges |
|---|---|---|---|---|---|
| `admin` | `admin123` | `admin` | IRCTC Chief Administrator | `admin@irctc.gov.in` | Full Admin Dashboard, Train Management, Route Halts, Seat Quotas, Charting, Global Bookings |
| `south_admin` | `admin123` | `admin` | Southern Railway Principal Chief Operations Manager | `admin.sr@indianrail.gov.in` | Full Admin Dashboard, Train Management, Route Halts, Seat Quotas, Charting, Global Bookings |

### What Admin Privileges Include:
- **Admin Dashboard (`/admin/dashboard`)**: Total revenue, total bookings, active train inventory, CNF/RAC/WL passenger metrics, recent system transactions.
- **Train Inventory & Route Setup (`/admin/trains`)**: Create new trains and configure intermediate halts, distances, day numbers, arrival/departure schedules.
- **Coach Quota Configuration (`/admin/train/<id>`)**: Set CNF limits, RAC limits, WL limits, and base fare per km for all classes (`1A`, `2A`, `3A`, `SL`, `CC`, `2S`).
- **Global Bookings Inventory (`/admin/bookings`)**: Search and filter all passenger bookings across all trains and PNRs.
- **Reservation Charting Engine (`/admin/chart`)**: Trigger reservation charting for any train run, locking bookings, assigning final RAC seats, and automatically refunding unconfirmed waitlist passengers.

---

## 2. Real-World South Indian Railway Stations

The database includes 23 real-world stations covering Tamil Nadu, Kerala, Karnataka, Andhra Pradesh, Telangana, and key connecting national hubs:

### Southern Railway (Tamil Nadu & Kerala):
- `MAS`: MGR Chennai Central (Chennai, Tamil Nadu)
- `MS`: Chennai Egmore (Chennai, Tamil Nadu)
- `CBE`: Coimbatore Junction (Coimbatore, Tamil Nadu)
- `MDU`: Madurai Junction (Madurai, Tamil Nadu)
- `TPJ`: Tiruchchirappalli Junction (Tiruchchirappalli, Tamil Nadu)
- `SA`: Salem Junction (Salem, Tamil Nadu)
- `ED`: Erode Junction (Erode, Tamil Nadu)
- `KPD`: Katpadi Junction / Vellore (Vellore, Tamil Nadu)
- `TEN`: Tirunelveli Junction (Tirunelveli, Tamil Nadu)
- `TVC`: Thiruvananthapuram Central (Trivandrum, Kerala)
- `ERS`: Ernakulam Junction / South (Kochi, Kerala)
- `CLT`: Kozhikode Main / Calicut (Kozhikode, Kerala)
- `CAN`: Kannur (Kannur, Kerala)
- `TCR`: Thrissur (Thrissur, Kerala)
- `PGT`: Palakkad Junction (Palakkad, Kerala)

### South Western & South Central Railway:
- `SBC`: KSR Bengaluru City (Bengaluru, Karnataka)
- `MYS`: Mysuru Junction (Mysuru, Karnataka)
- `SC`: Secunderabad Junction (Hyderabad, Telangana)
- `BZA`: Vijayawada Junction (Vijayawada, Andhra Pradesh)
- `TPTY`: Tirupati Main (Tirupati, Andhra Pradesh)

### National Hubs:
- `NDLS`: New Delhi (Delhi)
- `MMCT`: Mumbai Central (Maharashtra)
- `HWH`: Howrah Junction (West Bengal)

---

## 3. Real-World South Indian Trains Seeded

1. **`20607` - Chennai - Mysuru Vande Bharat Express**
   - Route: `MAS` (05:50) $\rightarrow$ `KPD` (07:13) $\rightarrow$ `SBC` (10:15) $\rightarrow$ `MYS` (12:20) [500 km]
   - Classes: `CC` (AC Chair Car), `1A` (Executive Chair Car)
2. **`12675` - Kovai Superfast Express**
   - Route: `MAS` (06:10) $\rightarrow$ `KPD` (07:53) $\rightarrow$ `SA` (10:52) $\rightarrow$ `ED` (11:50) $\rightarrow$ `CBE` (14:05) [495 km]
   - Classes: `CC`, `2S` (Second Sitting)
3. **`12635` - Vaigai Superfast Express**
   - Route: `MS` (13:50) $\rightarrow$ `TPJ` (19:45) $\rightarrow$ `MDU` (21:30) [497 km]
   - Classes: `CC`, `2S`
4. **`20633` - Kerala Vande Bharat Express**
   - Route: `CAN` (15:28) $\rightarrow$ `CLT` (16:28) $\rightarrow$ `TCR` (18:10) $\rightarrow$ `ERS` (19:17) $\rightarrow$ `TVC` (22:40) [501 km]
   - Classes: `CC`, `1A`
5. **`12624` - Trivandrum - Chennai Mail**
   - Route: `TVC` $\rightarrow$ `TCR` $\rightarrow$ `PGT` $\rightarrow$ `CBE` $\rightarrow$ `ED` $\rightarrow$ `SA` $\rightarrow$ `KPD` $\rightarrow$ `MAS` [918 km]
   - Classes: `1A`, `2A`, `3A`, `SL`
6. **`12695` - Chennai - Trivandrum Superfast Express**
   - Route: `MAS` $\rightarrow$ `KPD` $\rightarrow$ `SA` $\rightarrow$ `ED` $\rightarrow$ `CBE` $\rightarrow$ `PGT` $\rightarrow$ `TCR` $\rightarrow$ `ERS` $\rightarrow$ `TVC` [924 km]
   - Classes: `2A`, `3A`, `SL`
7. **`12637` - Pandian Superfast Express**
   - Route: `MS` (Chennai Egmore) $\rightarrow$ `TPJ` (Trichy) $\rightarrow$ `MDU` (Madurai) [497 km]
   - Classes: `1A`, `2A`, `3A`, `SL`
8. **`16525` - Island Express (Kanyakumari - Bengaluru)**
   - Route: `TVC` $\rightarrow$ `ERS` $\rightarrow$ `TCR` $\rightarrow$ `PGT` $\rightarrow$ `CBE` $\rightarrow$ `ED` $\rightarrow$ `SA` $\rightarrow$ `SBC` [944 km]
   - Classes: `2A`, `3A`, `SL`
9. **`12759` - Charminar Superfast Express**
   - Route: `MAS` (Chennai Central) $\rightarrow$ `BZA` (Vijayawada) $\rightarrow$ `SC` (Secunderabad/Hyderabad) [790 km]
   - Classes: `1A`, `2A`, `3A`, `SL`
10. **`12626` - Kerala Superfast Express**
    - Route: `NDLS` $\rightarrow$ `BZA` $\rightarrow$ `TPTY` $\rightarrow$ `KPD` $\rightarrow$ `SA` $\rightarrow$ `ED` $\rightarrow$ `CBE` $\rightarrow$ `PGT` $\rightarrow$ `TCR` $\rightarrow$ `ERS` $\rightarrow$ `TVC` [3030 km]
    - Classes: `2A`, `3A`, `SL`

---

## 4. Seeded Upcoming Travel Dates & Authentic Bookings

Upcoming journey dates seeded across South Indian routes:
- `2026-10-25`
- `2026-10-28`
- `2026-11-02`
- `2026-11-05`
- `2026-11-10`
- `2026-11-15`

### Test Accounts:
- **Admin Accounts**:
  - `admin` / `admin123`
  - `south_admin` / `admin123`
- **Passenger Accounts**:
  - `anand` / `user123` (Chennai)
  - `karthik` / `user123` (Coimbatore)
  - `lakshmi` / `user123` (Trivandrum)
  - `passenger` / `user123`
  - `priya` / `user123` (Madurai)

---

## 5. Verification

- MySQL Database Live Query:
  - Users: 7 (2 Admins, 5 Passengers)
  - Stations: 23
  - Trains: 10
  - Route Stops: 64
  - Coach Quotas: 29
  - Bookings: 36
  - Passengers: 90 (78 CNF, 12 RAC)
- Automated Unit Tests:
  `python -m unittest discover -s tests` $\rightarrow$ **7 / 7 Tests Passed Cleanly (0 Errors)**
