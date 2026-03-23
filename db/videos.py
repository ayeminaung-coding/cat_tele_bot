"""
db/videos.py — Fetching and managing videos in DB.
"""
import uuid
from typing import List, Dict, Any
from db.client import get_supabase
from utils.db_async import run_blocking


async def get_all_videos() -> List[Dict[str, Any]]:
    """Fetch all videos, ordered by created_at."""
    sb = get_supabase()
    result = await run_blocking(lambda: sb.table("videos").select("*").order("created_at", desc=True).execute())
    return result.data


async def get_video(video_id: str) -> Dict[str, Any] | None:
    """Fetch a single video by ID."""
    sb = get_supabase()
    result = await run_blocking(
        lambda: sb.table("videos")
        .select("*")
        .eq("id", video_id)
        .maybe_single()
        .execute()
    )
    return result.data


async def add_video(title: str, price: int) -> Dict[str, Any]:
    """Insert a new video. Returns the created row."""
    sb = get_supabase()
    # Use UUID-based IDs to avoid collisions when admins add videos in the same second.
    video_id = f"vid_{uuid.uuid4().hex[:12]}"
    result = await run_blocking(
        lambda: sb.table("videos")
        .insert({"id": video_id, "title": title, "price": price, "status": "available"})
        .execute()
    )
    if result and hasattr(result, "data") and result.data:
        return result.data[0]

    # Some API paths can return an empty representation; verify the row exists.
    verify = await run_blocking(
        lambda: sb.table("videos")
        .select("*")
        .eq("id", video_id)
        .maybe_single()
        .execute()
    )
    if verify and hasattr(verify, "data") and verify.data:
        return verify.data

    raise RuntimeError("Insert failed: no row returned and no row found by id")


async def delete_video(video_id: str) -> None:
    """Hard-delete a video by ID."""
    sb = get_supabase()
    await run_blocking(lambda: sb.table("videos").delete().eq("id", video_id).execute())


async def set_video_link(video_id: str, link: str) -> None:
    """Store a channel/invite link for a specific video."""
    sb = get_supabase()
    await run_blocking(
        lambda: sb.table("videos").update({"channel_link": link}).eq("id", video_id).execute()
    )

async def set_video_channel_id(video_id: str, channel_id: int) -> None:
    """Store a channel ID for a specific video."""
    sb = get_supabase()
    await run_blocking(
        lambda: sb.table("videos").update({"channel_id": channel_id}).eq("id", video_id).execute()
    )

