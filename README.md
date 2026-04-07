# Litecoin Wallet RPC Microservice

A lightweight, FastAPI-based microservice providing RPC interaction with the Litecoin blockchain. Designed to be integrated into larger applications, this service handles wallet derivations and blockchain interactions through a clean REST API.

## Features

- **Wallet Derivation**: Uses `bip_utils` for hierarchical deterministic (HD) wallet key derivation (BIP84)
- **Blockchain Interactions**: Connects to ElectrumX servers for raw blockchain data retrieval (UTXOs, transactions, balance checks, etc.)
- **RESTful API**: Built with FastAPI for high performance and automatic documentation
- **Microservice Architecture**: Designed to be consumed by other services in a distributed system

## Tech Stack

- **Python 3.12**
- **FastAPI** - Web framework
- **bip_utils** - HD wallet derivation
- **Electrum Protocol** - Blockchain data via raw RPC connections to ElectrumX servers (TCP)

## Quick Start

### Prerequisites

- Python 3.12
- Access to an ElectrumX server (or run your own)

### Running the Service

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# local development

gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
# production run
```

API documentation will be available at:
- Swagger UI: `http://localhost:8000/docs`

<!-- ## API Endpoints -->

<!-- ### Wallet Operations -->
<!-- - `POST /wallet/derive` - Derive addresses from seed/mnemonic -->
<!-- - `POST /wallet/generate-seed` - Generate a new BIP39 mnemonic seed -->

<!-- ### Blockchain Operations -->
<!-- - `GET /address/{address}/balance` - Get address balance -->
<!-- - `GET /address/{address}/transactions` - Get address transaction history -->
<!-- - `GET /address/{address}/utxos` - Get unspent outputs for an address -->
<!-- - `POST /transaction/get` - Retrieve transaction details -->
<!-- - `POST /transaction/broadcast` - Broadcast a raw transaction -->

<!-- ## Usage Example -->

<!-- ```python -->
<!-- import requests -->

<!-- # Derive addresses from mnemonic -->
<!-- response = requests.post("http://localhost:8000/wallet/derive", json={ -->
    <!-- "mnemonic": "your twelve word seed phrase here...", -->
    <!-- "derivation_path": "m/44'/2'/0'/0/0", -->
    <!-- "num_addresses": 5 -->
<!-- }) -->

<!-- # Check address balance -->
<!-- response = requests.get("http://localhost:8000/address/ltc1qexample/balance") -->
<!-- ``` -->

<!-- ## Project Structure -->

<!-- ``` -->
<!-- litecoin-wallet-rpc/ -->
<!-- ├── app/ -->
<!-- │   ├── main.py              # FastAPI application entrypoint -->
<!-- │   ├── routes/              # API route definitions -->
<!-- │   ├── services/            # Business logic (wallet, blockchain) -->
<!-- │   └── schemas/             # Pydantic models -->
<!-- ├── requirements.txt         # Python dependencies -->
<!-- └── README.md -->
<!-- ``` -->

## License

GNU Affero General Public License
