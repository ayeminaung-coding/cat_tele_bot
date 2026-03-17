"""
handlers/invite_handler.py — Generates and sends VIP invite links.
"""
import logging
from datetime import datetime, timedelta, timezone
from telegram.ext import ContextTypes

from config import settings
from db.payments import update_payment_status
from db.users import set_user_status
from db.logs import log_action
from data.messages import approval_message
from data.plans import get_plan
from utils.retry import async_retry

logger = logging.getLogger(__name__)


async def generate_and_send_invite(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    payment_id: str,
    plan_id: str,
) -> str | None:
    """
    1. Create a one-use invite link (expires in 24h).
    2. Store it in the payment record.
    3. Update user status to 'active'.
    4. Send congratulations message with the link.
    Returns the invite link on success, None on failure.
    """
    expire_date = datetime.now(tz=timezone.utc) + timedelta(hours=24)

    try:
        invite = await async_retry(
            lambda: context.bot.create_chat_invite_link(
                chat_id=settings.VIP_CHANNEL_ID,
                member_limit=1,
                expire_date=expire_date,
                name=f"VIP-{user_id}",
            ),
            label="create_chat_invite_link",
        )
        link = invite.invite_link
    except Exception as e:
        logger.error(f"Failed to create invite link for user {user_id}: {e}")
        await log_action("error", user_id=user_id, payment_id=payment_id, detail=f"invite_link_failed: {e}")
        return None

    # ── Update DB ───────────────────────────────────────────
    await update_payment_status(payment_id, status="approved", invite_link=link)
    await set_user_status(user_id, "active")

    # ── Send link to user ───────────────────────────────────
    plan = get_plan(plan_id)
    try:
        await async_retry(
            lambda: context.bot.send_message(
                chat_id=user_id,
                text=approval_message(link, plan),
            ),
            label="send_approval",
        )
    except Exception as e:
        logger.error(f"Failed to send invite link to user {user_id}: {e}")

    await log_action(
        action_type="invite_sent",
        user_id=user_id,
        payment_id=payment_id,
        detail=f"link={link}",
    )
    return link
