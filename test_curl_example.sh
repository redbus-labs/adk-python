#!/bin/bash
# Test script matching the provided curl command

echo "Testing Postgres ADK API Server with curl..."
echo "=============================================="

# Test the /chat endpoint with the exact curl command format
curl --location 'http://localhost:8000/chat' \
  --header 'BUSINESS_UNIT: BUS' \
  --header 'COUNTRY: IND' \
  --header 'Content-Type: application/json' \
  --header 'X-CLIENT: SELF_HELP' \
  --data '{
    "message": "Hi",
    "orderItemUUID": "8dc29a95411be00600ec264701020100"
}' \
  --no-buffer

echo ""
echo "=============================================="
echo "Test completed!"

