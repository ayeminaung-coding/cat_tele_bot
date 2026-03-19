"""
handlers/admin_video_handler.py — Admin commands to add/delete single VIP videos.
"""
import logging
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import settings
from db.videos import get_all_videos, add_video, delete_video, get_video
from data.messages import (
    ADMIN_ONLY,
    ASK_VIDEO_TITLE,
    ASK_VIDEO_PRICE,
    INVALID_PRICE,
    ADD_VIDEO_CANCELLED,
    add_video_success,
    ASK_DELETE_VIDEO,
    NO_VIDEOS_TO_DELETE,
    delete_confirm_prompt,
    delete_video_success,
    DELETE_VIDEO_CANCELLED,
)
from data.keyboards import delete_video_list_keyboard, delete_confirm_keyboard

logger = logging.getLogger(__name__)

# ── ConversationHandler states ──────────────────────────────────
WAITING_TITLE = 0
WAITING_PRICE = 1


# ══════════════════════════════════════════════════════════════
#  ADD VIDEO FLOW  (/addvideo)
# ══════════════════════════════════════════════════════════════

async def addvideo_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: /addvideo"""
    if update.effective_user.id not in settings.ADMIN_IDS:
        await update.message.reply_text(ADMIN_ONLY)
        return ConversationHandler.END

    await update.message.reply_text(ASK_VIDEO_TITLE)
    return WAITING_TITLE


async def addvideo_get_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive the title, ask for price."""
    title = update.message.text.strip()
    context.user_data["new_video_title"] = title
    await update.message.reply_text(ASK_VIDEO_PRICE)
    return WAITING_PRICE


async def addvideo_get_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive the price, insert to DB, confirm."""
    text = update.message.text.strip().replace(",", "")
    if not text.isdigit():
        await update.message.reply_text(INVALID_PRICE)
        return WAITING_PRICE  # ask again

    price = int(text)
    title = context.user_data.pop("new_video_title", "")

    await add_video(title, price)
    await update.message.reply_text(add_video_success(title, price))
    return ConversationHandler.END


async def addvideo_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin cancelled mid-flow via /cancel."""
    context.user_data.pop("new_video_title", None)
    await update.message.reply_text(ADD_VIDEO_CANCELLED)
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════
#  DELETE VIDEO FLOW  (/deletevideo)
# ══════════════════════════════════════════════════════════════

async def deletevideo_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point: /deletevideo — shows inline list of all videos."""
    if update.effective_user.id not in settings.ADMIN_IDS:
        await update.message.reply_text(ADMIN_ONLY)
        return

    videos = await get_all_videos()
    if not videos:
        await update.message.reply_text(NO_VIDEOS_TO_DELETE)
        return

    await update.message.reply_text(
        ASK_DELETE_VIDEO,
        reply_markup=delete_video_list_keyboard(videos),
    )


async def handle_delete_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin tapped a video in the delete list — show confirm dialog."""
    query = update.callback_query
    await query.answer()

    if update.effective_user.id not in settings.ADMIN_IDS:
        return

    video_id = query.data.split(":", 1)[1]
    video = await get_video(video_id)
    if not video:
        await query.edit_message_text("❓ ဗီဒီယို ရှာမတွေ့ပါ။")
        return

    await query.edit_message_text(
        delete_confirm_prompt(video["title"]),
        reply_markup=delete_confirm_keyboard(video_id),
    )


async def handle_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin confirmed deletion."""
    query = update.callback_query
    await query.answer()

    if update.effective_user.id not in settings.ADMIN_IDS:
        return

    video_id = query.data.split(":", 1)[1]
    video = await get_video(video_id)
    title = video["title"] if video else video_id

    await delete_video(video_id)
    await query.edit_message_text(delete_video_success(title))


async def handle_delete_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin cancelled deletion."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(DELETE_VIDEO_CANCELLED)


# ══════════════════════════════════════════════════════════════
#  ConversationHandler factory (call this from bot_app.py)
# ══════════════════════════════════════════════════════════════

def build_addvideo_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("addvideo", addvideo_start)],
        states={
            WAITING_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, addvideo_get_title)],
            WAITING_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, addvideo_get_price)],
        },
        fallbacks=[CommandHandler("cancel", addvideo_cancel)],
        per_chat=True,
        per_user=True,
    )
