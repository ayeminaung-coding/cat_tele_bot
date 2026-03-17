"""
utils/unique_amount.py — Generate slightly-varied payment amounts.
Enables admins to identify which KBZPay transaction belongs to which user.
"""
import random
from data.plans import get_plan


def get_unique_amount(plan_id: str) -> int:
    """
    Returns base price ± random offset (1–5 MMK).
    Example: plan price 5000 → might return 5003 or 4998
    """
    plan = get_plan(plan_id)
    if plan is None:
        raise ValueError(f"Unknown plan_id: {plan_id}")
    base = plan["price"]
    offset = random.randint(1, 5)
    direction = random.choice([1, -1])
    return base + (direction * offset)
