"""
handlers/user_handler.py — /start command and plan selection callback.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from db.users import upsert_user, get_user
from data.messages import (
    WELCOME, ALREADY_ACTIVE, BANNED,
    plan_list_header, payment_instructions,
)
from data.keyboards import view_plans_keyboard, plan_selection_keyboard
from data.plans import get_plan, PLANS
from utils.session import IDLE, PLAN_SELECTED, AWAITING_SCREENSHOT
from utils.unique_amount import get_unique_amount
from config import settings

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — register user and show welcome."""
    user = update.effective_user
    if not user:
        return

    # Upsert user record
    await upsert_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name or "User",
    )

    # Check ban / active status
    db_user = await get_user(user.id)
    if db_user:
        if db_user.get("status") == "banned":
            await update.message.reply_text(BANNED)
            return
        if db_user.get("status") == "active":
            await update.message.reply_text(ALREADY_ACTIVE)
            return

    # Reset session
    sm = context.bot_data["session_manager"]
    await sm.reset(user.id)

    await update.message.reply_text(
        WELCOME,
        reply_markup=view_plans_keyboard(),
    )


async def handle_plan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles:
      - callback_data="retry"          → show plan list
      - callback_data="plan:<plan_id>" → store plan, show payment instructions
    """
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    sm = context.bot_data["session_manager"]

    data = query.data

    # ── Show plan list (retry or initial view) ─────────────
    if data == "retry":
        # Check ban
        db_user = await get_user(user.id)
        if db_user and db_user.get("status") == "banned":
            await query.edit_message_text(BANNED)
            return

        await sm.reset(user.id)
        await query.edit_message_text(
            plan_list_header(),
            reply_markup=plan_selection_keyboard(),
        )
        return

    # ── Plan selected ──────────────────────────────────────
    if data.startswith("plan:"):
        plan_id = data.split(":", 1)[1]
        plan = get_plan(plan_id)
        if not plan:
            await query.edit_message_text("❓ မသိသော အစီအစဉ်။ ထပ်မံ /start ကို နှိပ်ပါ။")
            return

        # Compute unique amount
        amount: int = (
            get_unique_amount(plan_id)
            if settings.USE_UNIQUE_AMOUNT
            else plan["price"]
        )

        # Save session
        await sm.set(user.id, state=AWAITING_SCREENSHOT, plan_id=plan_id, amount=amount)

        await query.edit_message_text(
            payment_instructions(plan, amount),
            parse_mode=None,
        )
