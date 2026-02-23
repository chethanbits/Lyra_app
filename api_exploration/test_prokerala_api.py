"""
TEST 1: Prokerala Astrology API (Cloud-based, Free tier available)
==================================================================

What it is:
  - Cloud API by Prokerala.com (commercial service)
  - FREE plan: 5,000 credits/month, 5 requests/min
  - Uses OAuth2 client credentials for authentication
  - Returns JSON responses

How to set up:
  1. Go to https://api.prokerala.com/login and create a FREE account
  2. Go to Dashboard > Applications > Create New
  3. Copy the Client ID and Client Secret
  4. Put them in config.py or set environment variables:
       set PROKERALA_CLIENT_ID=your_id
       set PROKERALA_CLIENT_SECRET=your_secret

Key API endpoints:
  - v2/astrology/kundli              -> Basic kundli/birth chart
  - v2/astrology/kundli/advanced     -> Full kundli with dasha, yoga etc.
  - v2/astrology/planet-position     -> Planet positions (what Chethan wants!)
  - v2/astrology/birth-details       -> Nakshatra, tithi, karana, yoga
  - v2/astrology/mangal-dosha        -> Manglik dosha check
  - v2/astrology/kundli-matching     -> Marriage compatibility
  - v2/astrology/panchang            -> Daily panchang
  - v2/astrology/chart               -> Chart SVG image

Credit costs:  
  - Most endpoints: 2-5 credits per call
  - Advanced kundli: ~50 credits per call
  - With 5000 free credits, you can test ~100-2500 calls/month
"""

import json
import time
import os
import sys

try:
    from urllib.parse import urlencode
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
except ImportError:
    from urllib import urlencode
    from urllib2 import urlopen, Request, HTTPError

from config import (
    PROKERALA_CLIENT_ID, 
    PROKERALA_CLIENT_SECRET,
    PROKERALA_BASE_URL,
    PROKERALA_TOKEN_URL,
    SAMPLE_PERSON,
)


# ============================================================
# Prokerala API Client (adapted from their official example)
# ============================================================

class ProkeralaClient:
    TOKEN_FILE = "./prokerala_token.json"
    
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = PROKERALA_BASE_URL
    
    def _parse_response(self, response):
        """Parse the API response."""
        res = response.read()
        content_type = response.info().get("content-type", "")
        content_type = content_type.split(";", 1)[0]
        
        if content_type == "application/json":
            res = json.loads(res)
        
        status = response.getcode()
        if status == 200:
            return res
        
        # Handle errors
        if isinstance(res, dict) and "errors" in res:
            errors = res["errors"]
            if status == 401 or status == 403:
                raise Exception(f"Authentication error: {errors[0].get('detail', 'Unknown')}")
            elif status == 400:
                raise Exception(f"Validation error: {json.dumps(errors, indent=2)}")
            elif status >= 500:
                raise Exception(f"Server error: {errors[0].get('detail', 'Unknown')}")
        
        raise Exception(f"HTTP {status}: {res}")
    
    def _save_token(self, token):
        with open(self.TOKEN_FILE, "w") as f:
            json.dump({
                "access_token": token["access_token"],
                "expires_at": int(time.time()) + token["expires_in"],
            }, f)
    
    def _get_cached_token(self):
        if not os.path.isfile(self.TOKEN_FILE):
            return None
        try:
            with open(self.TOKEN_FILE, "r") as f:
                token = json.load(f)
            if token["expires_at"] < int(time.time()):
                return None
            return token["access_token"]
        except (ValueError, KeyError):
            return None
    
    def _fetch_new_token(self):
        """Get OAuth2 token using client credentials."""
        data = urlencode({
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }).encode("ascii")
        
        request = Request(self.base_url + "token", data)
        try:
            response = urlopen(request)
            token = self._parse_response(response)
            self._save_token(token)
            return token["access_token"]
        except HTTPError as e:
            error_body = e.read().decode()
            raise Exception(f"Token request failed (HTTP {e.code}): {error_body}")
    
    def get(self, endpoint, params):
        """Make authenticated GET request to Prokerala API."""
        token = self._get_cached_token()
        if not token:
            token = self._fetch_new_token()
        
        query_string = urlencode(params)
        uri = f"{self.base_url}{endpoint}?{query_string}"
        request = Request(uri, headers={"Authorization": f"Bearer {token}"})
        
        try:
            response = urlopen(request)
            return self._parse_response(response)
        except HTTPError as e:
            error_body = e.read().decode()
            raise Exception(f"API request failed (HTTP {e.code}): {error_body}")


