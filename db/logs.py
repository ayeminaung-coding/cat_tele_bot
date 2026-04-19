"""
db/logs.py — Action logging to Supabase logs table.
"""
from typing import Optional
from db.client import get_supabase
import logging
from utils.db_async import run_blocking

logger = logging.getLogger(__name__)


async def log_action(
    action_type: str,
    admin_id: Optional[int] = None,
    user_id: Optional[int] = None,
    order_id: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    """
    Log an action to Supabase asynchronously.
    Falls back to console log if Supabase fails.
    """
    try:
        sb = get_supabase()
        await run_blocking(
            lambda: sb.table("logs").insert({
                "action_type": action_type,
                "admin_id": admin_id,
                "user_id": user_id,
                "order_id": order_id,
                "detail": detail,
            }).execute()
        )
    except Exception as e:
        logger.error(f"[LOG FALLBACK] action={action_type} user={user_id} detail={detail} | err={e}")


async def count_user_actions(
    action_type: str,
    user_id: int,
    detail: Optional[str] = None,
) -> int:
    """Count matching log actions for a user (optionally by exact detail)."""
    sb = get_supabase()

    def _query():
        q = sb.table("logs").select("id", count="exact").eq("action_type", action_type).eq("user_id", user_id)
        if detail is not None:
            q = q.eq("detail", detail)
        return q.limit(0).execute()

    result = await run_blocking(_query)
    return result.count if result.count is not None else 0
