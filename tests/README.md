# Test Suite for Litecoin Wallet RPC

This directory contains integration tests for the Litecoin Wallet RPC microservice.

## Setup

All tests use script hashes from `script_hashes.txt`. Update this file with your own script hashes:

```bash
# script_hashes.txt (one per line)
04fbd6d7ac5c54aedcb91084b7c774531089223a7f06d428606c3602e9f96523
1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890
```

## Running Tests

Make sure the FastAPI server is running:

```bash
cd ..
fastapi dev
```

Then in another terminal, run the tests:

### 1. Basic API Test (Health Check)

```bash
./test_api.sh
```

Tests basic endpoints like `/health`, `/seed`, and error handling.

### 2. Balance & History Endpoints

```bash
./test_balance_and_history.sh
```

Tests:
- `POST /balance` - Get balances for multiple script hashes
- `POST /history` - Get transaction history for multiple script hashes
- Verifies ElectrumX connection status

### 3. Subscription Workflow

**Step 1: Subscribe to script hashes**

```bash
./test_subscribe.sh
```

Tests:
- `POST /subscribe` - Subscribe to updates without webhook
- `POST /subscribe` - Subscribe with webhook URL
- `GET /subscriptions` - List all active subscriptions

**Step 2: Unsubscribe from script hashes**

```bash
./test_unsubscribe.sh
```

Tests:
- `DELETE /subscribe` - Unsubscribe from updates (batch operation)
- Verifies subscriptions are removed

### 4. Full Workflow Test (Legacy)

```bash
./test_subscription_workflow.sh
```

Complete end-to-end subscription workflow in a single script.

## Test Features

- **Batch operations**: All endpoints use list-first design
- **Dynamic script hashes**: Loaded from `script_hashes.txt` file
- **Color output**: Easy to read test results
- **Error handling**: Tests include error cases
- **JSON output**: All responses are pretty-printed with `jq`

## Example Script Hashes

To get real script hashes for testing, you can use:

```python
import hashlib
from electrumx.lib.address import address_to_scripthash

address = "ltc1qexample..."
script_hash = address_to_scripthash(address)
print(script_hash)
```

Or convert an address using the Electrum protocol directly:

```bash
# Check the dev_examples for detailed examples
cd ../dev_examples
python3 query_balance_extensive_debug_logging.py
```
