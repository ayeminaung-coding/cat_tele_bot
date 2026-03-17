"""
utils/retry.py — Retry wrapper for async Telegram API calls.
"""
import asyncio
import logging
from typing import Callable, TypeVar, Awaitable

from telegram.error import TelegramError

T = TypeVar("T")
logger = logging.getLogger(__name__)


async def async_retry(
    coro_fn: Callable[[], Awaitable[T]],
    retries: int = 3,
    delay: float = 1.0,
    label: str = "operation",
) -> T:
    """
    Retry an async coroutine on TelegramError.
    Raises the final exception if all retries fail.
    """
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return await coro_fn()
        except TelegramError as e:
            last_exc = e
            logger.warning(f"[retry] {label} attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                await asyncio.sleep(delay * attempt)
    raise last_exc  # type: ignore
