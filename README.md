# Orbit Integration Monitor

A full-stack SAP integration error monitoring dashboard for **Next Decade**. Fetches 3 months of CPI correlation logs from the EIH API, classifies them with an LLM on SAP BTP AI Core, stores results in SAP HANA Cloud, and presents them in a React dashboard modelled after the Orbit Integration Suite design.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  React + Vite (frontend :5173)                          │
│  Dashboard → KPI Strip → Process Health → Detail View   │
└───────────────────┬─────────────────────────────────────┘
                    │ /api/* (Vite proxy in dev)
┌───────────────────▼─────────────────────────────────────┐
│  FastAPI (backend :8000)                                 │
│  /api/dashboard  /api/ingest  /api/logs                  │
└──────┬──────────────────────┬───────────────────────────┘
       │                      │
┌──────▼──────┐    ┌──────────▼──────────────┐
│ SAP HANA    │    │ SAP BTP AI Core          │
│ Cloud       │    │ (LangChain → ChatOpenAI) │
│ (hdbcli)    │    │ OAuth2 client creds      │
└─────────────┘    └─────────────────────────┘
       ▲
┌──────┴──────────────────────────────────────┐
│ EIH API (Next Decade)                        │
│ POST /external/integrationhub/correlation/  │
│      logs/v1                                │
│ source=workday, destination=sap             │
└─────────────────────────────────────────────┘
```

## Project Structure

```
.
├── backend/
│   ├── .env                        # credentials (never commit)
│   ├── requirements.txt
│   └── app/
│       ├── main.py                 # FastAPI app, lifespan, CORS
│       ├── config.py               # pydantic-settings from .env
│       ├── database.py             # HANA connection + table creation
│       ├── schemas.py              # Pydantic request/response models
│       ├── services/
│       │   ├── auth.py             # AI Core OAuth2 token (cached, auto-refresh)
│       │   ├── cpi_fetcher.py      # EIH API — 13 weekly chunks × 90 days
│       │   ├── llm_service.py      # LangChain classification + fallback
│       │   └── hana_service.py     # all HANA CRUD + KPI aggregations
│       └── routers/
│           ├── dashboard.py        # GET /api/dashboard/kpis|process-health
│           ├── ingestion.py        # POST /api/ingest/start|reset, GET /api/ingest/status
│           └── logs.py             # GET /api/logs/{id}/detail
└── frontend/
    ├── index.html
    ├── vite.config.js              # proxies /api → :8000
    └── src/
        ├── App.jsx
        ├── index.css               # CSS variables matching Orbit design
        ├── services/api.js         # axios wrappers for all endpoints
        ├── pages/Dashboard.jsx     # root state, view toggle, sync polling
        └── components/
            ├── Sidebar.jsx         # nav rail (Dashboard active, others placeholder)
            ├── Topbar.jsx          # title + system badges + Sync Data button
            ├── KpiStrip.jsx        # dark-gradient 5+4 KPI grid
            ├── ProcessHealth.jsx   # accordion process groups + scenario rows
            └── DetailView.jsx      # flow track, timeline, error box, AI recommendations
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- Access to SAP HANA Cloud instance
- Access to SAP BTP AI Core (deployment provisioned)

## Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
```

Create `backend/.env` (already populated with project credentials — keep secret):

```env
AICORE_CLIENT_ID=...
AICORE_CLIENT_SECRET=...
AICORE_AUTH_URL=https://gen-ai.authentication.us10.hana.ondemand.com
AICORE_BASE_URL=https://api.ai.prod.us-east-1.aws.ml.hana.ondemand.com/v2
AICORE_RESOURCE_GROUP=default
LLM_DEPLOYMENT_ID=...

HANA_HOST=...
HANA_PORT=443
HANA_USER=...
HANA_PASSWORD=...
HANA_SCHEMA=AI_USE_CASES_HDI_DB_1

CPI_API_URL=https://api-eih-qa.next-decade.com/external/integrationhub/correlation/logs/v1
CPI_SOURCE=workday
CPI_DESTINATION=sap
```

```bash
uvicorn app.main:app --reload       # starts on http://localhost:8000
```

On first start, HANA tables are created automatically (`NDORBITCUSTOMISED_CPI_RAW_LOGS`, `NDORBITCUSTOMISED_CPI_CLASSIFIED_LOGS`, `NDORBITCUSTOMISED_CPI_INGESTION_STATUS`).

### Frontend

```bash
cd frontend
npm install
npm run dev                         # starts on http://localhost:5173
```

## Usage

1. Open `http://localhost:5173`
2. Click **Sync Data** in the top-right — this triggers `POST /api/ingest/start`
3. The backend fetches 3 months of Workday → SAP logs in weekly chunks, classifies each with the LLM, and stores results in HANA
4. A progress banner polls `GET /api/ingest/status` every 5 seconds
5. On completion the dashboard populates:
   - **KPI Strip** — In Progress, Total Incidents, Pending Approval, Fix Failed, Auto Fixed, Failed Messages, Auto Fix Rate, Avg Resolution Time, RCA Coverage
   - **Process Health** — accordion grouped by process (Finance, HR, Procurement, Reporting, Other), sorted errors first
6. Click any scenario row to open the **Detail View** — integration flow track, execution timeline, error box, and AI-generated recommendations

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/dashboard/kpis` | Aggregated KPI metrics |
| `GET` | `/api/dashboard/process-health` | Process groups with scenarios |
| `GET` | `/api/logs/{id}/detail` | Full detail for one classified log |
| `POST` | `/api/ingest/start` | Start background ingestion (409 if already running) |
| `GET` | `/api/ingest/status` | Current ingestion status + progress counts |
| `POST` | `/api/ingest/reset` | Reset status back to idle |
| `GET` | `/health` | Health check |

## HANA Tables

| Table | Purpose |
|-------|---------|
| `NDORBITCUSTOMISED_CPI_RAW_LOGS` | Raw EIH API entries, deduped on `CORRELATION_ID` |
| `NDORBITCUSTOMISED_CPI_CLASSIFIED_LOGS` | LLM output: process group, status, flow steps, timeline, recommendations (stored as JSON columns) |
| `NDORBITCUSTOMISED_CPI_INGESTION_STATUS` | Single row tracking the current/last ingestion run |

## LLM Classification

Each log is sent to the AI Core deployment with a structured prompt. The model returns:

- **Process group** — Finance / Payroll GL posting, HR / Employee master sync, Procurement / PO confirmation, Reporting / FI extracts, or Other / Integration
- **Root cause** — 1–2 sentence analysis
- **Recommendations** — actionable steps
- **Flow steps** — integration path nodes with ok/error/idle status
- **Timeline events** — step-by-step execution log
- **Error detail** — heading + code block

If the LLM call fails, a rule-based fallback classification is used so ingestion never stalls.

## Deployment (SAP BTP BAS)

- Run the backend as a Cloud Foundry app or via BAS terminal
- Serve the frontend build (`npm run build` → `dist/`) via a static file server or CF staticfile buildpack
- Set all `.env` variables as CF environment variables or BAS workspace settings
