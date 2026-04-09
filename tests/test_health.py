#!/usr/bin/env python3
"""Test health check endpoint."""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

print("\n" + "=" * 60)
print("TEST: Health Check")
print("=" * 60)

try:
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response:\n{json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("\n✓ Health check passed")
    else:
        print(f"\n✗ Health check failed")
except Exception as e:
    print(f"\n✗ Error: {e}")

print("=" * 60 + "\n")
