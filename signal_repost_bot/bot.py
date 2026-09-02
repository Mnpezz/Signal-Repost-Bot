"""Core bot event orchestrator."""

import logging
from typing import Optional, List
from signal_repost_bot.config import AppConfig
from signal_repost_bot.models import SignalEnvelope
from signal_repost_bot.filter import MessageFilter
from signal_repost_bot.formatter import MessageFormatter
from signal_repost_bot.storage import StorageStore
from signal_repost_bot.client import create_signal_client, BaseSignalClient

logger = logging.getLogger(__name__)


class SignalRepostBot:
    """Main bot controller managing receiving, filtering, formatting, and reposting."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.filter = MessageFilter(config)
        self.formatter = MessageFormatter(config.formatting)
        self.storage = StorageStore(config.storage.db_path)
        self.client: BaseSignalClient = create_signal_client(
            client_mode=config.client_mode,
            account=config.signal_account,
            endpoint=config.endpoint,
        )

    async def start(self) -> None:
        """Start the Signal Repost Bot."""
        logger.info("Starting Signal Repost Bot for account %s...", self.config.signal_account)
        logger.info("Loaded %d active route(s):", len(self.config.routes))
        for r in self.config.routes:
            logger.info("  • Route '%s': Monitored=%s -> Target=%s", r.name, r.source_group_ids, r.spectator_group_id)

        # Cleanup old dedup DB entries on launch
        deleted = self.storage.cleanup_old_records(self.config.storage.dedup_ttl_days)
        if deleted > 0:
            logger.info("Cleaned up %d expired deduplication record(s)", deleted)

        await self.client.connect()
        logger.info("Signal client connected. Listening for incoming messages...")
        await self.client.listen(self.on_envelope)

    async def stop(self) -> None:
        """Stop the bot gracefully."""
        logger.info("Stopping Signal Repost Bot...")
        await self.client.disconnect()

    async def on_envelope(self, envelope: SignalEnvelope) -> None:
        """
        Callback triggered whenever a Signal envelope is received.
        Evaluates message against all configured routes.

        Args:
            envelope: Incoming Signal envelope
        """
        if not self.config.routes:
            return

        for route in self.config.routes:
            # 1. Filter evaluation for this specific route
            should_repost, reason = self.filter.evaluate_route(envelope, route)
            if not should_repost:
                logger.debug("Route '%s' skipped message: %s", route.name, reason)
                continue

            # 2. Check deduplication (scoped to spectator group ID)
            raw_key = self.storage.get_message_key(envelope)
            route_msg_key = f"{route.spectator_group_id}:{raw_key}"
            if self.storage.is_processed(route_msg_key):
                logger.info("Route '%s' skipped duplicate message (%s)", route.name, route_msg_key[:12])
                continue

            # 3. Collect local attachment paths
            attachment_paths: List[str] = []
            for att in envelope.attachments:
                if att.path:
                    attachment_paths.append(att.path)
                else:
                    logger.warning("Attachment ID %s missing local file path. Skipping attachment.", att.id)

            # 4. Format caption using route-specific formatting rules
            formatter = MessageFormatter(route.formatting)
            formatted_caption = formatter.format(envelope, fallback_group_name=route.name)

            logger.info(
                "[%s] Reposting message from group [%s] (%s) to spectator group [%s] with %d attachment(s)",
                route.name,
                envelope.group_name or "Unknown",
                envelope.sender_name,
                route.spectator_group_id,
                len(attachment_paths),
            )

            # 5. Send message to target spectator group
            success = await self.client.send_message(
                recipient_group_id=route.spectator_group_id,
                message=formatted_caption,
                attachments=attachment_paths,
            )

            # 6. Mark as processed if sent
            if success:
                self.storage.mark_processed(envelope, route_msg_key)
                logger.info("[%s] Successfully reposted message to spectator group", route.name)
            else:
                logger.error("[%s] Failed to repost message to spectator group", route.name)
