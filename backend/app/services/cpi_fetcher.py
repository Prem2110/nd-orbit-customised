import re
import uuid
import json
import logging
import httpx
from collections import defaultdict
from datetime import datetime, timedelta
from app.config import settings

logger = logging.getLogger(__name__)


def _extract_rows(data) -> list:
    """
    EIH API returns: {"Logs": {"Columns": [...], "Rows": [...]}, ...}
    Extract the Rows list from that structure.
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Primary: EIH format {"Logs": {"Rows": [...]}}
        logs_block = data.get("Logs") or data.get("logs")
        if isinstance(logs_block, dict):
            rows = logs_block.get("Rows") or logs_block.get("rows")
            if isinstance(rows, list):
                return rows
        # Generic fallbacks
        for key in ("data", "results", "items", "records", "correlations"):
            if key in data and isinstance(data[key], list):
                return data[key]
    return []


def _normalize_status(raw: str) -> str:
    s = str(raw).upper().strip()
    if s in ("FAILED", "ERROR", "FAILURE"):
        return "FAILED"
    if s in ("SUCCESS", "COMPLETED", "DONE", "OK", "PROCESSED", "INFORMATION", "INFO"):
        return "SUCCESS"
    if s in ("WARNING", "WARN", "PARTIALLY_FAILED"):
        return "WARNING"
    if s in ("RUNNING", "PROCESSING", "IN_PROGRESS", "PENDING"):
        return "RUNNING"
    return s or "UNKNOWN"


def _parse_dt(val) -> datetime | None:
    if not val:
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=None)
    s = str(val)
    # Truncate fractional seconds to 6 digits (Python max)
    s = re.sub(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.)(\d{7,})',
               lambda m: m.group(1) + m.group(2)[:6], s)
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _group_by_correlation(rows: list[dict]) -> list[dict]:
    """
    Group raw EIH log rows by CorrelationId.
    Multiple rows per correlation are consolidated into one entry.
    Worst LogLevel across the group determines the overall status.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        corr = row.get("CorrelationId") or row.get("correlationId") or ""
        if corr:
            groups[corr].append(row)

    result = []
    for corr_id, group_rows in groups.items():
        log_levels = [r.get("LogLevel", "Information") for r in group_rows]
        if "Error" in log_levels:
            worst = "Error"
        elif "Warning" in log_levels:
            worst = "Warning"
        else:
            worst = "Information"

        first = group_rows[0]
        integration_type = first.get("IntegrationType", "")
        application = first.get("Application", "")

        timestamps = [_parse_dt(r.get("Timestamp")) for r in group_rows]
        timestamps = [t for t in timestamps if t]
        earliest_ts = min(timestamps).isoformat() if timestamps else None
        latest_ts = max(timestamps).isoformat() if timestamps else None

        # Collect messages: errors first, then warnings, then first 2 info
        err_msgs  = [r.get("Message", "") for r in group_rows if r.get("LogLevel") == "Error"]
        warn_msgs = [r.get("Message", "") for r in group_rows if r.get("LogLevel") == "Warning"]
        info_msgs = [r.get("Message", "") for r in group_rows if r.get("LogLevel") == "Information"]

        selected = []
        for m in (err_msgs + warn_msgs + info_msgs[:2]):
            if m:
                selected.append(m[:500])
            if len(selected) >= 4:
                break
        combined_message = " || ".join(selected)

        scenario = f"{integration_type}" if integration_type else "integration"
        if application:
            scenario = f"{scenario} ({application})"

        result.append({
            "CorrelationId": corr_id,
            "IntegrationType": integration_type,
            "Application": application,
            "LogLevel": worst,
            "Timestamp": earliest_ts,
            "EndTimestamp": latest_ts,
            "scenarioName": scenario,
            "errorCode": f"{integration_type.upper()}_ERROR" if worst in ("Error", "Warning") and integration_type else None,
            "errorMessage": combined_message if combined_message else None,
        })
    return result


