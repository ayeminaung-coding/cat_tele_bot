"""
handlers/admin_video_handler.py — Admin commands to add/delete/single videos.
"""

import logging

from telegram import InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import settings
from data.bundle_manager import get_bundle_info, set_bundle_info
from data.keyboards import (
    delete_confirm_keyboard,
    delete_video_list_keyboard,
    set_video_channel_id_keyboard,
    set_video_link_keyboard,
    view_video_selection_keyboard,
)
from data.messages import (
    ADD_VIDEO_CANCELLED,
    ADMIN_ONLY,
    ASK_DELETE_VIDEO,
    ASK_SETCHANNELID_ID,
    ASK_SETCHANNELID_VIDEO,
    ASK_SETLINK_URL,
    ASK_SETLINK_VIDEO,
    ASK_VIDEO_PRICE,
    ASK_VIDEO_TITLE,
    ASK_VIEW_VIDEO,
    DELETE_VIDEO_CANCELLED,
    INVALID_PRICE,
    NO_VIDEO_FOUND,
    NO_VIDEOS_TO_DELETE,
    SETCHANNELID_CANCELLED,
    SETLINK_CANCELLED,
    VIEW_VIDEO_CANCELLED,
    add_video_success,
    delete_confirm_prompt,
    delete_video_success,
    setchannelid_success,
    setlink_success,
    video_info_display,
)
from db.logs import log_action
from db.videos import (
    add_video,
    delete_video,
    get_all_videos,
    get_video,
    set_video_channel_id,
    set_video_link,
)

logger = logging.getLogger(__name__)

# ── ConversationHandler states ──────────────────────────────────
WAITING_TITLE = 0
WAITING_PRICE = 1
WAITING_LINK = 2
WAITING_BUNDLE_TEXT = 3
WAITING_CHANNEL_ID = 4
VIEW_VIDEO_SELECT = 5

# ────────────────────────────────────────────────────────────────


# ═══════════════════════════════════════════════════════════════
#  ADD VIDEO FLOW  (/addvideo)
# ═══════════════════════════════════════════════════════════════


async def addvideo_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: /addvideo"""
    if update.effective_user.id not in settings.ADMIN_IDS:
        await update.message.reply_text(ADMIN_ONLY)
        return ConversationHandler.END

    await update.message.reply_text(ASK_VIDEO_TITLE)
    return WAITING_TITLE


async def addvideo_get_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin sent video title."""
    title = update.message.text.strip()
    if not title:
        await update.message.reply_text(
            "❌ Title ထည့်သွင်းရန် မသေချာပါ။\nပလီဇီ။ ထပ်မံ ကြိုးစားပါ။"
        )
        return WAITING_TITLE

    context.user_data["video_title"] = title
    await update.message.reply_text(ASK_VIDEO_PRICE)
    return WAITING_PRICE


async def addvideo_get_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin sent video price."""
    price_str = update.message.text.strip()
    try:
        price = int(price_str)
        if price <= 0:
            raise ValueError("Price must be positive")
    except ValueError:
        await update.message.reply_text(INVALID_PRICE)
        return WAITING_PRICE

    title = context.user_data.get("video_title", "Unknown")
    context.user_data.clear()

    admin_id = update.effective_user.id
    try:
        created_id = await add_video(title, price)
        await update.message.reply_text(
            f"{add_video_success(title, price)}\n🆔 Video ID: <code>{created_id['id'] or 'unknown'}</code>",
            parse_mode="HTML",
        )
        await log_action(
            "add_video",
            admin_id=admin_id,
            detail=f"id={created_id['id']} title={title} price={price}",
        )
    except Exception as e:
        logger.error(f"Failed to add video: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ ဒေတာဘေ့စ်သို့ သိမ်းဆည်းရာတွင် အမှားအယွင်းဖြစ်နေပါသည်။\nအမှား: {e}"
        )
        await log_action(
            "add_video_error",
            admin_id=admin_id,
            detail=f"title={title} price={price} err={e}",
        )

    return ConversationHandler.END


async def addvideo_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin sent /cancel during the flow."""
    context.user_data.clear()
    await update.message.reply_text(ADD_VIDEO_CANCELLED)
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════
#  DELETE VIDEO FLOW  (/deletevideo)
# ═══════════════════════════════════════════════════════════════


