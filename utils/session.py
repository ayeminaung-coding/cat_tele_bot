"""
utils/session.py — Async-safe in-memory session manager.
"""
import asyncio
import time

SESSION_TTL = 30 * 60  # 30 minutes idle

IDLE = "IDLE"
SELECTING_VIDEO = "SELECTING_VIDEO"
AWAITING_SCREENSHOT = "AWAITING_SCREENSHOT"


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[int, dict] = {}
        self._lock = asyncio.Lock()

    def _default(self) -> dict:
        return {
            "state": IDLE,
            "order_type": None,  # 'single' or 'bundle'
            "video_id": None,    # populated if 'single'
            "amount": None,      # 1000 or 5000
            "updated_at": time.time(),
        }

    async def get(self, user_id: int) -> dict:
        async with self._lock:
            session = self._sessions.get(user_id, self._default())
            if time.time() - session.get("updated_at", 0) > SESSION_TTL:
                session = self._default()
                self._sessions[user_id] = session
            return dict(session)

    async def set(self, user_id: int, **kwargs) -> None:
        async with self._lock:
            current = self._sessions.get(user_id, self._default())
            current.update(kwargs)
            current["updated_at"] = time.time()
            self._sessions[user_id] = current

    async def reset(self, user_id: int) -> None:
        async with self._lock:
            self._sessions[user_id] = self._default()

    async def get_state(self, user_id: int) -> str:
        session = await self.get(user_id)
        return session["state"]
