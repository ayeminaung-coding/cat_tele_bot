"""
db/logs.py — Action logging to Supabase logs table.
"""
from typing import Optional
from db.client import get_supabase
import logging

logger = logging.getLogger(__name__)


async def log_action(
    action_type: str,
    admin_id: Optional[int] = None,
    user_id: Optional[int] = None,
    payment_id: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    """
    Log an action to Supabase asynchronously.
    Falls back to console log if Supabase fails.
    """
    try:
        sb = get_supabase()
        sb.table("logs").insert({
            "action_type": action_type,
            "admin_id": admin_id,
            "user_id": user_id,
            "payment_id": payment_id,
            "detail": detail,
        }).execute()
    except Exception as e:
        logger.error(f"[LOG FALLBACK] action={action_type} user={user_id} detail={detail} | err={e}")
