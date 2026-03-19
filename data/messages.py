"""
data/messages.py — Myanmar-language message templates for Video Bot.
"""
from config import settings

WELCOME = (
    "မင်္ဂလာပါ! White Cat Channelမှကြိုဆိုပါတယ်! 🎬\n\n"
    "VIP တရုတ်animation ဇာတ်ကားများကို ဝယ်ယူကြည့်ရှုနိုင်ပါပြီ။\n"
    "အောက်ပါ ရွေးချယ်စရာများမှ တစ်ခုကို နှိပ်ပါ။"
)

BANNED = (
    "⛔ အကောင့်ကို ပိတ်ဆို့ထားသောကြောင့်\n"
    "ဝန်ဆောင်မှုကို ရယူ၍မရနိုင်ပါ။\n"
    "Admin ထံ ဆက်သွယ်ပါ။ @whitecatadmin"
)

# ── SINGLE VIDEO FLOW ───────────────────────────────────────────────────────

SINGLE_VIDEO_HEADER = "🎬 ဝယ်ယူလိုသော ဇာတ်ကားကို ရွေးချယ်ပါ:"

def video_unavailable(title: str) -> str:
    return (
        f"⚠️ '{title}' ကို လောလောဆယ် ဝယ်ယူ၍ မရနိုင်သေးပါ။\n"
        f"အခြား ဇာတ်ကားကို ရွေးချယ်ပါ။"
    )

def single_payment_instructions(title: str, amount: int) -> str:
    return (
        f"💳 ငွေပေးချေနည်း (KBZPay / Wave Pay နှစ်ခုလုံး အောက်က နံပါတ်ကိုလွှဲပေးပါနော်..)\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎬 ဇာတ်ကား : {title}\n"
        f"💰 စျေးနှုန်း  : {amount:,} ကျပ်\n\n"
        f"📱 လွှဲရမည့် နံပါတ်  : {settings.KBZPAY_PHONE}\n"
        f"👤 အမည်  : {settings.KBZPAY_NAME}\n"
        f"📋 Note   : Noteမှာ drama လို့ရေးပေးနော်❤️\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"ငွေပေးချေပြီးပါက 📸 ငွေပေးချေမှု screenshot ကို "
        f"ဒီ chat ထဲမှာ ပို့ပေးပါနော် ❤️‍🔥.."
    )

from data.bundle_manager import get_bundle_info

# ── BUNDLE FLOW ─────────────────────────────────────────────────────────────

def bundle_payment_instructions(amount: int) -> str:
    return (
        f"💳 ငွေပေးချေနည်း \n (KBZPay/Wave Pay နှစ်ခုလုံး အောက်က နံပါတ်ကို လွှဲပေးပါနော်..)\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 အမျိုးအစား : ၁၅ ပုဒ် VIP ဝင်မည်\n"
        f"💰 စျေးနှုန်း  : {amount:,} ကျပ်\n\n"
        f"📱 လွှဲရမည့် နံပါတ်  : {settings.KBZPAY_PHONE}\n"
        f"👤 အမည်  : {settings.KBZPAY_NAME}\n"
        f"📋 Note   : Noteမှာ drama လို့ရေးပေးနော်❤️\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"ငွေပေးချေပြီးပါက 📸 ငွေပေးချေမှု screenshot ကို "
        f"ဒီ chat ထဲမှာ ပို့ပေးပါနော် ❤️‍🔥.."
    )

# ── PAYMENT COMMON ─────────────────────────────────────────────────────────

PAYMENT_RECEIVED = (
    "✅ Screenshot လက်ခံရရှိပါပြီ!\n\n"
    "⏳ Adminမှ စစ်ဆေးနေဆဲမို့ နာရီဝက်၊ တစ်နာရီလောက် စောင့်ပေးပါနော်..\n"
    "အတည်ပြုပြီးရင် Channel Linkကို ဒီChatမှာပဲ တိုက်ရိုက်ပေးပို့ပေးပါမယ်နော်\n\n"
    "ကျေးဇူးတင်ပါတယ်ရှင့် 🙏"
)

# ── ADMIN ACTIONS ──────────────────────────────────────────────────────────

def approval_message() -> str:
    return (
        f"🎉 ငွေပေးချေမှု အောင်မြင်ပါသည်။\n\n"
        f"Admin မှ သင်ဝယ်ယူထားသော VIP channelကို တစ်နာရီအတွင်း ပေးပို့ပေးပါမယ်နော် 🎬"
    )

def bundle_approval_message(invite_link: str) -> str:
    return (
        f"🎉 ငွေပေးချေမှု အောင်မြင်ပါသည်။\n\n"
        f"အောက်ပါ လင့်မှတဆင့် VIP Channel သို့ ဝင်ရောက်နိုင်ပါပြီ👇\n"
        f"{invite_link}\n\n"
        f"⚠️ မှတ်ချက်။ ။ အပေါ်က လင့်သည် ၁ ယောက်သာ ဝင်ခွင့်ရှိပြီး၊ ဝင်ပြီးသည်နှင့် အလိုအလျောက် ပျက်သွားမည်ဖြစ်သည်"
    )

