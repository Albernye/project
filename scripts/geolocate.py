from pathlib import Path
from algorithms.fingerprint import fingerprint
from algorithms.PDR import PDR
from algorithms.filters import KalmanFilter
from scripts.utils import (cfg, get_logger, read_csv_safe, write_csv_safe,
                           read_json_safe, write_json_safe, default_pdr_row,
                           default_fingerprint_row, default_qr_event)


def setup_paths():
    """Retourne les chemins des fichiers live à charger."""
    return {
        'pdr_file'     : cfg.PDR_TRACE,
        'knn_train'    : cfg.STATS_DIR / cfg.GLOBAL_KNN,
        'fingerprints' : cfg.FP_CURRENT,
        'qr_events'    : cfg.QR_EVENTS,
    }

def get_last_qr_position(events_path: Path):
    """Renvoie la position du dernier événement QR, ou None."""
    events = read_json_safe(events_path)
    if not isinstance(events, list) or not events:
        return None
    last = events[-1]
    return tuple(last.get('position', (None, None)))

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