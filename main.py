"""Simple Litecoin Wallet RPC - MVP with get_history only."""

import asyncio
import json
import ssl
import logging
import os
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
import hashlib

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from bip_utils import P2WPKHAddrDecoder
from contextlib import asynccontextmanager


# ============================================================================
# Configuration
# ============================================================================

env_path = os.getenv("ENV_FILE", ".env")
if Path(env_path).exists():
    load_dotenv(env_path)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)-8s] %(name)s - %(message)s",
)
log = logging.getLogger(__name__)

# Environment variables
ELECTRUMX_URL = os.getenv("ELECTRUMX_URL", "ssl://localhost:50002")
IS_TESTNET = os.getenv("TESTNET", "false").lower() == "true"
ADDRESS_HRP = "tltc" if IS_TESTNET else "ltc"

log.info(f"Config: ElectrumX={ELECTRUMX_URL}, Testnet={IS_TESTNET}, HRP={ADDRESS_HRP}")


# ============================================================================
# Utilities
# ============================================================================

def address_to_scripthash(address: str) -> str:
    """Convert Litecoin bech32 address to ElectrumX script hash."""
    try:
        log.debug(f"Converting address {address} to script hash")
        decoder = P2WPKHAddrDecoder()
        witness_program = decoder.DecodeAddr(address, hrp=ADDRESS_HRP)
        script_pubkey = bytes.fromhex("0014") + witness_program
        script_hash = hashlib.sha256(script_pubkey).digest()[::-1]
        result = script_hash.hex()
        log.debug(f"  -> {result}")
        return result
    except Exception as e:
        log.error(f"Failed to convert address {address}: {e}")
        raise ValueError(f"Invalid address {address}: {e}")


# ============================================================================
# Pydantic Models
# ============================================================================

class HistoryRequest(BaseModel):
    """Request for transaction history."""
    addresses: list[str]


class TransactionsRequest(BaseModel):
    """Request for transaction details."""
    tx_hashes: list[str]


# ============================================================================
# ElectrumX Client
# ============================================================================

