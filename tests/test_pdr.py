import pytest
import numpy as np
import pandas as pd
from algorithms.PDR import pdr_delta
import sys
from pathlib import Path

# Ajoute le dossier racine du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def load_test_imu(csv_path):
    df = pd.read_csv(csv_path, sep=';')
    accel = df[['ACCE_X','ACCE_Y','ACCE_Z']].values
    gyro_deg = df[['GYRO_X','GYRO_Y','GYRO_Z']].values
    gyro = np.deg2rad(gyro_deg)
    timestamps = df['timestamp'].values
    fs = 1.0/np.mean(np.diff(timestamps))
    return accel, gyro, fs

@pytest.fixture
def simple_pdr_data(tmp_path):
    """Crée des données PDR simples pour test basique"""
    N = 100
    timestamps = np.linspace(0, 10, N)  # 10 secondes
    
    # Accélération simulant la marche (oscillations périodiques)
    walking_freq = 2.0  # 2 Hz, soit 2 pas par seconde
    t = timestamps
    
    # Simulation d'accélération de marche
    acce_x = 0.5 * np.sin(2 * np.pi * walking_freq * t)
    acce_y = 9.8 + 2.0 * np.sin(2 * np.pi * walking_freq * t + np.pi/2)  # gravité + oscillations
    acce_z = 0.3 * np.sin(2 * np.pi * walking_freq * t + np.pi/4)
    
    acce_mod = np.sqrt(acce_x**2 + acce_y**2 + acce_z**2)
    
    # Gyroscope avec une légère rotation (tournant lentement)
    gyro_x = 0.1 * np.sin(0.5 * t)
    gyro_y = 0.1 * np.cos(0.5 * t)
    gyro_z = 0.05 * np.sin(0.2 * t)  # Yaw lent
    
    gyro_mod = np.sqrt(gyro_x**2 + gyro_y**2 + gyro_z**2)
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'long': np.full(N, 2.0),
        'lat': np.full(N, 41.4),
        # POSI_X[0] != 0 pour éviter la boucle infinie dans PDR
        'POSI_X': np.concatenate(([1.0], np.zeros(N-1))),
        'POSI_Y': np.zeros(N),
        # Données d'accélération réalistes
        'ACCE_X': acce_x,
        'ACCE_Y': acce_y,
        'ACCE_Z': acce_z,
        'ACCE_MOD': acce_mod,
        # Données de gyroscope réalistes
        'GYRO_X': gyro_x,
        'GYRO_Y': gyro_y,
        'GYRO_Z': gyro_z,
        'GYRO_MOD': gyro_mod,
        # Magnétomètre (pas utilisé dans PDR mais présent)
        'MAGN_X': np.zeros(N),
        'MAGN_Y': np.zeros(N),
        'MAGN_Z': np.zeros(N),
        'MAGN_MOD': np.zeros(N),
    })
    
    csv_path = tmp_path / "simple_pdr.csv"
    df.to_csv(csv_path, sep=';', index=False)
    return str(csv_path)

@pytest.fixture
def stationary_pdr_data(tmp_path):
    """Crée des données PDR stationnaires (pas de mouvement)"""
    N = 50
    timestamps = np.linspace(0, 5, N)
    
    # Accélération stationnaire (juste la gravité avec du bruit)
    noise_level = 0.1
    acce_x = np.random.normal(0, noise_level, N)
    acce_y = np.random.normal(9.8, noise_level, N)  # gravité
    acce_z = np.random.normal(0, noise_level, N)
    
    acce_mod = np.sqrt(acce_x**2 + acce_y**2 + acce_z**2)
    
    # Gyroscope stationnaire (bruit faible)
    gyro_noise = 0.01
    gyro_x = np.random.normal(0, gyro_noise, N)
    gyro_y = np.random.normal(0, gyro_noise, N)
    gyro_z = np.random.normal(0, gyro_noise, N)
    
    gyro_mod = np.sqrt(gyro_x**2 + gyro_y**2 + gyro_z**2)
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'long': np.full(N, 2.0),
        'lat': np.full(N, 41.4),
        'POSI_X': np.concatenate(([1.0], np.zeros(N-1))),
        'POSI_Y': np.zeros(N),
        'ACCE_X': acce_x,
        'ACCE_Y': acce_y,
        'ACCE_Z': acce_z,
        'ACCE_MOD': acce_mod,
        'GYRO_X': gyro_x,
        'GYRO_Y': gyro_y,
        'GYRO_Z': gyro_z,
        'GYRO_MOD': gyro_mod,
        'MAGN_X': np.zeros(N),
        'MAGN_Y': np.zeros(N),
        'MAGN_Z': np.zeros(N),
        'MAGN_MOD': np.zeros(N),
    })
    
    csv_path = tmp_path / "stationary_pdr.csv"
    df.to_csv(csv_path, sep=';', index=False)
    return str(csv_path)

