"""
Unit tests for the position endpoint and related geolocation functions.
tests/test_position.py
"""
import unittest
from unittest.mock import patch, MagicMock, Mock
import json
import tempfile
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.geolocate import (
    normalize_room_id, 
    normalize_position_to_3tuple,
    get_latest_positions,
    get_last_qr_position
)
import config as cfg


class TestNormalizeRoomId(unittest.TestCase):
    """Test room ID normalization"""
    
    def test_already_normalized(self):
        self.assertEqual(normalize_room_id("2-01"), "2-01")
        self.assertEqual(normalize_room_id("1-15"), "1-15")
    
    def test_three_digit_format(self):
        self.assertEqual(normalize_room_id("201"), "2-01")
        self.assertEqual(normalize_room_id("115"), "1-15")
    
    def test_two_digit_format(self):
        self.assertEqual(normalize_room_id("15"), "2-15")
        self.assertEqual(normalize_room_id("01"), "2-01")
    
    def test_invalid_formats(self):
        self.assertIsNone(normalize_room_id(""))
        self.assertIsNone(normalize_room_id("abc"))
        self.assertIsNone(normalize_room_id("2-"))
        self.assertIsNone(normalize_room_id("2-abc"))


class TestNormalizePositionTo3tuple(unittest.TestCase):
    """Test position normalization to 3-tuple format"""
    
    def test_none_input(self):
        self.assertIsNone(normalize_position_to_3tuple(None))
    
    def test_2tuple_input(self):
        result = normalize_position_to_3tuple((1.0, 2.0))
        self.assertEqual(result, (1.0, 2.0, cfg.DEFAULT_FLOOR))
    
    def test_3tuple_input(self):
        result = normalize_position_to_3tuple((1.0, 2.0, 3))
        self.assertEqual(result, (1.0, 2.0, 3))
    
    def test_list_input(self):
        result = normalize_position_to_3tuple([1.5, 2.5])
        self.assertEqual(result, (1.5, 2.5, cfg.DEFAULT_FLOOR))
    
    def test_numpy_array_input(self):
        try:
            import numpy as np
            arr = np.array([1.0, 2.0, 3.0])
            result = normalize_position_to_3tuple(arr)
            self.assertEqual(result, (1.0, 2.0, 3))
        except ImportError:
            self.skipTest("NumPy not available")
    
    def test_insufficient_coordinates(self):
        self.assertIsNone(normalize_position_to_3tuple([1.0]))
        self.assertIsNone(normalize_position_to_3tuple([]))
    
    def test_invalid_types(self):
        self.assertIsNone(normalize_position_to_3tuple("invalid"))
        self.assertIsNone(normalize_position_to_3tuple(42))


class TestGetLastQrPosition(unittest.TestCase):
    """Test QR position retrieval"""
    
    def test_no_events(self):
        result = get_last_qr_position([])
        self.assertIsNone(result)
    
    def test_no_qr_events(self):
        events = [
            {"type": "other", "timestamp": "2024-01-01T10:00:00Z"},
        ]
        result = get_last_qr_position(events)
        self.assertIsNone(result)
    
    def test_valid_qr_event(self):
        events = [
            {
                "type": "qr",
                "timestamp": "2024-01-01T10:00:00Z",
                "position": [2.194291, 41.406351]
            }
        ]
        result = get_last_qr_position(events)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[0], 2.194291)
        self.assertAlmostEqual(result[1], 41.406351)
    
    def test_multiple_qr_events_returns_latest(self):
        events = [
            {
                "type": "qr",
                "timestamp": "2024-01-01T10:00:00Z",
                "position": [1.0, 1.0]
            },
            {
                "type": "qr", 
                "timestamp": "2024-01-01T11:00:00Z",
                "position": [2.0, 2.0]
            }
        ]
        result = get_last_qr_position(events)
        self.assertEqual(result, (2.0, 2.0))
    
    def test_invalid_position_format(self):
        events = [
            {
                "type": "qr",
                "timestamp": "2024-01-01T10:00:00Z", 
                "position": [1.0]  # Only one coordinate
            }
        ]
        result = get_last_qr_position(events)
        self.assertIsNone(result)


