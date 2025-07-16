#!/bin/bash
#
# Simule des appels à algorithms.fusion.fuse() pour vérifier les drapeaux PDR / fingerprint.

python3 << 'EOF'
import json
from algorithms.fusion import fuse, reset_kalman

ROOM = "201"

def run_test(pdr, finger):
    reset_kalman()
    result = fuse(pdr_pos=pdr,
                  finger_pos=finger,
                  qr_reset=None,
                  room=ROOM)
    # Affiche les coordonnées + on regarde les flags
    lat, lon, floor = result
    sources = {
        "pdr":   pdr is not None,
        "finger": finger is not None,
        "qr_reset": False
    }
    print(json.dumps({
        "input": {"pdr": pdr, "finger": finger},
        "output": {"position": [lat, lon, floor], "sources": sources}
    }, ensure_ascii=False))
    
print("=== Test PDR seul ===")
run_test([0.1, -0.05], None)

print("\n=== Test Fingerprint seul ===")
run_test(None, [41.406, 2.195])

print("\n=== Test PDR + Fingerprint ===")
run_test([0.2, 0.1], [41.407, 2.196])
EOF
