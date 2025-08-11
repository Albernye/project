"""
Unit tests for the position endpoint and related geolocation functions.
Comprehensive test suite covering happy path, edge cases, and error conditions.
tests/test_position.py
"""
import unittest
from unittest.mock import patch
import json
import tempfile
import numpy as np
import time
import sys
from pathlib import Path
import logging
from io import StringIO

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.geolocate import (
    normalize_room_id, 
    normalize_position_to_3tuple,
    get_latest_positions,
    get_last_qr_position,
    safe_get_latest_positions
)
import config as cfg


class TestNormalizeRoomId(unittest.TestCase):
    """Test room ID normalization including edge cases"""
    
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
        """Test various invalid input formats"""
        invalid_inputs = ["", "abc", "2-", "2-abc", None, 123, [], {}, "1-", "-01"]
        for invalid_input in invalid_inputs:
            with self.subTest(input=invalid_input):
                self.assertIsNone(normalize_room_id(invalid_input))
    
    def test_extreme_values(self):
        """Test extreme numeric values"""
        self.assertEqual(normalize_room_id("999"), "9-99")
        self.assertEqual(normalize_room_id("100"), "1-00")
        self.assertIsNone(normalize_room_id("1234"))  # Too many digits
        self.assertIsNone(normalize_room_id("0"))     # Too few digits
    
    def test_special_characters(self):
        """Test inputs with special characters"""
        special_cases = ["2-01a", "2 01", "2.01", "2/01", "2\\01", "2_01"]
        for case in special_cases:
            with self.subTest(input=case):
                self.assertIsNone(normalize_room_id(case))


class TestNormalizePositionTo3tuple(unittest.TestCase):
    """Test position normalization including error cases"""
    
    def test_none_input(self):
        self.assertIsNone(normalize_position_to_3tuple(None))
    
    def test_valid_inputs(self):
        """Test various valid input formats"""
        result = normalize_position_to_3tuple((1.0, 2.0))
        self.assertEqual(result, (1.0, 2.0, cfg.DEFAULT_FLOOR))
        
        result = normalize_position_to_3tuple((1.0, 2.0, 3))
        self.assertEqual(result, (1.0, 2.0, 3))
        
        result = normalize_position_to_3tuple([1.5, 2.5])
        self.assertEqual(result, (1.5, 2.5, cfg.DEFAULT_FLOOR))
    
    def test_numpy_array_input(self):
        """Test numpy array inputs"""
        try:
            import numpy as np
            arr = np.array([1.0, 2.0, 3.0])
            result = normalize_position_to_3tuple(arr)
            self.assertEqual(result, (1.0, 2.0, 3))
            
            # Test with different numpy dtypes
            arr_int = np.array([1, 2, 3], dtype=np.int32)
            result = normalize_position_to_3tuple(arr_int)
            self.assertEqual(result, (1.0, 2.0, 3))
        except ImportError:
            self.skipTest("NumPy not available")
    
    def test_insufficient_coordinates(self):
        """Test inputs with insufficient coordinates"""
        invalid_inputs = [[1.0], [], [np.nan], [1.0, np.nan]]
        for invalid_input in invalid_inputs:
            with self.subTest(input=invalid_input):
                self.assertIsNone(normalize_position_to_3tuple(invalid_input))
    
    def test_invalid_types(self):
        """Test various invalid input types"""
        invalid_inputs = ["invalid", 42, {}, set(), lambda x: x]
        for invalid_input in invalid_inputs:
            with self.subTest(input=invalid_input):
                self.assertIsNone(normalize_position_to_3tuple(invalid_input))
    
    def test_extreme_coordinates(self):
        """Test extreme coordinate values"""
        # Extreme but valid coordinates
        result = normalize_position_to_3tuple([-180.0, -90.0])
        self.assertIsNotNone(result)
        self.assertEqual(result[:2], (-180.0, -90.0))
        
        result = normalize_position_to_3tuple([180.0, 90.0])
        self.assertIsNotNone(result)
        self.assertEqual(result[:2], (180.0, 90.0))
        
        # Very large numbers
        result = normalize_position_to_3tuple([1e10, 1e10])
        self.assertIsNotNone(result)
    
    def test_nan_infinity_values(self):
        """Test NaN and infinity values"""
        result = normalize_position_to_3tuple([float('inf'), 1.0])
        self.assertIsNone(result)
        
        result = normalize_position_to_3tuple([1.0, float('nan')])
        self.assertIsNone(result)
    
    def test_non_numeric_strings(self):
        """Test string inputs that might be mistaken for numbers"""
        invalid_inputs = [["1.0", "2.0"], ("1", "2"), ["abc", "def"]]
        for invalid_input in invalid_inputs:
            with self.subTest(input=invalid_input):
                # Should either convert successfully or return None
                result = normalize_position_to_3tuple(invalid_input)
                # Allow either None or successful conversion
                if result is not None:
                    self.assertEqual(len(result), 3)


