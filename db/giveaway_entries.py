"""
db/giveaway_entries.py — Giveaway entry operations via Supabase.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from db.client import get_supabase
from utils.db_async import run_blocking


async def create_giveaway_entry(
    giveaway_id: str,
    user_id: int,
    username: Optional[str],
    first_name: Optional[str],
    comment_text: str,
    comment_message_id: int,
    comment_chat_id: int,
    comment_created_at: Optional[datetime],
) -> bool:
    sb = get_supabase()
    payload = {
        "giveaway_id": giveaway_id,
        "user_id": user_id,
        "username": username,
        "first_name": first_name or "",
        "comment_text": comment_text,
        "comment_message_id": comment_message_id,
        "comment_chat_id": comment_chat_id,
    }
    if comment_created_at:
        payload["comment_created_at"] = comment_created_at.isoformat()
    result = await run_blocking(
        lambda: sb.table("giveaway_entries")
        .upsert(payload, on_conflict="giveaway_id,user_id", ignore_duplicates=True)
        .execute()
    )
    return bool(result.data)


async def get_giveaway_entry_count(giveaway_id: str) -> int:
    sb = get_supabase()
    result = await run_blocking(
        lambda: sb.table("giveaway_entries")
        .select("id", count="exact")
        .eq("giveaway_id", giveaway_id)
        .limit(0)
        .execute()
    )
    return result.count if result.count is not None else 0


async def list_giveaway_entries(giveaway_id: str) -> list[dict]:
    sb = get_supabase()
    result = await run_blocking(
        lambda: sb.table("giveaway_entries")
        .select("*")
        .eq("giveaway_id", giveaway_id)
        .execute()
    )
    return result.data or []


async def list_latest_entries(giveaway_id: str, limit: int = 3) -> list[dict]:
    sb = get_supabase()
    result = await run_blocking(
        lambda: sb.table("giveaway_entries")
        .select("*")
        .eq("giveaway_id", giveaway_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []
