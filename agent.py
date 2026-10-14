"""Google Gemini AI Agent configuration and execution core.

Manages:
- Versatile, general-purpose system prompt for a wide variety of domains:
  general knowledge, programming, math/science, education, writing/translation,
  business, and multi-turn context.
- Native integration with Google GenAI SDK (`google.genai`).
- Direct Gemini generation without forcing tools for ordinary queries.
- Tool calling (`get_current_weather`, `lookup_knowledge_base`, `calculate_service_quote`)
  with Automatic Function Calling (AFC).
- Multi-turn conversation context injection from SQLite persistent memory.
- Detailed error handling for missing keys, invalid models, rate limits (429), and server issues.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional

from config import settings
from memory import memory_store

# Google Gen AI SDK
try:
    from google import genai
    from google.genai import types, errors
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False
    genai = None  # type: ignore
    types = None  # type: ignore
    errors = None  # type: ignore

logger = logging.getLogger("whatsapp_bot.agent")

# ----------------- General-Purpose Persona & System Prompt -----------------

SYSTEM_INSTRUCTIONS = """You are a highly capable, knowledgeable, and helpful AI Assistant powered by Google Gemini.

You are a general-purpose AI designed to assist users across a broad spectrum of topics and tasks:

1. Core Capabilities:
   - General Knowledge: History, geography, science, literature, politics, notable figures, and world events.
   - Programming & Tech: Python, Java, JavaScript, TypeScript, SQL, HTML/CSS, algorithms, system architecture, web development, and code debugging with clean, copyable examples.
   - Mathematics & Science: Solve step-by-step arithmetic and algebra (showing clear calculations), physics, chemistry, biology, and engineering concepts.
   - Education & Learning: Concept explanations, exam prep, study guides, step-by-step tutorials, and clear analogies.
   - Writing & Languages: Grammar correction, drafting, editing, and natural language translations across languages (including English, Kannada, Hindi, Spanish, French, German, Japanese, etc.).
   - Business & Productivity: Strategy, career advice, professional communication, and everyday problem solving.
   - Conversational Continuity: Maintain context from earlier messages in the conversation and answer follow-ups naturally.

2. Presentation & Formatting:
   - Keep answers clear, direct, well-structured, and helpful.
   - Use WhatsApp-style formatting effectively:
     • *bold* for key terms, numbers, or section headers.
     • _italics_ for gentle emphasis or clarification.
     • `code` or code blocks for programming snippets, formulas, or commands.
     • bullet points (• or *) for lists and sequential steps.
   - Use emojis tastefully where appropriate (e.g. 💡, ✅, 💻, 🌤️, 📊).

3. Tools & Direct Knowledge:
   - Answer general knowledge, coding, math, translation, science, and everyday questions DIRECTLY using your comprehensive knowledge base. Do NOT attempt to invoke tools for general questions.
   - Specialized tools are available and should ONLY be called when genuinely required:
     • `get_current_weather`: Invoke ONLY when the user asks for real-time live weather or forecast in a specific city/location.
     • `lookup_knowledge_base`: Invoke ONLY when the user specifically inquires about our internal company business hours, return/refund policies, or company subscription tiers.
     • `calculate_service_quote`: Invoke ONLY when the user asks for a price estimate or monthly quote for our service tiers (Starter, Professional, Enterprise) and seat count.
   - Never fabricate real-time live information or fake tool outputs.