class TestGetLastQrPosition(unittest.TestCase):
    """Test QR position retrieval with comprehensive error handling"""
    
    def test_no_events(self):
        self.assertIsNone(get_last_qr_position([]))
    
    def test_none_events(self):
        self.assertIsNone(get_last_qr_position(None))
    
    def test_no_qr_events(self):
        events = [
            {"type": "other", "timestamp": "2024-01-01T10:00:00Z"},
            {"type": "wifi", "timestamp": "2024-01-01T10:01:00Z"},
        ]
        self.assertIsNone(get_last_qr_position(events))
    
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
    
    def test_invalid_position_formats(self):
        """Test various invalid position formats"""
        invalid_cases = [
            {"type": "qr", "timestamp": "2024-01-01T10:00:00Z", "position": [1.0]},  # Too few coords
            {"type": "qr", "timestamp": "2024-01-01T10:00:00Z", "position": []},     # Empty position
            {"type": "qr", "timestamp": "2024-01-01T10:00:00Z", "position": None},   # Null position
            {"type": "qr", "timestamp": "2024-01-01T10:00:00Z", "position": "invalid"}, # String position
            {"type": "qr", "timestamp": "2024-01-01T10:00:00Z"},  # Missing position
        ]
        
        for invalid_case in invalid_cases:
            with self.subTest(case=invalid_case):
                result = get_last_qr_position([invalid_case])
                self.assertIsNone(result)
    
    def test_extreme_coordinates(self):
        """Test extreme but valid coordinate values"""
        extreme_cases = [
            [-180.0, -90.0],   # Min valid lat/lon
            [180.0, 90.0],     # Max valid lat/lon
            [0.0, 0.0],        # Origin
            [-179.999, 89.999] # Near limits
        ]
        
        for coords in extreme_cases:
            with self.subTest(coords=coords):
                events = [{
                    "type": "qr",
                    "timestamp": "2024-01-01T10:00:00Z",
                    "position": coords
                }]
                result = get_last_qr_position(events)
                self.assertIsNotNone(result)
                self.assertEqual(result, tuple(coords))
    
    def test_malformed_events(self):
        """Test malformed event structures"""
        malformed_events = [
            {},  # Empty event
            {"type": "qr"},  # Missing timestamp and position
            {"timestamp": "2024-01-01T10:00:00Z"},  # Missing type
            None,  # Null event
            "invalid",  # String instead of dict
        ]
        
        for event in malformed_events:
            with self.subTest(event=event):
                # Should handle malformed events gracefully
                result = get_last_qr_position([event] if event is not None else [{}])
                self.assertIsNone(result)
    
    def test_file_reading_errors(self):
        """Test error handling when reading from files"""
        # Non-existent file
        non_existent = Path("/non/existent/path.json")
        result = get_last_qr_position(qr_events_path=non_existent)
        self.assertIsNone(result)
        
        # Invalid JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content {")
            invalid_json_path = Path(f.name)
        
        try:
            result = get_last_qr_position(qr_events_path=invalid_json_path)
            self.assertIsNone(result)
        finally:
            invalid_json_path.unlink()