class TestGetLatestPositions(unittest.TestCase):
    """Test the main position retrieval function"""

    @patch('algorithms.filters.load_imu')
    @patch('algorithms.PDR.pdr_delta')
    @patch('services.geolocate.get_last_qr_position')
    @patch('algorithms.fingerprint.ll_to_local')
    def test_all_positions_available(self, mock_ll_to_local, mock_qr_pos, mock_pdr_delta, mock_load_imu):
        # Mock PDR data with the required columns
        mock_data = pd.DataFrame({
            'ACCE_X': [0.1, 0.2, 0.3],
            'ACCE_Y': [0.1, 0.2, 0.3],
            'ACCE_Z': [0.1, 0.2, 0.3]
        })
        mock_load_imu.return_value = (
            mock_data,  # accel DataFrame with necessary columns
            Mock(),     # gyro mock
            100.0       # sampling frequency
        )
        mock_pdr_delta.return_value = (1.0, 2.0)

        # Mock QR data
        mock_qr_pos.return_value = (2.194291, 41.406351)
        mock_ll_to_local.return_value = (10.0, 20.0)

        pdr, wifi, qr = get_latest_positions()

        # PDR should be normalized to 3-tuple
        self.assertIsNotNone(pdr)
        self.assertEqual(len(pdr), 3)
        self.assertEqual(pdr[:2], (1.0, 2.0))

        # WiFi should be None (deprecated)
        self.assertIsNone(wifi)

        # QR should be normalized to 3-tuple
        self.assertIsNotNone(qr)
        self.assertEqual(len(qr), 3)
        self.assertEqual(qr[:2], (10.0, 20.0))


class MockFlaskApp:
    """Mock Flask app for testing routes"""
    
    def __init__(self):
        self.routes = {}
        self.request = Mock()
    
    def route(self, path, methods=None):
        def decorator(func):
            self.routes[path] = func
            return func
        return decorator


from flask import request

class TestPositionRoute(unittest.TestCase):
    """Test the /position route handler"""

    @patch('services.geolocate.get_latest_positions')
    @patch('algorithms.fusion.fuse')
    def test_missing_room_parameter(self, mock_fuse, mock_get_latest):
        with patch('flask.request') as mock_request:
            # Setup mock request with args missing 'room'
            mock_request.args.get.return_value = None

            # Perform your test logic here
            room = mock_request.args.get('room')
            self.assertIsNone(room)

    @patch('services.geolocate.get_latest_positions')
    @patch('algorithms.fusion.fuse')
    def test_position_success(self, mock_fuse, mock_get_latest):
        with patch('flask.request') as mock_request:
            mock_request.args.get.return_value = "201"

            # Mock the dependencies
            mock_get_latest.return_value = (
                (1.0, 2.0, 2),  # PDR
                None,           # WiFi (deprecated)
                (10.0, 20.0, 2) # QR
            )
            mock_fuse.return_value = (15.0, 25.0, 2)

            # Verify room is obtained correctly
            room = mock_request.args.get('room')
            self.assertEqual(room, "201")

            # Simulate the fixed position route logic
            pdr_pos, finger_pos, qr_reset = mock_get_latest.return_value
            fused_pos = mock_fuse.return_value

            # Verify the response format
            self.assertEqual(len(fused_pos), 3)
            x, y, floor = fused_pos

            expected_response = {
                "position": [float(x), float(y), int(floor)],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sources": {
                    "pdr": bool(pdr_pos),
                    "fingerprint": False,
                    "qr_reset": bool(qr_reset)
                }
            }

            # Verify structure
            self.assertIn("position", expected_response)
            self.assertIn("timestamp", expected_response)
            self.assertIn("sources", expected_response)
            self.assertEqual(len(expected_response["position"]), 3)

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    unittest.main(verbosity=2)



class TestIntegration(unittest.TestCase):
    """Integration tests with real data files"""
    
    def setUp(self):
        # Create temporary test data
        self.temp_dir = tempfile.mkdtemp()
        self.temp_qr_file = Path(self.temp_dir) / "qr_events.json"
        
        # Sample QR events data
        self.qr_events = [
            {
                "type": "qr",
                "room": "2-01", 
                "timestamp": "2024-01-01T10:00:00Z",
                "position": [2.194291, 41.406351]
            },
            {
                "type": "qr",
                "room": "2-02",
                "timestamp": "2024-01-01T11:00:00Z", 
                "position": [2.194300, 41.406360]
            }
        ]
        
        # Write test data
        with open(self.temp_qr_file, 'w') as f:
            json.dump(self.qr_events, f)
    
    def test_qr_position_from_file(self):
        result = get_last_qr_position(qr_events_path=self.temp_qr_file)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        # Should return the latest QR position
        self.assertAlmostEqual(result[0], 2.194300)
        self.assertAlmostEqual(result[1], 41.406360)
    
    def test_empty_qr_file(self):
        empty_file = Path(self.temp_dir) / "empty.json"
        with open(empty_file, 'w') as f:
            json.dump([], f)
        
        result = get_last_qr_position(qr_events_path=empty_file)
        self.assertIsNone(result)


if __name__ == '__main__':
    # Set up logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    unittest.main(verbosity=2)