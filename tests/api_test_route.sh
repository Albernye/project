#!/bin/bash
curl -s "http://127.0.0.1:5000/route?from=201&to=202" | jq .
