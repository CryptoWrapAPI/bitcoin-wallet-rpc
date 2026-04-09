# Litecoin Wallet RPC - MVP

Simple FastAPI microservice to query Litecoin transaction history from ElectrumX servers.

## Features (MVP)

- ✅ Get transaction history for wallet addresses (batch operation)
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

3. Start the server:
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
  },
  "tltc1qg9dvsx67z38uwzl4xvucktdc5tx66xgduykar4": {
    "transactions": [],
    "count": 0,
    "timestamp": "2026-04-09T20:00:00.000000+00:00"
  }
}
```

## Running Tests

```bash
# Health check
../env12/bin/python test_health.py

# Get history
../env12/bin/python test_history.py
```

## Error Handling

- **Invalid addresses**: Returns 400 with error message
- **Connection lost**: Attempts 1 reconnection, then returns 503 with error
- **Query errors**: Returns 500 with error message
- **All errors are logged** for debugging

## Logging

Logs include:
- Address-to-script-hash conversions
- ElectrumX connection/disconnection
- All requests and responses (JSON-RPC)
- Error details with full stack traces
