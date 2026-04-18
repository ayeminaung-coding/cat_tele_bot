"""
handlers/user_handler.py — /start command and video selection.
"""
import html
import logging
from pathlib import Path
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
from utils.rate_limiter import check_user_rate_limit

logger = logging.getLogger(__name__)


from config import settings


LEGACY_CALLBACK_ALIASES = {
    "buy_single": "main_buy_single",
    "single": "main_buy_single",
    "buy_bundle": "main_buy_bundle",
    "bundle": "main_buy_bundle",
    "main_menu": "back_to_main",
    "back": "back_to_main",
}


def normalize_callback_data(data: str | None) -> str:
    """Normalize old callback payloads to current callback format."""
    if not data:
        return ""

    normalized = data.strip()
    if not normalized:
        return ""

    if normalized in LEGACY_CALLBACK_ALIASES:
        return LEGACY_CALLBACK_ALIASES[normalized]

    if normalized.startswith("video_"):
        return f"video:{normalized.split('_', 1)[1]}"

    if normalized.startswith("page_"):
        return f"page:{normalized.split('_', 1)[1]}"

    if normalized.startswith("buy_"):
        return f"buy:{normalized.split('_', 1)[1]}"

    return normalized

async def handle_user_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fallback handler for generic text messages. Forwards them to the admin group."""
    # Check rate limit first
    if await check_user_rate_limit(update, context):
        return

    user = update.effective_user
    text = update.message.text

    safe_name = html.escape(user.full_name or "User")
    safe_text = html.escape(text or "")
    
    # Send a quick acknowledgment
    await update.message.reply_text("📨 သင်၏မက်ဆေ့ခ်ျကို Admin ထံသို့ ပေးပို့လိုက်ပါသည်။ Admin မှ အမြန်ဆုံး အကြောင်းပြန်ပေးပါမည်။")
    
    # Forward to admin group
    admin_msg = (
        f"📩 <b>#SupportTicket</b>\n"
        f"User: <a href='tg://user?id={user.id}'>{safe_name}</a>\n"
        f"ID: <code>{user.id}</code>\n\n"
        f"{safe_text}"
    )
    await context.bot.send_message(
        chat_id=settings.ADMIN_GROUP_ID,
        text=admin_msg,
        parse_mode="HTML"
    )

async def send_welcome_message(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Helper functional to send welcome images."""
    from telegram import InputMediaPhoto

    # 1. Try to send the two images first (as an album/media group)
    project_root = Path(__file__).resolve().parent.parent
    img1 = project_root / "assets" / "plan1.jpg"
    img2 = project_root / "assets" / "plan2.jpg"

    if img1.exists() and img2.exists():
        try:
            with img1.open("rb") as f1, img2.open("rb") as f2:
                await context.bot.send_media_group(
                    chat_id=chat_id,
                    media=[
                        InputMediaPhoto(f1),
                        InputMediaPhoto(f2),
                    ],
                )
        except Exception as e:
            logger.error(f"Failed to send welcome images: {e}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    # Check rate limit (but allow admins to bypass)
    if user.id not in settings.ADMIN_IDS:
        if await check_user_rate_limit(update, context):
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

    # 1. Send short greeting to attach the persistent reply keyboard
    await update.message.reply_text(
        "👋 မင်္ဂလာပါ",
        reply_markup=main_menu_keyboard(),
    )
    
    # 2. Send the plan images
    await send_welcome_message(user.id, context)
    
    # 3. Send the main welcome text with inline selection buttons
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
    data = normalize_callback_data(query.data)

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
        
        # await send_welcome_message(user.id, context)
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
        
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

        await context.bot.send_message(
            chat_id=user.id,
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
        await query.edit_message_text(
            text=single_payment_instructions(video["title"], amount),
            reply_markup=back_to_main_keyboard()
        )
        return


async def handle_stale_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fallback for outdated inline buttons still visible in user chat history."""
    query = update.callback_query
    user = update.effective_user
    if not query or not user:
        return

    await query.answer("ခလုတ်ဟောင်းဖြစ်နေပါတယ်။ အသစ်ပြန်ဖွင့်ပေးလိုက်ပါပြီ။", show_alert=True)

    sm = context.bot_data["session_manager"]
    await sm.reset(user.id)

    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=user.id,
        text=WELCOME,
        reply_markup=start_inline_keyboard(),
    )

