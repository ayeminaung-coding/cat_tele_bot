"""
handlers/error_handler.py — Global PTB error handler.
"""
import html
import logging
import traceback
from telegram import Update
from telegram.ext import ContextTypes

from db.logs import log_action
from data.messages import GENERIC_ERROR
from utils.alerts import send_admin_alert

logger = logging.getLogger(__name__)


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Catches all unhandled exceptions from handlers.
    - Logs full traceback to console + Supabase
    - Sends a friendly Myanmar fallback message to user (if possible)
    """
    logger.error("Unhandled exception:", exc_info=context.error)
    tb = "".join(traceback.format_exception(type(context.error), context.error, context.error.__traceback__))

    user_id = None
    if isinstance(update, Update) and update.effective_user:
        user_id = update.effective_user.id
        try:
            if update.effective_message:
                await update.effective_message.reply_text(GENERIC_ERROR)
        except Exception:
            pass

    await log_action(
        action_type="error",
        user_id=user_id,
        detail=tb[:500],  # store first 500 chars
    )

    try:
        await send_admin_alert(
            context=context,
            title="Unhandled bot exception",
            detail=tb,
            severity="critical",
        )
    except Exception:
        # Never let error-handler alerts raise further errors.
        pass
