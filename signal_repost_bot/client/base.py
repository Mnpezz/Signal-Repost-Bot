"""Abstract Base Class for Signal Client connections."""

from abc import ABC, abstractmethod
from typing import List, Callable, Awaitable, Dict, Any
from signal_repost_bot.models import SignalEnvelope


class BaseSignalClient(ABC):
    """Abstract Signal Client interface for receiving and sending Signal messages."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to Signal daemon or API endpoint."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close client connection."""
        pass

    @abstractmethod
    async def list_groups(self) -> List[Dict[str, Any]]:
        """List groups joined by the Signal account."""
        pass

    @abstractmethod
    async def send_message(
        self,
        recipient_group_id: str,
        message: str,
        attachments: List[str],
    ) -> bool:
        """
        Send a message with optional attachment files to a target group.

        Args:
            recipient_group_id: Target group ID
            message: Formatted text caption
            attachments: List of local file paths to attachments

        Returns:
            bool: True if message sent successfully
        """
        pass

    @abstractmethod
    async def listen(self, callback: Callable[[SignalEnvelope], Awaitable[None]]) -> None:
        """
        Listen for incoming Signal envelopes and dispatch to callback function.

        Args:
            callback: Async function taking a SignalEnvelope
        """
        pass
