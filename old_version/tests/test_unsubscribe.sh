#!/bin/bash
# Test: Unsubscribe from script hash updates (wallet addresses now)

set -e

BASE_URL="http://localhost:8000"
SCRIPT_HASHES_FILE="$(dirname "$0")/wallet_addresses.txt"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Read wallet addresses from file
readarray -t ADDRESSES < "$SCRIPT_HASHES_FILE"

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Test: Unsubscribe from Wallet Address Updates${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Wallet addresses to unsubscribe: ${#ADDRESSES[@]}${NC}"
echo ""

# Display the addresses being unsubscribed
for i in "${!ADDRESSES[@]}"; do
    echo -e "${YELLOW}  [$((i+1))] ${ADDRESSES[$i]}${NC}"
done
echo ""

# Check current subscriptions before unsubscribe
echo -e "\n${YELLOW}[1] Checking current subscriptions before unsubscribe...${NC}"
echo -e "${BLUE}curl -s ${BASE_URL}/subscriptions | jq .${NC}"
echo ""

BEFORE=$(curl -s "${BASE_URL}/subscriptions")
echo "$BEFORE" | jq .
BEFORE_COUNT=$(echo "$BEFORE" | jq '.total_subscriptions')
echo -e "${YELLOW}Current subscriptions: $BEFORE_COUNT${NC}"
echo ""

# Build JSON array of addresses using printf with commas
ADDRESSES_JSON=""
for addr in "${ADDRESSES[@]}"; do
    if [ -z "$ADDRESSES_JSON" ]; then
        ADDRESSES_JSON="\"$addr\""
    else
        ADDRESSES_JSON="$ADDRESSES_JSON, \"$addr\""
    fi
done
PAYLOAD="{\"addresses\": [$ADDRESSES_JSON]}"

# Unsubscribe
echo -e "\n${YELLOW}[2] Unsubscribing from all wallet addresses...${NC}"
echo -e "${BLUE}curl -X DELETE ${BASE_URL}/subscribe \\${NC}"
echo -e "${BLUE}  -H 'Content-Type: application/json' \\${NC}"
echo -e "${BLUE}  -d '{\"addresses\": [${#ADDRESSES[@]} addresses]}'${NC}"
echo ""

UNSUBSCRIBE_RESPONSE=$(curl -s -X DELETE "${BASE_URL}/subscribe" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

echo "$UNSUBSCRIBE_RESPONSE" | jq .
UNSUBSCRIBED_COUNT=$(echo "$UNSUBSCRIBE_RESPONSE" | jq '.script_hashes | length')
echo -e "${GREEN}✓ Unsubscribed from $UNSUBSCRIBED_COUNT script hashes${NC}"
echo ""

# Verify subscriptions after unsubscribe
echo -e "\n${YELLOW}[3] Verifying subscriptions after unsubscribe...${NC}"
echo -e "${BLUE}curl -s ${BASE_URL}/subscriptions | jq .${NC}"
echo ""

AFTER=$(curl -s "${BASE_URL}/subscriptions")
echo "$AFTER" | jq .
AFTER_COUNT=$(echo "$AFTER" | jq '.total_subscriptions')
echo -e "${GREEN}✓ Remaining subscriptions: $AFTER_COUNT${NC}"
echo ""

if [ "$AFTER_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓ All subscriptions successfully removed!${NC}"
else
    echo -e "${YELLOW}⚠ Note: $AFTER_COUNT subscriptions remain${NC}"
fi
echo ""

echo -e "\n${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Unsubscribe test completed successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
