# Deploy Lyra to Vercel + Render

Use this when pushing your updated code so your boss can test the live app.

---

## 1. Remove / don’t commit unnecessary stuff

Already ignored via `.gitignore` (won’t be pushed):

- `lyra_app/node_modules/`, `lyra_app/dist/`
- `prodbackend/__pycache__/`, `prodbackend/venv/`, `prodbackend/.env`
- `prodbackend/_tuning_guide_extract/`, `prodbackend/_step_guide_extract/`, `prodbackend/*.docx`, `prodbackend/*.py.txt`, `prodbackend/lyra_preloaded.db`
- `.env`, `.env.local`, IDE/OS junk

**Optional (if you want a smaller repo):**

- If `swisseph-master/` at repo root is not used by the app or API, you can add to `.gitignore`:  
  `swisseph-master/`
- Don’t commit any `.env` or secrets; use Vercel/Render **Environment Variables** in the dashboard.

---

## 2. What gets deployed where

| Part            | Where     | Root / config              |
|-----------------|-----------|----------------------------|
| **Frontend (Lyra app)** | **Vercel**  | Root Directory: `lyra_app` |
| **Backend (API)**       | **Render** | `render.yaml` → `rootDir: prodbackend` |

---

## 3. Push the updated code

From the repo root (e.g. `prokeralaandvedic`):

```bash
git status
git add .
git commit -m "Lyra updates: splash, birth details, festivals 15yr, panchang timeline, deploy prep"
git push origin main
```

(Use your real branch name if it’s not `main`.)

---

## 4. Vercel (frontend)

- If the project is already connected: **Vercel will auto-deploy on push**.
- **Root Directory:** must be `lyra_app` (Vercel dashboard → Project → Settings → General).
- **Environment variable (important):**
  - Name: `VITE_API_URL`
  - Value: your Render API URL, e.g. `https://lyra-pyjhora-api.onrender.com`  
    (no trailing slash)
- **Build:** uses `lyra_app/vercel.json` (build command `npm run build`, output `dist`).

After push, open the Vercel deployment URL and test the app. The app will call the API from `VITE_API_URL`.

---

## 5. Render (backend API)

- If the service is already created from this repo: **Render will auto-deploy on push** (when connected to the same branch).
- **Blueprint:** repo root has `render.yaml` with `rootDir: prodbackend`, so Render builds and runs the **prodbackend** app (`uvicorn app:app`).
- **Build:** `pip install -r Requirements.txt`  
- **Start:** `uvicorn app:app --host 0.0.0.0 --port $PORT`

If you previously had a service pointing at `api_exploration`, either:

- Create a **new** Web Service and connect this repo; Render will use `render.yaml` and deploy **prodbackend**, or  
- Edit the existing service: set **Root Directory** to `prodbackend`, **Build Command** to `pip install -r Requirements.txt`, **Start Command** to `uvicorn app:app --host 0.0.0.0 --port $PORT`, then deploy.

Copy the Render service URL (e.g. `https://lyra-pyjhora-api.onrender.com`) and set it as `VITE_API_URL` in Vercel (step 4).

---

## 6. Quick checklist

1. [ ] `.gitignore` is updated (no secrets or heavy local-only files committed).
2. [ ] `git add` / `git commit` / `git push` from repo root.
3. [ ] **Vercel:** Root Directory = `lyra_app`, `VITE_API_URL` = Render API URL.
4. [ ] **Render:** Service uses `prodbackend` (via `render.yaml` or manual Root Directory + build/start commands).
5. [ ] Open Vercel URL and test: splash → onboarding → birth details (city lookup, coordinates) → home (panchang, Rahu Kaal, festivals).

---

## 7. If Render build fails

- Ensure **Python version** is 3.10 or 3.11 (in Render dashboard: Environment → add `PYTHON_VERSION` = `3.11.0` if needed).
- If `ephe` or Swiss Ephemeris is missing, ensure `prodbackend/ephe` is committed (it’s not in `.gitignore`).  
- If you use a preloaded DB and it’s large, consider not committing `lyra_preloaded.db` (already in `.gitignore`) and relying on the non-store code path on Render.

---

## 8. One-line summary

**You:** Push the repo. **Vercel** builds `lyra_app` and serves the frontend. **Render** builds `prodbackend` and runs the API. Set `VITE_API_URL` in Vercel to your Render API URL so the app talks to the deployed API.
