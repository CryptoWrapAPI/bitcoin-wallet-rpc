import asyncio
import json
import ssl
import logging
import os
from pathlib import Path
from typing import Optional
import datetime as dt
from datetime import datetime
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from bip_utils import Bip39MnemonicGenerator, Bip39WordsNum, P2WPKHAddrDecoder
import hashlib

# Load environment variables from .env file
env_path = os.getenv("ENV_FILE", ".env")
if Path(env_path).exists():
    load_dotenv(env_path)
    env_source = f"from {env_path}"
else:
    env_source = "from system environment"

# Configure logging to use a proper logger instead of uvicorn.error
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s - %(message)s",
)
log = logging.getLogger(__name__)
log.info(f"Loaded environment {env_source}")

# Suppress overly verbose uvicorn logging
# logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
# logging.getLogger("uvicorn.error").setLevel(logging.WARNING)


# ============================================================================
# Address Conversion Utilities
# ============================================================================


def get_address_hrp() -> str:
    """Get the HRP (Human Readable Part) for addresses based on testnet flag."""
    is_testnet = os.getenv("TESTNET", "false").lower() == "true"
    return "tltc" if is_testnet else "ltc"


def address_to_scripthash(address: str) -> str:
    """
    Convert a Litecoin/Litecoin-testnet bech32 address (P2WPKH) to ElectrumX-compatible script hash.

    Args:
        address: Litecoin bech32 address (starting with ltc1 or tltc1)

    Returns:
        Script hash as hex string in little-endian format (ElectrumX format)
    """
    try:
        # Decode the bech32 address to get the witness program
        decoder = P2WPKHAddrDecoder()
        hrp = get_address_hrp()
        witness_program = decoder.DecodeAddr(address, hrp=hrp)

        # For P2WPKH, ScriptPubKey is 0x0014 + 20-byte witness program
        script_pubkey = bytes.fromhex("0014") + witness_program

        # Compute SHA256 hash of the scriptPubKey
        script_hash = hashlib.sha256(script_pubkey).digest()

        # Convert to little-endian (reverse byte order) for ElectrumX
        script_hash_le = script_hash[::-1]

        return script_hash_le.hex()
    except Exception as e:
        raise ValueError(f"Failed to convert address to script hash: {e}")


# ============================================================================
# Pydantic Models
# ============================================================================


class AddressRequest(BaseModel):
    """Request with wallet addresses instead of script hashes."""

    addresses: list[str]


class ScriptHashRequest(BaseModel):
    """Request with script hashes."""

    script_hashes: list[str]


class BalanceRequest(BaseModel):
    """Request for balance (supports both addresses and script hashes)."""

    script_hashes: Optional[list[str]] = None
    addresses: Optional[list[str]] = None

    def get_script_hashes_with_mapping(self) -> tuple[list[str], dict[str, str]]:
        """Get script hashes and address mapping, hashing only once."""
        mapping = {}
        script_hashes = []
        
        if self.script_hashes:
            script_hashes = self.script_hashes
        elif self.addresses:
            for addr in self.addresses:
                script_hash = address_to_scripthash(addr)
                script_hashes.append(script_hash)
                mapping[script_hash] = addr
        else:
            raise ValueError("Either script_hashes or addresses must be provided")
        
        return script_hashes, mapping

    def get_script_hashes(self) -> list[str]:
        """Get script hashes, converting addresses if needed (single hash operation)."""
        script_hashes, _ = self.get_script_hashes_with_mapping()
        return script_hashes

    def get_script_hash_to_address_map(self) -> dict[str, str]:
        """Get mapping of script_hash to address if addresses were provided."""
        _, mapping = self.get_script_hashes_with_mapping()
        return mapping


class SubscribeRequest(BaseModel):
    """Subscribe request."""

    script_hashes: Optional[list[str]] = None
    addresses: Optional[list[str]] = None
    webhook_url: Optional[str] = None

    def get_script_hashes_with_mapping(self) -> tuple[list[str], dict[str, str]]:
        """Get script hashes and address mapping, hashing only once."""
        mapping = {}
        script_hashes = []
        
        if self.script_hashes:
            script_hashes = self.script_hashes
        elif self.addresses:
            for addr in self.addresses:
                script_hash = address_to_scripthash(addr)
                script_hashes.append(script_hash)
                mapping[script_hash] = addr
        else:
            raise ValueError("Either script_hashes or addresses must be provided")
        
        return script_hashes, mapping

    def get_script_hashes(self) -> list[str]:
        """Get script hashes, converting addresses if needed (single hash operation)."""
        script_hashes, _ = self.get_script_hashes_with_mapping()
        return script_hashes

    def get_script_hash_to_address_map(self) -> dict[str, str]:
        """Get mapping of script_hash to address if addresses were provided."""
        _, mapping = self.get_script_hashes_with_mapping()
        return mapping


