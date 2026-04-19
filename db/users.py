"""
db/users.py — User CRUD operations via Supabase.
"""
from typing import Optional
from db.client import get_supabase
from db.orders import get_approved_order_user_ids, get_all_order_user_ids
from utils.db_async import run_blocking


async def upsert_user(telegram_id: int, username: Optional[str], first_name: str) -> dict:
    """Insert or update a user record. Returns the upserted row."""
    sb = get_supabase()
    data = {
        "telegram_id": telegram_id,
        "username": username,
        "first_name": first_name,
    }
    result = await run_blocking(
        lambda: sb.table("users")
        .upsert(data, on_conflict="telegram_id", ignore_duplicates=False)
        .execute()
    )
    return result.data[0] if result.data else data


async def get_user(telegram_id: int) -> Optional[dict]:
    """Fetch a user by telegram_id. Returns None if not found."""
    sb = get_supabase()
    result = await run_blocking(
        lambda: sb.table("users")
        .select("*")
        .eq("telegram_id", telegram_id)
        .maybe_single()
        .execute()
    )
    return result.data


async def set_user_status(telegram_id: int, status: str) -> None:
    """Update user status: 'active' | 'pending' | 'banned'."""
    sb = get_supabase()
    await run_blocking(
        lambda: sb.table("users").update({"status": status}).eq("telegram_id", telegram_id).execute()
    )


async def get_user_stats() -> dict:
    """Fetch total users and users joined today."""
    from datetime import datetime, timezone
    sb = get_supabase()
    
    # Total users
    res_total = await run_blocking(
        lambda: sb.table("users").select("telegram_id", count="exact").limit(0).execute()
    )
    total = res_total.count if res_total.count is not None else 0
    
    # Daily users (joined today)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    res_daily = await run_blocking(
        lambda: sb.table("users")
        .select("telegram_id", count="exact")
        .gte("created_at", today_start)
        .limit(0)
        .execute()
    )
    daily = res_daily.count if res_daily.count is not None else 0
    
    return {"total": total, "daily": daily}


async def get_active_user_ids() -> list[int]:
    """Return all non-banned users."""
    sb = get_supabase()
    result = await run_blocking(
        lambda: sb.table("users").select("telegram_id").neq("status", "banned").execute()
    )
    rows = result.data or []
    return [int(row["telegram_id"]) for row in rows if row.get("telegram_id") is not None]


async def _filter_active(user_ids: list[int]) -> list[int]:
    if not user_ids:
        return []
    sb = get_supabase()
    result = await run_blocking(
        lambda: sb.table("users")
        .select("telegram_id")
        .neq("status", "banned")
        .in_("telegram_id", user_ids)
        .execute()
    )
    rows = result.data or []
    return [int(row["telegram_id"]) for row in rows if row.get("telegram_id") is not None]


async def get_paid_user_ids() -> list[int]:
    """Users that have at least one approved order."""
    ids = await get_approved_order_user_ids()
    return await _filter_active(ids)


async def get_single_buyer_user_ids() -> list[int]:
    """Users that have at least one approved single order."""
    ids = await get_approved_order_user_ids(order_type="single")
    return await _filter_active(ids)


async def get_bundle_buyer_user_ids() -> list[int]:
    """Users that have at least one approved bundle order."""
    ids = await get_approved_order_user_ids(order_type="bundle")
    return await _filter_active(ids)


async def get_no_order_user_ids() -> list[int]:
    """Users that have never placed an order."""
    active_ids = set(await get_active_user_ids())
    ordered_ids = set(await get_all_order_user_ids())
    return list(active_ids - ordered_ids)
