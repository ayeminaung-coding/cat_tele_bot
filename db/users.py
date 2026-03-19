"""
db/users.py — User CRUD operations via Supabase.
"""
from typing import Optional
from db.client import get_supabase
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
