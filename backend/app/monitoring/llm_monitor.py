import json
import logging
import threading
import requests
from app.config import settings

logger = logging.getLogger(__name__)

_BASE_URL = settings.LLM_USAGE_MONITOR_BASE_URL
_API_KEY = settings.LLM_USAGE_MONITOR_API_KEY
_APP_ID = settings.LLM_USAGE_MONITOR_APP_ID
_MODEL_NAME = settings.LLM_USAGE_MONITOR_MODEL_NAME
_CALL_TYPE_L = settings.LLM_USAGE_MONITOR_CALL_TYPE_L_INVOKE
_CALL_TYPE_A = settings.LLM_USAGE_MONITOR_CALL_TYPE_A_INVOKE


def _post(call_type: str, metadata: str) -> None:
    if not _BASE_URL:
        return
    try:
        requests.post(
            f"{_BASE_URL.rstrip('/')}/log-metadata/",
            params={
                "app_id": _APP_ID,
                "call_type": call_type,
                "model_name": _MODEL_NAME,
            },
            headers={"Authorization": f"Bearer {_API_KEY}"},
            json={"metadata": metadata},
            timeout=10,
        )
    except Exception as exc:
        logger.warning("LLM usage monitor POST failed: %s", exc)


def _fire(call_type: str, metadata: str) -> None:
    t = threading.Thread(target=_post, args=(call_type, metadata), daemon=True)
    t.start()


def log_llm_invoke(response_data: dict) -> None:
    """Call after every direct LLM HTTP response (l_invoke)."""
    try:
        metadata = json.dumps(response_data, default=str)
    except Exception:
        metadata = str(response_data)
    _fire(_CALL_TYPE_L, metadata)


def log_agent_invoke(result) -> None:
    """Call after every LangChain agent invocation (a_invoke). Not used currently."""
    try:
        from langchain_core.load import dumps as lc_dumps
        metadata = lc_dumps(result)
    except Exception:
        metadata = str(result)
    _fire(_CALL_TYPE_A, metadata)
