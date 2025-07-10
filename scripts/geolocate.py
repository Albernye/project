import os
import json
from config import config
from project.algorithms.fingerprint import fingerprint
from project.algorithms.PDR import PDR
from project.algorithms.filters import KalmanFilter

# Configuration des chemins
def setup_paths():
    project_root = config.get_project_root()
    return {
        'pdr_file': os.path.join(project_root, 'data', 'pdr_traces', 'current.csv'),
        'knn_train': os.path.join(project_root, 'data', 'stats', 'knn_train.csv'),
        'fingerprints': os.path.join(project_root, 'data', 'recordings', 'current_fingerprints.csv'),
        'qr_events': os.path.join(project_root, 'data', 'qr_events.json')
    }


def load_latest_live(paths):
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
    finger_pos = tuple(finger_preds[-1]) if len(finger_preds) > 0 else None

    # --- Reset QR ---
    qr_reset = None
    if os.path.exists(paths['qr_events']):
        with open(paths['qr_events'], 'r', encoding='utf-8') as f:
            events = json.load(f)
        if events:
            qr_reset = tuple(events[-1]['position'])

    return pdr_pos, finger_pos, qr_reset


def fuse(pdr_pos, finger_pos, qr_reset=None):
    """
    Calcule la position fusionnée via un filtre de Kalman.
    """
    kf = KalmanFilter()
    # Reset initial state si QR disponible
    if qr_reset:
        kf.reset_state(qr_reset)
    # Prédiction (PDR)
    if pdr_pos:
        kf.predict(pdr_delta=pdr_pos)
    # Mise à jour (Fingerprint)
    if finger_pos:
        kf.update(measurement=finger_pos)
    return kf.get_state()


if __name__ == '__main__':
    paths = setup_paths()
    pdr_pos, finger_pos, qr_reset = load_latest_live(paths)
    if pdr_pos is None or finger_pos is None:
        raise RuntimeError("Données PDR ou fingerprint manquantes pour la fusion")
    fused_position = fuse(pdr_pos, finger_pos, qr_reset)
    print(f"Position fusionnée: {fused_position}")
