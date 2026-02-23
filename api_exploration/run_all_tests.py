"""
MASTER TEST SCRIPT - Run all 3 astrology API/package tests
============================================================

This script tests all 3 options side by side:
  1. Prokerala API (cloud, free tier 5000 credits/month)
  2. VedicAstro   (local, free, open source)
  3. PyJHora      (local, free, open source)

All 3 are given the SAME birth data and we compare what they return.

Run:  python run_all_tests.py
"""

import sys
import json
import traceback
from datetime import datetime


def separator(title):
    print("\n")
    print("#" * 70)
    print(f"#  {title}")
    print("#" * 70)


def main():
    print("=" * 70)
    print("  ASTROLOGY API EXPLORATION - COMPARISON OF ALL 3 OPTIONS")
    print("=" * 70)
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    from config import SAMPLE_PERSON
    person = SAMPLE_PERSON
    print(f"\n  Test Person: {person['name']}")
    print(f"  Born: {person['date']} at {person['time']}")
    print(f"  Place: {person['place']} ({person['latitude']}, {person['longitude']})")
    
    results = {}
    
    # ============================================================
    # TEST 1: Prokerala API
    # ============================================================
    separator("TEST 1: PROKERALA API (Cloud - Free Tier)")
    try:
        from test_prokerala_api import ProkeralaClient, test_planet_position
        from config import PROKERALA_CLIENT_ID, PROKERALA_CLIENT_SECRET
        
        if PROKERALA_CLIENT_ID == "YOUR_CLIENT_ID_HERE":
            print("\n  [SKIPPED] Prokerala credentials not set.")
            print("  To enable: sign up at https://api.prokerala.com/login")
            print("  Then set Client ID/Secret in config.py")
            results['prokerala'] = "SKIPPED - credentials not set"
        else:
            client = ProkeralaClient(PROKERALA_CLIENT_ID, PROKERALA_CLIENT_SECRET)
            prokerala_result = test_planet_position(client, person)
            results['prokerala'] = "SUCCESS"
            print("\n  [OK] Prokerala API working!")
    except Exception as e:
        results['prokerala'] = f"ERROR: {e}"
        print(f"\n  [FAIL] Prokerala: {e}")
    
    # ============================================================
    # TEST 2: VedicAstro (Local)
    # ============================================================
    separator("TEST 2: VEDICASTRO (Local - Free)")
    try:
        from test_vedicastro import test_vedicastro
        vedicastro_result = test_vedicastro()
        if vedicastro_result:
            results['vedicastro'] = "SUCCESS"
            print("\n  [OK] VedicAstro working!")
        else:
            results['vedicastro'] = "NOT INSTALLED"
    except Exception as e:
        results['vedicastro'] = f"ERROR: {e}"
        print(f"\n  [FAIL] VedicAstro: {e}")
        traceback.print_exc()
    
    # ============================================================
    # TEST 3: PyJHora (Local)
    # ============================================================
    separator("TEST 3: PYJHORA (Local - Free)")
    try:
        from test_pyjhora import test_pyjhora_basic
        pyjhora_result = test_pyjhora_basic()
        if pyjhora_result:
            results['pyjhora'] = "SUCCESS"
            print("\n  [OK] PyJHora working!")
        else:
            results['pyjhora'] = "NOT INSTALLED"
    except Exception as e:
        results['pyjhora'] = f"ERROR: {e}"
        print(f"\n  [FAIL] PyJHora: {e}")
        traceback.print_exc()
    
    # ============================================================
    # SUMMARY
    # ============================================================
    separator("SUMMARY")
    
    print("""
    +------------------+----------+--------+------------------------------------------+
    | Option           | Status   | Cost   | Notes                                    |
    +------------------+----------+--------+------------------------------------------+""")
    
    for name, status in results.items():
        if name == 'prokerala':
            cost = "Free*"
            notes = "Cloud API, 5000 credits/mo free tier"
        elif name == 'vedicastro':
            cost = "Free"
            notes = "Local, KP system focused"
        else:
            cost = "Free"
            notes = "Local, most comprehensive"
        
        status_short = "OK" if status == "SUCCESS" else ("SKIP" if "SKIP" in str(status) else "FAIL")
        print(f"    | {name:16s} | {status_short:8s} | {cost:6s} | {notes:40s} |")
    
    print("    +------------------+----------+--------+------------------------------------------+")
    
    print("""
    RECOMMENDATION FOR CHETHAN'S REQUIREMENT:
    ==========================================
    "Pass date/time/location -> generate planetary positions for 28 years"
    
    Best option: PyJHora (FREE, local, most comprehensive)
    - Can calculate planet positions for ANY date/time/place
    - Supports all major Vedic astrology calculations
    - No API costs, no rate limits
    - Can process all your Excel data locally
    - Can be wrapped into a FastAPI service easily
    
    Prokerala API is useful for:
    - Quick validation/cross-checking of results
    - Getting formatted kundli charts
    - If you need features PyJHora doesn't have
    
    VedicAstro is useful for:
    - KP (Krishnamurti Paddhati) specific calculations
    - Already has a FastAPI wrapper built in
    - Simpler API than PyJHora
    """)


if __name__ == "__main__":
    main()
