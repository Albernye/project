import pytest
from services.geolocate import get_last_qr_position

def test_get_last_qr_position_valid():
    events = [
        {"type": "qr", "timestamp": 1000, "position": [1.0, 1.0]},
        {"type": "qr", "timestamp": 2000, "position": [2.0, 2.0]},
        {"type": "qr", "timestamp": 1500, "position": [1.5, 1.5]}
    ]
    result = get_last_qr_position(events=events)
    assert result == (2.0, 2.0)

def test_get_last_qr_position_equal_timestamps():
    events = [
        {"type": "qr", "timestamp": 1000, "position": [0.0, 0.0]},
        {"type": "qr", "timestamp": 1000, "position": [1.0, 1.0]},
    ]
    result = get_last_qr_position(events=events)
    assert result == (1.0, 1.0)

def test_get_last_qr_position_no_qr():
    events = [
        {"type": "wifi", "timestamp": 1000, "position": [1.0, 1.0]},
        {"type": "imu", "timestamp": 2000}
    ]
    result = get_last_qr_position(events=events)
    assert result is None

def test_get_last_qr_position_missing_position():
    events = [
        {"type": "qr", "timestamp": 1000},  # pas de position
        {"type": "qr", "timestamp": 1500, "position": None}
    ]
    result = get_last_qr_position(events=events)
    assert result is None

def test_get_last_qr_position_invalid_position_format():
    events = [
        {"type": "qr", "timestamp": 1500, "position": "not_a_list"},
        {"type": "qr", "timestamp": 1501, "position": [1.0]},  # 1 seule coordonnée
    ]
    result = get_last_qr_position(events=events)
    assert result is None
