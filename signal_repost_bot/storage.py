"""SQLite persistence layer for message deduplication and bot state."""

import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from signal_repost_bot.models import SignalEnvelope


class StorageStore:
    """Manages SQLite storage for deduplication of processed Signal messages."""

    def __init__(self, db_path: str = "data/bot_state.db"):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize SQLite database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_messages (
                    msg_key TEXT PRIMARY KEY,
                    group_id TEXT,
                    sender TEXT,
                    timestamp INTEGER,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    @staticmethod
    def get_message_key(envelope: SignalEnvelope) -> str:
        """Generate a unique deterministic hash key for a Signal envelope."""
        group_id = envelope.group_id or ""
        sender = envelope.sender_number
        timestamp = envelope.timestamp or 0
        text = envelope.text or ""
        att_ids = ",".join(sorted(att.id or att.filename or "" for att in envelope.attachments))

        raw_str = f"{group_id}:{sender}:{timestamp}:{text}:{att_ids}"
        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

    def is_processed(self, msg_key: str) -> bool:
        """Check if message key has already been processed."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_messages WHERE msg_key = ?", (msg_key,))
            return cursor.fetchone() is not None

    def mark_processed(self, envelope: SignalEnvelope, msg_key: Optional[str] = None):
        """Mark a message envelope as processed in the database."""
        key = msg_key or self.get_message_key(envelope)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO processed_messages (msg_key, group_id, sender, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (key, envelope.group_id, envelope.sender_number, envelope.timestamp),
            )
            conn.commit()

    def cleanup_old_records(self, ttl_days: int = 30) -> int:
        """Remove processed message records older than specified TTL in days."""
        cutoff = datetime.utcnow() - timedelta(days=ttl_days)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM processed_messages WHERE processed_at < ?", (cutoff,))
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