class ElectrumXClient:
    """Simple ElectrumX TCP/SSL client for history queries."""

    def __init__(self, url: str):
        self.url = url
        self.protocol, self.host, self.port = self._parse_url(url)
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.request_id_counter = 0
        self.read_lock = asyncio.Lock()
        self.logger = logging.getLogger(f"{__name__}.ElectrumXClient")
        self.connected = False

    def _parse_url(self, url: str) -> tuple[str, str, int]:
        """Parse connection URL like ssl://host:port or tcp://host:port."""
        if "://" not in url:
            raise ValueError(f"Invalid URL format. Expected protocol://host:port, got: {url}")
        
        protocol, rest = url.split("://", 1)
        protocol = protocol.lower()
        
        if protocol not in ("ssl", "tcp"):
            raise ValueError(f"Unsupported protocol '{protocol}'. Use 'ssl' or 'tcp'")
        
        if ":" not in rest:
            raise ValueError(f"Missing port in URL. Expected host:port, got: {rest}")
        
        host, port_str = rest.rsplit(":", 1)
        
        try:
            port = int(port_str)
        except ValueError:
            raise ValueError(f"Invalid port number: {port_str}")
        
        return protocol, host, port

    async def connect(self):
        """Connect to ElectrumX server."""
        try:
            self.logger.info(f"Connecting to {self.url} ({self.protocol.upper()})")

            if self.protocol == "ssl":
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                self.reader, self.writer = await asyncio.open_connection(
                    self.host, self.port, ssl=context
                )
            else:  # tcp
                self.reader, self.writer = await asyncio.open_connection(
                    self.host, self.port
                )
            
            self.logger.info(f"✓ Connected to {self.url}")
            
            # Handshake
            response = await self._send_request("server.version", ["wallet-rpc", "1.4"], request_id=0)
            if "error" in response:
                raise RuntimeError(f"Handshake failed: {response['error']}")
            
            server_info = response.get("result", [])
            self.logger.info(f"✓ Handshake OK - Server: {server_info[0] if server_info else 'Unknown'}, Protocol: {server_info[1] if len(server_info) > 1 else 'Unknown'}")
            
            self.connected = True
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self.connected = False
            raise

    async def disconnect(self):
        """Disconnect from server."""
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
                self.logger.info("Disconnected")
            except Exception as e:
                self.logger.warning(f"Error disconnecting: {e}")
            finally:
                self.connected = False

    async def _send_request(self, method: str, params: Optional[list] = None, request_id: Optional[int] = None) -> dict:
        """Send JSON-RPC request and wait for response."""
        if params is None:
            params = []
        if request_id is None:
            self.request_id_counter += 1
            request_id = self.request_id_counter

        request = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        raw_request = json.dumps(request).encode("utf-8") + b"\n"
        
        self.logger.debug(f">>> Sending: {method} (id={request_id})")

        async with self.read_lock:
            self.writer.write(raw_request)
            await self.writer.drain()

            # Read response
            buffer = b""
            while True:
                if b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if line.strip():
                        try:
                            msg = json.loads(line.decode("utf-8"))
                            self.logger.debug(f"<<< Received: {json.dumps(msg)}")
                            msg_id = msg.get("id")

                            if msg_id == request_id:
                                return msg
                            else:
                                self.logger.warning(f"[UNEXPECTED] Got id={msg_id}, expected {request_id}: {json.dumps(msg)}")
                        except json.JSONDecodeError as e:
                            self.logger.error(f"JSON decode error: {e}")

                try:
                    chunk = await asyncio.wait_for(self.reader.read(4096), timeout=30)
                except asyncio.TimeoutError:
                    raise RuntimeError("Timeout waiting for response")

                if not chunk:
                    raise ConnectionError("Server closed connection")

                buffer += chunk
                self.logger.debug(f"[BUFFER] Received {len(chunk)} bytes")

    async def get_history(self, script_hash: str) -> list[dict]:
        """Get transaction history for a script hash."""
        self.logger.debug(f"Fetching history for {script_hash[:16]}...")
        
        response = await self._send_request("blockchain.scripthash.get_history", [script_hash])
        
        if "error" in response:
            raise RuntimeError(f"History query failed: {response['error']}")
        
        history = response.get("result", [])
        self.logger.info(f"✓ Got {len(history)} transactions for {script_hash[:16]}...")
        return history

    async def _batch_requests(self, requests_list: list[tuple]) -> list[dict]:
        """Send multiple requests in batch and read all responses.
        
        Args:
            requests_list: List of (method, params, request_id) tuples
            
        Returns:
            List of responses indexed by request_id
        """
        self.logger.debug(f"Batch sending {len(requests_list)} requests")
        
        # Build all requests
        raw_requests = []
        request_ids = set()
        for method, params, request_id in requests_list:
            request = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
            raw_request = json.dumps(request).encode("utf-8") + b"\n"
            raw_requests.append(raw_request)
            request_ids.add(request_id)
            self.logger.debug(f"  [{request_id}] {method}")

        # Send all at once
        async with self.read_lock:
            for raw_request in raw_requests:
                self.writer.write(raw_request)
            await self.writer.drain()
            self.logger.debug(f"✓ Sent {len(raw_requests)} requests in batch")

            # Now read all responses
            responses = {}
            buffer = b""
            expected_count = len(requests_list)
            received_count = 0

            while received_count < expected_count:
                if b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if line.strip():
                        try:
                            msg = json.loads(line.decode("utf-8"))
                            self.logger.debug(f"<<< Received: {json.dumps(msg)[:100]}...")
                            msg_id = msg.get("id")

                            if msg_id in request_ids:
                                responses[msg_id] = msg
                                received_count += 1
                                self.logger.debug(f"    ✓ Counted! Now {received_count}/{expected_count}")
                                
                                # Check if we have all responses - break immediately
                                if received_count >= expected_count:
                                    self.logger.debug(f"✓ Got all {expected_count} responses, exiting read loop")
                                    break
                                    
                            else:
                                self.logger.warning(f"[UNEXPECTED] {json.dumps(msg)[:100]}...")
                        except json.JSONDecodeError as e:
                            self.logger.error(f"JSON decode error: {e}")

                # Only try to read more if we still need responses
                if received_count >= expected_count:
                    break
                    
                try:
                    chunk = await asyncio.wait_for(self.reader.read(4096), timeout=30)
                except asyncio.TimeoutError:
                    self.logger.error(f"Timeout: got {received_count}/{expected_count} responses")
                    raise RuntimeError(f"Timeout waiting for batch responses (got {received_count}/{expected_count})")

                if not chunk:
                    if received_count >= expected_count:
                        break
                    self.logger.error(f"Connection closed: got {received_count}/{expected_count} responses")
                    raise ConnectionError(f"Server closed connection after {received_count}/{expected_count} responses")

                buffer += chunk
                self.logger.debug(f"[BUFFER] Received {len(chunk)} bytes, have {received_count}/{expected_count} responses")

        self.logger.debug(f"✓ Batch complete: got all {expected_count} responses")
        return [responses.get(req[2]) for req in requests_list]

    async def get_transactions(self, tx_hashes: list[str]) -> list[dict]:
        """Get verbose transaction details for multiple transaction hashes in batch."""
        self.logger.info(f"Fetching details for {len(tx_hashes)} transactions")
        
        # Prepare batch requests
        batch = []
        for tx_hash in tx_hashes:
            self.request_id_counter += 1
            batch.append(("blockchain.transaction.get", [tx_hash, True], self.request_id_counter))
        
        # Send batch
        responses = await self._batch_requests(batch)
        
        # Process responses
        results = []
        for (method, params, req_id), response in zip(batch, responses):
            tx_hash = params[0]
            
            if response is None:
                self.logger.error(f"No response for {tx_hash[:16]}...")
                results.append({"tx_hash": tx_hash, "error": "No response from server"})
            elif "error" in response:
                self.logger.error(f"Error for {tx_hash[:16]}...: {response['error']}")
                results.append({"tx_hash": tx_hash, "error": str(response['error'])})
            else:
                tx_data = response.get("result", {})
                # Add tx_hash to the result
                tx_data["tx_hash"] = tx_hash
                self.logger.info(f"✓ Got transaction {tx_hash[:16]}...")
                results.append(tx_data)
        
        return results


