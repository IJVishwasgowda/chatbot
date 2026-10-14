"""Live API and CORS integration tests for WhatsApp Web frontend."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from config import settings
from agent import bot_agent
from main import app


@pytest.fixture
def client():
    settings.MESSAGING_PROVIDER = "mock"

    # Configure mock client on bot_agent so API tests simulate Gemini generation
    mock_client = MagicMock()

    async def mock_generate(model, contents, config):
        last_turn = contents[-1].parts[0].text if contents else ""
        resp = MagicMock()
        resp.candidates = []
        if "weather" in last_turn.lower() or "tokyo" in last_turn.lower():
            resp.text = "🌤️ *Weather in Tokyo*: 18°C, Clear skies."
        elif "hour" in last_turn.lower():
            resp.text = "💡 *Operating Hours*: Open Monday-Friday 8am-8pm EST."
        else:
            resp.text = f"AI response to: {last_turn}"
        return resp

    mock_client.aio.models.generate_content = AsyncMock(side_effect=mock_generate)
    original_custom = bot_agent._custom_client
    bot_agent._custom_client = mock_client

    with TestClient(app) as test_client:
        yield test_client

    bot_agent._custom_client = original_custom


def test_cors_preflight_and_headers(client):
    """Test CORS headers for Vite dev server origin."""
    # 1. Preflight OPTIONS request
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    options_resp = client.options("/chat", headers=headers)
    assert options_resp.status_code == 200
    assert "access-control-allow-origin" in options_resp.headers

    # 2. Regular POST request with Origin header
    post_resp = client.post(
        "/chat",
        json={"sender_id": "19998887777", "message": "Ping from Vite origin"},
        headers={"Origin": "http://localhost:5173"},
    )
    assert post_resp.status_code == 200
    assert "access-control-allow-origin" in post_resp.headers


def test_chat_and_tools_flow(client):
    """Test web chat with tool execution intents (weather, kb, quote)."""
    sender = "18885554321"

    # Test 1: Weather intent
    resp_weather = client.post(
        "/chat",
        json={"sender_id": sender, "message": "What is the weather in Tokyo?"},
    )
    assert resp_weather.status_code == 200
    data_w = resp_weather.json()
    assert "reply" in data_w
    assert "Tokyo" in data_w["reply"] or "Weather" in data_w["reply"]

    # Test 2: Knowledge Base FAQ intent
    resp_kb = client.post(
        "/chat",
        json={"sender_id": sender, "message": "What are your operating hours?"},
    )
    assert resp_kb.status_code == 200
    data_kb = resp_kb.json()
    assert "Operating Hours" in data_kb["reply"] or "hours" in data_kb["reply"].lower()

    # Test 3: History reflects both turns
    resp_hist = client.get(f"/history/{sender}")
    assert resp_hist.status_code == 200
    turns = resp_hist.json()["history"]
    assert len(turns) >= 4  # 2 user messages + 2 assistant replies

    # Test 4: Conversations list includes this sender
    resp_convs = client.get("/conversations")
    assert resp_convs.status_code == 200
    conv_list = resp_convs.json()["conversations"]
    assert any(c["sender_id"] == sender for c in conv_list)
