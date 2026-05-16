"""
handlers/join_request_handler.py — Admin workflow for channel join requests.
"""
import html
import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import settings
from data.keyboards import join_request_admin_keyboard
from db.logs import log_action

logger = logging.getLogger(__name__)


async def _notify_admins(context: ContextTypes.DEFAULT_TYPE, text: str, chat_id: int, user_id: int) -> None:
    """Send join request details to admin group and admin users."""
    keyboard = join_request_admin_keyboard(chat_id=chat_id, user_id=user_id)

    sent_to_group = False
    try:
        await context.bot.send_message(
            chat_id=settings.ADMIN_GROUP_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        sent_to_group = True
    except Exception as exc:
        logger.error(f"Failed to notify admin group for join request: {exc}")

    # Fallback/extra visibility: also DM each admin if group post fails.
    if not sent_to_group:
        for admin_id in settings.ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
            except Exception as exc:
                logger.error(f"Failed to notify admin {admin_id} for join request: {exc}")


async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Receive join requests from channels/groups where bot has rights and route to admins."""
    join_req = update.chat_join_request
    if not join_req:
        return

    req_user = join_req.from_user
    req_chat = join_req.chat

    user_name = html.escape(req_user.full_name or "User")
    username = f"@{html.escape(req_user.username)}" if req_user.username else "(username မရှိ)"
    chat_title = html.escape(req_chat.title or str(req_chat.id))

    msg = (
        "📥 <b>VIP Join Request</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"Channel: <b>{chat_title}</b>\n"
        f"Channel ID: <code>{req_chat.id}</code>\n"
        f"User: <a href='tg://user?id={req_user.id}'>{user_name}</a> ({username})\n"
        f"User ID: <code>{req_user.id}</code>"
    )

    await _notify_admins(context, msg, chat_id=req_chat.id, user_id=req_user.id)
    await log_action(
        action_type="join_request_received",
        user_id=req_user.id,
        detail=f"chat_id={req_chat.id}",
    )


async def handle_join_request_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin approve/reject callbacks for join requests."""
    query = update.callback_query
    await query.answer()

    admin_user = update.effective_user
    if admin_user.id not in settings.ADMIN_IDS:
        await query.answer("⛔ Admin only", show_alert=True)
        return

    data = query.data or ""
    # Expected format: jr:approve:<chat_id>:<user_id> or jr:reject:<chat_id>:<user_id>
    try:
        _, action, chat_id_str, user_id_str = data.split(":", 3)
        chat_id = int(chat_id_str)
        user_id = int(user_id_str)
    except Exception:
        await query.answer("⚠️ Invalid join request action", show_alert=True)
        return

    try:
        if action == "approve":
            await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
            action_text = "approved"
            result_line = "✅ Join request approved"
            log_type = "join_request_approved"
        elif action == "reject":
            await context.bot.decline_chat_join_request(chat_id=chat_id, user_id=user_id)
            action_text = "rejected"
            result_line = "❌ Join request rejected"
            log_type = "join_request_rejected"
        else:
            await query.answer("⚠️ Unsupported action", show_alert=True)
            return
    except Exception as exc:
        logger.error(f"Join request {action} failed chat={chat_id} user={user_id}: {exc}")
        await query.answer("⚠️ Action failed or request already handled", show_alert=True)
        return

    await log_action(
        action_type=log_type,
        admin_id=admin_user.id,
        user_id=user_id,
        detail=f"chat_id={chat_id}",
    )

    admin_name = html.escape(admin_user.first_name or "Admin")
    current = query.message.text_html if query.message and query.message.text_html else (query.message.text if query.message else "")
    if current:
        updated = (
            f"{current}\n\n"
            f"{result_line} by <b>{admin_name}</b>\n"
            f"Action: <code>{action_text}</code>"
        )
        try:
            await query.edit_message_text(updated, parse_mode="HTML", reply_markup=None)
        except Exception:
            # If message is unchanged or cannot be edited, silently ignore.
            pass
