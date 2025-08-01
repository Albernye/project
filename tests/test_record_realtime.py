import sys
from pathlib import Path
# Ajoute le dossier racine du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pandas as pd
from scripts.record_realtime import record_realtime

@pytest.fixture
def dummy_folder(tmp_path):
    folder = tmp_path / "2-01_test"
    folder.mkdir()
    df = pd.DataFrame({
        "seconds_elapsed": list(range(11)),
        "x": [0]*11,
        "y": [1]*11,
        "z": [2]*11
    })
    df.to_csv(folder / "accelerometer.csv", index=False)
    return folder

@pytest.fixture
def patch_recordings_dir(monkeypatch, tmp_path):
    from scripts.utils import cfg
    monkeypatch.setattr(cfg, "RECORDINGS_DIR", tmp_path / "recordings")
    return cfg

def test_record_realtime_creates_file(dummy_folder, patch_recordings_dir, tmp_path):
    result = record_realtime(dummy_folder, "127.0.0.1")
    assert result is True
    rec_dir = tmp_path / "recordings" / "door_2-01"
    files = list(rec_dir.glob("recording_*.csv"))
    assert files, "No recording file created"
    df = pd.read_csv(files[0])
    assert len(df) == 11
    assert "timestamp" in df.columns
