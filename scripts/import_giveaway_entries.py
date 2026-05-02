"""
Import giveaway entries from a JSON export.

Usage example:
  python scripts/import_giveaway_entries.py \
    --giveaway-id gid-123 \
    --input giveaway_entries.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, Dict, List

from db.client import get_supabase
from utils.db_async import run_blocking


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import giveaway entries from JSON.")
    parser.add_argument("--giveaway-id", required=True)
    parser.add_argument("--input", required=True, help="Path to JSON file")
    parser.add_argument("--batch", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def _load_entries(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("JSON must be a list of entries")
    return data


def _chunk(items: List[Dict[str, Any]], size: int) -> List[List[Dict[str, Any]]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


async def _upsert_batch(payload: List[Dict[str, Any]]) -> None:
    sb = get_supabase()
    await run_blocking(
        lambda: sb.table("giveaway_entries")
        .upsert(payload, on_conflict="giveaway_id,user_id", ignore_duplicates=True)
        .execute()
    )


async def main() -> None:
    args = _parse_args()
    entries = _load_entries(args.input)

    payload: List[Dict[str, Any]] = []
    for entry in entries:
        user_id = entry.get("user_id")
        if not user_id:
            continue

        payload.append(
            {
                "giveaway_id": args.giveaway_id,
                "user_id": int(user_id),
                "username": entry.get("username"),
                "first_name": entry.get("first_name") or "",
                "comment_text": entry.get("comment_text") or "",
                "comment_message_id": entry.get("comment_message_id"),
                "comment_chat_id": entry.get("comment_chat_id"),
                "comment_created_at": entry.get("comment_created_at"),
            }
        )

    if args.dry_run:
        print(f"Dry run: would import {len(payload)} entries.")
        return

    batches = _chunk(payload, max(1, args.batch))
    for batch in batches:
        await _upsert_batch(batch)

    print(f"Imported {len(payload)} entries into giveaway_id={args.giveaway_id}")


if __name__ == "__main__":
    asyncio.run(main())
