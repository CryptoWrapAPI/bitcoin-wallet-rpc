"""ElectrumX client with persistent TCP/SSL connection."""

import asyncio
import json
import ssl
import logging
from typing import Optional
from datetime import datetime
import datetime as dt


class ElectrumXClient:
    """Persistent TCP/SSL connection to ElectrumX server with request queueing."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.request_id_counter = 0
        self._read_lock: Optional[asyncio.Lock] = None
        self.notification_queue: Optional[asyncio.Queue] = None
        self.logger = logging.getLogger(f"{__name__}.ElectrumXClient")

    async def connect(self):
        """Establish SSL connection to ElectrumX server."""
        try:
            # Initialize async primitives (must be done in event loop context)
            self._read_lock = asyncio.Lock()
            self.notification_queue = asyncio.Queue(maxsize=100)
            
            self.logger.info(f"Connecting to ElectrumX at {self.host}:{self.port}")

            # Create SSL context
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            # Connect with asyncio
            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port, ssl=context
            )

            self.logger.info(f"Connected to {self.host}:{self.port}")

            # Perform handshake
            await self._handshake()

        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            raise

    async def disconnect(self):
        """Close connection."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.logger.info("Disconnected from ElectrumX")

    async def _handshake(self):
        """Send server.version handshake."""
        response = await self._send_request(
            "server.version", ["litecoin-wallet-rpc", "1.4"], request_id=0
        )

        if "error" in response:
            raise RuntimeError(f"Handshake failed: {response['error']}")

        server_info = response["result"]
        self.logger.info(
            f"Handshake OK - Server: {server_info[0]}, Protocol: {server_info[1]}"
        )

    async def _send_request(
        self,
        method: str,
        params: Optional[list] = None,
        request_id: Optional[int] = None,
    ):
        """Send JSON-RPC request and wait for matching response."""
        if params is None:
            params = []

        if request_id is None:
            self.request_id_counter += 1
            request_id = self.request_id_counter

        request = {"id": request_id, "method": method, "params": params}

        raw_request = json.dumps(request).encode("utf-8") + b"\n"

        self.logger.debug(f">>> Sending {method} (id={request_id})")
        
        async with self._read_lock:
            self.writer.write(raw_request)
            await self.writer.drain()

            # Read responses until we get one matching our request_id
            buffer = b""
            while True:
                if b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if line.strip():
                        try:
                            msg = json.loads(line.decode("utf-8"))
                            msg_id = msg.get("id")

                            if msg_id == request_id:
                                self.logger.debug(
                                    f"<<< Received response (id={request_id})"
                                )
                                return msg
                            elif "method" in msg:
                                # Server notification - queue it for processing
                                self.logger.info(
                                    f"[Notification] {msg.get('method')} - {msg.get('params')}"
                                )
                                try:
                                    self.notification_queue.put_nowait(msg)
                                except asyncio.QueueFull:
                                    self.logger.warning("Notification queue full, dropping message")
                            else:
                                self.logger.warning(f"[Unexpected] {json.dumps(msg)}")
                        except json.JSONDecodeError as e:
                            self.logger.error(f"Failed to parse JSON: {e}")

                try:
                    chunk = await asyncio.wait_for(
                        self.reader.read(4096), timeout=30
                    )
                except asyncio.TimeoutError:
                    raise RuntimeError("Timeout waiting for response")

                if not chunk:
                    raise ConnectionError("Server closed the connection")

                buffer += chunk

    async def get_balance(self, script_hash: str) -> dict:
        """Get balance for a script hash."""
        response = await self._send_request(
            "blockchain.scripthash.get_balance", [script_hash]
        )

        if "error" in response:
            raise RuntimeError(f"Balance query failed: {response['error']}")

        result = response["result"]
        confirmed = result.get("confirmed", 0)
        unconfirmed = result.get("unconfirmed", 0)

        return {
            "script_hash": script_hash,
            "confirmed": confirmed,
            "unconfirmed": unconfirmed,
            "confirmed_ltc": confirmed / 1e8,
            "unconfirmed_ltc": unconfirmed / 1e8,
            "timestamp": datetime.now(dt.timezone.utc).isoformat(),
        }

    async def get_history(self, script_hash: str) -> list[dict]:
        """Get transaction history for a script hash."""
        response = await self._send_request(
            "blockchain.scripthash.get_history", [script_hash]
        )

        if "error" in response:
            raise RuntimeError(f"History query failed: {response['error']}")

        history = response["result"]
        return [
            {
                "script_hash": script_hash,
                "tx_hash": tx["tx_hash"],
                "height": tx.get("height", -1),
                "fee": tx.get("fee"),
                "timestamp": datetime.now(dt.timezone.utc).isoformat(),
            }
            for tx in history
        ]

    async def subscribe_to_scripthash(self, script_hash: str) -> str:
        """Subscribe to updates for a script hash. Returns status hash."""
        self.logger.info(f"Subscribing to script hash: {script_hash}")
        response = await self._send_request(
            "blockchain.scripthash.subscribe", [script_hash]
        )

        if "error" in response:
            raise RuntimeError(f"Subscription failed: {response['error']}")

        # Returns the status hash (changes when balance/history changes)
        status_hash = response["result"]
        self.logger.info(f"Successfully subscribed to {script_hash}, status: {status_hash}")
        return status_hash

    async def ping(self) -> None:
        """Send keepalive ping to server."""
        self.logger.debug("Sending keepalive ping to server")
        response = await self._send_request("server.ping", [])

        if "error" in response:
            self.logger.warning(f"Ping error: {response['error']}")
        else:
            self.logger.debug("Ping successful")
