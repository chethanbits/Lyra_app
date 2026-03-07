# Lyra – Production Architecture & Build Plan

This document describes the **end-to-end architecture** and **plan** for building Lyra as a **real production app** (not a sample). Use it to align with your boss and to drive implementation.

---

## 1. What We’re Building (Product)

- **Lyra – Align Your Day**: A daily alignment app based on Vedic Panchang.
- **Users** get: today’s alignment score, panchang details, planner (good/bad times), calendar view, optional personality/analytics (from collected data).
- **Boss goals**: Production-quality app, clear architecture, data completed for personalities, charts for analytics, planner/calendar updated with real logic.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER (Browser / Mobile)                         │
└─────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  FRONTEND (Lyra App)                                                         │
│  • React (Vite) + Capacitor for Android                                      │
│  • Hosted: Vercel (web)  |  Build: Android APK                              │
│  • Gets GPS (lat/lon) for local panchang                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                    │
                    │  HTTPS (REST)
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  BACKEND API (HTTP layer: routes, validation, auth)                          │
│  • FastAPI  • Hosted: Render                                                 │
│  • Serves /day, /range, /heatmap from preloaded data (or cache)             │
└─────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  BACKEND PROCESSING LAYER (clear, separate — no HTTP here)                  │
│  • Engine: compute_panchanga() + compute_alignment_score()                   │
│  • Uses: PyJHora + weights YAML                                              │
│  • Used by: preload job (batch) and optionally on-demand fallback           │
└─────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PRELOADED FIXED DATA (not generated every time)                             │
│  • Precompute e.g. 365 days × fixed cities; store in DB / cache              │
│  • API reads from store; regenerate only when weights or range change        │
└─────────────────────────────────────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌───────────────────┐   ┌───────────────────┐
│  DATABASE         │   │  FILES              │
│  • Postgres       │   │  • Weights YAML    │
│  • Stores:        │   └───────────────────┘
│    - users        │
│    - preferences  │   (PyJHora runs only in processing layer / preload job)
│    - saved places │
│    - personalities│
│    - preloaded    │
│      alignment    │
└───────────────────┘
```

**Design choices:**

- **Clear backend processing layer**: Panchang + scoring live in a **separate layer** (engine), not mixed with HTTP. API routes only validate input, call the processing layer or read preloaded data, and return JSON.
- **Preloaded fixed data**: Alignment/panchang for a **fixed set** (e.g. 365 days for Delhi, Mumbai, Chennai, Bangalore, Pune, Hyderabad) is **generated once** (batch job/script), stored in DB. The API **serves from this store**; data is **not generated on every request**.
- **One backend service** in production: API + processing layer + preloaded data + DB.
- **Database** is required: users, preferences, personalities, and **preloaded alignment data**.

---

## 3. Components in Detail

### 3.1 Frontend (Lyra App)

| Item | Technology | Purpose |
|------|------------|--------|
| App | React + Vite | SPA, fast builds |
| Mobile | Capacitor | Android (and later iOS) from same codebase |
| Hosting (web) | Vercel | CDN, serverless, env vars |
| State | React state + optional context/light store | No need for Redux at start |
| API client | Fetch to backend base URL | Single origin (our API) |
| GPS | Browser Geolocation API | Send lat/lon/tz to backend for panchang |

**Production checklist (frontend):**

- [ ] Use backend API URL from env (e.g. `VITE_API_URL`); no hardcoded localhost in prod.
- [ ] Handle loading and errors (e.g. “Allow location” for GPS, API errors).
- [ ] Planner and Calendar call real APIs (`/day`, `/range`, `/heatmap`) with user’s location.
- [ ] If we add auth: send token (e.g. Bearer) in API requests.

---

### 3.2 Backend API (Production Service)

| Item | Choice | Purpose |
|------|--------|--------|
| Runtime | Python 3.11+ | Matches PyJHora and current stack |
| Framework | FastAPI | Async, OpenAPI, validation |
| Panchang + scoring | PyJHora + prod backend engine (weights YAML) | Single source of truth for alignment logic |
| Auth (later) | JWT or session cookies + secure storage | Login/signup, “my data” |
| Database client | asyncpg or SQLAlchemy (async) | Postgres |
| Config | Env vars (and/or secrets manager) | DB URL, API keys, feature flags |

**Endpoints (production):**

| Endpoint | Purpose | Auth |
|----------|---------|------|
| `GET /health` | Liveness | No |
| `GET /config` | Weights/debug info | No (or restrict in prod) |
| `GET /day` | Panchang + score for one day (query: date, lat, lon, tz) | No (or optional user) |
| `GET /range` | List of days (e.g. month) | No |
| `GET /heatmap` | Lightweight scores for calendar | No |
| `POST /auth/register`, `POST /auth/login` | (When we add users) | No |
| `GET /me`, `PATCH /me/preferences` | User profile, saved location | Yes |
| `GET /personalities`, `GET /analytics/...` | Data for boss’s charts | Yes (or internal only) |

**Production checklist (backend):**

- [ ] One repo/folder for “production backend” (merge api_exploration + prod backend logic into one service).
- [ ] All panchang/alignment logic uses **weights YAML** and **engine** (compute_panchanga, compute_alignment_score) so we can tune and run 365-day stats.
- [ ] Database: connection pool, migrations (e.g. Alembic), no secrets in code.
- [ ] Logging: structured logs (JSON) and log level from env.
- [ ] Errors: consistent format (e.g. `{ "error": "code", "message": "..." }`), no stack traces in prod response.
- [ ] CORS: allow only frontend origin(s) in production.
- [ ] Rate limiting: per IP or per user to avoid abuse.

---

### 3.3 Database (Production)

**Why a database:**

- **Users** (if we add sign-up): email, hashed password, created_at.
- **Preferences**: default city, timezone, notification settings.
- **Saved places**: user’s locations for quick panchang.
- **Personalities data**: the “individual data we collected at starting” for analytics and charts (per boss).
- **Audit / analytics**: who used what when (if we need it later).

**Suggested schema (minimal for production start):**

- **users** – id, email, password_hash, created_at, updated_at.
- **user_preferences** – user_id, default_lat, default_lon, default_tz, region (NORTH_INDIA/SOUTH_INDIA), created_at, updated_at.
- **saved_places** – user_id, name, lat, lon, tz, created_at.
- **personalities** – id, external_id or name, birth_date, birth_time, place, lat, lon, tz, source, created_at, updated_at. (For the data you already collected and for charts.)
- **alignment_scores_cache** (optional) – date, lat, lon, tz, score, band, payload JSON; for speeding up repeated requests.
- **preloaded_alignment** – date, place_id or (lat, lon, tz), score, band, panchang_json (or normalized columns). Filled by **preload job**; API reads from here. Data need not be generated every time.

**Hosting options:**

- **Supabase**: Postgres + Auth + optional storage; free tier.
- **Neon**: Serverless Postgres; free tier.
- **Render Postgres**: if backend is on Render; paid.
- **Railway / Fly.io**: Postgres add-on.

Start with **one** of these and use **migrations** (e.g. Alembic) from day one so schema is versioned and repeatable.

---

### 3.4 Auth (When We Add “My Account”)

- **Sign up / Login**: email + password; store only hashed passwords (e.g. bcrypt).
- **Session**: JWT in Authorization header or httpOnly cookie.
- **Frontend**: login page, store token, send with API calls; logout clears token.
- **Backend**: middleware or dependency that validates token and attaches `user_id` to request.

We can defer auth until boss asks for “accounts”; then add the above without changing the overall architecture.

---

## 4. Data Flow (End-to-End)

1. **User opens app** → Frontend loads, (optional) asks for GPS.
2. **Frontend** calls `GET /day?date=2026-02-24&lat=28.61&lon=77.20&tz=5.5`.
3. **Backend** receives request; (optional) checks auth if endpoint is protected.
4. **Backend** looks up (date, lat, lon, tz) in **preloaded** store (DB). If found, return that. If not found and on-demand is supported, call **processing layer** once, cache result, then return.
5. **Processing layer** (only when preloading or on-demand): `compute_panchanga()` (PyJHora) → `compute_alignment_score()` → `build_day_result()`. Not called on every request for preloaded keys.
6. **Backend** returns JSON: panchang + score + band + summary lines.
7. **Frontend** shows alignment score, panchang, and summary; Planner/Calendar use `/range` and `/heatmap` with same (lat, lon, tz).

**Personalities / analytics (boss’s ask):**

- Data lives in **DB** (e.g. `personalities` table or CSV imported into DB).
- Backend exposes e.g. `GET /personalities` or `GET /analytics/summary` (with filters) for charting.
- Frontend (or a separate admin/dashboard) calls these and builds charts (e.g. Chart.js, Recharts, or export to Excel).

---

## 5. Repo and Deployment Layout (Production)

**Single repo (current):**

```
lyra/
├── app/                    # Frontend (React/Vite) – deploy to Vercel
├── backend/                # Single production backend (FastAPI + engine + DB)
│   ├── app.py              # Routes, auth, personalities/analytics endpoints
│   ├── engine.py           # Panchang + scoring (PyJHora + weights)
│   ├── text_engine.py      # Summary lines
│   ├── db.py               # DB connection, models
│   ├── migrations/         # Alembic or similar
│   ├── weights_balanced.yaml
│   └── requirements.txt
├── docs/
│   └── ARCHITECTURE_AND_PLAN.md   # This file
└── README.md
```

**Deployment:**

- **Frontend**: Vercel; env `VITE_API_URL` = production API URL.
- **Backend**: Render (or Railway, Fly.io); env `DATABASE_URL`, `LYRA_WEIGHTS_PATH`, etc.
- **Database**: Supabase/Neon/etc.; URL only in backend env, never in frontend.

**Current state vs this plan:**

- We have **api_exploration** (PyJHora API) and **prodbackend** (engine + weights + app.py). For production we **merge** into one **backend** that has both PyJHora integration and DB (and later auth). No need to run two separate backends in prod.

---

## 6. Phased Plan (What to Build When)

**Phase 1 – Foundation (do first)**  
- [ ] Single production backend: FastAPI + engine (compute_panchanga, compute_alignment_score implemented) + weights YAML.  
- [ ] Endpoints: `/health`, `/config`, `/day`, `/range`, `/heatmap`.  
- [ ] Deploy backend to Render; frontend points to it (already done for current API).  
- [ ] Frontend: use GPS (lat/lon/tz) for all panchang calls; show loading/errors.  
- [ ] Run `generate_365_stats.py` for 6 cities; tune weights so Mean 58–62, Std 8–12, Favorable 10–15%, Challenging <7%.

**Phase 2 – Database and data**  
- [ ] Add Postgres (Supabase or Neon); run migrations.  
- [ ] Tables: `users`, `user_preferences`, `saved_places`, `personalities`.  
- [ ] Import “personalities” / collected data into DB (script or admin endpoint).  
- [ ] Backend: read/write DB for preferences and personalities; optional cache for alignment by (date, lat, lon, tz).

**Phase 3 – Planner and Calendar (real logic)**  
- [ ] Planner: good/bad time windows from panchang (e.g. Rahu Kalam, favorable nakshatra hours); backend endpoint or extend `/day` with `time_windows`.  
- [ ] Calendar: consume `/heatmap` and optionally `/range`; show month view with scores/bands.  
- [ ] Frontend: wire Planner and Calendar to these APIs and to user’s location.

**Phase 4 – Auth and “my data” (if required)**  
- [ ] Sign up / login; JWT or session.  
- [ ] Endpoints: `/auth/register`, `/auth/login`, `GET /me`, `PATCH /me/preferences`, saved places CRUD.  
- [ ] Frontend: login/signup screens, send token with requests, “My account” or settings.

**Phase 5 – Analytics and charts (boss’s ask)**  
- [ ] Endpoints: `GET /personalities`, `GET /analytics/summary` (or similar) from DB.  
- [ ] Frontend or internal dashboard: charts (e.g. distribution of scores, by city, by date range); export if needed.  
- [ ] Ensure “data completed for personalities” and “chart for analytics” are satisfied.

---

## 7. What “Production” Means Here

- **Single backend** in production (no split between “api_exploration” and “prodbackend” for deployment).  
- **Database** for users, preferences, personalities, and analytics.  
- **Weights and logic** in one place (engine + YAML); 365-day stats script to validate tuning.  
- **GPS** for correct local panchang.  
- **Structured plan** (this doc) and phased work (Phases 1–5) so we build toward a real app, not ad‑hoc samples.  
- **Logging, errors, CORS, env-based config** as we go.

---

## 8. How to Present This to Your Boss

You can say:

- “We have an **architecture doc** that describes the full system: frontend, single backend API, database, and how data flows. The backend will use PyJHora and our weights to compute panchang and alignment scores; the same backend will serve the app and, later, personalities and analytics.”
- “We’ll build in **phases**: (1) backend + engine + deploy + GPS and weight tuning, (2) database and importing personalities data, (3) planner and calendar with real logic, (4) auth if needed, (5) analytics and charts for the data you want.”
- “For production we’ll use a **database** (e.g. Postgres on Supabase or Neon) for users, preferences, and the personalities data so we can run charts and analytics properly.”

If you want, next step can be **Phase 1** in code: one backend folder, engine implemented, and deployment + frontend GPS wired to it.
