from datetime import datetime

def format_status_badge(status, rac_wl_num=None):
    """Format status string into display badges with color coding."""
    if status == 'CNF':
        return {'text': 'CNF / Confirmed', 'badge': 'bg-success', 'code': 'CNF'}
    elif status == 'RAC':
        num = f"RAC {rac_wl_num}" if rac_wl_num else "RAC"
        return {'text': f"{num} (Reservation Against Cancellation)", 'badge': 'bg-warning text-dark', 'code': 'RAC'}
    elif status == 'WL':
        num = f"WL {rac_wl_num}" if rac_wl_num else "WL"
        return {'text': f"{num} (Waitlisted)", 'badge': 'bg-danger', 'code': 'WL'}
    elif status in ['CANCELLED', 'AUTO_CANCELLED_WL']:
        return {'text': 'CANCELLED', 'badge': 'bg-secondary', 'code': 'CAN'}
    return {'text': status, 'badge': 'bg-info text-dark', 'code': status}

def get_coach_bay_matrix(travel_class, seat_no):
    """
    Generate a structured Visual Coach Bay representation highlighting the passenger's seat.
    - 3AC / SL: 8-berth bay (1: Lower, 2: Middle, 3: Upper, 4: Lower, 5: Middle, 6: Upper, 7: Side Lower, 8: Side Upper)
    - 2AC: 6-berth bay (1: Lower, 2: Upper, 3: Lower, 4: Upper, 5: Side Lower, 6: Side Upper)
    - CC / 2S: 5-seat row (1: Window, 2: Middle, 3: Aisle, 4: Aisle, 5: Window)
    """
    if not seat_no:
        return None

    if travel_class in ['3A', 'SL']:
        bay_no = ((seat_no - 1) // 8) + 1
        base_seat = (bay_no - 1) * 8
        layout = [
            {'seat_no': base_seat + 1, 'type': 'LB', 'name': 'Lower', 'side': 'main'},
            {'seat_no': base_seat + 2, 'type': 'MB', 'name': 'Middle', 'side': 'main'},
            {'seat_no': base_seat + 3, 'type': 'UB', 'name': 'Upper', 'side': 'main'},
            {'seat_no': base_seat + 4, 'type': 'LB', 'name': 'Lower', 'side': 'main'},
            {'seat_no': base_seat + 5, 'type': 'MB', 'name': 'Middle', 'side': 'main'},
            {'seat_no': base_seat + 6, 'type': 'UB', 'name': 'Upper', 'side': 'main'},
            {'seat_no': base_seat + 7, 'type': 'SL', 'name': 'Side Lower', 'side': 'side'},
            {'seat_no': base_seat + 8, 'type': 'SU', 'name': 'Side Upper', 'side': 'side'},
        ]
    elif travel_class == '2A':
        bay_no = ((seat_no - 1) // 6) + 1
        base_seat = (bay_no - 1) * 6
        layout = [
            {'seat_no': base_seat + 1, 'type': 'LB', 'name': 'Lower', 'side': 'main'},
            {'seat_no': base_seat + 2, 'type': 'UB', 'name': 'Upper', 'side': 'main'},
            {'seat_no': base_seat + 3, 'type': 'LB', 'name': 'Lower', 'side': 'main'},
            {'seat_no': base_seat + 4, 'type': 'UB', 'name': 'Upper', 'side': 'main'},
            {'seat_no': base_seat + 5, 'type': 'SL', 'name': 'Side Lower', 'side': 'side'},
            {'seat_no': base_seat + 6, 'type': 'SU', 'name': 'Side Upper', 'side': 'side'},
        ]
    else:  # CC / 2S / 1A
        bay_no = ((seat_no - 1) // 5) + 1
        base_seat = (bay_no - 1) * 5
        layout = [
            {'seat_no': base_seat + 1, 'type': 'W', 'name': 'Window', 'side': 'left'},
            {'seat_no': base_seat + 2, 'type': 'M', 'name': 'Middle', 'side': 'left'},
            {'seat_no': base_seat + 3, 'type': 'A', 'name': 'Aisle', 'side': 'left'},
            {'seat_no': base_seat + 4, 'type': 'A', 'name': 'Aisle', 'side': 'right'},
            {'seat_no': base_seat + 5, 'type': 'W', 'name': 'Window', 'side': 'right'},
        ]

    for item in layout:
        item['is_allocated'] = (item['seat_no'] == seat_no)

    return {
        'bay_number': bay_no,
        'travel_class': travel_class,
        'allocated_seat_no': seat_no,
        'layout': layout
    }

def get_ticket_summary(booking):
    """Generate printable IRCTC E-Ticket summary dictionary with visual coach bay matrix."""
    train = booking.train
    src_route = None
    dst_route = None
    
    for r in train.routes:
        if r.station_id == booking.from_station_id:
            src_route = r
        elif r.station_id == booking.to_station_id:
            dst_route = r
            
    distance = (dst_route.distance_km - src_route.distance_km) if (src_route and dst_route) else 0.0
    
    passenger_list = []
    for idx, p in enumerate(booking.passengers, start=1):
        b_badge = format_status_badge(p.booking_status.split('/')[0].strip() if '/' in p.booking_status else p.booking_status, p.rac_wl_number)
        c_badge = format_status_badge(p.current_status, p.rac_wl_number)
        
        seat_display = f"{p.coach_no} / {p.seat_no}" if (p.coach_no and p.seat_no) else (p.coach_no or 'N/A')
        coach_bay = get_coach_bay_matrix(booking.travel_class, p.seat_no)
        
        passenger_list.append({
            'sno': idx,
            'name': p.name,
            'age': p.age,
            'gender': p.gender,
            'berth_preference': p.berth_preference,
            'booking_status_text': p.booking_status,
            'booking_badge': b_badge,
            'current_status_text': p.current_status,
            'current_badge': c_badge,
            'seat_display': seat_display,
            'berth_type': p.berth_type or 'N/A',
            'coach_no': p.coach_no,
            'seat_no': p.seat_no,
            'coach_bay': coach_bay,
            'is_cancelled': p.is_cancelled,
            'refund_amount': p.refund_amount
        })

    return {
        'pnr': booking.pnr,
        'booking_id': booking.id,
        'train_number': train.train_number,
        'train_name': train.name,
        'from_station_code': booking.from_station.code,
        'from_station_name': booking.from_station.name,
        'to_station_code': booking.to_station.code,
        'to_station_name': booking.to_station.name,
        'departure_time': src_route.departure_time if src_route else '--:--',
        'arrival_time': dst_route.arrival_time if dst_route else '--:--',
        'journey_date': booking.journey_date.strftime('%d-%b-%Y'),
        'booking_date': booking.booking_time.strftime('%d-%b-%Y %H:%M'),
        'travel_class': booking.travel_class,
        'quota': booking.quota,
        'total_fare': f"₹{booking.total_fare:.2f}",
        'distance_km': distance,
        'passengers': passenger_list,
        'chart_prepared': booking.chart_prepared,
        'status': booking.status
    }
