import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch
from algorithms.fingerprint import euclidean_distance, fingerprint

def test_euclidean_distance():
    # Coordonnées de test (longitude, latitude)
    lon1, lat1 = 48.8566, 2.3522  # Paris, France
    lon2, lat2 = 40.7128, -74.0060  # New York, USA

    distance = euclidean_distance(lon1, lat1, lon2, lat2)
    assert distance > 0
    assert isinstance(distance, float)

def test_fingerprint_predictions():
    knntrainfile = "dummy_knntrainfile.csv"
    FPfile = "dummy_FPfile.csv"
    kP, kZ, R = 3, 3, 5.0

    # Mock des données pour éviter de lire les fichiers pendant le test
    mock_train_data = pd.DataFrame({
        'long': [11.111628329564, 11.111567743893],
        'lat': [49.461219385271, 49.46132292478],
        'Z': [0, 1],
        'rssi1': [-50, -55],
        'rssi2': [-60, -65]
    })

    mock_fp_data = pd.DataFrame({
        'rssi1': [-52],
        'rssi2': [-62]
    })

    # Utilisation du mock pour simuler la lecture des fichiers CSV
    with patch('pandas.read_csv', side_effect=[mock_train_data, mock_fp_data]):
        predictions = fingerprint(knntrainfile, FPfile, kP, kZ, R)
        # Vérification du format des prédictions
        assert predictions.shape[1] == 3  # long, lat, Z
        assert predictions.shape[0] == 1  # Selon mock_fp_data
