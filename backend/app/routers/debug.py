import json
import logging
from fastapi import APIRouter
from app.database import get_connection
from app.config import settings
from app.services import llm_service, cpi_fetcher
from app.services.auth import token_manager
import httpx

router = APIRouter(prefix="/api/debug", tags=["debug"])
logger = logging.getLogger(__name__)
S = settings.HANA_SCHEMA


@router.get("/raw-samples")
def raw_samples(limit: int = 3):
    """Show raw payloads stored from the EIH API so we can see the actual field names."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f'SELECT "CORRELATION_ID","STATUS","SCENARIO_NAME","RAW_PAYLOAD" '
        f'FROM "{S}"."NDORBITCUSTOMISED_CPI_RAW_LOGS" '
        f'ORDER BY "INGESTED_AT" DESC'
    )
    rows = cursor.fetchmany(limit)
    cursor.close()
    conn.close()

    result = []
    for row in rows:
        corr_id, status, scenario_name, raw_payload = row
        payload_parsed = None
        try:
            payload_parsed = json.loads(raw_payload) if raw_payload else None
        except Exception:
            payload_parsed = str(raw_payload)[:500]

        result.append({
            "correlation_id": corr_id,
            "normalized_status": status,
            "normalized_scenario_name": scenario_name,
            "raw_api_payload": payload_parsed,
        })

    return {"count": len(result), "samples": result}


@router.get("/test-llm")
async def test_llm():
    """Run LLM classification on one stored raw log and return the raw output + any error."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f'SELECT "ID","CORRELATION_ID","SOURCE","DESTINATION","STATUS",'
        f'"SCENARIO_NAME","ERROR_CODE","ERROR_MESSAGE" '
        f'FROM "{S}"."NDORBITCUSTOMISED_CPI_RAW_LOGS" '
        f'ORDER BY "INGESTED_AT" DESC'
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return {"error": "No raw logs in database — run Sync Data first"}

    cols = ["id", "correlation_id", "source", "destination", "status",
            "scenario_name", "error_code", "error_message"]
    log = dict(zip(cols, row))

    # Test token fetch
    try:
        token = await token_manager.get_token()
        token_ok = True
        token_preview = token[:20] + "..." if token else "empty"
    except Exception as e:
        token_ok = False
        token_preview = str(e)

    # Test raw LLM call via /invoke (bypass classify_log's try/except so we see the real error)
    from app.services.llm_service import CLASSIFY_TEMPLATE, SYSTEM_PROMPT, _call_claude

    raw_response = None
    llm_error = None
    parsed_result = None
    parse_error = None

    try:
        prompt = CLASSIFY_TEMPLATE.format(
            correlation_id=log.get("correlation_id", ""),
            source=log.get("source", ""),
            destination=log.get("destination", ""),
            status=log.get("status", ""),
            scenario_name=log.get("scenario_name", ""),
            error_code=log.get("error_code") or "None",
            error_message=(log.get("error_message") or "None")[:800],
        )
        raw_response = await _call_claude(prompt)
        import json as _json
        content = raw_response.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        parsed_result = _json.loads(content.strip())
    except Exception as e:
        llm_error = f"{type(e).__name__}: {e}"

    return {
        "log_used": log,
        "ai_core_token_ok": token_ok,
        "token_preview": token_preview,
        "llm_raw_response": raw_response,
        "llm_parsed_result": parsed_result,
        "llm_error": llm_error,
        "parse_error": parse_error,
    }


@router.get("/aicore-deployments")
async def list_aicore_deployments():
    """List all deployments visible on AI Core so we can verify the deployment ID and status."""
    try:
        token = await token_manager.get_token()
    except Exception as e:
        return {"error": f"Token fetch failed: {e}"}

    results = {}
    resource_groups = ["default", settings.AICORE_RESOURCE_GROUP]
    for rg in set(resource_groups):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{settings.AICORE_BASE_URL}/lm/deployments",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "AI-Resource-Group": rg,
                    },
                    timeout=15.0,
                )
                results[rg] = {
                    "status_code": resp.status_code,
                    "deployments": resp.json() if resp.status_code == 200 else resp.text,
                }
        except Exception as e:
            results[rg] = {"error": str(e)}

    return {
        "configured_deployment_id": settings.LLM_DEPLOYMENT_ID,
        "configured_base_url": settings.AICORE_BASE_URL,
        "inference_url": f"{settings.AICORE_BASE_URL}/inference/deployments/{settings.LLM_DEPLOYMENT_ID}/chat/completions",
        "results_by_resource_group": results,
    }


@router.get("/test-api")
async def test_api():
    """Hit the EIH API for the last 7 days and return the raw response to see field names."""
    from datetime import datetime, timedelta
    end = datetime.utcnow()
    start = end - timedelta(days=7)
    payload = {
        "source": settings.CPI_SOURCE,
        "destination": settings.CPI_DESTINATION,
        "startTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endTime": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "correlationId": "",
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(settings.CPI_API_URL, json=payload, timeout=30.0)
            raw = resp.json()
        entries = raw if isinstance(raw, list) else raw
        # Return first entry's keys so we can see the field structure
        first_entry = None
        if isinstance(raw, list) and raw:
            first_entry = raw[0]
        elif isinstance(raw, dict):
            for key in ("data", "logs", "results", "items", "records", "correlations"):
                if key in raw and isinstance(raw[key], list) and raw[key]:
                    first_entry = raw[key][0]
                    break
        return {
            "status_code": resp.status_code,
            "response_type": type(raw).__name__,
            "top_level_keys": list(raw.keys()) if isinstance(raw, dict) else "list",
            "total_entries": len(raw) if isinstance(raw, list) else None,
            "first_entry_keys": list(first_entry.keys()) if first_entry else None,
            "first_entry": first_entry,
        }
    except Exception as e:
        return {"error": str(e)}
