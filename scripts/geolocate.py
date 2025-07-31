from pathlib import Path
from typing import Optional, Tuple
import logging
import pandas as pd
import numpy as np

from algorithms.fingerprint import (get_last_position, ll_to_local, set_origin)
from algorithms.PDR import pdr_delta
from algorithms.filters import load_imu
from scripts.utils import cfg, read_json_safe

# Optional simulation import
if cfg.USE_SIMULATED_IMU:
    from scripts.navigation_simulation import simulate_movement

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_paths() -> dict:
    """Retourne les chemins des fichiers live à charger."""
    return {
        'pdr_file': cfg.PDR_TRACE,
        'knn_train': cfg.STATS_DIR / cfg.GLOBAL_KNN,
        'fingerprints': cfg.FP_CURRENT,
        'qr_events': cfg.QR_EVENTS,
    }


def initialize_coordinate_system(lon: float = None, lat: float = None) -> None:
    """
    Initialise le système de coordonnées locales.
    À appeler une seule fois au début de l'application.
    """
    origin_lon = lon if lon is not None else cfg.DEFAULT_POSXY[0]
    origin_lat = lat if lat is not None else cfg.DEFAULT_POSXY[1]
    set_origin(origin_lon, origin_lat)
    logger.info(f"Origine définie à ({origin_lon}, {origin_lat})")


def get_last_qr_position(events=None, qr_events_path: Path = None) -> Optional[Tuple[float, float]]:
    """Renvoie la position géographique du dernier événement QR."""
    if qr_events_path:
        events = read_json_safe(qr_events_path)
    elif events is None:
        logger.warning("Aucun événement fourni.")
        return None

    if not events:
        logger.warning("Aucun événement QR.")
        return None

    qr_events = []
    for idx, event in enumerate(events):
        if event.get("type") == "qr":
            position = event.get("position")
            if isinstance(position, list) and len(position) == 2:
                qr_events.append((event, idx))  # Stocker avec l'index original

    if not qr_events:
        logger.warning("Aucun événement QR valide trouvé.")
        return None

    # Trier les événements QR par timestamp, puis par leur position dans la liste d'origine
    qr_events_sorted = sorted(qr_events, key=lambda x: (x[0]["timestamp"], x[1]))
    last_qr_event = qr_events_sorted[-1][0]  # Récupérer l'événement

    position = last_qr_event["position"]

    try:
        lon, lat = map(float, position)
        logger.info(f"QR position: ({lon}, {lat})")
        return lon, lat
    except Exception as e:
        logger.error(f"Position QR invalide: {position}, erreur: {e}")
        return None

def get_latest_positions() -> Tuple[Tuple[float, float, int], Optional[Tuple[float, float, int]], Optional[Tuple[float, float, int]]]:
    """
    Récupère les dernières positions : PDR, WiFi, QR.
    Retourne trois tuples ou None.
    """
    # PDR
    if cfg.USE_SIMULATED_IMU:
        duration, fs = cfg.SIM_DURATION, cfg.SIM_FS
        accel, gyro, times = simulate_movement(duration, fs)
        fs = 1.0 / np.mean(np.diff(times))
    else:
        accel, gyro, fs = load_imu(cfg.PDR_TRACE)
    dx, dy = pdr_delta(accel, gyro, fs)
    pdr_pos = (dx, dy, cfg.DEFAULT_FLOOR)

    # WiFi
    try:
        x, y, floor = get_last_position(
            str(cfg.STATS_DIR / cfg.GLOBAL_KNN),
            str(cfg.FP_CURRENT),
            kP=3, kZ=3, R=10.0
        )
        wifi_pos = (x, y, floor)
    except Exception:
        wifi_pos = None

    # QR
    qr_geo = get_last_qr_position(cfg.QR_EVENTS)
    qr_pos = None
    if qr_geo:
        x, y = ll_to_local(*qr_geo)
        qr_pos = (x, y, cfg.DEFAULT_FLOOR)

    return pdr_pos, wifi_pos, qr_pos


class PositionTracker:
    """Gère la position unifiée selon WiFi > QR > PDR"""
    def __init__(self):
        self.current: Optional[Tuple[float, float, int]] = None

    def update(self) -> Optional[Tuple[float, float, int]]:
        pdr, wifi, qr = get_latest_positions()
        if wifi:
            self.current = wifi
        elif qr:
            self.current = qr
        elif pdr and self.current:
            dx, dy, _ = pdr
            x, y, floor = self.current
            self.current = (x + dx, y + dy, floor)
        else:
            logger.warning("Mise à jour impossible")
        logger.info(f"Position maj: {self.current}")
        return self.current

    def reset(self, pos: Tuple[float, float, int]) -> None:
        self.current = pos
        logger.info(f"Position forcée: {pos}")


# Exécution en standalone
if __name__ == '__main__':
    initialize_coordinate_system()
    tracker = PositionTracker()
    for _ in range(5):
        tracker.update()
    print(f"Final: {tracker.current}")
