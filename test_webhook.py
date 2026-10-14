"""Local mock webhook simulator for WhatsApp Cloud API.

Allows testing webhook endpoints locally without needing Meta Developer Portal
or ngrok tunnels. Can run either against an in-process FastAPI instance
or against a live local server (http://localhost:8000).

Usage:
    # Run in-process test simulation
    python test_webhook.py

    # Run against a live server
    python test_webhook.py --live --url http://localhost:8000
"""

import argparse
import asyncio
import json
import time
from typing import Any, Dict

import httpx

from config import settings
from main import app


def build_whatsapp_text_payload(
    from_number: str = "15551234567",
    text_body: str = "Hello! What is the weather in Paris?",
    message_id: str = "wamid.HBgLMTU1NTEyMzQ1NjcVAgARGBI1RkQ4OEQzODcxRDMyRjc4",
) -> Dict[str, Any]:
    """Build a standard WhatsApp Cloud API incoming text message payload."""
    return {
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
                                "phone_number_id": settings.PHONE_NUMBER_ID or "1234567890",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Test User"},
                                    "wa_id": from_number,
                                }
                            ],
                            "messages": [
                                {
                                    "from": from_number,
                                    "id": message_id,
                                    "timestamp": str(int(time.time())),
                                    "text": {"body": text_body},
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def build_whatsapp_media_payload(
    from_number: str = "15551234567",
    media_type: str = "image",
    caption: str = "Check this photo!",
    message_id: str = "wamid.HBgLMTU1NTEyMzQ1NjcVAgARGBI5RkQ4OEQzODcxRDMyRjc5",
) -> Dict[str, Any]:
    """Build a WhatsApp Cloud API incoming media message payload."""
    media_obj: Dict[str, Any] = {"id": "media_987654321"}
    if media_type == "image":
        media_obj.update({"mime_type": "image/jpeg", "caption": caption})
    elif media_type == "audio":
        media_obj.update({"mime_type": "audio/ogg", "voice": True})
    elif media_type == "document":
        media_obj.update({"mime_type": "application/pdf", "filename": "document.pdf", "caption": caption})

    return {
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
                                "phone_number_id": settings.PHONE_NUMBER_ID or "1234567890",
                            },
                            "contacts": [{"profile": {"name": "Test User"}, "wa_id": from_number}],
                            "messages": [
                                {
                                    "from": from_number,
                                    "id": message_id,
                                    "timestamp": str(int(time.time())),
                                    "type": media_type,
                                    media_type: media_obj,
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def build_whatsapp_button_payload(
    from_number: str = "15551234567",
    button_title: str = "Operating Hours",
    button_id: str = "btn_hours",
    message_id: str = "wamid.HBgLMTU1NTEyMzQ1NjcVAgARGBI5RkQ4OEQzODcxRDMyRjgx",
) -> Dict[str, Any]:
    """Build an interactive button reply payload."""
    return {
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
                                "phone_number_id": settings.PHONE_NUMBER_ID or "1234567890",
                            },
                            "contacts": [{"profile": {"name": "Test User"}, "wa_id": from_number}],
                            "messages": [
                                {
                                    "from": from_number,
                                    "id": message_id,
                                    "timestamp": str(int(time.time())),
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "button_reply",
                                        "button_reply": {
                                            "id": button_id,
                                            "title": button_title,
                                        },
                                    },
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


async def run_simulation(base_url: str = "http://testserver", live: bool = False):
    """Execute the simulation sequence."""
    print("=" * 70)
    print(" WhatsApp AI Chatbot Webhook Simulation Suite")
    print("=" * 70)

    # Use live HTTP client or ASGI AsyncClient
    if live:
        client = httpx.AsyncClient(base_url=base_url, timeout=10.0)
    else:
        # We configure settings to use mock provider during simulation so no real HTTP calls to Meta are made
        settings.MESSAGING_PROVIDER = "mock"
        client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
            timeout=10.0,
        )

    async with client:
        # Step 1: Webhook GET verification handshake
        print("\n[TEST 1] Testing Webhook GET Verification Handshake...")
        verify_params = {
            "hub.mode": "subscribe",
            "hub.verify_token": settings.VERIFY_TOKEN,
            "hub.challenge": "1158201444",
        }
        res = await client.get("/webhook", params=verify_params)
        print(f"Status Code: {res.status_code}")
        print(f"Response: {res.text}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        assert res.text == "1158201444", f"Challenge mismatch: {res.text}"
        print(" Verification handshake PASSED!")

        # Step 2: Inbound Text Message (Tool triggering: Weather)
        print("\n[TEST 2] Sending Inbound Text Message ('What is the weather in Tokyo?')...")
        msg_id_1 = f"wamid_test_{int(time.time())}_1"
        payload_1 = build_whatsapp_text_payload(
            from_number="15551234567",
            text_body="What is the weather in Tokyo?",
            message_id=msg_id_1,
        )
        res1 = await client.post("/webhook", json=payload_1)
        print(f"Status Code: {res1.status_code}, Response: {res1.json()}")
        assert res1.status_code == 200
        print(" Text intake accepted! Processing in background worker.")

        # Give worker a moment to process the turn
        await asyncio.sleep(0.5)

        # Step 3: Inbound Knowledge Base Inquiry
        print("\n[TEST 3] Sending Inbound Inquiry ('What are your operating hours?')...")
        msg_id_2 = f"wamid_test_{int(time.time())}_2"
        payload_2 = build_whatsapp_text_payload(
            from_number="15551234567",
            text_body="What are your operating hours?",
            message_id=msg_id_2,
        )
        res2 = await client.post("/webhook", json=payload_2)
        print(f"Status Code: {res2.status_code}, Response: {res2.json()}")
        assert res2.status_code == 200

        # Step 4: Non-Text Media Message (Voice Note)
        print("\n[TEST 4] Sending Audio Voice Message...")
        msg_id_3 = f"wamid_test_{int(time.time())}_3"
        payload_3 = build_whatsapp_media_payload(
            from_number="15551234567",
            media_type="audio",
            message_id=msg_id_3,
        )
        res3 = await client.post("/webhook", json=payload_3)
        print(f"Status Code: {res3.status_code}, Response: {res3.json()}")
        assert res3.status_code == 200

        # Step 5: Interactive Button Reply
        print("\n[TEST 5] Sending Interactive Button Reply...")
        msg_id_4 = f"wamid_test_{int(time.time())}_4"
        payload_4 = build_whatsapp_button_payload(
            from_number="15551234567",
            button_title="Check Plans",
            button_id="btn_plans",
            message_id=msg_id_4,
        )
        res4 = await client.post("/webhook", json=payload_4)
        print(f"Status Code: {res4.status_code}, Response: {res4.json()}")
        assert res4.status_code == 200

        # Step 6: Deduplication Test (Sending same msg_id_1 again)
        print("\n[TEST 6] Testing Message Deduplication (re-sending msg_id_1)...")
        res_dup = await client.post("/webhook", json=payload_1)
        print(f"Status Code: {res_dup.status_code}, Response: {res_dup.json()}")
        assert res_dup.status_code == 200

        # Step 7: Check Session History & Health
        await asyncio.sleep(0.5)
        print("\n[TEST 7] Verifying Health Check & User Conversation History...")
        health_res = await client.get("/health")
        print("Health Status:", json.dumps(health_res.json(), indent=2))

        history_res = await client.get("/history/15551234567")
        print("\nUser Chat History:")
        for turn in history_res.json().get("history", []):
            print(f" - [{turn['role'].upper()}] {turn['content'][:80]}...")

    print("\n" + "=" * 70)
    print(" All simulation scenarios completed successfully!")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="WhatsApp AI Chatbot Webhook Test Simulator")
    parser.add_argument("--live", action="store_true", help="Run against a live running server")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of live server")
    args = parser.parse_args()

    asyncio.run(run_simulation(base_url=args.url, live=args.live))


if __name__ == "__main__":
    main()
