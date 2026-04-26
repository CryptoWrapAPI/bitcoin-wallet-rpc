# Tests

Test scripts for the Bitcoin Wallet RPC service. Each script targets a specific endpoint.

## Prerequisites

1. Start the server:
   ```bash
   uvicorn main:app --host 127.0.0.1 --port 8000
   ```

2. The base URL is hardcoded as `http://127.0.0.1:8000` in each script.

## Test Scripts

### `test_health.py`
Verifies the `/health` endpoint is responding correctly. No configuration needed.

### `test_history.py`
Tests the `/history` endpoint — fetches transaction history for wallet addresses.

**Setup:** Add your Bitcoin addresses (one per line) to `addrs.txt` in this directory. Lines starting with `#` are ignored.

### `test_transactions.py`
Tests the `/transactions` endpoint — fetches verbose details for transaction hashes.

**Setup:** Add transaction hashes (one per line, 64-char hex) to `tx_hashes.txt` in this directory.

### `test_derive.py`
Tests the `/derive` endpoint — derives wallet addresses from a BIP84 master private key.

**Setup:** Edit the script and set your master private key (`XPRV`, prefix `ttpv...`/`xprv...`), `ACCOUNT_INDEX`, and `ADDRESS_INDEX`.

## Running

```bash
../env12/bin/python test_health.py
../env12/bin/python test_history.py
../env12/bin/python test_transactions.py
../env12/bin/python test_derive.py
```
