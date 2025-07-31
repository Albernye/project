# This code is a copy of PDR.py from Louis Royet's project on Indoor Navigation System

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt
from scipy.linalg import expm


def step_detection_accelerometer(magnitude, time, plot=True, fig_idx=1):
    # Calculate sample rate
    num_samples = len(magnitude)
    time_exp = time[-1] - time[0]
    freq_Acc = np.ceil(num_samples / time_exp)  # samples/s or Hz
    
    # Apply low-pass Butterworth filter
    order_filter = 4
    cutoff_freq = 2.0  # Hz
    b, a = butter(order_filter, cutoff_freq / (freq_Acc / 2), btype='low')
    Acc_mag_filt = filtfilt(b, a, magnitude)
    
    # Detect steps
    threshold_acc = 0.4  # Threshold of 0.4 m/s^2
    threshold_acc_discard = 2.0  # Threshold above which indicates excessive movement
    gravity = 9.8
    Acc_filt_binary = np.zeros(num_samples)
    Acc_filt_detrend = np.zeros(num_samples)
    
    for ii in range(1, num_samples):
        gravity = 0.999 * gravity + 0.001 * magnitude[ii]  # Experimental gravity calculation
        Acc_filt_detrend[ii] = Acc_mag_filt[ii] - gravity
        
        if Acc_filt_detrend[ii] > threshold_acc and Acc_filt_detrend[ii] < threshold_acc_discard:
            Acc_filt_binary[ii] = 1  # Up phases of body (start step)
        elif Acc_filt_detrend[ii] < -threshold_acc:
            if Acc_filt_binary[ii-1] == 1:
                Acc_filt_binary[ii] = 0
            else:
                Acc_filt_binary[ii] = -1  # Down phases of body (end step)
        else:
            Acc_filt_binary[ii] = 0  # Between thresholds

    StanceBegins_idx = []
    StepDect = np.zeros(num_samples)
    steps = np.full(num_samples, np.nan)
    window = int(0.4 * freq_Acc)  # Samples in window to consider 0.4 seconds

    for ii in range(window + 2, num_samples):
        if (Acc_filt_binary[ii] == -1 and Acc_filt_binary[ii - 1] == 0 \
            and np.sum(Acc_filt_binary[ii - window:ii - 2]) > 1):
            StepDect[ii] = 1
            StanceBegins_idx.append(ii)
        steps[ii] = 0 if StepDect[ii] else np.nan
    
    # Build StancePhase, guarding end-of-array
    StancePhase = np.zeros(num_samples)
    for idx in StanceBegins_idx:
        end = min(idx + 10, num_samples)
        StancePhase[idx:end] = 1

    Num_steps = len(StanceBegins_idx)
    
    # Plotting
    if plot:
        plt.figure(fig_idx)
        plt.plot(time, magnitude, 'r-', label='|Acc|')
        plt.plot(time, Acc_mag_filt, 'b-', label='lowpass(|Acc|)')
        plt.plot(time, Acc_filt_detrend, 'c-', label='detrend')
        plt.plot(time, Acc_filt_binary, 'gx-', label='Binary')
        plt.plot(time, steps, 'ro', markersize=8, label='Detected Steps')
        plt.title('Accelerometer Step Detection')
        plt.xlabel('Time (s)')
        plt.ylabel('Acceleration')
        plt.legend()
        plt.show()
    
    return Num_steps, StanceBegins_idx, StancePhase


