# Litecoin Wallet RPC - MVP

Simple FastAPI microservice to query Litecoin data from ElectrumX servers.

## Features (MVP)

- ✅ Get transaction history for wallet addresses (batch operation)
- ✅ Get verbose transaction details for tx hashes (batch operation)
- ✅ Health check endpoint
- ✅ Address-to-script-hash conversion (P2WPKH)
- ✅ Support for testnet and mainnet
- ✅ Comprehensive error handling and logging
- ✅ Connection recovery (1 reconnection attempt on failure)

## Future Features

- Subscribe/unsubscribe to address notifications (requires ElectrumX v1.4.2+)
- Keepalive pings to maintain long-lived connections
- WebSocket support for real-time updates
- Webhook notifications for blockchain events

## Setup

1. Create `.env` file:
   ```
   ELECTRUMX_HOST=electrum.ltc.xurious.com
   ELECTRUMX_PORT=51002
   TESTNET=true
   ENV_FILE=.env
   ```

2. Paste wallet addresses into `addrs.txt` (one per line):
   ```
   tltc1qk8yyn8v267d5sr2tum8tq7djxdqf0vulhth62y
   tltc1qg9dvsx67z38uwzl4xvucktdc5tx66xgduykar4
   ```

3. Paste transaction hashes into `tx_hashes.txt` (one per line):
   ```
   abc123def456...
   fedcba987654...
   ```

4. Start the server:
   ```bash
   ../env12/bin/uvicorn main:app --host 127.0.0.1 --port 8000
   ```

## API Endpoints

### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-04-09T20:00:00.000000+00:00"
}
```

### `POST /history`
Get transaction history for addresses.

**Request:**
```json
{
  "addresses": [
    "tltc1qk8yyn8v267d5sr2tum8tq7djxdqf0vulhth62y",
    "tltc1qg9dvsx67z38uwzl4xvucktdc5tx66xgduykar4"
  ]
}
```

**Response:**
```json
{
  "tltc1qk8yyn8v267d5sr2tum8tq7djxdqf0vulhth62y": {
    "transactions": [
      {
        "height": 2500000,
        "tx_hash": "abc123..."
      },
      {
        "height": 0,
        "fee": 1000,
        "tx_hash": "def456..."
      }
    ],
    "count": 2,
    "timestamp": "2026-04-09T20:00:00.000000+00:00"
  }
}
```

### `POST /transactions`
Get verbose transaction details for transaction hashes (batch operation).

**Request:**
```json
{
  "tx_hashes": [
    "abc123def456abc123def456abc123def456abc123def456abc123def456abc1",
    "fedcba987654fedcba987654fedcba987654fedcba987654fedcba987654fedc"
  ]
}
```

**Response:**
```json
{
  "timestamp": "2026-04-09T20:00:00.000000+00:00",
  "count": 2,
  "transactions": [
    {
      "tx_hash": "abc123def456...",
      "txid": "abc123def456...",
      "hash": "...",
      "version": 2,
      "size": 225,
      "vsize": 144,
      "weight": 576,
      "locktime": 0,
      "vin": [...],
      "vout": [...],
      "hex": "...",
      "confirmations": 1000,
      "time": 1234567890,
      "blocktime": 1234567890
    },
    {
      "tx_hash": "fedcba987654...",
      "error": "Transaction not found"
    }
  ]
}
```

## Running Tests

```bash
# Health check
../env12/bin/python test_health.py

# Get transaction history
../env12/bin/python test_history.py

# Get transaction details
../env12/bin/python test_transactions.py
```

## Error Handling

- **Invalid addresses**: Returns 400 with error message
- **Invalid tx hashes**: Returns 400 with error message
- **Connection lost**: Attempts 1 reconnection, then returns 503 with error
- **Query errors**: Returns 500 with error message
- **All errors are logged** for debugging

## Logging

Logs include:
- Address-to-script-hash conversions
- ElectrumX connection/disconnection
- All requests and responses (JSON-RPC)
- Error details with full stack traces

## Batch Operations

Both `/history` and `/transactions` endpoints support batch operations:
- All requests are sent to ElectrumX in a single batch
- Responses are read efficiently without blocking
- Production-ready and optimized for performance
