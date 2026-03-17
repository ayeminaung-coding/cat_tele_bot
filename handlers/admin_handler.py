"""
handlers/admin_handler.py — Admin group: forward payment + approve/reject callbacks.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import settings
from db.payments import (
    get_payment_by_id,
    is_duplicate_approval,
    update_payment_status,
)
from db.users import get_user
from db.logs import log_action
from data.messages import (
    REJECTION_MESSAGE,
    admin_caption,
    admin_approved_caption,
    admin_rejected_caption,
)
from data.keyboards import admin_action_keyboard, retry_keyboard
from data.plans import get_plan
from handlers.invite_handler import generate_and_send_invite
from utils.retry import async_retry

logger = logging.getLogger(__name__)


async def forward_to_admin(
    context: ContextTypes.DEFAULT_TYPE,
    payment_id: str,
    user_id: int,
    username: str | None,
    first_name: str,
    plan_id: str,
    amount: int,
    file_id: str,
) -> int | None:
    """
    Send the user's screenshot + payment details to the admin group.
    Returns the sent message's ID (stored so replies can be routed back).
    """
    plan = get_plan(plan_id)
    caption = admin_caption(user_id, username, first_name, plan, amount, payment_id)

    try:
        msg = await async_retry(
            lambda: context.bot.send_photo(
                chat_id=settings.ADMIN_GROUP_ID,
                photo=file_id,
                caption=caption,
                reply_markup=admin_action_keyboard(payment_id),
            ),
            label="forward_to_admin",
        )
        return msg.message_id
    except Exception as e:
        logger.error(f"Failed to forward to admin group: {e}")
        return None


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles ✅ approve / ❌ reject inline button clicks in admin group.
    Only registered ADMIN_IDS can trigger actions.
    """
    query = update.callback_query
    await query.answer()

    admin_user = update.effective_user

    # ── Security: only authorized admins ───────────────────
    if admin_user.id not in settings.ADMIN_IDS:
        logger.warning(f"Unauthorized callback from user {admin_user.id}")
        return

    data = query.data  # "approve:<uuid>" or "reject:<uuid>"
    action, payment_id = data.split(":", 1)

    # ── Load payment ────────────────────────────────────────
    payment = await get_payment_by_id(payment_id)
    if not payment:
        await query.edit_message_caption(
            caption="❌ Payment ကို ရှာမတွေ့ပါ (ID မှားနေသည်)။",
        )
        return

    user_id: int = payment["user_id"]
    plan_id: str = payment["plan_id"]
    admin_name = admin_user.first_name or "Admin"

    # ══════════ APPROVE ══════════════════════════════════════
    if action == "approve":
        # Duplicate approval guard
        if await is_duplicate_approval(payment_id):
            await query.answer("⚠️ ဤ payment ကို ရှိပြီးသား အတည်ပြုပြီးဖြစ်သည်!", show_alert=True)
            return

        # Generate invite link and notify user
        link = await generate_and_send_invite(context, user_id, payment_id, plan_id)

        # Edit admin message to show approved
        approved_text = admin_approved_caption(admin_name)
        if link:
            approved_text += f"\n🔗 Link: {link}"
        try:
            await query.edit_message_caption(
                caption=f"{query.message.caption}\n\n{approved_text}",
                reply_markup=None,
            )
        except Exception as e:
            logger.warning(f"Could not edit admin message: {e}")

        await log_action(
            action_type="approve",
            admin_id=admin_user.id,
            user_id=user_id,
            payment_id=payment_id,
        )

    # ══════════ REJECT ════════════════════════════════════════
    elif action == "reject":
        # Guard: only reject pending payments
        if payment.get("status") in ("approved", "rejected"):
            await query.answer("⚠️ ဤ payment ကို ရှိပြီးသား စီမံပြီးဖြစ်သည်!", show_alert=True)
            return

        # Update DB
        await update_payment_status(payment_id, status="rejected")

        # Notify user
        try:
            await async_retry(
                lambda: context.bot.send_message(
                    chat_id=user_id,
                    text=REJECTION_MESSAGE,
                    reply_markup=retry_keyboard(),
                ),
                label="send_rejection",
            )
        except Exception as e:
            logger.error(f"Failed to send rejection to user {user_id}: {e}")

        # Edit admin message
        rejected_text = admin_rejected_caption(admin_name)
        try:
            await query.edit_message_caption(
                caption=f"{query.message.caption}\n\n{rejected_text}",
                reply_markup=None,
            )
        except Exception as e:
            logger.warning(f"Could not edit admin message: {e}")

        await log_action(
            action_type="reject",
            admin_id=admin_user.id,
            user_id=user_id,
            payment_id=payment_id,
        )
