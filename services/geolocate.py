from pathlib import Path
from typing import Optional, Tuple
import logging
import traceback
import pandas as pd
import numpy as np

import config as cfg
from algorithms.fingerprint import (ll_to_local, set_origin)
from algorithms.PDR import pdr_delta
from algorithms.filters import load_imu
from services.utils import read_json_safe, get_room_position
from archives.simulation.simu_pdr import simulate_imu_movement
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_paths() -> dict:
    """Return the paths for the various data sources."""
    return {
        'pdr_file': cfg.PDR_TRACE,
        #'knn_train': cfg.STATS_DIR / cfg.GLOBAL_KNN,
        'fingerprints': cfg.FP_CURRENT,
        'qr_events': cfg.QR_EVENTS_FILE,
    }


def initialize_coordinate_system(lon: float = None, lat: float = None) -> None:
    """
    Initialize the local coordinate system.
    Call once at the start of the application.
    """
    origin_lon = lon if lon is not None else cfg.DEFAULT_POSXY[0]
    origin_lat = lat if lat is not None else cfg.DEFAULT_POSXY[1]
    set_origin(origin_lon, origin_lat)
    logger.info(f"Origin set at ({origin_lon}, {origin_lat})")

def normalize_room_id(room_id):
    """
    Normalize a room ID to the format "F-XX" where:
    For example:
      - "201" -> "2-01"
      - "2-01" -> "2-01"
      - "15"  -> "2-15" 
    """
    if not isinstance(room_id, str) or not room_id:
        return None

    # Case "F-XX" : already normalized
    if '-' in room_id:
        parts = room_id.split('-')
        if len(parts)==2 and parts[0].isdigit() and parts[1].isdigit():
            floor, num = int(parts[0]), int(parts[1])
            return f"{floor}-{num:02d}"
        else:
            return None

    # Case compact "FNN" (3 number digits)
    if room_id.isdigit():
        if len(room_id) == 3:
            floor = int(room_id[0])
            num   = int(room_id[1:])
            return f"{floor}-{num:02d}"
        elif len(room_id) == 2:
            num = int(room_id)
            return f"2-{num:02d}"
        elif len(room_id) == 1 or len(room_id) > 3:
            return None

    logger.warning(f"Room ID invalid: {room_id}")
    return None

def get_node_position(node_id, corridor_data):
    """Retrieve the position of a node (room or corridor point)"""
    if node_id.startswith('2-'):
        try:
            pos = get_room_position(node_id)
            # Ensure we always return numeric coordinates, never Path
            if isinstance(pos, tuple) and len(pos) >= 2:
                return [float(pos[0]), float(pos[1])]
            elif isinstance(pos, (list, tuple)) and len(pos) >= 2:
                return [float(pos[0]), float(pos[1])]
            else:
                logger.warning(f"Invalid position format for room {node_id}: {pos}")
                return None
        except Exception as e:
            logger.warning(f"Position not found for room {node_id}: {e}")
            return None

    # If it's a corridor point
    if corridor_data and 'corridor_structure' in corridor_data:
        for corridor_name, corridor_info in corridor_data['corridor_structure'].items():
            for point_name, x, y in corridor_info.get('points', []):
                if point_name == node_id:
                    return [float(x), float(y)]

    logger.warning(f"Position not found for node {node_id}")
    return None

def get_last_qr_position(events=None, qr_events_path: Path = None) -> Optional[Tuple[float, float]]:
    """Return the geographic position of the last QR event as (lon, lat) tuple."""
    if qr_events_path:
        events = read_json_safe(qr_events_path)
    elif events is None:
        logger.warning("No events provided.")
        return None

    if not events:
        logger.warning("No QR events found.")
        return None

    qr_events = []
    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        if event.get("type") == "qr":
            position = event.get("position")
            if isinstance(position, list) and len(position) == 2:
                qr_events.append((event, idx))

    if not qr_events:
        logger.warning("No valid QR events found.")
        return None

    # Sort qr events by timestamp and get the last one
    qr_events_sorted = sorted(qr_events, key=lambda x: (x[0]["timestamp"], x[1]))
    last_qr_event = qr_events_sorted[-1][0]  # Get the last event

    position = last_qr_event["position"]

    try:
        lon, lat = map(float, position)
        logger.info(f"QR position: ({lon}, {lat})")
        return (lon, lat)
    except Exception as e:
        logger.error(f"Invalid QR position: {position}, error: {e}")
    return None

