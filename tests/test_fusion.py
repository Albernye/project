import pytest
import numpy as np
import sys
from pathlib import Path

# Add project root to PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from algorithms.fingerprint import ll_to_local
from algorithms.fusion import fuse, reset_kalman

def test_fusion_singleton():
    """Test that the Kalman filter updates state on successive PDR deltas."""
    reset_kalman()
    result1 = fuse(pdr_delta=(1, 0, 0))
    result2 = fuse(pdr_delta=(0, 1, 0))

    # Use local coordinates to measure actual movement
    x1, y1 = ll_to_local(result1[0], result1[1])
    x2, y2 = ll_to_local(result2[0], result2[1])

    distance_moved = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    assert distance_moved > 0.001, f"Kalman filter did not move enough: {distance_moved} m"

def test_no_movement_case():
    """Test the no movement case"""
    reset_kalman()
    result = fuse()
    assert isinstance(result, (tuple, list, np.ndarray))
    assert len(result) >= 2

def test_fusion_simple():
    """Test basic fusion with two positions (PDR only)"""
    reset_kalman()
    pos1 = (1.0, 2.0, 0.0)
    pos2 = (1.1, 2.1, 0.0)
    fused = fuse(pdr_delta=pos1)
    fused2 = fuse(pdr_delta=pos2)
    assert isinstance(fused, (tuple, list, np.ndarray))
    assert len(fused) >= 2
    assert isinstance(fused[0], (int, float, np.floating))
    assert isinstance(fused[1], (int, float, np.floating))

def test_fusion_reset():
    """Test the reset function with QR code"""
    reset_kalman()
    qr_pos = (3.0, 4.0, 0.0)
    fused = fuse(qr_anchor=qr_pos, room="2-01")
    assert isinstance(fused, (tuple, list, np.ndarray))
    assert len(fused) >= 2

    # Use relaxed tolerance to account for filter smoothing
    assert np.allclose(fused[:2], qr_pos[:2], atol=1.0)

def test_pdr_only():
    """Test with only PDR (no fingerprint)"""
    reset_kalman()
    pdr_pos = (2.0, 3.0, 0.0)
    result = fuse(pdr_delta=pdr_pos)
    assert isinstance(result, (tuple, list, np.ndarray))
    assert len(result) >= 2

def test_fingerprint_only():
    """Test with only fingerprint (no PDR)"""
    reset_kalman()
    finger_pos = (2.5, 3.5, 0.0)
    result = fuse(fingerprint=finger_pos)
    assert isinstance(result, (tuple, list, np.ndarray))
    assert len(result) >= 2

    # Sequence of positions
    positions = [
        ((1.0, 1.0, 0.0), (1.1, 0.9, 0.0)),  # (pdr, fingerprint)
        ((0.1, 0.1, 0.0), (1.2, 1.1, 0.0)),
        ((0.0, 0.1, 0.0), (1.2, 1.2, 0.0)),
    ]
    
    results = []
    for pdr, finger in positions:
        result = fuse(pdr_delta=pdr, fingerprint=finger)
        results.append(result)
        assert isinstance(result, (tuple, list, np.ndarray))
        assert len(result) >= 2

    # Check that successive positions evolve
    for i in range(1, len(results)):
        x_prev, y_prev = ll_to_local(*results[i-1][:2])
        x_curr, y_curr = ll_to_local(*results[i][:2])
        distance = ((x_curr - x_prev)**2 + (y_curr - y_prev)**2)**0.5
        assert distance > 0.001, f"Positions {i-1} and {i} are too close: {distance} m"

if __name__ == "__main__":
    print("Running fusion tests...")
    test_fusion_simple(); print("✅ test_fusion_simple passed")
    test_fusion_reset(); print("✅ test_fusion_reset passed")
    test_pdr_only(); print("✅ test_pdr_only passed")
    test_fingerprint_only(); print("✅ test_fingerprint_only passed")
    test_fusion_singleton(); print("✅ test_fusion_singleton passed")
    test_no_movement_case(); print("✅ test_no_movement_case passed")
    print("All tests passed!")
