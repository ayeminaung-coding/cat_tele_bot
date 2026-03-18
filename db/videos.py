"""
db/videos.py — Fetching videos from DB.
"""
from typing import List, Dict, Any
from db.client import get_supabase


async def get_all_videos() -> List[Dict[str, Any]]:
    """Fetch all videos, ordered by ID."""
    sb = get_supabase()
    result = sb.table("videos").select("*").order("id").execute()
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
