from pathlib import Path
from typing import Optional, Tuple
import logging
import traceback
import pandas as pd
import numpy as np

from algorithms.fingerprint import (get_last_position, ll_to_local, set_origin)
from algorithms.PDR import pdr_delta
from algorithms.filters import load_imu
from services.utils import read_json_safe, get_room_position
from archives.simulation.simu_pdr import simulate_imu_movement
from config import (
    PDR_TRACE, FP_CURRENT, QR_EVENTS_FILE, ROOM_POS_CSV,
    DEFAULT_FLOOR, DEFAULT_POSXY, DEFAULT_AP_N, DEFAULT_RSSI,
    GLOBAL_KNN, STATS_DIR, SIM_DURATION, SIM_FS,
)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_paths() -> dict:
    """Return the paths for the various data sources."""
    return {
        'pdr_file': PDR_TRACE,
        'knn_train': STATS_DIR / GLOBAL_KNN,
        'fingerprints': FP_CURRENT,
        'qr_events': QR_EVENTS_FILE,
    }


def initialize_coordinate_system(lon: float = None, lat: float = None) -> None:
    """
    Initialize the local coordinate system.
    Call once at the start of the application.
    """
    origin_lon = lon if lon is not None else DEFAULT_POSXY[0]
    origin_lat = lat if lat is not None else DEFAULT_POSXY[1]
    set_origin(origin_lon, origin_lat)
    logger.info(f"Origin set at ({origin_lon}, {origin_lat})")

def normalize_room_id(room_id):
    """
    Normalize a room ID to the format "F-XX" where:
    For example:
      - "201" -> "2-01"
      - "2-01" -> "2-01"
      - "15"  -> "0-15" 
    """
    if not room_id:
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
    if len(room_id) == 3 and room_id.isdigit():
        floor = int(room_id[0])
        num   = int(room_id[1:])
        return f"{floor}-{num:02d}"

    # Case 2 digits "NN" (2 number digits)
    if room_id.isdigit():
        num = int(room_id)
        return f"2-{num:02d}"

    logger.warning(f"Room ID invalid: {room_id}")
    return None

def get_node_position(node_id, corridor_data):
    """Retrieve the position of a node (room or corridor point)"""
    # If it's a room
    if node_id.startswith('2-'):
        try:
            return get_room_position(node_id)
        except Exception as e:
            logger.warning(f"Position not found for room {node_id}: {e}")
            return None

    # If it's a corridor point
    if corridor_data and 'corridor_structure' in corridor_data:
        for corridor_name, corridor_info in corridor_data['corridor_structure'].items():
            for point_name, x, y in corridor_info.get('points', []):
                if point_name == node_id:
                    return [x, y]

    logger.warning(f"Position not found for node {node_id}")
    return None

def get_last_qr_position(events=None, qr_events_path: Path = None) -> Optional[Tuple[float, float]]:
    """Return the geographic position of the last QR event."""
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
        if event.get("type") == "qr":
            position = event.get("position")
            if isinstance(position, list) and len(position) == 2:
                qr_events.append((event, idx))  # Stock the event and its index

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
        return lon, lat
    except Exception as e:
        logger.error(f"Invalid QR position: {position}, error: {e}")
    return None

def get_latest_positions() -> Tuple[Tuple[float, float, int], Optional[Tuple[float, float, int]], Optional[Tuple[float, float, int]]]:
    """
    Get the latest positions: PDR, WiFi, QR.
    Return three tuples or None.
    """
    # PDR
    # if SIMULATED_IMU:
    #     duration, fs = SIM_DURATION, SIM_FS
    #     accel, gyro, times = simulate_imu_movement(duration, fs)
    #     fs = 1.0 / np.mean(np.diff(times))
    # else:
    try:
        res = load_imu(PDR_TRACE)
        logger.debug(f"DEBUG load_imu returned -> {res!r}")
        accel, gyro, fs = res
        if accel.shape[0] < 2 or fs <= 0:
            raise ValueError("Insufficient IMU data for PDR")
        dx, dy = pdr_delta(accel, gyro, fs)
        pdr_pos = (dx, dy, DEFAULT_FLOOR)
    except Exception as e:
        logger.warning(f"PDR skipped: {e}")
        pdr_pos = None

    # WiFi
    # fingerprint may not yet be configured
    wifi_pos = None
    knn_path = STATS_DIR / GLOBAL_KNN
    if knn_path.exists() and Path(FP_CURRENT).exists():
        try:
            x, y, floor = get_last_position(
                str(knn_path),
                str(FP_CURRENT),
                kP=3, kZ=3, R=10.0
            )
            wifi_pos = (x, y, floor)
        except Exception as e:
            logger.warning(f"Fingerprint failed: {e}")

    # QR
    qr_geo = get_last_qr_position(QR_EVENTS_FILE)
    qr_pos = None
    if qr_geo:
        x, y = ll_to_local(*qr_geo)
        qr_pos = (x, y, DEFAULT_FLOOR)

    return pdr_pos, wifi_pos, qr_pos

def safe_get_latest_positions():
    """Version sécurisée de get_latest_positions avec gestion d'erreur robuste"""
    try:
        return get_latest_positions()
    except Exception as e:
        logger.error(f"Erreur dans get_latest_positions: {e}")
        logger.debug(traceback.format_exc())
        # Retourner des valeurs par défaut plutôt que de faire planter
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


# Exécution en standalone
if __name__ == '__main__':
    initialize_coordinate_system()
    tracker = PositionTracker()
    for _ in range(5):
        tracker.update()
    print(f"Final: {tracker.current}")
