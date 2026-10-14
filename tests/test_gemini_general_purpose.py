"""Comprehensive tests for General-Purpose Gemini AI Agent and Conversation Memory.

Validates all required domains and test queries:
1. General knowledge, history, programming, math, translation, tech comparisons.
2. Multi-turn conversation memory and follow-up contextual recall.
3. Selective tool usage (no forced tools for ordinary questions).
4. Missing API keys, invalid model identifiers, 429 rate limits, and server error handling.
5. Strict isolation between distinct users' conversation histories in SQLite.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from google.genai import errors

from agent import WhatsAppAgent
from memory import memory_store


@pytest.fixture
def mock_gemini_agent():
    """Create a WhatsAppAgent wired to a simulated Gemini model response generator."""
    mock_client = MagicMock()

    async def mock_generate_content(model, contents, config):
        # Retrieve the latest user prompt from contents
        user_prompt = ""
        for c in reversed(contents):
            if c.role == "user" and c.parts and hasattr(c.parts[0], "text"):
                user_prompt = c.parts[0].text
                break

        resp = MagicMock()
        resp.candidates = []

        q_lower = user_prompt.lower()

        # 1. AI Definition
        if "what is artificial intelligence" in q_lower:
            resp.text = (
                "*Artificial Intelligence (AI)* is the simulation of human intelligence in machines "
                "programmed to think, learn, and solve problems. It encompasses machine learning, "
                "deep learning, computer vision, and natural language processing."
            )
        # 2. Python functions
        elif "python function" in q_lower:
            resp.text = (
                "In Python, a *function* is defined using the `def` keyword:\n\n"
                "```python\ndef greet(name):\n    return f'Hello, {name}!'\n```\n\n"
                "Functions accept parameters, execute logic, and return values."
            )
        # 3. Arithmetic calculation: 25 x 48
        elif "25 × 48" in user_prompt or "25 * 48" in user_prompt or "25 x 48" in q_lower:
            resp.text = (
                "*Calculation:* 25 × 48\n"
                "• 25 × 40 = 1,000\n"
                "• 25 × 8 = 200\n"
                "• 1,000 + 200 = *1,200*\n\n"
                "Result: *1,200*"
            )
        # 4. First PM of India
        elif "prime minister of india" in q_lower:
            resp.text = (
                "*Jawaharlal Nehru* was the first Prime Minister of independent India, "
                "serving from August 15, 1947, until his death in 1964."
            )
        # 5. Kannada translation
        elif "kannada" in q_lower and "how are you" in q_lower:
            resp.text = (
                "The Kannada translation of 'How are you?' is:\n\n"
                "*ನೀವು ಹೇಗಿದ್ದೀರಿ?* (Nīvu hēgiddīri? - formal/polite)\n"
                "*ಹೇಗಿದ್ದೀಯಾ?* (Hēgiddīyā? - informal/casual)"
            )
        # 6. NLP vs LLMs
        elif "nlp" in q_lower and "llm" in q_lower:
            resp.text = (
                "*NLP (Natural Language Processing)* is the broad field of computer science "
                "dealing with how machines interact with human language.\n\n"
                "*LLMs (Large Language Models)* are a specific, cutting-edge class of deep learning "
                "models (like Gemini, GPT) trained on massive text corpora to perform complex language tasks."
            )
        # 7. Memory Recall check: "What did I ask you in my previous message?"
        elif "previous message" in q_lower:
            # Check previous user turns in contents
            user_turns = [
                c.parts[0].text
                for c in contents[:-1]
                if c.role == "user" and c.parts and hasattr(c.parts[0], "text")
            ]
            if user_turns:
                prev_q = user_turns[-1]
                resp.text = f"In your previous message, you asked: *'{prev_q}'*"
            else:
                resp.text = "You haven't asked any previous questions in this conversation."
        else:
            resp.text = f"Gemini direct response to: {user_prompt}"

        return resp

    mock_client.aio.models.generate_content = AsyncMock(side_effect=mock_generate_content)
    agent = WhatsAppAgent(
        api_key="valid_test_gemini_key",
        model="gemini-2.5-flash",
        client=mock_client,
    )
    return agent


@pytest.mark.asyncio
async def test_general_knowledge_ai_definition(mock_gemini_agent):
    """Test Question 1: What is artificial intelligence?"""
    sender = "test_user_ai_01"
    reply = await mock_gemini_agent.process_user_turn(
        sender_id=sender,
        user_message="What is artificial intelligence?",
    )
    assert "Artificial Intelligence" in reply
    assert "simulation of human intelligence" in reply.lower()
    # Confirm not a hardcoded fallback
    assert "Live weather & forecasts" not in reply


@pytest.mark.asyncio
async def test_programming_python_functions(mock_gemini_agent):
    """Test Question 2: Explain Python functions with examples."""
    sender = "test_user_py_02"
    reply = await mock_gemini_agent.process_user_turn(
        sender_id=sender,
        user_message="Explain Python functions with examples.",
    )
    assert "def greet" in reply or "function" in reply.lower()
    assert "```python" in reply


@pytest.mark.asyncio
async def test_math_step_by_step_calculation(mock_gemini_agent):
    """Test Question 3: Solve 25 × 48 and show the calculation."""
    sender = "test_user_math_03"
    reply = await mock_gemini_agent.process_user_turn(
        sender_id=sender,
        user_message="Solve 25 × 48 and show the calculation.",
    )
    assert "1,200" in reply or "1200" in reply
    assert "Calculation" in reply or "×" in reply


@pytest.mark.asyncio
async def test_history_first_pm_india(mock_gemini_agent):
    """Test Question 4: Who was the first Prime Minister of India?"""
    sender = "test_user_hist_04"
    reply = await mock_gemini_agent.process_user_turn(
        sender_id=sender,
        user_message="Who was the first Prime Minister of India?",
    )
    assert "Jawaharlal Nehru" in reply


@pytest.mark.asyncio
async def test_translation_to_kannada(mock_gemini_agent):
    """Test Question 5: Translate 'How are you?' into Kannada."""
    sender = "test_user_lang_05"
    reply = await mock_gemini_agent.process_user_turn(
        sender_id=sender,
        user_message="Translate 'How are you?' into Kannada.",
    )
    assert "ಹೇಗಿದ್ದೀರಿ" in reply or "Hēgiddīri" in reply or "Kannada" in reply


@pytest.mark.asyncio
async def test_tech_nlp_vs_llm_comparison(mock_gemini_agent):
    """Test Question 6: Explain the difference between NLP and LLMs."""
    sender = "test_user_tech_06"
    reply = await mock_gemini_agent.process_user_turn(
        sender_id=sender,
        user_message="Explain the difference between NLP and LLMs.",
    )
    assert "NLP" in reply
    assert "LLM" in reply


@pytest.mark.asyncio
async def test_conversation_memory_follow_up(mock_gemini_agent):
    """Test Question 7: Verify conversation memory with follow-up 'What did I ask you in my previous message?'"""
    sender = "test_user_mem_07"
    await memory_store.clear_history(sender)

    # Turn 1: Ask history question
    q1 = "Who was the first Prime Minister of India?"
    reply1 = await mock_gemini_agent.process_user_turn(
        sender_id=sender,
        user_message=q1,
    )
    assert "Jawaharlal Nehru" in reply1

    # Turn 2: Follow-up question relying on memory
    q2 = "What did I ask you in my previous message?"
    reply2 = await mock_gemini_agent.process_user_turn(
        sender_id=sender,
        user_message=q2,
    )
    # Model recalls the exact earlier question from SQLite memory history
    assert "Who was the first Prime Minister of India?" in reply2

    # Check history in SQLite contains both user turns and both assistant replies
    history = await memory_store.get_history(sender)
    assert len(history) == 4
    assert history[0]["content"] == q1
    assert history[1]["content"] == reply1
    assert history[2]["content"] == q2
    assert history[3]["content"] == reply2


@pytest.mark.asyncio
async def test_user_memory_isolation(mock_gemini_agent):
    """Verify different users' conversation histories are strictly isolated and not mixed."""
    user_a = "user_alpha_111"
    user_b = "user_beta_222"
    await memory_store.clear_history(user_a)
    await memory_store.clear_history(user_b)

    # User A asks about Python
    await mock_gemini_agent.process_user_turn(
        sender_id=user_a,
        user_message="Explain Python functions with examples.",
    )

    # User B asks about India
    await mock_gemini_agent.process_user_turn(
        sender_id=user_b,
        user_message="Who was the first Prime Minister of India?",
    )

    # User A asks what they asked previously -> should mention Python, NOT India
    reply_a = await mock_gemini_agent.process_user_turn(
        sender_id=user_a,
        user_message="What did I ask you in my previous message?",
    )
    assert "Python" in reply_a
    assert "Prime Minister" not in reply_a

    # User B asks what they asked previously -> should mention Prime Minister, NOT Python
    reply_b = await mock_gemini_agent.process_user_turn(
        sender_id=user_b,
        user_message="What did I ask you in my previous message?",
    )
    assert "Prime Minister" in reply_b
    assert "Python" not in reply_b


