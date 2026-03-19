import json
import os
from pathlib import Path

# Provide a default message in case the file doesn't exist
DEFAULT_BUNDLE_TEXT = (
    "၁၅ပုဒ်မှာက\n"
    "1. လင်တန်းနဲ့ သခင်လေးယွဲ့တို\n"
    "2. စစ်သူကြီးကတော်က ကွာရှင်းချင်နေတယ်\n"
    "\n\n"
    "ဒါလေးတွေ စဆုံးပြီးထားပါတယ်\n"
    "15ပုဒ်ပြည့်တဲ့ထိ ဆက်တင်မှာပါ"
)

BUNDLE_FILE = Path(__file__).parent / "bundle_info.json"

def get_bundle_info() -> str:
    if not BUNDLE_FILE.exists():
        return DEFAULT_BUNDLE_TEXT
    try:
        with open(BUNDLE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("bundle_text", DEFAULT_BUNDLE_TEXT)
    except Exception:
        return DEFAULT_BUNDLE_TEXT

def set_bundle_info(new_text: str) -> None:
    with open(BUNDLE_FILE, "w", encoding="utf-8") as f:
        json.dump({"bundle_text": new_text}, f, ensure_ascii=False)
