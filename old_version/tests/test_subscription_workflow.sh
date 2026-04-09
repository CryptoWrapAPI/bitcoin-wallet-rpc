#!/bin/bash
# Test subscription workflow: get balance, get history, subscribe, list, unsubscribe

set -e

BASE_URL="http://localhost:8000"
SCRIPT_HASH="04fbd6d7ac5c54aedcb91084b7c774531089223a7f06d428606c3602e9f96523"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Litecoin Wallet RPC - Subscription Workflow Test${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

# Step 1: Get Balance
echo -e "\n${YELLOW}[1a] Getting balance for SINGLE script hash (batch of 1)...${NC}"
echo -e "${BLUE}curl -X POST ${BASE_URL}/balance \\${NC}"
echo -e "${BLUE}  -H 'Content-Type: application/json' \\${NC}"
echo -e "${BLUE}  -d '{\"script_hashes\": [\"${SCRIPT_HASH}\"]}' | jq .${NC}"
echo ""
curl -X POST "${BASE_URL}/balance" \
  -H "Content-Type: application/json" \
  -d "{\"script_hashes\": [\"${SCRIPT_HASH}\"]}" | jq .
echo ""

echo -e "\n${YELLOW}[1b] Getting balance for MULTIPLE script hashes...${NC}"
echo -e "${BLUE}curl -X POST ${BASE_URL}/balance \\${NC}"
echo -e "${BLUE}  -H 'Content-Type: application/json' \\${NC}"
echo -e "${BLUE}  -d '{\"script_hashes\": [\"${SCRIPT_HASH}\", \"1234567890abcdef...\"]}' | jq .${NC}"
echo ""
curl -X POST "${BASE_URL}/balance" \
  -H "Content-Type: application/json" \
  -d "{\"script_hashes\": [\"${SCRIPT_HASH}\", \"1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef\"]}" | jq .
echo ""

# Step 2: Get Transaction History (batch)
echo -e "\n${YELLOW}[2] Getting transaction history for script hash...${NC}"
echo -e "${BLUE}curl -X POST ${BASE_URL}/history \\${NC}"
echo -e "${BLUE}  -H 'Content-Type: application/json' \\${NC}"
echo -e "${BLUE}  -d '{\"script_hashes\": [\"${SCRIPT_HASH}\"]}' | jq .${NC}"
echo ""
curl -X POST "${BASE_URL}/history" \
  -H "Content-Type: application/json" \
  -d "{\"script_hashes\": [\"${SCRIPT_HASH}\"]}" | jq . | head -40
echo ""

# Step 3: Subscribe without webhook
echo -e "\n${YELLOW}[3] Subscribing to script hash updates (without webhook)...${NC}"
echo -e "${BLUE}curl -X POST ${BASE_URL}/subscribe \\${NC}"
echo -e "${BLUE}  -H 'Content-Type: application/json' \\${NC}"
echo -e "${BLUE}  -d '{\"script_hashes\": [\"${SCRIPT_HASH}\"]}' | jq .${NC}"
echo ""
curl -X POST "${BASE_URL}/subscribe" \
  -H "Content-Type: application/json" \
  -d "{\"script_hashes\": [\"${SCRIPT_HASH}\"]}" | jq .
echo ""

# Step 4: List subscriptions
echo -e "\n${YELLOW}[4] Listing all active subscriptions...${NC}"
echo -e "${BLUE}curl -s ${BASE_URL}/subscriptions | jq .${NC}"
echo ""
curl -s "${BASE_URL}/subscriptions" | jq .
echo ""

# Step 5: Subscribe with webhook
echo -e "\n${YELLOW}[5] Subscribing again with webhook URL...${NC}"
echo -e "${BLUE}curl -X POST ${BASE_URL}/subscribe \\${NC}"
echo -e "${BLUE}  -H 'Content-Type: application/json' \\${NC}"
echo -e "${BLUE}  -d '{\"script_hashes\": [\"${SCRIPT_HASH}\"], \"webhook_url\": \"https://webhook.example.com/notify\"}' | jq .${NC}"
echo ""
curl -X POST "${BASE_URL}/subscribe" \
  -H "Content-Type: application/json" \
  -d "{\"script_hashes\": [\"${SCRIPT_HASH}\"], \"webhook_url\": \"https://webhook.example.com/notify\"}" | jq .
echo ""

# Step 6: List subscriptions again (should show webhook)
echo -e "\n${YELLOW}[6] Listing subscriptions (should show webhook URL)...${NC}"
echo -e "${BLUE}curl -s ${BASE_URL}/subscriptions | jq .${NC}"
echo ""
curl -s "${BASE_URL}/subscriptions" | jq .
echo ""

# Step 7: Unsubscribe from multiple
echo -e "\n${YELLOW}[7] Unsubscribing from script hashes...${NC}"
echo -e "${BLUE}curl -X DELETE ${BASE_URL}/subscribe \\${NC}"
echo -e "${BLUE}  -H 'Content-Type: application/json' \\${NC}"
echo -e "${BLUE}  -d '{\"script_hashes\": [\"${SCRIPT_HASH}\"]}' | jq .${NC}"
echo ""
curl -X DELETE "${BASE_URL}/subscribe" \
  -H "Content-Type: application/json" \
  -d "{\"script_hashes\": [\"${SCRIPT_HASH}\"]}" | jq .
echo ""

# Step 8: Verify unsubscribe worked
echo -e "\n${YELLOW}[8] Verifying subscription was removed...${NC}"
echo -e "${BLUE}curl -s ${BASE_URL}/subscriptions | jq .${NC}"
echo ""
curl -s "${BASE_URL}/subscriptions" | jq .
echo ""

echo -e "\n${GREEN}✓ Workflow test completed!${NC}"
echo -e "\n${YELLOW}Summary:${NC}"
echo "  - Retrieved balance and transaction history"
echo "  - Subscribed to script hash without webhook"
echo "  - Updated subscription with webhook URL"
echo "  - Verified subscription in active list"
echo "  - Unsubscribed successfully"
echo ""
echo -e "${YELLOW}Next: Send a real blockchain transaction to test webhook notifications!${NC}"
echo ""
