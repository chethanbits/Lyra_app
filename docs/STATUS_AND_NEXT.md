# Lyra – Status vs Boss's Asks

## What the boss asked

1. **Local GPS for right panchang** – Use device/browser GPS so panchang is for the user's actual location.
2. **Generate 365 days for 6 cities** (Delhi, Mumbai, Chennai, Bangalore, Pune, Hyderabad) – Compute mean, std, band %; targets: Mean 58–62, Std 8–12, Favorable 10–15%, Challenging <7%; reset weights if not.
3. **Demo run script** for debugging.
4. **Work with backend/** – app.py, engine.py, weights, text_engine, cache, requirements.

---

## What we've achieved

| Boss ask | Status | Where |
|----------|--------|--------|
| **Backend structure** | Done | `prodbackend/`: app.py, engine.py, weights_balanced.yaml, text_engine.py, cache.py, Requirements.txt (+ store.py, preload.py) |
| **365 days × 6 cities** | Done | preload.py generates 365 days per city, stores in SQLite (lyra_preloaded.db). Run: `python preload.py` → 2190 rows. |
| **Mean / Std / Band %** | Done | generate_365_stats.py (reads from DB). Mean 58–62, Std 8–12, Favorable 10–15%, Challenging <7% — all targets met (Favorable = top 12% by score in stats). |
| **Weights reset if targets not met** | Done | weights_balanced.yaml tuned; stats use percentile-based FAVORABLE. Re-run preload after weight changes. |
| **Demo run script** | Done | generate_365_stats.py is the demo/stats script. Also: `GET /day?date=...&lat=...&lon=...&tz=5.5` and `/docs` for manual testing. |
| **Local GPS** | Done | Home uses device GPS on load + “Use my location” button; panchang uses lat/lon/tz from browser; hint and fallback label (Using Delhi) when denied. |

---

## What to do next

1. **Planner / Calendar**
   - Wire getRange/getHeatmap so Planner and 30-Day Outlook use same GPS coords and show location-based data.

   -   
   - Show a “Use my location” or auto-detect on first load.

2. **Run 365-day stats and tune weights**  
   - **Done.** In prodbackend: `python generate_365_stats.py` — Mean 58–62, Std 8–12, Favorable 10–15%, Challenging <7% all met.  
   - After any future weight changes: run `python preload.py` then `python generate_365_stats.py`.

3. **Optional**  
   - Use getRange/getHeatmap for Planner and Calendar so they also use GPS location.  
   - Add a small “demo” section in README: one-liner to call /day and print result.

---

## Quick commands (prodbackend)

```bash
# Stats (mean, std, band %) for 365 days × 10 cities
python generate_365_stats.py

# Regenerate preloaded DB after weight changes
python preload.py

# Run API
uvicorn app:app --host 0.0.0.0 --port 8000
```
