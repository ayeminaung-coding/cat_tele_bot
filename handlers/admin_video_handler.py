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
from db.videos import get_all_videos, add_video, delete_video, get_video, set_video_link, set_video_channel_id
from db.logs import log_action
from data.bundle_manager import set_bundle_info, get_bundle_info
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
    ASK_SETLINK_VIDEO,
    ASK_SETLINK_URL,
    setlink_success,
    SETLINK_CANCELLED,
    ASK_SETCHANNELID_VIDEO,
    ASK_SETCHANNELID_ID,
    setchannelid_success,
    SETCHANNELID_CANCELLED,
)
from data.keyboards import (
    delete_video_list_keyboard,
    delete_confirm_keyboard,
    set_video_link_keyboard,
    set_video_channel_id_keyboard,
)

logger = logging.getLogger(__name__)

# ── ConversationHandler states ──────────────────────────────────
WAITING_TITLE = 0
WAITING_PRICE = 1
WAITING_LINK  = 2  # used by setvideolink conv
WAITING_BUNDLE_TEXT = 3 # used by setbundletext conv
WAITING_CHANNEL_ID = 4 # used by setchannelid conv


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
    admin_id = update.effective_user.id if update.effective_user else None

    try:
        created = await add_video(title, price)
        created_id = created.get("id") if isinstance(created, dict) else None
        if created_id:
            saved = await get_video(created_id)
            if not saved:
                raise RuntimeError("Insert did not persist in database")
        await update.message.reply_text(
            f"{add_video_success(title, price)}\n🆔 Video ID: <code>{created_id or 'unknown'}</code>",
            parse_mode="HTML",
        )
        await log_action("add_video", admin_id=admin_id, detail=f"id={created_id} title={title} price={price}")
    except Exception as e:
        logger.error(f"Failed to add video: {e}", exc_info=True)
        await update.message.reply_text(f"❌ ဒေတာဘေ့စ်သို့ သိမ်းဆည်းရာတွင် အမှားအယွင်းဖြစ်နေပါသည်။\nအမှား: {e}")
        await log_action("add_video_error", admin_id=admin_id, detail=f"title={title} price={price} err={e}")
        
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


# ════════════════════════════════════════════════════════════
#  SET VIDEO LINK FLOW  (/setvideolink)
# ════════════════════════════════════════════════════════════

async def setvideolink_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry: /setvideolink — shows inline list of videos."""
    if update.effective_user.id not in settings.ADMIN_IDS:
        await update.message.reply_text(ADMIN_ONLY)
        return ConversationHandler.END

    videos = await get_all_videos()
    if not videos:
        await update.message.reply_text(NO_VIDEOS_TO_DELETE)
        return ConversationHandler.END

    await update.message.reply_text(
        ASK_SETLINK_VIDEO,
        reply_markup=set_video_link_keyboard(videos),
    )
    return WAITING_LINK


async def setvideolink_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin tapped a video — store the ID and ask for the URL."""
    query = update.callback_query
    await query.answer()

    video_id = query.data.split(":", 1)[1]
    video = await get_video(video_id)
    if not video:
        await query.edit_message_text("\u2753 \u1017\u102e\u1012\u102e\u101a\u102d\u102f \u101b\u103e\u102c\u1019\u1010\u103d\u1031\u1037\u1015\u102b\u104b")
        return ConversationHandler.END

    context.user_data["setlink_video_id"] = video_id
    context.user_data["setlink_video_title"] = video["title"]
    await query.edit_message_text(f"{ASK_SETLINK_URL}\n\n({video['title']})")
    return WAITING_LINK


