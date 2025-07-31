import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import sys

# Ajouter le dossier racine du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from algorithms.filters import load_imu
from algorithms.PDR import pdr_delta

@ pytest.fixture
def simple_pdr_data(tmp_path):
    """Crée un fichier CSV PDR simple pour test basique"""
    N = 100
    timestamps = np.linspace(0, 10, N)
    walking_freq = 1.8
    acce_x = 0.5 * np.sin(2 * np.pi * walking_freq * timestamps)
    acce_y = 9.8 + 2.0 * np.sin(2 * np.pi * walking_freq * timestamps + np.pi/2)
    acce_z = 0.3 * np.sin(2 * np.pi * walking_freq * timestamps + np.pi/4)
    acce_mod = np.sqrt(acce_x**2 + acce_y**2 + acce_z**2)
    gyro_x = 0.1 * np.sin(0.5 * timestamps)
    gyro_y = 0.1 * np.cos(0.5 * timestamps)
    gyro_z = 0.05 * np.sin(0.2 * timestamps)
    gyro_mod = np.sqrt(gyro_x**2 + gyro_y**2 + gyro_z**2)

    df = pd.DataFrame({
        'timestamp': timestamps,
        'ACCE_X': acce_x,
        'ACCE_Y': acce_y,
        'ACCE_Z': acce_z,
        'ACCE_MOD': acce_mod,
        'GYRO_X': gyro_x,
        'GYRO_Y': gyro_y,
        'GYRO_Z': gyro_z,
        'GYRO_MOD': gyro_mod,
    })
    path = tmp_path / "simple_pdr.csv"
    df.to_csv(path, sep=';', index=False)
    return str(path)

@ pytest.fixture
def stationary_pdr_data(tmp_path):
    """Crée des données PDR stationnaires (pas de mouvement)"""
    N = 50
    timestamps = np.linspace(0, 5, N)
    noise = 0.1
    acce_x = np.random.normal(0, noise, N)
    acce_y = np.random.normal(9.8, noise, N)
    acce_z = np.random.normal(0, noise, N)
    acce_mod = np.sqrt(acce_x**2 + acce_y**2 + acce_z**2)
    gyro_noise = 0.01
    gyro_x = np.random.normal(0, gyro_noise, N)
    gyro_y = np.random.normal(0, gyro_noise, N)
    gyro_z = np.random.normal(0, gyro_noise, N)
    gyro_mod = np.sqrt(gyro_x**2 + gyro_y**2 + gyro_z**2)

    df = pd.DataFrame({
        'timestamp': timestamps,
        'ACCE_X': acce_x,
        'ACCE_Y': acce_y,
        'ACCE_Z': acce_z,
        'ACCE_MOD': acce_mod,
        'GYRO_X': gyro_x,
        'GYRO_Y': gyro_y,
        'GYRO_Z': gyro_z,
        'GYRO_MOD': gyro_mod,
    })
    path = tmp_path / "stationary_pdr.csv"
    df.to_csv(path, sep=';', index=False)
    return str(path)

@ pytest.mark.parametrize("csv_data", ["simple_pdr_data", "stationary_pdr_data"])
def test_pdr_returns_floats(csv_data, request):
    """Test que pdr_delta renvoie des floats sans erreur"""
    csv_path = request.getfixturevalue(csv_data)
    accel, gyro, fs = load_imu(csv_path)
    dx, dy = pdr_delta(accel, gyro, fs)
    assert isinstance(dx, float)
    assert isinstance(dy, float)


def test_pdr_stationary_behavior(stationary_pdr_data):
    """Test comportement PDR avec données stationnaires (≈0 déplacement)"""
    accel, gyro, fs = load_imu(stationary_pdr_data)
    dx, dy = pdr_delta(accel, gyro, fs)
    assert abs(dx) < 0.5 and abs(dy) < 0.5


def test_pdr_numerical_stability(simple_pdr_data):
    """Test qu'il n'y a pas de NaN/Inf"""
    accel, gyro, fs = load_imu(simple_pdr_data)
    dx, dy = pdr_delta(accel, gyro, fs)
    assert not np.isnan(dx) and not np.isinf(dx)
    assert not np.isnan(dy) and not np.isinf(dy)


def test_pdr_various_lengths(tmp_path):
    """Test robustesse sur différentes tailles de données"""
    for N in [30, 50, 200]:
        timestamps = np.linspace(0, N/20, N)
        signal = 0.5 * np.sin(2 * np.pi * 1.5 * timestamps)
        df = pd.DataFrame({
            'timestamp': timestamps,
            'ACCE_X': signal,
            'ACCE_Y': 9.8 + signal,
            'ACCE_Z': np.zeros(N),
            'ACCE_MOD': np.sqrt(signal**2 + (9.8+signal)**2),
            'GYRO_X': np.zeros(N),
            'GYRO_Y': np.zeros(N),
            'GYRO_Z': np.zeros(N),
            'GYRO_MOD': np.zeros(N),
        })
        path = tmp_path / f"varlen_{N}.csv"
        df.to_csv(path, sep=';', index=False)
        accel, gyro, fs = load_imu(str(path))
        dx, dy = pdr_delta(accel, gyro, fs)
        assert isinstance(dx, float) and isinstance(dy, float)
        # pas d'erreur et renvoie float
