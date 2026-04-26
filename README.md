# Bitcoin Wallet RPC Microservice

A lightweight, FastAPI-based microservice providing RPC interaction with the Bitcoin blockchain via ElectrumX/Fulcrum protocol. Designed to be integrated into larger applications, this service handles wallet derivations and blockchain interactions through a clean REST API.

Public ElectrumX/Fulcrum servers can be found here: https://1209k.com/bitcoin-eye/ele.php?chain=btc (Or you can setup your own!)

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
ELECTRUMX_URL=ssl://blackie.c3-soft.com:57006
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
  "height": 4947025,
  "hex": "00e0b125338ac18da81fac744461099a6e2c17c6edfbb5e6a5e9591ec6430f0000000000f8d16ebbc86317d5337b8d61263ac3f885f62c35463a62476e837036e53e595449ffed69c7f71a1c7e028dd7",
  "last_update": "2026-04-26T12:10:58.528407+00:00",
  "timestamp": "2026-04-26T12:11:00.450249+00:00"
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
  "xpub": "vprv9DMUxX4ShgxMMspZPJNbJWd8eMYGEusxaQGme5ayurx99988Yh4wmV7o1u4kbVNduTXEpTnZXXk9U5diNC5D4NamDBieVaqPKtwTwRM1Xj6",
  "account_index": 0,
  "address_index": 0
}
```

**Response:**
```json
{
  "address": "tb1qz32llcc48uegkd65rltzjy0p6646pv6pd0c696",
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
    "tb1qz32llcc48uegkd65rltzjy0p6646pv6pd0c696",
    "tb1q386nqxcn0stm9mnctcg67ggrg3kzcdkkjlag5z",
    "tb1qy2w67vnv0twsmk860h9cu20l8qqyqd9484lmqq"
  ]
}
```

**Response:**
```json
{
  "tb1qz32llcc48uegkd65rltzjy0p6646pv6pd0c696": {
    "transactions": [
      {
        "height": 4947019,
        "tx_hash": "6b8a491f79df009fa06bd4c367c60c01196425bf01fe4d69ab92a40cee764a22"
      },
      {
        "fee": 231,
        "height": 0,
        "tx_hash": "e5dd43b664d5c9a998a4a1e9411281b5b299cc1753637492a603eefa7f45110e"
      }
    ],
    "count": 2,
    "timestamp": "2026-04-26T12:11:00.870438+00:00"
  },
  "tb1q386nqxcn0stm9mnctcg67ggrg3kzcdkkjlag5z": {
    "transactions": [],
    "count": 0,
    "timestamp": "2026-04-26T12:11:01.073126+00:00"
  },
  "tb1qy2w67vnv0twsmk860h9cu20l8qqyqd9484lmqq": {
    "transactions": [
      {
        "fee": 231,
        "height": 0,
        "tx_hash": "e5dd43b664d5c9a998a4a1e9411281b5b299cc1753637492a603eefa7f45110e"
      }
    ],
    "count": 1,
    "timestamp": "2026-04-26T12:11:01.275849+00:00"
  }
}
```

### `POST /transactions`

Get verbose transaction details for transaction hashes (batch operation).

**Request:**
```json
{
  "tx_hashes": [
    "6b8a491f79df009fa06bd4c367c60c01196425bf01fe4d69ab92a40cee764a22",
    "e5dd43b664d5c9a998a4a1e9411281b5b299cc1753637492a603eefa7f45110e"
  ]
}
```

**Response:**
```json
{
  "timestamp": "2026-04-26T12:11:01.587956+00:00",
  "count": 2,
  "transactions": [
    {
      "blockhash": "000000000d8389a7b9e74165d50193ebb041cf1e292ab4181a7771a53c491cd7",
      "blocktime": 1777205027,
      "confirmations": 7,
      "hash": "6b8a491f79df009fa06bd4c367c60c01196425bf01fe4d69ab92a40cee764a22",
      "hex": "020000000184b4a5b5370f41ab1bc17e2bb1e17189a3a12841db79191e54f1715603e01da7010000006a47304402204e9f9d0bd67fdb13cfb655fb367864ff25e28fa99a752ae309bb8a6d980e3809022065062e600db152f3865f0538891563dc3fb392ee249298c48e8b2884cfcce6d7012103c5927626d2034c92fd8fe0c90b78e9a5e3e930b7585575cb28be6ddc0e05b4b1fdffffff02e244c33500000000160014bdfa5eac97696d28a6c63aa8422cf743eecc243057f30100000000001600141455ffe3153f328b37541fd62911e1d6aba0b341497c4b00",
      "locktime": 4947017,
      "size": 219,
      "time": 1777205027,
      "txid": "6b8a491f79df009fa06bd4c367c60c01196425bf01fe4d69ab92a40cee764a22",
      "version": 2,
      "vin": [
        {
          "scriptSig": {
            "asm": "304402204e9f9d0bd67fdb13cfb655fb367864ff25e28fa99a752ae309bb8a6d980e3809022065062e600db152f3865f0538891563dc3fb392ee249298c48e8b2884cfcce6d7[ALL] 03c5927626d2034c92fd8fe0c90b78e9a5e3e930b7585575cb28be6ddc0e05b4b1",
            "hex": "47304402204e9f9d0bd67fdb13cfb655fb367864ff25e28fa99a752ae309bb8a6d980e3809022065062e600db152f3865f0538891563dc3fb392ee249298c48e8b2884cfcce6d7012103c5927626d2034c92fd8fe0c90b78e9a5e3e930b7585575cb28be6ddc0e05b4b1"
          },
          "sequence": 4294967293,
          "txid": "a71de0035671f1541e1979db4128a1a38971e1b12b7ec11bab410f37b5a5b484",
          "vout": 1
        }
      ],
      "vout": [
        {
          "n": 0,
          "scriptPubKey": {
            "address": "tb1qhha9atyhd9kj3fkx825yyt8hg0hvcfpsktk34k",
            "asm": "0 bdfa5eac97696d28a6c63aa8422cf743eecc2430",
            "desc": "addr(tb1qhha9atyhd9kj3fkx825yyt8hg0hvcfpsktk34k)#f6d9p0yu",
            "hex": "0014bdfa5eac97696d28a6c63aa8422cf743eecc2430",
            "type": "witness_v0_keyhash"
          },
          "value": 9.01989602
        },
        {
          "n": 1,
          "scriptPubKey": {
            "address": "tb1qz32llcc48uegkd65rltzjy0p6646pv6pd0c696",
            "asm": "0 1455ffe3153f328b37541fd62911e1d6aba0b341",
            "desc": "addr(tb1qz32llcc48uegkd65rltzjy0p6646pv6pd0c696)#5lt6shch",
            "hex": "00141455ffe3153f328b37541fd62911e1d6aba0b341",
            "type": "witness_v0_keyhash"
          },
          "value": 0.00127831
        }
      ],
      "vsize": 219,
      "weight": 876,
      "tx_hash": "6b8a491f79df009fa06bd4c367c60c01196425bf01fe4d69ab92a40cee764a22"
    },
    {
      "hash": "d809cb04779847a82533e58cab480f5f62e8f60870414d5ccf059ea875807306",
      "hex": "02000000000101224a76ee0ca492ab694dfe01bf256419010cc667c3d46ba09f00df791f498a6b0100000000fdffffff02647d000000000000160014229daf326c7add0dd8fa7dcb8e29ff38004034b50c750100000000001600148bad78bca378389361ea2ac6f930ca1138c360c7024730440220379c41cf92775e4387e710465dbaf493330ae9987577c531a855acc60110a1b5022060fb20261b5f7e5954e62d902bc20d278493fc879b9bdb6185c7e550e56f3cf7012102124cea741f7e5ad49517a143047fbbd4b6fa240e5d1dd84247fc66aad5c294074d7c4b00",
      "locktime": 4947021,
      "size": 222,
      "txid": "e5dd43b664d5c9a998a4a1e9411281b5b299cc1753637492a603eefa7f45110e",
      "version": 2,
      "vin": [
        {
          "scriptSig": {
            "asm": "",
            "hex": ""
          },
          "sequence": 4294967293,
          "txid": "6b8a491f79df009fa06bd4c367c60c01196425bf01fe4d69ab92a40cee764a22",
          "txinwitness": [
            "30440220379c41cf92775e4387e710465dbaf493330ae9987577c531a855acc60110a1b5022060fb20261b5f7e5954e62d902bc20d278493fc879b9bdb6185c7e550e56f3cf701",
            "02124cea741f7e5ad49517a143047fbbd4b6fa240e5d1dd84247fc66aad5c29407"
          ],
          "vout": 1
        }
      ],
      "vout": [
        {
          "n": 0,
          "scriptPubKey": {
            "address": "tb1qy2w67vnv0twsmk860h9cu20l8qqyqd9484lmqq",
            "asm": "0 229daf326c7add0dd8fa7dcb8e29ff38004034b5",
            "desc": "addr(tb1qy2w67vnv0twsmk860h9cu20l8qqyqd9484lmqq)#t332vp4a",
            "hex": "0014229daf326c7add0dd8fa7dcb8e29ff38004034b5",
            "type": "witness_v0_keyhash"
          },
          "value": 0.000321
        },
        {
          "n": 1,
          "scriptPubKey": {
            "address": "tb1q3wkh309r0qufxc029tr0jvx2zyuvxcx8ru3y0z",
            "asm": "0 8bad78bca378389361ea2ac6f930ca1138c360c7",
            "desc": "addr(tb1q3wkh309r0qufxc029tr0jvx2zyuvxcx8ru3y0z)#udreds0y",
            "hex": "00148bad78bca378389361ea2ac6f930ca1138c360c7",
            "type": "witness_v0_keyhash"
          },
          "value": 0.000955
        }
      ],
      "vsize": 141,
      "weight": 561,
      "tx_hash": "e5dd43b664d5c9a998a4a1e9411281b5b299cc1753637492a603eefa7f45110e"
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
    "tb1qz32llcc48uegkd65rltzjy0p6646pv6pd0c696",
    "tb1q386nqxcn0stm9mnctcg67ggrg3kzcdkkjlag5z",
    "tb1qy2w67vnv0twsmk860h9cu20l8qqyqd9484lmqq"
  ]
}
```

**Response:**
```json
{
  "tb1qz32llcc48uegkd65rltzjy0p6646pv6pd0c696": {
    "confirmed": 127831,
    "unconfirmed": -127831,
    "timestamp": "2026-04-26T12:10:59.536058+00:00"
  },
  "tb1q386nqxcn0stm9mnctcg67ggrg3kzcdkkjlag5z": {
    "confirmed": 0,
    "unconfirmed": 0,
    "timestamp": "2026-04-26T12:10:59.898507+00:00"
  },
  "tb1qy2w67vnv0twsmk860h9cu20l8qqyqd9484lmqq": {
    "confirmed": 0,
    "unconfirmed": 32100,
    "timestamp": "2026-04-26T12:11:00.341517+00:00"
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

