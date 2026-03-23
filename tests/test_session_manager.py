import asyncio

from utils.session import InMemorySessionManager


async def _user_flow(manager: InMemorySessionManager, user_id: int) -> None:
    await manager.set(user_id, state="SELECTING_VIDEO", amount=1000)
    data = await manager.get(user_id)
    assert data["state"] == "SELECTING_VIDEO"
    assert data["amount"] == 1000
    await manager.reset(user_id)
    data = await manager.get(user_id)
    assert data["state"] == "IDLE"


async def test_inmemory_session_concurrency() -> None:
    manager = InMemorySessionManager()
    await asyncio.gather(*(_user_flow(manager, uid) for uid in range(1, 201)))


async def test_same_user_updates_are_consistent() -> None:
    manager = InMemorySessionManager()

    async def writer(amount: int) -> None:
        await manager.set(42, amount=amount)

    await asyncio.gather(*(writer(i) for i in range(50)))
    data = await manager.get(42)
    assert data["amount"] in set(range(50))
