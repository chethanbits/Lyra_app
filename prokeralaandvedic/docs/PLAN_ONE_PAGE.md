# Lyra – One-Page Plan (for boss)

## What we’re building

**Lyra – Align Your Day**: production app that gives users a daily alignment score and panchang based on their **location (GPS)** and date. Includes Planner (good/bad times), Calendar, and later: personalities data and analytics charts.

---

## Architecture (end-to-end)

1. **Frontend (Lyra app)** – React app on web (Vercel) and Android (Capacitor). Gets user’s GPS and calls our API.
2. **Backend API** – One Python (FastAPI) service with:
   - **Clear backend processing layer**: Panchang + scoring in a separate module (engine), not mixed with HTTP. Used by a **preload job** and optionally on-demand.
   - **Preloaded fixed data**: We precompute alignment/panchang for a fixed set (e.g. 365 days × 6 cities), store in DB. API **serves from this store**; data **need not be generated every time**.
   - Serves `/day`, `/range`, `/heatmap` for the app; connects to **database** for users, preferences, personalities/analytics, and preloaded alignment data.
3. **Database** – Postgres (e.g. Supabase/Neon) for:
   - Users and preferences (when we add login).
   - Saved places.
   - **Personalities data** (the collected data) and any data needed for **analytics charts**.
4. **No separate “sample” backends in production** – one backend service that does scoring + API + DB.

---

## Build plan (phases)

| Phase | What | Outcome |
|-------|------|--------|
| **1** | Single backend with engine (panchang + scoring), deploy to Render; frontend uses GPS and this API; run 365-day stats and tune weights (Mean 58–62, Std 8–12, Favorable 10–15%, Challenging &lt;7%). | App works end-to-end with real scoring and location. |
| **2** | Add database; tables for users, preferences, personalities; import collected data. | Data in one place for analytics and future features. |
| **3** | Planner and Calendar: real logic (good/bad times, heatmap from API). | Planner and Calendar show real data, not mock. |
| **4** | Auth (sign up / login) if required. | “My account,” saved places, preferences. |
| **5** | Analytics and charts for personalities data; complete “data for chart” as requested. | Boss can prepare charts and analytics. |

---

## Why this is “production” and not just a sample

- **One backend** in production (no duplicate or sample-only APIs).
- **Database** for users, preferences, and personalities/analytics (required for real product and for your charts).
- **Weights and scoring** in one engine + YAML; validated with 365-day stats script.
- **GPS** so panchang is correct for the user’s location.
- **Preloaded fixed data**: Alignment for a fixed set (e.g. 365 days × cities) generated once, stored in DB; API reads from store.
- **Phased plan** so we build in order: backend + deploy → DB + preload → Planner/Calendar → Auth → Analytics/charts.

---

## Updates (boss feedback)

- **Clear backend processing layer** — Panchang + scoring live in a dedicated layer (engine), not mixed with API routes.
- **Preload fixed data** — Data need not be generated every time; we preload and store it; API serves from store.

---

## Where the details live

Full technical architecture, data flow, and checklist: **docs/ARCHITECTURE_AND_PLAN.md**.
