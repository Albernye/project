import pytest
import numpy as np
from algorithms.filters import KalmanFilter
import sys
from pathlib import Path
# Ajoute le dossier racine du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

@pytest.fixture
def kalman():
    return KalmanFilter()

def test_kalman_reset(kalman):
    # Test de la fonctionnalité de réinitialisation QR
    kalman.reset_state((5, 3, 2))
    assert kalman.x.flatten().tolist() == [5, 3, 2]
    assert np.allclose(kalman.P, np.eye(3))
