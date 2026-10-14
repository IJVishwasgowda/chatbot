"""Configuration module for WhatsApp AI Chatbot backend.

Loads and validates environment variables for Google Antigravity SDK,
WhatsApp Cloud API, fallback providers (Twilio, Green-API), and storage.
"""

import os
from pathlib import Path
from typing import Literal
from dotenv import load_dotenv

# Load .env file from project root if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class Settings:
    """Application runtime settings with fail-safe defaults."""

    # Server configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    # Gemini & AI Agent credentials
    GEMINI_API_KEY: str = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("ANTIGRAVITY_API_KEY")
        or ""
    )
    ANTIGRAVITY_API_KEY: str = (
        os.getenv("ANTIGRAVITY_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or ""
    )
    AGENT_MODEL: str = (
        os.getenv("AGENT_MODEL")
        or os.getenv("GEMINI_MODEL")
        or "gemini-2.5-flash"
    )
    AGENT_TEMPERATURE: float = float(os.getenv("AGENT_TEMPERATURE", "0.7"))

    # Messaging Provider Selection: "whatsapp" (default), "twilio", "green_api", "mock"
    MESSAGING_PROVIDER: Literal["whatsapp", "twilio", "green_api", "mock"] = (
        os.getenv("MESSAGING_PROVIDER", "whatsapp").lower()  # type: ignore
    )

    # WhatsApp Cloud API credentials
    WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "")
    PHONE_NUMBER_ID: str = os.getenv("PHONE_NUMBER_ID", "")
    VERIFY_TOKEN: str = os.getenv("VERIFY_TOKEN", "my_whatsapp_webhook_secret_token_123")
    APP_SECRET: str = os.getenv("APP_SECRET", "")  # For HMAC-SHA256 signature verification
    WHATSAPP_API_VERSION: str = os.getenv("WHATSAPP_API_VERSION", "v21.0")
    WHATSAPP_BASE_URL: str = os.getenv(
        "WHATSAPP_BASE_URL", f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"
    )

    # Twilio Fallback credentials
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER: str = os.getenv("TWILIO_FROM_NUMBER", "whatsapp:+14155238886")

    # Green-API Fallback credentials
    GREEN_API_INSTANCE_ID: str = os.getenv("GREEN_API_INSTANCE_ID", "")
    GREEN_API_TOKEN: str = os.getenv("GREEN_API_TOKEN", "")
    GREEN_API_HOST: str = os.getenv("GREEN_API_HOST", "https://api.green-api.com")

    # Storage & Memory
    DB_PATH: str = os.getenv("DB_PATH", str(DATA_DIR / "conversations.db"))
    MAX_HISTORY_TURNS: int = int(os.getenv("MAX_HISTORY_TURNS", "20"))

    # Resiliency, Queue & Rate Limiting
    MAX_QUEUE_SIZE: int = int(os.getenv("MAX_QUEUE_SIZE", "1000"))
    WORKER_CONCURRENCY: int = int(os.getenv("WORKER_CONCURRENCY", "4"))
    HTTP_TIMEOUT_SECONDS: float = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10.0"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_BACKOFF_FACTOR: float = float(os.getenv("RETRY_BACKOFF_FACTOR", "1.5"))


# Singleton settings instance
settings = Settings()
