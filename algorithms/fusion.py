# This code fuses PDR and fingerprint positions using a Kalman filter

from scripts.geolocate import get_latest_positions
from project.algorithms.filters import KalmanFilter


def fuse(pdr_pos, finger_pos, qr_reset=None):
    """
    Fusionne les positions avec un filtre de Kalman :
    - pdr_pos : estimation par déplacement relatif (PDR)
    - finger_pos : estimation absolue (Wi-Fi fingerprint)
    - qr_reset : position absolue de référence (QR code)
    """
    kf = KalmanFilter()

    # Reset avec QR si présent
    if qr_reset:
        kf.reset_state(qr_reset)

    # Mise à jour prédictive avec PDR
    if pdr_pos:
        kf.predict(pdr_delta=pdr_pos)

    # Mise à jour corrective avec fingerprint
    if finger_pos:
        kf.update(measurement=finger_pos)

    return kf.get_state()


if __name__ == '__main__':
    # Récupère les positions depuis geolocate.py
    pdr_pos, finger_pos, qr_reset = get_latest_positions()

    if not pdr_pos or not finger_pos:
        print("❌ Fusion impossible : position PDR ou fingerprint manquante.")
    else:
        fused = fuse(pdr_pos, finger_pos, qr_reset)
        print(f"✅ Position fusionnée : {fused}")