def normalize_position_to_3tuple(pos, default_floor=None) -> Optional[Tuple[float, float, int]]:
    """
    Normalize any position format to (x, y, floor) tuple.
    Handles 2-tuples, 3-tuples, lists, numpy arrays, etc.
    """
    if pos is None:
        return None

    if default_floor is None:
        default_floor = cfg.DEFAULT_FLOOR

    try:
        if isinstance(pos, np.ndarray):
            pos_list = pos.tolist()
        elif isinstance(pos, (tuple, list)):
            pos_list = list(pos)
        else:
            logger.warning(f"Unexpected position type: {type(pos)}")
            return None

        if pos_list is None or len(pos_list) < 2:
            logger.warning(f"Position has insufficient coordinates: {pos_list}")
            return None

        try:
            x = float(pos_list[0])
            y = float(pos_list[1])
        except (ValueError, TypeError):
            logger.warning(f"Position values not convertible to float: {pos_list}")
            return None
        
        if np.isnan(x) or np.isinf(x) or np.isnan(y) or np.isinf(y):
            logger.warning(f"Position has NaN or infinity: {pos_list}")
            return None

        # Floor handling
        if len(pos_list) >= 3:
            try:
                floor = int(pos_list[2])
            except (ValueError, TypeError):
                floor = default_floor
        else:
            floor = default_floor

        return (x, y, floor)
    except Exception as e:
        logger.error(f"Failed to normalize position {pos}: {e}")
        return None


def get_latest_positions() -> Tuple[Optional[Tuple[float, float, int]], Optional[Tuple[float, float, int]], Optional[Tuple[float, float, int]]]:
    """
    Get the latest positions: PDR, (WiFi), QR.
    Return three 3-tuples (x, y, floor) or None for each.
    """
    # PDR
    pdr_pos = None
    try:
        accel, gyro, fs = load_imu(cfg.PDR_TRACE)
        if accel.shape[0] < 2 or fs <= 0:
            raise ValueError("Insufficient IMU data for PDR")
        dx, dy = pdr_delta(accel, gyro, fs)
        
        pdr_pos = normalize_position_to_3tuple((dx, dy))
    except Exception as e:
        logger.warning(f"PDR skipped: {e}")

    # WiFi (deprecated but keeping structure)
    wifi_pos = None

    # QR
    qr_pos = None
    try:
        qr_geo = get_last_qr_position(qr_events_path=cfg.QR_EVENTS_FILE)
        if qr_geo:
        # Check for NaN or infinity in QR coordinates
            if any((v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v)))) for v in qr_geo):
                logger.warning(f"QR coordinates invalid: {qr_geo}")
                qr_pos = None
            else:
                x, y = ll_to_local(*qr_geo)
                qr_pos = normalize_position_to_3tuple((x, y))
    except Exception as e:
        logger.warning(f"QR position failed: {e}")

    logger.debug(f"Latest positions - PDR: {pdr_pos}, WiFi: {wifi_pos}, QR: {qr_pos}")
    return pdr_pos, wifi_pos, qr_pos

def safe_get_latest_positions():
    """Safe version of get_latest_positions with robust error handling"""
    try:
        return get_latest_positions()
    except Exception as e:
        logger.error(f"Error in get_latest_positions: {e}")
        logger.debug(traceback.format_exc())
        # Return default values rather than crashing
        return None, None, None
class PositionTracker:
    """Manages the unified position according to QR > WIFI > PDR"""
    def __init__(self):
        self.current: Optional[Tuple[float, float, int]] = None

    def update(self) -> Optional[Tuple[float, float, int]]:
        pdr, wifi, qr = get_latest_positions()
        if qr:
            self.current = qr
        elif wifi:
            self.current = wifi
        elif pdr and self.current:
            dx, dy, _ = pdr
            x, y, floor = self.current
            self.current = (x + dx, y + dy, floor)
        else:
            logger.warning("Update failed")
        logger.info(f"Position updated: {self.current}")
        return self.current

    def reset(self, pos: Tuple[float, float, int]) -> None:
        self.current = pos
        logger.info(f"Position forced: {pos}")


# Execution in standalone
if __name__ == '__main__':
    initialize_coordinate_system()
    tracker = PositionTracker()
    for _ in range(5):
        tracker.update()
    print(f"Final: {tracker.current}")