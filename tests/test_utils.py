import sys
from pathlib import Path
# Ajoute le dossier racine du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from scripts.utils import get_room_position, load_room_positions, default_pdr_row

@pytest.fixture
def room_csv(tmp_path):
    csv = tmp_path / "room_positions.csv"
    csv.write_text("room,position_x,position_y\n2-201,2.0,41.4\n")
    return csv

def test_get_room_position(room_csv):
    positions = load_room_positions(str(room_csv))
    assert "2-201" in positions
    assert positions["2-201"] == (2.0, 41.4)

def test_default_pdr_row():
    row = default_pdr_row()
    assert "timestamp" in row
    assert "POSI_X" in row
    assert "POSI_Y" in row
