"""Subscription management and notification handling."""

import asyncio
import logging
from typing import Optional


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