async def setvideolink_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin sent the URL — save it to DB and confirm."""
    link = update.message.text.strip()
    video_id = context.user_data.pop("setlink_video_id", None)
    title = context.user_data.pop("setlink_video_title", "")

    if not video_id:
        await update.message.reply_text(SETLINK_CANCELLED)
        return ConversationHandler.END

    # Validate Telegram invite link format
    if not _is_valid_telegram_link(link):
        await update.message.reply_text(
            "❌ မှားယွင်းသော လင့်ခ်ပုံစံ။\n\n"
            "ဥပမာများ:\n"
            "• https://t.me/+xxxxx\n"
            "• https://telegram.me/joinchat/xxxxx\n"
            "• https://t.me/xxxxx\n\n"
            "ထပ်မံကြိုးစားပါ။"
        )
        # Restore state for retry
        context.user_data["setlink_video_id"] = video_id
        context.user_data["setlink_video_title"] = title
        return WAITING_LINK

    await set_video_link(video_id, link)
    await update.message.reply_text(setlink_success(title))
    return ConversationHandler.END


def _is_valid_telegram_link(link: str) -> bool:
    """Validate Telegram invite/channel link format."""
    from urllib.parse import urlparse
    import re

    try:
        parsed = urlparse((link or "").strip())
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host not in ("t.me", "telegram.me"):
        return False

    path = (parsed.path or "").strip("/")
    if not path:
        return False

    parts = path.split("/")
    slug_re = re.compile(r"[A-Za-z0-9_-]{5,}")

    # t.me/username or t.me/+invitecode
    if len(parts) == 1:
        slug = parts[0]
        if slug.startswith("+"):
            slug = slug[1:]
        return bool(slug_re.fullmatch(slug))

    # t.me/joinchat/invitecode
    if len(parts) == 2 and parts[0].lower() == "joinchat":
        return bool(slug_re.fullmatch(parts[1]))

    return False


async def setvideolink_cancel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin tapped cancel in the video picker."""
    query = update.callback_query
    await query.answer()
    context.user_data.pop("setlink_video_id", None)
    context.user_data.pop("setlink_video_title", None)
    await query.edit_message_text(SETLINK_CANCELLED)
    return ConversationHandler.END


async def setvideolink_cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin sent /cancel during the flow."""
    context.user_data.pop("setlink_video_id", None)
    context.user_data.pop("setlink_video_title", None)
    await update.message.reply_text(SETLINK_CANCELLED)
    return ConversationHandler.END


# ════════════════════════════════════════════════════════════
#  SET CHANNEL ID FLOW  (/setchannelid)
# ════════════════════════════════════════════════════════════

async def setchannelid_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry: /setchannelid — shows inline list of videos."""
    if update.effective_user.id not in settings.ADMIN_IDS:
        await update.message.reply_text(ADMIN_ONLY)
        return ConversationHandler.END

    videos = await get_all_videos()
    if not videos:
        await update.message.reply_text(NO_VIDEOS_TO_DELETE)
        return ConversationHandler.END

    await update.message.reply_text(
        ASK_SETCHANNELID_VIDEO,
        reply_markup=set_video_channel_id_keyboard(videos),
    )
    return WAITING_CHANNEL_ID

async def setchannelid_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin tapped a video — store the ID and ask for the Channel ID."""
    query = update.callback_query
    await query.answer()

    video_id = query.data.split(":", 1)[1]
    video = await get_video(video_id)
    if not video:
        # Fallback error mapping
        await query.edit_message_text("❓ ဗီဒီယို ရှာမတွေ့ပါ။")
        return ConversationHandler.END

    context.user_data["setchannelid_video_id"] = video_id
    context.user_data["setchannelid_video_title"] = video["title"]
    await query.edit_message_text(f"{ASK_SETCHANNELID_ID}\n\n({video['title']})")
    return WAITING_CHANNEL_ID

async def setchannelid_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin sent the Channel ID — save it to DB and confirm."""
    channel_id_str = update.message.text.strip()
    video_id = context.user_data.pop("setchannelid_video_id", None)
    title = context.user_data.pop("setchannelid_video_title", "")

    if not video_id:
        await update.message.reply_text(SETCHANNELID_CANCELLED)
        return ConversationHandler.END

    # Validate Channel ID format (must be integer starting with -100)
    try:
        channel_id = int(channel_id_str)
        if not _is_valid_channel_id(channel_id):
            await update.message.reply_text(
                "❌ မှားယွင်းသော Channel ID ပုံစံ။\n\n"
                "Telegram Channel ID သည် -100 ဖြင့် စရပါမည်။\n"
                "ဥပမာ: -1001234567890\n\n"
                "ထပ်မံကြိုးစားပါ။"
            )
            # Restore state for retry
            context.user_data["setchannelid_video_id"] = video_id
            context.user_data["setchannelid_video_title"] = title
            return WAITING_CHANNEL_ID

        await set_video_channel_id(video_id, channel_id)
        await update.message.reply_text(setchannelid_success(title))
    except ValueError:
        await update.message.reply_text(
            "❌ မှားယွင်းနေပါသည်။ သေချာသော Telegram Channel ID ဂဏန်း (ဥပမာ: -1001234567) ကိုသာ ပေးပို့ပါ။"
        )
        # Give them another chance
        context.user_data["setchannelid_video_id"] = video_id
        context.user_data["setchannelid_video_title"] = title
        return WAITING_CHANNEL_ID
    return ConversationHandler.END


