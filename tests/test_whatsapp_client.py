"""Unit tests for WhatsApp Cloud API client, retries, and formatting."""

import pytest
import httpx
from unittest.mock import AsyncMock, patch

from whatsapp_client import (
    WhatsAppCloudAPIClient,
    MockMessagingClient,
    TokenExpiredError,
    RateLimitExceededError,
    get_messaging_client,
)


@pytest.mark.asyncio
async def test_send_text_message_payload():
    """Verify outgoing WhatsApp text payload format."""
    client = WhatsAppCloudAPIClient(
        token="test_token",
        phone_number_id="1234567890",
        base_url="https://graph.facebook.com/v21.0",
    )

    mock_response = httpx.Response(
        status_code=200,
        json={"messaging_product": "whatsapp", "messages": [{"id": "wamid.out_123"}]},
        request=httpx.Request("POST", "https://graph.facebook.com/v21.0/1234567890/messages"),
    )

    with patch.object(client, "_post_with_retry", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = {"messages": [{"id": "wamid.out_123"}]}
        res = await client.send_text_message(to="+15551234567", text="*Hello world!*")

        assert "messages" in res
        mock_post.assert_awaited_once_with(
            "messages",
            {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": "15551234567",
                "type": "text",
                "text": {"preview_url": False, "body": "*Hello world!*"},
            },
        )
    await client.close()


@pytest.mark.asyncio
async def test_send_interactive_buttons_payload():
    """Verify interactive button payload and constraints (max 3 buttons, 20 char title)."""
    client = WhatsAppCloudAPIClient(token="test_token", phone_number_id="1234567890")

    buttons = [
        {"id": "btn_1", "title": "Check Weather Now"},  # Exactly 17 chars
        {"id": "btn_2", "title": "This is a super extremely long title that exceeds twenty chars"},
        {"id": "btn_3", "title": "Help"},
        {"id": "btn_4", "title": "Ignored fourth button"},  # Meta allows max 3
    ]

    with patch.object(client, "_post_with_retry", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = {"messages": [{"id": "wamid.out_btn_1"}]}
        await client.send_interactive_buttons(
            to="15551234567",
            body_text="Choose an action:",
            buttons=buttons,
        )

        mock_post.assert_awaited_once()
        sent_payload = mock_post.await_args.args[1]
        action_buttons = sent_payload["interactive"]["action"]["buttons"]

        # Assert max 3 buttons
        assert len(action_buttons) == 3
        # Assert title capped to 20 chars
        assert len(action_buttons[1]["reply"]["title"]) <= 20
        assert action_buttons[1]["reply"]["title"] == "This is a super extr"
    await client.close()


@pytest.mark.asyncio
async def test_token_expired_error():
    """Verify that Meta code 190 triggers TokenExpiredError."""
    client = WhatsAppCloudAPIClient(token="expired_token", phone_number_id="1234567890")

    error_resp = httpx.Response(
        status_code=401,
        json={
            "error": {
                "message": "Error validating access token: Session has expired",
                "type": "OAuthException",
                "code": 190,
                "error_subcode": 463,
            }
        },
        request=httpx.Request("POST", "https://graph.facebook.com/v21.0/1234567890/messages"),
    )

    with patch.object(httpx.AsyncClient, "post", return_value=error_resp):
        with pytest.raises(TokenExpiredError) as exc_info:
            await client.send_text_message(to="15551234567", text="Test")
        assert "token expired" in str(exc_info.value).lower()
    await client.close()


@pytest.mark.asyncio
async def test_mock_messaging_client():
    """Verify MockMessagingClient records messages in-memory."""
    mock_client = MockMessagingClient()
    await mock_client.send_text_message(to="15550001111", text="Hello from mock!")
    await mock_client.send_interactive_buttons(
        to="15550001111",
        body_text="Select option",
        buttons=[{"id": "b1", "title": "Yes"}],
    )
    await mock_client.mark_message_as_read("wamid.mock_read_1")

    assert len(mock_client.sent_messages) == 2
    assert mock_client.sent_messages[0]["text"] == "Hello from mock!"
    assert len(mock_client.marked_as_read) == 1
    assert mock_client.marked_as_read[0] == "wamid.mock_read_1"


def test_messaging_client_factory():
    """Verify factory returns appropriate client classes."""
    wa_client = get_messaging_client("whatsapp")
    assert isinstance(wa_client, WhatsAppCloudAPIClient)

    mock_client = get_messaging_client("mock")
    assert isinstance(mock_client, MockMessagingClient)
