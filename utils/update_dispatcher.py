"""Queue-based dispatcher for Telegram webhook updates."""
import asyncio
import logging
import time
from typing import Any, Callable

from telegram import Update

logger = logging.getLogger(__name__)


class UpdateDispatcher:
    def __init__(
        self,
        app: Any,
        workers: int,
        queue_size: int,
        decode_fn: Callable[[dict, Any], Any] | None = None,
    ) -> None:
        self._app = app
        self._workers = max(1, workers)
        self._queue: asyncio.Queue[dict | None] = asyncio.Queue(maxsize=queue_size)
        self._tasks: list[asyncio.Task] = []
        self._decode_fn = decode_fn or (lambda raw, bot: Update.de_json(data=raw, bot=bot))
        self._running = False
        self._seen_update_ids: dict[int, float] = {}
        self._dedupe_ttl_seconds = 600
        self._dedupe_max_entries = 50000

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        for idx in range(self._workers):
            self._tasks.append(asyncio.create_task(self._worker(idx)))

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        for _ in self._tasks:
            await self._queue.put(None)
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    def enqueue_raw(self, payload: dict) -> bool:
        update_id = self._extract_update_id(payload)
        if update_id is not None:
            now = time.monotonic()
            self._prune_seen_update_ids(now)
            if update_id in self._seen_update_ids:
                logger.debug("Skipping duplicate update_id=%s", update_id)
                return True

        try:
            self._queue.put_nowait(payload)
            if update_id is not None:
                self._seen_update_ids[update_id] = time.monotonic()
            return True
        except asyncio.QueueFull:
            return False

    @staticmethod
    def _extract_update_id(payload: dict) -> int | None:
        raw_id = payload.get("update_id")
        return raw_id if isinstance(raw_id, int) else None

    def _prune_seen_update_ids(self, now: float) -> None:
        cutoff = now - self._dedupe_ttl_seconds
        while self._seen_update_ids:
            first_update_id = next(iter(self._seen_update_ids))
            first_seen = self._seen_update_ids[first_update_id]
            if first_seen >= cutoff and len(self._seen_update_ids) <= self._dedupe_max_entries:
                break
            self._seen_update_ids.pop(first_update_id, None)

    def queue_size(self) -> int:
        return self._queue.qsize()

    def queue_capacity(self) -> int:
        return self._queue.maxsize

    def worker_count(self) -> int:
        return self._workers

    async def _worker(self, worker_id: int) -> None:
        while True:
            payload = await self._queue.get()
            if payload is None:
                self._queue.task_done()
                break
            try:
                update = self._decode_fn(payload, self._app.bot)
                await self._app.process_update(update)
            except Exception as exc:
                logger.error("Worker %s failed to process update: %s", worker_id, exc)
            finally:
                self._queue.task_done()
