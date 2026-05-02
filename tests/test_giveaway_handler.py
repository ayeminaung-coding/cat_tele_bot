import os
from types import SimpleNamespace

import pytest

# Ensure config can load for handler imports
os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("WEBHOOK_URL", "https://example.com")
os.environ.setdefault("ADMIN_GROUP_ID", "-1001")
os.environ.setdefault("VIP_CHANNEL_ID", "-2001")
os.environ.setdefault("DISCUSSION_GROUP_ID", "-3001")
os.environ.setdefault("ADMIN_IDS", "123")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-key")

from handlers import giveaway_handler


class FakeBot:
    def __init__(self, chat_id: int) -> None:
        self._chat_id = chat_id

    async def get_chat(self, _username: str):
        return SimpleNamespace(id=self._chat_id)


class FakeContext:
    def __init__(self, chat_id: int) -> None:
        self.bot = FakeBot(chat_id)
        self.args = []


@pytest.mark.asyncio
async def test_parse_post_ref_private_link() -> None:
    ctx = FakeContext(chat_id=-100999)
    channel_id, post_id = await giveaway_handler._parse_post_ref(
        "https://t.me/c/123456789/555",
        ctx,
    )
    assert channel_id == -100123456789
    assert post_id == 555


@pytest.mark.asyncio
async def test_parse_post_ref_public_link() -> None:
    ctx = FakeContext(chat_id=-100777)
    channel_id, post_id = await giveaway_handler._parse_post_ref(
        "https://t.me/MyChannel/321",
        ctx,
    )
    assert channel_id == -100777
    assert post_id == 321


@pytest.mark.asyncio
async def test_handle_giveaway_comment_inserts_once(monkeypatch) -> None:
    giveaway = {"id": "gid-1"}
    calls = {"entries": 0, "logs": 0}

    async def fake_get_active_giveaway_by_post(channel_id: int, post_id: int):
        return giveaway

    async def fake_create_giveaway_entry(**_kwargs):
        calls["entries"] += 1
        # First insert succeeds, duplicate ignored
        return calls["entries"] == 1

    async def fake_log_action(**_kwargs):
        calls["logs"] += 1

    monkeypatch.setattr(giveaway_handler, "get_active_giveaway_by_post", fake_get_active_giveaway_by_post)
    monkeypatch.setattr(giveaway_handler, "create_giveaway_entry", fake_create_giveaway_entry)
    monkeypatch.setattr(giveaway_handler, "log_action", fake_log_action)

    origin_chat = SimpleNamespace(id=-100111)
    forward_origin = SimpleNamespace(type="channel", chat=origin_chat, message_id=77)
    replied = SimpleNamespace(forward_origin=forward_origin)

    user = SimpleNamespace(id=555, username="user", first_name="User")
    message = SimpleNamespace(
        from_user=user,
        reply_to_message=replied,
        text="first comment",
        caption=None,
        message_id=901,
        chat_id=-3001,
        date=None,
    )
    update = SimpleNamespace(message=message)

    await giveaway_handler.handle_giveaway_comment(update, SimpleNamespace())
    await giveaway_handler.handle_giveaway_comment(update, SimpleNamespace())

    assert calls["entries"] == 2
    assert calls["logs"] == 1


@pytest.mark.asyncio
async def test_giveaway_draw_dedupes_users(monkeypatch) -> None:
    entries = [
        {"user_id": 1, "username": "a", "first_name": "A"},
        {"user_id": 1, "username": "a", "first_name": "A"},
        {"user_id": 2, "username": "b", "first_name": "B"},
    ]
    giveaway = {"id": "gid-2", "winner_count": 2, "status": "active"}
    captured = {"winners": None, "replies": []}

    async def fake_get_giveaway_by_id(_gid: str):
        return giveaway

    async def fake_list_entries(**_kwargs):
        return entries

    async def fake_mark_drawn(giveaway_id: str, winner_user_ids: list[int]):
        captured["winners"] = winner_user_ids

    async def fake_log_action(**_kwargs):
        return None

    def fake_sample(items, k: int):
        return list(items)[:k]

    async def reply_text(text: str):
        captured["replies"].append(text)

    message = SimpleNamespace(reply_text=reply_text)
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=123))
    context = SimpleNamespace(args=["gid-2"], bot=None)

    monkeypatch.setattr(giveaway_handler, "get_giveaway_by_id", fake_get_giveaway_by_id)
    monkeypatch.setattr(giveaway_handler, "list_giveaway_entries", fake_list_entries)
    monkeypatch.setattr(giveaway_handler, "mark_giveaway_drawn", fake_mark_drawn)
    monkeypatch.setattr(giveaway_handler, "log_action", fake_log_action)
    monkeypatch.setattr(giveaway_handler.random, "sample", fake_sample)

    await giveaway_handler.giveaway_draw_command(update, context)

    assert captured["winners"] == [1, 2]
