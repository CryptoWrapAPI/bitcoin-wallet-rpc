#!/bin/bash
# Test: Subscribe to script hash updates (wallet_addresses with updated API)

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
echo -e "${BLUE}Test: Subscribe to Wallet Address Updates${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Wallet addresses to subscribe: ${#ADDRESSES[@]}${NC}"
echo ""

# Display the addresses being subscribed
for i in "${!ADDRESSES[@]}"; do
    echo -e "${YELLOW}  [$((i+1))] ${ADDRESSES[$i]}${NC}"
done
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
PAYLOAD="{\"addresses\": [$ADDRESSES_JSON], \"webhook_url\": \"https://webhook.example.com/notify\"}"

# Subscribe without webhook
echo -e "\n${YELLOW}[1] Subscribing to updates (no webhook)...${NC}"
echo -e "${BLUE}curl -X POST ${BASE_URL}/subscribe \\${NC}"
echo -e "${BLUE}  -H 'Content-Type: application/json' \\${NC}"
echo -e "${BLUE}  -d '{\"addresses\": [${#ADDRESSES[@]} addresses]}'${NC}"
echo ""

RESPONSE=$(curl -s -X POST "${BASE_URL}/subscribe" \
  -H "Content-Type: application/json" \
  -d "{\"addresses\": [$ADDRESSES_JSON]}")

echo "$RESPONSE" | jq .
echo ""

# Subscribe with webhook
echo -e "\n${YELLOW}[2] Subscribing again with webhook URL...${NC}"
echo -e "${BLUE}curl -X POST ${BASE_URL}/subscribe \\${NC}"
echo -e "${BLUE}  -H 'Content-Type: application/json' \\${NC}"
echo -e "${BLUE}  -d '{\"addresses\": [...], \"webhook_url\": \"https://webhook.example.com/notify\"}'${NC}"
echo ""

RESPONSE=$(curl -s -X POST "${BASE_URL}/subscribe" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

echo "$RESPONSE" | jq .
echo ""

# List current subscriptions
echo -e "\n${YELLOW}[3] Listing all active subscriptions...${NC}"
echo -e "${BLUE}curl -s ${BASE_URL}/subscriptions | jq .${NC}"
echo ""

SUBSCRIPTIONS=$(curl -s "${BASE_URL}/subscriptions")
echo "$SUBSCRIPTIONS" | jq .

TOTAL=$(echo "$SUBSCRIPTIONS" | jq '.total_subscriptions')
echo -e "\n${GREEN}✓ Total active subscriptions: $TOTAL${NC}"
echo ""

echo -e "\n${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Subscribe test completed successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Next: Run test_unsubscribe.sh to test unsubscribe${NC}"
echo ""
