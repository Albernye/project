import pytest
from algorithms.filters import KalmanFilter
from algorithms.fusion import fuse
from algorithms.PDR import PDR
import numpy as np

@pytest.fixture
def kalman():
    return KalmanFilter()

@pytest.fixture
def pdr():
    return PDR()

def test_kalman_reset(kalman):
    # Test QR reset functionality
    kalman.reset_state((5, 3, 2))
    assert kalman.x.flatten().tolist() == [5, 3, 2]
    assert np.allclose(kalman.P, np.eye(3))

def test_pdr_rotation(pdr):
    # Test rotation compensation (10x higher angular velocity to account for 0.1 factor)
    step = pdr._apply_rotation((1, 0, 0), [0, 0, np.pi/2 * 10], 0)
    assert np.allclose(step, [0, 1, 0], atol=0.1)

def test_fusion_singleton():
    # Test singleton pattern in fusion
    result1 = fuse((1, 0, 0), (0.9, 0.1, 0), None)
    result2 = fuse((0, 1, 0), (0.2, 1.1, 0), None)
    assert not np.allclose(result1, result2)

def test_full_integration(kalman, pdr):
    # Full integration test
    # Simulate movement with floor change
    imu_data = [
        ([2.8, 0, 9.8], [0, 0, 0], 0),      # Step forward
            ([3.0, 0, 9.8], [0, 0, 15.7], 1),   # Rotation de 90 degrés (π/2 rad * 10)
        ([2.7, 0, 9.8], [0, 0, 0], 1)       # Step on new floor
    ]
    
    positions = []
    for accel, gyro, floor in imu_data:
        pdr.process_imu_data(accel, gyro, floor)
        positions.append(pdr.kf.get_state())
    
    # Verify final position and orientation
    final_pos = positions[-1]
    assert final_pos[2] == 1  # Correct floor
    assert abs(final_pos[0]) < 0.5  # Should face Y axis after rotation
    assert final_pos[1] > 0.6  # Should have moved forward

def test_no_movement_case():
    # Test with no movement data
    from algorithms.fusion import reset_kalman
    reset_kalman()
    result = fuse(None, None, None)
    assert np.allclose(result, (0, 0, 0), atol=1e-3)
