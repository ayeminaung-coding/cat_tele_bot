"""
db/orders.py — Order CRUD operations (replaces payments.py).
"""
from typing import Optional
from db.client import get_supabase
from utils.db_async import run_blocking


async def create_order(
    user_id: int,
    order_type: str,     # 'single' | 'bundle'
    amount: int,
    screenshot_url: str,
    video_id: Optional[str] = None,
) -> str:
    """Insert a new pending order. Returns the order UUID."""
    sb = get_supabase()
    result = await run_blocking(
        lambda: sb.table("orders")
        .insert({
            "user_id": user_id,
            "type": order_type,
            "video_id": video_id,
            "amount": amount,
            "screenshot_url": screenshot_url,
            "status": "pending",
        })
        .execute()
    )
    return result.data[0]["id"]


async def get_order_by_id(order_id: str) -> Optional[dict]:
    sb = get_supabase()
    result = await run_blocking(
        lambda: sb.table("orders")
        .select("*")
        .eq("id", order_id)
        .maybe_single()
        .execute()
    )
    return result.data


async def get_order_by_admin_msg_id(admin_msg_id: int) -> Optional[dict]:
    """Find an order via the forwarded admin group message ID."""
    sb = get_supabase()
    result = await run_blocking(
        lambda: sb.table("orders")
        .select("*")
        .eq("admin_msg_id", admin_msg_id)
        .maybe_single()
        .execute()
    )
    return result.data


async def set_admin_msg_id(order_id: str, admin_msg_id: int) -> None:
    sb = get_supabase()
    await run_blocking(
        lambda: sb.table("orders").update({"admin_msg_id": admin_msg_id}).eq("id", order_id).execute()
    )


async def is_duplicate_approval(order_id: str) -> bool:
    """Return True if this order has already been approved."""
    order = await get_order_by_id(order_id)
    return order is not None and order.get("status") == "approved"


async def update_order_status(
    order_id: str,
    status: str,
) -> None:
    """Update order status."""
    sb = get_supabase()
    await run_blocking(lambda: sb.table("orders").update({"status": status}).eq("id", order_id).execute())

async def get_order_stats() -> dict:
    """Fetch total orders for today and yesterday."""
    from datetime import datetime, timezone, timedelta
    sb = get_supabase()
    
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    
    # Today's orders
    res_today = await run_blocking(
        lambda: sb.table("orders")
        .select("id", count="exact")
        .gte("created_at", today_start.isoformat())
        .limit(0).execute()
    )
    today_count = res_today.count if res_today.count is not None else 0
    
    # Yesterday's orders
    res_yesterday = await run_blocking(
        lambda: sb.table("orders")
        .select("id", count="exact")
        .gte("created_at", yesterday_start.isoformat())
        .lt("created_at", today_start.isoformat())
        .limit(0).execute()
    )
    yesterday_count = res_yesterday.count if res_yesterday.count is not None else 0
    
    return {
        "today": today_count,
        "yesterday": yesterday_count
    }
