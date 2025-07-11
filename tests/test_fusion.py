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