REJECTION_MESSAGE = (
    "❌ ငွေပေးချေမှု ငြင်းပယ်ခြင်းခံရပါသည်။\n\n"
    "ဖြစ်နိုင်သော အကြောင်းအရာများ:\n"
    "• Screenshot မှားယွင်းနေသည်\n"
    "• ငွေပမာဏ တိကျမှုမရှိ\n"
    "• ငွေပေးချေမှု အတိအကျမတွေ့ရ\n\n"
    "ပြန်လည် ကြိုးစားလိုပါက အောက်ပါ Button ကို နှိပ်ပါ။"
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
        item_text = f"🎬 ဇာတ်ကား တစ်ကား : {video_title}"
    else:
        item_text = "📦 ဇာတ်ကား ၁၅ ကား Bundle"

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



NOT_IN_PAYMENT_FLOW = (
    "ℹ️ ငွေပေးချေမှု မစတင်ရသေးပါ။\n"
    "/start ကို နှိပ်ပြီး ရွေးချယ်မှုအသစ် ပြုလုပ်ပါ။"
)

GENERIC_ERROR = (
    "😔 တစ်ခုခု မှားယွင်းသွားပါသည်။\n"
    "ခဏစောင့်ပြီး ထပ်မံ ကြိုးစားကြည့်ပါ။\n"
    "ပြဿနာ ဆက်ရှိနေပါက Admin ထံ ဆက်သွယ်ပါ။ \n ဆက်သွယ်ရန် - @whitecatadmin"
)

UPLOAD_FAILED = (
    "⚠️ Screenshot တင်သွင်း မအောင်မြင်ပါ။\n"
    "ကျေးဇူးပြု၍ ထပ်မံ ကြိုးစားပါ။"
)

# ── ADMIN VIDEO MANAGEMENT ─────────────────────────────────────────────────

ADMIN_ONLY = "⛔ ဤ command ကို Admin သာ သုံးနိုင်သည်။"

ASK_VIDEO_TITLE = (
    "🎬 ထည့်သွင်းမည့် ဇာတ်ကားအမည် ရိုက်ထည့်ပါ:\n"
    "(ပယ်ဖျက်ရန် /cancel )"
)

ASK_VIDEO_PRICE = (
    "💰 ဈေးနှုန်း ရိုက်ထည့်ပါ (ကျပ်):\n"
    "ဥပမာ — 1000"
)

INVALID_PRICE = "⚠️ ကျပ် ပမာဏ ဂဏန်းဖြင့်သာ ရိုက်ထည့်ပါ။ ဥပမာ — 1000"

ADD_VIDEO_CANCELLED = "❌ ဇာတ်ကားထည့်ခြင်း ပယ်ဖျက်ပြီ။"


def add_video_success(title: str, price: int) -> str:
    return (
        f"✅ ဇာတ်ကား ထည့်သွင်းပြီ!\n\n"
        f"🎬 အမည် : {title}\n"
        f"💰 ဈေးနှုန်း : {price:,} ကျပ်"
    )


ASK_DELETE_VIDEO = "🗑 ဖျက်မည့် ဇာတ်ကားကို ရွေးချယ်ပါ:"

NO_VIDEOS_TO_DELETE = "📭 ဇာတ်ကား မရှိသေးပါ။"


def delete_confirm_prompt(title: str) -> str:
    return (
        f"⚠️ '{title}' ကို ဖျက်မည်။\n"
        f"ဤဇာတ်ကားနှင့် ချိတ်ဆက်ထားသော Orders များ ကျန်ရှိနိုင်သည်။\n\n"
        f"သေချာသလား?"
    )


def delete_video_success(title: str) -> str:
    return f"✅ '{title}' ဖျက်ပြီ!"


DELETE_VIDEO_CANCELLED = "❌ ဖျက်ခြင်း ပယ်ဖျက်ပြီ။"

# ── SETVIDEOLINK FLOW ───────────────────────────────────────────────────────

ASK_SETLINK_VIDEO = "🔗 Link ထည့်ခှက်မည့် ဇာတ်ကားကို ရွေးချယ်ပါ:"

ASK_SETLINK_URL = (
    "📨 Channel / Video လင့်ခ်ကို ရိုက်ထည့်ပါ:\n"
    "(ဥပမာ: https://t.me/+xxxx )\n\n"
    "(လုပ်ငန်းစဥ်ကို ရပ်တန့်ရန် /cancel ကိုနှိပ်ပါ။)"
)


def setlink_success(title: str) -> str:
    return f"✅ '{title}' အတွက် Link သိမ်ပြီ!"


SETLINK_CANCELLED = "❌ Link သတ်သွင်းခြင်း ပယ်ဖျက်ပြီ။"


# ── SINGLE VIDEO APPROVAL WITH LINK ────────────────────────────────────────

def single_approval_with_link(title: str, link: str) -> str:
    return (
        f"🎉 ငွေပေးချေမှု အောင်မြင်ပါတယ်..\n\n"
        f"🎬 ဇာတ်ကားအမည် : {title}\n\n"
        f"🔗 အောက်ကြည့်အတွက် လင့်ခ်ကို အောက်ပါ:\n"
        f"{link}\n\n"
        f"⚠️ မှတ်ချက် — ‌admi‌n မှ တစ်နာရီအတွင်း approve လုပ်ပေးပါမယ်နော်..\n "
        f"ခန လောက် စောင့်ပေးပါနော် .. \n ကျေးဇူးတင်ပါတယ်ရှင့် 🙏"
    )
