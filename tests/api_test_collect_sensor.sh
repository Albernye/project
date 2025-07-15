#!/bin/bash
curl -s -X POST http://127.0.0.1:5000/collect_sensor_data \
     -H 'Content-Type: application/json' \
     -d '{"room":"201","accelerometer":[{"x":0,"y":1,"z":0}]}' | jq .
