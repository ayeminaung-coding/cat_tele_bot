"""
config.py — Loads and validates all environment variables.
"""
import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    return val


def _get_admin_ids() -> List[int]:
    raw = _require("ADMIN_IDS")
    try:
        return [int(x.strip()) for x in raw.split(",") if x.strip()]
    except ValueError:
        raise EnvironmentError("ADMIN_IDS must be comma-separated integers")


@dataclass(frozen=True)
class Settings:
    BOT_TOKEN: str
    WEBHOOK_URL: str
    ADMIN_GROUP_ID: int
    VIP_CHANNEL_ID: int
    VIP_INVITE_LINK_PAID: str
    ADMIN_IDS: List[int]
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    KBZPAY_PHONE: str
    KBZPAY_NAME: str
    PORT: int
    USE_UNIQUE_AMOUNT: bool
    MAX_FILE_SIZE: int
    REDIS_URL: str
    UPDATE_WORKERS: int
    UPDATE_QUEUE_SIZE: int
    ADMIN_REVIEW_TIME_HOURS: int
    BROADCAST_BATCH_SIZE: int
    BROADCAST_BATCH_DELAY_SECONDS: float


def load_settings() -> Settings:
    return Settings(
        BOT_TOKEN=_require("BOT_TOKEN"),
        WEBHOOK_URL=_require("WEBHOOK_URL").rstrip("/"),
        ADMIN_GROUP_ID=int(_require("ADMIN_GROUP_ID")),
        VIP_CHANNEL_ID=int(_require("VIP_CHANNEL_ID")),
        VIP_INVITE_LINK_PAID=os.getenv("VIP_INVITE_LINK_PAID", ""),
        ADMIN_IDS=_get_admin_ids(),
        SUPABASE_URL=_require("SUPABASE_URL"),
        SUPABASE_SERVICE_KEY=_require("SUPABASE_SERVICE_KEY"),
        KBZPAY_PHONE=os.getenv("KBZPAY_PHONE", "09-XXX-XXXXXXX"),
        KBZPAY_NAME=os.getenv("KBZPAY_NAME", "VIP Bot"),
        PORT=int(os.getenv("PORT", "8000")),
        USE_UNIQUE_AMOUNT=os.getenv("USE_UNIQUE_AMOUNT", "true").lower() == "true",
        MAX_FILE_SIZE=int(os.getenv("MAX_FILE_SIZE", "5242880")),
        REDIS_URL=os.getenv("REDIS_URL", "").strip(),
        UPDATE_WORKERS=int(os.getenv("UPDATE_WORKERS", "8")),
        UPDATE_QUEUE_SIZE=int(os.getenv("UPDATE_QUEUE_SIZE", "1000")),
        ADMIN_REVIEW_TIME_HOURS=int(os.getenv("ADMIN_REVIEW_TIME_HOURS", "1")),
        BROADCAST_BATCH_SIZE=int(os.getenv("BROADCAST_BATCH_SIZE", "20")),
        BROADCAST_BATCH_DELAY_SECONDS=float(os.getenv("BROADCAST_BATCH_DELAY_SECONDS", "0.4")),
    )


# Singleton — imported everywhere
settings = load_settings()
