"""Save complete Prokerala API output to JSON file for inspection."""

import json
from config import PROKERALA_CLIENT_ID, PROKERALA_CLIENT_SECRET, SAMPLE_PERSON
from test_prokerala_api import ProkeralaClient

person = SAMPLE_PERSON
client = ProkeralaClient(PROKERALA_CLIENT_ID, PROKERALA_CLIENT_SECRET)

dt_str = f"{person['date']}T{person['time']}{person['timezone']}"
coords = f"{person['latitude']},{person['longitude']}"

results = {}

# 1. Planet positions
print("Fetching planet positions...")
results['planet_position'] = client.get("v2/astrology/planet-position", {
    "ayanamsa": 1, "coordinates": coords, "datetime": dt_str,
})

# 2. Birth details
print("Fetching birth details...")
results['birth_details'] = client.get("v2/astrology/birth-details", {
    "ayanamsa": 1, "coordinates": coords, "datetime": dt_str,
})

# 3. Kundli
print("Fetching kundli...")
results['kundli'] = client.get("v2/astrology/kundli", {
    "ayanamsa": 1, "coordinates": coords, "datetime": dt_str,
})

# 4. Panchang
print("Fetching panchang...")
try:
    results['panchang'] = client.get("v2/astrology/panchang", {
        "ayanamsa": 1, "coordinates": coords, "datetime": dt_str,
    })
except Exception as e:
    results['panchang'] = f"Error: {e}"

# 5. Mangal Dosha
print("Fetching mangal dosha...")
try:
    results['mangal_dosha'] = client.get("v2/astrology/mangal-dosha", {
        "ayanamsa": 1, "coordinates": coords, "datetime": dt_str,
    })
except Exception as e:
    results['mangal_dosha'] = f"Error: {e}"

# Save everything
output = {
    "person": person,
    "api": "Prokerala Astrology API (v2)",
    "endpoints_tested": list(results.keys()),
    "results": results,
}

with open("prokerala_output_sample.json", "w") as f:
    json.dump(output, f, indent=2, default=str)

print(f"\nAll output saved to: prokerala_output_sample.json")
print(f"Endpoints tested: {list(results.keys())}")
