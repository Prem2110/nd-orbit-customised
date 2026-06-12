import httpx
import logging
from datetime import datetime, timedelta
from app.config import settings

logger = logging.getLogger(__name__)


class AICorTokenManager:
    _token: str | None = None
    _expires_at: datetime | None = None

    async def get_token(self) -> str:
        if self._token and self._expires_at and datetime.utcnow() < self._expires_at:
            return self._token

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.AICORE_AUTH_URL}/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.AICORE_CLIENT_ID,
                    "client_secret": settings.AICORE_CLIENT_SECRET,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["access_token"]
            expires_in = int(data.get("expires_in", 3600))
            self._expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 120)
            logger.info("SAP AI Core token refreshed")
            return self._token


token_manager = AICorTokenManager()
