# Prokerala / Vedic Astrology – App & Wrapper

This repo contains **the app** and **the wrapper** in one place (“the library”).

## Contents

| Folder | Description |
|--------|-------------|
| **api_exploration/** | **Wrapper** – PyJHora as a REST API (FastAPI). Panchang, planet positions, dasha, transits, geocode. Run with `uvicorn pyjhora_api:app --port 8000`. |
| **lyra_app/** | **Lyra – Align Your Day** – React (Vite) app from Figma design. Daily dashboard, planner, calendar, settings. Uses the wrapper for all astrology data. |
| **horoscope_app/** | Simple demo: panchang + North/South Indian horoscope charts (HTML, served by the API at `/app`). |

## Quick start

1. **Start the wrapper**
   ```bash
   cd api_exploration
   .\venv\Scripts\activate   # Windows
   uvicorn pyjhora_api:app --port 8000
   ```

2. **Start Lyra**
   ```bash
   cd lyra_app
   npm install
   npm run dev
   ```
   Open http://localhost:5173

3. **Optional**: Open http://localhost:8000/app for the simple horoscope chart demo.

## Wrapper API (api_exploration)

- `GET /` or `/app` – Horoscope app or API info
- `GET /docs` – Swagger UI
- `GET /geocode?city=...` – City → lat, lon, timezone
- `GET /panchang-detailed` – Sunrise/Sunset, Moonrise/Moonset, Tithi, Nakshatra, Vaara, Rahu Kaal, Month, Season, Samvatsara
- `GET /planet-positions` – Planet positions + house numbers (1–12)
- `GET /dasha` – Vimshottari Mahadasha + Antardasha (120 years)
- `GET /transits?year=...` – Planetary sign transitions for a year
- `GET /positions-28-years` – 28-year positions from DOB

All endpoints take date/time/location (year, month, day, hour, minute, lat, lon, tz) as needed.

## Deploy (free: Vercel + Render)

To get a live link for the app (e.g. for your boss to open in the browser): deploy the **app** to **Vercel** and the **API** to **Render**. Both are free. Step-by-step: **[DEPLOY.md](DEPLOY.md)**.

## Design base

Lyra’s design follows the Figma file “Lyra – Align Your Day”: constellation-inspired, light ivory + midnight blue, emerald/amber/muted red, minimal layout. See `LYRA_APP_PLAN.md` for implementation notes.
