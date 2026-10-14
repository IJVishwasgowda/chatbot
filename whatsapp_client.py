"""Asynchronous WhatsApp client and messaging provider integrations.

Supports:
- Meta WhatsApp Cloud API (Graph API) with interactive replies, mark-as-read,
  exponential backoff retry for rate limits (HTTP 429 / 5xx), and token error detection.
- Twilio WhatsApp fallback.
- Green-API WhatsApp fallback.
- Mock messaging client for unit tests and local demonstrations.
"""

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

from config import settings

logger = logging.getLogger("whatsapp_bot.client")


class TokenExpiredError(Exception):
    """Raised when the WhatsApp Cloud API access token is expired or invalid (OAuth error 190)."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class RateLimitExceededError(Exception):
    """Raised when the messaging provider rate limit is exceeded."""

    def __init__(self, message: str, retry_after: float = 5.0):
        super().__init__(message)
        self.retry_after = retry_after


class BaseMessagingClient(ABC):
    """Abstract base class for WhatsApp / messaging providers."""

    @abstractmethod
    async def send_text_message(
        self, to: str, text: str, preview_url: bool = False
    ) -> Dict[str, Any]:
        """Send a standard text message to the recipient."""
        pass

    @abstractmethod
    async def send_interactive_buttons(
        self, to: str, body_text: str, buttons: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Send an interactive reply button message.
        
        Buttons format: [{"id": "btn_1", "title": "Option 1"}, ...]
        """
        pass

    @abstractmethod
    async def mark_message_as_read(self, message_id: str) -> bool:
        """Mark an incoming message as read."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Clean up HTTP client sessions."""
        pass


