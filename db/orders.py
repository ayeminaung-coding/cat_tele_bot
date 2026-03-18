"""
db/orders.py — Order CRUD operations (replaces payments.py).
"""
from typing import Optional
from db.client import get_supabase


async def create_order(
    user_id: int,
    order_type: str,     # 'single' | 'bundle'
    amount: int,
    screenshot_url: str,
    video_id: Optional[str] = None,
) -> str:
    """Insert a new pending order. Returns the order UUID."""
    sb = get_supabase()
    result = (
        sb.table("orders")
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
    result = (
        sb.table("orders")
        .select("*")
        .eq("id", order_id)
        .maybe_single()
        .execute()
    )
    return result.data


async def get_order_by_admin_msg_id(admin_msg_id: int) -> Optional[dict]:
    """Find an order via the forwarded admin group message ID."""
    sb = get_supabase()
    result = (
        sb.table("orders")
        .select("*")
        .eq("admin_msg_id", admin_msg_id)
        .maybe_single()
        .execute()
    )
    return result.data


async def set_admin_msg_id(order_id: str, admin_msg_id: int) -> None:
    sb = get_supabase()
    sb.table("orders").update({"admin_msg_id": admin_msg_id}).eq("id", order_id).execute()


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
    sb.table("orders").update({"status": status}).eq("id", order_id).execute()
