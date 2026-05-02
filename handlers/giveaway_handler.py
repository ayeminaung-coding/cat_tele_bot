"""
handlers/giveaway_handler.py — Admin giveaway commands and comment capture.
"""
from __future__ import annotations

import logging
import random
import re
from typing import Optional, Tuple

from telegram import Update
from telegram.ext import ContextTypes

from config import settings
from db.giveaways import (
    create_giveaway,
    get_active_giveaway_by_post,
    get_giveaway_by_id,
    get_giveaway_by_post,
    mark_giveaway_drawn,
    reset_giveaway_draw,
)
from db.giveaway_entries import (
    create_giveaway_entry,
    get_giveaway_entry_count,
    list_giveaway_entries,
    list_latest_entries,
)
from db.logs import log_action

logger = logging.getLogger(__name__)
_secure_rand = random.SystemRandom()


async def handle_giveaway_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.from_user:
        return

    if not message.reply_to_message:
        return

    channel_id, post_id = _extract_post_ref_from_comment(message)
    if channel_id is None or post_id is None:
        return

    giveaway = await get_active_giveaway_by_post(channel_id=channel_id, post_id=post_id)
    if not giveaway:
        return

    text = message.text or message.caption
    if not text:
        return

    inserted = await create_giveaway_entry(
        giveaway_id=giveaway["id"],
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        comment_text=text,
        comment_message_id=message.message_id,
        comment_chat_id=message.chat_id,
        comment_created_at=message.date,
    )
    if inserted:
        await log_action(
            action_type="giveaway_entry_added",
            user_id=message.from_user.id,
            detail=f"giveaway_id={giveaway['id']} post_id={post_id}",
        )


async def giveaway_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    if update.effective_user.id not in settings.ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only")
        return

    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /giveaway_start <post_link_or_id> <winner_count>"
        )
        return

    post_ref = args[0]
    winner_count_raw = args[1]
    try:
        winner_count = max(1, int(winner_count_raw))
    except ValueError:
        await update.message.reply_text("Winner count must be a number.")
        return

    channel_id, post_id = await _parse_post_ref(post_ref, context)
    if channel_id is None or post_id is None:
        await update.message.reply_text(
            "Could not parse the post link/ID. Use a t.me link or channel_id:post_id."
        )
        return

    existing = await get_active_giveaway_by_post(channel_id=channel_id, post_id=post_id)
    if existing:
        await update.message.reply_text(
            f"Giveaway already active. ID: {existing['id']}"
        )
        return

    giveaway = await create_giveaway(
        channel_id=channel_id,
        post_id=post_id,
        discussion_chat_id=settings.DISCUSSION_GROUP_ID,
        winner_count=winner_count,
        created_by=update.effective_user.id,
    )

    await log_action(
        action_type="giveaway_started",
        admin_id=update.effective_user.id,
        detail=f"giveaway_id={giveaway['id']} post_id={post_id}",
    )

    await update.message.reply_text(
        "Giveaway started.\n"
        f"ID: {giveaway['id']}\n"
        f"Post: {post_id}\n"
        f"Winners: {winner_count}"
    )


async def giveaway_draw_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    if update.effective_user.id not in settings.ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only")
        return

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "Usage: /giveaway_draw <giveaway_id_or_post_link>"
        )
        return

    giveaway = await _resolve_giveaway(args[0], context)
    if not giveaway:
        await update.message.reply_text("Giveaway not found.")
        return

    if giveaway.get("status") == "drawn":
        winners = giveaway.get("winner_user_ids") or []
        await update.message.reply_text(
            "Giveaway already drawn.\n"
            f"Winners: {', '.join(str(x) for x in winners) or 'None'}"
        )
        return

    entries = await list_giveaway_entries(giveaway_id=giveaway["id"])
    if not entries:
        await update.message.reply_text("No entries yet.")
        return

    unique_entries: dict[int, dict] = {}
    for entry in entries:
        user_id = entry.get("user_id")
        if user_id is None:
            continue
        unique_entries[int(user_id)] = entry

    unique_list = list(unique_entries.values())
    if not unique_list:
        await update.message.reply_text("No valid entries to draw from.")
        return

    winner_count = int(giveaway.get("winner_count", 1))
    sample_size = min(winner_count, len(unique_list))
    winners = _secure_rand.sample(unique_list, k=sample_size)
    winner_user_ids = [int(entry["user_id"]) for entry in winners]

    await mark_giveaway_drawn(giveaway_id=giveaway["id"], winner_user_ids=winner_user_ids)

    await log_action(
        action_type="giveaway_drawn",
        admin_id=update.effective_user.id,
        detail=f"giveaway_id={giveaway['id']} winners={winner_user_ids}",
    )

    winner_lines = []
    for idx, entry in enumerate(winners, start=1):
        uname = entry.get("username")
        display = f"@{uname}" if uname else entry.get("first_name") or str(entry.get("user_id"))
        winner_lines.append(f"{idx}. {display} (id={entry.get('user_id')})")

    await update.message.reply_text(
        "Winners selected:\n" + "\n".join(winner_lines)
    )