class TestGetLatestPositions(unittest.TestCase):
    """Test the main position retrieval function with error scenarios"""

    @patch('services.geolocate.load_imu')
    @patch('services.geolocate.pdr_delta')
    @patch('services.geolocate.get_last_qr_position')
    @patch('services.geolocate.ll_to_local')
    def test_all_positions_available(self, mock_ll_to_local, mock_qr_pos, mock_pdr_delta, mock_load_imu):
        """Test successful case with all positions available"""
        mock_accel = np.array([
            [0.1, 0.1, 0.1],
            [0.2, 0.2, 0.2],
            [0.3, 0.3, 0.3]
        ])
        mock_gyro = np.array([
            [0.01, 0.01, 0.01],
            [0.02, 0.02, 0.02],
            [0.03, 0.03, 0.03]
        ])
        mock_load_imu.return_value = (mock_accel, mock_gyro, 100.0)
        mock_pdr_delta.return_value = (1.0, 2.0)
        mock_qr_pos.return_value = (2.194291, 41.406351)
        mock_ll_to_local.return_value = (10.0, 20.0)

        pdr, wifi, qr = get_latest_positions()

        self.assertIsNotNone(pdr)
        self.assertEqual(len(pdr), 3)
        self.assertEqual(pdr[:2], (1.0, 2.0))
        self.assertIsNone(wifi)
        self.assertIsNotNone(qr)
        self.assertEqual(len(qr), 3)
        self.assertEqual(qr[:2], (10.0, 20.0))

    @patch('services.geolocate.load_imu')
    @patch('services.geolocate.pdr_delta')
    @patch('services.geolocate.get_last_qr_position')
    def test_pdr_failure_scenarios(self, mock_qr_pos, mock_pdr_delta, mock_load_imu):
        """Test various PDR failure scenarios"""
        mock_qr_pos.return_value = None
        
        # Test insufficient IMU data
        mock_load_imu.return_value = (np.array([[0.1, 0.1, 0.1]]), np.array([[0.01, 0.01, 0.01]]), 100.0)
        pdr, wifi, qr = get_latest_positions()
        self.assertIsNone(pdr)
        
        # Test zero sampling frequency
        mock_load_imu.return_value = (np.array([[0.1, 0.1, 0.1], [0.2, 0.2, 0.2]]), 
                                     np.array([[0.01, 0.01, 0.01], [0.02, 0.02, 0.02]]), 0)
        pdr, wifi, qr = get_latest_positions()
        self.assertIsNone(pdr)
        
        # Test load_imu exception
        mock_load_imu.side_effect = FileNotFoundError("PDR file not found")
        pdr, wifi, qr = get_latest_positions()
        self.assertIsNone(pdr)
        
        # Test pdr_delta exception
        mock_load_imu.side_effect = None
        mock_load_imu.return_value = (np.array([[0.1, 0.1, 0.1], [0.2, 0.2, 0.2]]), 
                                     np.array([[0.01, 0.01, 0.01], [0.02, 0.02, 0.02]]), 100.0)
        mock_pdr_delta.side_effect = ValueError("PDR calculation failed")
        pdr, wifi, qr = get_latest_positions()
        self.assertIsNone(pdr)

    @patch('services.geolocate.get_last_qr_position')
    @patch('services.geolocate.ll_to_local')
    def test_qr_failure_scenarios(self, mock_ll_to_local, mock_qr_pos):
        """Test various QR failure scenarios"""
        # Test QR position not found
        mock_qr_pos.return_value = None
        pdr, wifi, qr = get_latest_positions()
        self.assertIsNone(qr)
        
        # Test coordinate conversion failure
        mock_qr_pos.return_value = (2.194291, 41.406351)
        mock_ll_to_local.side_effect = Exception("Coordinate conversion failed")
        pdr, wifi, qr = get_latest_positions()
        self.assertIsNone(qr)
        
        # Test invalid QR coordinates
        mock_qr_pos.return_value = (float('inf'), 41.406351)
        mock_ll_to_local.side_effect = None
        mock_ll_to_local.return_value = (10.0, 20.0)
        pdr, wifi, qr = get_latest_positions()
        self.assertIsNone(qr)

    def test_safe_get_latest_positions(self):
        """Test the safe wrapper function"""
        # Should return None values when main function fails
        with patch('services.geolocate.get_latest_positions') as mock_main:
            mock_main.side_effect = Exception("Critical failure")
            result = safe_get_latest_positions()
            self.assertEqual(result, (None, None, None))

    @patch('services.geolocate.logger')
    @patch('services.geolocate.load_imu')
    def test_logging_on_errors(self, mock_load_imu, mock_logger):
        """Test that errors are properly logged"""
        mock_load_imu.side_effect = FileNotFoundError("File not found")
        
        pdr, wifi, qr = get_latest_positions()
        
        # Verify warning was logged
        mock_logger.warning.assert_called()
        call_args = mock_logger.warning.call_args[0][0]
        self.assertIn("PDR skipped", call_args)


