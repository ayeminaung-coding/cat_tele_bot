"""
db/storage.py — Supabase Storage for payment screenshots.
"""
import uuid
import logging
from db.client import get_supabase
from config import settings

logger = logging.getLogger(__name__)

BUCKET = "screenshots"
ALLOWED_MIME = {"image/jpeg", "image/png"}


async def upload_screenshot(
    file_bytes: bytes,
    mime_type: str,
    user_id: int,
) -> str:
    """
    Upload a screenshot to Supabase Storage.
    Returns a signed URL valid for 24 hours.
    Raises ValueError on invalid type/size.
    """
    # ── Validate ────────────────────────────────────────────
    if mime_type not in ALLOWED_MIME:
        raise ValueError(f"invalid_mime:{mime_type}")
    if len(file_bytes) > settings.MAX_FILE_SIZE:
        raise ValueError(f"file_too_large:{len(file_bytes)}")

    # ── Build unique path ───────────────────────────────────
    ext = "jpg" if mime_type == "image/jpeg" else "png"
    filename = f"{user_id}/{uuid.uuid4().hex}.{ext}"

    # ── Upload ──────────────────────────────────────────────
    sb = get_supabase()
    sb.storage.from_(BUCKET).upload(
        path=filename,
        file=file_bytes,
        file_options={"content-type": mime_type},
    )
    logger.info(f"Uploaded screenshot: {filename}")

    # ── Return signed URL (24 h = 86400 s) ─────────────────
    result = sb.storage.from_(BUCKET).create_signed_url(filename, expires_in=86400)
    return result["signedURL"]