class WhatsAppCloudAPIClient(BaseMessagingClient):
    """Production client for Meta WhatsApp Cloud API (Graph API)."""

    def __init__(
        self,
        token: Optional[str] = None,
        phone_number_id: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.token = token or settings.WHATSAPP_TOKEN
        self.phone_number_id = phone_number_id or settings.PHONE_NUMBER_ID
        self.base_url = (base_url or settings.WHATSAPP_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.HTTP_TIMEOUT_SECONDS
        self._client: Optional[httpx.AsyncClient] = None

    def _get_http_client(self) -> httpx.AsyncClient:
        """Lazily initialize an httpx.AsyncClient connection pool."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def _post_with_retry(
        self, endpoint: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Post request with exponential backoff for transient errors (429, 5xx)."""
        url = f"{self.base_url}/{self.phone_number_id}/{endpoint.lstrip('/')}"
        client = self._get_http_client()

        max_retries = settings.MAX_RETRIES
        backoff = settings.RETRY_BACKOFF_FACTOR

        for attempt in range(1, max_retries + 1):
            try:
                response = await client.post(url, json=payload)

                # Check for Meta OAuth token expiration / invalid token
                if response.status_code == 401:
                    err_json = response.json() if response.content else {}
                    error_data = err_json.get("error", {})
                    code = error_data.get("code")
                    if code == 190 or "token" in error_data.get("message", "").lower():
                        logger.critical(
                            "WhatsApp Cloud API Token is EXPIRED or INVALID! Error: %s",
                            error_data,
                        )
                        raise TokenExpiredError(
                            "WhatsApp Cloud API token expired or unauthorized.",
                            details=error_data,
                        )
                    response.raise_for_status()

                # Handle Rate Limiting (429)
                if response.status_code == 429:
                    retry_after = float(
                        response.headers.get(
                            "Retry-After", backoff * (2 ** (attempt - 1))
                        )
                    )
                    logger.warning(
                        "WhatsApp API rate limit hit (429). Attempt %d/%d. Waiting %.1fs",
                        attempt,
                        max_retries,
                        retry_after,
                    )
                    if attempt == max_retries:
                        raise RateLimitExceededError(
                            "Exceeded maximum retries on WhatsApp rate limit.",
                            retry_after=retry_after,
                        )
                    await asyncio.sleep(retry_after + random.uniform(0.1, 0.5))
                    continue

                # Handle Server Errors (500, 502, 503, 504)
                if response.status_code >= 500:
                    logger.warning(
                        "WhatsApp API server error %d on attempt %d/%d",
                        response.status_code,
                        attempt,
                        max_retries,
                    )
                    if attempt == max_retries:
                        response.raise_for_status()
                    wait_time = (backoff ** attempt) + random.uniform(0.1, 0.5)
                    await asyncio.sleep(wait_time)
                    continue

                # Raise for any other 4xx errors
                response.raise_for_status()
                return response.json()

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                logger.warning(
                    "Network error connecting to WhatsApp API (attempt %d/%d): %s",
                    attempt,
                    max_retries,
                    exc,
                )
                if attempt == max_retries:
                    raise
                wait_time = (backoff ** attempt) + random.uniform(0.1, 0.5)
                await asyncio.sleep(wait_time)

        raise RuntimeError("Failed to complete WhatsApp API request after retries.")

    async def send_text_message(
        self, to: str, text: str, preview_url: bool = False
    ) -> Dict[str, Any]:
        """Send a standard text message via WhatsApp Cloud API."""
        clean_to = to.replace("+", "").strip()
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_to,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": text,
            },
        }
        logger.info("Sending WhatsApp text message to %s (len: %d)", clean_to, len(text))
        return await self._post_with_retry("messages", payload)

    async def send_interactive_buttons(
        self, to: str, body_text: str, buttons: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Send up to 3 interactive reply buttons."""
        clean_to = to.replace("+", "").strip()
        
        # Meta limits button replies to at most 3 buttons
        formatted_buttons = []
        for btn in buttons[:3]:
            formatted_buttons.append(
                {
                    "type": "reply",
                    "reply": {
                        "id": btn.get("id", f"btn_{len(formatted_buttons)}"),
                        "title": btn.get("title", "")[:20],  # Meta 20-char max title
                    },
                }
            )

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body_text},
                "action": {"buttons": formatted_buttons},
            },
        }
        logger.info(
            "Sending WhatsApp interactive buttons to %s (count: %d)",
            clean_to,
            len(formatted_buttons),
        )
        return await self._post_with_retry("messages", payload)

    async def mark_message_as_read(self, message_id: str) -> bool:
        """Mark message as read to acknowledge receipt in the WhatsApp client."""
        if not message_id:
            return False
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        try:
            await self._post_with_retry("messages", payload)
            return True
        except Exception as e:
            logger.debug("Failed to mark message %s as read: %s", message_id, e)
            return False

    async def close(self) -> None:
        """Close HTTP client connection pool."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class TwilioClient(BaseMessagingClient):
    """Fallback client for Twilio WhatsApp API."""

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
    ):
        self.account_sid = account_sid or settings.TWILIO_ACCOUNT_SID
        self.auth_token = auth_token or settings.TWILIO_AUTH_TOKEN
        self.from_number = from_number or settings.TWILIO_FROM_NUMBER
        self._client: Optional[httpx.AsyncClient] = None

    def _get_http_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                auth=(self.account_sid, self.auth_token),
                timeout=httpx.Timeout(settings.HTTP_TIMEOUT_SECONDS),
            )
        return self._client

    async def send_text_message(
        self, to: str, text: str, preview_url: bool = False
    ) -> Dict[str, Any]:
        """Send WhatsApp message using Twilio REST API."""
        to_number = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
        from_number = (
            self.from_number
            if self.from_number.startswith("whatsapp:")
            else f"whatsapp:{self.from_number}"
        )
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        
        client = self._get_http_client()
        data = {
            "To": to_number,
            "From": from_number,
            "Body": text,
        }
        logger.info("Sending Twilio WhatsApp message to %s", to_number)
        resp = await client.post(url, data=data)
        resp.raise_for_status()
        return resp.json()

    async def send_interactive_buttons(
        self, to: str, body_text: str, buttons: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Twilio fallback formats buttons as a clean numbered list."""
        button_options = "\n".join(
            f"{i + 1}. {btn.get('title', '')}" for i, btn in enumerate(buttons)
        )
        combined_text = f"{body_text}\n\n{button_options}"
        return await self.send_text_message(to, combined_text)

    async def mark_message_as_read(self, message_id: str) -> bool:
        # Twilio manages read receipts automatically
        return True

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class GreenAPIClient(BaseMessagingClient):
    """Fallback client for Green-API WhatsApp instances."""

    def __init__(
        self,
        instance_id: Optional[str] = None,
        token: Optional[str] = None,
        host: Optional[str] = None,
    ):
        self.instance_id = instance_id or settings.GREEN_API_INSTANCE_ID
        self.token = token or settings.GREEN_API_TOKEN
        self.host = (host or settings.GREEN_API_HOST).rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    def _get_http_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.HTTP_TIMEOUT_SECONDS)
            )
        return self._client

    async def send_text_message(
        self, to: str, text: str, preview_url: bool = False
    ) -> Dict[str, Any]:
        """Send message using Green-API sendMessage."""
        clean_to = to.replace("+", "").strip()
        chat_id = clean_to if "@c.us" in clean_to else f"{clean_to}@c.us"
        url = f"{self.host}/waInstance{self.instance_id}/sendMessage/{self.token}"

        payload = {
            "chatId": chat_id,
            "message": text,
        }
        logger.info("Sending Green-API message to %s", chat_id)
        client = self._get_http_client()
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()

    async def send_interactive_buttons(
        self, to: str, body_text: str, buttons: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Green-API button fallback."""
        button_options = "\n".join(
            f"[{i + 1}] {btn.get('title', '')}" for i, btn in enumerate(buttons)
        )
        return await self.send_text_message(to, f"{body_text}\n\n{button_options}")

    async def mark_message_as_read(self, message_id: str) -> bool:
        return True

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class MockMessagingClient(BaseMessagingClient):
    """In-memory mock messaging client for unit testing and local offline demos."""

    def __init__(self):
        self.sent_messages: List[Dict[str, Any]] = []
        self.marked_as_read: List[str] = []

    async def send_text_message(
        self, to: str, text: str, preview_url: bool = False
    ) -> Dict[str, Any]:
        entry = {
            "type": "text",
            "to": to,
            "text": text,
            "preview_url": preview_url,
            "message_id": f"mock_msg_{len(self.sent_messages) + 1}",
        }
        self.sent_messages.append(entry)
        logger.info("[MOCK MESSAGING] Sent to %s: %s", to, text)
        return {"messages": [{"id": entry["message_id"]}], "status": "sent"}

    async def send_interactive_buttons(
        self, to: str, body_text: str, buttons: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        entry = {
            "type": "interactive_button",
            "to": to,
            "body_text": body_text,
            "buttons": buttons,
            "message_id": f"mock_msg_{len(self.sent_messages) + 1}",
        }
        self.sent_messages.append(entry)
        logger.info(
            "[MOCK MESSAGING] Sent buttons to %s: %s (options: %s)",
            to,
            body_text,
            [b.get("title") for b in buttons],
        )
        return {"messages": [{"id": entry["message_id"]}], "status": "sent"}

    async def mark_message_as_read(self, message_id: str) -> bool:
        self.marked_as_read.append(message_id)
        return True

    async def close(self) -> None:
        pass


def get_messaging_client(
    provider: Optional[str] = None,
) -> BaseMessagingClient:
    """Factory function returning the configured messaging client instance."""
    active_provider = (provider or settings.MESSAGING_PROVIDER).lower()

    if active_provider == "whatsapp":
        return WhatsAppCloudAPIClient()
    elif active_provider == "twilio":
        return TwilioClient()
    elif active_provider == "green_api":
        return GreenAPIClient()
    elif active_provider == "mock":
        return MockMessagingClient()
    else:
        logger.warning(
            "Unknown messaging provider '%s'. Defaulting to WhatsAppCloudAPIClient",
            active_provider,
        )
        return WhatsAppCloudAPIClient()
