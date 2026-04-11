# Litecoin Wallet RPC Microservice

A lightweight, FastAPI-based microservice providing RPC interaction with the Litecoin blockchain via ElectrumX servers. Designed to be integrated into larger applications, this service handles wallet derivations and blockchain interactions through a clean REST API.

The project uses `asyncio` to establish a persistent connection to an ElectrumX server over TCP or SSL.
Electrum Protocol Methods: https://electrumx.readthedocs.io/en/latest/protocol-methods.html

All script hash conversions are handled in memory. SQLite can optionally be added in the future for persistence, or Redis to support distributed deployments.

## Features

- **Wallet Derivation**: Uses `bip_utils` for hierarchical deterministic (HD) wallet key derivation (BIP84) — derive addresses from a master private key or account public key
- **Transaction History**: Get transaction history for multiple wallet addresses in a single batch request
- **Transaction Details**: Fetch verbose transaction data for multiple tx hashes in a single batch request
- **Balance Query**: Get confirmed and unconfirmed balances for wallet addresses
- **Block Height Subscription**: Real-time block height notifications via ElectrumX subscription
- **Address-to-Script-Hash Conversion**: P2WPKH support for mainnet and testnet
- **Comprehensive Error Handling**: Logging, connection recovery (1 reconnection attempt on failure)
- **Batch Operations**: All blockchain queries are sent efficiently in a single batch

## Future Features

- Caching to avoid rate-limiting by ElectrumX servers
- Using multiple ElectrumX servers for failover (rotate server from a list if failed or rate-limited)
- Subscribe/unsubscribe to address notifications (`blockchain.scripthash.subscribe`) with webhook callbacks
- Keepalive pings to maintain long-lived connections
- WebSocket support for real-time updates
- SQLite/Redis caching layer

## Tech Stack

- **Python 3.12** (`bip_utils` may be incompatible with other versions)
- **FastAPI** — Web framework
- **bip_utils** — HD wallet derivation (BIP39, BIP84)
- **Electrum Protocol** — Blockchain data via raw RPC connections (TCP or SSL)

## Quick Start

### Prerequisites

- Python 3.12
- Access to an ElectrumX server (or run your own)

### 1. Create `.env` file

```
ELECTRUMX_URL=ssl://electrum.ltc.xurious.com:51002
TESTNET=true
ENV_FILE=.env
```

`ELECTRUMX_URL` format: `protocol://host:port` — supports `ssl://` and `tcp://`.

### 2. Start the server

#### Option A: Docker (Recommended)

```bash
docker compose up --build
```

#### Option B: Local Python

```bash
pip install fastapi[standard]
fastapi run
```

> For development with auto-reload: `fastapi dev`
> Alternatively, you can use uvicorn directly: `uvicorn main:app --host 127.0.0.1 --port 8000`

API documentation available at `http://localhost:8000/docs`.

## API Endpoints

### `GET /block-height`

Get current block height from header subscription (updated in real-time).

**Response:**
```json
{
  "height": 520481,
  "hex": "00000020890208a0ae3a3892aa047c5468725846577cfcd9b512b50000000000000000005dc2b02f2d297a9064ee103036c14d678f9afc7e3d9409cf53fd58b82e938e8ecbeca05a2d2103188ce804c4",
  "last_update": "2026-04-09T20:00:00.000000+00:00",
  "timestamp": "2026-04-09T20:00:00.000000+00:00"
}
```

### `POST /derive`

Derive a wallet address from a BIP84 extended key.

Accepts either a **master private key** (depth 0, e.g. `ttpv...` / `xprv...`) or an **account public key** (depth 3, e.g. `ttub...` / `xpub...`).

Derivation path: `m/84'/coin'/account_index'/0/address_index`

> **Note**: Master *public* keys cannot derive hardened paths (`m/84'/...`). Use a master private key or an account-level public key.

**Request:**
```json
{
  "xpub": "ttpv96BtqegdxXcePe8...",
  "account_index": 0,
  "address_index": 0
}
```

**Response:**
```json
{
  "address": "tltc1q90mr483lhf9nmygyzz0sye8tpv42le4g2272mf",
  "account_index": 0,
  "address_index": 0,
  "chain": "external"
}
```

### `POST /history`

Get transaction history for wallet addresses (batch operation).

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
      { "height": 2500000, "tx_hash": "abc123..." },
      { "height": 0, "fee": 1000, "tx_hash": "def456..." }
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
      "version": 2,
      "size": 225,
      "vsize": 144,
      "weight": 576,
      "locktime": 0,
      "vin": [...],
      "vout": [...],
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

### `POST /balance`

Get confirmed and unconfirmed balances for wallet addresses.

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
    "confirmed": 103873966,
    "unconfirmed": 23684400,
    "timestamp": "2026-04-09T20:00:00.000000+00:00"
  },
  "tltc1qg9dvsx67z38uwzl4xvucktdc5tx66xgduykar4": {
    "confirmed": 0,
    "unconfirmed": 0,
    "timestamp": "2026-04-09T20:00:00.000000+00:00"
  }
}
```

Balances are returned in satoshis (minimum coin units).

## Running Tests

See [tests/README.md](tests/README.md) for test setup and usage instructions.

## Error Handling

| Scenario | Status | Detail |
|---|---|---|
| Invalid address | 400 | Descriptive error message |
| Invalid tx hash | 400 | Must be 64-char hex string |
| Invalid derivation key | 400 | Unsupported depth or malformed key |
| Connection lost | 503 | After 1 reconnection attempt fails |
| Query error | 500 | Error details logged on server |

All errors are logged with full stack traces for debugging.

## Logging

The service logs:
- Address-to-script-hash conversions
- ElectrumX connection lifecycle (connect/disconnect)
- All JSON-RPC requests and responses
- Error details with full stack traces

## License

GNU Affero General Public License

