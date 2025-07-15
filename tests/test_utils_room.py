import pytest
from scripts.utils import load_room_positions, get_room_position

def test_load_room_positions(tmp_path, monkeypatch):
    csv = tmp_path / "room_positions.csv"
    csv.write_text("room,position_x,position_y\n2-201,2.0,41.4\n")
    positions = load_room_positions(str(csv))
    assert "2-201" in positions
    assert positions["2-201"] == (2.0, 41.4)

def test_get_room_position(tmp_path, monkeypatch):
    csv = tmp_path / "room_positions.csv"
    csv.write_text("room,position_x,position_y\n2-201,2.0,41.4\n")
    # Patch _room_positions_cache and path
    import scripts.utils as utils_mod
    utils_mod._room_positions_cache = None
    monkeypatch.setattr(utils_mod, "load_room_positions", lambda path: {"2-201": (2.0, 41.4)})
    pos = utils_mod.get_room_position("2-201")
    assert pos == (2.0, 41.4)
