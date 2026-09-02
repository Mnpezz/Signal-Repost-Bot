"""Unit tests for signal models and JSON envelope parsing."""

import pytest
from signal_repost_bot.models import SignalEnvelope, Attachment, GroupInfo, DataMessage


def test_attachment_media_detection():
    photo = Attachment(contentType="image/jpeg", id="1", filename="test.jpg")
    png = Attachment(contentType="image/png", id="2", filename="test.png")
    gif = Attachment(contentType="image/gif", id="3", filename="test.gif")
    video = Attachment(contentType="video/mp4", id="4", filename="test.mp4")
    other = Attachment(contentType="application/pdf", id="5", filename="doc.pdf")

    assert photo.is_image is True
    assert photo.is_gif is False
    assert photo.is_video is False

    assert png.is_image is True

    assert gif.is_image is False
    assert gif.is_gif is True

    assert video.is_video is True
    assert video.is_image is False

    assert other.is_image is False
    assert other.is_video is False


def test_envelope_group_message_parsing():
    payload = {
        "source": "+15550001111",
        "sourceName": "Alice",
        "timestamp": 1690000000000,
        "dataMessage": {
            "timestamp": 1690000000000,
            "message": "Fresh batch just arrived!",
            "groupInfo": {
                "groupId": "group-abc-123",
                "name": "Market Vendors",
            },
            "attachments": [
                {"contentType": "image/jpeg", "id": "att-1", "filename": "photo.jpg"}
            ],
        },
    }

    envelope = SignalEnvelope(**payload)
    assert envelope.is_group_message is True
    assert envelope.group_id == "group-abc-123"
    assert envelope.group_name == "Market Vendors"
    assert envelope.sender_name == "Alice"
    assert envelope.text == "Fresh batch just arrived!"
    assert envelope.has_image() is True
    assert envelope.has_media() is True
