"""
utils/alerts.py — Admin alert delivery utility.
"""
import logging

from telegram.ext import ContextTypes

from config import settings

logger = logging.getLogger(__name__)


async def send_admin_alert(
    context: ContextTypes.DEFAULT_TYPE,
    title: str,
    detail: str,
    severity: str = "critical",
) -> None:
    """Send an alert to admin group, with admin-DM fallback."""
    icon = "🚨" if severity == "critical" else "⚠️"
    text = (
        f"{icon} <b>{title}</b>\n"
        f"Severity: <code>{severity}</code>\n\n"
        f"<pre>{detail[:1800]}</pre>"
    )

    try:
        await context.bot.send_message(
            chat_id=settings.ADMIN_GROUP_ID,
            text=text,
            parse_mode="HTML",
            disable_notification=(severity != "critical"),
        )
        return
    except Exception as exc:
        logger.error("Failed to send alert to admin group: %s", exc)

    for admin_id in settings.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=text,
                parse_mode="HTML",
                disable_notification=(severity != "critical"),
            )
        except Exception as exc:
            logger.error("Failed to send alert to admin %s: %s", admin_id, exc)
