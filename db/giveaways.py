"""
db/giveaways.py — Giveaway CRUD operations via Supabase.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from db.client import get_supabase
from utils.db_async import run_blocking


async def create_giveaway(
    channel_id: int,
    post_id: int,
    discussion_chat_id: int,
    winner_count: int,
    created_by: Optional[int],
) -> dict:
    sb = get_supabase()
    payload = {
        "channel_id": channel_id,
        "post_id": post_id,
        "discussion_chat_id": discussion_chat_id,
        "winner_count": winner_count,
        "created_by": created_by,
    }
    result = await run_blocking(lambda: sb.table("giveaways").insert(payload).execute())
    return result.data[0] if result.data else payload


async def get_giveaway_by_id(giveaway_id: str) -> Optional[dict]:
    sb = get_supabase()
    result = await run_blocking(
        lambda: sb.table("giveaways").select("*").eq("id", giveaway_id).maybe_single().execute()
    )
    return result.data


async def get_active_giveaway_by_post(channel_id: int, post_id: int) -> Optional[dict]:
    sb = get_supabase()
    result = await run_blocking(
        lambda: sb.table("giveaways")
        .select("*")
        .eq("channel_id", channel_id)
        .eq("post_id", post_id)
        .eq("status", "active")
        .maybe_single()
        .execute()
    )
    return result.data


async def mark_giveaway_drawn(giveaway_id: str, winner_user_ids: list[int]) -> None:
    sb = get_supabase()
    now = datetime.now(timezone.utc).isoformat()
    await run_blocking(
        lambda: sb.table("giveaways")
        .update({
            "status": "drawn",
            "winner_user_ids": winner_user_ids,
            "drawn_at": now,
        })
        .eq("id", giveaway_id)
        .execute()
    )


async def close_giveaway(giveaway_id: str) -> None:
    sb = get_supabase()
    now = datetime.now(timezone.utc).isoformat()
    await run_blocking(
        lambda: sb.table("giveaways")
        .update({"status": "closed", "closed_at": now})
        .eq("id", giveaway_id)
        .execute()
    )
