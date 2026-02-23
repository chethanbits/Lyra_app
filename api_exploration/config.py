"""
Configuration for Astrology API exploration.

PROKERALA API:
  - Sign up FREE at https://api.prokerala.com/login
  - Free plan: 5,000 credits/month, 5 requests/min
  - After login, go to Dashboard > Client Details to get Client ID and Secret
  - Put them below or set as environment variables

VEDICASTRO & PYJHORA:
  - These are FREE open-source Python packages
  - No API keys needed - they run locally using Swiss Ephemeris
"""

import os

# ============================================================
# PROKERALA API CREDENTIALS (Free tier: 5000 credits/month)
# ============================================================
# Option 1: Set environment variables PROKERALA_CLIENT_ID and PROKERALA_CLIENT_SECRET
# Option 2: Paste them directly below (don't commit to git!)
PROKERALA_CLIENT_ID = os.environ.get("PROKERALA_CLIENT_ID", "51029016-7922-431c-9a9c-eb639b20dff5")
PROKERALA_CLIENT_SECRET = os.environ.get("PROKERALA_CLIENT_SECRET", "9JKxtfB10bgZFgqzasjc4lAzGUvRwnUnlCSZBRNf")

PROKERALA_BASE_URL = "https://api.prokerala.com/"
PROKERALA_TOKEN_URL = "https://api.prokerala.com/token"

# ============================================================
# SAMPLE BIRTH DATA (from your Excel - used for testing)
# ============================================================
SAMPLE_PERSON = {
    "name": "Dominique Ane",
    "date": "1968-10-06",       # YYYY-MM-DD
    "time": "05:35:00",         # HH:MM:SS
    "latitude": 48.55,          # 48n33 = 48 + 33/60 = 48.55
    "longitude": 3.30,          # 3e18 = 3 + 18/60 = 3.30
    "timezone": "+01:00",       # France timezone (CET)
    "place": "Provins, France",
}

# Path to your Excel data
EXCEL_PATH = r"c:\Users\91866\Desktop\prokeralaandvedic\astro_excel_data 05-02-2026_BACKUP.xlsx"
