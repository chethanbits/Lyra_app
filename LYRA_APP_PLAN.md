# Lyra App – What to Do (from Figma base)

## Goal
- **App**: Lyra – Align Your Day (from Figma design + chat spec)
- **Wrapper**: PyJHora API in `api_exploration/` (already built)
- **End state**: Both the app and the wrapper live in this repo (“in the library”)

## What You Have
1. **Figma access** – Lyra design (Welcome, Registration, Home, Planner, Calendar, Settings, etc.)
2. **Wrapper (API)** – `api_exploration/` with:
   - `/panchang-detailed` – Sunrise/Sunset, Moonrise/Moonset, Tithi, Nakshatra, Vaara, Rahu Kaal, Month, Season, Samvatsara
   - `/planet-positions` – Planets + house numbers for birth details
   - `/dasha` – Vimshottari Mahadasha + Antardasha
   - `/transits` – Yearly sign transitions
   - `/geocode` – City → lat/lon/timezone
3. **Simple demo** – `horoscope_app/` (panchang + North/South charts)

## What to Do (Steps)

### 1. Use Figma as the visual base
- Open the Lyra file in Figma; use it for layout, colors, typography, and components.
- No need to use Figma Make’s generated code unless you prefer it; we can build the app in code to match the design.

### 2. Build the Lyra app in this repo
- Create a **Lyra app** (e.g. `lyra_app/`) that implements all screens from the Figma + chat spec.
- Tech choice: **React (Vite)** for a web app that works on mobile (responsive/PWA), or **React Native** if you need a native mobile app. Recommended: React (Vite) first for speed and reuse of the same API.

### 3. Connect the app to the wrapper
- All astrology data comes from **one place**: the PyJHora API in `api_exploration/`.
- Lyra app calls:
  - `GET /panchang-detailed` for daily Panchang (Tithi, Nakshatra, Rahu Kaal, etc.).
  - `GET /planet-positions` for birth chart / alignment logic.
  - `GET /geocode?city=...` for birth place.
  - Later: `/dasha`, `/transits` for planner and advanced features.
- Run API: `cd api_exploration && uvicorn pyjhora_api:app --port 8000`.

### 4. Implement the flow (from Figma + chat)
- Welcome → Onboarding (optional) → Registration / Login → Personalization (General vs Personal) → Birth Details (if Personal) → **Home**.
- Home: date (Gregorian + Hindu), location, **Alignment Score**, breakdown chips (Tithi, Nakshatra, Yoga, Rahu), Panchang grid, sunrise–sunset timeline, “Plan Event”, “30-Day Outlook”.
- Day Details: full Panchang, expandable sections, timeline.
- Planner: event type (Marriage, Travel, etc.), date range → **Planner Results** (ranked dates from API/transits).
- Calendar: month grid, color-coded days, festivals, heatmap.
- Settings: location, personalization, calculation (Ayanamsa, month type), notifications, **theme (Light/Dark)**.
- Also: loading state, error state, guest vs logged-in indicator.

### 5. Keep design consistent with Figma
- **Theme**: Constellation-inspired, calm, premium.
- **Default**: Light ivory background, deep midnight blue accents.
- **Colors**: Emerald (favorable), amber (neutral), muted red (caution).
- **UI**: Clean sans-serif, generous whitespace, no clutter, no religious ornamentation.

### 6. “App + wrapper in the library”
- **Wrapper**: `api_exploration/` (PyJHora API) = the library backend.
- **App**: `lyra_app/` = the Lyra frontend that uses the wrapper.
- Both in the same repo; deploy API and app separately (e.g. API on a server, app on Vercel/Netlify or app store).

## Next Step
Scaffold the Lyra app in `lyra_app/` (React + Vite), add the main screens and bottom nav, and wire Home to `/panchang-detailed` and `/planet-positions` so the dashboard shows real data from the wrapper.
