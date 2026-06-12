# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Orbit Integration Monitor** — A full-stack app that fetches SAP CPI error logs from an EIH (Enterprise Integration Hub) API, classifies them using an LLM on SAP BTP AI Core, stores results in SAP HANA Cloud, and surfaces them in a React dashboard.

```
backend/   FastAPI + LangChain + hdbcli
frontend/  React + Vite
```

## Commands

### Backend
```bash
cd backend
pip install -r requirements.txt        # install deps
uvicorn app.main:app --reload          # dev server on :8000
```

### Frontend
```bash
cd frontend
npm install                            # install deps
npm run dev                            # dev server on :5173 (proxies /api → :8000)
npm run build                          # production build
```

## Architecture

### Backend (`backend/app/`)

| File | Responsibility |
|------|---------------|
| `config.py` | Pydantic Settings — reads `.env` for AI Core and HANA credentials |
| `database.py` | HANA connection via `hdbcli`, creates `NDORBITCUSTOMISED_CPI_RAW_LOGS`, `NDORBITCUSTOMISED_CPI_CLASSIFIED_LOGS`, `NDORBITCUSTOMISED_CPI_INGESTION_STATUS` tables on startup |
| `schemas.py` | Pydantic request/response models |
| `services/auth.py` | OAuth2 client-credentials token manager for SAP AI Core (caches token, auto-refreshes) |
| `services/cpi_fetcher.py` | POSTs to the EIH API in weekly chunks for the past 90 days; normalises response into a standard dict |
| `services/llm_service.py` | LangChain `ChatOpenAI` pointed at the AI Core deployment; classifies each log into process group, root cause, recommendations, flow steps, timeline |
| `services/hana_service.py` | All HANA CRUD — insert raw logs, insert classified logs, aggregate KPIs, group by process, fetch detail |
| `routers/dashboard.py` | `GET /api/dashboard/kpis`, `GET /api/dashboard/process-health` |
| `routers/ingestion.py` | `POST /api/ingest/start` (background task), `GET /api/ingest/status`, `POST /api/ingest/reset` |
| `routers/logs.py` | `GET /api/logs/{id}/detail` |

### Ingestion flow
1. `POST /api/ingest/start` → background task fires
2. `cpi_fetcher.fetch_3_months()` — 13 weekly API calls, deduplicates by `correlation_id`
3. `hana_service.save_raw_logs()` — bulk upsert into `NDORBITCUSTOMISED_CPI_RAW_LOGS`
4. `llm_service.classify_batch()` — concurrent LLM calls (semaphore 5), fallback on failure
5. `hana_service.save_classified_log()` — writes to `NDORBITCUSTOMISED_CPI_CLASSIFIED_LOGS`
6. Status polled via `GET /api/ingest/status`

### SAP AI Core auth
Token URL: `{AICORE_AUTH_URL}/oauth/token` (client_credentials)  
Inference URL: `{AICORE_BASE_URL}/inference/deployments/{LLM_DEPLOYMENT_ID}/chat/completions`  
Required header on every LLM call: `AI-Resource-Group: default`

### Frontend (`frontend/src/`)

| Component | What it does |
|-----------|--------------|
| `pages/Dashboard.jsx` | Root state — owns view toggle, data loading, sync polling |
| `components/Sidebar.jsx` | Nav rail; only Dashboard is active, others are placeholders |
| `components/Topbar.jsx` | Page title + system badges + **Sync Data** button |
| `components/KpiStrip.jsx` | Two-row dark gradient KPI grid (5+4 metrics) |
| `components/ProcessHealth.jsx` | Accordion process groups → expandable scenario rows |
| `components/DetailView.jsx` | Flow track, timeline, error box, AI recommendations |
| `services/api.js` | Axios calls to `/api/*` (proxied by Vite in dev) |

### HANA schema (`AI_USE_CASES_HDI_DB_1`)

- `NDORBITCUSTOMISED_CPI_RAW_LOGS` — raw entries from the EIH API, deduped on `CORRELATION_ID`
- `NDORBITCUSTOMISED_CPI_CLASSIFIED_LOGS` — LLM output: process group, status, incident ID, flow steps (JSON), timeline (JSON), error detail (JSON), recommendations (JSON), boolean flags
- `NDORBITCUSTOMISED_CPI_INGESTION_STATUS` — single row (ID=1) tracking current ingestion run

## Environment
All credentials live in `backend/.env`. Never commit this file.
