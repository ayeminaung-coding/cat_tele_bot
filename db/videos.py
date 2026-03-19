"""
db/videos.py — Fetching and managing videos in DB.
"""
import time
from typing import List, Dict, Any
from db.client import get_supabase


async def get_all_videos() -> List[Dict[str, Any]]:
    """Fetch all videos, ordered by created_at."""
    sb = get_supabase()
    result = sb.table("videos").select("*").order("created_at").execute()
    return result.data


async def get_video(video_id: str) -> Dict[str, Any] | None:
    """Fetch a single video by ID."""
    sb = get_supabase()
    result = (
        sb.table("videos")
        .select("*")
        .eq("id", video_id)
        .maybe_single()
        .execute()
    )
    return result.data


async def add_video(title: str, price: int) -> Dict[str, Any]:
    """Insert a new video. Returns the created row."""
    sb = get_supabase()
    video_id = f"vid_{int(time.time())}"
    result = (
        sb.table("videos")
        .insert({"id": video_id, "title": title, "price": price, "status": "available"})
        .execute()
    )
    return result.data[0]


async def delete_video(video_id: str) -> None:
    """Hard-delete a video by ID."""
    sb = get_supabase()
    sb.table("videos").delete().eq("id", video_id).execute()


async def set_video_link(video_id: str, link: str) -> None:
    """Store a channel/invite link for a specific video."""
    sb = get_supabase()
    sb.table("videos").update({"channel_link": link}).eq("id", video_id).execute()

