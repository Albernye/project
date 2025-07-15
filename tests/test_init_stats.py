import pytest
import pandas as pd
from pathlib import Path
import sys
from pathlib import Path
# Ajoute le dossier racine du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import init_stats

@pytest.fixture
def dummy_raw_folder(tmp_path):
    # Crée un dossier raw/2-201_abc avec un fichier capteur minimal
    raw_dir = tmp_path / "raw"
    folder = raw_dir / "2-201_abc"
    folder.mkdir(parents=True)
    # Fichier capteur minimal
    df = pd.DataFrame({
        "timestamp": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "x": [0]*11,
        "y": [1]*11,
        "z": [2]*11
    })
    df.to_csv(folder / "accelerometer.csv", index=False)
    return raw_dir

def test_process_room_data(tmp_path, dummy_raw_folder, monkeypatch):
    # Patch RAW_DIR and STATS_DIR to use tmp_path
    monkeypatch.setattr(init_stats, "RAW_DIR", dummy_raw_folder)
    monkeypatch.setattr(init_stats, "STATS_DIR", tmp_path / "stats")
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir(exist_ok=True)
    folder = next(dummy_raw_folder.iterdir())
    room = "2-201"
    result = init_stats.process_room_data(folder, room, processed_dir)
    assert result is True
    # Vérifie que le fichier processed existe
    processed_files = list(processed_dir.glob("room_2-201_processed.csv"))
    assert processed_files, "Processed file not created"
    # Vérifie que le fichier stats existe
    stats_files = list((tmp_path / "stats").glob("room_2-201.csv"))
    assert stats_files, "Stats file not created"
