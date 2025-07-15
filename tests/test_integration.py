import pytest
import numpy as np
from algorithms.filters import KalmanFilter
from algorithms.fusion import fuse
from algorithms.PDR import PDR
import pandas as pd

import sys
from pathlib import Path
# Ajoute le dossier racine du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

@pytest.fixture
def kalman():
    return KalmanFilter()

@pytest.fixture
def pdr(tmp_path):
    # Ce même fixture pourrait être utilisé dans test_pdr.py
    N = 200
    timestamps = np.linspace(0, 5, N)
    df = pd.DataFrame({
        'timestamp': timestamps,
        'long':      np.full(N, 2.0),
        'lat':       np.full(N, 41.4),
        'POSI_X':    np.concatenate(([1.0], np.zeros(N-1))),
        'POSI_Y':    np.zeros(N),
        'ACCE_X':    np.zeros(N),
        'ACCE_Y':    np.ones(N),
        'ACCE_Z':    np.zeros(N),
        'ACCE_MOD':  np.linalg.norm(np.vstack((np.zeros(N), np.ones(N), np.zeros(N))).T, axis=1),
        'GYRO_X':    np.zeros(N),
        'GYRO_Y':    np.zeros(N),
        'GYRO_Z':    np.zeros(N),
        'GYRO_MOD':  np.zeros(N),
        'MAGN_X':    np.zeros(N),
        'MAGN_Y':    np.zeros(N),
        'MAGN_Z':    np.zeros(N),
        'MAGN_MOD':  np.zeros(N),
    })
    csv_path = tmp_path / "dummy_pdr.csv"
    df.to_csv(csv_path, sep=';', index=False)
    return PDR(str(csv_path))

def test_full_integration(kalman, pdr):
    # Test d'intégration complet
    # Simuler un mouvement avec un changement de niveau
    imu_data = [
        ([2.8, 0, 9.8], [0, 0, 0], 0),      # Pas vers l'avant
        ([3.0, 0, 9.8], [0, 0, 15.7], 1),   # Rotation de 90 degrés
        ([2.7, 0, 9.8], [0, 0, 0], 1)       # Pas sur un nouveau niveau
    ]

    positions = []
    for accel, gyro, floor in imu_data:
        pdr.process_imu_data(accel, gyro, floor)
        positions.append(pdr.kf.get_state())

    # Vérifier la position finale et l'orientation
    final_pos = positions[-1]
    assert final_pos[2] == 1  # Bon niveau
    assert abs(final_pos[0]) < 0.5  # Devrait faire face à l'axe Y après rotation
    assert final_pos[1] > 0.6  # Devrait avoir bougé vers l'avant
