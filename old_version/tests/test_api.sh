#!/bin/bash
# API Tests using curl for the Litecoin Wallet RPC service

set -e

BASE_URL="http://localhost:8000"
PASSED=0
FAILED=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test helper
test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    local expected_code="$5"
    
    echo -e "\n${YELLOW}TEST: $name${NC}"
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$BASE_URL$endpoint")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    echo "Response Code: $http_code"
    echo "Response Body:"
    echo "$body" | jq '.' 2>/dev/null || echo "$body"
    
    if [ "$http_code" = "$expected_code" ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAILED (expected $expected_code, got $http_code)${NC}"
        ((FAILED++))
    fi
}

# =============================================================================
# Tests
# =============================================================================

echo -e "\n${YELLOW}========================================${NC}"
echo -e "${YELLOW}Litecoin Wallet RPC - API Tests${NC}"
echo -e "${YELLOW}========================================${NC}"

# Test 1: Health check
test_endpoint "Health Check" "GET" "/health" "" "200"

# Test 2: Generate seed
test_endpoint "Generate BIP39 Seed" "GET" "/seed" "" "200"

# Test 3: Get single balance (will fail if ElectrumX not connected, but endpoint works)
test_endpoint "Get Balance (Single)" "GET" "/balance/04fbd6d7ac5c54aedcb91084b7c774531089223a7f06d428606c3602e9f96523" "" "200"

# Test 4: Get multiple balances
test_endpoint "Get Balances (Multiple)" "POST" "/balance" '{
    "script_hashes": [
        "04fbd6d7ac5c54aedcb91084b7c774531089223a7f06d428606c3602e9f96523",
        "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    ]
}' "200"

# Test 5: Subscribe to updates (single)
test_endpoint "Subscribe (Single)" "POST" "/subscribe" '{
    "script_hashes": ["04fbd6d7ac5c54aedcb91084b7c774531089223a7f06d428606c3602e9f96523"]
}' "200"

# Test 6: Subscribe with webhook
test_endpoint "Subscribe with Webhook" "POST" "/subscribe" '{
    "script_hashes": [
        "04fbd6d7ac5c54aedcb91084b7c774531089223a7f06d428606c3602e9f96523",
        "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    ],
    "webhook_url": "https://example.com/webhook"
}' "200"

# Test 7: List subscriptions
test_endpoint "List Subscriptions" "GET" "/subscriptions" "" "200"

# Test 8: Invalid endpoint
echo -e "\n${YELLOW}TEST: Invalid Endpoint (404)${NC}"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/invalid/endpoint")
http_code=$(echo "$response" | tail -n1)
echo "Response Code: $http_code"
if [ "$http_code" = "404" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAILED (expected 404, got $http_code)${NC}"
    ((FAILED++))
fi

# =============================================================================
# Summary
# =============================================================================

echo -e "\n${YELLOW}========================================${NC}"
echo -e "${YELLOW}Test Summary${NC}"
echo -e "${YELLOW}========================================${NC}"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}Some tests failed.${NC}"
    exit 1
fi