def normalize_entry(raw: dict, source: str, destination: str) -> dict:
    correlation_id = (
        raw.get("CorrelationId") or raw.get("correlationId")
        or raw.get("correlation_id") or raw.get("id")
        or raw.get("messageId") or raw.get("transactionId")
    )
    status_raw = (
        raw.get("LogLevel") or raw.get("status") or raw.get("Status")
        or raw.get("state") or "Information"
    )
    start_time = _parse_dt(
        raw.get("Timestamp") or raw.get("startTime") or raw.get("start_time")
        or raw.get("createdAt") or raw.get("requestTime")
    )
    end_time = _parse_dt(
        raw.get("EndTimestamp") or raw.get("endTime") or raw.get("end_time")
        or raw.get("updatedAt") or raw.get("completedAt")
    )
    scenario_name = (
        raw.get("scenarioName") or raw.get("IntegrationType") or raw.get("processName")
        or raw.get("flowName") or raw.get("name") or raw.get("integrationName")
        or "Unknown"
    )
    error_code = raw.get("errorCode") or raw.get("error_code") or raw.get("faultCode")
    error_message = (
        raw.get("errorMessage") or raw.get("error_message") or raw.get("Message")
        or raw.get("message") or raw.get("faultMessage")
    )

    duration_minutes = None
    if start_time and end_time:
        delta = (end_time - start_time).total_seconds() / 60
        duration_minutes = int(max(0, delta))

    return {
        "id": str(uuid.uuid4()),
        "correlation_id": str(correlation_id) if correlation_id else str(uuid.uuid4()),
        "source": source,
        "destination": destination,
        "status": _normalize_status(str(status_raw)),
        "start_time": start_time,
        "end_time": end_time,
        "scenario_name": str(scenario_name)[:200] if scenario_name else "Unknown Scenario",
        "error_code": str(error_code)[:200] if error_code else None,
        "error_message": str(error_message)[:4000] if error_message else None,
        "raw_payload": json.dumps(raw, default=str),
        "duration_minutes": duration_minutes,
    }


async def fetch_chunk(
    client: httpx.AsyncClient,
    start: datetime,
    end: datetime,
    source: str,
    destination: str,
) -> list[dict]:
    payload = {
        "source": source,
        "destination": destination,
        "startTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endTime": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "correlationId": "",
    }
    try:
        resp = await client.post(settings.CPI_API_URL, json=payload, timeout=60.0)
        resp.raise_for_status()
        raw_data = resp.json()
        rows = _extract_rows(raw_data)
        grouped = _group_by_correlation(rows)
        normalized = [normalize_entry(e, source, destination) for e in grouped]
        logger.info(
            f"Chunk [{start.date()} → {end.date()}]: "
            f"{len(rows)} log rows → {len(normalized)} unique correlations"
        )
        return normalized
    except Exception as e:
        logger.error(f"Chunk fetch failed [{start.date()} → {end.date()}]: {e}")
        return []


async def fetch_3_months(
    source: str | None = None,
    destination: str | None = None,
) -> list[dict]:
    src = source or settings.CPI_SOURCE
    dst = destination or settings.CPI_DESTINATION

    end = datetime.utcnow()
    start = end - timedelta(days=45)

    all_logs: list[dict] = []
    current = start

    async with httpx.AsyncClient() as client:
        while current < end:
            chunk_end = min(current + timedelta(days=7), end)
            chunk = await fetch_chunk(client, current, chunk_end, src, dst)
            all_logs.extend(chunk)
            current = chunk_end

    # Cross-chunk deduplication on correlation_id
    seen: set[str] = set()
    unique_logs = []
    for log in all_logs:
        cid = log["correlation_id"]
        if cid not in seen:
            seen.add(cid)
            unique_logs.append(log)

    logger.info(f"Total unique correlations: {len(unique_logs)} (raw: {len(all_logs)})")
    return unique_logs
