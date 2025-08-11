#!/bin/bash
# Integration test: POST to /scan_qr and check for email status in response
set -e
URL="http://127.0.0.1:5000/scan_qr"
ROOM="2-01"
RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" -d "{\"room\": \"$ROOM\"}" $URL)
echo "Response: $RESPONSE"
echo "$RESPONSE" | grep -q 'email' && echo "PASS: Email status present in response" || echo "FAIL: No email status in response"
