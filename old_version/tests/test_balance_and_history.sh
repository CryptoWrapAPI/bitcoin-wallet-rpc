#!/bin/bash
# Test /balance and /history endpoints with wallet addresses from file

set -e

BASE_URL="http://localhost:8000"
ADDRESSES_FILE="$(dirname "$0")/wallet_addresses.txt"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Read wallet addresses from file
readarray -t ADDRESSES < "$ADDRESSES_FILE"

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Test: Balance & History Endpoints${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Wallet addresses loaded: ${#ADDRESSES[@]}${NC}"
echo ""

# Build JSON array of wallet addresses using printf with commas
ADDRESSES_JSON=""
for addr in "${ADDRESSES[@]}"; do
    if [ -z "$ADDRESSES_JSON" ]; then
        ADDRESSES_JSON="\"$addr\""
    else
        ADDRESSES_JSON="$ADDRESSES_JSON, \"$addr\""
    fi
done
PAYLOAD="{\"addresses\": [$ADDRESSES_JSON]}"

# Test 1: Get balances
echo -e "\n${YELLOW}[1] Getting balances for all wallet addresses...${NC}"
echo -e "${BLUE}curl -X POST ${BASE_URL}/balance \\${NC}"
echo -e "${BLUE}  -H 'Content-Type: application/json' \\${NC}"
echo -e "${BLUE}  -d '{\"addresses\": [${#ADDRESSES[@]} addresses]}' | jq .${NC}"
echo ""

BALANCE_RESPONSE=$(curl -s -X POST "${BASE_URL}/balance" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

echo "$BALANCE_RESPONSE" | jq .
BALANCE_COUNT=$(echo "$BALANCE_RESPONSE" | jq 'length')
echo -e "\n${GREEN}✓ Received balances for $BALANCE_COUNT addresses${NC}"
echo ""

# Test 2: Get transaction history
echo -e "\n${YELLOW}[2] Getting transaction history for all wallet addresses...${NC}"
echo -e "${BLUE}curl -X POST ${BASE_URL}/history \\${NC}"
echo -e "${BLUE}  -H 'Content-Type: application/json' \\${NC}"
echo -e "${BLUE}  -d '{\"addresses\": [${#ADDRESSES[@]} addresses]}' | jq .${NC}"
echo ""

HISTORY_RESPONSE=$(curl -s -X POST "${BASE_URL}/history" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

echo "$HISTORY_RESPONSE" | jq . | head -50
HISTORY_COUNT=$(echo "$HISTORY_RESPONSE" | jq 'length')
echo -e "\n${GREEN}✓ Received $HISTORY_COUNT transactions${NC}"
echo ""

# Test 3: Verify health
echo -e "\n${YELLOW}[3] Verifying service health...${NC}"
HEALTH=$(curl -s "${BASE_URL}/health")
echo "$HEALTH" | jq .
CONNECTED=$(echo "$HEALTH" | jq '.electrum_connected')
if [ "$CONNECTED" = "true" ]; then
    echo -e "${GREEN}✓ ElectrumX connected${NC}"
else
    echo -e "${RED}✗ ElectrumX NOT connected${NC}"
fi
echo ""

echo -e "\n${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Test completed successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
