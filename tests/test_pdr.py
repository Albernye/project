import pytest
import numpy as np
import pandas as pd
from algorithms.PDR import PDR

@pytest.fixture
def pdr(tmp_path):
    """
    Crée un CSV minimal que PDR peut ingérer, puis instancie PDR dessus.
    """
    # Générer 200 échantillons pour simuler des données
    N = 200
    timestamps = np.linspace(0, 5, N)
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

def test_pdr_rotation(pdr):
    # Teste la compensation de rotation (10x la vitesse angulaire pour tenir compte du facteur 0.1)
    step = pdr._apply_rotation((1, 0, 0), [0, 0, np.pi/2 * 10], 0)
    assert np.allclose(step, [0, 1, 0], atol=0.1)
