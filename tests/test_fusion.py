import pytest
import numpy as np
from algorithms.fusion import fuse, reset_kalman
import sys
from pathlib import Path
# Ajoute le dossier racine du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
    pos1 = (1.0, 2.0, 0.0)
    pos2 = (1.1, 2.1, 0.0)
    fused = fuse(pos1, pos2)
    assert isinstance(fused, (tuple, list, np.ndarray))
    assert len(fused) >= 2

def test_fusion_reset():
    reset_kalman()
    pos = (3.0, 4.0, 0.0)
    fused = fuse(pos, None, qr_reset=pos)
    print("DEBUG fused:", fused, "pos:", pos)
    assert np.allclose(fused[:2], pos[:2], atol=1e-1)  # tolérance augmentée si besoin
