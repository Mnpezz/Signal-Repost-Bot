"""Message formatter to format repost captions with group & sender metadata."""

from typing import Optional
from datetime import datetime
from signal_repost_bot.config import FormattingConfig
from signal_repost_bot.models import SignalEnvelope


class MessageFormatter:
    """Formats incoming Signal envelope text into a spectator group post."""

    def __init__(self, config: FormattingConfig):
        self.config = config

    def format(self, envelope: SignalEnvelope, fallback_group_name: Optional[str] = None) -> str:
        """
        Format the caption for the spectator group.

        Args:
            envelope: Incoming Signal envelope
            fallback_group_name: Optional friendly group/route name if raw group ID hash is received

        Returns:
            str: Complete formatted repost caption
        """
        raw_group_name = envelope.group_name
        # If group name is missing or is raw base64 Group ID hash (e.g. UrFJfd5CoAF5I/SRDj...), use fallback_group_name
        if not raw_group_name or raw_group_name == envelope.group_id or ("=" in raw_group_name or "/" in raw_group_name or len(raw_group_name) > 35):
            group_name = fallback_group_name or raw_group_name or "Signal Group"
        else:
            group_name = raw_group_name

        sender_name = envelope.sourceName or "Unknown Sender"
        sender_phone = envelope.sender_phone
        sender_number = envelope.sender_number or ""
        dm_link = envelope.signal_dm_link
        text = envelope.text or ""

        # Format sender display (use phone number if available, avoid raw UUIDs in header title)
        if self.config.prepend_sender_name:
            if self.config.include_sender_number and sender_phone:
                sender_display = f"{sender_name} ({sender_phone})"
            else:
                sender_display = sender_name
        else:
            sender_display = ""

        # Format header using custom template or default logic
        header_parts = []
        if self.config.prepend_group_name:
            header_parts.append(f"[{group_name}]")
        if self.config.prepend_sender_name and sender_display:
            header_parts.append(sender_display)

        if header_parts:
            header_prefix = " ".join(header_parts)
            if self.config.header_template and self.config.header_template != "📸 [{group_name}] {sender_name}:\n\n":
                header = self.config.header_template.format(
                    group_name=group_name,
                    sender_name=sender_display,
                    sender_number=sender_phone or sender_number,
                    dm_link=dm_link or "",
                )
                if not header.endswith("\n"):
                    header = header + "\n"
            else:
                header = f"📸 {header_prefix}:\n"

            # Add clickable Direct Message deep link if configured
            if self.config.include_dm_link and dm_link:
                header += f"💬 Direct Message: {dm_link}\n"

            header += "\n"
        else:
            header = ""

        timestamp_str = ""
        if self.config.show_timestamp and envelope.timestamp:
            try:
                dt = datetime.fromtimestamp(envelope.timestamp / 1000.0)
                timestamp_str = f"\n\n🕒 {dt.strftime('%Y-%m-%d %H:%M:%S')}"
            except Exception:
                pass

        return f"{header}{text}{timestamp_str}".strip()
