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
from utils.update_dispatcher import UpdateDispatcher

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Build PTB application (singleton)
ptb_app = build_application()
dispatcher = UpdateDispatcher(
    app=ptb_app,
    workers=settings.UPDATE_WORKERS,
    queue_size=settings.UPDATE_QUEUE_SIZE,
)


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
    await dispatcher.start()
    yield
    await dispatcher.stop()
    session_manager = ptb_app.bot_data.get("session_manager")
    if session_manager and hasattr(session_manager, "close"):
        await session_manager.close()
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
        if not dispatcher.enqueue_raw(body):
            logger.warning("Update queue is full; rejecting update for retry")
            return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
    return Response(status_code=status.HTTP_200_OK)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=False)
