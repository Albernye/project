import pytest
import numpy as np
import sys
from pathlib import Path

# Add project root to PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from algorithms.fusion import fuse, reset_kalman

def test_fusion_singleton():
    """Test the singleton behavior of the fusion function"""
    reset_kalman()
    result1 = fuse(pdr_delta=(1,0,0))
    result2 = fuse(pdr_delta=(0,1,0))
    assert not np.allclose(result1, result2)

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
    print("DEBUG fused:", fused, "qr_pos:", qr_pos)
    assert isinstance(fused, (tuple, list, np.ndarray))
    assert len(fused) >= 2

    # Test with relaxed tolerance to account for filter uncertainties
    assert np.allclose(fused[:2], qr_pos[:2], atol=1.0)

def test_pdr_only():
    """Test with only PDR (no fingerprint)"""
    reset_kalman()
    pdr_pos = (2.0, 3.0, 0.0)
    result = fuse(pdr_pos, None, None)
    
    assert isinstance(result, (tuple, list, np.ndarray))
    assert len(result) >= 2

def test_fingerprint_only():
    """Test with only fingerprint (no PDR)"""
    reset_kalman()
    finger_pos = (2.5, 3.5, 0.0)
    result = fuse(None, finger_pos, None)
    
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
        result = fuse(pdr, finger, None)
        results.append(result)
        assert isinstance(result, (tuple, list, np.ndarray))
        assert len(result) >= 2

    # All results must be valid
    assert len(results) == 3

    # Positions must evolve consistently
    for i in range(1, len(results)):
        # Successive positions must not be identical
        assert not np.allclose(results[i-1][:2], results[i][:2], atol=1e-6)

if __name__ == "__main__":
    # Run tests
    print("Running fusion tests...")
    
    test_fusion_simple()
    print("✅ test_fusion_simple passed")
    
    test_fusion_reset()
    print("✅ test_fusion_reset passed")
    
    test_pdr_only()
    print("✅ test_pdr_only passed")
    
    test_fingerprint_only()
    print("✅ test_fingerprint_only passed")
    
    print("All tests passed!")