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
from handlers.user_handler import start_command, handle_plan_callback
from handlers.payment_handler import handle_screenshot
from handlers.admin_handler import handle_admin_callback
from handlers.message_router import handle_admin_text_reply
from handlers.error_handler import handle_error
from utils.session import SessionManager


def build_application() -> Application:
    app = (
        Application.builder()
        .token(settings.BOT_TOKEN)
        .build()
    )

    # Shared session manager across all handlers
    app.bot_data["session_manager"] = SessionManager()

    # ── User-side commands ─────────────────────────────────
    app.add_handler(CommandHandler("start", start_command))

    # ── Inline button callbacks ────────────────────────────
    # Plan selection (prefix: "plan:")
    app.add_handler(CallbackQueryHandler(handle_plan_callback, pattern=r"^plan:"))
    # Admin approve/reject (prefix: "approve:" / "reject:")
    app.add_handler(CallbackQueryHandler(handle_admin_callback, pattern=r"^(approve|reject):"))
    # Retry flow
    app.add_handler(CallbackQueryHandler(handle_plan_callback, pattern=r"^retry$"))

    # ── Screenshot / document upload (private chat only) ───
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & (filters.PHOTO | filters.Document.IMAGE),
            handle_screenshot,
        )
    )

    # ── Admin group text replies ───────────────────────────
    app.add_handler(
        MessageHandler(
            filters.Chat(settings.ADMIN_GROUP_ID) & filters.REPLY & filters.TEXT,
            handle_admin_text_reply,
        )
    )

    # ── Global error handler ───────────────────────────────
    app.add_error_handler(handle_error)

    return app
