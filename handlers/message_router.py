"""
handlers/message_router.py — Routes admin text replies to the correct user.

When an admin replies (using Telegram's reply feature) to a forwarded
payment message in the admin group, this handler finds the original user
and forwards the admin's text to them.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from db.payments import get_payment_by_admin_msg_id
from db.logs import log_action
from config import settings
from utils.retry import async_retry

logger = logging.getLogger(__name__)


async def handle_admin_text_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Called when an admin sends a text reply to a payment message in admin group.
    Only runs if:
      - Chat is admin group
      - Message is a reply (reply_to_message exists)
      - Sender is a registered admin
    """
    message = update.message
    admin_user = update.effective_user

    # ── Security: only registered admins ───────────────────
    if admin_user.id not in settings.ADMIN_IDS:
        return

    if not message.reply_to_message:
        return

    replied_msg_id = message.reply_to_message.message_id

    # ── Find linked payment ─────────────────────────────────
    payment = await get_payment_by_admin_msg_id(replied_msg_id)
    if not payment:
        logger.info(f"Admin replied to msg {replied_msg_id} but no payment linked.")
        return

    user_id: int = payment["user_id"]
    admin_text = message.text or ""

    if not admin_text.strip():
        return

    # ── Forward to user ─────────────────────────────────────
    forwarded_text = (
        f"📩 Admin မှ သတင်းစကား:\n\n{admin_text}"
    )

    try:
        await async_retry(
            lambda: context.bot.send_message(
                chat_id=user_id,
                text=forwarded_text,
            ),
            label="admin_reply_to_user",
        )
        logger.info(f"Forwarded admin msg to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to forward admin reply to user {user_id}: {e}")
        return

    await log_action(
        action_type="admin_message_sent",
        admin_id=admin_user.id,
        user_id=user_id,
        payment_id=payment.get("id"),
        detail=f"text={admin_text[:80]}",
    )
