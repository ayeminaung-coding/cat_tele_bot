"""
data/plans.py — VIP plan definitions.
"""
from typing import TypedDict


class Plan(TypedDict):
    id: str
    name: str
    price: int
    duration: str
    description: str


PLANS: list[Plan] = [
    {
        "id": "1m",
        "name": "တစ်လ",
        "price": 5000,
        "duration": "၃၀ ရက်",
        "description": "VIP အသင်းဝင် တစ်လ",
    },
    {
        "id": "3m",
        "name": "သုံးလ",
        "price": 12000,
        "duration": "၉၀ ရက်",
        "description": "VIP အသင်းဝင် သုံးလ (သက်သာသောဈေးနှုန်း)",
    },
    {
        "id": "life",
        "name": "တစ်သက်တာ",
        "price": 30000,
        "duration": "တစ်သက်တာ",
        "description": "တစ်ကြိမ်ပေး၊ တစ်သက်တာသုံး",
    },
]

PLAN_MAP: dict[str, Plan] = {p["id"]: p for p in PLANS}


def get_plan(plan_id: str) -> Plan | None:
    return PLAN_MAP.get(plan_id)
