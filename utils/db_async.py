"""Helpers to run blocking DB and storage operations off the event loop."""
import asyncio
from typing import Callable, TypeVar

T = TypeVar("T")


async def run_blocking(func: Callable[[], T]) -> T:
    """Execute a blocking callable in a worker thread."""
    return await asyncio.to_thread(func)
