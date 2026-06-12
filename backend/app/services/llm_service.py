import json
import logging
import asyncio
import httpx
from app.config import settings
from app.services.auth import token_manager

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an SAP integration expert. Analyze integration log entries and return structured JSON classification.
Always respond with valid JSON only — no markdown, no explanation, just the JSON object."""

CLASSIFY_TEMPLATE = """Analyze this SAP integration log (Workday → SAP via EIH dispatcher) and return a JSON object.

Log details:
- Correlation ID: {correlation_id}
- Source system: {source}
- Destination system: {destination}
- Overall status: {status}
- Integration type / scenario: {scenario_name}
- Error code: {error_code}
- Log messages: {error_message}

Context: This is a Workday-to-SAP integration log. Integration types include workorder (GL journal entries / payroll postings), employee (HR master data), procurement (PO), reporting (FI extracts). The "Application" in the scenario name is the Azure Function dispatcher.

Return exactly this JSON structure (no extra keys, no markdown):
{{
  "process_group": "<one of: Finance / Payroll GL posting | HR / Employee master sync | Procurement / PO confirmation | Reporting / FI extracts | Work Order / Dispatch | Other / Integration>",
  "process_route": "<source display name> → <destination display name>",
  "status": "<error | warning | success>",
  "scenario_title": "<short human-readable title for this specific log, max 60 chars>",
  "source_system": "<display name for source, e.g. Workday>",
  "destination_system": "<display name for destination, e.g. SAP S/4HANA>",
  "root_cause": "<1-2 sentence root cause analysis>",
  "recommendations": ["<action 1>", "<action 2>", "<action 3>"],
  "flow_steps": [
    {{"label": "<system name>", "step": "<step action>", "status": "<ok | error | idle>"}},
    {{"label": "<system name>", "step": "<step action>", "status": "<ok | error | idle>"}}
  ],
  "timeline_events": [
    {{"status": "<ok | error | warn | idle>", "event": "<event title>", "description": "<what happened>", "time": "<HH:MM>"}}
  ],
  "error_detail": {{
    "heading": "<error heading, empty string if no error>",
    "code": "<error code block text, empty string if no error>"
  }},
  "is_pending_approval": false,
  "is_auto_fixed": false,
  "is_fix_failed": false
}}

Rules:
- process_group must be exactly one of the listed options
- status must be error/warning/success (lowercase)
- flow_steps should reflect the integration path (typically 4-5 steps)
- is_auto_fixed = true only if status is success after a retry
- is_fix_failed = true if status is error and all retries exhausted
- is_pending_approval = true if manual intervention is needed"""


def _fallback(log: dict) -> dict:
    status = log.get("status", "UNKNOWN")
    display = "error" if status == "FAILED" else "warning" if status == "WARNING" else "success"
    src = log.get("source", "Source")
    dst = log.get("destination", "Destination")
    return {
        "process_group": "Other / Integration",
        "process_route": f"{src.title()} → {dst.upper()}",
        "status": display,
        "scenario_title": log.get("scenario_name", "Unknown Scenario")[:60],
        "source_system": src.title(),
        "destination_system": dst.upper(),
        "root_cause": "Automated classification unavailable — manual review required.",
        "recommendations": ["Review the integration log manually in SAP CPI"],
        "flow_steps": [
            {"label": src.title(), "step": "Process", "status": "ok" if display != "error" else "error"},
            {"label": dst.upper(), "step": "Receive", "status": "idle" if display == "error" else "ok"},
        ],
        "timeline_events": [],
        "error_detail": {
            "heading": log.get("error_code") or "Unknown Error",
            "code": log.get("error_message") or "No details available",
        },
        "is_pending_approval": display == "error",
        "is_auto_fixed": False,
        "is_fix_failed": display == "error",
    }


async def _call_claude(prompt: str) -> str:
    """Call SAP AI Core Claude deployment via /invoke with Anthropic message format."""
    token = await token_manager.get_token()
    url = (
        f"{settings.AICORE_BASE_URL}/inference/deployments"
        f"/{settings.LLM_DEPLOYMENT_ID}/invoke"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "AI-Resource-Group": settings.AICORE_RESOURCE_GROUP,
        "Content-Type": "application/json",
    }
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1500,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]


async def classify_log(log: dict) -> dict:
    prompt = CLASSIFY_TEMPLATE.format(
        correlation_id=log.get("correlation_id", ""),
        source=log.get("source", ""),
        destination=log.get("destination", ""),
        status=log.get("status", ""),
        scenario_name=log.get("scenario_name", ""),
        error_code=log.get("error_code") or "None",
        error_message=(log.get("error_message") or "None")[:800],
    )

    try:
        content = await _call_claude(prompt)
        content = content.strip()

        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        result = json.loads(content.strip())
        return result
    except Exception as e:
        logger.warning(f"LLM classification failed for {log.get('correlation_id')}: {e}")
        return _fallback(log)


async def classify_batch(logs: list[dict], concurrency: int = 5) -> list[dict]:
    semaphore = asyncio.Semaphore(concurrency)

    async def _classify_one(log: dict) -> dict:
        async with semaphore:
            result = await classify_log(log)
            await asyncio.sleep(0.2)
            return result

    tasks = [_classify_one(log) for log in logs]
    return await asyncio.gather(*tasks)