class BalanceResponse(BaseModel):
    script_hash: str
    address: Optional[str] = None
    confirmed: int
    unconfirmed: int
    confirmed_ltc: float
    unconfirmed_ltc: float
    timestamp: str


class TransactionResponse(BaseModel):
    script_hash: str
    address: Optional[str] = None
    tx_hash: str
    height: int
    fee: Optional[int] = None
    timestamp: str


# ============================================================================
# ElectrumX Client
# ============================================================================


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


# ============================================================================
# Subscription Manager
# ============================================================================


class SubscriptionManager:
    """Manages script hash subscriptions and results."""

    def __init__(self):
        self._subscribed_hashes: dict[
            str, dict
        ] = {}  # {script_hash: {webhook_url, address, ...}}
        self._hash_results: dict[str, dict] = {}  # {script_hash: balance_data}
        self._script_hash_to_address: dict[str, str] = {}  # {script_hash: address}
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger(f"{__name__}.SubscriptionManager")

    async def map_script_hash(self, script_hash: str, address: Optional[str] = None):
        """Map a script hash to its original address."""
        async with self._lock:
            if address:
                self._script_hash_to_address[script_hash] = address
                self.logger.debug(f"Mapped {script_hash} -> {address}")

    async def get_address_for_script_hash(self, script_hash: str) -> Optional[str]:
        """Get the original address for a script hash."""
        async with self._lock:
            return self._script_hash_to_address.get(script_hash)

    async def subscribe(
        self, script_hash: str, webhook_url: Optional[str] = None, electrum_client=None
    ):
        """Subscribe to updates for a script hash."""
        async with self._lock:
            if script_hash not in self._subscribed_hashes:
                self._subscribed_hashes[script_hash] = {}
                self.logger.info(f"New subscription: {script_hash}")

            if webhook_url:
                self._subscribed_hashes[script_hash]["webhook_url"] = webhook_url
                self.logger.info(f"  - Webhook: {webhook_url}")

        # Actually subscribe on the server if client is available
        if electrum_client:
            try:
                status_hash = await electrum_client.subscribe_to_scripthash(script_hash)
                async with self._lock:
                    self._subscribed_hashes[script_hash]["status_hash"] = status_hash
            except Exception as e:
                self.logger.error(
                    f"Failed to subscribe to {script_hash} on server: {e}"
                )

    async def unsubscribe(self, script_hash: str) -> bool:
        """Unsubscribe from updates for a script hash. Returns True if was subscribed."""
        async with self._lock:
            was_subscribed = False
            if script_hash in self._subscribed_hashes:
                del self._subscribed_hashes[script_hash]
                self.logger.info(f"Unsubscribed from: {script_hash}")
                was_subscribed = True
            
            # Clean up the address mapping when unsubscribing
            if script_hash in self._script_hash_to_address:
                del self._script_hash_to_address[script_hash]
                self.logger.debug(f"Cleared address mapping for: {script_hash}")
            
            return was_subscribed

    async def store_result(self, script_hash: str, result: dict):
        """Store balance result for a script hash."""
        async with self._lock:
            self._hash_results[script_hash] = result
            self.logger.info(
                f"Updated balance for {script_hash}: "
                f"{result['confirmed_ltc']:.8f} LTC confirmed, "
                f"{result['unconfirmed_ltc']:.8f} LTC unconfirmed"
            )

    async def get_result(self, script_hash: str) -> Optional[dict]:
        """Get stored result for a script hash."""
        async with self._lock:
            return self._hash_results.get(script_hash)

    async def get_all_subscribed(self) -> dict[str, dict]:
        """Get all subscribed hashes."""
        async with self._lock:
            return self._subscribed_hashes.copy()

    async def get_all_results(self) -> dict[str, dict]:
        """Get all results."""
        async with self._lock:
            return self._hash_results.copy()

    async def on_update(self, script_hash: str, result: dict):
        """Called when a subscription receives an update."""
        await self.store_result(script_hash, result)

        # Get the webhook URL if registered
        async with self._lock:
            webhook_url = self._subscribed_hashes.get(script_hash, {}).get("webhook_url")
            address = self._script_hash_to_address.get(script_hash)

        self.logger.info(
            f"[UPDATE] Script hash {script_hash[:16]}... (address: {address})"
        )
        self.logger.info(
            f"  Confirmed: {result.get('confirmed_ltc', 0):.8f} LTC, "
            f"Unconfirmed: {result.get('unconfirmed_ltc', 0):.8f} LTC"
        )

        if webhook_url:
            self.logger.info(f"[WEBHOOK] Would POST update to {webhook_url}")
            # TODO: Implement actual webhook call
        else:
            self.logger.debug(f"[UPDATE] No webhook registered for {script_hash}")


