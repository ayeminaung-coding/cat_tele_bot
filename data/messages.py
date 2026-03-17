"""
data/messages.py — All bot messages in Myanmar language.
"""
from config import settings


# ── Welcome ────────────────────────────────────────────────────────────────

WELCOME = (
    "မင်္ဂလာပါ! 🌟\n\n"
    "VIP အသင်းဝင် ဝန်ဆောင်မှုသို့ ကြိုဆိုပါသည်။\n"
    "အောက်ပါအစီအစဉ်များကို ရွေးချယ်ပြီး\n"
    "KBZPay ဖြင့် ငွေပေးချေနိုင်ပါသည်။ 💳"
)

ALREADY_ACTIVE = (
    "✅ သင်သည် ရှိပြီးသား VIP အသင်းဝင် ဖြစ်ပါသည်။\n"
    "ဆောင်ရွက်ချက်ကို ဆက်လက်ခံစားနိုင်ပါသည်။"
)

BANNED = (
    "⛔ အကောင့်ကို ပိတ်ဆို့ထားသောကြောင့်\n"
    "ဝန်ဆောင်မှုကို ရယူ၍မရနိုင်ပါ။\n"
    "Admin ထံ ဆက်သွယ်ပါ။"
)


# ── Plans ──────────────────────────────────────────────────────────────────

def plan_list_header() -> str:
    return "📋 VIP အစီအစဉ်များ\n\nကြိုက်နှစ်သက်သော အစီအစဉ်တစ်ခုကို ရွေးချယ်ပါ:"


def plan_item(plan: dict) -> str:
    return (
        f"🏷 {plan['name']}  —  {plan['price']:,} ကျပ်\n"
        f"   ⏳ {plan['duration']}"
    )


# ── Payment Instructions ───────────────────────────────────────────────────

def payment_instructions(plan: dict, amount: int) -> str:
    return (
        f"💳 ငွေပေးချေနည်း (KBZPay)\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 အစီအစဉ်  : {plan['name']} ({plan['duration']})\n"
        f"💰 ပေးချေရမည့် ပမာဏ  : {amount:,} ကျပ် ⚠️ (တိကျစွာ ပေးပို့ပါ)\n\n"
        f"📱 KBZPay နံပတ်  : {settings.KBZPAY_PHONE}\n"
        f"👤 အမည်  : {settings.KBZPAY_NAME}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"ငွေပေးချေပြီးပါက 📸 ငွေပေးချေမှု screenshot ကို\n"
        f"ဤ chat တွင် ပေးပို့ပါ။"
    )


# ── Payment Received ───────────────────────────────────────────────────────

PAYMENT_RECEIVED = (
    "✅ Screenshot လက်ခံရရှိပြီ!\n\n"
    "⏳ Admin မှ စစ်ဆေးနေဆဲဖြစ်ပါသည်။\n"
    "မကြာမီ အတည်ပြုချက် ပေးပို့ပါမည်။\n\n"
    "ကျေးဇူးတင်ပါသည် 🙏"
)


# ── Approval ───────────────────────────────────────────────────────────────

def approval_message(invite_link: str, plan: dict) -> str:
    return (
        f"🎉 ဂုဏ်ယူပါသည်! VIP အသင်းဝင်မှု အတည်ပြုပြီးပါပြီ!\n\n"
        f"📦 အစီအစဉ် : {plan['name']} ({plan['duration']})\n\n"
        f"🔗 VIP ဂုပ်ချိပ် link:\n{invite_link}\n\n"
        f"⚠️ ဤ link သည် တစ်ကြိမ်သာ သုံးနိုင်ပါသည်။\n"
        f"မိတ်ဆွေများနှင့် မမျှဝေပါနှင့်။\n\n"
        f"VIP ကို ကြိုဆိုပါသည်! 🌟"
    )


REJECTION_MESSAGE = (
    "❌ ငွေပေးချေမှု ငြင်းပယ်ခြင်းခံရပါသည်။\n\n"
    "ဖြစ်နိုင်သော အကြောင်းအရာများ:\n"
    "• Screenshot မှားယွင်းနေသည်\n"
    "• ငွေပမာဏ တိကျမှုမရှိ\n"
    "• ငွေပေးချေမှု အတိအကျမတွေ့ရ\n\n"
    "ပြန်လည် ကြိုးစားလိုပါက အောက်ပါ ခလုတ်ကို နှိပ်ပါ။"
)


# ── Errors ────────────────────────────────────────────────────────────────

INVALID_FILE_TYPE = (
    "⚠️ ဓာတ်ပုံသာ ပေးပို့ပါ။\n"
    "လက်ခံသောဖော်မတ်: JPG, PNG\n\n"
    "PDF, video သို့မဟုတ် အခြား ဖိုင်များ မလက်ခံပါ။"
)

FILE_TOO_LARGE = (
    "⚠️ ဖိုင်အရွယ်အစား ကြီးလွန်းသည်။\n"
    "အများဆုံး 5MB သာ ပေးပို့နိုင်ပါသည်။\n\n"
    "ဖိုင်ကို သေးငယ်အောင် ပြုပြင်ပြီး ထပ်မံ ပေးပို့ပါ။"
)

NOT_IN_PAYMENT_FLOW = (
    "ℹ️ ငွေပေးချေမှု flow မဖွင့်ရသေးပါ။\n"
    "/start ကို နှိပ်ပြီး အစီအစဉ် ရွေးချယ်ပါ။"
)

GENERIC_ERROR = (
    "😔 တစ်ခုခု မှားယွင်းသွားပါသည်။\n"
    "ခဏစောင့်ပြီး ထပ်မံ ကြိုးစားကြည့်ပါ။\n"
    "ပြဿနာ ဆက်ရှိနေပါက Admin ထံ ဆက်သွယ်ပါ။"
)

UPLOAD_FAILED = (
    "⚠️ Screenshot တင်သွင်း မအောင်မြင်ပါ။\n"
    "ကျေးဇူးပြု၍ ထပ်မံ ကြိုးစားပါ။"
)


# ── Admin group captions ───────────────────────────────────────────────────

def admin_caption(user_id: int, username: str | None, first_name: str, plan: dict, amount: int, payment_id: str) -> str:
    uname = f"@{username}" if username else "မရှိ"
    return (
        f"💰 ငွေပေးချေမှု တင်ပြချက်\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 အမည်  : {first_name} ({uname})\n"
        f"🆔 User ID  : {user_id}\n"
        f"📦 အစီအစဉ်  : {plan['name']} ({plan['duration']})\n"
        f"💵 ပမာဏ  : {amount:,} ကျပ်\n"
        f"🔑 Payment ID  : {payment_id}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⬇️ အောက်မှ ဆုံးဖြတ်ချက်ချပါ:"
    )


def admin_approved_caption(admin_name: str) -> str:
    return f"✅ **{admin_name}** မှ အတည်ပြုပြီး"


def admin_rejected_caption(admin_name: str) -> str:
    return f"❌ **{admin_name}** မှ ငြင်းပယ်ပြီး"
