"""FastAPI production server for WhatsApp AI Chatbot backend.

Features:
- Meta WhatsApp Cloud API GET verification handshake and POST payload intake.
- Decoupled asynchronous worker queue with FIFO ordering and message deduplication.
- Toggleable fallback support for Twilio and Green-API webhooks.
- Multi-worker background processing with per-user locks.
- Real-time diagnostics and session memory management endpoints.
"""

import asyncio
from datetime import datetime, timezone
import hashlib
import hmac
import logging
import sys
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
import uvicorn
from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    Header,
    Query,
    Request,
    Response,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from agent import bot_agent
from config import settings
from memory import memory_store
from whatsapp_client import get_messaging_client

# Configure structured logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s (%(threadName)s): %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("whatsapp_bot.main")

# Global async queue and per-user FIFO locks
_message_queue: Optional[asyncio.Queue] = None
_user_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
_worker_tasks: list[asyncio.Task] = []


def get_message_queue() -> asyncio.Queue:
    """Return the active asyncio.Queue bound to the running event loop."""
    global _message_queue
    if _message_queue is None:
        _message_queue = asyncio.Queue(maxsize=settings.MAX_QUEUE_SIZE)
    return _message_queue


# ----------------- Background Worker Pipeline -----------------

async def message_worker(worker_id: int):
    """Background worker taking messages from the async queue and invoking the agent."""
    logger.info("Starting message queue worker #%d", worker_id)
    messaging_client = get_messaging_client()
    queue = get_message_queue()

    while True:
        item_retrieved = False
        try:
            task_item = await queue.get()
            item_retrieved = True
            sender_id = task_item["sender_id"]
            message_id = task_item["message_id"]
            text = task_item["text"]
            media_type = task_item["media_type"]
            metadata = task_item.get("metadata", {})

            # Acquire per-user lock to enforce strict FIFO dialog order
            async with _user_locks[sender_id]:
                # Double-check deduplication inside the lock
                if await memory_store.is_message_processed(message_id):
                    logger.info("Message %s already processed. Skipping.", message_id)
                    queue.task_done()
                    item_retrieved = False
                    continue

                logger.info(
                    "[Worker %d] Processing turn for user %s (message_id: %s)",
                    worker_id,
                    sender_id,
                    message_id,
                )

                # Acknowledge receipt to user on WhatsApp
                await messaging_client.mark_message_as_read(message_id)

                # Process turn through Antigravity agent & persistent memory
                reply_text = await bot_agent.process_user_turn(
                    sender_id=sender_id,
                    user_message=text,
                    media_type=media_type,
                    metadata=metadata,
                )

                # Transmit outbound reply via active messaging client
                try:
                    await messaging_client.send_text_message(to=sender_id, text=reply_text)
                    logger.info(
                        "[Worker %d] Outbound reply dispatched to %s",
                        worker_id,
                        sender_id,
                    )
                except Exception as send_err:
                    logger.error(
                        "[Worker %d] Failed to send message to %s: %s",
                        worker_id,
                        sender_id,
                        send_err,
                    )

                # Mark message ID as processed in SQLite
                await memory_store.mark_message_processed(message_id, sender_id)

            queue.task_done()
            item_retrieved = False

        except asyncio.CancelledError:
            logger.info("Worker #%d received cancellation signal.", worker_id)
            break
        except Exception as exc:
            logger.exception("Unexpected error in worker #%d: %s", worker_id, exc)
            if item_retrieved:
                queue.task_done()


# ----------------- Application Lifespan -----------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    global _message_queue, _user_locks, _worker_tasks
    logger.info("Starting WhatsApp AI Chatbot Backend...")
    logger.info("Active Provider: %s", settings.MESSAGING_PROVIDER)
    logger.info("Antigravity Model: %s", settings.AGENT_MODEL)
    logger.info("Worker Concurrency: %d", settings.WORKER_CONCURRENCY)

    # Initialize queue and locks on current event loop
    _message_queue = asyncio.Queue(maxsize=settings.MAX_QUEUE_SIZE)
    _user_locks = defaultdict(asyncio.Lock)
    _worker_tasks = []

    # Launch background worker tasks
    for i in range(settings.WORKER_CONCURRENCY):
        task = asyncio.create_task(message_worker(worker_id=i + 1))
        _worker_tasks.append(task)

    yield

    logger.info("Shutting down WhatsApp AI Chatbot Backend...")
    # Cancel workers
    for task in _worker_tasks:
        task.cancel()
    await asyncio.gather(*_worker_tasks, return_exceptions=True)
    _worker_tasks.clear()

    # Close messaging client HTTP pools
    client = get_messaging_client()
    await client.close()
    logger.info("All background tasks and HTTP connections closed.")


