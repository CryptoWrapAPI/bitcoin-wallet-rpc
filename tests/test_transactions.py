#!/usr/bin/env python3
"""Test transactions endpoint."""

import requests
import json
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
TX_HASHES_FILE = Path(__file__).parent / "tx_hashes.txt"

# Read transaction hashes from file
with open(TX_HASHES_FILE) as f:
    tx_hashes = [line.strip() for line in f if line.strip() and not line.startswith("#")]

if not tx_hashes:
    print("No transaction hashes in tx_hashes.txt")
    exit(1)

print("\n" + "=" * 60)
print("TEST: Get Transaction Details")
print("=" * 60)
print(f"Transaction hashes ({len(tx_hashes)}):")
for tx_hash in tx_hashes:
    print(f"  - {tx_hash}")
print()

try:
    payload = {"tx_hashes": tx_hashes}
    response = requests.post(f"{BASE_URL}/transactions", json=payload)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response:\n{json.dumps(data, indent=2)}")
    
    if response.status_code == 200:
        print(f"\n✓ Transactions request succeeded (got {data.get('count', 0)} transactions)")
    else:
        print(f"\n✗ Transactions request failed")
except Exception as e:
    print(f"\n✗ Error: {e}")

print("=" * 60 + "\n")
