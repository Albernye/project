import pytest
import pandas as pd
from pathlib import Path
import sys
from pathlib import Path
# Ajoute le dossier racine du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.init_stats import process_room_data, init_stats
from scripts.utils import cfg

@pytest.fixture
def dummy_raw_folder(tmp_path):
    # Crée un dossier raw/2-01_abc avec un fichier capteur minimal
    raw_dir = tmp_path / "raw"
    folder = raw_dir / "2-01_abc"
    folder.mkdir(parents=True)
    # Fichier capteur minimal (au moins 15 lignes pour être sûr)
    df = pd.DataFrame({
        "time": list(range(20)),  # 20 lignes pour être sûr
        "x": [0]*20,
        "y": [1]*20,
        "z": [2]*20
    })
    df.to_csv(folder / "accelerometer.csv", index=False)
    return raw_dir

def test_process_room_data(tmp_path, dummy_raw_folder, monkeypatch):
    # Patch cfg.RAW_DIR and cfg.STATS_DIR to use tmp_path
    monkeypatch.setattr(cfg, "RAW_DIR", dummy_raw_folder)
    monkeypatch.setattr(cfg, "STATS_DIR", tmp_path / "stats")

    (cfg.STATS_DIR).mkdir(exist_ok=True)

    processed_dir = tmp_path / "processed"
    processed_dir.mkdir(exist_ok=True)
     
    folder = next(dummy_raw_folder.iterdir())
    room = "2-01"
    
    result = process_room_data(folder, room, processed_dir)
    assert result is True
    # Vérifie que le fichier processed existe
    processed_files = list(processed_dir.glob("room_2-01_processed.csv"))
    assert processed_files, "Processed file not created"
    # Vérifie que le fichier stats existe
    stats_files = list((tmp_path / "stats").glob("room_2-01.csv"))
    assert stats_files, "Stats file not created"
