"""
utils/session.py — Async-safe in-memory session manager.

States:
    IDLE                 → initial / after reset
    PLAN_SELECTED        → user chose a plan
    AWAITING_SCREENSHOT  → payment instructions shown, waiting for image
"""
import asyncio
import time
from typing import Optional

SESSION_TTL = 30 * 60  # 30 minutes idle → auto-reset

IDLE = "IDLE"
PLAN_SELECTED = "PLAN_SELECTED"
AWAITING_SCREENSHOT = "AWAITING_SCREENSHOT"


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[int, dict] = {}
        self._lock = asyncio.Lock()

    def _default(self) -> dict:
        return {
            "state": IDLE,
            "plan_id": None,
            "amount": None,
            "updated_at": time.time(),
        }

    async def get(self, user_id: int) -> dict:
        async with self._lock:
            session = self._sessions.get(user_id, self._default())
            # Auto-expire idle sessions
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
