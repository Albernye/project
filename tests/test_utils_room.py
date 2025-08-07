import sys
from pathlib import Path
# Ajoute le dossier racine du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from services.utils import load_room_positions, get_room_position

@pytest.fixture
def room_csv(tmp_path):
    csv = tmp_path / "room_positions.csv"
    csv.write_text("room,position_x,position_y\n2-201,2.0,41.4\n")
    return csv

@pytest.fixture
def patch_room_cache(monkeypatch):
    import services.utils as utils_mod
    utils_mod._room_positions_cache = None
    monkeypatch.setattr(utils_mod, "load_room_positions", lambda path: {"2-201": (2.0, 41.4)})
    return utils_mod

def test_load_room_positions(room_csv):
    positions = load_room_positions(str(room_csv))
    assert "2-201" in positions
    assert positions["2-201"] == (2.0, 41.4)

def test_get_room_position(patch_room_cache):
    pos = patch_room_cache.get_room_position("2-201")
    assert pos == (2.0, 41.4)