def test_pdr_basic_functionality(simple_pdr_data):
    """Test que PDR fonctionne sans erreur"""
    try:
        accel, gyro, fs = load_test_imu(simple_pdr_data)
        dx, dy = pdr_delta(accel, gyro, fs)
            # Should return numeric deltas
        assert isinstance(dx, float) and isinstance(dy, float)    
    except Exception as e:
        pytest.fail(f"PDR raised an exception: {e}")

def test_pdr_stationary_behavior(stationary_pdr_data):
    """Test comportement PDR avec données stationnaires"""
    accel, gyro, fs = load_test_imu(stationary_pdr_data)
    dx, dy = pdr_delta(accel, gyro, fs)
    assert abs(dx) < 0.5 and abs(dy) < 0.5

def test_pdr_output_format(simple_pdr_data):
    """Test format des sorties PDR"""
    accel, gyro, fs = load_test_imu(simple_pdr_data)
    dx, dy = pdr_delta(accel, gyro, fs)
    assert isinstance(dx, float)
    assert isinstance(dy, float)    
    

def test_pdr_numerical_stability(simple_pdr_data):
    """Test stabilité numérique"""
    accel, gyro, fs = load_test_imu(simple_pdr_data)
    dx, dy = pdr_delta(accel, gyro, fs)
    
    # Vérifier qu'il n'y a pas de NaN ou Inf
    assert not np.any(np.isnan(dx)), "NaN values found in dx"
    assert not np.any(np.isinf(dx)), "Inf values found in dx"
    assert not np.any(np.isnan(dy)), "NaN values found in dy"
    assert not np.any(np.isinf(dy)), "Inf values found in dy"
    
    print(f"✅ Numerical stability test passed")


def test_pdr_different_data_sizes():
    """Test avec différentes tailles de données"""
    for N in [30, 50, 200]:  # Commence à 30 pour éviter les problèmes de filtfilt
        # Créer des données temporaires
        timestamps = np.linspace(0, N/20, N)  # Fréquence variable
        
        # Ajouter un peu de variation pour simuler de la marche
        walking_signal = 0.5 * np.sin(2 * np.pi * 2.0 * timestamps)  # 2 Hz
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'long': np.full(N, 2.0),
            'lat': np.full(N, 41.4),
            'POSI_X': np.concatenate(([1.0], np.zeros(N-1))),
            'POSI_Y': np.zeros(N),
            'ACCE_X': walking_signal,
            'ACCE_Y': np.full(N, 9.8) + walking_signal,
            'ACCE_Z': np.zeros(N),
            'ACCE_MOD': np.sqrt(walking_signal**2 + (9.8 + walking_signal)**2),
            'GYRO_X': np.zeros(N),
            'GYRO_Y': np.zeros(N),
            'GYRO_Z': np.zeros(N),
            'GYRO_MOD': np.zeros(N),
            'MAGN_X': np.zeros(N),
            'MAGN_Y': np.zeros(N),
            'MAGN_Z': np.zeros(N),
            'MAGN_MOD': np.zeros(N),
        })

if __name__ == "__main__":
    # Pour exécuter les tests directement
    pytest.main([__file__, "-v"])