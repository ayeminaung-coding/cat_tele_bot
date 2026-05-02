"""
Export unique commenters for a specific channel post via MTProto (Telethon).

Usage example:
  python scripts/mtproto_export_comments.py \
    --api-id 123456 --api-hash abcdef... \
    --session mtproto.session \
    --chat -1001234567890 \
    --channel -1002223334444 \
    --post-id 987 \
    --output giveaway_entries.json

Notes:
- --chat is the discussion group ID.
- --channel is the channel ID where the post lives.
- --post-id is the channel post ID.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from telethon import TelegramClient
from telethon.tl.types import PeerChannel


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export unique commenters for a post.")
    parser.add_argument("--api-id", type=int, required=True)
    parser.add_argument("--api-hash", required=True)
    parser.add_argument("--session", required=True, help="Session file name or path")
    parser.add_argument("--chat", type=int, required=True, help="Discussion group ID")
    parser.add_argument(
        "--channel",
        required=True,
        help="Channel ID (e.g. -100...) or username (e.g. @mychannel)",
    )
    parser.add_argument("--post-id", type=int, required=True, help="Channel post ID")
    parser.add_argument("--output", default="giveaway_entries.json")
    parser.add_argument("--limit", type=int, default=0, help="Max messages to scan (0 = no limit)")
    parser.add_argument("--debug", action="store_true", help="Print matching diagnostics")
    return parser.parse_args()


def _peer_channel_id(peer: Optional[PeerChannel]) -> Optional[int]:
    if peer and hasattr(peer, "channel_id"):
        return int(peer.channel_id)
    return None


def _normalize_channel_id(channel_id: int) -> int:
    """
    Convert Bot API channel IDs (e.g. -1001234567890) to MTProto IDs (1234567890).
    If the ID is already MTProto format, return as-is.
    """
    raw = int(channel_id)
    if raw < 0 and str(raw).startswith("-100"):
        return int(str(raw)[4:])
    return abs(raw)


async def _resolve_channel_id(client: TelegramClient, raw: str) -> int:
    cleaned = str(raw).strip()
    if cleaned.startswith("@"):
        entity = await client.get_entity(cleaned)
        return int(getattr(entity, "id", 0))
    return int(cleaned)


def _is_target_reply(fwd_from: Any, channel_id: int, post_id: int) -> bool:
    if not fwd_from:
        return False

    fwd_channel_id = None
    if hasattr(fwd_from, "from_id"):
        fwd_channel_id = _peer_channel_id(fwd_from.from_id)

    fwd_post_id = getattr(fwd_from, "channel_post", None)
    expected_channel_id = _normalize_channel_id(channel_id)

    return fwd_channel_id == expected_channel_id and fwd_post_id == post_id


async def main() -> None:
    args = _parse_args()

    entries: Dict[int, Dict[str, Any]] = {}
    stats = {
        "seen": 0,
        "replies": 0,
        "missing_reply": 0,
        "missing_forward": 0,
        "channel_mismatch": 0,
        "post_mismatch": 0,
        "matched": 0,
    }

    async with TelegramClient(args.session, args.api_id, args.api_hash) as client:
        channel_id = await _resolve_channel_id(client, args.channel)
        async for msg in client.iter_messages(args.chat, limit=args.limit or None):
            stats["seen"] += 1
            if not msg.reply_to_msg_id:
                continue
            stats["replies"] += 1

            replied = await msg.get_reply_message()
            if not replied:
                stats["missing_reply"] += 1
                continue

            if not replied.fwd_from:
                stats["missing_forward"] += 1
                continue

            expected_channel_id = _normalize_channel_id(channel_id)
            fwd_channel_id = _peer_channel_id(getattr(replied.fwd_from, "from_id", None))
            fwd_post_id = getattr(replied.fwd_from, "channel_post", None)

            if fwd_channel_id != expected_channel_id:
                stats["channel_mismatch"] += 1
                continue
            if fwd_post_id != args.post_id:
                stats["post_mismatch"] += 1
                continue

            if not _is_target_reply(replied.fwd_from, channel_id, args.post_id):
                continue

            sender = await msg.get_sender()
            user_id = getattr(sender, "id", None)
            if not user_id:
                continue

            entries[int(user_id)] = {
                "user_id": int(user_id),
                "username": getattr(sender, "username", None),
                "first_name": getattr(sender, "first_name", None),
                "comment_message_id": msg.id,
                "comment_chat_id": args.chat,
                "comment_text": msg.message or "",
                "comment_created_at": msg.date.astimezone(timezone.utc).isoformat()
                if msg.date
                else datetime.now(timezone.utc).isoformat(),
            }
            stats["matched"] += 1

    output_list: List[Dict[str, Any]] = list(entries.values())
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(output_list, handle, ensure_ascii=False, indent=2)

    print(f"Exported {len(output_list)} unique commenters -> {args.output}")
    if args.debug:
        print(
            "Debug summary: "
            f"seen={stats['seen']} replies={stats['replies']} missing_reply={stats['missing_reply']} "
            f"missing_forward={stats['missing_forward']} channel_mismatch={stats['channel_mismatch']} "
            f"post_mismatch={stats['post_mismatch']} matched={stats['matched']}"
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
