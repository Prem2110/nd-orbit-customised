# SAP BTP Deployment Guide — Orbit Integration Monitor

Deploy using SAP Business Application Studio (BAS) terminal.  
Two CF apps are created: **nd-orbit-backend** (FastAPI) and **nd-orbit-frontend** (React static).

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| SAP BTP Account | CF environment enabled |
| CF Org & Space | At least Developer role |
| BAS Access | Full-Stack Cloud Application dev space |
| HANA Cloud | Instance running (`AI_USE_CASES_HDI_DB_1` schema) |
| AI Core | Deployment `d059e276d281dbad` in Running state |

---

## Project structure after prep

```
project-root/
├── backend/
│   ├── app/
│   ├── manifest.yml          ← CF manifest (backend)
│   ├── .cfignore             ← excludes .env, __pycache__
│   ├── requirements.txt
│   └── runtime.txt           ← python-3.11.x
├── frontend/
│   ├── src/
│   ├── dist/                 ← built output (npm run build)
│   ├── manifest.yml          ← CF manifest (frontend)
│   ├── Staticfile            ← enables SPA pushstate routing
│   └── .env.production       ← VITE_API_BASE_URL (set before build)
└── DEPLOYMENT.md
```

---

## Step 1 — Open BAS and login to CF

In BAS, open a terminal (`Terminal → New Terminal`).

```bash
cf login -a https://api.cf.us10.hana.ondemand.com
```

Enter your SAP BTP email and password when prompted.  
Select your **Org** and **Space** from the list.

Verify you are in the right space:
```bash
cf target
```

---

## Step 2 — Clone / open the project in BAS

If not already open, clone the repo into BAS:
```bash
git clone <your-repo-url>
cd "ND Orbit Customised"
```

---

## Step 3 — Deploy the backend

### 3a. Push the backend app

```bash
cd backend
cf push nd-orbit-backend
```

The Python buildpack reads `runtime.txt` (Python 3.11) and `requirements.txt` automatically.

At this point the app will start but **crash** — environment variables are not set yet. That is expected.

### 3b. Set all environment variables

Copy and run these commands one by one in the BAS terminal.  
Replace each `<value>` with your actual credential.

```bash
cf set-env nd-orbit-backend AICORE_CLIENT_ID      "<your-aicore-client-id>"
cf set-env nd-orbit-backend AICORE_CLIENT_SECRET   "<your-aicore-client-secret>"
cf set-env nd-orbit-backend AICORE_AUTH_URL         "<your-aicore-auth-url>"
cf set-env nd-orbit-backend AICORE_BASE_URL         "<your-aicore-base-url>"
cf set-env nd-orbit-backend AICORE_RESOURCE_GROUP   "default"
cf set-env nd-orbit-backend LLM_DEPLOYMENT_ID       "<your-llm-deployment-id>"
cf set-env nd-orbit-backend HANA_HOST               "<your-hana-host>"
cf set-env nd-orbit-backend HANA_PORT               "443"
cf set-env nd-orbit-backend HANA_USER               "<your-hana-user>"
cf set-env nd-orbit-backend HANA_PASSWORD           "<your-hana-password>"
cf set-env nd-orbit-backend HANA_SCHEMA             "<your-hana-schema>"
cf set-env nd-orbit-backend CPI_API_URL             "<your-cpi-api-url>"
cf set-env nd-orbit-backend LLM_USAGE_MONITOR_APP_ID      "28"
cf set-env nd-orbit-backend LLM_USAGE_MONITOR_MODEL_NAME  "claude-sonnet-4-6"
cf set-env nd-orbit-backend LLM_USAGE_MONITOR_BASE_URL    "<your-monitor-base-url>"
cf set-env nd-orbit-backend LLM_USAGE_MONITOR_API_KEY     "<your-monitor-api-key>"
cf set-env nd-orbit-backend LLM_USAGE_MONITOR_CALL_TYPE_L_INVOKE "l_invoke"
cf set-env nd-orbit-backend LLM_USAGE_MONITOR_CALL_TYPE_A_INVOKE "a_invoke"
```

> The `ALLOWED_ORIGINS` for CORS will be set in Step 5 once you know the frontend URL.

### 3c. Restage the backend

```bash
cf restage nd-orbit-backend
```

### 3d. Note the backend URL

