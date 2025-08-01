# This code implements a Kalman Filter for estimating 2D position and floor level

import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def load_imu(pdr_file):
    """Load IMU data from CSV and return accel (Nx3), gyro (Nx3, rad/s), and sampling rate fs."""
    df = pd.read_csv(pdr_file, delimiter=';')
    accel = df[['ACCE_X','ACCE_Y','ACCE_Z']].values
    gyro_deg = df[['GYRO_X','GYRO_Y','GYRO_Z']].values
    gyro = np.deg2rad(gyro_deg)
    timestamps = df['timestamp'].values.astype(float)
    dt = np.diff(timestamps)
    fs = 1.0 / np.mean(dt) if len(dt) > 1 else None
    return accel, gyro, fs

class KalmanFilter:
    """
    3-state Kalman Filter: [x, y, floor]
    """
    def __init__(self,
                 Q=np.diag([0.1,0.1,0.01]),
                 R_wifi=np.diag([2.0,2.0,0.1]),
                 R_qr=np.diag([0.01,0.01,0.01])):
        self.dim = 3
        self.x = np.zeros((3,1))
        self.P = np.eye(3)
        self.Q = Q
        self.R_wifi = R_wifi
        self.R_qr = R_qr
        self.H = np.eye(3)

    def reset_state(self, state: tuple):
        if len(state)!=3: raise ValueError
        self.x = np.array(state, float).reshape(3,1)
        self.P = np.eye(3)
        logger.info(f"Filter reset to {state}")

    def predict(self, delta: tuple, Q_override=None):
        dx,dy,df = (list(delta)+[0,0,0])[:3]
        u = np.array([dx,dy,df]).reshape(3,1)
        self.x += u
        Q = Q_override if Q_override is not None else self.Q
        self.P += Q
        logger.debug(f"Predict {delta}, x={self.x.flatten()}")

    def update(self, meas: tuple, source: str='wifi', R_override=None):
        if len(meas)!=3: raise ValueError
        z = np.array(meas,float).reshape(3,1)
        R = R_override if R_override is not None else (self.R_qr if source=='qr' else self.R_wifi)
        y = z - self.H@self.x
        S = self.H@self.P@self.H.T + R
        K = self.P@self.H.T @ np.linalg.inv(S)
        self.x += K@y
        self.P = (np.eye(3)-K@self.H)@self.P
        logger.debug(f"Update {source} {meas}, x={self.x.flatten()}")

    def get_state(self) -> tuple:
        return tuple(self.x.flatten())