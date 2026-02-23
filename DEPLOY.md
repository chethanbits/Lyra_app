# Deploy Lyra (Vercel + Render) – Free

Deploy the **app** to **Vercel** and the **API** to **Render**. Both have free tiers. No payment needed for this setup.

---

## Cost

| Service | Plan | Cost |
|--------|------|------|
| **Vercel** (app) | Hobby / Free | **$0** |
| **Render** (API) | Free Web Service | **$0** (service may sleep after ~15 min idle; wakes on first request) |

You do **not** need a credit card for the free tiers.

---

## 1. Deploy the API (Render) first

You need the API URL before building the app, so the app can call it.

1. Push your repo to **GitHub** (if not already).
2. Go to [render.com](https://render.com) and sign up (GitHub login is fine).
3. **Dashboard** → **New** → **Blueprint**.
4. Connect your **GitHub repo** (the one containing `api_exploration` and `lyra_app`).
5. Render will detect the **render.yaml** in the repo root. It defines one service:
   - **Name:** lyra-pyjhora-api  
   - **Root directory:** api_exploration  
   - **Build:** `pip install -r requirements.txt`  
   - **Start:** `uvicorn pyjhora_api:app --host 0.0.0.0 --port $PORT`
6. Click **Apply** (or create the service). Wait for the first deploy to finish.
7. Copy the service URL (e.g. `https://lyra-pyjhora-api.onrender.com`). You will use this as the app’s API URL.

**If you don’t use Blueprint:**  
- **New** → **Web Service** → connect repo → set **Root Directory** to `api_exploration` → **Build Command:** `pip install -r requirements.txt` → **Start Command:** `uvicorn pyjhora_api:app --host 0.0.0.0 --port $PORT` → Create.

---

## 2. Deploy the app (Vercel)

1. Go to [vercel.com](https://vercel.com) and sign up (GitHub login is fine).
2. **Add New** → **Project** → import the **same GitHub repo**.
3. Set **Root Directory** to **`lyra_app`** (not the repo root).  
   - **Framework Preset:** Vite (auto-detected).  
   - **Build Command:** `npm run build`  
   - **Output Directory:** `dist`
4. **Environment variables:** Add one:
   - **Name:** `VITE_API_URL`  
   - **Value:** your Render API URL (e.g. `https://lyra-pyjhora-api.onrender.com`)  
   - No trailing slash.
5. Click **Deploy**. Wait for the build to finish.
6. Your app will be at a URL like `https://lyra-app-xxx.vercel.app`.

**SPA routing:** The repo includes `lyra_app/vercel.json` so that all routes (e.g. `/welcome`, `/app/home`) serve `index.html` and React Router works.

---

## 3. Share the app link

Send your boss (or anyone) the **Vercel app URL**. They open it in the browser on phone or laptop; no install, no Git. The app will call the Render API automatically.

---

## 4. Updating after changes

- **You:** Push to GitHub (e.g. `main`).  
- **Vercel** and **Render** will redeploy automatically if “Deploy on push” is enabled (default).  
- No need to redeploy by hand unless you change env vars (e.g. in Vercel, change `VITE_API_URL` and redeploy).

---

## Folder layout (for reference)

```
your-repo/
├── render.yaml          ← Render uses this (API)
├── DEPLOY.md            ← This file
├── api_exploration/     ← API (Python/FastAPI) – Render rootDir
│   ├── requirements.txt
│   └── pyjhora_api.py
└── lyra_app/            ← App (React/Vite) – Vercel root
    ├── vercel.json
    ├── package.json
    └── ...
```

---

## Troubleshooting

- **App loads but Panchang/API fails:** Check that `VITE_API_URL` in Vercel is exactly your Render API URL (https, no trailing slash). Then trigger a new deploy so the build picks it up.
- **Render service “unavailable” after a while:** Free tier spins down when idle. The first request after that may take 30–60 seconds; then it’s fast again.
- **CORS errors:** The API already allows all origins (`*`). If you still see CORS issues, confirm the request is going to the Render URL, not localhost.
