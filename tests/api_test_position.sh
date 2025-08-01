#!/bin/bash
# Usage: bash tests/api_test_position.sh [NUM_ROOM]
# Ex : bash tests/api_test_position.sh 201

# Numéro de salle passé en argument, ou 201 par défaut
ROOM="${1:-201}"

echo "=== GET /position?room=${ROOM} ==="
curl -s "http://127.0.0.1:5000/position?room=${ROOM}" | jq .