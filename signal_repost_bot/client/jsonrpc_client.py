"""Async JSON-RPC client for signal-cli socket/stdio connection."""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Callable, Awaitable, Dict, Any, Optional
from signal_repost_bot.client.base import BaseSignalClient
from signal_repost_bot.models import SignalEnvelope, JsonRpcResponse

logger = logging.getLogger(__name__)


class JsonRpcSignalClient(BaseSignalClient):
    """Client connecting to `signal-cli daemon` over TCP socket or Unix Domain socket."""

    def __init__(self, account: str, endpoint: str):
        self.account = account
        self.endpoint = endpoint
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._running = False
        self._callback: Optional[Callable[[SignalEnvelope], Awaitable[None]]] = None

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def connect(self) -> None:
        """Establish TCP socket or Unix Domain socket connection with a 64MB buffer limit."""
        # Allow up to 64MB lines for large JSON responses containing group metadata/avatars
        max_buffer = 64 * 1024 * 1024

        try:
            if ":" in self.endpoint:
                host, port = self.endpoint.split(":", 1)
                logger.info("Connecting to signal-cli TCP socket at %s:%s", host, port)
                self.reader, self.writer = await asyncio.open_connection(
                    host, int(port), limit=max_buffer
                )
            else:
                logger.info("Connecting to signal-cli Unix domain socket at %s", self.endpoint)
                self.reader, self.writer = await asyncio.open_unix_connection(
                    self.endpoint, limit=max_buffer
                )
        except (ConnectionRefusedError, FileNotFoundError, OSError) as e:
            raise ConnectionError(
                f"Could not connect to signal-cli daemon at '{self.endpoint}'.\n"
                f"Details: {e}\n\n"
                f"📌 Is signal-cli daemon running?\n"
                f"To start signal-cli in JSON-RPC socket mode:\n"
                f"  signal-cli -u {self.account} daemon --tcp {self.endpoint}\n\n"
                f"Or if using Docker Compose (REST API mode):\n"
                f"  1. Set 'client_mode: rest_api' and 'endpoint: http://127.0.0.1:8080' in config.yaml\n"
                f"  2. Run 'docker-compose up -d'\n"
            ) from e

        self._running = True
        asyncio.create_task(self._read_loop())
        logger.info("Connected to signal-cli daemon")

    async def disconnect(self) -> None:
        """Close connection."""
        self._running = False
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            logger.info("Disconnected from signal-cli daemon")

    async def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        if not self.writer:
            raise RuntimeError("Client is not connected to signal-cli daemon")

        req_id = self._next_id()
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {"account": self.account, **(params or {})},
            "id": req_id,
        }

        fut = asyncio.get_event_loop().create_future()
        self._pending_requests[req_id] = fut

        line = json.dumps(payload) + "\n"
        self.writer.write(line.encode("utf-8"))
        await self.writer.drain()

        return await asyncio.wait_for(fut, timeout=30.0)

    async def list_groups(self) -> List[Dict[str, Any]]:
        """List joined groups from signal-cli."""
        res = await self._send_request("listGroups")
        if isinstance(res, list):
            return res
        return []

    async def send_message(
        self,
        recipient_group_id: str,
        message: str,
        attachments: List[str],
    ) -> bool:
        """Send a message with attachments to a group."""
        params: Dict[str, Any] = {
            "groupId": recipient_group_id,
            "message": message,
        }
        if attachments:
            params["attachments"] = attachments

        try:
            res = await self._send_request("send", params)
            logger.info("Successfully sent message to group %s (result: %s)", recipient_group_id, res)
            return True
        except Exception as e:
            logger.error("Failed to send message to group %s: %s", recipient_group_id, e)
            return False

    async def listen(self, callback: Callable[[SignalEnvelope], Awaitable[None]]) -> None:
        """Set callback and block until disconnect."""
        self._callback = callback
        while self._running:
            await asyncio.sleep(1.0)

    async def _read_line_chunked(self) -> bytes:
        """Read line chunks safely even if single payload exceeds standard stream buffer limits."""
        if not self.reader:
            return b""
        chunks = []
        while True:
            try:
                chunk = await self.reader.readline()
                if not chunk:
                    return b"".join(chunks)
                chunks.append(chunk)
                if chunk.endswith(b"\n"):
                    return b"".join(chunks)
            except asyncio.LimitOverrunError as e:
                chunk = await self.reader.read(e.consumed)
                chunks.append(chunk)

    async def _read_loop(self) -> None:
        """Read incoming JSON lines from signal-cli socket."""
        while self._running and self.reader:
            try:
                line_bytes = await self._read_line_chunked()
                if not line_bytes:
                    logger.warning("Signal socket connection closed by server")
                    break

                text = line_bytes.decode("utf-8").strip()
                if not text:
                    continue

                data = json.loads(text)
                await self._process_incoming_json(data)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in signal-cli read loop: %s", e, exc_info=True)

    async def _process_incoming_json(self, data: Dict[str, Any]) -> None:
        """Route responses and notifications."""
        # 1. Handle JSON-RPC response to a pending request ID
        req_id = data.get("id")
        if req_id in self._pending_requests:
            fut = self._pending_requests.pop(req_id)
            if "error" in data:
                fut.set_exception(RuntimeError(data["error"]))
            else:
                fut.set_result(data.get("result"))
            return

        # 2. Handle JSON-RPC incoming notification or receive method
        envelope_data = None
        if "envelope" in data:
            envelope_data = data["envelope"]
        elif data.get("method") == "receive" and "params" in data:
            params = data["params"]
            if "envelope" in params:
                envelope_data = params["envelope"]
            elif "result" in params and isinstance(params["result"], dict) and "envelope" in params["result"]:
                envelope_data = params["result"]["envelope"]

        if envelope_data and self._callback:
            try:
                envelope = SignalEnvelope(**envelope_data)
                self._resolve_attachment_paths(envelope)
                await self._callback(envelope)
            except Exception as e:
                logger.error("Error processing incoming envelope: %s", e, exc_info=True)

    def _resolve_attachment_paths(self, envelope: SignalEnvelope) -> None:
        """Ensure attachment path fields point to accessible local files."""
        if not envelope.dataMessage or not envelope.dataMessage.attachments:
            return

        home = Path.home()
        # Common directories where signal-cli stores downloaded attachments
        search_dirs = [
            home / ".local/share/signal-cli/data/attachments",
            home / ".local/share/signal-cli/attachments",
            home / ".config/signal-cli/data/attachments",
            home / ".config/signal-cli/attachments",
            Path("/var/lib/signal-cli/data/attachments"),
            Path("./data/attachments"),
        ]

        # Also search inside any subdirectory in ~/.local/share/signal-cli
        signal_base = home / ".local/share/signal-cli"
        if signal_base.exists():
            for p in signal_base.rglob("attachments"):
                if p.is_dir() and p not in search_dirs:
                    search_dirs.append(p)

        for att in envelope.dataMessage.attachments:
            # Check if att.path is already valid and exists
            if att.path and Path(att.path).exists():
                att.path = str(Path(att.path).resolve())
                continue

            # Candidate identifiers to search for
            identifiers = [
                x for x in [att.path, att.id, att.storedFilename, att.filename, att.customFilename]
                if x
            ]

            found = False
            for ident in identifiers:
                ident_path = Path(ident)
                if ident_path.is_absolute() and ident_path.exists():
                    att.path = str(ident_path.resolve())
                    found = True
                    break

                # Search across all candidate attachment directories
                for d in search_dirs:
                    if not d.exists():
                        continue
                    # Check exact filename / ID match
                    candidate = d / ident
                    if candidate.exists() and candidate.is_file():
                        att.path = str(candidate.resolve())
                        found = True
                        break
                    # Check partial/prefixed match e.g. "12345-filename.jpg" or "12345"
                    try:
                        for f in d.iterdir():
                            if f.is_file() and (ident in f.name or f.name.startswith(ident)):
                                att.path = str(f.resolve())
                                found = True
                                break
                    except Exception:
                        pass
                    if found:
                        break
                if found:
                    break

            if att.path:
                logger.info("Resolved attachment [%s] -> %s", att.id or att.filename, att.path)
            else:
                logger.warning("Could not resolve local file path for attachment ID=%s filename=%s", att.id, att.filename)
