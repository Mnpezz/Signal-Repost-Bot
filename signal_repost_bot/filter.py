"""Message filter engine to determine whether an incoming envelope should be reposted."""

import logging
from typing import Tuple, Optional
from signal_repost_bot.config import AppConfig, RouteConfig
from signal_repost_bot.models import SignalEnvelope

logger = logging.getLogger(__name__)


class MessageFilter:
    """Evaluates incoming Signal envelopes against configured rules and routes."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.filters = config.filters

    def evaluate_route(self, envelope: SignalEnvelope, route: RouteConfig) -> Tuple[bool, Optional[str]]:
        """
        Evaluate envelope against a specific route's filtering rules.

        Returns:
            (bool, Optional[str]): Tuple of (should_repost, reason_for_decision)
        """
        filters = route.filters

        # 1. Check if envelope contains a data message
        if not envelope.dataMessage:
            return False, "Not a data message (reaction, receipt, or call)"

        # 2. Check if envelope is from a group
        if not envelope.is_group_message:
            return False, "Not a group message"

        group_id = envelope.group_id

        # 3. Check if message is from the spectator group itself
        if group_id == route.spectator_group_id:
            return False, "Message originated from spectator group"

        # 4. Check if message was sent by the bot account itself
        if filters.ignore_bot_messages:
            sender = envelope.sender_number
            if sender and sender == self.config.signal_account:
                return False, "Message sent by bot account itself"

        # 5. Source group check
        if "*" not in route.source_group_ids:
            if group_id not in route.source_group_ids:
                return False, f"Group ID '{group_id}' not in route '{route.name}' source_group_ids"

        # 6. Blacklist & Whitelist sender check
        sender_id = envelope.sender_number
        if sender_id in filters.blacklisted_senders:
            return False, f"Sender '{sender_id}' is blacklisted"

        if filters.whitelisted_senders:
            if sender_id not in filters.whitelisted_senders:
                return False, f"Sender '{sender_id}' is not in whitelisted_senders"

        # 7. Quote/Reply check
        if filters.ignore_replies and envelope.dataMessage.quote:
            return False, "Message is a reply/quote"

        # 8. Media requirement check
        if filters.require_photo:
            has_media = envelope.has_media(
                allow_videos=filters.allow_videos,
                allow_gifs=filters.allow_gifs,
            )
            if not has_media:
                return False, "Message does not contain required photo/media"

        # 9. Text caption requirement check
        if filters.require_text:
            text = envelope.text
            if not text or not text.strip():
                return False, "Message does not contain required text caption"

        return True, "Message passed all filter criteria for route"

    def should_repost(self, envelope: SignalEnvelope) -> Tuple[bool, Optional[str]]:
        """Backwards compatibility wrapper evaluating the first route or global rules."""
        if self.config.routes:
            return self.evaluate_route(envelope, self.config.routes[0])
        return False, "No routes configured"
