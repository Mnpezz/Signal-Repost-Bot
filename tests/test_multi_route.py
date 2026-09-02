"""Unit tests for Multi-Route configuration, evaluation, and sender number formatting."""

import pytest
from signal_repost_bot.config import AppConfig, RouteConfig, FilterConfig, FormattingConfig
from signal_repost_bot.models import SignalEnvelope, DataMessage, GroupInfo, Attachment
from signal_repost_bot.filter import MessageFilter
from signal_repost_bot.formatter import MessageFormatter


def test_multi_route_filter_matching():
    route_curb = RouteConfig(
        name="Curb Route",
        spectator_group_id="spectator-curb",
        source_group_ids=["source-curb-1"],
        filters=FilterConfig(require_photo=True, require_text=True),
    )
    route_housing = RouteConfig(
        name="Housing Route",
        spectator_group_id="spectator-housing",
        source_group_ids=["source-housing-1"],
        filters=FilterConfig(require_photo=True, require_text=True),
    )

    config = AppConfig(
        signal_account="+19998887777",
        routes=[route_curb, route_housing],
    )
    flt = MessageFilter(config)

    # Message from Curb source group
    env_curb = SignalEnvelope(
        source="+15551112222",
        sourceName="Alice",
        dataMessage=DataMessage(
            message="Free couch on curb!",
            groupInfo=GroupInfo(groupId="source-curb-1", name="Curb Chat"),
            attachments=[Attachment(contentType="image/jpeg", id="att1")],
        ),
    )

    curb_pass, _ = flt.evaluate_route(env_curb, route_curb)
    housing_pass, _ = flt.evaluate_route(env_curb, route_housing)

    assert curb_pass is True
    assert housing_pass is False


def test_formatter_include_sender_number():
    fmt_config = FormattingConfig(
        include_sender_number=True,
        include_dm_link=True,
        header_template="🏠 [{group_name}] {sender_name}:\n",
    )
    formatter = MessageFormatter(fmt_config)

    env = SignalEnvelope(
        source="+15553334444",
        sourceNumber="+15553334444",
        sourceName="Landlord Bob",
        dataMessage=DataMessage(
            message="1BR available $1200/mo",
            groupInfo=GroupInfo(groupId="g1", name="Housing Chat"),
        ),
    )

    result = formatter.format(env)
    assert "🏠 [Housing Chat] Landlord Bob (+15553334444):" in result
    assert "💬 Direct Message: https://signal.me/#p/+15553334444" in result
    assert "1BR available $1200/mo" in result
