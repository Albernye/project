from pathlib import Path
from typing import Optional, Tuple
import logging
import pandas as pd
import numpy as np

from algorithms.fingerprint import (get_last_position, ll_to_local, set_origin)
from algorithms.PDR import pdr_delta
from algorithms.filters import load_imu
from scripts.utils import cfg, read_json_safe
from simulation.simu_pdr import simulate_imu_movement
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_paths() -> dict:
    """Return the paths for the various data sources."""
    return {
        'pdr_file': cfg.PDR_TRACE,
        'knn_train': cfg.STATS_DIR / cfg.GLOBAL_KNN,
        'fingerprints': cfg.FP_CURRENT,
        'qr_events': cfg.QR_EVENTS,
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
    # if cfg.USE_SIMULATED_IMU:
    #     duration, fs = cfg.SIM_DURATION, cfg.SIM_FS
    #     accel, gyro, times = simulate_imu_movement(duration, fs)
    #     fs = 1.0 / np.mean(np.diff(times))
    # else:
    accel, gyro, fs = load_imu(cfg.PDR_TRACE)
    dx, dy = pdr_delta(accel, gyro, fs)
    pdr_pos = (dx, dy, cfg.DEFAULT_FLOOR)

    # WiFi
    # fingerprint may not yet be configured
    wifi_pos = None
    knn_path = cfg.STATS_DIR / cfg.GLOBAL_KNN
    if knn_path.exists() and Path(cfg.FP_CURRENT).exists():
        try:
            x, y, floor = get_last_position(
                str(knn_path),
                str(cfg.FP_CURRENT),
                kP=3, kZ=3, R=10.0
            )
            wifi_pos = (x, y, floor)
        except Exception as e:
            logger.warning(f"Fingerprint failed: {e}")

    # QR
    qr_geo = get_last_qr_position(cfg.QR_EVENTS)
    qr_pos = None
    if qr_geo:
        x, y = ll_to_local(*qr_geo)
        qr_pos = (x, y, cfg.DEFAULT_FLOOR)

    return pdr_pos, wifi_pos, qr_pos


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
