#!/bin/bash
#
# Simulate calls to algorithms.fusion.fuse() to check PDR / QR / fingerprint flags.

python3 << 'EOF'
import json
from algorithms.fusion import fuse, reset_kalman

ROOM = "201"

def run_test_pdr(pdr):
    reset_kalman()
    result = fuse(pdr_delta=pdr, qr_anchor=None, room=ROOM)
    lat, lon, floor = result
    sources = {
        "pdr": pdr is not None,
        "qr_reset": False
    }
    print(json.dumps({
        "input": {"pdr": pdr},
        "output": {"position": [lat, lon, floor], "sources": sources}
    }, ensure_ascii=False))

def run_test_qr(qr):
    reset_kalman()
    result = fuse(pdr_delta=None, qr_anchor=qr, room=ROOM)
    lat, lon, floor = result
    sources = {
        "pdr": False,
        "qr_reset": True
    }
    print(json.dumps({
        "input": {"qr": qr},
        "output": {"position": [lat, lon, floor], "sources": sources}
    }, ensure_ascii=False))

print("=== Test PDR only ===")
run_test_pdr([0.1, -0.05, 0.0])

print("\n=== Test QR only ===")
run_test_qr((41.406, 2.195, 0.0))

print("\n=== Test PDR + QR (reset then move) ===")
run_test_qr((41.406, 2.195, 0.0))
run_test_pdr([0.2, 0.1, 0.0])
EOF
