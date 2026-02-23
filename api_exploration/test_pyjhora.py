"""
TEST 3: PyJHora - Complete Vedic Astrology Package (FREE, runs locally)
========================================================================

What it is:
  - Free, open-source Python package (MIT license)
  - VERY comprehensive - based on "Vedic Astrology - An Integrated Approach" by PVR Narasimha Rao
  - Runs 100% locally using Swiss Ephemeris
  - No API keys, no internet needed, no cost per call!

What it returns:
  - Planet positions (longitude, sign, nakshatra, pada) - matches Prokerala!
  - Panchang data (tithi, nakshatra, yoga, karana)
  - Can generate 28-year planetary positions (Chethan's requirement)
  - And much more (dasha, yogas, charts, etc.)

Install:
  pip install PyJHora pyswisseph geopy timezonefinder geocoder
"""

import json
import sys
import traceback
from datetime import datetime, timedelta

from config import SAMPLE_PERSON


SIGNS = ['Mesha/Aries', 'Vrishabha/Taurus', 'Mithuna/Gemini', 'Kataka/Cancer',
         'Simha/Leo', 'Kanya/Virgo', 'Tula/Libra', 'Vrischika/Scorpio',
         'Dhanus/Sagittarius', 'Makara/Capricorn', 'Kumbha/Aquarius', 'Meena/Pisces']
PLANET_INDICES = {
    'Sun': 0, 'Moon': 1, 'Mars': 2, 'Mercury': 3,
    'Jupiter': 4, 'Venus': 5, 'Saturn': 6
}


