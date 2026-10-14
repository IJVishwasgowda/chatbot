"""Unit tests for conversation memory store (SQLite)."""

import asyncio
import os
import tempfile
import pytest

from memory import SQLiteMemoryStore


@pytest.fixture
def temp_store():
    """Create a temporary isolated SQLite database for testing."""
    import gc
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = f.name
    store = SQLiteMemoryStore(db_path=temp_path)
    yield store
    del store
    gc.collect()
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        for extra in (f"{temp_path}-wal", f"{temp_path}-shm"):
            if os.path.exists(extra):
                os.remove(extra)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_save_and_retrieve_history(temp_store):
    """Test saving messages and retrieving them in chronological order."""
    sender = "15551112222"
    
    await temp_store.save_message(sender, "user", "Hello assistant!")
    await temp_store.save_message(sender, "assistant", "Hello! How can I help?")
    await temp_store.save_message(sender, "user", "What is the weather today?")

    history = await temp_store.get_history(sender, limit=10)
    assert len(history) == 3
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello assistant!"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Hello! How can I help?"
    assert history[2]["role"] == "user"
    assert history[2]["content"] == "What is the weather today?"


@pytest.mark.asyncio
async def test_sliding_window_limit(temp_store):
    """Test that message retrieval strictly honors the limit (sliding window)."""
    sender = "15553334444"
    
    # Insert 30 messages
    for i in range(30):
        role = "user" if i % 2 == 0 else "assistant"
        await temp_store.save_message(sender, role, f"Message #{i}")

    # Default limit is 20
    history = await temp_store.get_history(sender, limit=20)
    assert len(history) == 20
    # Should contain the latest 20 messages (from 10 to 29)
    assert history[0]["content"] == "Message #10"
    assert history[-1]["content"] == "Message #29"


@pytest.mark.asyncio
async def test_multi_user_isolation(temp_store):
    """Ensure messages from one user do not leak into another user's history."""
    user_a = "15551111111"
    user_b = "15552222222"

    await temp_store.save_message(user_a, "user", "Message for A")
    await temp_store.save_message(user_b, "user", "Message for B")

    history_a = await temp_store.get_history(user_a)
    history_b = await temp_store.get_history(user_b)

    assert len(history_a) == 1
    assert history_a[0]["content"] == "Message for A"
    assert len(history_b) == 1
    assert history_b[0]["content"] == "Message for B"


@pytest.mark.asyncio
async def test_message_deduplication(temp_store):
    """Test deduplication tracking table."""
    msg_id = "wamid.test_dedup_001"
    sender = "15551234567"

    # Initially not processed
    assert await temp_store.is_message_processed(msg_id) is False

    # Mark processed
    await temp_store.mark_message_processed(msg_id, sender)
    assert await temp_store.is_message_processed(msg_id) is True

    # Duplicate call should not fail (INSERT OR IGNORE)
    await temp_store.mark_message_processed(msg_id, sender)
    assert await temp_store.is_message_processed(msg_id) is True


@pytest.mark.asyncio
async def test_clear_history(temp_store):
    """Test clearing history for a single user."""
    user = "15559998888"
    await temp_store.save_message(user, "user", "Message 1")
    await temp_store.save_message(user, "assistant", "Reply 1")

    deleted = await temp_store.clear_history(user)
    assert deleted == 2

    history = await temp_store.get_history(user)
    assert len(history) == 0


def test_format_history_for_prompt(temp_store):
    """Test prompt formatting helper."""
    history = [
        {"role": "user", "content": "Hi", "media_type": "text"},
        {"role": "assistant", "content": "Hello! How can I help?", "media_type": "text"},
        {"role": "user", "content": "Check this", "media_type": "image"},
    ]
    prompt_str = temp_store.format_history_for_prompt(history)
    assert "User: Hi" in prompt_str
    assert "Assistant: Hello! How can I help?" in prompt_str
    assert "User [IMAGE]: Check this" in prompt_str
