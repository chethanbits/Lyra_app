# Lyra – Align Your Day

**Mobile app** (iOS & Android), built with React and packaged for the app stores. UI follows the Figma design; flow: Welcome → Choose Your Experience → (General → Home | Personal → Birth Details → Home). Uses the **PyJHora wrapper API** in `api_exploration/` for all astrology data.

During development the app runs in the browser (or in device simulators once Capacitor is set up).

## Theme

- **Default**: Light ivory background, deep midnight blue accents
- **Colors**: Emerald (favorable), amber (neutral), muted red (caution)
- **Typography**: DM Sans, clean and minimal

## Run the app

1. **Start the wrapper (API)** first:
   ```bash
   cd api_exploration
   .\venv\Scripts\activate
   uvicorn pyjhora_api:app --port 8000
   ```

2. **Start Lyra** (from repo root):
   ```bash
   cd lyra_app
   npm install
   npm run dev
   ```

3. Open **http://localhost:5173** → Welcome screen. Click "Explore Lyra (Guest Mode)" to go to Home. Home fetches Panchang from the API and shows Alignment Score + grid.

## Screens

- **Welcome** – Lyra branding. "Explore Lyra (Guest Mode)" → Choose Your Experience; "Create Your Lyra" → Registration.
- **Choose Your Experience** – General Mode (location-based) → Home; Personal Mode → Birth Details.
- **Birth Details** – Birth date, time (optional), place. Save & Continue → Home.
- **Registration** – Placeholder (email/password flow to be added).
- **Home** – Date, Alignment Score, breakdown chips, Panchang grid (Tithi, Nakshatra, Rahu Kalam, Sunrise, Sunset), Plan Event / 30-Day Outlook
- **Planner** – Event category (Marriage, Travel, etc.), date range (30/60/Custom)
- **Calendar** – Month grid, color legend (placeholder for API-driven heatmap)
- **Settings** – Theme (Light/Dark), Location, Calculation (Ayanamsa, Month type), Notifications

## API (wrapper)

Lyra calls these endpoints from `api_exploration` (PyJHora):

- `GET /panchang-detailed` – Sunrise/Sunset, Moonrise/Moonset, Tithi, Nakshatra, Vaara, Rahu Kaal, Month, Season, Samvatsara
- `GET /planet-positions` – For birth chart / personalization (future)
- `GET /geocode?city=...` – Birth place (future)
- `GET /transits` – For planner best-dates (future)

Set `VITE_API_URL` in `.env` if the API is not on `http://localhost:8000`.

**Port:** Dev server runs on **5173** (Vite default). If you get `EACCES` on another port, use `npm run dev` and open http://localhost:5173.

---

## Testing at a fixed mobile size (like Figma)

- **Design reference:** The **Lyra Mobile App Design** folder uses a mobile breakpoint of **768px**; layout is built for phone-first.
- **Recommended viewport for development:** Use one of these so your localhost matches Figma / real devices:
  - **390×844** – iPhone 14 / 14 Pro (common Figma artboard)
  - **375×667** – iPhone SE / 8 (narrower)
  - **375×812** – iPhone X / 11 / 12 mini

**Option A – Browser DevTools (recommended)**  
1. Open http://localhost:5173  
2. F12 → toggle device toolbar (Ctrl+Shift+M / Cmd+Shift+M)  
3. Pick “iPhone 14 Pro” or set custom size **390×844**

**Option B – Lock the app width on desktop**  
Add the class `mobile-frame` to `<body>` in `index.html`. The app will render in a **390px**-wide column in the center of the screen, so you always see the same layout as on a phone without resizing the window.

---

## Android simulator (Windows)

**Full steps:** see **[ANDROID.md](ANDROID.md)** for installing Android Studio, creating an AVD, running the API, building with `VITE_API_URL=http://10.0.2.2:8000`, and running the app in the emulator.

Lyra is a **mobile app**; to run it in device simulators you need:

1. **Capacitor** (to wrap the built app for iOS/Android) – to be added when we’re ready to run in simulators.
2. **iOS:** Xcode (Mac only) → **Xcode → Open Developer Tool → Simulator**. After adding Capacitor: `npx cap open ios` to open the project in Xcode and run on a simulated iPhone.
3. **Android:** Android Studio → **Device Manager** → create a virtual device (e.g. Pixel 6). After adding Capacitor: `npx cap open android` to open in Android Studio and run on the emulator.

Until simulators are set up, we develop and test in the **browser** with Chrome DevTools device mode (e.g. 390×844) or on a **real phone** at `http://<your-PC-IP>:5173` on the same Wi‑Fi.

**Reply you can give your boss:**  
“We’re building a mobile app (React, to be packaged with Capacitor for iOS/Android). I don’t have the simulator setup yet — I’ve been testing in the browser with device emulation. I’ll set up Xcode Simulator (iOS) and/or Android Studio emulator (Android) and add Capacitor so we can run and test the app in simulators.”
