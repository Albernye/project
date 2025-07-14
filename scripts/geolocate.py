import os
import json
from config import config
from algorithms.fingerprint import fingerprint
from algorithms.PDR import PDR
from algorithms.filters import KalmanFilter

# Configuration des chemins
def setup_paths():
    project_root = config.get_project_root()
    return {
        'pdr_file': os.path.join(project_root, 'data', 'pdr_traces', 'current.csv'),
        'knn_train': os.path.join(project_root, 'data', 'stats', 'knn_train.csv'),
        'fingerprints': os.path.join(project_root, 'data', 'recordings', 'current_fingerprints.csv'),
        'qr_events': os.path.join(project_root, 'data', 'qr_events.json')
    }


def get_latest_positions(paths):
    """
    Récupère la dernière position PDR et la position fingerprint kNN, plus le dernier reset QR.
    """
    # --- PDR offline ---
    thetas, positions = PDR(paths['pdr_file'])
    if positions is None or len(positions) == 0:
        pdr_pos = None
    else:
        pdr_pos = tuple(positions[-1])

    # --- Wi‑Fi fingerprinting kNN ---
    kP = config.get('knn.kP', 3)
    kZ = config.get('knn.kZ', 3)
    R  = config.get('floor.threshold', 5.0)
    finger_preds = fingerprint(
        knntrainfile=paths['knn_train'],
        FPfile=paths['fingerprints'],
        kP=kP, kZ=kZ, R=R
    )
