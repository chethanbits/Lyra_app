"""
Utility functions to parse birth data from the Excel file.

The Excel has Birth_Place like: "Provins, France, 48n33, 3e18"
  - "48n33" means 48 degrees 33 minutes North  -> +48.55
  - "3e18"  means 3 degrees 18 minutes East    -> +3.30
  - "12s03" means 12 degrees 3 minutes South   -> -12.05
  - "77w03" means 77 degrees 3 minutes West    -> -77.05
"""

import re
import openpyxl
from datetime import datetime


def parse_dms_coordinate(coord_str):
    """
    Parse coordinates like '48n33', '3e18', '12s03', '77w03'
    Returns decimal degrees (positive for N/E, negative for S/W).
    """
    coord_str = coord_str.strip()
    match = re.match(r'(\d+)([nsewNSEW])(\d+)', coord_str)
    if not match:
        return None
    
    degrees = int(match.group(1))
    direction = match.group(2).lower()
    minutes = int(match.group(3))
    
    decimal = degrees + minutes / 60.0
    
    if direction in ('s', 'w'):
        decimal = -decimal
    
    return round(decimal, 4)


def parse_birth_place(birth_place_str):
    """
    Parse Birth_Place field like "Provins, France, 48n33, 3e18"
    Returns: (place_name, latitude, longitude) or (place_name, None, None)
    """
    if not birth_place_str:
        return ("Unknown", None, None)
    
    parts = [p.strip() for p in birth_place_str.split(',')]
    
    lat = None
    lon = None
    place_parts = []
    
    for part in parts:
        coord = parse_dms_coordinate(part)
        if coord is not None:
            if lat is None:
                lat = coord
            else:
                lon = coord
        else:
            place_parts.append(part)
    
    place_name = ', '.join(place_parts) if place_parts else "Unknown"
    return (place_name, lat, lon)


def parse_birth_date(date_str):
    """Parse DD-MM-YYYY to datetime.date"""
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str).strip(), "%d-%m-%Y").date()
    except ValueError:
        return None


def parse_birth_time(time_str):
    """Parse HH:MM to (hour, minute, second)"""
    if not time_str:
        return (12, 0, 0)  # default noon if unknown
    
    parts = str(time_str).strip().split(':')
    hour = int(parts[0]) if len(parts) > 0 else 12
    minute = int(parts[1]) if len(parts) > 1 else 0
    second = int(parts[2]) if len(parts) > 2 else 0
    return (hour, minute, second)


def load_sample_people(excel_path, sheet_name='Individuals_Sample', count=5):
    """
    Load a few sample people from the Excel file.
    Returns list of dicts with parsed birth data.
    """
    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    ws = wb[sheet_name]
    
    headers = None
    people = []
    
    for row_num, row in enumerate(ws.iter_rows(values_only=True), 1):
        if row_num == 1:
            headers = list(row)
            continue
        
        if len(people) >= count:
            break
        
        record = dict(zip(headers, row))
        
        # Parse the fields we need
        birth_date = parse_birth_date(record.get('Birth_Date'))
        hour, minute, second = parse_birth_time(record.get('Birth_Time'))
        place_name, lat, lon = parse_birth_place(record.get('Birth_Place'))
        
        if birth_date and lat is not None and lon is not None:
            people.append({
                'id': record.get('Individual_ID'),
                'name': record.get('Corrected_Full_Name', 'Unknown'),
                'gender': record.get('Gender', 'Unknown'),
                'birth_date': birth_date,
                'birth_hour': hour,
                'birth_minute': minute,
                'birth_second': second,
                'latitude': lat,
                'longitude': lon,
                'place': place_name,
                'country': record.get('Country', ''),
                # ISO datetime string for API calls
                'datetime_iso': f"{birth_date.isoformat()}T{hour:02d}:{minute:02d}:{second:02d}+00:00",
                'coordinates': f"{lat},{lon}",
            })
    
    wb.close()
    return people


if __name__ == "__main__":
    from config import EXCEL_PATH
    
    print("=" * 60)
    print("Testing coordinate parser:")
    print(f"  48n33 -> {parse_dms_coordinate('48n33')}")   # 48.55
    print(f"  3e18  -> {parse_dms_coordinate('3e18')}")    # 3.3
    print(f"  12s03 -> {parse_dms_coordinate('12s03')}")   # -12.05
    print(f"  77w03 -> {parse_dms_coordinate('77w03')}")   # -77.05
    
    print("\n" + "=" * 60)
    print("Testing birth place parser:")
    place, lat, lon = parse_birth_place("Provins, France, 48n33,  3e18")
    print(f"  Place: {place}, Lat: {lat}, Lon: {lon}")
    
    print("\n" + "=" * 60)
    print(f"Loading 5 sample people from Excel...")
    people = load_sample_people(EXCEL_PATH, count=5)
    for p in people:
        print(f"\n  {p['name']} ({p['gender']})")
        print(f"    Born: {p['birth_date']} at {p['birth_hour']:02d}:{p['birth_minute']:02d}")
        print(f"    Place: {p['place']} (lat={p['latitude']}, lon={p['longitude']})")
        print(f"    ISO datetime: {p['datetime_iso']}")
        print(f"    Coordinates: {p['coordinates']}")
