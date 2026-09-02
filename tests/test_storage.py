"""Unit tests for SQLite storage deduplication."""

import pytest
import tempfile
from pathlib import Path
from signal_repost_bot.models import SignalEnvelope, DataMessage, GroupInfo
from signal_repost_bot.storage import StorageStore


def test_storage_deduplication():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_state.db")
        store = StorageStore(db_path=db_path)

        env = SignalEnvelope(
            source="+15550001111",
            timestamp=1690000000000,
            dataMessage=DataMessage(
                message="Sample post",
                groupInfo=GroupInfo(groupId="g1", name="Group A"),
            ),
        )

        msg_key = store.get_message_key(env)
        assert store.is_processed(msg_key) is False

        store.mark_processed(env, msg_key)
        assert store.is_processed(msg_key) is True
