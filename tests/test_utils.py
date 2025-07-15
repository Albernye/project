from scripts.utils import get_room_position, load_room_positions, default_pdr_row

def test_get_room_position(tmp_path):
    # Crée un CSV temporaire
    csv = tmp_path / "room_positions.csv"
    csv.write_text("room,position_x,position_y\n2-201,2.0,41.4\n")
    positions = load_room_positions(str(csv))
    assert "2-201" in positions
    assert positions["2-201"] == (2.0, 41.4)

def test_default_pdr_row():
    row = default_pdr_row()
    assert "timestamp" in row
    assert "POSI_X" in row
    assert "POSI_Y" in row
