from pathlib import Path
from typing import Optional
import logging
from algorithms.fingerprint import fingerprint
from algorithms.PDR import PDR
from algorithms.filters import KalmanFilter
from scripts.utils import (cfg, read_json_safe)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_paths():
    """Retourne les chemins des fichiers live à charger."""
    return {
        'pdr_file'     : cfg.PDR_TRACE,
        'knn_train'    : cfg.STATS_DIR / cfg.GLOBAL_KNN,
        'fingerprints' : cfg.FP_CURRENT,
        'qr_events'    : cfg.QR_EVENTS,
    }

def get_last_qr_position(qr_events_path: Path) -> Optional[tuple]:
    """Renvoie la position du dernier événement QR, ou None."""
    try:
        events = read_json_safe(qr_events_path)
        if not events:
            logger.warning("Aucun événement QR trouvé")
            return None

        last_event = events[-1]
        position = last_event.get('position')

        if not position or not isinstance(position, (list, tuple)):
            logger.error(f"Position QR invalide: {position}")
            return None

        if len(position) < 2:
            logger.error(f"Position QR trop courte: {position}")
            return None

        # Conversion en float et validation
        try:
            lon, lat = float(position[0]), float(position[1])
            logger.info(f"Position QR récupérée: ({lon}, {lat})")
            return (lon, lat)
        except (ValueError, TypeError) as e:
            logger.error(f"Position QR non numérique: {position}")
            return None

    except Exception as e:
        logger.error(f"Erreur lors de la lecture des événements QR: {e}")
        return None


def get_latest_positions() -> tuple:
    """
    Récupère les 3 sources de position :
      - PDR (via PDR(paths['pdr_file']))
      - fingerprinting WiFi (via fingerprint(...))
      - dernier reset QR (dernier item de qr_events.json)
    Renvoie un tuple (pdr_pos, finger_pos, qr_pos) où chaque pos est
    soit (lat,lon) soit None.
    """
    paths = setup_paths()

    # --- 1) PDR offline ---
    try:
        thetas, positions = PDR(str(paths['pdr_file']))
        pdr_pos = tuple(positions[-1]) if positions and len(positions)>0 else None
    except Exception:
        pdr_pos = None

    # --- 2) Wi‑Fi fingerprinting kNN ---
    try:
        # Ici tu peux remplacer par tes hyper‑params ou charger un petit dict de config
        finger = fingerprint(
            knntrainfile=str(paths['knn_train']),
            FPfile=str(paths['fingerprints']),
            kP=3, kZ=3, R=5.0
        )
        finger_pos = tuple(finger) if finger is not None else None
    except Exception:
        finger_pos = None

    # --- 3) Dernier QR reset ---
    try:
        qr_pos = get_last_qr_position(paths['qr_events'])
    except Exception:
        qr_pos = None

    return pdr_pos, finger_pos, qr_pos