async def giveaway_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    if update.effective_user.id not in settings.ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only")
        return

    args = context.args or []
    if not args:
        await update.message.reply_text("Usage: /giveaway_stats <giveaway_id_or_post_link>")
        return

    giveaway = await _resolve_giveaway(args[0], context)
    if not giveaway:
        await update.message.reply_text("Giveaway not found.")
        return

    count = await get_giveaway_entry_count(giveaway_id=giveaway["id"])
    samples = await list_latest_entries(giveaway_id=giveaway["id"], limit=3)

    sample_lines = []
    for entry in samples:
        uname = entry.get("username")
        display = f"@{uname}" if uname else entry.get("first_name") or str(entry.get("user_id"))
        comment_text = entry.get("comment_text") or ""
        sample_lines.append(f"- {display}: {comment_text[:80]}")

    winners = giveaway.get("winner_user_ids") or []
    winners_text = ", ".join(str(x) for x in winners) if winners else "None"

    response = (
        f"Giveaway ID: {giveaway['id']}\n"
        f"Post: {giveaway.get('post_id')}\n"
        f"Status: {giveaway.get('status')}\n"
        f"Unique entries: {count}\n"
        f"Winners: {winners_text}"
    )

    if sample_lines:
        response += "\n\nRecent comments:\n" + "\n".join(sample_lines)

    await update.message.reply_text(response)


async def giveaway_reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    if update.effective_user.id not in settings.ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only")
        return

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "Usage: /giveaway_reset <giveaway_id_or_post_link>"
        )
        return

    giveaway = await _resolve_giveaway(args[0], context)
    if not giveaway:
        await update.message.reply_text("Giveaway not found.")
        return

    if giveaway.get("status") != "drawn":
        await update.message.reply_text("Giveaway is not drawn yet.")
        return

    await reset_giveaway_draw(giveaway_id=giveaway["id"])

    await log_action(
        action_type="giveaway_reset",
        admin_id=update.effective_user.id,
        detail=f"giveaway_id={giveaway['id']}",
    )

    await update.message.reply_text(
        "Giveaway reset. You can draw again."
    )


def _extract_post_ref_from_comment(message) -> Tuple[Optional[int], Optional[int]]:
    replied = message.reply_to_message
    if not replied:
        return None, None

    # PTB v21: forward_origin holds channel post metadata
    origin = getattr(replied, "forward_origin", None)
    if origin and getattr(origin, "type", None) == "channel":
        origin_chat = getattr(origin, "chat", None)
        channel_id = getattr(origin_chat, "id", None)
        post_id = getattr(origin, "message_id", None)
        if channel_id and post_id:
            return int(channel_id), int(post_id)

    # Fallback for older forward metadata
    forward_chat = getattr(replied, "forward_from_chat", None)
    forward_msg_id = getattr(replied, "forward_from_message_id", None)
    if forward_chat and forward_msg_id:
        return int(forward_chat.id), int(forward_msg_id)

    return None, None


async def _resolve_giveaway(arg: str, context: ContextTypes.DEFAULT_TYPE) -> Optional[dict]:
    giveaway = await get_giveaway_by_id(arg)
    if giveaway:
        return giveaway

    channel_id, post_id = await _parse_post_ref(arg, context)
    if channel_id is None or post_id is None:
        return None

    giveaway = await get_active_giveaway_by_post(channel_id=channel_id, post_id=post_id)
    if giveaway:
        return giveaway

    return await get_giveaway_by_post(channel_id=channel_id, post_id=post_id)


async def _parse_post_ref(ref: str, context: ContextTypes.DEFAULT_TYPE) -> Tuple[Optional[int], Optional[int]]:
    cleaned = ref.strip()

    # Format: channel_id:post_id
    if ":" in cleaned:
        parts = cleaned.split(":", 1)
        if len(parts) == 2 and parts[0].lstrip("-").isdigit() and parts[1].isdigit():
            return int(parts[0]), int(parts[1])

    # Format: t.me/c/<internal_id>/<post_id>
    match_private = re.search(r"t\.me/c/(\d+)/(\d+)", cleaned)
    if match_private:
        internal_id = match_private.group(1)
        post_id = int(match_private.group(2))
        channel_id = int(f"-100{internal_id}")
        return channel_id, post_id

    # Format: t.me/<username>/<post_id>
    match_public = re.search(r"t\.me/([A-Za-z0-9_]+)/([0-9]+)", cleaned)
    if match_public:
        username = match_public.group(1)
        post_id = int(match_public.group(2))
        try:
            chat = await context.bot.get_chat(f"@{username}")
            return int(chat.id), post_id
        except Exception as exc:
            logger.warning("Failed to resolve channel %s: %s", username, exc)
            return None, None

    return None, None
