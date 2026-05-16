"""
utils/rate_limiter.py — Simple rate limiter for Telegram bot commands.
"""
import asyncio
import time
from collections import defaultdict
from typing import DefaultDict, List, Tuple

from telegram import Update
from telegram.ext import ContextTypes


class RateLimiter:
    """
    In-memory rate limiter using a sliding window approach.
    Tracks requests per user within a time window.
    """

    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: int = 60,
        cooldown_seconds: int = 30,
    ) -> None:
        """
        Args:
            max_requests: Maximum requests allowed within the window.
            window_seconds: Time window in seconds.
            cooldown_seconds: Cooldown period when rate limit is exceeded.
        """
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._cooldown_seconds = cooldown_seconds
        # user_id -> list of timestamps
        self._requests: DefaultDict[int, List[float]] = defaultdict(list)
        # user_id -> cooldown end timestamp
        self._cooldowns: DefaultDict[int, float] = defaultdict(float)
        self._lock = asyncio.Lock()

    async def is_rate_limited(self, user_id: int) -> Tuple[bool, float]:
        """
        Check if a user is rate limited.

        Returns:
            Tuple of (is_limited, remaining_cooldown_seconds).
            If not limited, remaining_cooldown_seconds is 0.
        """
        now = time.time()

        async with self._lock:
            # Check if user is in cooldown
            if self._cooldowns[user_id] > now:
                remaining = self._cooldowns[user_id] - now
                return True, remaining

            # Clear old requests outside the window
            window_start = now - self._window_seconds
            self._requests[user_id] = [
                ts for ts in self._requests[user_id] if ts > window_start
            ]

            # Check if rate limit exceeded
            if len(self._requests[user_id]) >= self._max_requests:
                # Start cooldown
                self._cooldowns[user_id] = now + self._cooldown_seconds
                return True, self._cooldown_seconds

            # Record this request
            self._requests[user_id].append(now)
            return False, 0.0

    async def reset(self, user_id: int) -> None:
        """Reset rate limit for a user (e.g., for admin users)."""
        async with self._lock:
            self._requests.pop(user_id, None)
            self._cooldowns.pop(user_id, None)


# Global rate limiter instance for user commands
_user_rate_limiter = RateLimiter(max_requests=10, window_seconds=60, cooldown_seconds=30)


async def check_user_rate_limit(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """
    Check rate limit for a user. Sends a warning message if rate limited.

    Returns:
        True if the request should be blocked (rate limited).
        False if the request can proceed.
    """
    if not update.effective_user:
        return False

    user_id = update.effective_user.id
    is_limited, remaining = await _user_rate_limiter.is_rate_limited(user_id)

    if is_limited:
        if update.effective_message:
            await update.effective_message.reply_text(
                f"⚠️ စောပါသေးသည်။ {int(remaining) + 1}စက္ကန့် အကြာတွင် ထပ်မံကြိုးစားပါ။"
            )
        return True

    return False


async def reset_user_rate_limit(user_id: int) -> None:
    """Reset rate limit for a specific user (e.g., for admins)."""
    await _user_rate_limiter.reset(user_id)