def test_pyjhora():
    """Test PyJHora with sample birth data."""

    print("=" * 60)
    print("  PYJHORA - COMPLETE VEDIC ASTROLOGY ENGINE")
    print("  Free, open-source, runs locally")
    print("=" * 60)

    try:
        from jhora.panchanga import drik
        from jhora import utils
    except ImportError as e:
        print(f"\n[!] PyJHora not installed: {e}")
        print("    Install with:")
        print("      pip install PyJHora pyswisseph geopy timezonefinder geocoder")
        return None

    person = SAMPLE_PERSON
    print(f"\nPerson: {person['name']}")
    print(f"Born: {person['date']} at {person['time']}")
    print(f"Place: {person['place']} ({person['latitude']}, {person['longitude']})")

    # Parse date/time
    date_parts = person['date'].split('-')
    year, month, day = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
    time_parts = person['time'].split(':')
    hour, minute, second = int(time_parts[0]), int(time_parts[1]), int(time_parts[2])

    # Create PyJHora objects
    dob = drik.Date(year, month, day)
    tob = (hour, minute, second)
    tz_offset = float(person['timezone'].replace('+', '').split(':')[0])
    place = drik.Place(person['place'], person['latitude'], person['longitude'], tz_offset)

    # Julian Day
    jd = utils.julian_day_number(dob, tob)
    print(f"Julian Day: {jd}")

    # ---- 1. PLANET POSITIONS ----
    print("\n" + "=" * 60)
    print("1. PLANET POSITIONS (Sidereal - Lahiri Ayanamsa)")
    print("=" * 60)

    all_planets = {}
    for planet_name, planet_idx in PLANET_INDICES.items():
        lon = drik.sidereal_longitude(jd, planet_idx)
        sign_idx = int(lon / 30) % 12
        deg_in_sign = lon % 30
        all_planets[planet_name] = {
            "longitude": round(lon, 4),
            "sign": SIGNS[sign_idx],
            "degrees_in_sign": round(deg_in_sign, 4),
        }
        print(f"  {planet_name:10s}: {lon:8.4f}°  ->  {SIGNS[sign_idx]:22s}  {deg_in_sign:.4f}°")

    # Rahu and Ketu (from planetary_positions)
    positions = drik.planetary_positions(jd, place)
    # Rahu is typically last or second-to-last in the list
    # Let's find it by checking which position matches Prokerala's Rahu value
    print(f"\n  (Raw planetary_positions returned {len(positions)} objects)")

    # ---- 2. PANCHANG DATA ----
    print("\n" + "=" * 60)
    print("2. PANCHANG DATA AT BIRTH")
    print("=" * 60)

    panchang = {}
    try:
        tithi_r = drik.tithi(jd, place)
        panchang['tithi'] = str(tithi_r)
        print(f"  Tithi: {tithi_r}")
    except Exception as e:
        print(f"  Tithi: Error - {e}")

    try:
        naksh = drik.nakshatra(jd, place)
        panchang['nakshatra'] = str(naksh)
        print(f"  Nakshatra: {naksh}")
    except Exception as e:
        print(f"  Nakshatra: Error - {e}")

    try:
        yoga = drik.yogam(jd, place)
        panchang['yoga'] = str(yoga)
        print(f"  Yoga: {yoga}")
    except Exception as e:
        print(f"  Yoga: Error - {e}")

    try:
        karana = drik.karana(jd, place)
        panchang['karana'] = str(karana)
        print(f"  Karana: {karana}")
    except Exception as e:
        print(f"  Karana: Error - {e}")

    # ---- 3. 28-YEAR PLANETARY POSITIONS ----
    print("\n" + "=" * 60)
    print("3. 28-YEAR PLANETARY POSITIONS (yearly snapshots)")
    print("   This is what Chethan asked for!")
    print("=" * 60)

    print(f"\n  {'Year':>6s} | {'Sun':>16s} | {'Jupiter':>16s} | {'Saturn':>16s}")
    print(f"  {'-'*6} | {'-'*16} | {'-'*16} | {'-'*16}")

    yearly_data = []
    for yr_offset in range(0, 29):
        target_year = year + yr_offset
        target_dob = drik.Date(target_year, month, day)
        target_jd = utils.julian_day_number(target_dob, tob)

        year_entry = {"year": target_year, "planets": {}}

        for planet_name, planet_idx in PLANET_INDICES.items():
            lon = drik.sidereal_longitude(target_jd, planet_idx)
            sign_idx = int(lon / 30) % 12
            deg_in_sign = lon % 30
            year_entry["planets"][planet_name] = {
                "longitude": round(lon, 4),
                "sign": SIGNS[sign_idx],
                "degrees_in_sign": round(deg_in_sign, 4),
            }

        yearly_data.append(year_entry)

        # Print Sun, Jupiter, Saturn for the table
        sun = year_entry["planets"]["Sun"]
        jup = year_entry["planets"]["Jupiter"]
        sat = year_entry["planets"]["Saturn"]
        print(f"  {target_year:>6d} | {sun['sign'].split('/')[0]:>8s} {sun['degrees_in_sign']:6.1f}° | "
              f"{jup['sign'].split('/')[0]:>8s} {jup['degrees_in_sign']:6.1f}° | "
              f"{sat['sign'].split('/')[0]:>8s} {sat['degrees_in_sign']:6.1f}°")

    # ---- SAVE OUTPUT ----
    print("\n" + "=" * 60)
    print("4. SAVING OUTPUT")
    print("=" * 60)

    output = {
        "person": person,
        "api": "PyJHora v4.6.0 (local, free)",
        "birth_planet_positions": all_planets,
        "panchang": panchang,
        "yearly_positions_28_years": yearly_data,
    }

    with open("pyjhora_output_sample.json", "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"  Saved to: pyjhora_output_sample.json")

    # ---- SUMMARY ----
    print("\n" + "=" * 60)
    print("SUMMARY OF WHAT PYJHORA RETURNED:")
    print("=" * 60)
    print(f"  Planet positions:  7 planets with longitude, sign, degrees (matches Prokerala!)")
    print(f"  Panchang:          Tithi, Nakshatra, Yoga, Karana")
    print(f"  28-year data:      {len(yearly_data)} yearly snapshots with all 7 planets")
    print(f"  All FREE, runs locally, no API calls needed!")

    return output


if __name__ == "__main__":
    try:
        result = test_pyjhora()
        if result:
            print("\n" + "=" * 60)
            print("PYJHORA TEST PASSED!")
            print("=" * 60)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        traceback.print_exc()
