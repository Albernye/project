import pytest
import numpy as np
import pandas as pd
from algorithms.PDR import PDR 

import sys
from pathlib import Path
# Ajoute le dossier racine du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

@pytest.fixture
def pdr(tmp_path):
    N = 200
    timestamps = np.linspace(0, 5, N)  # N points, index 0 à N-1
    df = pd.DataFrame({
        'timestamp': timestamps,
        'long':      np.full(N, 2.0),
        'lat':       np.full(N, 41.4),
        # POSI_X[0] != 0 pour éviter la boucle infinie dans PDR
        'POSI_X':    np.concatenate(([1.0], np.zeros(N-1))),
        'POSI_Y':    np.zeros(N),
        # Accélération avec gravité et petite variation
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
    # On passe le chemin au constructeur PDR
    return PDR(str(csv_path))

def test_pdr_initialization(pdr):
    df, trajectory = pdr
    assert df is not None
    assert trajectory.shape[1] == 2