"""
handlers/broadcast_handler.py — Admin broadcast flow with selectable user segments.
"""
import logging
import re
from typing import Callable, Awaitable

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import settings
from data.keyboards import broadcast_confirm_keyboard, broadcast_segment_keyboard
from data.messages import (
    ADMIN_ONLY,
    BROADCAST_SEGMENT_PROMPT,
    BROADCAST_ASK_MESSAGE,
    BROADCAST_CANCELLED,
    broadcast_confirm_message,
    broadcast_result_message,
)
from db.logs import log_action
from db.users import (
    get_active_user_ids,
    get_paid_user_ids,
    get_no_order_user_ids,
    get_single_buyer_user_ids,
    get_bundle_buyer_user_ids,
)
from utils.retry import async_retry

logger = logging.getLogger(__name__)

WAITING_SEGMENT = 0
WAITING_MESSAGE = 1
WAITING_CONFIRM = 2

SEGMENT_LABELS = {
    "all": "All users",
    "paid": "Paid users",
    "no_order": "No-order users",
    "single": "Single buyers",
    "bundle": "Bundle buyers",
}


def _is_admin(update: Update) -> bool:
    user = update.effective_user
    return bool(user and user.id in settings.ADMIN_IDS)


async def _segment_getters() -> dict[str, Callable[[], Awaitable[list[int]]]]:
    return {
        "all": get_active_user_ids,
        "paid": get_paid_user_ids,
        "no_order": get_no_order_user_ids,
        "single": get_single_buyer_user_ids,
        "bundle": get_bundle_buyer_user_ids,
    }


async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_admin(update):
        await update.message.reply_text(ADMIN_ONLY)
        return ConversationHandler.END

    getters = await _segment_getters()
    counts = {}
    for key, getter in getters.items():
        try:
            counts[key] = len(await getter())
        except Exception as exc:
            logger.error("Failed to fetch broadcast segment %s: %s", key, exc)
            counts[key] = 0

    context.user_data["bc_counts"] = counts
    context.user_data.pop("bc_segment", None)
    context.user_data.pop("bc_message", None)

    await update.message.reply_text(
        BROADCAST_SEGMENT_PROMPT,
        reply_markup=broadcast_segment_keyboard(counts),
    )
    return WAITING_SEGMENT


async def broadcast_pick_segment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if not _is_admin(update):
        await query.answer("Admin only", show_alert=True)
        return ConversationHandler.END

    data = query.data or ""
    if data == "bc:cancel":
        await query.edit_message_text(BROADCAST_CANCELLED)
        return ConversationHandler.END

    m = re.match(r"^bc:seg:(all|paid|no_order|single|bundle)$", data)
    if not m:
        await query.answer("Invalid selection", show_alert=True)
        return WAITING_SEGMENT

    segment = m.group(1)
    context.user_data["bc_segment"] = segment
    await query.edit_message_text(
        f"✅ Segment selected: {SEGMENT_LABELS[segment]}\n\n{BROADCAST_ASK_MESSAGE}"
    )
    return WAITING_MESSAGE


async def broadcast_receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_admin(update):
        await update.message.reply_text(ADMIN_ONLY)
        return ConversationHandler.END

    segment = context.user_data.get("bc_segment")
    if not segment:
        await update.message.reply_text(BROADCAST_CANCELLED)
        return ConversationHandler.END

    body = (update.message.text or "").strip()
    if not body:
        await update.message.reply_text("⚠️ Empty message မပို့နိုင်ပါ။")
        return WAITING_MESSAGE

    getters = await _segment_getters()
    target_ids = await getters[segment]()
    context.user_data["bc_message"] = body
    context.user_data["bc_targets"] = target_ids

    await update.message.reply_text(
        broadcast_confirm_message(
            segment_label=SEGMENT_LABELS[segment],
            total_users=len(target_ids),
            body=body,
        ),
        reply_markup=broadcast_confirm_keyboard(),
    )
    return WAITING_CONFIRM


async def _send_broadcast(
    context: ContextTypes.DEFAULT_TYPE,
    user_ids: list[int],
    message: str,
) -> tuple[int, int, list[int]]:
    import asyncio

    sent = 0
    failed_ids: list[int] = []

    if not user_ids:
        return sent, 0, failed_ids

    batch_size = max(1, settings.BROADCAST_BATCH_SIZE)
    delay = max(0.0, settings.BROADCAST_BATCH_DELAY_SECONDS)

    for i in range(0, len(user_ids), batch_size):
        batch = user_ids[i : i + batch_size]

        async def _send_one(uid: int) -> tuple[int, bool]:
            try:
                await async_retry(
                    lambda: context.bot.send_message(chat_id=uid, text=message),
                    label="broadcast_send",
                )
                return uid, True
            except Exception:
                return uid, False

        results = await asyncio.gather(*[_send_one(uid) for uid in batch])
        for uid, ok in results:
            if ok:
                sent += 1
            else:
                failed_ids.append(uid)

        if i + batch_size < len(user_ids) and delay > 0:
            await asyncio.sleep(delay)

    return sent, len(failed_ids), failed_ids


async def broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if not _is_admin(update):
        await query.answer("Admin only", show_alert=True)
        return ConversationHandler.END

    data = query.data or ""
    if data == "bc:cancel":
        await query.edit_message_text(BROADCAST_CANCELLED)
        return ConversationHandler.END

    if data != "bc:send":
        await query.answer("Invalid action", show_alert=True)
        return WAITING_CONFIRM

    segment = context.user_data.get("bc_segment")
    body = context.user_data.get("bc_message")
    target_ids = context.user_data.get("bc_targets", [])

    if not segment or not body:
        await query.edit_message_text(BROADCAST_CANCELLED)
        return ConversationHandler.END

    sent, failed, failed_ids = await _send_broadcast(context, target_ids, body)

    await query.edit_message_text(
        broadcast_result_message(
            segment_label=SEGMENT_LABELS[segment],
            target=len(target_ids),
            sent=sent,
            failed=failed,
        )
    )

    failed_preview = ",".join(str(uid) for uid in failed_ids[:20])
    await log_action(
        action_type="admin_broadcast",
        admin_id=update.effective_user.id if update.effective_user else None,
        detail=(
            f"segment={segment} target={len(target_ids)} sent={sent} failed={failed}"
            + (f" failed_ids={failed_preview}" if failed_preview else "")
        ),
    )

    context.user_data.pop("bc_segment", None)
    context.user_data.pop("bc_message", None)
    context.user_data.pop("bc_targets", None)
    return ConversationHandler.END


async def broadcast_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(BROADCAST_CANCELLED)
    elif update.message:
        await update.message.reply_text(BROADCAST_CANCELLED)

    context.user_data.pop("bc_segment", None)
    context.user_data.pop("bc_message", None)
    context.user_data.pop("bc_targets", None)
    return ConversationHandler.END


def build_broadcast_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_start)],
        states={
            WAITING_SEGMENT: [
                CallbackQueryHandler(broadcast_pick_segment, pattern=r"^bc:(seg:|cancel)"),
            ],
            WAITING_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_receive_message),
                CallbackQueryHandler(broadcast_cancel, pattern=r"^bc:cancel$"),
            ],
            WAITING_CONFIRM: [
                CallbackQueryHandler(broadcast_confirm, pattern=r"^bc:(send|cancel)$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", broadcast_cancel)],
        allow_reentry=True,
        per_chat=True,
        per_user=True,
        per_message=False,
    )
