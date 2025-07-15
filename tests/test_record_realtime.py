import sys
from pathlib import Path
# Ajoute le dossier racine du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pandas as pd
from scripts.record_realtime import record_realtime

@pytest.fixture
def dummy_folder(tmp_path):
    folder = tmp_path / "2-201_test"
    folder.mkdir()
    df = pd.DataFrame({
        "timestamp": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "x": [0]*11,
        "y": [1]*11,
        "z": [2]*11
    })
    df.to_csv(folder / "accelerometer.csv", index=False)
    return folder

@pytest.fixture
def patch_recordings_dir(monkeypatch, tmp_path):
    from scripts import record_realtime as rr_mod
    monkeypatch.setattr(rr_mod, "RECORDINGS_DIR", tmp_path / "recordings")
    return rr_mod

def test_record_realtime_creates_file(dummy_folder, patch_recordings_dir, tmp_path):
    result = patch_recordings_dir.record_realtime(dummy_folder, "127.0.0.1")
    assert result is True
    rec_dir = tmp_path / "recordings" / "door_2-201"
    files = list(rec_dir.glob("recording_*.csv"))
    assert files, "No recording file created"
