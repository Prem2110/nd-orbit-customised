import asyncio
import logging
import httpx
from datetime import datetime, timedelta
from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.schemas import IngestionStatusResponse
from app.services import hana_service, cpi_fetcher, llm_service
from app.config import settings

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])
logger = logging.getLogger(__name__)

_running = False


async def _run_ingestion():
    """
    Batch-by-batch ingestion:
      For each weekly chunk (13 weeks × 7 days = 90 days):
        1. Fetch from EIH API
        2. Save raw logs to HANA immediately
        3. Classify with LLM immediately
        4. Update progress in HANA
    Never holds all data in memory at once.
    """
    global _running
    _running = True
    started = datetime.utcnow()
    hana_service.update_ingestion_status("running", started_at=started)

    total_fetched = 0
    total_classified = 0

    end = datetime.utcnow()
    start = end - timedelta(days=45)

    # Build list of weekly windows
    windows = []
    current = start
    while current < end:
        chunk_end = min(current + timedelta(days=7), end)
        windows.append((current, chunk_end))
        current = chunk_end

    logger.info(f"Starting batch ingestion: {len(windows)} weekly chunks")

    try:
        async with httpx.AsyncClient() as client:
            for i, (week_start, week_end) in enumerate(windows):
                logger.info(f"Chunk {i+1}/{len(windows)}: {week_start.date()} → {week_end.date()}")

                # 1. Fetch this week from EIH API
                chunk = await cpi_fetcher.fetch_chunk(
                    client, week_start, week_end,
                    settings.CPI_SOURCE, settings.CPI_DESTINATION
                )

                if not chunk:
                    logger.info(f"  Chunk {i+1}: no data, skipping")
                    continue

                # 2. Save raw logs to HANA immediately
                saved = hana_service.save_raw_logs(chunk)
                total_fetched += saved
                logger.info(f"  Chunk {i+1}: {len(chunk)} records, {saved} new saved")

                # 3. Get the newly saved logs that need classification
                unclassified = hana_service.get_unclassified_raw_logs()
                if not unclassified:
                    logger.info(f"  Chunk {i+1}: no new logs to classify")
                    continue

                # 4. Classify in sub-batches of 5 (respects AI Core rate limits)
                sub_batch_size = 5
                for j in range(0, len(unclassified), sub_batch_size):
                    sub_batch = unclassified[j: j + sub_batch_size]
                    classifications = await llm_service.classify_batch(sub_batch, concurrency=5)
                    for raw_log, classification in zip(sub_batch, classifications):
                        hana_service.save_classified_log(raw_log["id"], raw_log, classification)
                        total_classified += 1

                logger.info(f"  Chunk {i+1}: classified {len(unclassified)} logs (total: {total_classified})")

                # 5. Update progress after each chunk
                hana_service.update_ingestion_status(
                    "running",
                    started_at=started,
                    total_fetched=total_fetched,
                    total_classified=total_classified,
                )

        hana_service.update_ingestion_status(
            "completed",
            started_at=started,
            completed_at=datetime.utcnow(),
            total_fetched=total_fetched,
            total_classified=total_classified,
        )
        logger.info(f"Ingestion completed: {total_fetched} fetched, {total_classified} classified")

    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        hana_service.update_ingestion_status(
            "failed",
            started_at=started,
            completed_at=datetime.utcnow(),
            total_fetched=total_fetched,
            total_classified=total_classified,
            error_message=str(e),
        )
    finally:
        _running = False


@router.post("/start")
def start_ingestion(background_tasks: BackgroundTasks):
    if _running:
        raise HTTPException(status_code=409, detail="Ingestion already running")
    background_tasks.add_task(_run_ingestion)
    return {"message": "Ingestion started"}


@router.get("/status", response_model=IngestionStatusResponse)
def ingestion_status():
    return hana_service.get_ingestion_status()


@router.post("/reset")
def reset_ingestion():
    if _running:
        raise HTTPException(status_code=409, detail="Ingestion is running — wait for it to complete")
    hana_service.update_ingestion_status("idle")
    return {"message": "Status reset to idle"}


@router.post("/clear")
def clear_data():
    """Delete all raw and classified log data and reset status to idle."""
    if _running:
        raise HTTPException(status_code=409, detail="Ingestion is running — wait for it to complete")
    deleted = hana_service.clear_all_logs()
    hana_service.update_ingestion_status("idle")
    return {
        "message": "All log data cleared. Status reset to idle.",
        "raw_deleted": deleted["raw_deleted"],
        "classified_deleted": deleted["classified_deleted"],
    }
