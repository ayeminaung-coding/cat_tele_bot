"""
data/messages.py — Myanmar-language message templates for Video Bot.
"""
from config import settings

WELCOME = (
    "မင်္ဂလာပါ! 🎬\n\n"
    "သီးသန့် ဗီဒီယိုများကို ဝယ်ယူကြည့်ရှုနိုင်ပါပြီ။\n"
    "အောက်ပါ ရွေးချယ်စရာများမှ တစ်ခုကို နှိပ်ပါ။"
)

BANNED = (
    "⛔ အကောင့်ကို ပိတ်ဆို့ထားသောကြောင့်\n"
    "ဝန်ဆောင်မှုကို ရယူ၍မရနိုင်ပါ။\n"
    "Admin ထံ ဆက်သွယ်ပါ။"
)

# ── SINGLE VIDEO FLOW ───────────────────────────────────────────────────────

SINGLE_VIDEO_HEADER = "🎬 ဝယ်ယူလိုသော ဗီဒီယိုကို ရွေးချယ်ပါ:"

def video_unavailable(title: str) -> str:
    return (
        f"⚠️ '{title}' ကို လောလောဆယ် ဝယ်ယူ၍ မရနိုင်သေးပါ။\n"
        f"အခြား ဗီဒီယိုကို ရွေးချယ်ပါ။"
    )

def single_payment_instructions(title: str, amount: int) -> str:
    return (
        f"💳 ငွေပေးချေနည်း (KBZPay)\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎬 ဗီဒီယို : {title}\n"
        f"💰 ပမာဏ  : {amount:,} ကျပ် ⚠️ (တိကျစွာ ပေးပို့ပါ)\n\n"
        f"📱 KBZPay နံပတ်  : {settings.KBZPAY_PHONE}\n"
        f"👤 အမည်  : {settings.KBZPAY_NAME}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"ငွေပေးချေပြီးပါက 📸 ငွေပေးချေမှု screenshot ကို\n"
        f"ဤ chat တွင် ပေးပို့ပါ။"
    )

# ── BUNDLE FLOW ─────────────────────────────────────────────────────────────

def bundle_payment_instructions(amount: int) -> str:
    return (
        f"💳 ငွေပေးချေနည်း (KBZPay)\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 အမျိုးအစား : ဗီဒီယို ၁၅ ကား အစုလိုက်ဝယ်မည်\n"
        f"💰 ပမာဏ  : {amount:,} ကျပ် ⚠️ (တိကျစွာ ပေးပို့ပါ)\n\n"
        f"📱 KBZPay နံပတ်  : {settings.KBZPAY_PHONE}\n"
        f"👤 အမည်  : {settings.KBZPAY_NAME}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"ငွေပေးချေပြီးပါက 📸 ငွေပေးချေမှု screenshot ကို\n"
        f"ဤ chat တွင် ပေးပို့ပါ။"
    )

# ── PAYMENT COMMON ─────────────────────────────────────────────────────────

PAYMENT_RECEIVED = (
    "✅ Screenshot လက်ခံရရှိပြီ!\n\n"
    "⏳ Admin မှ စစ်ဆေးနေဆဲဖြစ်ပါသည်။\n"
    "အတည်ပြုပြီးပါက ဗီဒီယိုများကို ဤ chat မှတဆင့် တိုက်ရိုက် ပေးပို့ပေးပါမည်။\n\n"
    "ကျေးဇူးတင်ပါသည် 🙏"
)

# ── ADMIN ACTIONS ──────────────────────────────────────────────────────────

def approval_message() -> str:
    return (
        f"🎉 ငွေပေးချေမှု အောင်မြင်ပါသည်။\n\n"
        f"Admin မှ သင်ဝယ်ယူထားသော ဗီဒီယို(များ)ကို မကြာမီ ပေးပို့ပေးပါမည်။ 🎬"
    )

REJECTION_MESSAGE = (
    "❌ ငွေပေးချေမှု ငြင်းပယ်ခြင်းခံရပါသည်။\n\n"
    "ဖြစ်နိုင်သော အကြောင်းအရာများ:\n"
    "• Screenshot မှားယွင်းနေသည်\n"
    "• ငွေပမာဏ တိကျမှုမရှိ\n"
    "• ငွေပေးချေမှု အတိအကျမတွေ့ရ\n\n"
    "ပြန်လည် ကြိုးစားလိုပါက /start ကို နှိပ်ပါ။"
)

# ── ADMIN GROUP CAPTIONS ───────────────────────────────────────────────────

def admin_caption(
    user_id: int, 
    username: str | None, 
    first_name: str, 
    order_type: str, 
    amount: int, 
    order_id: str,
    video_title: str | None = None
) -> str:
    uname = f"@{username}" if username else "မရှိ"
    
    if order_type == "single":
        item_text = f"🎬 ဗီဒီယို တစ်ကား : {video_title}"
    else:
        item_text = "📦 ဗီဒီယို ၁၅ ကား Bundle"

    return (
        f"💰 ငွေပေးချေမှု တင်ပြချက်\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 အမည်  : {first_name} ({uname})\n"
        f"🆔 User ID  : {user_id}\n"
        f"{item_text}\n"
        f"💵 ပမာဏ  : {amount:,} ကျပ်\n"
        f"🔑 Order ID  : {order_id}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⬇️ အောက်မှ ဆုံးဖြတ်ချက်ချပါ:"
    )

def admin_approved_caption(admin_name: str) -> str:
    return f"✅ **{admin_name}** မှ အတည်ပြုပြီး"

def admin_rejected_caption(admin_name: str) -> str:
    return f"❌ **{admin_name}** မှ ငြင်းပယ်ပြီး"

# ── ERRORS ────────────────────────────────────────────────────────────────

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
    "/start ကို နှိပ်ပြီး ရွေးချယ်မှုအသစ် ပြုလုပ်ပါ။"
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