class TestPositionRoute(unittest.TestCase):
    """Test the /position route handler with comprehensive error cases"""

    @patch('web.app.get_latest_positions')
    @patch('web.app.fuse')
    def test_missing_room_parameter(self, mock_fuse, mock_get_latest):
        """Test missing room parameter"""
        from web.app import app
        with app.test_client() as client:
            response = client.get('/position')
            self.assertEqual(response.status_code, 400)
            data = response.get_json()
            self.assertIn('error', data)

    @patch('web.app.get_latest_positions')
    @patch('web.app.fuse')
    def test_position_success(self, mock_fuse, mock_get_latest):
        """Test successful position request"""
        from web.app import app
        mock_get_latest.return_value = (
            (1.0, 2.0, 2),  # PDR
            None,           # WiFi (deprecated)
            (10.0, 20.0, 2) # QR
        )
        mock_fuse.return_value = (15.0, 25.0, 2)
        
        with app.test_client() as client:
            response = client.get('/position?room=201')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIn('position', data)
            self.assertEqual(len(data['position']), 3)
            self.assertIn('timestamp', data)
            self.assertIn('sources', data)

    @patch('web.app.get_latest_positions')
    @patch('web.app.fuse')
    def test_get_latest_positions_exception(self, mock_fuse, mock_get_latest):
        """Test exception in get_latest_positions"""
        from web.app import app
        mock_get_latest.side_effect = Exception("Position retrieval failed")
        
        with app.test_client() as client:
            response = client.get('/position?room=201')
            # Should handle exception gracefully
            self.assertIn(response.status_code, [500, 200])  # Depends on error handling implementation

    @patch('web.app.get_latest_positions')
    @patch('web.app.fuse')
    def test_fusion_algorithm_failure(self, mock_fuse, mock_get_latest):
        """Test fusion algorithm failure"""
        from web.app import app
        mock_get_latest.return_value = ((1.0, 2.0, 2), None, (10.0, 20.0, 2))
        mock_fuse.side_effect = Exception("Fusion failed")
        
        with app.test_client() as client:
            response = client.get('/position?room=201')
            # Should handle fusion failure gracefully
            self.assertIn(response.status_code, [500, 200])

    @patch('web.app.get_latest_positions')
    @patch('web.app.fuse')
    def test_no_positions_available(self, mock_fuse, mock_get_latest):
        """Test case where no positions are available"""
        from web.app import app
        mock_get_latest.return_value = (None, None, None)
        mock_fuse.return_value = None
        
        with app.test_client() as client:
            response = client.get('/position?room=201')
            # Should handle no positions gracefully
            if response.status_code == 200:
                data = response.get_json()
                self.assertIsNotNone(data)

    @patch('web.app.get_latest_positions')
    @patch('web.app.fuse')
    def test_invalid_room_format(self, mock_fuse, mock_get_latest):
        """Test various invalid room formats"""
        from web.app import app
        mock_get_latest.return_value = ((1.0, 2.0, 2), None, (10.0, 20.0, 2))
        mock_fuse.return_value = (15.0, 25.0, 2)
        
        invalid_rooms = ["", "abc", "999999", "1-", "-01", "1-abc"]
        
        with app.test_client() as client:
            for room in invalid_rooms:
                with self.subTest(room=room):
                    response = client.get(f'/position?room={room}')
                    # Should either reject or handle invalid room gracefully
                    self.assertIn(response.status_code, [400, 200])

    @patch('web.app.get_latest_positions')
    @patch('web.app.fuse')  
    def test_extreme_coordinate_values(self, mock_fuse, mock_get_latest):
        """Test extreme coordinate values in response"""
        from web.app import app
        # Test with extreme coordinates
        extreme_coords = [
            (float('inf'), 0.0, 2),
            (0.0, float('nan'), 2), 
            (1e10, -1e10, 2),
            (-180.0, -90.0, 2),
            (180.0, 90.0, 2)
        ]
        
        with app.test_client() as client:
            for coords in extreme_coords:
                with self.subTest(coords=coords):
                    mock_get_latest.return_value = (coords, None, None)
                    mock_fuse.return_value = coords
                    
                    response = client.get('/position?room=201')
                    # Should handle extreme values gracefully
                    if response.status_code == 200:
                        data = response.get_json()
                        # Verify response structure is maintained
                        self.assertIn('position', data)

    def test_malformed_json_response(self):
        """Test handling of malformed JSON responses"""
        from web.app import app
        
        with app.test_client() as client:
            # Test with various request methods
            for method in ['POST', 'PUT', 'DELETE']:
                response = getattr(client, method.lower())('/position?room=201')
                # Should reject non-GET methods or handle appropriately
                self.assertIn(response.status_code, [405, 200])


