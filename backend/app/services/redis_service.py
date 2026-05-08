import json
from typing import Any, List, Optional

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class RedisService:
    """
    Async service for Redis interaction.
    Used for chat history, session management, and caching.
    """

    def __init__(self) -> None:
        self._client: Optional[Any] = None
        self._enabled = REDIS_AVAILABLE

    @property
    def client(self) -> Optional[Any]:
        if not self._enabled:
            return None
        
        if self._client is None:
            try:
                self._client = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
            except Exception as e:
                logger.warning("Could not connect to Redis: %s. History features will be disabled.", e)
                self._enabled = False
                return None
        return self._client

    async def ping(self) -> bool:
        """Check if Redis is alive."""
        if not self.client:
            return False
        try:
            return await self.client.ping()
        except Exception as e:
            logger.error("Redis ping failed: %s", e)
            return False

    # ── Chat History ───────────────────────────────────────────────────────

    async def add_history(self, session_id: str, message: dict) -> None:
        """Add a message to a session's history (list)."""
        if not self.client:
            return
        try:
            key = f"chat_history:{session_id}"
            await self.client.lpush(key, json.dumps(message))
            await self.client.ltrim(key, 0, 99)  # Keep last 100 messages
            await self.client.expire(key, 86400) # Expire after 24 hours
        except Exception as e:
            logger.warning("Failed to save history to Redis: %s", e)

    async def get_history(self, session_id: str, limit: int = 10) -> List[dict]:
        """Retrieve the most recent messages for a session."""
        if not self.client:
            return []
        try:
            key = f"chat_history:{session_id}"
            items = await self.client.lrange(key, 0, limit - 1)
            return [json.loads(item) for item in items]
        except Exception as e:
            logger.warning("Failed to get history from Redis: %s", e)
            return []

    async def clear_history(self, session_id: str) -> None:
        """Delete history for a session."""
        if not self.client:
            return
        try:
            await self.client.delete(f"chat_history:{session_id}")
        except Exception as e:
            logger.warning("Failed to clear history in Redis: %s", e)

    # ── Generic Cache ──────────────────────────────────────────────────────

    async def set_cache(self, key: str, value: Any, expire: int = 3600) -> None:
        """Set a value in cache with expiration."""
        if not self.client:
            return
        try:
            await self.client.set(key, json.dumps(value), ex=expire)
        except Exception as e:
            logger.warning("Failed to set cache in Redis: %s", e)

    async def get_cache(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        if not self.client:
            return None
        try:
            val = await self.client.get(key)
            return json.loads(val) if val else None
        except Exception as e:
            logger.warning("Failed to get cache from Redis: %s", e)
            return None


# Singleton instance
redis_service = RedisService()
