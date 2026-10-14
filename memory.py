"""Persistent conversation memory store for WhatsApp chatbot.

Manages per-user dialog history in SQLite with thread-safe execution,
WAL mode for concurrent access, and a sliding window of the last 15-20 turns.
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import settings

logger = logging.getLogger("whatsapp_bot.memory")


class SQLiteMemoryStore:
    """Thread-safe SQLite persistent store for conversation turns."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or settings.DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    from contextlib import contextmanager

    @contextmanager
    def _connection_context(self):
        """Create a configured SQLite connection with WAL mode and ensure it is closed."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=10.0,
            check_same_thread=False,
            isolation_level=None,  # Autocommit mode
        )
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA busy_timeout = 5000;")
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize database schema with proper indexes."""
        with self._connection_context() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                    content TEXT NOT NULL,
                    media_type TEXT NOT NULL DEFAULT 'text',
                    created_at TIMESTAMP NOT NULL,
                    metadata_json TEXT
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_sender_created
                ON messages(sender_id, created_at DESC);
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_messages (
                    message_id TEXT PRIMARY KEY,
                    sender_id TEXT NOT NULL,
                    processed_at TIMESTAMP NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_processed_sender
                ON processed_messages(sender_id);
                """
            )
        logger.info("Initialized conversation memory database at %s", self.db_path)

    # ---------------- Synchronous Core Methods ----------------

    def save_message_sync(
        self,
        sender_id: str,
        role: str,
        content: str,
        media_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Persist a conversation turn to the database."""
        now = datetime.now(timezone.utc).isoformat()
        metadata_str = json.dumps(metadata or {})
        with self._connection_context() as conn:
            cursor = conn.execute(
                """
                INSERT INTO messages (sender_id, role, content, media_type, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (sender_id, role, content, media_type, now, metadata_str),
            )
            return cursor.lastrowid or 0

    def get_history_sync(
        self, sender_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve recent conversation turns in chronological order."""
        turn_limit = limit if limit is not None else settings.MAX_HISTORY_TURNS
        with self._connection_context() as conn:
            # Fetch the latest N messages (descending), then reverse to chronological order
            cursor = conn.execute(
                """
                SELECT id, sender_id, role, content, media_type, created_at, metadata_json
                FROM messages
                WHERE sender_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (sender_id, turn_limit),
            )
            rows = cursor.fetchall()
            
            history = []
            for row in reversed(rows):
                metadata = {}
                if row["metadata_json"]:
                    try:
                        metadata = json.loads(row["metadata_json"])
                    except json.JSONDecodeError:
                        metadata = {}
                history.append(
                    {
                        "id": row["id"],
                        "sender_id": row["sender_id"],
                        "role": row["role"],
                        "content": row["content"],
                        "media_type": row["media_type"],
                        "created_at": row["created_at"],
                        "metadata": metadata,
                    }
                )
            return history

    def clear_history_sync(self, sender_id: str) -> int:
        """Clear all conversation history for a specific sender."""
        with self._connection_context() as conn:
            cursor = conn.execute(
                "DELETE FROM messages WHERE sender_id = ?",
                (sender_id,),
            )
            return cursor.rowcount

    def is_message_processed_sync(self, message_id: str) -> bool:
        """Check whether a WhatsApp message ID has already been processed."""
        with self._connection_context() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM processed_messages WHERE message_id = ?",
                (message_id,),
            )
            return cursor.fetchone() is not None

    def mark_message_processed_sync(self, message_id: str, sender_id: str) -> None:
        """Record a WhatsApp message ID as processed to enforce deduplication."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connection_context() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO processed_messages (message_id, sender_id, processed_at)
                VALUES (?, ?, ?)
                """,
                (message_id, sender_id, now),
            )

    def get_stats_sync(self) -> Dict[str, Any]:
        """Return aggregate statistics for health checks."""
        with self._connection_context() as conn:
            msg_count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            user_count = conn.execute(
                "SELECT COUNT(DISTINCT sender_id) FROM messages"
            ).fetchone()[0]
            dedup_count = conn.execute(
                "SELECT COUNT(*) FROM processed_messages"
            ).fetchone()[0]
            return {
                "total_messages": msg_count,
                "distinct_users": user_count,
                "deduplicated_messages": dedup_count,
            }

    def get_conversations_sync(self) -> List[Dict[str, Any]]:
        """Retrieve list of distinct conversations with last message preview and message count."""
        with self._connection_context() as conn:
            cursor = conn.execute(
                """
                SELECT 
                    m.sender_id,
                    m.content AS last_message,
                    m.role AS last_role,
                    m.media_type AS last_media_type,
                    m.created_at AS last_timestamp,
                    cnt.total_messages
                FROM messages m
                INNER JOIN (
                    SELECT sender_id, MAX(id) as max_id, COUNT(*) as total_messages
                    FROM messages
                    GROUP BY sender_id
                ) cnt ON m.sender_id = cnt.sender_id AND m.id = cnt.max_id
                ORDER BY m.id DESC;
                """
            )
            rows = cursor.fetchall()
            conversations = []
            for row in rows:
                conversations.append(
                    {
                        "sender_id": row["sender_id"],
                        "last_message": row["last_message"],
                        "last_role": row["last_role"],
                        "media_type": row["last_media_type"],
                        "last_timestamp": row["last_timestamp"],
                        "total_messages": row["total_messages"],
                    }
                )
            return conversations

    # ---------------- Asynchronous Interfaces ----------------

    async def save_message(
        self,
        sender_id: str,
        role: str,
        content: str,
        media_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Asynchronously save a message turn to SQLite."""
        return await asyncio.to_thread(
            self.save_message_sync, sender_id, role, content, media_type, metadata
        )

    async def get_history(
        self, sender_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Asynchronously retrieve conversation history in chronological order."""
        return await asyncio.to_thread(self.get_history_sync, sender_id, limit)

    async def get_conversations(self) -> List[Dict[str, Any]]:
        """Asynchronously retrieve conversation summaries."""
        return await asyncio.to_thread(self.get_conversations_sync)

    async def clear_history(self, sender_id: str) -> int:
        """Asynchronously delete user history."""
        return await asyncio.to_thread(self.clear_history_sync, sender_id)

    async def is_message_processed(self, message_id: str) -> bool:
        """Asynchronously check message deduplication status."""
        return await asyncio.to_thread(self.is_message_processed_sync, message_id)

    async def mark_message_processed(self, message_id: str, sender_id: str) -> None:
        """Asynchronously record message deduplication mark."""
        await asyncio.to_thread(self.mark_message_processed_sync, message_id, sender_id)

    async def get_stats(self) -> Dict[str, Any]:
        """Asynchronously retrieve memory store metrics."""
        return await asyncio.to_thread(self.get_stats_sync)

    def format_history_for_prompt(
        self, history: List[Dict[str, Any]]
    ) -> str:
        """Format history list into a structured dialog transcript for prompt injection."""
        if not history:
            return "No previous conversation history. This is the start of the chat."

        lines = ["=== RECENT CONVERSATION HISTORY ==="]
        for turn in history:
            role_label = "User" if turn["role"] == "user" else "Assistant"
            media_info = (
                f" [{turn['media_type'].upper()}]"
                if turn.get("media_type") and turn["media_type"] != "text"
                else ""
            )
            content = turn.get("content", "").strip()
            lines.append(f"{role_label}{media_info}: {content}")
        lines.append("=== END OF CONVERSATION HISTORY ===")
        return "\n".join(lines)


# Singleton memory store instance
memory_store = SQLiteMemoryStore()