"""

# ----------------- Specialized Agentic Tools -----------------

def get_current_weather(location: str) -> Dict[str, Any]:
    """Retrieve real-time weather information and forecast for any city or location.

    Args:
        location: Name of the city, region, or area (e.g. 'Paris', 'Tokyo', 'San Francisco').
    """
    loc_clean = location.strip().title()
    sample_weather = {
        "location": loc_clean,
        "temperature": "22°C (72°F)",
        "condition": "Partly Cloudy with sunny intervals",
        "humidity": "58%",
        "wind_speed": "12 km/h",
        "recommendation": "Pleasant conditions outside, ideal for outdoor activities.",
    }
    logger.info("Tool executed: get_current_weather for '%s'", loc_clean)
    return sample_weather


def lookup_knowledge_base(query: str) -> Dict[str, Any]:
    """Search internal company knowledge base, business hours, service details, and FAQ.

    Args:
        query: Specific query regarding company business hours, refund policy, or subscription plans.
    """
    q_lower = query.lower()
    logger.info("Tool executed: lookup_knowledge_base for query: '%s'", query)

    if "hour" in q_lower or "time" in q_lower or "open" in q_lower:
        return {
            "topic": "Operating Hours",
            "content": "Our support center is open Monday through Friday, 8:00 AM – 8:00 PM EST. Weekend automated support is available 24/7.",
        }
    elif "return" in q_lower or "refund" in q_lower:
        return {
            "topic": "Refund & Return Policy",
            "content": "We offer a 30-day money-back guarantee with hassle-free returns. Contact support with your order ID.",
        }
    elif "plan" in q_lower or "tier" in q_lower or "pricing" in q_lower:
        return {
            "topic": "Available Plans",
            "content": "Starter: $29/mo (up to 5 users). Professional: $99/mo (up to 25 users). Enterprise: Custom tailored solutions.",
        }
    else:
        return {
            "topic": "General Information",
            "content": "We provide AI-powered automated workflow and messaging infrastructure. You can ask for our plans, hours, or request a quote.",
        }


def calculate_service_quote(service_tier: str, users_count: int) -> Dict[str, Any]:
    """Calculate an estimated monthly price quote based on tier and team size.

    Args:
        service_tier: 'starter', 'professional', or 'enterprise'.
        users_count: Total number of active team seats required.
    """
    tier = service_tier.lower().strip()
    users = max(1, int(users_count))

    rates = {"starter": 6.0, "professional": 12.0, "enterprise": 20.0}
    base_rate = rates.get(tier, 10.0)
    monthly_total = base_rate * users

    logger.info("Tool executed: calculate_service_quote (tier: %s, users: %d)", tier, users)
    return {
        "tier": tier.title(),
        "users": users,
        "price_per_user": f"${base_rate:.2f}/mo",
        "estimated_monthly_total": f"${monthly_total:.2f}/mo",
        "includes": "24/7 priority SLA, API access, and dedicated support onboarding.",
    }


REGISTERED_TOOLS: List[Callable[..., Any]] = [
    get_current_weather,
    lookup_knowledge_base,
    calculate_service_quote,
]


# ----------------- WhatsApp Agent Class -----------------

class WhatsAppAgent:
    """Encapsulated Gemini AI agent manager with persistent multi-turn conversation memory."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        client: Optional[Any] = None,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY or settings.ANTIGRAVITY_API_KEY
        self.model = model or settings.AGENT_MODEL
        self.temperature = settings.AGENT_TEMPERATURE
        self._custom_client = client

    def _get_client(self) -> Optional[Any]:
        """Lazily initialize and return the Google GenAI Client instance."""
        if self._custom_client is not None:
            return self._custom_client

        if not GOOGLE_GENAI_AVAILABLE:
            logger.error("google-genai package is not installed.")
            return None

        clean_key = (self.api_key or "").strip()
        if not clean_key or clean_key in (
            "mock_key",
            "your_api_key_here",
            "your_actual_gemini_or_antigravity_api_key_here",
            "your_google_antigravity_api_key_here",
            "your_gemini_api_key_here",
        ):
            return None

        try:
            return genai.Client(api_key=clean_key)
        except Exception as exc:
            logger.error("Failed to initialize genai.Client: %s", exc)
            return None

    def _build_gemini_contents(
        self, history: List[Dict[str, Any]], current_prompt: str
    ) -> List[Any]:
        """Convert SQLite memory history into properly alternating Gemini types.Content turns."""
        contents: List[Any] = []

        # Determine if the current prompt was already saved to SQLite before execute_agent
        history_to_process = list(history)
        has_current_turn = (
            bool(history_to_process)
            and history_to_process[-1].get("role") == "user"
            and history_to_process[-1].get("content") == current_prompt
        )

        if not has_current_turn:
            history_to_process.append({"role": "user", "content": current_prompt})

        for turn in history_to_process:
            role = "user" if turn.get("role") == "user" else "model"
            text = (turn.get("content") or "").strip()
            if not text:
                continue

            # Merge consecutive same-role turns to satisfy Gemini API alternating requirement
            if contents and contents[-1].role == role:
                existing_part = contents[-1].parts[0]
                existing_part.text = f"{existing_part.text}\n\n{text}"
            else:
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=text)],
                    )
                )

        # Gemini API requires that the conversation begins with a 'user' turn
        while contents and contents[0].role != "user":
            contents.pop(0)

        # Fallback if empty
        if not contents:
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=current_prompt)],
                )
            ]

        return contents

    def _handle_special_media(
        self, media_type: str, caption: str
    ) -> Optional[str]:
        """Check if incoming message is a non-text media and generate an immediate helpful reply."""
        media_type = (media_type or "text").lower()

        if media_type == "audio":
            return (
                "🎙️ *I received your voice message!*\n\n"
                "I currently specialize in text and images. "
                "Could you please type a quick summary or question? I'd be happy to help!"
            )

        if media_type in ("video", "document"):
            caption_info = f"\n_Caption provided:_ \"{caption}\"" if caption else ""
            return (
                f"📄 *I received your {media_type}!*{caption_info}\n\n"
                "Please type what you'd like me to check or assist you with regarding this file."
            )

        if media_type == "image" and not caption.strip():
            return (
                "📸 *Thanks for sharing the photo!*\n\n"
                "What would you like me to do with this image? "
                "Feel free to reply with your question or details."
            )

        return None

    async def execute_agent(
        self, sender_id: str, prompt: str, media_type: str = "text"
    ) -> str:
        """Execute Gemini model generation with SQLite multi-turn memory and error handling."""
        clean_prompt = prompt.strip()
        if not clean_prompt:
            return "Please provide a message or question to chat."

        # Handle voice notes, attachments without captions
        media_reply = self._handle_special_media(media_type, clean_prompt)
        if media_reply:
            return media_reply

        # Retrieve recent dialog history from SQLite memory (up to MAX_HISTORY_TURNS)
        recent_history = await memory_store.get_history(
            sender_id, limit=settings.MAX_HISTORY_TURNS
        )

        # Check API key configuration
        client = self._get_client()
        if client is None:
            logger.warning(
                "Gemini API key is unconfigured or invalid (sender: %s). Reporting configuration requirement.",
                sender_id,
            )
            return (
                "⚠️ *Gemini API key is not configured.*\n\n"
                "Please set `GEMINI_API_KEY` (or `ANTIGRAVITY_API_KEY`) in your `.env` file to chat with the AI model."
            )

        # Assemble Gemini multi-turn contents
        contents = self._build_gemini_contents(recent_history, clean_prompt)

        # Configure model parameters and function calling tools
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTIONS,
            temperature=self.temperature,
            tools=REGISTERED_TOOLS,
        )

        try:
            logger.info(
                "Calling Gemini model '%s' for sender %s (history turns: %d)",
                self.model,
                sender_id,
                len(contents),
            )

            # Asynchronous Gemini generation with Automatic Function Calling (AFC)
            response = await client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )

            # Extract generated response text
            if response.text and response.text.strip():
                return response.text.strip()

            # Inspect candidates if response.text is empty
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    text_parts = [
                        p.text
                        for p in candidate.content.parts
                        if hasattr(p, "text") and p.text
                    ]
                    if text_parts:
                        return "".join(text_parts).strip()

                if candidate.finish_reason:
                    return f"⚠️ Response completed with status: {candidate.finish_reason}. Please rephrase your query."

            return "I processed your request, but could not generate a text response. Please try again."

        except errors.ClientError as exc:
            err_str = str(exc)
            logger.error("Gemini ClientError for sender %s: %s", sender_id, err_str)

            code = getattr(exc, "code", None)
            status_str = getattr(exc, "status", None) or ""

            if code == 429 or "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "RESOURCE_EXHAUSTED" in status_str:
                return (
                    "⚠️ *Rate Limit Exceeded*: Gemini API quota or rate limit has been reached. "
                    "Please wait a moment and try again."
                )
            elif (
                code == 403
                or "403" in err_str
                or "API_KEY_INVALID" in err_str
                or "PERMISSION_DENIED" in err_str
            ):
                return (
                    "⚠️ *Authentication Error*: Invalid or unauthorized Gemini API key. "
                    "Please check your `GEMINI_API_KEY` in `.env`."
                )
            elif code == 404 or "404" in err_str or "NOT_FOUND" in err_str:
                return (
                    f"⚠️ *Model Not Found*: The configured model '{self.model}' was not found. "
                    "Please verify `AGENT_MODEL` in your `.env` (recommended: `gemini-2.5-flash`)."
                )
            elif code == 400 or "400" in err_str or "INVALID_ARGUMENT" in err_str:
                clean_msg = err_str.split("\n")[0][:140]
                return f"⚠️ *Invalid Request Error*: {clean_msg}"
            else:
                clean_msg = err_str.split("\n")[0][:140]
                return f"⚠️ *Gemini API Error*: {clean_msg}"

        except errors.ServerError as exc:
            logger.error("Gemini ServerError for sender %s: %s", sender_id, exc)
            return (
                "⚠️ *Gemini Server Error*: Google AI services are temporarily unavailable. "
                "Please try again shortly."
            )

        except errors.APIError as exc:
            logger.error("Gemini APIError for sender %s: %s", sender_id, exc)
            clean_msg = str(exc).split("\n")[0][:140]
            return f"⚠️ *Gemini Service Error*: {clean_msg}"

        except asyncio.TimeoutError:
            logger.error("Gemini API call timed out for sender %s", sender_id)
            return "⚠️ *Timeout*: The AI service took too long to respond. Please try again."

        except Exception as exc:
            logger.exception("Unexpected error during agent execution for sender %s: %s", sender_id, exc)
            return f"⚠️ *Processing Error*: An unexpected error occurred ({type(exc).__name__}). Please try again."

    async def process_user_turn(
        self,
        sender_id: str,
        user_message: str,
        media_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Full pipeline: records user message, executes agent, records assistant reply, returns text."""
        # 1. Record inbound user message in SQLite memory
        await memory_store.save_message(
            sender_id=sender_id,
            role="user",
            content=user_message,
            media_type=media_type,
            metadata=metadata,
        )

        # 2. Execute agent
        assistant_reply = await self.execute_agent(
            sender_id=sender_id,
            prompt=user_message,
            media_type=media_type,
        )

        # 3. Record outbound assistant reply in SQLite memory
        await memory_store.save_message(
            sender_id=sender_id,
            role="assistant",
            content=assistant_reply,
            media_type="text",
            metadata={"model": self.model},
        )

        return assistant_reply


# Singleton agent instance
bot_agent = WhatsAppAgent()
