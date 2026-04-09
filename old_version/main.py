"""Litecoin Wallet RPC Microservice - Main FastAPI Application."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from bip_utils import Bip39MnemonicGenerator, Bip39WordsNum

from config import log, BalanceRequest, SubscribeRequest
from client import ElectrumXClient
from subscriptions import SubscriptionManager
from requests import get_balances_handler, get_history_handler


# ============================================================================
# Global State
# ============================================================================

electrum_client: ElectrumXClient | None = None
subscription_manager: SubscriptionManager | None = None


# ============================================================================
# Background Tasks
# ============================================================================


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


# ============================================================================
# FastAPI Lifespan
# ============================================================================


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
    
    # Close ElectrumX connection
    if electrum_client:
        await electrum_client.disconnect()


# ============================================================================
# FastAPI Application
# ============================================================================

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


@app.post("/balance")
async def get_balances(request: BalanceRequest):
    """Get balances for addresses or script hashes (batch operation)."""
    return await get_balances_handler(request, electrum_client, subscription_manager)


@app.post("/history")
async def get_history_batch(request: BalanceRequest):
    """Get transaction history for addresses or script hashes (batch operation)."""
    return await get_history_handler(request, electrum_client, subscription_manager)


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
async def health_check():
    """Health check endpoint."""
    if not subscription_manager:
        return {"status": "unhealthy", "error": "Service not ready"}

    return {
        "status": "healthy",
        "electrum_connected": electrum_client is not None,
        "timestamp": str(__import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat()),
    }