# ============================================================================
# FastAPI Application
# ============================================================================

# Global state
electrum_client: Optional[ElectrumXClient] = None
subscription_manager: Optional[SubscriptionManager] = None


async def _keepalive_loop(client: ElectrumXClient):
    """Background task: send keepalive pings to ElectrumX server."""
    log.info("[Keepalive] Starting keepalive loop (ping every 5 minutes)")
    while True:
        try:
            await asyncio.sleep(300)  # 5 minutes
            await client.ping()
        except asyncio.CancelledError:
            log.info("[Keepalive] Shutting down keepalive loop")
            break
        except Exception as e:
            log.error(f"[Keepalive] Ping failed: {e}")


async def _notification_listener(
    client: ElectrumXClient, manager: SubscriptionManager
):
    """Background task: listen for server notifications from the queue."""
    log.info("[Notifications] Starting notification listener (consuming from queue)")
    
    while True:
        try:
            # Wait for next notification from the queue (with timeout to allow cancellation)
            msg = await asyncio.wait_for(client.notification_queue.get(), timeout=60)
            
            log.debug(f"[Notifications] Processing message from queue: {msg}")
            
            # Handle server notifications
            if "method" in msg:
                method = msg["method"]
                params = msg.get("params", [])
                
                log.info(f"[Notifications] Server notification: {method}")
                
                if method == "blockchain.scripthash.subscribe":
                    # params: [script_hash, status_hash]
                    if len(params) >= 1:
                        script_hash = params[0]
                        status_hash = params[1] if len(params) > 1 else None
                        
                        log.info(
                            f"[Notifications] Balance changed for {script_hash[:16]}..., "
                            f"status: {status_hash[:16] if status_hash else 'None'}..."
                        )
                        
                        # Fetch updated balance
                        try:
                            balance = await client.get_balance(script_hash)
                            await manager.on_update(script_hash, balance)
                        except Exception as e:
                            log.error(
                                f"[Notifications] Failed to fetch balance "
                                f"for {script_hash}: {e}"
                            )
                        
        except asyncio.TimeoutError:
            log.debug("[Notifications] Queue timeout, continuing...")
        except asyncio.CancelledError:
            log.info("[Notifications] Notification listener shutting down")
            break
        except Exception as e:
            log.error(f"[Notifications] Error processing message: {e}")



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown."""
    global electrum_client, subscription_manager

    # Startup
    log.info("Starting Litecoin Wallet RPC Microservice")
    subscription_manager = SubscriptionManager()

    # ElectrumX connection is optional, can be disabled for testing
    enable_electrumx = os.getenv("ENABLE_ELECTRUMX", "true").lower() == "true"

    # Background tasks
    keepalive_task = None
    notification_task = None

    if enable_electrumx:
        electrum_host = os.getenv("ELECTRUMX_HOST")
        electrum_port = int(os.getenv("ELECTRUMX_PORT"))

        electrum_client = ElectrumXClient(host=electrum_host, port=electrum_port)

        try:
            await electrum_client.connect()
            log.info("✓ Connected to ElectrumX")
            
            # Start background tasks
            keepalive_task = asyncio.create_task(
                _keepalive_loop(electrum_client)
            )
            notification_task = asyncio.create_task(
                _notification_listener(electrum_client, subscription_manager)
            )
        except Exception as e:
            log.error(f"Failed to connect to ElectrumX: {e}")
            log.warning("Continuing without ElectrumX connection")
            electrum_client = None
    else:
        log.info("ElectrumX disabled (ENABLE_ELECTRUMX=false)")
        electrum_client = None

    yield

    # Shutdown
    log.info("Shutting down")
    
    # Cancel background tasks
    if keepalive_task:
        keepalive_task.cancel()
        try:
            await keepalive_task
        except asyncio.CancelledError:
            pass
    
    if notification_task:
        notification_task.cancel()
        try:
            await notification_task
        except asyncio.CancelledError:
            pass
    
    if electrum_client:
        await electrum_client.disconnect()


app = FastAPI(
    title="Litecoin Wallet RPC",
    description="ElectrumX-based RPC for Litecoin wallet operations",
    lifespan=lifespan,
)


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/seed")
async def generate_seed():
    """Generate a new 24-word BIP39 mnemonic."""
    mnemonic = Bip39MnemonicGenerator().FromWordsNumber(Bip39WordsNum.WORDS_NUM_24)
    return {"mnemonic": mnemonic.ToStr()}


@app.post("/balance", response_model=list[BalanceResponse])
async def get_balances(request: BalanceRequest):
    """Get balances for addresses or script hashes (batch operation, list-first)."""
    if not electrum_client:
        raise HTTPException(status_code=503, detail="ElectrumX not connected")

    try:
        script_hashes = request.get_script_hashes()
        hash_to_addr = request.get_script_hash_to_address_map()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Store the address mappings
    for script_hash, address in hash_to_addr.items():
        await subscription_manager.map_script_hash(script_hash, address)

    results = []
    for script_hash in script_hashes:
        try:
            result = await electrum_client.get_balance(script_hash)
            
            # Get the original address if available
            address = await subscription_manager.get_address_for_script_hash(script_hash)
            result["address"] = address
            
            await subscription_manager.store_result(script_hash, result)
            results.append(result)
        except Exception as e:
            log.error(f"Error querying {script_hash}: {e}")
            address = await subscription_manager.get_address_for_script_hash(script_hash)
            results.append(
                {
                    "script_hash": script_hash,
                    "address": address,
                    "confirmed": 0,
                    "unconfirmed": 0,
                    "confirmed_ltc": 0.0,
                    "unconfirmed_ltc": 0.0,
                    "timestamp": datetime.now(dt.timezone.utc).isoformat(),
                    "error": str(e),
                }
            )

    return results


@app.post("/history", response_model=list[TransactionResponse])
async def get_history_batch(request: BalanceRequest):
    """Get transaction history for addresses or script hashes (batch operation, list-first)."""
    if not electrum_client:
        raise HTTPException(status_code=503, detail="ElectrumX not connected")

    try:
        script_hashes = request.get_script_hashes()
        hash_to_addr = request.get_script_hash_to_address_map()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Store the address mappings
    for script_hash, address in hash_to_addr.items():
        await subscription_manager.map_script_hash(script_hash, address)

    all_results = []
    for script_hash in script_hashes:
        try:
            results = await electrum_client.get_history(script_hash)
            # Get the original address if available
            address = await subscription_manager.get_address_for_script_hash(script_hash)
            # Add address to each result
            for result in results:
                result["address"] = address
            all_results.extend(results)
        except Exception as e:
            log.error(f"Error querying history for {script_hash}: {e}")

    return all_results


@app.post("/subscribe")
async def subscribe(request: SubscribeRequest):
    """Subscribe to updates for addresses or script hashes (batch operation)."""
    if not subscription_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    if not electrum_client:
        raise HTTPException(status_code=503, detail="ElectrumX not connected")

    try:
        script_hashes = request.get_script_hashes()
        hash_to_addr = request.get_script_hash_to_address_map()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Store the address mappings
    for script_hash, address in hash_to_addr.items():
        await subscription_manager.map_script_hash(script_hash, address)

    # Subscribe to all hashes in parallel using asyncio.gather
    async def subscribe_one(script_hash: str):
        await subscription_manager.subscribe(
            script_hash, request.webhook_url, electrum_client=electrum_client
        )
        return script_hash
    
    # Execute all subscriptions concurrently
    subscribed = await asyncio.gather(
        *[subscribe_one(sh) for sh in script_hashes],
        return_exceptions=False
    )

    return {
        "status": "subscribed",
        "script_hashes": subscribed,
        "webhook_url": request.webhook_url,
        "message": "In production, updates would be sent to the webhook URL",
    }



@app.delete("/subscribe")
async def unsubscribe_batch(request: BalanceRequest):
    """Unsubscribe from updates for addresses or script hashes (batch operation)."""
    if not subscription_manager:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        script_hashes = request.get_script_hashes()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Unsubscribe all in parallel
    async def unsubscribe_one(script_hash: str):
        was_subscribed = await subscription_manager.unsubscribe(script_hash)
        return {"script_hash": script_hash, "was_subscribed": was_subscribed}
    
    unsubscribed = await asyncio.gather(
        *[unsubscribe_one(sh) for sh in script_hashes],
        return_exceptions=False
    )

    return {
        "status": "unsubscribed",
        "script_hashes": [item["script_hash"] for item in unsubscribed],
        "details": unsubscribed,
    }


@app.get("/subscriptions")
async def list_subscriptions():
    """List all active subscriptions."""
    if not subscription_manager:
        raise HTTPException(status_code=503, detail="Service not ready")

    subscribed = await subscription_manager.get_all_subscribed()
    results = await subscription_manager.get_all_results()

    return {
        "total_subscriptions": len(subscribed),
        "subscribed_hashes": list(subscribed.keys()),
        "results": results,
    }


@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "electrum_connected": electrum_client is not None
        and electrum_client.reader is not None,
        "timestamp": datetime.now(dt.timezone.utc).isoformat(),
    }
