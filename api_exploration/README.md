# Astrology API Exploration

Testing 3 options for generating planetary positions from birth data (date/time/location).

## The 3 Options

| Option | Type | Cost | Best For |
|--------|------|------|----------|
| **Prokerala API** | Cloud API | Free tier (5000 credits/mo) | Quick results, formatted charts, kundli matching |
| **VedicAstro** | Local Python pkg | 100% Free | KP system, simple API, FastAPI wrapper included |
| **PyJHora** | Local Python pkg | 100% Free | Most comprehensive, 200+ yogas, all dasha systems |

## Quick Setup

```bash
# 1. Create virtual environment
cd api_exploration
python -m venv venv
venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install flatlib sidereal branch (needed by VedicAstro)
pip install git+https://github.com/diliprk/flatlib.git@sidereal#egg=flatlib

# 4. (Optional) Set Prokerala credentials for cloud API testing
#    Sign up FREE at https://api.prokerala.com/login
#    Then edit config.py with your Client ID and Secret

# 5. Run all tests
python run_all_tests.py
```

## Individual Test Scripts

```bash
python utils.py                  # Test Excel data parsing
python test_prokerala_api.py     # Test Prokerala cloud API
python test_vedicastro.py        # Test VedicAstro local package
python test_pyjhora.py           # Test PyJHora local package
python run_all_tests.py          # Run all 3 and compare
```

## What Each Returns

### Prokerala API
- Planet positions (longitude, sign, nakshatra)
- Birth details (tithi, yoga, karana)
- Kundli chart data
- Dasha periods
- Dosha checks (Manglik, Kaal Sarp)

### VedicAstro
- Planet positions with KP sublords
- House cusps
- ABCD significators (planet-wise and house-wise)
- Vimshottari Dasha
- Planetary aspects

### PyJHora (Most Comprehensive)
- Planet positions for ANY date/time/place
- All divisional charts (D-1 through D-300)
- 22+ graha dasha types
- 22+ raasi dasha types
- 200+ yoga calculations
- Ashtakavarga
- Shadbala (planet strengths)
- Panchang data
- **Can generate 28-year planetary positions** (Chethan's requirement)

## File Structure

```
api_exploration/
  config.py              - API keys, sample data, settings
  utils.py               - Excel parser, coordinate converter
  requirements.txt       - Python dependencies
  test_prokerala_api.py  - Prokerala cloud API test
  test_vedicastro.py     - VedicAstro local test
  test_pyjhora.py        - PyJHora local test (+ 28-year generator)
  run_all_tests.py       - Compare all 3 side by side
  README.md              - This file
```

## Prokerala API Setup (Free Tier)

1. Go to https://api.prokerala.com/login
2. Create a free account
3. Go to Dashboard > Applications > Create New Application
4. Copy Client ID and Client Secret
5. Edit `config.py` and paste them in
6. Free plan: 5000 credits/month, 5 API calls/minute

## Next Steps

1. Run the tests to see what each option returns
2. Decide which option (or combination) fits the project needs
3. For Chethan's "28-year planetary positions" requirement -> PyJHora is the best fit
4. Can wrap PyJHora into a FastAPI service for team use