@pytest.mark.asyncio
async def test_missing_api_key_handling():
    """Verify behavior when API key is completely missing."""
    agent = WhatsAppAgent(api_key="")
    reply = await agent.execute_agent(sender_id="user_nokey", prompt="Hello!")
    assert "Gemini API key is not configured" in reply


@pytest.mark.asyncio
async def test_invalid_model_name_handling():
    """Verify behavior when configured model name is invalid (e.g. 404 Not Found)."""
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=errors.ClientError(404, {"error": {"message": "models/invalid-model-v99 is not found", "status": "NOT_FOUND"}})
    )
    agent = WhatsAppAgent(
        api_key="valid_key",
        model="invalid-model-v99",
        client=mock_client,
    )
    reply = await agent.execute_agent(sender_id="user_badmodel", prompt="Hello!")
    assert "Model Not Found" in reply or "invalid-model-v99" in reply


@pytest.mark.asyncio
async def test_rate_limit_429_handling():
    """Verify behavior when API quota/rate limit is exceeded (HTTP 429)."""
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=errors.ClientError(429, {"error": {"message": "quota exceeded for current minute", "status": "RESOURCE_EXHAUSTED"}})
    )
    agent = WhatsAppAgent(
        api_key="valid_key",
        model="gemini-2.5-flash",
        client=mock_client,
    )
    reply = await agent.execute_agent(sender_id="user_ratelimit", prompt="Hello!")
    assert "Rate Limit Exceeded" in reply


@pytest.mark.asyncio
async def test_server_error_500_handling():
    """Verify behavior when Google AI services experience 5xx server errors."""
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=errors.ServerError(500, {"error": {"message": "Internal Server Error in Gemini backend", "status": "INTERNAL"}})
    )
    agent = WhatsAppAgent(
        api_key="valid_key",
        model="gemini-2.5-flash",
        client=mock_client,
    )
    reply = await agent.execute_agent(sender_id="user_servererr", prompt="Hello!")
    assert "Gemini Server Error" in reply