def _is_valid_channel_id(channel_id: int) -> bool:
    """Validate Telegram Channel ID format (must start with -100)."""
    # Telegram channel IDs start with -100 and continue with digits.
    channel_str = str(channel_id)
    return (
        channel_str.startswith("-100")
        and len(channel_str) > 4
        and channel_str[4:].isdigit()
    )

async def setchannelid_cancel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin tapped cancel in the video picker."""
    query = update.callback_query
    await query.answer()
    context.user_data.pop("setchannelid_video_id", None)
    context.user_data.pop("setchannelid_video_title", None)
    await query.edit_message_text(SETCHANNELID_CANCELLED)
    return ConversationHandler.END

async def setchannelid_cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin sent /cancel during the flow."""
    context.user_data.pop("setchannelid_video_id", None)
    context.user_data.pop("setchannelid_video_title", None)
    await update.message.reply_text(SETCHANNELID_CANCELLED)
    return ConversationHandler.END

# ════════════════════════════════════════════════════════════
#  SET BUNDLE TEXT FLOW  (/setbundletext)
# ════════════════════════════════════════════════════════════

async def setbundletext_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry: /setbundletext — asks admin to enter the new bundle info text or sets it directly."""
    if update.effective_user.id not in settings.ADMIN_IDS:
        await update.message.reply_text(ADMIN_ONLY)
        return ConversationHandler.END

    # If the user typed something after the command, save it directly
    command_text = update.message.text
    if " " in command_text:
        new_text = command_text.split(" ", 1)[1].strip()
        if new_text:
            set_bundle_info(new_text)
            await update.message.reply_text("✅ Bundle ဇာတ်လမ်းစာရင်း အသစ်ကို သိမ်းဆည်းပြီးပါပြီ။")
            return ConversationHandler.END

    current_text = get_bundle_info()
    msg = (
        f"📝 ယခုလက်ရှိ Bundle ဇာတ်လမ်းစာရင်း:\n\n{current_text}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"ကျေးဇူးပြု၍ Bundle အသစ်အတွက် စာသား(Text)ကို ရိုက်ထည့်ပါ။\n"
        f"(လုပ်ငန်းစဥ်ကို ရပ်တန့်ရန် /cancel ကိုနှိပ်ပါ။)"
    )
    await update.message.reply_text(msg)
    return WAITING_BUNDLE_TEXT

async def setbundletext_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin sent new bundle text."""
    new_text = update.message.text.strip()
    set_bundle_info(new_text)
    await update.message.reply_text("✅ Bundle ဇာတ်လမ်းစာရင်း အသစ်ကို သိမ်းဆည်းပြီးပါပြီ။")
    return ConversationHandler.END

async def setbundletext_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin sent /cancel during bundle text update."""
    await update.message.reply_text("❌ Bundle ဇာတ်လမ်းစာရင်း ပြင်ဆင်ခြင်းကို ပယ်ဖျက်လိုက်ပါသည်။")
    return ConversationHandler.END

# ════════════════════════════════════════════════════════════
#  ConversationHandler factories (call these from bot_app.py)
# ════════════════════════════════════════════════════════════

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
        allow_reentry=True,
    )


def build_setvideolink_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("setvideolink", setvideolink_start)],
        states={
            WAITING_LINK: [
                # Step 1: admin picks a video via inline button
                CallbackQueryHandler(setvideolink_pick, pattern=r"^setlink_select:"),
                CallbackQueryHandler(setvideolink_cancel_cb, pattern=r"^setlink_cancel$"),
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
                CallbackQueryHandler(setchannelid_pick, pattern=r"^setchannelid_select:"),
                CallbackQueryHandler(setchannelid_cancel_cb, pattern=r"^setchannelid_cancel$"),
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
            WAITING_BUNDLE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, setbundletext_save)],
        },
        fallbacks=[CommandHandler("cancel", setbundletext_cancel)],
        per_chat=True,
        per_user=True,
        allow_reentry=True,
    )
