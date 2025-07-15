import pytest
import numpy as np
from algorithms.fusion import fuse, reset_kalman

def test_fusion_singleton():
    # Teste le modèle singleton dans la fusion
    result1 = fuse((1, 0, 0), (0.9, 0.1, 0), None)
    result2 = fuse((0, 1, 0), (0.2, 1.1, 0), None)
    assert not np.allclose(result1, result2)

def test_no_movement_case():
    # Teste le cas sans mouvement
    reset_kalman()
    result = fuse(None, None, None)
    assert np.allclose(result, (0, 0, 0), atol=1e-3)

def test_fusion_simple():
    reset_kalman()
    pos1 = (1.0, 2.0)
    pos2 = (1.1, 2.1)
    fused = fuse(pos1, pos2)
    assert isinstance(fused, (tuple, list, np.ndarray))
    assert len(fused) >= 2

def test_fusion_reset():
    reset_kalman()
    pos = (3.0, 4.0)
    fused = fuse(pos, None, qr_reset=pos)
    assert np.allclose(fused[:2], pos, atol=1e-2)
