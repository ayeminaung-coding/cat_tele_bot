"""
main.py — FastAPI entry point. Receives Telegram webhook updates.
"""
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from telegram import Update

from bot_app import build_application
from config import settings

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Build PTB application (singleton)
ptb_app = build_application()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Set webhook on startup, remove on shutdown."""
    await ptb_app.initialize()
    webhook_url = f"{settings.WEBHOOK_URL}/webhook"
    await ptb_app.bot.set_webhook(
        url=webhook_url,
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )
    logger.info(f"✅ Webhook set → {webhook_url}")
    await ptb_app.start()
    yield
    await ptb_app.stop()
    await ptb_app.bot.delete_webhook()
    await ptb_app.shutdown()
    logger.info("Bot stopped.")


app = FastAPI(title="Telegram VIP Bot", lifespan=lifespan)


@app.post("/webhook")
async def telegram_webhook(request: Request) -> Response:
    """Receive Telegram update and dispatch asynchronously."""
    try:
        body = await request.json()
        update = Update.de_json(data=body, bot=ptb_app.bot)
        await ptb_app.process_update(update)
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
    return Response(status_code=status.HTTP_200_OK)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=False)
