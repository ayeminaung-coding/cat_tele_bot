"""
utils/session.py — Session manager with in-memory and Redis backends.
"""
import asyncio
import json
import time
from typing import Any, Protocol

from config import settings

SESSION_TTL = 30 * 60  # 30 minutes idle

IDLE = "IDLE"
SELECTING_VIDEO = "SELECTING_VIDEO"
AWAITING_SCREENSHOT = "AWAITING_SCREENSHOT"


class SessionManager:
    """Compatibility alias to keep existing imports working."""


class SessionManagerProtocol(Protocol):
    async def get(self, user_id: int) -> dict: ...
    async def set(self, user_id: int, **kwargs) -> None: ...
    async def reset(self, user_id: int) -> None: ...
    async def get_state(self, user_id: int) -> str: ...
    async def close(self) -> None: ...


class InMemorySessionManager:
    def __init__(self) -> None:
        self._sessions: dict[int, dict] = {}
        self._locks: dict[int, asyncio.Lock] = {}
        self._locks_guard = asyncio.Lock()

    async def _get_lock(self, user_id: int) -> asyncio.Lock:
        lock = self._locks.get(user_id)
        if lock is not None:
            return lock
        async with self._locks_guard:
            return self._locks.setdefault(user_id, asyncio.Lock())

    def _default(self) -> dict:
        return {
            "state": IDLE,
            "order_type": None,  # 'single' or 'bundle'
            "video_id": None,    # populated if 'single'
            "amount": None,      # 1000 or 5000
            "updated_at": time.time(),
        }

    async def get(self, user_id: int) -> dict:
        lock = await self._get_lock(user_id)
        async with lock:
            session = self._sessions.get(user_id, self._default())
            if time.time() - session.get("updated_at", 0) > SESSION_TTL:
                session = self._default()
                self._sessions[user_id] = session
            return dict(session)

    async def set(self, user_id: int, **kwargs) -> None:
        lock = await self._get_lock(user_id)
        async with lock:
            current = self._sessions.get(user_id, self._default())
            current.update(kwargs)
            current["updated_at"] = time.time()
            self._sessions[user_id] = current

    async def reset(self, user_id: int) -> None:
        lock = await self._get_lock(user_id)
        async with lock:
            self._sessions[user_id] = self._default()

    async def get_state(self, user_id: int) -> str:
        session = await self.get(user_id)
        return session["state"]

    async def close(self) -> None:
        return None


class RedisSessionManager:
    def __init__(self, redis_url: str) -> None:
        try:
            import redis.asyncio as redis
        except ImportError as exc:
            raise RuntimeError("redis package is required for RedisSessionManager") from exc

        self._redis = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        self._locks: dict[int, asyncio.Lock] = {}
        self._locks_guard = asyncio.Lock()

    async def _get_lock(self, user_id: int) -> asyncio.Lock:
        """Get or create a per-user lock for thread-safe session updates."""
        lock = self._locks.get(user_id)
        if lock is not None:
            return lock
        async with self._locks_guard:
            return self._locks.setdefault(user_id, asyncio.Lock())

    def _key(self, user_id: int) -> str:
        return f"session:{user_id}"

    def _default(self) -> dict:
        return {
            "state": IDLE,
            "order_type": None,
            "video_id": None,
            "amount": None,
            "updated_at": time.time(),
        }

    async def _reset_locked(self, user_id: int) -> None:
        """Reset session while caller already holds the per-user lock."""
        await self._redis.set(self._key(user_id), json.dumps(self._default()), ex=SESSION_TTL)

    async def _read_locked(self, user_id: int) -> dict:
        """Read/validate session while caller already holds the per-user lock."""
        payload = await self._redis.get(self._key(user_id))
        if not payload:
            return self._default()

        try:
            session = json.loads(payload)
            if time.time() - session.get("updated_at", 0) > SESSION_TTL:
                await self._reset_locked(user_id)
                return self._default()
            return session
        except Exception:
            await self._reset_locked(user_id)
            return self._default()

    async def get(self, user_id: int) -> dict:
        lock = await self._get_lock(user_id)
        async with lock:
            return await self._read_locked(user_id)

    async def set(self, user_id: int, **kwargs) -> None:
        lock = await self._get_lock(user_id)
        async with lock:
            current = await self._read_locked(user_id)
            current.update(kwargs)
            current["updated_at"] = time.time()
            await self._redis.set(self._key(user_id), json.dumps(current), ex=SESSION_TTL)

    async def reset(self, user_id: int) -> None:
        lock = await self._get_lock(user_id)
        async with lock:
            await self._reset_locked(user_id)

    async def get_state(self, user_id: int) -> str:
        session = await self.get(user_id)
        return session["state"]

    async def close(self) -> None:
        await self._redis.aclose()


def create_session_manager() -> SessionManagerProtocol:
    if settings.REDIS_URL:
        return RedisSessionManager(settings.REDIS_URL)
    return InMemorySessionManager()


SessionManager = InMemorySessionManager
