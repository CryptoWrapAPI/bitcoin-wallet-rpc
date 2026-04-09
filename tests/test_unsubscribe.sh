#!/bin/bash
# Test: Unsubscribe from script hash updates

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
echo -e "${BLUE}Test: Unsubscribe from Script Hash Updates${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Script hashes to unsubscribe: ${#SCRIPT_HASHES[@]}${NC}"
echo ""

# Display the hashes being unsubscribed
for i in "${!SCRIPT_HASHES[@]}"; do
    echo -e "${YELLOW}  [$((i+1))] ${SCRIPT_HASHES[$i]}${NC}"
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

# Build JSON array of script hashes
HASHES_JSON=$(printf '"%s"' "${SCRIPT_HASHES[@]}" | sed 's/" "/", "/g')
PAYLOAD="{\"script_hashes\": [$HASHES_JSON]}"

# Unsubscribe
echo -e "\n${YELLOW}[2] Unsubscribing from all script hashes...${NC}"
echo -e "${BLUE}curl -X DELETE ${BASE_URL}/subscribe \\${NC}"
echo -e "${BLUE}  -H 'Content-Type: application/json' \\${NC}"
echo -e "${BLUE}  -d '{\"script_hashes\": [${#SCRIPT_HASHES[@]} hashes]}'${NC}"
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
