import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch
from algorithms.fingerprint import fingerprint, set_origin
import sys
from pathlib import Path
# Ajoute le dossier racine du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def test_fingerprint_predictions():
    knntrainfile = "dummy_knntrainfile.csv"
    FPfile = "dummy_FPfile.csv"
    kP, kZ = 2, 2

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
    set_origin(mock_train_data['long'].iloc[0],mock_fp_data['lat'].iloc[0])
    with patch('pandas.read_csv', side_effect=[mock_fp_data, mock_train_data]):
        result = fingerprint(knntrainfile, FPfile, kP=kP, kZ=kZ)
        # Should return a 3‑tuple (x, y, floor)
        assert isinstance(result, tuple) and len(result) == 3
        x, y, f = result
        assert isinstance(x, float) and isinstance(y, float)
        assert isinstance(f, int)