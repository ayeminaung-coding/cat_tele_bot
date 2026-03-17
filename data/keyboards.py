"""
data/keyboards.py — Inline keyboard builders.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from data.plans import PLANS


def plan_selection_keyboard() -> InlineKeyboardMarkup:
    """One button per plan, each carrying the plan id as callback data."""
    buttons = [
        [InlineKeyboardButton(
            text=f"{'✨' if p['id'] == 'life' else '📦'} {p['name']} — {p['price']:,} ကျပ်",
            callback_data=f"plan:{p['id']}",
        )]
        for p in PLANS
    ]
    return InlineKeyboardMarkup(buttons)


def admin_action_keyboard(payment_id: str) -> InlineKeyboardMarkup:
    """Approve / Reject buttons sent to admin group."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ အတည်ပြုမည်", callback_data=f"approve:{payment_id}"),
            InlineKeyboardButton("❌ ငြင်းပယ်မည်", callback_data=f"reject:{payment_id}"),
        ]
    ])


def retry_keyboard() -> InlineKeyboardMarkup:
    """Shown to user after rejection so they can restart."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 ထပ်မံ ကြိုးစားရန်", callback_data="retry")]
    ])


def view_plans_keyboard() -> InlineKeyboardMarkup:
    """Shown on /start welcome message."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 အစီအစဉ်များ ကြည့်ရန်", callback_data="retry")]
    ])
