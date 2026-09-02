"""Unit tests for MessageFormatter."""

import pytest
from signal_repost_bot.config import FormattingConfig
from signal_repost_bot.models import SignalEnvelope, DataMessage, GroupInfo
from signal_repost_bot.formatter import MessageFormatter


def test_formatter_default():
    fmt_config = FormattingConfig(
        prepend_group_name=True,
        prepend_sender_name=True,
    )
    formatter = MessageFormatter(fmt_config)

    env = SignalEnvelope(
        source="+15550001111",
        sourceName="Joe's Seafood",
        dataMessage=DataMessage(
            message="Fresh shrimp today!",
            groupInfo=GroupInfo(groupId="g1", name="Market Vendors"),
        ),
    )

    result = formatter.format(env)
    assert result == "📸 [Market Vendors] Joe's Seafood:\n\nFresh shrimp today!"


def test_formatter_group_only():
    fmt_config = FormattingConfig(
        prepend_group_name=True,
        prepend_sender_name=False,
    )
    formatter = MessageFormatter(fmt_config)

    env = SignalEnvelope(
        source="+15550001111",
        sourceName="Joe's Seafood",
        dataMessage=DataMessage(
            message="Fresh shrimp today!",
            groupInfo=GroupInfo(groupId="g1", name="Market Vendors"),
        ),
    )

    result = formatter.format(env)
    assert result == "📸 [Market Vendors]:\n\nFresh shrimp today!"