async def deletevideo_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point: /deletevideo — shows inline list of all videos."""
    if update.effective_user.id not in settings.ADMIN_IDS:
        await update.message.reply_text(ADMIN_ONLY)
        return

    try:
        videos = await get_all_videos()
        if not videos:
            await update.message.reply_text(NO_VIDEOS_TO_DELETE)
            return

        keyboard = delete_video_list_keyboard(videos)
        await update.message.reply_text(ASK_DELETE_VIDEO, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in deletevideo_start: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ ဇာတ်ကားစာရင်းကို ရယူရာတွင် အမှားဖြစ်နေပါသည်။\nကျေးဇူးပြု၍ ထပ်မံ ကြိုးစားပါ။"
        )


async def handle_delete_select(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Admin tapped a video in the delete list — show confirm dialog."""
    query = update.callback_query
    await query.answer()

    video_id = query.data.split(":", 1)[1]
    context.user_data["delete_video_id"] = video_id

    video = await get_video(video_id)
    if video:
        prompt = delete_confirm_prompt(video["title"])
        keyboard = delete_confirm_keyboard(video_id)
        await query.edit_message_text(prompt, reply_markup=keyboard)
    else:
        await query.edit_message_text("❓ ဇာတ်ကား မတွေ့ရပါ။")


async def handle_delete_confirm(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Admin confirmed deletion."""
    query = update.callback_query
    await query.answer()

    video_id = query.data.split(":", 1)[1]
    video = await get_video(video_id)

    if video:
        title = video["title"]
        await delete_video(video_id)
        await query.edit_message_text(delete_video_success(title))

        admin_id = update.effective_user.id
        await log_action(
            "delete_video",
            admin_id=admin_id,
            detail=f"id={video_id} title={title}",
        )
    else:
        await query.edit_message_text("❌ ဇာတ်ကား မတွေ့ရပါ။")


async def handle_delete_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Admin cancelled deletion."""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(DELETE_VIDEO_CANCELLED)


# ═══════════════════════════════════════════════════════════════
#  SET VIDEO LINK FLOW  (/setvideolink)
# ═══════════════════════════════════════════════════════════════


async def setvideolink_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry: /setvideolink — shows inline list of videos."""
    if update.effective_user.id not in settings.ADMIN_IDS:
        await update.message.reply_text(ADMIN_ONLY)
        return ConversationHandler.END

    try:
        videos = await get_all_videos()
        if not videos:
            await update.message.reply_text(NO_VIDEOS_TO_DELETE)
            return ConversationHandler.END

        keyboard = set_video_link_keyboard(videos)
        await update.message.reply_text(ASK_SETLINK_VIDEO, reply_markup=keyboard)
        return WAITING_LINK
    except Exception as e:
        logger.error(f"Error in setvideolink_start: {e}", exc_info=True)
        await update.message.reply_text("❌ ဇာတ်ကားစာရင်းကို ရယူရာတွင် အမှားဖြစ်နေပါသည်။")
        return ConversationHandler.END


async def setvideolink_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin tapped a video — store the ID and ask for the link."""
    query = update.callback_query
    await query.answer()

    video_id = query.data.split(":", 1)[1]
    video = await get_video(video_id)
    if not video:
        await query.edit_message_text("❓ ဇာတ်ကား မတွေ့ရပါ။")
        return ConversationHandler.END

    context.user_data["setlink_video_id"] = video_id
    context.user_data["setlink_video_title"] = video["title"]
    await query.edit_message_text(f"{ASK_SETLINK_URL}\n\n({video['title']})")
    return WAITING_LINK


async def setvideolink_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin sent the Link URL — save it to DB and confirm."""
    link = update.message.text.strip()

    if not link:
        await update.message.reply_text("❌ Link ကို ရိုက်ထည့်ပါ။")
        return WAITING_LINK

    if not _is_valid_telegram_link(link):
        await update.message.reply_text(
            "⚠️ Telegram link ဖြစ်ရပါမည်။\nဥပမာ: https://t.me/+xxxx သို့မဟုတ် https://t.me/xxxx"
        )
        return WAITING_LINK

    video_id = context.user_data.get("setlink_video_id")
    video_title = context.user_data.get("setlink_video_title", "Unknown")
    context.user_data.clear()

    try:
        await set_video_link(video_id, link)
        await update.message.reply_text(setlink_success(video_title))

        admin_id = update.effective_user.id
        await log_action(
            "set_video_link",
            admin_id=admin_id,
            detail=f"id={video_id} title={video_title} link={link}",
        )
    except Exception as e:
        logger.error(f"Failed to set video link: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ ဒေတာဘေ့စ်သို့ သိမ်းဆည်းရာတွင် အမှားဖြစ်နေပါသည်။\nအမှား: {e}"
        )

    return ConversationHandler.END


def _is_valid_telegram_link(link: str) -> bool:
    """Validate Telegram invite/channel link format."""
    import re
    from urllib.parse import urlparse

    try:
        parsed = urlparse((link or "").strip())
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname or ""
        # Accept t.me links or invite links with + or /s/
        if hostname != "t.me":
            return False
        path = parsed.path or ""
        return bool(
            re.match(r"^/[\w\d_]+$", path)
            or re.match(r"^/\+[\w\d_]+$", path)
            or re.match(r"^/s/[\w\d_]+$", path)
        )
    except Exception:
        return False


async def setvideolink_cancel_cb(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Admin tapped cancel in the video picker."""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(SETLINK_CANCELLED)
    return ConversationHandler.END


async def setvideolink_cancel_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Admin sent /cancel during the flow."""
    context.user_data.pop("setlink_video_id", None)
    context.user_data.pop("setlink_video_title", None)
    await update.message.reply_text(SETLINK_CANCELLED)
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════
#  SET CHANNEL ID FLOW  (/setchannelid)
# ═══════════════════════════════════════════════════════════════


async def setchannelid_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry: /setchannelid — shows inline list of videos."""
    if update.effective_user.id not in settings.ADMIN_IDS:
        await update.message.reply_text(ADMIN_ONLY)
        return ConversationHandler.END

    try:
        videos = await get_all_videos()
        if not videos:
            await update.message.reply_text(NO_VIDEOS_TO_DELETE)
            return ConversationHandler.END

        keyboard = set_video_channel_id_keyboard(videos)
        await update.message.reply_text(ASK_SETCHANNELID_VIDEO, reply_markup=keyboard)
        return WAITING_CHANNEL_ID
    except Exception as e:
        logger.error(f"Error in setchannelid_start: {e}", exc_info=True)
        await update.message.reply_text("❌ ဇာတ်ကားစာရင်းကို ရယူရာတွင် အမှားဖြစ်နေပါသည်။")
        return ConversationHandler.END


async def setchannelid_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin tapped a video — store the ID and ask for the Channel ID."""
    query = update.callback_query
    await query.answer()

    video_id = query.data.split(":", 1)[1]
    video = await get_video(video_id)
    if not video:
        await query.edit_message_text("❓ ဇာတ်ကား မတွေ့ရပါ။")
        return ConversationHandler.END

    context.user_data["setchannelid_video_id"] = video_id
    context.user_data["setchannelid_video_title"] = video["title"]
    await query.edit_message_text(f"{ASK_SETCHANNELID_ID}\n\n({video['title']})")
    return WAITING_CHANNEL_ID


async def setchannelid_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin sent the Channel ID — save it to DB and confirm."""
    channel_str = update.message.text.strip()

    if not _is_valid_channel_id(channel_str):
        await update.message.reply_text(
            "❌ Channel ID အမှားဖြစ်နေပါသည်။\n-100 ဖြင့် စတင်သော ဂဏန်းများသာ ဖြစ်ရပါမည်။\nဥပမာ: -1001234567890"
        )
        return WAITING_CHANNEL_ID

    video_id = context.user_data.get("setchannelid_video_id")
    video_title = context.user_data.get("setchannelid_video_title", "Unknown")
    channel_id = int(channel_str)
    context.user_data.clear()

    try:
        await set_video_channel_id(video_id, channel_id)
        await update.message.reply_text(setchannelid_success(video_title))

        admin_id = update.effective_user.id
        await log_action(
            "set_channel_id",
            admin_id=admin_id,
            detail=f"id={video_id} title={video_title} channel_id={channel_id}",
        )
    except Exception as e:
        logger.error(f"Failed to set channel ID: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ ဒေတာဘေ့စ်သို့ သိမ်းဆည်းရာတွင် အမှားဖြစ်နေပါသည်။\nအမှား: {e}"
        )

    return ConversationHandler.END


def _is_valid_channel_id(channel_str: str) -> bool:
    """Validate Telegram Channel ID format."""
    try:
        channel_id = int(channel_str)
        # Telegram channel IDs are typically -100xxxxxxxxxxxxx
        return channel_id < 0 and len(str(abs(channel_id))) >= 10
    except (ValueError, TypeError):
        return False


async def setchannelid_cancel_cb(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Admin tapped cancel in the video picker."""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(SETCHANNELID_CANCELLED)
    return ConversationHandler.END


async def setchannelid_cancel_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Admin sent /cancel during the flow."""
    context.user_data.pop("setchannelid_video_id", None)
    context.user_data.pop("setchannelid_video_title", None)
    await update.message.reply_text(SETCHANNELID_CANCELLED)
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════
#  SET BUNDLE TEXT FLOW  (/setbundletext)
# ═══════════════════════════════════════════════════════════════


async def setbundletext_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Entry: /setbundletext — asks admin to enter the new bundle info text or sets it directly."""
    if update.effective_user.id not in settings.ADMIN_IDS:
        await update.message.reply_text(ADMIN_ONLY)
        return ConversationHandler.END

    existing = get_bundle_info()  # Synchronous function
    current_text = (
        existing if isinstance(existing, str) else existing.get("info_text", "")
    )

    msg = (
        "📝 Bundle ဇာတ်လမ်းစာရင်း စာသားအသစ်ကို ရိုက်ထည့်ပါ။\n"
        f"ပြန်လည်ကြည့်ရှုရန်:\n{current_text}\n\n"
        "(ပယ်ဖျက်လိုပါက /cancel ကိုနှိပ်ပါ)"
    )
    await update.message.reply_text(msg)
    return WAITING_BUNDLE_TEXT


async def setbundletext_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin sent new bundle text."""
    new_text = update.message.text.strip()

    if not new_text:
        await update.message.reply_text("❌ စာသားအသစ်ကို ရိုက်ထည့်ပါ။")
        return WAITING_BUNDLE_TEXT

    set_bundle_info(new_text)  # Synchronous function
    await update.message.reply_text("✅ Bundle ဇာတ်လမ်းစာရင်း အသစ်ကို သိမ်းဆည်းပြီးပါပြီ။")
    return ConversationHandler.END


async def setbundletext_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Admin sent /cancel during bundle text update."""
    await update.message.reply_text("❌ Bundle ဇာတ်လမ်းစာရင်း ပြင်ဆင်ခြင်းကို ပယ်ဖျက်လိုက်ပါသည်။")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════
#  VIEW VIDEO INFO FLOW  (/viewvideo)
# ═══════════════════════════════════════════════════════════════


async def viewvideo_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: /viewvideo — shows inline list of all videos."""
    if update.effective_user.id not in settings.ADMIN_IDS:
        await update.message.reply_text(ADMIN_ONLY)
        return ConversationHandler.END

    try:
        videos = await get_all_videos()
        if not videos:
            await update.message.reply_text(NO_VIDEO_FOUND)
            return ConversationHandler.END

        keyboard = view_video_selection_keyboard(videos)
        await update.message.reply_text(ASK_VIEW_VIDEO, reply_markup=keyboard)
        return VIEW_VIDEO_SELECT
    except Exception as e:
        logger.error(f"Error in viewvideo_start: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ ဇာတ်ကားစာရင်းကို ရယူရာတွင် အမှားဖြစ်နေပါသည်။\nကျေးဇူးပြု၍ ထပ်မံ ကြိုးစားပါ။"
        )
        return ConversationHandler.END


async def handle_view_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin tapped a video in the view list — show video info."""
    query = update.callback_query
    await query.answer()

    video_id = query.data.split(":", 1)[1]
    video = await get_video(video_id)

    if not video:
        await query.edit_message_text(
            "❓ ဇာတ်ကားအချက်အလက် မတွေ့ရပါ။\nကျေးဇူးပြု၍ ထပ်မံ ကြိုးစားပါ။"
        )
        return ConversationHandler.END

    msg = video_info_display(video)
    # Keep only the cancel button
    keyboard = InlineKeyboardMarkup(
        [[query.message.reply_markup.inline_keyboard[-1][0]]]
    )

    await query.edit_message_text(
        msg,
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    return VIEW_VIDEO_SELECT


async def handle_view_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin cancelled the view video flow."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(VIEW_VIDEO_CANCELLED)
    return ConversationHandler.END


async def viewvideo_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin sent /cancel during the flow."""
    await update.message.reply_text(VIEW_VIDEO_CANCELLED)
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════
#  ConversationHandler factories (call these from bot_app.py)
# ═══════════════════════════════════════════════════════════════


def build_addvideo_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("addvideo", addvideo_start)],
        states={
            WAITING_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, addvideo_get_title)
            ],
            WAITING_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, addvideo_get_price)
            ],
        },
        fallbacks=[CommandHandler("cancel", addvideo_cancel)],
        per_chat=True,
        per_user=True,
        allow_reentry=True,
    )


