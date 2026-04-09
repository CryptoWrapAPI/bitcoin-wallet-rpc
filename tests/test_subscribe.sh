#!/bin/bash
# Test: Subscribe to script hash updates

set -e

BASE_URL="http://localhost:8000"
SCRIPT_HASHES_FILE="$(dirname "$0")/script_hashes.txt"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Read script hashes from file
readarray -t SCRIPT_HASHES < "$SCRIPT_HASHES_FILE"

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Test: Subscribe to Script Hash Updates${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Script hashes to subscribe: ${#SCRIPT_HASHES[@]}${NC}"
echo ""

# Display the hashes being subscribed
for i in "${!SCRIPT_HASHES[@]}"; do
    echo -e "${YELLOW}  [$((i+1))] ${SCRIPT_HASHES[$i]}${NC}"
done
echo ""

# Build JSON array of script hashes
HASHES_JSON=$(printf '"%s"' "${SCRIPT_HASHES[@]}" | sed 's/" "/", "/g')
PAYLOAD="{\"script_hashes\": [$HASHES_JSON], \"webhook_url\": \"https://webhook.example.com/notify\"}"

# Subscribe without webhook
echo -e "\n${YELLOW}[1] Subscribing to updates (no webhook)...${NC}"
echo -e "${BLUE}curl -X POST ${BASE_URL}/subscribe \\${NC}"
echo -e "${BLUE}  -H 'Content-Type: application/json' \\${NC}"
echo -e "${BLUE}  -d '{\"script_hashes\": [${#SCRIPT_HASHES[@]} hashes]}'${NC}"
echo ""

RESPONSE=$(curl -s -X POST "${BASE_URL}/subscribe" \
  -H "Content-Type: application/json" \
  -d "{\"script_hashes\": [$HASHES_JSON]}")

echo "$RESPONSE" | jq .
echo ""

# Subscribe with webhook
echo -e "\n${YELLOW}[2] Subscribing again with webhook URL...${NC}"
echo -e "${BLUE}curl -X POST ${BASE_URL}/subscribe \\${NC}"
echo -e "${BLUE}  -H 'Content-Type: application/json' \\${NC}"
echo -e "${BLUE}  -d '{\"script_hashes\": [...], \"webhook_url\": \"https://webhook.example.com/notify\"}'${NC}"
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
