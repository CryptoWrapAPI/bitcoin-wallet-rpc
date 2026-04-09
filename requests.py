"""On-demand request handlers for balance and history queries."""

import logging
from datetime import datetime
import datetime as dt

from fastapi import HTTPException
from config import BalanceRequest, BalanceResponse, TransactionResponse


log = logging.getLogger(__name__)


async def get_balances_handler(
    request: BalanceRequest, electrum_client, subscription_manager
) -> list[BalanceResponse]:
    """Get balances for addresses or script hashes (batch operation)."""
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


async def get_history_handler(
    request: BalanceRequest, electrum_client, subscription_manager
) -> list[TransactionResponse]:
    """Get transaction history for addresses or script hashes (batch operation)."""
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