app = FastAPI(
    title="WhatsApp AI Chatbot Service",
    description="Production WhatsApp microservice powered by Google Antigravity SDK & Meta Cloud API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------- Signature Verification Helper -----------------

def verify_meta_signature(payload_bytes: bytes, signature_header: Optional[str]) -> bool:
    """Validate X-Hub-Signature-256 header using configured Meta App Secret."""
    if not settings.APP_SECRET:
        # If no APP_SECRET is configured, skip validation (development mode)
        return True

    if not signature_header or not signature_header.startswith("sha256="):
        logger.warning("Missing or malformed X-Hub-Signature-256 header")
        return False

    expected_hash = signature_header.split("sha256=", 1)[1]
    mac = hmac.new(
        settings.APP_SECRET.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    )
    return hmac.compare_digest(mac.hexdigest(), expected_hash)


# ----------------- WhatsApp Webhook Endpoints -----------------

@app.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    """Meta WhatsApp Cloud API Webhook Verification Handshake.
    
    Meta sends a GET request to verify the webhook URL and token.
    Must return hub.challenge as plain text upon match.
    """
    logger.info(
        "Received Webhook verification handshake: mode=%s, token_match=%s",
        hub_mode,
        hub_verify_token == settings.VERIFY_TOKEN,
    )

    if hub_mode == "subscribe" and hub_verify_token == settings.VERIFY_TOKEN:
        logger.info("Webhook verification handshake SUCCESSFUL!")
        return PlainTextResponse(content=hub_challenge or "", status_code=status.HTTP_200_OK)

    logger.warning("Webhook verification handshake FAILED! Invalid verify token.")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Verification token mismatch or invalid hub.mode",
    )


@app.post("/webhook")
async def receive_webhook_payload(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
):
    """WhatsApp Cloud API Inbound Webhook intake.
    
    Validates Meta signature, parses incoming messages, immediately returns HTTP 200,
    and dispatches processing asynchronously.
    """
    body_bytes = await request.body()

    # 1. Validate signature if Meta App Secret is set
    if not verify_meta_signature(body_bytes, x_hub_signature_256):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid payload signature",
        )

    try:
        payload = await request.json()
    except Exception:
        # Always return 200 to Meta to avoid webhook unsubscription
        logger.error("Failed to parse incoming webhook JSON.")
        return JSONResponse(content={"status": "error", "message": "invalid JSON"}, status_code=200)

    # 2. Extract entries from Meta payload
    entries = payload.get("entry", [])
    if not entries:
        return JSONResponse(content={"status": "ignored", "reason": "no entries"}, status_code=200)

    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})
            
            # Ignore delivery / read status receipts
            if "statuses" in value and "messages" not in value:
                logger.debug("Received WhatsApp delivery status update: %s", value.get("statuses"))
                continue

            messages = value.get("messages", [])
            for msg in messages:
                message_id = msg.get("id")
                sender_id = msg.get("from")
                msg_type = msg.get("type", "text")

                if not message_id or not sender_id:
                    continue

                # Check deduplication
                if await memory_store.is_message_processed(message_id):
                    logger.info("Duplicate message %s received. Ignoring.", message_id)
                    continue

                # Extract content based on message type
                text_content = ""
                metadata: Dict[str, Any] = {"raw_type": msg_type}

                if msg_type == "text":
                    text_content = msg.get("text", {}).get("body", "")
                elif msg_type == "interactive":
                    # Interactive reply button or list selection
                    interactive = msg.get("interactive", {})
                    i_type = interactive.get("type")
                    if i_type == "button_reply":
                        text_content = interactive.get("button_reply", {}).get("title", "")
                        metadata["button_id"] = interactive.get("button_reply", {}).get("id")
                    elif i_type == "list_reply":
                        text_content = interactive.get("list_reply", {}).get("title", "")
                        metadata["list_id"] = interactive.get("list_reply", {}).get("id")
                elif msg_type == "image":
                    text_content = msg.get("image", {}).get("caption", "")
                    metadata["media_id"] = msg.get("image", {}).get("id")
                    metadata["mime_type"] = msg.get("image", {}).get("mime_type")
                elif msg_type == "audio":
                    text_content = ""
                    metadata["media_id"] = msg.get("audio", {}).get("id")
                elif msg_type == "video":
                    text_content = msg.get("video", {}).get("caption", "")
                    metadata["media_id"] = msg.get("video", {}).get("id")
                elif msg_type == "document":
                    text_content = msg.get("document", {}).get("caption", "")
                    metadata["filename"] = msg.get("document", {}).get("filename")
                    metadata["media_id"] = msg.get("document", {}).get("id")
                else:
                    text_content = f"[{msg_type} message received]"

                # Enqueue message for asynchronous agent processing
                queue_item = {
                    "sender_id": sender_id,
                    "message_id": message_id,
                    "text": text_content,
                    "media_type": msg_type,
                    "metadata": metadata,
                }

                try:
                    q = get_message_queue()
                    q.put_nowait(queue_item)
                    logger.info(
                        "Enqueued message %s from %s (type: %s, queue size: %d)",
                        message_id,
                        sender_id,
                        msg_type,
                        q.qsize(),
                    )
                except asyncio.QueueFull:
                    logger.error("Message queue is FULL! Dropping message %s", message_id)

    # Return 200 immediately to Meta Graph API
    return JSONResponse(content={"status": "ok"}, status_code=200)


# ----------------- Fallback Inbound Webhooks -----------------

