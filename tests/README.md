# Test Suite for Litecoin Wallet RPC

## Setup

1. First, paste your wallet addresses into `addrs.txt`, one per line:
   ```
   tltc1qk8yyn8v267d5sr2tum8tq7djxdqf0vulhth62y
   tltc1qg9dvsx67z38uwzl4xvucktdc5tx66xgduykar4
   ```

2. Make sure the server is running:
   ```bash
   cd ..
   ../env12/bin/uvicorn main:app --host 127.0.0.1 --port 8000
   ```

## Running Tests

Each test script is standalone and tests a single endpoint:

```bash
# Health check
../env12/bin/python test_health.py

# Get transaction history for addresses
../env12/bin/python test_history.py

# Subscribe to address updates
../env12/bin/python test_subscribe.py

# List active subscriptions
../env12/bin/python test_subscriptions.py

# Unsubscribe from addresses
../env12/bin/python test_unsubscribe.py
```

## Endpoints

- `GET /health` - Health check
- `POST /history` - Get transaction history for addresses
- `POST /subscribe` - Subscribe to address updates (notifications logged)
- `POST /unsubscribe` - Unsubscribe from addresses
- `GET /subscriptions` - List active subscriptions
