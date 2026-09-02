"""Async HTTP/WebSocket REST API Client for signal-cli-rest-api."""

import asyncio
import json
import base64
import logging
from pathlib import Path
from typing import List, Callable, Awaitable, Dict, Any, Optional
import aiohttp
import websockets
from signal_repost_bot.client.base import BaseSignalClient
from signal_repost_bot.models import SignalEnvelope

logger = logging.getLogger(__name__)


class RestApiSignalClient(BaseSignalClient):
    """Client connecting to signal-cli-rest-api via HTTP REST & WebSockets."""

    def __init__(self, account: str, endpoint: str):
        self.account = account
        self.endpoint = endpoint.rstrip("/")
        if not self.endpoint.startswith("http://") and not self.endpoint.startswith("https://"):
            self.endpoint = f"http://{self.endpoint}"

        self.session: Optional[aiohttp.ClientSession] = None
        self._ws_url = self.endpoint.replace("http://", "ws://").replace("https://", "wss://")
        self._running = False
        self._callback: Optional[Callable[[SignalEnvelope], Awaitable[None]]] = None

    async def connect(self) -> None:
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession()
        self._running = True
        logger.info("Initialized REST API client for endpoint %s", self.endpoint)

    async def disconnect(self) -> None:
        """Close HTTP session."""
        self._running = False
        if self.session:
            await self.session.close()
            logger.info("Closed REST API client session")

    async def list_groups(self) -> List[Dict[str, Any]]:
        """Fetch list of joined groups from signal-cli-rest-api."""
        if not self.session:
            raise RuntimeError("Client is not connected")

        url = f"{self.endpoint}/v1/groups/{self.account}"
        try:
            async with self.session.get(url) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data if isinstance(data, list) else []
        except (aiohttp.ClientConnectorError, aiohttp.ClientError) as e:
            raise ConnectionError(
                f"Could not connect to signal-cli-rest-api at '{self.endpoint}'.\n"
                f"Details: {e}\n\n"
                f"📌 Is the REST container running?\n"
                f"To start using Docker Compose:\n"
                f"  docker-compose up -d\n"
            ) from e

    async def send_message(
        self,
        recipient_group_id: str,
        message: str,
        attachments: List[str],
    ) -> bool:
        """Send message via POST /v2/send endpoint."""
        if not self.session:
            raise RuntimeError("Client is not connected")

        base64_attachments = []
        for att_path in attachments:
            p = Path(att_path)
            if p.exists():
                with open(p, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("utf-8")
                    base64_attachments.append(f"data:image/jpeg;base64,{encoded}")

        payload = {
            "number": self.account,
            "recipients": [recipient_group_id],
            "message": message,
        }
        if base64_attachments:
            payload["base64_attachments"] = base64_attachments

        url = f"{self.endpoint}/v2/send"
        try:
            async with self.session.post(url, json=payload) as resp:
                resp.raise_for_status()
                logger.info("Successfully posted message to spectator group %s", recipient_group_id)
                return True
        except Exception as e:
            logger.error("REST API send_message failed: %s", e)
            return False

    async def listen(self, callback: Callable[[SignalEnvelope], Awaitable[None]]) -> None:
        """Connect to WebSocket stream and dispatch incoming envelopes."""
        self._callback = callback
        ws_endpoint = f"{self._ws_url}/v1/receive/{self.account}"

        while self._running:
            try:
                logger.info("Connecting to Signal REST WebSocket at %s", ws_endpoint)
                async with websockets.connect(ws_endpoint) as ws:
                    logger.info("WebSocket connected. Listening for messages...")
                    async for message in ws:
                        if not self._running:
                            break
                        data = json.loads(message)
                        envelope_data = data.get("envelope") or data
                        if envelope_data and self._callback:
                            envelope = SignalEnvelope(**envelope_data)
                            await self._callback(envelope)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("WebSocket connection error: %s. Retrying in 5 seconds...", e)
                await asyncio.sleep(5.0)
