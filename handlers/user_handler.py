"""
handlers/user_handler.py — /start command and video selection.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from db.users import upsert_user, get_user
from db.videos import get_all_videos, get_video
from data.bundle_manager import get_bundle_info
from data.messages import (
    WELCOME, BANNED,
    SINGLE_VIDEO_HEADER, video_unavailable,
    single_payment_instructions, bundle_payment_instructions,
)
from data.keyboards import main_menu_keyboard, start_inline_keyboard, single_video_selection_keyboard, back_to_main_keyboard, buy_bundle_confirm_keyboard
from utils.session import IDLE, SELECTING_VIDEO, AWAITING_SCREENSHOT

logger = logging.getLogger(__name__)


from config import settings

async def handle_user_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fallback handler for generic text messages. Forwards them to the admin group."""
    user = update.effective_user
    text = update.message.text
    
    # Send a quick acknowledgment
    await update.message.reply_text("📨 သင်၏မက်ဆေ့ခ်ျကို Admin ထံသို့ ပေးပို့လိုက်ပါသည်။ Admin မှ အမြန်ဆုံး အကြောင်းပြန်ပေးပါမည်။")
    
    # Forward to admin group
    admin_msg = (
        f"📩 <b>#SupportTicket</b>\n"
        f"User: <a href='tg://user?id={user.id}'>{user.full_name}</a>\n"
        f"ID: <code>{user.id}</code>\n\n"
        f"{text}"
    )
    await context.bot.send_message(
        chat_id=settings.ADMIN_GROUP_ID,
        text=admin_msg,
        parse_mode="HTML"
    )

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    await upsert_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name or "User",
    )

    db_user = await get_user(user.id)
    if db_user and db_user.get("status") == "banned":
        await update.message.reply_text(BANNED)
        return

    sm = context.bot_data["session_manager"]
    await sm.reset(user.id)

    await update.message.reply_text(
        "👋 မင်္ဂလာပါ",
        reply_markup=main_menu_keyboard(),
    )
    await update.message.reply_text(
        WELCOME,
        reply_markup=start_inline_keyboard(),
    )


async def handle_buy_bundle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    sm = context.bot_data["session_manager"]
    amount = 5000
    bundle_text = get_bundle_info()
    await update.message.reply_text(
        bundle_text,
        reply_markup=buy_bundle_confirm_keyboard()
    )


async def handle_buy_single_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    sm = context.bot_data["session_manager"]
    await sm.set(user.id, state=SELECTING_VIDEO, order_type="single")
    videos = await get_all_videos()
    await update.message.reply_text(
        SINGLE_VIDEO_HEADER,
        reply_markup=single_video_selection_keyboard(videos)
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles all inline keyboard interactions related to ordering."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    sm = context.bot_data["session_manager"]
    data = query.data

    # Return to main menu
    if data == "back_to_main" or data == "retry":
        await sm.reset(user.id)
        try:
            await query.edit_message_reply_markup(reply_markup=None)  # strip inline buttons
        except Exception:
            pass  # message may already be gone — that's fine
        await context.bot.send_message(
            chat_id=user.id,
            text=WELCOME,
            reply_markup=start_inline_keyboard(),
        )
        return

    # ── BUY BUNDLE ──────────────────────────────────────────
    if data == "main_buy_bundle" or data == "buy:bundle":
        if data == "main_buy_bundle":
            bundle_text = get_bundle_info()
            await query.edit_message_text(
                bundle_text,
                reply_markup=buy_bundle_confirm_keyboard()
            )
            return
            
        amount = 5000
        await sm.set(user.id, state=AWAITING_SCREENSHOT, order_type="bundle", amount=amount)
        
        await query.edit_message_text(
            text=bundle_payment_instructions(amount),
            reply_markup=back_to_main_keyboard()
        )
        return

    # ── BUY SINGLE ──────────────────────────────────────────
    if data == "main_buy_single" or data == "buy:single":
        await sm.set(user.id, state=SELECTING_VIDEO, order_type="single")
        videos = await get_all_videos()
        await query.edit_message_text(
            SINGLE_VIDEO_HEADER,
            reply_markup=single_video_selection_keyboard(videos, page=0)
        )
        return

    # ── PAGINATION ──────────────────────────────────────────
    if data.startswith("page:"):
        session = await sm.get(user.id)
        if session["state"] != SELECTING_VIDEO:
            return
            
        page = int(data.split(":")[1])
        videos = await get_all_videos()
        await query.edit_message_text(
            SINGLE_VIDEO_HEADER,
            reply_markup=single_video_selection_keyboard(videos, page=page)
        )
        return

    # ── SELECT SPECIFIC VIDEO ───────────────────────────────
    if data.startswith("video:"):
        session = await sm.get(user.id)
        if session["state"] != SELECTING_VIDEO:
            return
            
        video_id = data.split(":", 1)[1]
        video = await get_video(video_id)
        
        if not video:
            await query.edit_message_text("❓ မသိသော ဗီဒီယို။ /start ပြန်နှိပ်ပါ။")
            return

        if video["status"] == "unavailable":
            await query.answer(video_unavailable(video['title']), show_alert=True)
            return

        amount = video["price"]
        await sm.set(user.id, state=AWAITING_SCREENSHOT, video_id=video_id, amount=amount)
        await query.edit_message_text(single_payment_instructions(video["title"], amount))
        return

