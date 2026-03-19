"""
bot_app.py — Builds and configures the python-telegram-bot Application.
"""
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from config import settings
from handlers.user_handler import (
    start_command,
    handle_callback,
    handle_buy_single_text,
    handle_buy_bundle_text,
)
from handlers.payment_handler import handle_screenshot
from handlers.admin_handler import handle_admin_callback
from handlers.admin_video_handler import (
    build_addvideo_conv,
    build_setvideolink_conv,
    build_setbundletext_conv,
    deletevideo_start,
    handle_delete_select,
    handle_delete_confirm,
    handle_delete_cancel,
)
from handlers.message_router import handle_admin_reply
from handlers.error_handler import handle_error
from utils.session import SessionManager


def build_application() -> Application:
    app = (
        Application.builder()
        .token(settings.BOT_TOKEN)
        .build()
    )

    app.bot_data["session_manager"] = SessionManager()

    # ── User-side commands ─────────────────────────────────
    app.add_handler(CommandHandler("start", start_command))
    
    # ── Text Handlers for Old Reply Keyboards ──────────────
    app.add_handler(MessageHandler(filters.Text("🎬 ဇာတ်လမ်း တစ်ပုဒ်ပဲ VIPဝင်မယ် - 1000 ကျပ်"), handle_buy_single_text))
    app.add_handler(MessageHandler(filters.Text("📦 ဇာတ်လမ်း 15ပုဒ် အစုလိုက် VIPဝင်မယ် - 5000 ကျပ်"), handle_buy_bundle_text))

    # ── Inline button callbacks ────────────────────────────
    # Main menu selections, video selection, and back buttons
    app.add_handler(CallbackQueryHandler(handle_callback, pattern=r"^(buy:|video:|back_to_main|retry)"))
    
    # ── Admin approve/reject (prefix: "approve:" / "reject:")
    app.add_handler(CallbackQueryHandler(handle_admin_callback, pattern=r"^(approve|reject):"))

    # ── Admin video management ─────────────────────────────
    app.add_handler(build_addvideo_conv())
    app.add_handler(build_setvideolink_conv())
    app.add_handler(build_setbundletext_conv())
    app.add_handler(CommandHandler("deletevideo", deletevideo_start))
    app.add_handler(CallbackQueryHandler(handle_delete_select, pattern=r"^del_select:"))
    app.add_handler(CallbackQueryHandler(handle_delete_confirm, pattern=r"^del_confirm:"))
    app.add_handler(CallbackQueryHandler(handle_delete_cancel, pattern=r"^del_cancel$"))

    # ── Screenshot / document upload (private chat only) ───
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & (filters.PHOTO | filters.Document.IMAGE),
            handle_screenshot,
        )
    )

    # ── Admin group text/media replies ─────────────────────
    # Allow Admins to reply with Text, Video, Document, Photo, Voice, etc
    app.add_handler(
        MessageHandler(
            filters.Chat(settings.ADMIN_GROUP_ID) & filters.REPLY & ~filters.COMMAND,
            handle_admin_reply,
        )
    )

    # ── Global error handler ───────────────────────────────
    app.add_error_handler(handle_error)

    return app

