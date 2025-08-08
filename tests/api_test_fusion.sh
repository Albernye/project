#!/bin/bash
#
# Simulate calls to algorithms.fusion.fuse() to check PDR / fingerprint flags.

python3 << 'EOF'
import json
from algorithms.fusion import fuse, reset_kalman

ROOM = "201"

def run_test(pdr):
    reset_kalman()
    result = fuse(pdr_pos=pdr,
                  finger_pos=None,
                  qr_reset=None,
                  room=ROOM)
    # Display the results
    lat, lon, floor = result
    sources = {
        "pdr":   pdr is not None,
        "finger": False,
        "qr_reset": False
    }
    print(json.dumps({
        "input": {"pdr": pdr, "finger": finger},
        "output": {"position": [lat, lon, floor], "sources": sources}
    }, ensure_ascii=False))
    
print("=== Test PDR seul ===")
run_test([0.1, -0.05])

print("\n=== Test Fingerprint seul ===")
run_test([41.406, 2.195])

print("\n=== Test PDR + Fingerprint ===")
run_test([0.2, 0.1])
EOF
