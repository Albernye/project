# This code implements a Kalman Filter for estimating 2D position and floor level

import numpy as np

class KalmanFilter:
    """
    Kalman Filter for 2D position and floor estimation.
    State vector: [x, y, floor]^T
    Assumes simple motion model: x_k = x_{k-1} + delta (from PDR)
    Measurement model: z_k = H x_k + v (identity)
    """
    def __init__(self, Q=None, R=None):
        # State dimension
        self.dim = 3
        # Initial state (x, y, floor)
        self.x = np.zeros((self.dim, 1))
        # Initial covariance
        self.P = np.eye(self.dim) * 1.0
        # Process noise covariance
        self.Q = Q if Q is not None else np.eye(self.dim) * 0.1
        # Measurement noise covariance
        self.R = R if R is not None else np.eye(self.dim) * 2.0
        # Measurement matrix (identity)
        self.H = np.eye(self.dim)

    def reset_state(self, position):
        """
        Reset state to given absolute position (tuple or list).
        Also resets covariance to initial values.
        """
        self.x = np.array(position, dtype=float).reshape((self.dim, 1))
        self.P = np.eye(self.dim) * 1.0

    def predict(self, pdr_delta):
        """
        Prediction step: incorporate PDR delta movement.
        pdr_delta: tuple or list (dx, dy, dfloor)
        """
        # State prediction: x = x_prev + delta
        delta = np.array(pdr_delta, dtype=float).reshape((self.dim, 1))
        self.x = self.x + delta
        # Covariance prediction: P = P + Q
        self.P = self.P + self.Q

    def update(self, measurement):
        """
        Update step with fingerprint measurement.
        measurement: tuple or list (x, y, floor)
        """
        z = np.array(measurement, dtype=float).reshape((self.dim, 1))
        # Innovation: y = z - H x
        y = z - self.H.dot(self.x)
        # Innovation covariance: S = H P H^T + R
        S = self.H.dot(self.P).dot(self.H.T) + self.R
        # Kalman gain: K = P H^T S^{-1}
        K = self.P.dot(self.H.T).dot(np.linalg.inv(S))
        # State update: x = x + K y
        self.x = self.x + K.dot(y)
        # Covariance update: P = (I - K H) P
        I = np.eye(self.dim)
        self.P = (I - K.dot(self.H)).dot(self.P)

    def get_state(self):
        """
        Returns current state estimate as tuple (x, y, floor).
        """
        return tuple(self.x.flatten())
