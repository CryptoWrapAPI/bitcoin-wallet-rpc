#!/usr/bin/env python3
"""Test address derivation endpoint."""

import requests
import json

BASE_URL = "http://127.0.0.1:8101"

# Configuration — change these values to test with your own master private key
XPRV = "vprv9DMUxX4ShgxMMspZPJNbJWd8eMYGEusxaQGme5ayurx99988Yh4wmV7o1u4kbVNduTXEpTnZXXk9U5diNC5D4NamDBieVaqPKtwTwRM1Xj6"  # Replace with your BIP84 master private key
ACCOUNT_INDEX = 0
ADDRESS_INDEX = 0

print("\n" + "=" * 60)
print("TEST: Address Derivation")
print("=" * 60)
print(f"XPRV: {XPRV[:20]}...")
print(f"Account index: {ACCOUNT_INDEX}")
print(f"Address index: {ADDRESS_INDEX}")
print()

try:
    payload = {
        "xpub": XPRV,
        "account_index": ACCOUNT_INDEX,
        "address_index": ADDRESS_INDEX,
    }
    response = requests.post(f"{BASE_URL}/derive", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response:\n{json.dumps(response.json(), indent=2)}")

    if response.status_code == 200:
        data = response.json()
        print(f"\n✓ Derived address: {data['address']}")
    else:
        print("\n✗ Derivation failed")
except Exception as e:
    print(f"\n✗ Error: {e}")

print("=" * 60 + "\n")
