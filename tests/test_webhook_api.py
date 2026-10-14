"""Integration tests for FastAPI Webhook endpoints using TestClient."""

import hashlib
import hmac
import json
import pytest
from fastapi.testclient import TestClient

from config import settings
from main import app
from test_webhook import build_whatsapp_text_payload, build_whatsapp_media_payload


from unittest.mock import AsyncMock, MagicMock
from agent import bot_agent


@pytest.fixture
def client():
    """Create a synchronous FastAPI test client with mock messaging provider."""
    settings.MESSAGING_PROVIDER = "mock"

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "Hello! I am your AI assistant."
    mock_resp.candidates = []
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_resp)

    original_custom = bot_agent._custom_client
    bot_agent._custom_client = mock_client

    with TestClient(app) as test_client:
        yield test_client

    bot_agent._custom_client = original_custom


def test_webhook_get_verification_success(client):
    """Test Meta webhook verification handshake with correct token."""
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": settings.VERIFY_TOKEN,
        "hub.challenge": "9876543210",
    }
    response = client.get("/webhook", params=params)
    assert response.status_code == 200
    assert response.text == "9876543210"


def test_webhook_get_verification_failure(client):
    """Test Meta webhook verification handshake with incorrect token."""
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "wrong_secret_token",
        "hub.challenge": "9876543210",
    }
    response = client.get("/webhook", params=params)
    assert response.status_code == 403


def test_webhook_post_text_message(client):
    """Test incoming text message intake."""
    payload = build_whatsapp_text_payload(
        from_number="15559876543",
        text_body="Hello AI!",
        message_id="wamid.test_post_001",
    )
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_post_delivery_status_ignored(client):
    """Test that delivery status receipts are acknowledged with 200 without error."""
    status_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "100000000000001",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550009999",
                                "phone_number_id": "1234567890",
                            },
                            "statuses": [
                                {
                                    "id": "wamid.out_123",
                                    "status": "delivered",
                                    "timestamp": "1728900000",
                                    "recipient_id": "15559876543",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }
    response = client.post("/webhook", json=status_payload)
    assert response.status_code == 200


def test_webhook_hmac_signature_validation(client):
    """Test HMAC SHA256 validation when APP_SECRET is configured."""
    original_secret = settings.APP_SECRET
    try:
        settings.APP_SECRET = "super_meta_secret_key"
        payload_dict = build_whatsapp_text_payload(
            from_number="15559876543",
            text_body="Secure message",
            message_id="wamid.test_post_secure_01",
        )
        raw_body = json.dumps(payload_dict).encode("utf-8")

        # 1. Invalid signature should fail
        bad_headers = {"X-Hub-Signature-256": "sha256=invalid_hash"}
        res_bad = client.post("/webhook", content=raw_body, headers=bad_headers)
        assert res_bad.status_code == 403

        # 2. Valid signature should succeed
        mac = hmac.new(
            settings.APP_SECRET.encode("utf-8"), msg=raw_body, digestmod=hashlib.sha256
        )
        good_headers = {
            "X-Hub-Signature-256": f"sha256={mac.hexdigest()}",
            "Content-Type": "application/json",
        }
        res_good = client.post("/webhook", content=raw_body, headers=good_headers)
        assert res_good.status_code == 200

    finally:
        settings.APP_SECRET = original_secret


def test_health_and_history_endpoints(client):
    """Test health check and history inspection endpoints."""
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    data = health_resp.json()
    assert data["status"] == "healthy"
    assert "queue" in data
    assert "storage" in data

    # Check history endpoint
    hist_resp = client.get("/history/15559876543")
    assert hist_resp.status_code == 200
    assert "turns_count" in hist_resp.json()

    # Clear history endpoint
    clear_resp = client.post("/history/15559876543/clear")
    assert clear_resp.status_code == 200
    assert clear_resp.json()["status"] == "cleared"


def test_direct_chat_and_conversations_endpoints(client):
    """Test web direct chat endpoint and conversation list retrieval."""
    test_sender = "15551234567"

    # 1. Send direct chat message
    chat_payload = {
        "sender_id": test_sender,
        "message": "Hello from web frontend!",
        "media_type": "text",
    }
    chat_resp = client.post("/chat", json=chat_payload)
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert chat_data["sender_id"] == test_sender
    assert chat_data["message"] == "Hello from web frontend!"
    assert "reply" in chat_data
    assert len(chat_data["reply"]) > 0

    # 2. Check conversation listing includes test_sender
    conv_resp = client.get("/conversations")
    assert conv_resp.status_code == 200
    conv_data = conv_resp.json()
    assert "conversations" in conv_data
    assert any(c["sender_id"] == test_sender for c in conv_data["conversations"])

    # 3. Check history has the recorded turns
    hist_resp = client.get(f"/history/{test_sender}")
    assert hist_resp.status_code == 200
    history = hist_resp.json()["history"]
    assert len(history) >= 2  # user message and assistant reply

    # 4. Validation error on empty message
    bad_resp = client.post("/chat", json={"sender_id": test_sender, "message": "   "})
    assert bad_resp.status_code == 400
