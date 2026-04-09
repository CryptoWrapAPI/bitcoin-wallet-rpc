#!/usr/bin/env python3
"""Test history endpoint."""

import requests
import json
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
ADDRS_FILE = Path(__file__).parent / "addrs.txt"

# Read addresses from file
with open(ADDRS_FILE) as f:
    addresses = [line.strip() for line in f if line.strip() and not line.startswith("#")]

if not addresses:
    print("No addresses in addrs.txt")
    exit(1)

print("\n" + "=" * 60)
print("TEST: Get History")
print("=" * 60)
print(f"Addresses ({len(addresses)}):")
for addr in addresses:
    print(f"  - {addr}")
print()

try:
    payload = {"addresses": addresses}
    response = requests.post(f"{BASE_URL}/history", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response:\n{json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("\n✓ History request succeeded")
    else:
        print(f"\n✗ History request failed")
except Exception as e:
    print(f"\n✗ Error: {e}")

print("=" * 60 + "\n")
