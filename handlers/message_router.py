"""
handlers/message_router.py — Routes admin replies (Text, Media, Documents) to the correct user.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from db.orders import get_order_by_admin_msg_id
from db.logs import log_action
from config import settings
from utils.retry import async_retry

logger = logging.getLogger(__name__)


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Called when an admin sends ANY message as a reply to a forwarded order in the admin group.
    Forwards text, videos, documents, or photos back to the corresponding user.
    """
    message = update.message
    admin_user = update.effective_user

    if admin_user.id not in settings.ADMIN_IDS:
        return
    if not message.reply_to_message:
        return

    replied_msg = message.reply_to_message

    # Check if replied message is a Support Ticket
    if replied_msg.text and "📩 #SupportTicket" in replied_msg.text:
        # Extract user ID
        import re
        match = re.search(r"ID:\s*(\d+)", replied_msg.text)
        if match:
            user_id = int(match.group(1))
            try:
                # Tell the user it's an admin reply if it's text
                if message.text:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"👨‍💻 <b>Admin Reply:</b>\n\n{message.text}",
                        parse_mode="HTML"
                    )
                else:
                    await context.bot.copy_message(
                        chat_id=user_id,
                        from_chat_id=message.chat_id,
                        message_id=message.message_id,
                    )
                logger.info(f"Copied admin support reply to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to copy admin support reply to user {user_id}: {e}")
            return

    replied_msg_id = replied_msg.message_id
    order = await get_order_by_admin_msg_id(replied_msg_id)
    if not order:
        return

    user_id: int = order["user_id"]
    order_id: str = order["id"]

    try:
        # Use copy_message so it duplicates the EXACT media/text without the "Forwarded from" header
        copied_msg = await async_retry(
            lambda: context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat_id,
                message_id=message.message_id,
            ),
            label="copy_message_to_user",
        )
        logger.info(f"Copied admin msg to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to copy admin reply to user {user_id}: {e}")
        return

    # Keep track in DB
    detail_text = f"msg_id={copied_msg.message_id}"
    if message.text:
        detail_text += f", text={message.text[:50]}"
    elif message.video:
        detail_text += ", type=video"
    elif message.document:
        detail_text += ", type=document"

    await log_action(
        action_type="admin_delivery_sent",
        admin_id=admin_user.id,
        user_id=user_id,
        order_id=order_id,
        detail=detail_text
    )
