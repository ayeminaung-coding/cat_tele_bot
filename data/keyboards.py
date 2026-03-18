"""
data/keyboards.py — Inline keyboard builders.
"""
from typing import List, Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu on /start"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 ဗီဒီယို တစ်ကားဝယ်မည်", callback_data="buy:single")],
        [InlineKeyboardButton("📦 ဗီဒီယို ၁၅ ကား အစုလိုက်ဝယ်မည်", callback_data="buy:bundle")]
    ])


def single_video_selection_keyboard(videos: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Dynamically build list of videos from the DB"""
    buttons = []
    for vid in videos:
        icon = "✅" if vid["status"] == "available" else "❌"
        text = f"{icon} {vid['title']}"
        buttons.append([InlineKeyboardButton(text, callback_data=f"video:{vid['id']}")])
    
    # Back button
    buttons.append([InlineKeyboardButton("🔙 ပြန်ထွက်မည်", callback_data="back_to_main")])
    return InlineKeyboardMarkup(buttons)


def admin_action_keyboard(order_id: str) -> InlineKeyboardMarkup:
    """Approve / Reject buttons sent to admin group."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ အတည်ပြုမည်", callback_data=f"approve:{order_id}"),
            InlineKeyboardButton("❌ ငြင်းပယ်မည်", callback_data=f"reject:{order_id}"),
        ]
    ])
