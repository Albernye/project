import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch
from algorithms.fingerprint import euclidean_distance, fingerprint
import sys
from pathlib import Path
# Ajoute le dossier racine du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
    kP, kZ, R = 2, 2, 5.0  

    # Mock data to avoid reading files during test
    mock_train_data = pd.DataFrame({
        'rssi1': [-50, -55],
        'rssi2': [-60, -65],
        'long': [11.111628329564, 11.111567743893],
        'lat': [49.461219385271, 49.46132292478],
        'Z': [0, 1]
    })

    mock_fp_data = pd.DataFrame({
        'time': [0],
        'rssi1': [-52],
        'rssi2': [-62],
        'long': [11.111628329564],
        'lat': [49.461219385271],
        'Z': [0]
    })

    # Use mock to simulate reading CSV files
    with patch('pandas.read_csv', side_effect=[mock_fp_data, mock_train_data]):
        predictions = fingerprint(knntrainfile, FPfile, kP, kZ, R)
        # Check the shape of predictions
        assert predictions.shape[1] == 3  # long, lat, Z
        assert predictions.shape[0] == 1  # According to mock_fp_data