@app.post("/webhook/twilio")
async def receive_twilio_webhook(request: Request):
    """Inbound webhook receiver for Twilio WhatsApp integration."""
    form_data = await request.form()
    from_user = form_data.get("From", "").replace("whatsapp:", "")
    body = form_data.get("Body", "")
    message_sid = form_data.get("MessageSid", "")
    num_media = int(form_data.get("NumMedia", "0"))

    if not from_user or not message_sid:
        return PlainTextResponse("<Response></Response>", media_type="application/xml")

    media_type = "image" if num_media > 0 else "text"
    queue_item = {
        "sender_id": from_user,
        "message_id": message_sid,
        "text": body,
        "media_type": media_type,
        "metadata": {"provider": "twilio"},
    }
    await get_message_queue().put(queue_item)
    return PlainTextResponse("<Response></Response>", media_type="application/xml")


@app.post("/webhook/green-api")
async def receive_green_api_webhook(request: Request):
    """Inbound webhook receiver for Green-API WhatsApp integration."""
    payload = await request.json()
    type_webhook = payload.get("typeWebhook")

    if type_webhook == "incomingMessageReceived":
        msg_data = payload.get("messageData", {})
        sender_data = payload.get("senderData", {})
        chat_id = sender_data.get("chatId", "").replace("@c.us", "")
        message_id = payload.get("idMessage", "")

        text = ""
        type_msg = msg_data.get("typeMessage")
        if type_msg == "textMessage":
            text = msg_data.get("textMessageData", {}).get("textMessage", "")
        elif type_msg == "imageMessage":
            text = msg_data.get("fileMessageData", {}).get("caption", "")

        if chat_id and message_id:
            await get_message_queue().put(
                {
                    "sender_id": chat_id,
                    "message_id": message_id,
                    "text": text,
                    "media_type": "text" if type_msg == "textMessage" else "image",
                    "metadata": {"provider": "green_api"},
                }
            )

    return JSONResponse(content={"status": "ok"})


# ----------------- Health & Telemetry Endpoints -----------------

@app.get("/")
async def root():
    """Service root endpoint."""
    return {
        "service": "WhatsApp AI Chatbot",
        "status": "operational",
        "docs": "/docs",
        "provider": settings.MESSAGING_PROVIDER,
        "model": settings.AGENT_MODEL,
    }


@app.get("/health")
async def health_check():
    """System health check and metrics."""
    stats = await memory_store.get_stats()
    q = get_message_queue()
    return {
        "status": "healthy",
        "queue": {
            "pending_messages": q.qsize(),
            "max_queue_size": settings.MAX_QUEUE_SIZE,
            "active_workers": len(_worker_tasks),
        },
        "storage": stats,
        "settings": {
            "messaging_provider": settings.MESSAGING_PROVIDER,
            "agent_model": settings.AGENT_MODEL,
            "gemini_configured": bool(settings.GEMINI_API_KEY or settings.ANTIGRAVITY_API_KEY),
            "antigravity_configured": bool(settings.ANTIGRAVITY_API_KEY or settings.GEMINI_API_KEY),
            "whatsapp_configured": bool(settings.WHATSAPP_TOKEN and settings.PHONE_NUMBER_ID),
        },
    }


@app.get("/history/{sender_id}")
async def get_user_history(sender_id: str, limit: int = 20):
    """Retrieve chat history for a specific phone number."""
    history = await memory_store.get_history(sender_id, limit=limit)
    return {"sender_id": sender_id, "turns_count": len(history), "history": history}


@app.post("/history/{sender_id}/clear")
async def clear_user_history(sender_id: str):
    """Clear conversation history for a specific phone number."""
    deleted = await memory_store.clear_history(sender_id)
    return {"status": "cleared", "sender_id": sender_id, "deleted_turns": deleted}


# ----------------- Web Frontend Direct Chat Endpoints -----------------

class DirectChatMessage(BaseModel):
    sender_id: str = Field(..., description="Phone number or unique sender identifier")
    message: str = Field(..., description="User message text")
    media_type: str = Field("text", description="Media type (default: text)")


@app.get("/conversations")
async def list_conversations():
    """Retrieve all distinct conversations with their latest message preview and count."""
    conversations = await memory_store.get_conversations()
    return {"conversations": conversations, "count": len(conversations)}


@app.post("/chat")
async def send_direct_chat_message(payload: DirectChatMessage):
    """Direct chat endpoint for the web frontend.

    Processes turn through the Antigravity agent & persistent SQLite memory store,
    returning the AI assistant reply synchronously.
    """
    sender_id = payload.sender_id.strip()
    user_message = payload.message.strip()

    if not sender_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sender_id cannot be empty",
        )
    if not user_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message cannot be empty",
        )

    # Acquire per-user lock to enforce strict FIFO dialog order
    async with _user_locks[sender_id]:
        reply_text = await bot_agent.process_user_turn(
            sender_id=sender_id,
            user_message=user_message,
            media_type=payload.media_type,
            metadata={"source": "web_frontend"},
        )

    return {
        "sender_id": sender_id,
        "message": user_message,
        "reply": reply_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ----------------- CLI Entry Point -----------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
