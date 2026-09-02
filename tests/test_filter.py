"""Unit tests for MessageFilter logic."""

import pytest
from signal_repost_bot.config import AppConfig, FilterConfig
from signal_repost_bot.models import SignalEnvelope, DataMessage, GroupInfo, Attachment, QuoteInfo
from signal_repost_bot.filter import MessageFilter


@pytest.fixture
def base_config():
    return AppConfig(
        signal_account="+19998887777",
        spectator_group_id="spectator-group-id",
        source_group_ids=["source-group-1", "source-group-2"],
        filters=FilterConfig(
            require_photo=True,
            require_text=True,
            ignore_replies=True,
            ignore_bot_messages=True,
        ),
    )


def test_filter_valid_message(base_config):
    flt = MessageFilter(base_config)
    env = SignalEnvelope(
        source="+15550001111",
        sourceName="Bob",
        dataMessage=DataMessage(
            message="Fresh items!",
            groupInfo=GroupInfo(groupId="source-group-1", name="Group A"),
            attachments=[Attachment(contentType="image/jpeg", id="a1")],
        ),
    )
    should_repost, reason = flt.should_repost(env)
    assert should_repost is True


def test_filter_rejects_text_only(base_config):
    flt = MessageFilter(base_config)
    env = SignalEnvelope(
        source="+15550001111",
        dataMessage=DataMessage(
            message="Hello everyone",
            groupInfo=GroupInfo(groupId="source-group-1", name="Group A"),
            attachments=[],
        ),
    )
    should_repost, reason = flt.should_repost(env)
    assert should_repost is False
    assert "photo/media" in reason


def test_filter_rejects_photo_without_text(base_config):
    flt = MessageFilter(base_config)
    env = SignalEnvelope(
        source="+15550001111",
        dataMessage=DataMessage(
            message="",
            groupInfo=GroupInfo(groupId="source-group-1", name="Group A"),
            attachments=[Attachment(contentType="image/png", id="a1")],
        ),
    )
    should_repost, reason = flt.should_repost(env)
    assert should_repost is False
    assert "text caption" in reason


def test_filter_rejects_spectator_group_origin(base_config):
    flt = MessageFilter(base_config)
    env = SignalEnvelope(
        source="+15550001111",
        dataMessage=DataMessage(
            message="Loop test",
            groupInfo=GroupInfo(groupId="spectator-group-id", name="Spectators"),
            attachments=[Attachment(contentType="image/jpeg", id="a1")],
        ),
    )
    should_repost, reason = flt.should_repost(env)
    assert should_repost is False
    assert "spectator group" in reason


def test_filter_rejects_unlisted_source_group(base_config):
    flt = MessageFilter(base_config)
    env = SignalEnvelope(
        source="+15550001111",
        dataMessage=DataMessage(
            message="Random group",
            groupInfo=GroupInfo(groupId="random-group-99", name="Random"),
            attachments=[Attachment(contentType="image/jpeg", id="a1")],
        ),
    )
    should_repost, reason = flt.should_repost(env)
    assert should_repost is False
    assert "source_group_ids" in reason


def test_filter_wildcard_source_groups(base_config):
    base_config.routes[0].source_group_ids = ["*"]
    flt = MessageFilter(base_config)
    env = SignalEnvelope(
        source="+15550001111",
        dataMessage=DataMessage(
            message="Any group message",
            groupInfo=GroupInfo(groupId="random-group-99", name="Random"),
            attachments=[Attachment(contentType="image/jpeg", id="a1")],
        ),
    )
    should_repost, reason = flt.should_repost(env)
    assert should_repost is True


def test_filter_rejects_replies(base_config):
    flt = MessageFilter(base_config)
    env = SignalEnvelope(
        source="+15550001111",
        dataMessage=DataMessage(
            message="Replying with photo",
            groupInfo=GroupInfo(groupId="source-group-1", name="Group A"),
            attachments=[Attachment(contentType="image/jpeg", id="a1")],
            quote=QuoteInfo(id=123, author="+15550002222", text="Original msg"),
        ),
    )
    should_repost, reason = flt.should_repost(env)
    assert should_repost is False
    assert "reply/quote" in reason
