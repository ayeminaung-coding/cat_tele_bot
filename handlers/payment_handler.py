"""
handlers/payment_handler.py — Handles screenshot uploads from users.
"""
import logging
import io
from telegram import Update, PhotoSize, Document
from telegram.ext import ContextTypes

from db.storage import upload_screenshot
from db.payments import create_payment, set_admin_msg_id
from db.logs import log_action
from data.messages import (
    PAYMENT_RECEIVED,
    INVALID_FILE_TYPE,
    FILE_TOO_LARGE,
    NOT_IN_PAYMENT_FLOW,
    UPLOAD_FAILED,
)
from utils.session import AWAITING_SCREENSHOT
from handlers.admin_handler import forward_to_admin

logger = logging.getLogger(__name__)

# Accepted MIME types
ALLOWED_MIME = {"image/jpeg", "image/png"}


async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Called when a user sends a photo or image document in private chat.
    Guards: session must be AWAITING_SCREENSHOT.
    """
    user = update.effective_user
    sm = context.bot_data["session_manager"]
    session = await sm.get(user.id)

    # ── Guard: must be in payment flow ─────────────────────
    if session["state"] != AWAITING_SCREENSHOT:
        await update.message.reply_text(NOT_IN_PAYMENT_FLOW)
        return

    plan_id: str = session["plan_id"]
    amount: int = session["amount"]

    # ── Determine file source (photo vs document) ───────────
    mime_type = "image/jpeg"
    file_id = None
    file_size = 0

    if update.message.photo:
        # Telegram compressed photo — largest size
        photo: PhotoSize = update.message.photo[-1]
        file_id = photo.file_id
        file_size = photo.file_size or 0
        mime_type = "image/jpeg"

    elif update.message.document:
        doc: Document = update.message.document
        mime_type = doc.mime_type or ""
        file_size = doc.file_size or 0

        # Validate MIME
        if mime_type not in ALLOWED_MIME:
            await update.message.reply_text(INVALID_FILE_TYPE)
            return

        file_id = doc.file_id

    if not file_id:
        await update.message.reply_text(INVALID_FILE_TYPE)
        return

    # ── Validate file size ──────────────────────────────────
    from config import settings
    if file_size > settings.MAX_FILE_SIZE:
        await update.message.reply_text(FILE_TOO_LARGE)
        return

    # ── Download from Telegram ──────────────────────────────
    try:
        tg_file = await context.bot.get_file(file_id)
        buf = io.BytesIO()
        await tg_file.download_to_memory(buf)
        file_bytes = buf.getvalue()
    except Exception as e:
        logger.error(f"Failed to download file from Telegram: {e}")
        await update.message.reply_text(UPLOAD_FAILED)
        return

    # ── Upload to Supabase Storage ──────────────────────────
    try:
        screenshot_url = await upload_screenshot(file_bytes, mime_type, user.id)
    except ValueError as e:
        err = str(e)
        if "invalid_mime" in err:
            await update.message.reply_text(INVALID_FILE_TYPE)
        elif "file_too_large" in err:
            await update.message.reply_text(FILE_TOO_LARGE)
        else:
            await update.message.reply_text(UPLOAD_FAILED)
        return
    except Exception as e:
        logger.error(f"Supabase upload failed: {e}")
        await update.message.reply_text(UPLOAD_FAILED)
        return

    # ── Create payment record ───────────────────────────────
    payment_id = await create_payment(
        user_id=user.id,
        plan_id=plan_id,
        amount=amount,
        screenshot_url=screenshot_url,
    )

    # ── Notify user ─────────────────────────────────────────
    await update.message.reply_text(PAYMENT_RECEIVED)

    # ── Reset session ───────────────────────────────────────
    await sm.reset(user.id)

    # ── Forward to admin group ──────────────────────────────
    admin_msg_id = await forward_to_admin(
        context=context,
        payment_id=payment_id,
        user_id=user.id,
        username=user.username,
        first_name=user.first_name or "User",
        plan_id=plan_id,
        amount=amount,
        file_id=file_id,
    )

    if admin_msg_id:
        await set_admin_msg_id(payment_id, admin_msg_id)

    await log_action(
        action_type="payment_submitted",
        user_id=user.id,
        payment_id=payment_id,
        detail=f"plan={plan_id} amount={amount}",
    )
