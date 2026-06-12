import logging
from hdbcli import dbapi
from app.config import settings

logger = logging.getLogger(__name__)

SCHEMA = settings.HANA_SCHEMA


def get_connection() -> dbapi.Connection:
    return dbapi.connect(
        address=settings.HANA_HOST,
        port=settings.HANA_PORT,
        user=settings.HANA_USER,
        password=settings.HANA_PASSWORD,
        encrypt=True,
        sslValidateCertificate=False,
    )


def _create_table(cursor, ddl: str):
    try:
        cursor.execute(ddl)
    except Exception as e:
        msg = str(e).lower()
        if "already exists" in msg or "duplicate" in msg or "258" in msg:
            pass
        else:
            raise


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    _create_table(cursor, f"""
        CREATE TABLE "{SCHEMA}"."NDORBITCUSTOMISED_CPI_RAW_LOGS" (
            "ID" NVARCHAR(200) PRIMARY KEY,
            "CORRELATION_ID" NVARCHAR(500),
            "SOURCE" NVARCHAR(100),
            "DESTINATION" NVARCHAR(100),
            "STATUS" NVARCHAR(50),
            "START_TIME" TIMESTAMP,
            "END_TIME" TIMESTAMP,
            "SCENARIO_NAME" NVARCHAR(1000),
            "ERROR_CODE" NVARCHAR(500),
            "ERROR_MESSAGE" NCLOB,
            "RAW_PAYLOAD" NCLOB,
            "INGESTED_AT" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    _create_table(cursor, f"""
        CREATE TABLE "{SCHEMA}"."NDORBITCUSTOMISED_CPI_CLASSIFIED_LOGS" (
            "ID" NVARCHAR(200) PRIMARY KEY,
            "RAW_LOG_ID" NVARCHAR(200),
            "CORRELATION_ID" NVARCHAR(500),
            "PROCESS_GROUP" NVARCHAR(300),
            "PROCESS_ROUTE" NVARCHAR(300),
            "STATUS" NVARCHAR(50),
            "INCIDENT_ID" NVARCHAR(200),
            "SCENARIO_TITLE" NVARCHAR(1000),
            "SOURCE_SYSTEM" NVARCHAR(200),
            "DESTINATION_SYSTEM" NVARCHAR(200),
            "LOG_TIMESTAMP" TIMESTAMP,
            "ROOT_CAUSE" NCLOB,
            "RECOMMENDATIONS" NCLOB,
            "FLOW_STEPS" NCLOB,
            "TIMELINE_EVENTS" NCLOB,
            "ERROR_DETAIL" NCLOB,
            "IS_PENDING_APPROVAL" INTEGER DEFAULT 0,
            "IS_AUTO_FIXED" INTEGER DEFAULT 0,
            "IS_FIX_FAILED" INTEGER DEFAULT 0,
            "RESOLUTION_MINUTES" INTEGER,
            "CLASSIFIED_AT" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    _create_table(cursor, f"""
        CREATE TABLE "{SCHEMA}"."NDORBITCUSTOMISED_CPI_INGESTION_STATUS" (
            "ID" INTEGER PRIMARY KEY,
            "STATUS" NVARCHAR(50) DEFAULT 'idle',
            "STARTED_AT" TIMESTAMP,
            "COMPLETED_AT" TIMESTAMP,
            "TOTAL_FETCHED" INTEGER DEFAULT 0,
            "TOTAL_CLASSIFIED" INTEGER DEFAULT 0,
            "ERROR_MESSAGE" NCLOB,
            "LAST_UPDATED" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

    try:
        cursor.execute(f'SELECT COUNT(*) FROM "{SCHEMA}"."NDORBITCUSTOMISED_CPI_INGESTION_STATUS" WHERE "ID" = 1')
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                f'INSERT INTO "{SCHEMA}"."NDORBITCUSTOMISED_CPI_INGESTION_STATUS" ("ID", "STATUS") VALUES (1, \'idle\')'
            )
            conn.commit()
    except Exception as e:
        logger.warning(f"Ingestion status seed: {e}")

    cursor.close()
    conn.close()
    logger.info("Database initialized")
