# This code fuses PDR (and fingerprint) positions using a Kalman filter

import logging
from algorithms.filters import KalmanFilter

logger = logging.getLogger(__name__)
_kf = None

def get_floor(room: str) -> int:
    try: return int(room.split('-')[0])
    except: return 0

def fuse(pdr_delta=None, qr_anchor=None, room=None):
    global _kf
    if _kf is None:
        _kf = KalmanFilter()
        logger.info("KalmanFilter initialized")

    # QR hard reset
    if qr_anchor:
        xq,yq,fq = qr_anchor
        _kf.reset_state((xq,yq,fq))
        state = _kf.get_state()
    else:
        # PDR predict
        if pdr_delta:
            _kf.predict(pdr_delta)
        state = _kf.get_state()

    # Wi-Fi fingerprinting deprecated: code kept for reference
    # defunct wifi_pose argument removed from signature
    # Wi-Fi update
    # elif wifi_pose:
    #     xf,yf,ff = wifi_pose
    #     if ff is None and room: ff=get_floor(room)
    #     _kf.update((xf,yf,ff), source='wifi')
    
    # Defensive conversion: always return tuple/list of floats
    def to_float_tuple(val):
        import numpy as np
        if val is None:
            return (0.0, 0.0, 0.0)
        if isinstance(val, (list, tuple)) and all(isinstance(x, (int, float)) for x in val):
            return tuple(map(float, val))
        if isinstance(val, np.ndarray):
            return tuple(val.astype(float).tolist())
        return (0.0, 0.0, 0.0)

    result = to_float_tuple(state)
    logger.info(f"Fused state: {result}")
    return result

def reset_kalman():
    """Reset the global Kalman filter state."""
    global _kf
    _kf = None
    logger.info("KalmanFilter global reset")
