#!/bin/bash
curl -s -X POST http://127.0.0.1:5000/confirm_position \
     -H 'Content-Type: application/json' \
     -d '{"room":"201","position":[41.406,2.195]}' | jq .
