import asyncio

from utils.update_dispatcher import UpdateDispatcher


class FakeApp:
    def __init__(self) -> None:
        self.bot = object()
        self.processed: list[dict] = []

    async def process_update(self, update: dict) -> None:
        await asyncio.sleep(0.001)
        self.processed.append(update)


async def test_dispatcher_processes_updates() -> None:
    app = FakeApp()
    dispatcher = UpdateDispatcher(
        app=app,
        workers=4,
        queue_size=16,
        decode_fn=lambda raw, _bot: raw,
    )

    await dispatcher.start()
    for i in range(10):
        assert dispatcher.enqueue_raw({"id": i}) is True

    await asyncio.wait_for(_wait_processed(app, 10), timeout=2)
    await dispatcher.stop()

    processed_ids = sorted(item["id"] for item in app.processed)
    assert processed_ids == list(range(10))


async def test_dispatcher_returns_false_when_queue_is_full() -> None:
    app = FakeApp()
    dispatcher = UpdateDispatcher(
        app=app,
        workers=1,
        queue_size=1,
        decode_fn=lambda raw, _bot: raw,
    )
    assert dispatcher.enqueue_raw({"id": 1}) is True
    assert dispatcher.enqueue_raw({"id": 2}) is False


async def _wait_processed(app: FakeApp, expected: int) -> None:
    while len(app.processed) < expected:
        await asyncio.sleep(0.01)
