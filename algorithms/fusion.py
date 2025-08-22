# This code fuses PDR and QR (and fingerprint) anchors positions using a Kalman filter
# Internal state is kept in local meters, output is converted back to GPS

import logging
from services.geolocate import normalize_position_to_3tuple
from algorithms.fingerprint import local_to_ll, ll_to_local, set_origin
from algorithms.filters import KalmanFilter

logger = logging.getLogger(__name__)
_kf = None

def set_origin_gps(lon: float, lat: float):
    """
    Set the origin for local coordinate transformation.

    Args:
        lon: Origin longitude in decimal degrees
        lat: Origin latitude in decimal degrees
    """
    global _kf
    set_origin(lon, lat)
    logger.info(f"Origin set at ({lon}, {lat})")
    # Reset Kalman when origin changes
    if _kf is not None:
        _kf.reset_state((0.0, 0.0, 0.0))
        logger.info("KalmanFilter reset due to origin change")

def get_floor(room: str) -> int:
    """Extract floor number from room string, fallback to 0."""
    try:
        return int(room.split('-')[0])
    except Exception:
        return 0

def to_float_tuple(val):
    """
    Defensive conversion: always return tuple/list of floats.
    """
    import numpy as np
    if val is None:
        return (0.0, 0.0, 0.0)
    if isinstance(val, (list, tuple)) and all(isinstance(x, (int, float)) for x in val):
        return tuple(map(float, val))
    if isinstance(val, np.ndarray):
        return tuple(val.astype(float).tolist())
    return (0.0, 0.0, 0.0)

# ------------------------------------------------------
# Main fusion logic
# ------------------------------------------------------

def fuse(pdr_delta=None, qr_anchor=None, fingerprint=None, room=None):
    """
    Fuse positions using Kalman filter.
    QR anchor > PDR delta.
    Returns (lon, lat, floor) tuple of floats.
    """
    global _kf

    if _kf is None:
        _kf = KalmanFilter()
        logger.info("KalmanFilter initialized")

    # --- QR hard reset ---
    if qr_anchor:
        pos_gps = to_float_tuple(normalize_position_to_3tuple(qr_anchor))
        x, y = ll_to_local(pos_gps[0], pos_gps[1])
        z = pos_gps[2] if pos_gps[2] is not None else get_floor(room)
        _kf.reset_state((x, y, z))
        state = to_float_tuple(_kf.get_state())

    # --- PDR predict ---
    elif pdr_delta:
        state = to_float_tuple(_kf.get_state() or (0.0, 0.0, get_floor(room)))
        dx, dy = pdr_delta[:2] if len(pdr_delta) >= 2 else (0.0, 0.0)
        _kf.predict((dx, dy, 0.0))  # Floor stable
        state = to_float_tuple(_kf.get_state())

    # --- fallback ---
    else:
        state = to_float_tuple(_kf.get_state() or (0.0, 0.0, get_floor(room)))

    # Wi-Fi fingerprinting deprecated: code kept for reference
    # defunct wifi_pose argument removed from signature
    # Wi-Fi update
    # elif wifi_pose:
    #     xf,yf,ff = wifi_pose
    #     if ff is None and room: ff=get_floor(room)
    #     _kf.update((xf,yf,ff), source='wifi')

    # --- Convert back from local meters to GPS ---
    x, y, z = state
    lon, lat = local_to_ll(x, y)
    floor = z

    result = (float(lon), float(lat), float(floor))
    logger.info(f"Fused state: {result}")
    return result

def reset_kalman():
    """Reset the global Kalman filter state."""
    global _kf
    _kf = None
    logger.info("KalmanFilter global reset")