def weiberg_stride_length_heading_position(acc, gyr, time, step_event, stance_phase, ver, idx_fig):
    # Constants
    K = 0.2  # Weinberg constant
    
    time_exp = time[-1] - time[0]
    num_samples_acc = acc.shape[0]
    freq_acc = np.ceil(num_samples_acc / time_exp)
    num_samples_gyr = gyr.shape[0]
    freq_gyr = np.ceil(num_samples_gyr / time_exp)

    if num_samples_acc != num_samples_gyr:
        min_samples = min(num_samples_acc, num_samples_gyr)
        acc = acc[:min_samples]
        gyr = gyr[:min_samples]
        num_samples_acc = num_samples_gyr = min_samples

    # Step 1: Magnitude
    m_acc = np.linalg.norm(acc, axis=1)
    # Step 2: Low-pass
    b, a = butter(4, 3 / (0.5 * freq_acc), btype='low')
    m_acc = filtfilt(b, a, m_acc)

    # Step 3: Stride lengths
    stride_lengths = []
    for ev in step_event:
        start = max(ev - 10, 0)
        end = min(ev + 10, num_samples_acc)
        acc_max = np.max(m_acc[start:end])
        acc_min = np.min(m_acc[start:end])
        bounce = (acc_max - acc_min)**0.25
        stride_lengths.append(bounce * K * 2)

    # Heading
    w = int(min(np.ceil(20 * freq_acc), num_samples_acc))
    acc_mean = np.mean(acc[:w, :], axis=0)
    roll = np.arctan2(acc_mean[1], acc_mean[2])
    pitch = -np.arctan2(acc_mean[0], np.hypot(acc_mean[1], acc_mean[2]))
    yaw = 0

    Rz = np.array([[np.cos(yaw), -np.sin(yaw), 0],[np.sin(yaw), np.cos(yaw), 0],[0,0,1]])
    Ry = np.array([[np.cos(pitch),0,np.sin(pitch)],[0,1,0],[-np.sin(pitch),0,np.cos(pitch)]])
    Rx = np.array([[1,0,0],[0,np.cos(roll),-np.sin(roll)],[0,np.sin(roll),np.cos(roll)]])

    rot = np.zeros((3,3,num_samples_acc))
    rot[:,:,0] = Rz @ Ry @ Rx
    dt = 1.0 / freq_gyr
    for i in range(1, num_samples_acc):
        gyro_i = gyr[i] * (np.pi/180 if np.max(np.abs(gyr[i])) > 10 else 1)
        S = np.array([[0,-gyro_i[2],gyro_i[1]],[gyro_i[2],0,-gyro_i[0]],[-gyro_i[1],gyro_i[0],0]])
        rot[:,:,i] = rot[:,:,i-1] @ expm(S * dt)

    thetas = np.zeros(len(step_event))
    idxs = np.clip((np.array(step_event) * freq_gyr / freq_acc).astype(int), 0, num_samples_acc-1)
    for i, idx in enumerate(idxs):
        thetas[i] = np.arctan2(rot[1,0,idx], rot[0,0,idx])

    # Positions
    pos = np.zeros((len(step_event),2))
    for i, theta in enumerate(thetas):
        if i==0:
            pos[i] = [stride_lengths[i]*np.cos(theta), stride_lengths[i]*np.sin(theta)]
        else:
            pos[i] = pos[i-1] + [stride_lengths[i]*np.cos(theta), stride_lengths[i]*np.sin(theta)]
    pos = np.vstack(([0,0], pos))

    if ver:
        plt.figure(idx_fig)
        plt.plot(pos[:,0], pos[:,1], 'bo-')
        plt.axis('equal'); plt.show()

    return thetas, pos


def pdr_delta(accel, gyro, fs):
    """
    Compute X/Y delta between last two steps given IMU arrays.
    """
    mag = np.linalg.norm(accel, axis=1)
    t = np.arange(len(mag)) / fs
    n, events, stance = step_detection_accelerometer(mag, t, plot=False)
    if len(events) < 2:
        return 0.0, 0.0
    thetas, pos = weiberg_stride_length_heading_position(accel, gyro, t, events, stance, ver=False, idx_fig=0)
    if pos.shape[0] < 2:
        return 0.0, 0.0
    dx = pos[-1,0] - pos[-2,0]
    dy = pos[-1,1] - pos[-2,1]
    return float(dx), float(dy)


def reset_pdr_state():
    pass