# ============================================================================
# Global State
# ============================================================================

electrum_client: Optional[ElectrumXClient] = None


# ============================================================================
# FastAPI Lifespan
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown."""
    global electrum_client
    
    log.info("Starting Litecoin Wallet RPC (MVP)")
    
    # Connect to ElectrumX
    electrum_client = ElectrumXClient(ELECTRUMX_URL)
    try:
        await electrum_client.connect()
        yield
        await electrum_client.disconnect()
    except Exception as e:
        log.error(f"Failed to connect to ElectrumX: {e}")
        raise


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(title="Litecoin Wallet RPC", lifespan=lifespan)


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy" if electrum_client and electrum_client.connected else "unhealthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/history")
async def get_history(request: HistoryRequest):
    """Get transaction history for addresses."""
    if not electrum_client:
        raise HTTPException(status_code=503, detail="ElectrumX not connected")
    
    log.info(f"History request for {len(request.addresses)} addresses")
    
    # Convert addresses to script hashes
    script_hashes = []
    addr_to_hash = {}
    for addr in request.addresses:
        try:
            script_hash = address_to_scripthash(addr)
            script_hashes.append(script_hash)
            addr_to_hash[script_hash] = addr
        except ValueError as e:
            log.error(f"Invalid address {addr}: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    # Get history
    response = {}
    for script_hash in script_hashes:
        address = addr_to_hash[script_hash]
        try:
            history = await electrum_client.get_history(script_hash)
            response[address] = {
                "transactions": history,
                "count": len(history),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except ConnectionError as e:
            # Connection error - try to reconnect once
            log.warning(f"Connection lost: {e}, attempting to reconnect...")
            try:
                await electrum_client.disconnect()
                await electrum_client.connect()
                # Retry the query
                history = await electrum_client.get_history(script_hash)
                response[address] = {
                    "transactions": history,
                    "count": len(history),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            except Exception as retry_error:
                log.error(f"Reconnection failed: {retry_error}")
                raise HTTPException(
                    status_code=503, 
                    detail=f"Failed to connect to ElectrumX: {retry_error}"
                )
        except Exception as e:
            # Other errors - return them
            log.error(f"Error fetching history for {address}: {e}")
            raise HTTPException(status_code=500, detail=f"Error querying ElectrumX: {e}")
    
    return response


@app.post("/transactions")
async def get_transactions(request: TransactionsRequest):
    """Get verbose transaction details for transaction hashes."""
    if not electrum_client:
        raise HTTPException(status_code=503, detail="ElectrumX not connected")
    
    log.info(f"Transactions request for {len(request.tx_hashes)} hashes")
    
    # Validate tx hashes
    for tx_hash in request.tx_hashes:
        if not isinstance(tx_hash, str) or len(tx_hash) != 64:
            log.error(f"Invalid tx_hash: {tx_hash}")
            raise HTTPException(status_code=400, detail=f"Invalid tx_hash: {tx_hash} (must be 64-char hex string)")
    
    # Get transactions
    try:
        transactions = await electrum_client.get_transactions(request.tx_hashes)
        
        response = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(transactions),
            "transactions": transactions
        }
        
        return response
        
    except ConnectionError as e:
        # Connection error - try to reconnect once
        log.warning(f"Connection lost: {e}, attempting to reconnect...")
        try:
            await electrum_client.disconnect()
            await electrum_client.connect()
            # Retry the query
            transactions = await electrum_client.get_transactions(request.tx_hashes)
            
            response = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "count": len(transactions),
                "transactions": transactions
            }
            
            return response
        except Exception as retry_error:
            log.error(f"Reconnection failed: {retry_error}")
            raise HTTPException(
                status_code=503, 
                detail=f"Failed to connect to ElectrumX: {retry_error}"
            )
    except Exception as e:
        # Other errors - return them
        log.error(f"Error fetching transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Error querying ElectrumX: {e}")
