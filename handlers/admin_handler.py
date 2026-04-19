"""
handlers/admin_handler.py — Admin group: forward order + approve/reject callbacks.
"""
import asyncio
import logging
from telegram import Update
from telegram.ext import ContextTypes

from config import settings
from db.orders import (
    get_order_by_id,
    is_duplicate_approval,
    update_order_status,
)
from db.logs import log_action
from data.messages import (
    REJECTION_MESSAGE,
    approval_message,
    bundle_approval_message,
    single_approval_with_link,
    admin_caption,
    admin_approved_caption,
    admin_rejected_caption,
)
from data.keyboards import admin_action_keyboard
from utils.retry import async_retry

logger = logging.getLogger(__name__)

async def userstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin stats about users."""
    if update.effective_user.id not in settings.ADMIN_IDS:
        await update.message.reply_text("⛔ ဤ command ကို Admin သာ သုံးနိုင်သည်။")
        return

    from db.users import get_user_stats
    from db.orders import get_order_stats
    
    stats = await get_user_stats()
    order_stats = await get_order_stats()
    
    msg = (
        "📊 <b>Bot User Statistics</b>\n\n"
        f"👥 Total Users: <b>{stats['total']}</b>\n"
        f"🆕 Joined Today: <b>{stats['daily']}</b>\n\n"
        "💳 <b>Order Statistics</b>\n\n"
        f"✅ Today's Orders: <b>{order_stats['today']}</b>\n"
        f"📅 Yesterday's Orders: <b>{order_stats['yesterday']}</b>"
    )
    await update.message.reply_text(msg, parse_mode="HTML")


async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin-only Telegram /health command."""
    if update.effective_user.id not in settings.ADMIN_IDS:
        await update.message.reply_text("⛔ ဤ command ကို Admin သာ သုံးနိုင်သည်။")
        return

    health_status = "ok"

    # Database check
    db_text = "connected"
    try:
        from db.client import get_supabase
        sb = get_supabase()
        await asyncio.to_thread(
            lambda: sb.table("users").select("telegram_id").limit(1).execute()
        )
    except Exception as e:
        db_text = f"error: {str(e)[:50]}"
        health_status = "degraded"

    # Bot check
    bot_text = "unknown"
    try:
        me = await context.bot.get_me()
        bot_text = f"@{me.username}"
    except Exception as e:
        bot_text = f"error: {str(e)[:50]}"
        health_status = "degraded"

    # Queue check (if available)
    queue_line = "n/a"
    dispatcher = context.application.bot_data.get("update_dispatcher")
    if dispatcher and hasattr(dispatcher, "queue_size") and hasattr(dispatcher, "queue_capacity"):
        q_size = dispatcher.queue_size()
        q_cap = dispatcher.queue_capacity()
        utilization = (q_size / q_cap) if q_cap else 0.0
        queue_line = f"{q_size}/{q_cap} ({utilization:.1%})"
        if utilization >= 0.9:
            health_status = "degraded"

    msg = (
        "🩺 <b>Bot Health</b>\n\n"
        f"Status: <b>{health_status}</b>\n"
        f"Database: <code>{db_text}</code>\n"
        f"Bot: <code>{bot_text}</code>\n"
        f"Queue: <code>{queue_line}</code>"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

async def forward_to_admin(
    context: ContextTypes.DEFAULT_TYPE,
    order_id: str,
    user_id: int,
    username: str | None,
    first_name: str,
    order_type: str,
    amount: int,
    file_id: str,
    video_title: str | None = None,
    risk_note: str | None = None,
    disable_notification: bool = False,
) -> int | None:
    caption = admin_caption(
        user_id,
        username,
        first_name,
        order_type,
        amount,
        order_id,
        video_title,
        risk_note,
    )
    
    if disable_notification:
        caption = "🌙 [Night Order]\n\n" + caption

    try:
        msg = await async_retry(
            lambda: context.bot.send_photo(
                chat_id=settings.ADMIN_GROUP_ID,
                photo=file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=admin_action_keyboard(order_id),
                disable_notification=disable_notification,
            ),
            label="forward_to_admin",
        )
        return msg.message_id
    except Exception as e:
        logger.error(f"Failed to forward to admin group: {e}")
        return None


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    admin_user = update.effective_user
    if admin_user.id not in settings.ADMIN_IDS:
        logger.warning(f"Unauthorized callback from {admin_user.id}")
        return

    data = query.data  # "approve:<uuid>" or "reject:<uuid>"
    action, order_id = data.split(":", 1)

    order = await get_order_by_id(order_id)
    if not order:
        await query.edit_message_caption("❌ Order ကို ရှာမတွေ့ပါ (ID မှားနေသည်)။")
        return

    user_id: int = order["user_id"]
    admin_name = admin_user.first_name or "Admin"

    # ══════════ APPROVE ══════════════════════════════════════
    if action == "approve":
        if await is_duplicate_approval(order_id):
            await query.answer("⚠️ ဤ payment ကို ရှိပြီးသား အတည်ပြုပြီးဖြစ်သည်!", show_alert=True)
            return

        # Build the approval message
        order_type = order.get("type", "")
        msg_text = approval_message()

        if order_type == "bundle":
            paid_link = (settings.VIP_INVITE_LINK_PAID or "").strip()
            invite_url = ""
            try:
                invite_link = await context.bot.create_chat_invite_link(
                    chat_id=settings.VIP_CHANNEL_ID,
                    member_limit=1,
                    name=f"Order {order_id}"
                )
                invite_url = invite_link.invite_link
            except Exception as e:
                logger.error(f"Failed to create VIP invite link: {e}")

            # Always try to include the env channel link; include invite link when generated.
            if invite_url or paid_link:
                msg_text = bundle_approval_message(invite_url, paid_link)
            else:
                logger.warning("Bundle approval has no links: both invite link generation and VIP_INVITE_LINK_PAID are unavailable")

        elif order_type == "single":
            # Auto-send the stored channel link if one exists for this video
            from db.videos import get_video
            video_id = order.get("video_id")
            if video_id:
                video = await get_video(video_id)
                if video:
                    channel_id = video.get("channel_id")
                    video_title = video.get("title", "")
                    channel_link = (video.get("channel_link") or "").strip()
                    invite_url = ""

                    if channel_id:
                        try:
                            invite_link = await context.bot.create_chat_invite_link(
                                chat_id=channel_id,
                                member_limit=1,
                                name=f"Order {order_id}"
                            )
                            invite_url = invite_link.invite_link
                        except Exception as e:
                            logger.error(f"Failed to create VIP invite link for channel {channel_id}: {e}")

                    # Always include both links when available: generated invite link + DB channel link.
                    if invite_url and channel_link:
                        msg_text = single_approval_with_link(video_title, invite_url, channel_link)
                    elif invite_url:
                        msg_text = single_approval_with_link(video_title, invite_url, "")
                    elif channel_link:
                        msg_text = single_approval_with_link(video_title, "", channel_link)

        try:
            from data.keyboards import after_payment_keyboard
            # Send the approval/invite link message WITHOUT any button so it stays permanently
            await async_retry(
                lambda: context.bot.send_message(
                    chat_id=user_id,
                    text=msg_text,
                ),
                label="send_approval"
            )
            # Send the "Back to Main" button as a separate follow-up message
            await async_retry(
                lambda: context.bot.send_message(
                    chat_id=user_id,
                    text="ထပ်မံဝယ်ယူလိုပါက အောက်မှ နှိပ်ပါ 👇",
                    reply_markup=after_payment_keyboard()
                ),
                label="send_approval_nav"
            )
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")

        # Edit admin text
        try:
            await query.edit_message_caption(
                caption=f"{query.message.caption}\n\n{admin_approved_caption(admin_name)}",
                reply_markup=None,
            )
        except Exception as e:
            logger.warning(f"Could edit admin msg: {e}")

        await update_order_status(order_id, "approved")
        await log_action("approve", admin_id=admin_user.id, user_id=user_id, order_id=order_id)

    # ══════════ REJECT ════════════════════════════════════════
    elif action == "reject":
        if order.get("status") in ("approved", "rejected"):
            await query.answer("⚠️ ဤ payment ကို ရှိပြီးသား စီမံပြီးဖြစ်သည်!", show_alert=True)
            return

        await update_order_status(order_id, "rejected")

        try:
            from data.keyboards import after_payment_keyboard
            await async_retry(
                lambda: context.bot.send_message(
                    chat_id=user_id,
                    text=REJECTION_MESSAGE,
                    reply_markup=after_payment_keyboard()
                ),
                label="send_rejection",
            )
        except Exception as e:
            logger.error(f"Failed to send rejection to user {user_id}: {e}")

        try:
            await query.edit_message_caption(
                caption=f"{query.message.caption}\n\n{admin_rejected_caption(admin_name)}",
                reply_markup=None,
            )
        except Exception as e:
            pass

        await log_action("reject", admin_id=admin_user.id, user_id=user_id, order_id=order_id)
