"""Unit tests for WhatsApp AI Agent and tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from agent import (
    WhatsAppAgent,
    get_current_weather,
    lookup_knowledge_base,
    calculate_service_quote,
    SYSTEM_INSTRUCTIONS,
)
from memory import memory_store


def test_weather_tool():
    """Verify live weather tool output."""
    res = get_current_weather("San Francisco")
    assert res["location"] == "San Francisco"
    assert "temperature" in res
    assert "condition" in res
    assert "humidity" in res


def test_knowledge_base_tool():
    """Verify knowledge base lookup tool."""
    res_hours = lookup_knowledge_base("What are your business hours?")
    assert "Operating Hours" in res_hours["topic"]

    res_refund = lookup_knowledge_base("How do I get a refund or return?")
    assert "Refund & Return Policy" in res_refund["topic"]

    res_pricing = lookup_knowledge_base("What subscription plans are available?")
    assert "Available Plans" in res_pricing["topic"]


def test_quote_calculator_tool():
    """Verify dynamic service quote tool."""
    res_starter = calculate_service_quote("starter", 3)
    assert res_starter["tier"] == "Starter"
    assert res_starter["users"] == 3
    assert "$18.00/mo" in res_starter["estimated_monthly_total"]

    res_pro = calculate_service_quote("professional", 10)
    assert res_pro["tier"] == "Professional"
    assert "$120.00/mo" in res_pro["estimated_monthly_total"]


def test_special_media_handling():
    """Verify immediate friendly responses for non-text media types."""
    agent = WhatsAppAgent()

    # Voice Note
    audio_reply = agent._handle_special_media("audio", "")
    assert audio_reply is not None
    assert "voice message" in audio_reply.lower()

    # Image without caption
    image_no_caption = agent._handle_special_media("image", "")
    assert image_no_caption is not None
    assert "photo" in image_no_caption.lower()

    # Image WITH caption should not be intercepted (should go to agent)
    image_with_caption = agent._handle_special_media("image", "Can you explain this chart?")
    assert image_with_caption is None

    # Document
    doc_reply = agent._handle_special_media("document", "financial_report.pdf")
    assert doc_reply is not None
    assert "document" in doc_reply.lower()


@pytest.mark.asyncio
async def test_agent_missing_api_key():
    """Verify clean, helpful notification when Gemini API key is not configured."""
    agent = WhatsAppAgent(api_key=None)
    reply = await agent.execute_agent(sender_id="15550001111", prompt="What is artificial intelligence?")
    assert "Gemini API key is not configured" in reply


@pytest.mark.asyncio
async def test_agent_process_user_turn():
    """Verify end-to-end user turn recording and response generation with mock client."""
    # Create mock GenAI response
    mock_response = MagicMock()
    mock_response.text = "🌤️ *Weather in London* is currently 22°C (72°F) and partly cloudy."
    mock_response.candidates = []

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    agent = WhatsAppAgent(api_key="valid_mock_api_key", client=mock_client)
    sender = "15554445555"

    reply = await agent.process_user_turn(
        sender_id=sender,
        user_message="What is the weather in London?",
        media_type="text",
    )

    assert "Weather in London" in reply
    assert "*" in reply  # Uses WhatsApp formatting

    # Check that both turns were stored in SQLite memory
    history = await memory_store.get_history(sender)
    assert len(history) >= 2
    assert history[-2]["role"] == "user"
    assert history[-2]["content"] == "What is the weather in London?"
    assert history[-1]["role"] == "assistant"
    assert history[-1]["content"] == reply
