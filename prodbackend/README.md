# Lyra Production Backend

FastAPI backend for the Lyra alignment app: PyJHora-based panchang, deterministic scoring, optional preloaded SQLite store.

## Files

| File | Purpose |
|------|--------|
| `app.py` | FastAPI: `/health`, `/day`, `/range`, `/heatmap`, `/config`. Reads from preloaded store first when `LYRA_USE_STORE=1`. |
| `engine.py` | **Implemented**: `compute_panchanga()` (PyJHora), `compute_alignment_score()`, `compute_range()`, `compute_heatmap()`, canonical names for weights. |
| `text_engine.py` | Deterministic 2-line summary from panchang + score. |
| `store.py` | SQLite store for preloaded alignment data (date, place_id, score, band, panchanga, summary). |
| `preload.py` | Script: 365 days × 6 cities → `lyra_preloaded.db`. |
| `weights_balanced.yaml` | Weights for tithi, nakshatra, yoga, karana, vaara, bands. |
| `generate_365_stats.py` | Stats over 365 days × 6 cities (mean, std, band %). |
| `download_ephe.py` | One-time: downloads Swiss Ephemeris `ephe` folder from GitHub into `prodbackend/ephe/`. |

## Swiss Ephemeris data (required for PyJHora)

PyJHora needs the **Swiss Ephemeris data files** (the `ephe` folder). Use **one** of these:

### Option 1 – Script (easiest)

```bash
cd prodbackend
python download_ephe.py
```

This downloads the official [Swiss Ephemeris ephe folder](https://github.com/aloistr/swisseph/tree/master/ephe) (same as Astro.com’s “Compressed Swiss Ephemeris planet and main asteroid files”) into `prodbackend/ephe/`. Then set the path (see below).

### Option 2 – Manual

- **Where:** [github.com/aloistr/swisseph/tree/master/ephe](https://github.com/aloistr/swisseph/tree/master/ephe) or the link from [Astrodienst](https://www.astro.com/ftp/swisseph/ephe/).
- **What:** The whole `ephe` folder (planet + lunar `.se1` files like `sepl_48.se1`, `seplm48.se1`). Either clone the repo and copy `ephe`, or download [master.zip](https://github.com/aloistr/swisseph/archive/refs/heads/master.zip), unzip, and copy the `swisseph-master/ephe` folder to `prodbackend/ephe`.

**Don’t use:** JPL ephemerides, PDF ephemeris, or only asteroid folders — you need the main planet/lunar files first.

### Set the path

After `ephe` is in place (e.g. `prodbackend/ephe`):

- **Windows (cmd):** `set SWISSEPH_EPHE_PATH=C:\path\to\prodbackend\ephe`
- **PowerShell:** `$env:SWISSEPH_EPHE_PATH = "C:\path\to\prodbackend\ephe"`
- **Linux/Mac:** `export SWISSEPH_EPHE_PATH=/path/to/prodbackend/ephe`

Then run the API or `preload.py`. The engine uses this env var and calls `swisseph.set_ephe_path()` before using PyJHora.

## Install and run API

```bash
cd prodbackend
pip install -r Requirements.txt
# Set ephemeris path if needed (see above)
uvicorn app:app --host 0.0.0.0 --port 8000
```

- **Without store:** Every `/day`, `/range`, `/heatmap` call uses the engine (PyJHora). Needs ephemeris.
- **With store:** Preload once, then run API with store:
  ```bash
  python preload.py --year 2026
  LYRA_USE_STORE=1 uvicorn app:app --host 0.0.0.0 --port 8000
  ```
  Optional: `LYRA_DB_PATH=/path/to/lyra_preloaded.db` if DB is not in `prodbackend/lyra_preloaded.db`.

## Preload (365 days × 6 cities)

```bash
cd prodbackend
# Ensure ephemeris path is set
python preload.py --year 2026
# Optional: --db /path/to/custom.db
```

Creates (or appends to) `lyra_preloaded.db`. Then run the API with `LYRA_USE_STORE=1` to serve from the store.

## Check stats (after ephemeris is set)

```bash
python generate_365_stats.py
```

Targets: Mean 58–62, Std 8–12, Favorable 10–15%, Challenging <7%.

## Deploy (e.g. Render)

1. Use `prodbackend` as the service root; start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`.
2. Add build step to download or include Swiss Ephemeris files and set `SWISSEPH_EPHE_PATH` (or equivalent) so PyJHora can find them.
3. For production with preloaded data: run `preload.py` in a one-off job or during build, then set `LYRA_USE_STORE=1` and (if needed) `LYRA_DB_PATH` so the API serves from the DB.

## Weights

Edit `weights_balanced.yaml` to tune score distribution. Then re-run `generate_365_stats.py` and optionally `preload.py` to refresh the store.
