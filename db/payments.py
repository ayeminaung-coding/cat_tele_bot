"""
db/payments.py — Payment CRUD operations via Supabase.
"""
from typing import Optional
from db.client import get_supabase


async def create_payment(
    user_id: int,
    plan_id: str,
    amount: int,
    screenshot_url: str,
) -> str:
    """Insert a new pending payment. Returns the payment UUID."""
    sb = get_supabase()
    result = (
        sb.table("payments")
        .insert({
            "user_id": user_id,
            "plan_id": plan_id,
            "amount": amount,
            "screenshot_url": screenshot_url,
            "status": "pending",
        })
        .execute()
    )
    return result.data[0]["id"]


async def get_payment_by_id(payment_id: str) -> Optional[dict]:
    sb = get_supabase()
    result = (
        sb.table("payments")
        .select("*")
        .eq("id", payment_id)
        .maybe_single()
        .execute()
    )
    return result.data


async def get_payment_by_admin_msg_id(admin_msg_id: int) -> Optional[dict]:
    """Find a payment via the forwarded admin group message ID."""
    sb = get_supabase()
    result = (
        sb.table("payments")
        .select("*")
        .eq("admin_msg_id", admin_msg_id)
        .maybe_single()
        .execute()
    )
    return result.data


async def set_admin_msg_id(payment_id: str, admin_msg_id: int) -> None:
    sb = get_supabase()
    sb.table("payments").update({"admin_msg_id": admin_msg_id}).eq("id", payment_id).execute()


async def is_duplicate_approval(payment_id: str) -> bool:
    """Return True if this payment has already been approved."""
    payment = await get_payment_by_id(payment_id)
    return payment is not None and payment.get("status") == "approved"


async def update_payment_status(
    payment_id: str,
    status: str,
    invite_link: Optional[str] = None,
) -> None:
    """Update payment status and optionally store invite link."""
    sb = get_supabase()
    payload: dict = {"status": status}
    if invite_link:
        payload["invite_link"] = invite_link
    sb.table("payments").update(payload).eq("id", payment_id).execute()
