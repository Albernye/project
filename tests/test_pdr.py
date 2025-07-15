import pytest
import numpy as np
import pandas as pd
from algorithms.PDR import PDR
import sys
from pathlib import Path

# Ajoute le dossier racine du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
        thetas, positions = PDR(simple_pdr_data)
        assert thetas is not None
        assert positions is not None
        assert len(thetas) >= 0  # Peut être vide si pas de pas détectés
        assert positions.shape[1] == 2  # Colonnes x, y
        print(f"✅ PDR executed successfully. Steps detected: {len(thetas)}")
        print(f"Final position: {positions[-1] if len(positions) > 0 else 'None'}")
    except Exception as e:
        pytest.fail(f"PDR raised an exception: {e}")

def test_pdr_stationary_behavior(stationary_pdr_data):
    """Test comportement PDR avec données stationnaires"""
    thetas, positions = PDR(stationary_pdr_data)
    
    # Avec des données stationnaires, peu ou pas de pas devraient être détectés
    assert len(thetas) <= 2, f"Too many steps detected for stationary data: {len(thetas)}"
    
    if len(positions) > 1:
        # Le mouvement total devrait être minimal
        total_distance = np.linalg.norm(positions[-1] - positions[0])
        assert total_distance < 1.0, f"Too much movement for stationary data: {total_distance}m"
    
    print(f"✅ Stationary test passed. Steps: {len(thetas)}, Final pos: {positions[-1] if len(positions) > 0 else 'None'}")

def test_pdr_output_format(simple_pdr_data):
    """Test format des sorties PDR"""
    thetas, positions = PDR(simple_pdr_data)
    
    # Vérifier les types
    assert isinstance(thetas, np.ndarray), "thetas should be numpy array"
    assert isinstance(positions, np.ndarray), "positions should be numpy array"
    
    # Vérifier les dimensions
    assert thetas.ndim == 1, "thetas should be 1D array"
    assert positions.ndim == 2, "positions should be 2D array"
    assert positions.shape[1] == 2, "positions should have 2 columns (x, y)"
    
    # Vérifier la cohérence des tailles
    if len(thetas) > 0:
        # positions inclut la position initiale (0,0), donc +1
        assert positions.shape[0] == len(thetas) + 1, f"Inconsistent sizes: {positions.shape[0]} vs {len(thetas) + 1}"
    
    print(f"✅ Format test passed. Thetas shape: {thetas.shape}, Positions shape: {positions.shape}")

def test_pdr_numerical_stability(simple_pdr_data):
    """Test stabilité numérique"""
    thetas, positions = PDR(simple_pdr_data)
    
    # Vérifier qu'il n'y a pas de NaN ou Inf
    assert not np.any(np.isnan(thetas)), "NaN values found in thetas"
    assert not np.any(np.isinf(thetas)), "Inf values found in thetas"
    assert not np.any(np.isnan(positions)), "NaN values found in positions"
    assert not np.any(np.isinf(positions)), "Inf values found in positions"
    
    # Vérifier des valeurs raisonnables
    if len(thetas) > 0:
        assert np.all(np.abs(thetas) <= 2 * np.pi), "Theta values seem unreasonable"
    
    if len(positions) > 0:
        max_distance = np.max(np.linalg.norm(positions, axis=1))
        assert max_distance < 100, f"Position values seem unreasonable: {max_distance}m"
    
    print(f"✅ Numerical stability test passed")

def test_pdr_initial_position(simple_pdr_data):
    """Test position initiale"""
    thetas, positions = PDR(simple_pdr_data)
    
    # La première position devrait être (0, 0)
    if len(positions) > 0:
        assert np.allclose(positions[0], [0, 0], atol=1e-6), f"Initial position should be (0,0), got {positions[0]}"
    
    print(f"✅ Initial position test passed")

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
        
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df.to_csv(f.name, sep=';', index=False)
            try:
                thetas, positions = PDR(f.name)
                assert positions.shape[1] == 2, f"Failed for N={N}"
                print(f"✅ Size test passed for N={N}")
            except Exception as e:
                pytest.fail(f"PDR failed for N={N}: {e}")
            finally:
                import os
                os.unlink(f.name)

if __name__ == "__main__":
    # Pour exécuter les tests directement
    pytest.main([__file__, "-v"])