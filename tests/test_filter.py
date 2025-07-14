import pytest
import numpy as np
from algorithms.filters import KalmanFilter

@pytest.fixture
def kalman():
    return KalmanFilter()

def test_kalman_reset(kalman):
    # Test de la fonctionnalité de réinitialisation QR
    kalman.reset_state((5, 3, 2))
    assert kalman.x.flatten().tolist() == [5, 3, 2]
    assert np.allclose(kalman.P, np.eye(3))
