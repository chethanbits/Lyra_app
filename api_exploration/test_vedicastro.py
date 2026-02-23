"""
TEST 2: VedicAstro - Open Source Vedic Astrology Package (FREE, runs locally)
==============================================================================

What it is:
  - Free, open-source Python package (MIT license)
  - Runs 100% locally using Swiss Ephemeris (pyswisseph)
  - Focused on Krishnamurti Paddhati (KP) system
  - Has a built-in FastAPI wrapper for API usage
  - No API keys, no internet, no cost per call!

What it returns:
  - Planet positions (longitude, sign, nakshatra, sublord)
  - House cusps and positions
  - Planet-wise and House-wise significators (ABCD)
  - Vimshottari Dasha periods
  - Planetary aspects (trine, sextile, square, conjunction)
  - Consolidated chart data

Install:
  pip install vedicastro
  pip install git+https://github.com/diliprk/flatlib.git@sidereal#egg=flatlib
"""

import json
import sys
import traceback

from config import SAMPLE_PERSON


def test_vedicastro():
    """Test VedicAstro package with sample birth data."""
    
    print("=" * 60)
    print("  VEDICASTRO - LOCAL VEDIC ASTROLOGY ENGINE")
    print("  Free, open-source, runs locally")
    print("=" * 60)
    
    try:
        from vedicastro import VedicAstro
    except ImportError as e:
        print(f"\n[!] VedicAstro not installed: {e}")
        print("    Install with:")
        print("      pip install vedicastro")
        print("      pip install git+https://github.com/diliprk/flatlib.git@sidereal#egg=flatlib")
        return None
    
    person = SAMPLE_PERSON
    print(f"\nPerson: {person['name']}")
    print(f"Born: {person['date']} at {person['time']}")
    print(f"Place: {person['place']} ({person['latitude']}, {person['longitude']})")
    
    # Parse date and time
    date_parts = person['date'].split('-')
    year, month, day = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
    time_parts = person['time'].split(':')
    hour, minute, second = int(time_parts[0]), int(time_parts[1]), int(time_parts[2])
    
    # Create horoscope object
    # VedicHoroscopeData(year, month, day, hour, minute, second, lat, lon, utc, ayanamsa, house_system)
    horoscope = VedicAstro.VedicHoroscopeData(
        year, month, day,
        hour, minute, second,
        person['latitude'], person['longitude'],
        person['timezone'],       # UTC offset like "+01:00"
        "Lahiri",                 # Ayanamsa
        "Equal"                   # House system
    )
    
    # Generate chart
    chart = horoscope.generate_chart()
    
    # ---- 1. PLANET POSITIONS ----
    print("\n" + "=" * 60)
    print("1. PLANET POSITIONS")
    print("=" * 60)
    planets_data = horoscope.get_planets_data_from_chart(chart)
    for planet in planets_data:
        p = planet._asdict()
        print(f"  {p.get('Object', p.get('object', 'N/A')):12s} | "
              f"Sign: {str(p.get('Sign', p.get('sign', 'N/A'))):12s} | "
              f"Long: {str(p.get('LonDecDeg', p.get('lon_dec_deg', 'N/A'))):>10s}")
    
    # ---- 2. HOUSE POSITIONS ----
    print("\n" + "=" * 60)
    print("2. HOUSE CUSPS")
    print("=" * 60)
    houses_data = horoscope.get_houses_data_from_chart(chart)
    for house in houses_data:
        h = house._asdict()
        print(f"  House {str(h.get('House', h.get('house', 'N/A'))):>3s} | "
              f"Sign: {str(h.get('Sign', h.get('sign', 'N/A'))):12s} | "
              f"Long: {str(h.get('LonDecDeg', h.get('lon_dec_deg', 'N/A'))):>10s}")
    
    # ---- 3. PLANET SIGNIFICATORS ----
    print("\n" + "=" * 60)
    print("3. PLANET-WISE SIGNIFICATORS (KP System)")
    print("=" * 60)
    planet_sigs = horoscope.get_planet_wise_significators(planets_data, houses_data)
    if isinstance(planet_sigs, list):
        for sig in planet_sigs[:5]:  # show first 5
            print(f"  {sig}")
    elif isinstance(planet_sigs, dict):
        for key, val in list(planet_sigs.items())[:5]:
            print(f"  {key}: {val}")
    else:
        print(f"  {str(planet_sigs)[:500]}")
    
    # ---- 4. VIMSHOTTARI DASHA ----
    print("\n" + "=" * 60)
    print("4. VIMSHOTTARI DASHA PERIODS")
    print("=" * 60)
    dasha = horoscope.compute_vimshottari_dasa(chart)
    if isinstance(dasha, list):
        for d in dasha[:10]:  # show first 10 periods
            print(f"  {d}")
    elif isinstance(dasha, dict):
        for key, val in list(dasha.items())[:10]:
            print(f"  {key}: {val}")
    else:
        print(f"  {str(dasha)[:1000]}")
    
    # ---- 5. PLANETARY ASPECTS ----
    print("\n" + "=" * 60)
    print("5. PLANETARY ASPECTS")
    print("=" * 60)
    aspects = horoscope.get_planetary_aspects(chart)
    if isinstance(aspects, list):
        for a in aspects[:10]:
            print(f"  {a}")
    elif isinstance(aspects, dict):
        for key, val in list(aspects.items())[:10]:
            print(f"  {key}: {val}")
    else:
        print(f"  {str(aspects)[:1000]}")
    
    # ---- 6. SAVE ALL OUTPUT TO JSON ----
    print("\n" + "=" * 60)
    print("6. SAVING ALL OUTPUT TO JSON FILE")
    print("=" * 60)
    
    # Try consolidated, but it may fail on some versions
    consolidated = None
    try:
        consolidated = horoscope.get_consolidated_chart_data(
            planets_data=planets_data,
            houses_data=houses_data,
            return_style=None
        )
    except Exception as e:
        print(f"  (consolidated chart had a library bug: {e})")
        print(f"  (this is fine - we already got all the data above)")
    
    # Save full output to file
    output = {
        "person": person,
        "planets_data": [p._asdict() for p in planets_data],
        "houses_data": [h._asdict() for h in houses_data],
        "dasha": dasha,
        "aspects": aspects,
    }
    if consolidated:
        output["consolidated"] = consolidated
    
    with open("vedicastro_output_sample.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    print("  Full output saved to: vedicastro_output_sample.json")
    
    # Print a nice summary
    print("\n" + "=" * 60)
    print("SUMMARY OF WHAT VEDICASTRO RETURNED:")
    print("=" * 60)
    print(f"  Planets:       {len(planets_data)} objects with longitude, sign, nakshatra, sublord")
    print(f"  Houses:        {len(houses_data)} house cusps with longitudes")
    print(f"  Significators: KP system ABCD significators per planet")
    print(f"  Dasha:         Vimshottari dasha with start/end dates + bhuktis")
    print(f"  Aspects:       Planetary aspects (conjunction, opposition, trine, etc.)")
    
    return {
        "planets_data": planets_data,
        "houses_data": houses_data,
        "dasha": dasha,
        "aspects": aspects,
    }


if __name__ == "__main__":
    try:
        result = test_vedicastro()
        if result:
            print("\n" + "=" * 60)
            print("VEDICASTRO TEST PASSED!")
            print("=" * 60)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        traceback.print_exc()
