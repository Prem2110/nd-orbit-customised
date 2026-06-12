import json
import uuid
import logging
from datetime import datetime
from app.database import get_connection
from app.config import settings

logger = logging.getLogger(__name__)
S = settings.HANA_SCHEMA


def _ts(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# ── Raw log operations ──────────────────────────────────────────────────────

def save_raw_logs(logs: list[dict]) -> int:
    if not logs:
        return 0
    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0
    for log in logs:
        try:
            cursor.execute(
                f'SELECT COUNT(*) FROM "{S}"."NDORBITCUSTOMISED_CPI_RAW_LOGS" WHERE "CORRELATION_ID" = ?',
                (log["correlation_id"],),
            )
            if cursor.fetchone()[0] > 0:
                continue
            cursor.execute(
                f"""INSERT INTO "{S}"."NDORBITCUSTOMISED_CPI_RAW_LOGS"
                    ("ID","CORRELATION_ID","SOURCE","DESTINATION","STATUS",
                     "START_TIME","END_TIME","SCENARIO_NAME","ERROR_CODE",
                     "ERROR_MESSAGE","RAW_PAYLOAD")
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    log["id"],
                    log["correlation_id"],
                    log.get("source"),
                    log.get("destination"),
                    log.get("status"),
                    _ts(log.get("start_time")),
                    _ts(log.get("end_time")),
                    log.get("scenario_name"),
                    log.get("error_code"),
                    log.get("error_message"),
                    log.get("raw_payload"),
                ),
            )
            inserted += 1
        except Exception as e:
            logger.warning(f"Raw log insert failed: {e}")
    conn.commit()
    cursor.close()
    conn.close()
    return inserted


def get_unclassified_raw_logs() -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""SELECT r."ID","CORRELATION_ID","SOURCE","DESTINATION","STATUS",
                   "START_TIME","END_TIME","SCENARIO_NAME","ERROR_CODE","ERROR_MESSAGE"
            FROM "{S}"."NDORBITCUSTOMISED_CPI_RAW_LOGS" r
            WHERE NOT EXISTS (
                SELECT 1 FROM "{S}"."NDORBITCUSTOMISED_CPI_CLASSIFIED_LOGS" c WHERE c."RAW_LOG_ID" = r."ID"
            )
            ORDER BY r."INGESTED_AT" DESC"""
    )
    cols = [d[0].lower() for d in cursor.description]
    rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return rows


# ── Classified log operations ───────────────────────────────────────────────

def _make_incident_id() -> str:
    now = datetime.utcnow()
    return f"INC-{now.year}-{str(uuid.uuid4().int)[:4]}"


def save_classified_log(raw_log_id: str, raw_log: dict, classification: dict) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    log_ts = raw_log.get("start_time") or raw_log.get("log_timestamp")
    duration = raw_log.get("duration_minutes")

    try:
        cursor.execute(
            f"""INSERT INTO "{S}"."NDORBITCUSTOMISED_CPI_CLASSIFIED_LOGS"
                ("ID","RAW_LOG_ID","CORRELATION_ID","PROCESS_GROUP","PROCESS_ROUTE",
                 "STATUS","INCIDENT_ID","SCENARIO_TITLE","SOURCE_SYSTEM","DESTINATION_SYSTEM",
                 "LOG_TIMESTAMP","ROOT_CAUSE","RECOMMENDATIONS","FLOW_STEPS",
                 "TIMELINE_EVENTS","ERROR_DETAIL","IS_PENDING_APPROVAL","IS_AUTO_FIXED",
                 "IS_FIX_FAILED","RESOLUTION_MINUTES")
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()),
                raw_log_id,
                raw_log.get("correlation_id"),
                classification.get("process_group", "Other / Integration"),
                classification.get("process_route", ""),
                classification.get("status", "success"),
                _make_incident_id(),
                classification.get("scenario_title", raw_log.get("scenario_name", "")),
                classification.get("source_system", ""),
                classification.get("destination_system", ""),
                _ts(log_ts) if isinstance(log_ts, datetime) else log_ts,
                classification.get("root_cause", ""),
                json.dumps(classification.get("recommendations", [])),
                json.dumps(classification.get("flow_steps", [])),
                json.dumps(classification.get("timeline_events", [])),
                json.dumps(classification.get("error_detail", {})),
                1 if classification.get("is_pending_approval") else 0,
                1 if classification.get("is_auto_fixed") else 0,
                1 if classification.get("is_fix_failed") else 0,
                duration,
            ),
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Classified log insert failed: {e}")
    finally:
        cursor.close()
        conn.close()


# ── Dashboard queries ───────────────────────────────────────────────────────

def get_kpis() -> dict:
    conn = get_connection()
    cursor = conn.cursor()

    def q(sql: str):
        cursor.execute(sql)
        row = cursor.fetchone()
        return row[0] if row else 0

    total = q(f'SELECT COUNT(*) FROM "{S}"."NDORBITCUSTOMISED_CPI_CLASSIFIED_LOGS"')
    failed = q(f'SELECT COUNT(*) FROM "{S}"."NDORBITCUSTOMISED_CPI_CLASSIFIED_LOGS" WHERE "STATUS" = \'error\'')
    warning = q(f'SELECT COUNT(*) FROM "{S}"."NDORBITCUSTOMISED_CPI_CLASSIFIED_LOGS" WHERE "STATUS" = \'warning\'')
    running = q(f'SELECT COUNT(*) FROM "{S}"."NDORBITCUSTOMISED_CPI_RAW_LOGS" WHERE "STATUS" = \'RUNNING\'')
    pending = q(f'SELECT COUNT(*) FROM "{S}"."NDORBITCUSTOMISED_CPI_CLASSIFIED_LOGS" WHERE "IS_PENDING_APPROVAL" = 1')
    auto_fixed = q(f'SELECT COUNT(*) FROM "{S}"."NDORBITCUSTOMISED_CPI_CLASSIFIED_LOGS" WHERE "IS_AUTO_FIXED" = 1')
    fix_failed = q(f'SELECT COUNT(*) FROM "{S}"."NDORBITCUSTOMISED_CPI_CLASSIFIED_LOGS" WHERE "IS_FIX_FAILED" = 1')

    cursor.execute(
        f'SELECT AVG("RESOLUTION_MINUTES") FROM "{S}"."NDORBITCUSTOMISED_CPI_CLASSIFIED_LOGS" WHERE "RESOLUTION_MINUTES" IS NOT NULL'
    )
    avg_res = cursor.fetchone()[0] or 0.0

    rca_with = q(
        f'SELECT COUNT(*) FROM "{S}"."NDORBITCUSTOMISED_CPI_CLASSIFIED_LOGS" WHERE "ROOT_CAUSE" IS NOT NULL AND LENGTH("ROOT_CAUSE") > 0 AND "STATUS" = \'error\''
    )
    rca_coverage = round((rca_with / failed * 100) if failed else 0, 1)
    auto_fix_rate = round((auto_fixed / failed * 100) if failed else 0, 1)

    cursor.close()
    conn.close()

    return {
        "in_progress": int(running),
        "total_incidents": int(total),
        "pending_approval": int(pending),
        "fix_failed": int(fix_failed),
        "auto_fixed": int(auto_fixed),
        "failed_messages": int(failed),
        "auto_fix_rate": auto_fix_rate,
        "avg_resolution_minutes": round(float(avg_res), 1),
        "rca_coverage": rca_coverage,
    }


def get_process_health() -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""SELECT "ID","PROCESS_GROUP","PROCESS_ROUTE","STATUS","SCENARIO_TITLE",
                   "SOURCE_SYSTEM","DESTINATION_SYSTEM","LOG_TIMESTAMP","CORRELATION_ID"
            FROM "{S}"."NDORBITCUSTOMISED_CPI_CLASSIFIED_LOGS"
            ORDER BY "LOG_TIMESTAMP" DESC"""
    )
    cols = [d[0].lower() for d in cursor.description]
    rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    cursor.close()
    conn.close()

    groups: dict[str, dict] = {}
    for row in rows:
        pg = row["process_group"] or "Other / Integration"
        if pg not in groups:
            groups[pg] = {
                "id": pg.lower().replace(" ", "-").replace("/", ""),
                "name": pg,
                "route": row["process_route"] or "",
                "status": "success",
                "error_count": 0,
                "warning_count": 0,
                "scenarios": [],
            }
        g = groups[pg]
        status = row["status"] or "success"
        if status == "error":
            g["error_count"] += 1
            g["status"] = "error"
        elif status == "warning" and g["status"] != "error":
            g["warning_count"] += 1
            g["status"] = "warning"

        ts = row["log_timestamp"]
        if isinstance(ts, datetime):
            time_str = ts.strftime("%b %d %H:%M")
        else:
            time_str = str(ts)[:16] if ts else "—"

        g["scenarios"].append({
            "id": row["id"],
            "name": row["scenario_title"] or "Unknown Scenario",
            "status": status,
            "time": time_str,
            "icon": _icon_for_group(pg),
        })

    result = list(groups.values())
    result.sort(key=lambda x: (0 if x["status"] == "error" else 1 if x["status"] == "warning" else 2))
    for g in result:
        g["scenarios"] = g["scenarios"][:20]
    return result


def _icon_for_group(pg: str) -> str:
    pg_lower = pg.lower()
    if "finance" in pg_lower or "payroll" in pg_lower or "gl" in pg_lower:
        return "file-dollar"
    if "hr" in pg_lower or "employee" in pg_lower or "human" in pg_lower:
        return "user-plus"
    if "procurement" in pg_lower or "purchase" in pg_lower or "vendor" in pg_lower:
        return "receipt"
    if "report" in pg_lower or "extract" in pg_lower:
        return "table-export"
    if "work order" in pg_lower or "workorder" in pg_lower or "dispatch" in pg_lower:
        return "tool"
    return "activity"


def get_log_detail(log_id: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""SELECT c."ID",c."CORRELATION_ID",c."PROCESS_GROUP",c."PROCESS_ROUTE",
                   c."STATUS",c."INCIDENT_ID",c."SCENARIO_TITLE",c."SOURCE_SYSTEM",
                   c."DESTINATION_SYSTEM",c."LOG_TIMESTAMP",c."ROOT_CAUSE",
                   c."RECOMMENDATIONS",c."FLOW_STEPS",c."TIMELINE_EVENTS",c."ERROR_DETAIL"
            FROM "{S}"."NDORBITCUSTOMISED_CPI_CLASSIFIED_LOGS" c
            WHERE c."ID" = ?""",
        (log_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if not row:
        return None

    (id_, corr_id, process_group, process_route, status, incident_id,
     scenario_title, src_sys, dst_sys, log_ts, root_cause,
     recommendations_json, flow_steps_json, timeline_json, error_detail_json) = row

    ts = log_ts
    if isinstance(ts, datetime):
        time_str = ts.strftime("%b %d %H:%M")
    else:
        time_str = str(ts)[:16] if ts else "—"

    def _parse(val, default):
        try:
            return json.loads(val) if val else default
        except Exception:
            return default

    recommendations = _parse(recommendations_json, [])
    flow_steps = _parse(flow_steps_json, [])
    timeline_events = _parse(timeline_json, [])
    error_detail = _parse(error_detail_json, {})

    return {
        "id": id_,
        "title": scenario_title or "Unknown Scenario",
        "process": process_group or "Other",
        "status": status or "success",
        "incident_id": incident_id or corr_id or id_,
        "time": time_str,
        "source": src_sys or "Source",
        "destination": dst_sys or "Destination",
        "flow": flow_steps,
        "timeline": timeline_events,
        "error": error_detail if error_detail and error_detail.get("heading") else None,
        "recommendations": recommendations,
    }


# ── Data management ────────────────────────────────────────────────────────

def clear_all_logs() -> dict:
    """Delete all raw and classified log data. Used before a fresh re-sync."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'DELETE FROM "{S}"."NDORBITCUSTOMISED_CPI_CLASSIFIED_LOGS"')
    classified_deleted = cursor.rowcount
    cursor.execute(f'DELETE FROM "{S}"."NDORBITCUSTOMISED_CPI_RAW_LOGS"')
    raw_deleted = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()
    return {"raw_deleted": raw_deleted, "classified_deleted": classified_deleted}


# ── Ingestion status ────────────────────────────────────────────────────────

def get_ingestion_status() -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""SELECT "STATUS","STARTED_AT","COMPLETED_AT","TOTAL_FETCHED",
                   "TOTAL_CLASSIFIED","ERROR_MESSAGE"
            FROM "{S}"."NDORBITCUSTOMISED_CPI_INGESTION_STATUS" WHERE "ID" = 1"""
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if not row:
        return {"status": "idle", "started_at": None, "completed_at": None,
                "total_fetched": 0, "total_classified": 0, "error": None}
    return {
        "status": row[0],
        "started_at": row[1],
        "completed_at": row[2],
        "total_fetched": row[3] or 0,
        "total_classified": row[4] or 0,
        "error": row[5],
    }


def update_ingestion_status(
    status: str,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    total_fetched: int = 0,
    total_classified: int = 0,
    error_message: str | None = None,
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""UPDATE "{S}"."NDORBITCUSTOMISED_CPI_INGESTION_STATUS"
            SET "STATUS" = ?, "STARTED_AT" = ?, "COMPLETED_AT" = ?,
                "TOTAL_FETCHED" = ?, "TOTAL_CLASSIFIED" = ?, "ERROR_MESSAGE" = ?,
                "LAST_UPDATED" = CURRENT_TIMESTAMP
            WHERE "ID" = 1""",
        (
            status,
            _ts(started_at) if started_at else None,
            _ts(completed_at) if completed_at else None,
            total_fetched,
            total_classified,
            error_message,
        ),
    )
    conn.commit()
    cursor.close()
    conn.close()
