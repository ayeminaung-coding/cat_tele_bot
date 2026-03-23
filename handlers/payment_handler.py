"""
handlers/payment_handler.py — Handles screenshot uploads from users.
"""
import logging
import io
from telegram import Update, PhotoSize, Document
from telegram.ext import ContextTypes

from db.storage import upload_screenshot
from db.orders import create_order, set_admin_msg_id
from db.videos import get_video
from db.logs import log_action
from data.messages import (
    PAYMENT_RECEIVED,
    INVALID_FILE_TYPE,
    NOT_IN_PAYMENT_FLOW,
    UPLOAD_FAILED,
)
from data.keyboards import start_inline_keyboard
from utils.session import AWAITING_SCREENSHOT
from handlers.admin_handler import forward_to_admin

logger = logging.getLogger(__name__)
ALLOWED_MIME = {"image/jpeg", "image/png"}


async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    sm = context.bot_data["session_manager"]
    session = await sm.get(user.id)

    # ── Guard: must be in payment flow ─────────────────────
    if session["state"] != AWAITING_SCREENSHOT:
        await update.message.reply_text(
            NOT_IN_PAYMENT_FLOW,
            reply_markup=start_inline_keyboard()
        )
        return

    order_type = session["order_type"] # 'single' or 'bundle'
    video_id = session.get("video_id")
    amount: int = session["amount"]

    # ── Determine file source (photo vs document) ───────────
    mime_type = "image/jpeg"
    file_id = None
    file_size = 0

    if update.message.photo:
        photo: PhotoSize = update.message.photo[-1]
        file_id = photo.file_id
        file_size = photo.file_size or 0
    elif update.message.document:
        doc: Document = update.message.document
        mime_type = doc.mime_type or ""
        file_size = doc.file_size or 0
        if mime_type not in ALLOWED_MIME:
            await update.message.reply_text(INVALID_FILE_TYPE)
            return
        file_id = doc.file_id

    if not file_id:
        await update.message.reply_text(INVALID_FILE_TYPE)
        return

    # ── Download and Optimization ────────────────────────
    try:
        tg_file = await context.bot.get_file(file_id)
        buf = io.BytesIO()
        await tg_file.download_to_memory(buf)
        file_bytes = buf.getvalue()

        # Try to compress the image if it's large using PIL
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(file_bytes))
            
            # Convert to RGB to safely save as JPEG
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            # Resize if too large
            _MAX_DIMENSION = 1920
            img.thumbnail((_MAX_DIMENSION, _MAX_DIMENSION), Image.Resampling.LANCZOS)
            
            out_buf = io.BytesIO()
            img.save(out_buf, format="JPEG", quality=75, optimize=True)
            file_bytes = out_buf.getvalue()
            mime_type = "image/jpeg"
        except ImportError:
            logger.warning("Pillow not installed, skipping compression.")
        except Exception as e:
            logger.error(f"Image compression failed, using original bytes: {e}")

    except Exception as e:
        logger.error(f"Failed to download file: {e}")
        await update.message.reply_text(UPLOAD_FAILED)
        return

    try:
        screenshot_url = await upload_screenshot(file_bytes, mime_type, user.id)
    except Exception as e:
        logger.error(f"Supabase upload failed: {e}")
        await update.message.reply_text(UPLOAD_FAILED)
        return

    # ── Create Order ────────────────────────────────────────
    order_id = await create_order(
        user_id=user.id,
        order_type=order_type,
        amount=amount,
        screenshot_url=screenshot_url,
        video_id=video_id
    )

    await update.message.reply_text(PAYMENT_RECEIVED)
    await sm.reset(user.id)

    # ── Forward to Admin Group ──────────────────────────────
    video_title = None
    if order_type == "single" and video_id:
        vid = await get_video(video_id)
        video_title = vid["title"] if vid else "Unknown Video"

    admin_msg_id = await forward_to_admin(
        context=context,
        order_id=order_id,
        user_id=user.id,
        username=user.username,
        first_name=user.first_name or "User",
        order_type=order_type,
        amount=amount,
        file_id=file_id,
        video_title=video_title
    )

    if admin_msg_id:
        await set_admin_msg_id(order_id, admin_msg_id)

    await log_action(
        action_type="order_submitted",
        user_id=user.id,
        order_id=order_id,
        detail=f"type={order_type} amount={amount}"
    )
