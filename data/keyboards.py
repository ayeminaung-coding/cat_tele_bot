"""
data/keyboards.py — Keyboard builders (reply + inline).
"""
from typing import List, Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Persistent reply keyboard shown on /start and after returning to main menu."""
    return ReplyKeyboardMarkup(
        [
            ["အစကို ပြန်သွားမယ်"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def start_inline_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard shown under the welcome text."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🎬 ဇာတ်လမ်း တစ်ပုဒ်ပဲ VIPဝင်မယ် - 1000 ကျပ်", callback_data="main_buy_single")],
            [InlineKeyboardButton("📦 ဇာတ်လမ်း 15ပုဒ်  VIPဝင်မယ် - 5000 ကျပ်", callback_data="main_buy_bundle")],
        ]
    )


def single_video_selection_keyboard(videos: List[Dict[str, Any]], page: int = 0, page_size: int = 5) -> InlineKeyboardMarkup:
    """Dynamically build list of videos from the DB with pagination."""
    buttons = []
    
    start_idx = page * page_size
    end_idx = start_idx + page_size
    current_videos = videos[start_idx:end_idx]

    for vid in current_videos:
        icon = "✅" if vid["status"] == "available" else "❌"
        text = f"{icon} {vid['title']}"
        buttons.append([InlineKeyboardButton(text, callback_data=f"video:{vid['id']}")])
    
    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ ရှေ့သို့", callback_data=f"page:{page-1}"))
    if end_idx < len(videos):
        nav_buttons.append(InlineKeyboardButton("နောက်သို့ ➡️", callback_data=f"page:{page+1}"))
        
    if nav_buttons:
        buttons.append(nav_buttons)
    
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

def after_payment_keyboard() -> InlineKeyboardMarkup:
    """Keyboard sent after payment approval/rejection to restart the bot"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 ပင်မစာမျက်နှာသို့ ပြန်သွားမည်", callback_data="back_to_main")]
    ])

def buy_bundle_confirm_keyboard() -> InlineKeyboardMarkup:
    """Button to confirm bundle purchase after reading info."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ ဝယ်မယ်", callback_data="buy:bundle")],
        [InlineKeyboardButton("🔙 ပြန်ထွက်မယ်", callback_data="back_to_main")]
    ])

def back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Simple back button to return to main menu from payment instructions."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 ပြန်ထွက်မယ်", callback_data="back_to_main")]
    ])


def delete_video_list_keyboard(videos: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """List of all videos for admin delete selection."""
    buttons = [
        [InlineKeyboardButton(f"🗑 {v['title']}", callback_data=f"del_select:{v['id']}")]
        for v in videos
    ]
    buttons.append([InlineKeyboardButton("❌ ပယ်ဖျက်ပြီ", callback_data="del_cancel")])
    return InlineKeyboardMarkup(buttons)


def delete_confirm_keyboard(video_id: str) -> InlineKeyboardMarkup:
    """Confirm / cancel inline keyboard for deleting a specific video."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ ဖျက်မည်", callback_data=f"del_confirm:{video_id}"),
            InlineKeyboardButton("❌ မဖျက်ပါ", callback_data="del_cancel"),
        ]
    ])


def set_video_link_keyboard(videos: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """List of all videos for admin setvideolink selection."""
    buttons = []
    for v in videos:
        has_link = "🔗" if v.get("channel_link") else "➕"
        buttons.append([
            InlineKeyboardButton(f"{has_link} {v['title']}", callback_data=f"setlink_select:{v['id']}")
        ])
    buttons.append([InlineKeyboardButton("❌ ပယ်ဖျက်ပြီ", callback_data="setlink_cancel")])
    return InlineKeyboardMarkup(buttons)
def set_video_channel_id_keyboard(videos: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """List of all videos for admin setchannelid selection."""
    buttons = []
    for v in videos:
        has_id = "🔗" if v.get("channel_id") else "❌"
        buttons.append([
            InlineKeyboardButton(f"{has_id} {v['title']}", callback_data=f"setchannelid_select:{v['id']}")
        ])
    buttons.append([InlineKeyboardButton("❌ ပယ်ဖျက်မည်", callback_data="setchannelid_cancel")])
    return InlineKeyboardMarkup(buttons)