def build_setvideolink_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("setvideolink", setvideolink_start)],
        states={
            WAITING_LINK: [
                # Step 1: admin picks a video via inline button
                CallbackQueryHandler(setvideolink_pick, pattern=r"^setlink_select:"),
                CallbackQueryHandler(
                    setvideolink_cancel_cb, pattern=r"^setlink_cancel$"
                ),
                # Step 2: admin types the URL
                MessageHandler(filters.TEXT & ~filters.COMMAND, setvideolink_save),
            ],
        },
        fallbacks=[CommandHandler("cancel", setvideolink_cancel_cmd)],
        per_chat=True,
        per_user=True,
        allow_reentry=True,
    )


def build_setchannelid_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("setchannelid", setchannelid_start)],
        states={
            WAITING_CHANNEL_ID: [
                CallbackQueryHandler(
                    setchannelid_pick, pattern=r"^setchannelid_select:"
                ),
                CallbackQueryHandler(
                    setchannelid_cancel_cb, pattern=r"^setchannelid_cancel$"
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, setchannelid_save),
            ],
        },
        fallbacks=[CommandHandler("cancel", setchannelid_cancel_cmd)],
        per_chat=True,
        per_user=True,
        allow_reentry=True,
    )


def build_setbundletext_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("setbundletext", setbundletext_start)],
        states={
            WAITING_BUNDLE_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, setbundletext_save)
            ],
        },
        fallbacks=[CommandHandler("cancel", setbundletext_cancel)],
        per_chat=True,
        per_user=True,
        allow_reentry=True,
    )


def build_viewvideo_conv() -> ConversationHandler:
    """Build the ConversationHandler for /viewvideo."""
    return ConversationHandler(
        entry_points=[CommandHandler("viewvideo", viewvideo_start)],
        states={
            VIEW_VIDEO_SELECT: [
                CallbackQueryHandler(handle_view_select, pattern=r"^view_select:"),
                CallbackQueryHandler(handle_view_cancel, pattern=r"^view_cancel$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", viewvideo_cancel)],
        per_chat=True,
        per_user=True,
        allow_reentry=True,
    )