# ============================================================
# Test Functions
# ============================================================

def test_planet_position(client, person):
    """Test: Get planet positions for a birth chart."""
    print("\n" + "=" * 60)
    print("ENDPOINT: v2/astrology/planet-position")
    print("PURPOSE:  Get positions of all planets at birth time")
    print("=" * 60)
    
    result = client.get("v2/astrology/planet-position", {
        "ayanamsa": 1,  # 1 = Lahiri
        "coordinates": f"{person['latitude']},{person['longitude']}",
        "datetime": f"{person['date']}T{person['time']}{person['timezone']}",
    })
    
    print(f"\nPerson: {person['name']}")
    print(f"Birth:  {person['date']} {person['time']} at {person['place']}")
    print(f"\nRESPONSE (planet positions):")
    print(json.dumps(result, indent=2, default=str)[:3000])
    return result


def test_kundli(client, person):
    """Test: Get basic kundli/birth chart."""
    print("\n" + "=" * 60)
    print("ENDPOINT: v2/astrology/kundli")
    print("PURPOSE:  Get basic kundli (birth chart, houses, planets)")
    print("=" * 60)
    
    result = client.get("v2/astrology/kundli", {
        "ayanamsa": 1,
        "coordinates": f"{person['latitude']},{person['longitude']}",
        "datetime": f"{person['date']}T{person['time']}{person['timezone']}",
    })
    
    print(f"\nPerson: {person['name']}")
    print(f"\nRESPONSE (kundli):")
    print(json.dumps(result, indent=2, default=str)[:3000])
    return result


def test_birth_details(client, person):
    """Test: Get birth details (nakshatra, tithi, yoga, karana)."""
    print("\n" + "=" * 60)
    print("ENDPOINT: v2/astrology/birth-details")
    print("PURPOSE:  Get nakshatra, tithi, yoga, karana for birth time")
    print("=" * 60)
    
    result = client.get("v2/astrology/birth-details", {
        "ayanamsa": 1,
        "coordinates": f"{person['latitude']},{person['longitude']}",
        "datetime": f"{person['date']}T{person['time']}{person['timezone']}",
    })
    
    print(f"\nPerson: {person['name']}")
    print(f"\nRESPONSE (birth details):")
    print(json.dumps(result, indent=2, default=str)[:3000])
    return result


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  PROKERALA ASTROLOGY API - TEST SCRIPT")
    print("  Free tier: 5000 credits/month")
    print("=" * 60)
    
    # Check if credentials are set
    if PROKERALA_CLIENT_ID == "YOUR_CLIENT_ID_HERE":
        print("\n[!] Prokerala credentials not configured yet!")
        print("    To set up:")
        print("    1. Sign up FREE at https://api.prokerala.com/login")
        print("    2. Create an Application in your dashboard")
        print("    3. Copy Client ID and Secret")
        print("    4. Either:")
        print("       a. Edit config.py and paste them there, OR")
        print("       b. Set environment variables:")
        print("          set PROKERALA_CLIENT_ID=your_id")
        print("          set PROKERALA_CLIENT_SECRET=your_secret")
        print("\n    After setting up, re-run this script.")
        print("\n    NOTE: The Free plan gives 5000 credits/month.")
        print("    Planet position costs ~2 credits per call.")
        sys.exit(0)
    
    person = SAMPLE_PERSON
    client = ProkeralaClient(PROKERALA_CLIENT_ID, PROKERALA_CLIENT_SECRET)
    
    print(f"\nUsing sample person: {person['name']}")
    print(f"Born: {person['date']} at {person['time']}")
    print(f"Place: {person['place']} ({person['latitude']}, {person['longitude']})")
    
    try:
        # Test 1: Planet positions
        test_planet_position(client, person)
        
        # Test 2: Birth details  
        test_birth_details(client, person)
        
        # Test 3: Kundli
        test_kundli(client, person)
        
        print("\n" + "=" * 60)
        print("ALL PROKERALA TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("\nIf authentication failed, double-check your Client ID and Secret.")
