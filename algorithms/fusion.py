# This code fuses PDR and fingerprint positions using a Kalman filter

from scripts.geolocate import get_latest_positions
from algorithms.filters import KalmanFilter


_kf = None

def get_floor_from_room(room_str):
    """
    Extracts the floor number from a room identifier string.
    Example: "2-01" -> 2
    """
    try:
        return int(room_str[0])
    except (ValueError, IndexError):
        return None

def fuse(pdr_pos, finger_pos, qr_reset=None, room=None):
    """
    Fusionne les positions avec un filtre de Kalman :
    - pdr_pos : estimation par déplacement relatif (PDR) tuple (delta_x, delta_y)
    - finger_pos : estimation absolue (Wi-Fi fingerprint) tuple (x, y)
    - qr_reset : position absolue de référence (QR code) tuple (x, y)
    - room : identifiant de la salle (str) pour le logging

    Returns the fused position as a tuple (x, y, floor).
    """
    global _kf
    if _kf is None:
        _kf = KalmanFilter()

    # Reset avec QR si présent
    if qr_reset:
        lat, lon, *_ = qr_reset[:2]
        floor = get_floor_from_room(room)
        init_state = (lat, lon, floor) if floor is not None else (lat, lon)
        print(f"Resetting Kalman filter with position: {init_state}")
        _kf.reset_state(init_state)
        return _kf.get_state()

    # Mise à jour prédictive avec PDR
    if pdr_pos:
        dx, dy = pdr_pos[:2]
        dfloor = pdr_pos[2] if len(pdr_pos) > 2 else 0  # Pas de changement d'étage pour PDR
        delta3 = (dx, dy, dfloor)
        print(f"Applying PDR delta: {delta3}")
        _kf.predict(pdr_delta=delta3)

    # Mise à jour corrective avec fingerprint
    if finger_pos:
        x, y, *_ = finger_pos[:2]
        floor = finger_pos[2] if len(finger_pos) > 2 else get_floor_from_room(room)
        z3 = (x, y, floor) if floor is not None else (x, y)
        print(f"Updating Kalman filter with fingerprint position: {z3}")
        _kf.update(measurement=z3)

    return _kf.get_state()

def reset_kalman():
    global _kf
    _kf = None

if __name__ == '__main__':
    # Récupère les positions depuis geolocate.py
    pdr_pos, finger_pos, qr_reset = get_latest_positions()

    if not pdr_pos or not finger_pos:
        print("❌ Fusion impossible : position PDR ou fingerprint manquante.")
    else:
        fused = fuse(pdr_pos, finger_pos, qr_reset, room="2-01")
        print(f"✅ Position fusionnée : {fused}")