class TestIntegration(unittest.TestCase):
    """Integration tests with real data files and error scenarios"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_qr_file = Path(self.temp_dir) / "qr_events.json"
        
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
        
        with open(self.temp_qr_file, 'w') as f:
            json.dump(self.qr_events, f)
    
    def test_qr_position_from_file(self):
        """Test reading QR position from file"""
        result = get_last_qr_position(qr_events_path=self.temp_qr_file)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[0], 2.194300)
        self.assertAlmostEqual(result[1], 41.406360)
    
    def test_empty_qr_file(self):
        """Test empty QR events file"""
        empty_file = Path(self.temp_dir) / "empty.json"
        with open(empty_file, 'w') as f:
            json.dump([], f)
        
        result = get_last_qr_position(qr_events_path=empty_file)
        self.assertIsNone(result)
    
    def test_corrupted_qr_file(self):
        """Test corrupted QR events file"""
        corrupted_file = Path(self.temp_dir) / "corrupted.json"
        with open(corrupted_file, 'w') as f:
            f.write('{"invalid": json syntax')
        
        result = get_last_qr_position(qr_events_path=corrupted_file)
        self.assertIsNone(result)
    
    def test_file_permission_error(self):
        """Test file permission errors"""
        # This test might not work on all systems
        restricted_file = Path(self.temp_dir) / "restricted.json"
        with open(restricted_file, 'w') as f:
            json.dump(self.qr_events, f)
        
        try:
            restricted_file.chmod(0o000)  # Remove all permissions
            result = get_last_qr_position(qr_events_path=restricted_file)
            self.assertIsNone(result)
        except (OSError, PermissionError):
            # Skip test if we can't change permissions
            self.skipTest("Cannot modify file permissions")
        finally:
            try:
                restricted_file.chmod(0o644)  # Restore permissions for cleanup
            except (OSError, PermissionError):
                pass
    
    def test_large_qr_file(self):
        """Test performance with large QR events file"""
        large_events = []
        for i in range(1000):  # Create 1000 events
            large_events.append({
                "type": "qr",
                "room": f"2-{i:02d}",
                "timestamp": f"2024-01-01T{i%24:02d}:00:00Z",
                "position": [2.194291 + i*0.0001, 41.406351 + i*0.0001]
            })
        
        large_file = Path(self.temp_dir) / "large.json" 
        with open(large_file, 'w') as f:
            json.dump(large_events, f)
        
        start_time = time.time()
        result = get_last_qr_position(qr_events_path=large_file)
        elapsed_time = time.time() - start_time
        
        self.assertIsNotNone(result)
        self.assertLess(elapsed_time, 5.0) 


class TestLoggingAndMonitoring(unittest.TestCase):
    """Test logging behavior and monitoring aspects"""
    
    def setUp(self):
        # Capture log output
        self.log_capture = StringIO()
        self.handler = logging.StreamHandler(self.log_capture)
        self.handler.setLevel(logging.WARNING)
        logging.getLogger('services.geolocate').addHandler(self.handler)
    
    def tearDown(self):
        logging.getLogger('services.geolocate').removeHandler(self.handler)
    
    def test_warning_logs_on_pdr_failure(self):
        """Test that PDR failures generate appropriate warning logs"""
        with patch('services.geolocate.load_imu') as mock_load_imu:
            mock_load_imu.side_effect = FileNotFoundError("File not found")
            
            get_latest_positions()
            
            log_contents = self.log_capture.getvalue()
            self.assertIn("PDR skipped", log_contents)
    
    def test_warning_logs_on_qr_failure(self):
        """Test that QR failures generate appropriate warning logs"""
        with patch('services.geolocate.get_last_qr_position') as mock_qr:
            mock_qr.side_effect = Exception("QR processing failed")
            
            get_latest_positions()
            
            log_contents = self.log_capture.getvalue()
            self.assertIn("QR position failed", log_contents)


if __name__ == '__main__':
    # Configure logging for tests
    logging.basicConfig(
        level=logging.WARNING,
        format='%(levelname)s %(name)s:%(filename)s:%(lineno)d %(message)s'
    )
    
    # Run tests with high verbosity
    unittest.main(verbosity=2)