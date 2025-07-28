import numpy as np
from scipy.signal import butter, filtfilt, find_peaks


def lowpass_filter(data, cutoff, fs, order=2):
    """
    Apply a Butterworth low-pass filter.

    Args:
        data (np.ndarray): 1D signal.
        cutoff (float): cutoff frequency in Hz.
        fs (float): sampling rate in Hz.
        order (int): filter order.

    Returns:
        np.ndarray: filtered signal.
    """
    nyq = 0.5 * fs
    b, a = butter(order, cutoff / nyq, btype="low", analog=False)
    return filtfilt(b, a, data)


def detect_steps(accel_mag, fs, threshold=0.5, min_distance=0.3):
    """
    Detect step events from accelerometer magnitude.

    Args:
        accel_mag (np.ndarray): magnitude of acceleration (Nx).
        fs (float): sampling rate in Hz.
        threshold (float): minimum peak height.
        min_distance (float): minimum time between steps (s).

    Returns:
        np.ndarray: indices of detected steps.
    """
    # remove gravity via low-pass
    gravity = lowpass_filter(accel_mag, cutoff=0.3, fs=fs, order=2)
    detrended = accel_mag - gravity

    # find peaks
    distance_samples = int(min_distance * fs)
    peaks, _ = find_peaks(detrended, height=threshold, distance=distance_samples)
    return peaks


def compute_stride_lengths(accel_mag, peaks, K=0.2, window=5):
    """
    Compute stride lengths using Weinberg's model.

    Args:
        accel_mag (np.ndarray): magnitude of acceleration (Nx).
        peaks (np.ndarray): step event indices.
        K (float): Weinberg constant.
        window (int): number of samples around peak.

    Returns:
        np.ndarray: stride lengths per step.
    """
    strides = []
    for p in peaks:
        start = max(p - window, 0)
        end = min(p + window, len(accel_mag) - 1)
        segment = accel_mag[start:end]
        bounce = (segment.max() - segment.min()) ** 0.25
        strides.append(2 * K * bounce)
    return np.array(strides)


def compute_headings(gyro_z, fs, peaks):
    """
    Compute heading (yaw) at each step by integrating gyro Z.

    Args:
        gyro_z (np.ndarray): angular rate around Z-axis (rad/s).
        fs (float): sampling rate.
        peaks (np.ndarray): step indices.

    Returns:
        np.ndarray: heading per step.
    """
    yaw = np.cumsum(gyro_z) / fs
    idx = np.clip(peaks, 0, len(yaw) - 1)
    return yaw[idx]


def pdr_delta(accel, gyro, fs):
    """
    Compute the X/Y delta from the last two detected steps.

    Args:
        accel (np.ndarray): Nx3 accelerometer data.
        gyro (np.ndarray): Nx3 gyroscope data (rad/s).
        fs (float): sampling rate.

    Returns:
        (dx, dy): tuple of floats for displacement.
    """
    mag = np.linalg.norm(accel, axis=1)
    peaks = detect_steps(mag, fs)
    if len(peaks) < 2:
        return 0.0, 0.0

    strides = compute_stride_lengths(mag, peaks)
    headings = compute_headings(gyro[:, 2], fs, peaks)

    # cumulative positions
    x = np.cumsum(strides * np.cos(headings))
    y = np.cumsum(strides * np.sin(headings))

    # return last step delta
    dx = x[-1] - x[-2]
    dy = y[-1] - y[-2]
    return dx, dy