```bash
cf app nd-orbit-backend
```

Look for the **routes** line. Example:
```
routes: nd-orbit-backend.cfapps.us10.hana.ondemand.com
```

Keep this URL — you need it for the frontend build.

### 3e. Verify the backend is healthy

```bash
curl https://nd-orbit-backend.cfapps.us10.hana.ondemand.com/health
# expected: {"status":"ok"}
```

---

## Step 4 — Build and deploy the frontend

### 4a. Set the backend URL in .env.production

```bash
cd ../frontend
```

Edit `frontend/.env.production` and replace the placeholder:
```
VITE_API_BASE_URL=https://nd-orbit-backend.cfapps.us10.hana.ondemand.com
```

In BAS you can open the file in the editor, or use:
```bash
echo 'VITE_API_BASE_URL=https://nd-orbit-backend.cfapps.us10.hana.ondemand.com' > .env.production
```

### 4b. Install dependencies and build

```bash
npm install
npm run build
```

This produces the `dist/` folder containing the compiled React app.

### 4c. Copy Staticfile into dist

The `Staticfile` at `frontend/Staticfile` needs to be inside `dist/` before pushing:

```bash
cp Staticfile dist/Staticfile
```

### 4d. Push the frontend app

```bash
cf push nd-orbit-frontend
```

The `manifest.yml` points CF to the `dist/` folder and uses `staticfile_buildpack`.

### 4e. Note the frontend URL

```bash
cf app nd-orbit-frontend
```

Example:
```
routes: nd-orbit-frontend.cfapps.us10.hana.ondemand.com
```

---

## Step 5 — Wire CORS: tell the backend about the frontend URL

```bash
cd ../backend
cf set-env nd-orbit-backend ALLOWED_ORIGINS "https://nd-orbit-frontend.cfapps.us10.hana.ondemand.com"
cf restage nd-orbit-backend
```

---

## Step 6 — Verify end-to-end

Open the frontend URL in a browser:
```
https://nd-orbit-frontend.cfapps.us10.hana.ondemand.com
```

1. Dashboard loads with KPI strip visible
2. Click **Sync Data** — ingestion starts
3. Poll status via the UI or:
   ```bash
   curl https://nd-orbit-backend.cfapps.us10.hana.ondemand.com/api/ingest/status
   ```
4. Once `"status": "completed"`, KPIs and process health populate

---

## Useful CF commands (day-to-day)

| Task | Command |
|------|---------|
| View live logs | `cf logs nd-orbit-backend --recent` |
| Stream logs | `cf logs nd-orbit-backend` |
| Restart backend | `cf restart nd-orbit-backend` |
| View env vars | `cf env nd-orbit-backend` |
| Check app status | `cf apps` |
| Delete app | `cf delete nd-orbit-backend -f` |

---

## Re-deploying after code changes

### Backend change
```bash
cd backend
cf push nd-orbit-backend
```
Environment variables persist — no need to re-set them.

### Frontend change
```bash
cd frontend
npm run build
cp Staticfile dist/Staticfile
cf push nd-orbit-frontend
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Backend crashes on start | Missing env var | `cf logs nd-orbit-backend --recent` → check which var is missing |
| 502 Bad Gateway on frontend | Backend not running | `cf restart nd-orbit-backend` |
| CORS errors in browser console | `ALLOWED_ORIGINS` not set / wrong URL | Step 5 above |
| `/api/ingest/status` returns HANA error | HANA Cloud instance paused | Resume the HANA instance from BTP cockpit |
| LLM classification fails | AI Core deployment stopped | Check deployment `d059e276d281dbad` in AI Core Launchpad |
| `cf push` fails — Python version not found | Buildpack doesn't support 3.11 | Change `runtime.txt` to `python-3.10.x` |
| LLM usage not appearing in monitor | `LLM_USAGE_MONITOR_BASE_URL` missing | Run the `cf set-env` commands in Step 3b and restage |

---

## App URLs (fill in after first deploy)

| App | URL |
|-----|-----|
| Backend API | `https://nd-orbit-backend.cfapps.us10.hana.ondemand.com` |
| Frontend | `https://nd-orbit-frontend.cfapps.us10.hana.ondemand.com` |
| Health check | `https://nd-orbit-backend.cfapps.us10.hana.ondemand.com/health` |
