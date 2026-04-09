#!/usr/bin/env python3
"""Test subscriptions endpoint."""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

print("\n" + "=" * 60)
print("TEST: List Active Subscriptions")
print("=" * 60)

try:
    response = requests.get(f"{BASE_URL}/subscriptions")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Active subscriptions: {data.get('count', 0)}")
    if data.get('subscribed'):
        print("\nSubscribed addresses:")
        for addr in data['subscribed']:
            print(f"  - {addr}")
    else:
        print("No active subscriptions")
    
    print(f"\nFull response:\n{json.dumps(data, indent=2)}")
    
    if response.status_code == 200:
        print("\n✓ Subscriptions list request succeeded")
    else:
        print(f"\n✗ Subscriptions list request failed")
except Exception as e:
    print(f"\n✗ Error: {e}")

print("=" * 60 + "\n")
