import pytest
import pandas as pd
from pathlib import Path
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

def test_record_realtime_creates_file(dummy_folder, monkeypatch, tmp_path):
    # Patch RECORDINGS_DIR to tmp_path
    from scripts import record_realtime as rr_mod
    monkeypatch.setattr(rr_mod, "RECORDINGS_DIR", tmp_path / "recordings")
    result = rr_mod.record_realtime(dummy_folder, "127.0.0.1")
    assert result is True
    rec_dir = tmp_path / "recordings" / "door_2-201"
    files = list(rec_dir.glob("recording_*.csv"))
    assert files, "No recording file created"
