# This code is a copy of PDR.py from Louis Royet's project on Indoor Navigation System

import pandas as pd
import numpy as np
import glob
import warnings
import math
import csv
import matplotlib.pyplot as plt
import scipy.linalg
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
    Acc_filt_binary = np.zeros(len(magnitude))
    Acc_filt_detrend = np.zeros(len(magnitude))
    
    for ii in range(1, len(magnitude)):
        gravity = 0.999 * gravity + 0.001 * magnitude[ii]  # Experimental gravity calculation
        Acc_filt_detrend[ii] = Acc_mag_filt[ii] - gravity
        
        if Acc_filt_detrend[ii] > threshold_acc and Acc_filt_detrend[ii] < threshold_acc_discard:
            Acc_filt_binary[ii] = 1  # Up phases of body (start step)
        else:
            if Acc_filt_detrend[ii] < -threshold_acc:
                if Acc_filt_binary[ii-1] == 1:
                    Acc_filt_binary[ii] = 0
                else:
                    Acc_filt_binary[ii] = -1  # Down phases of body (end step)
            else:
                Acc_filt_binary[ii] = 0  # Between upper and lower threshold

    step_count = 0
    StanceBegins_idx = []
    time_step= []
    StepDect = np.zeros(len(magnitude))
    steps = np.full(len(magnitude), np.nan)
    
    window = int(0.4 * freq_Acc)  # Samples in window to consider 0.4 seconds
    
    for ii in range(window + 2, len(magnitude)):
        if (Acc_filt_binary[ii] == -1 and Acc_filt_binary[ii - 1] == 0 and np.sum(Acc_filt_binary[ii - window:ii - 2]) > 1):
            StepDect[ii] = 1
            time_step.append(time[ii])
            
            step_count += 1
            StanceBegins_idx.append(ii)
            
        if StepDect[ii]:
            steps[ii] = 0
        else:
            steps[ii] = np.nan
    
    
    # All support samples
    StancePhase = np.zeros(num_samples)
    for ii in StanceBegins_idx:
        StancePhase[ii:ii + 10] = np.ones(10)  # Assume support phase is the 10 following samples after start of support phase (StanceBegins_idx)

    Num_steps = len(StanceBegins_idx)  # Number of counted steps
    
    # Plotting
    if plot:
        plt.figure(fig_idx)
        plt.plot(time, magnitude, 'r-', label='|Acc|')
        plt.plot(time, Acc_mag_filt, 'b-', label='lowpass(|Acc|)')
        plt.plot(time, Acc_filt_detrend, 'c-', label='detrend(lowpass(|Acc|))')
        plt.plot(time, Acc_filt_binary, 'gx-', label='Binary')
        plt.plot(time, steps, 'ro', markersize=8, label='Detected Steps')
        plt.title('"SL+theta PDR": Accelerometer processing for Step detection')
        plt.xlabel('time (seconds)')
        plt.ylabel('Acceleration')
        plt.legend()
        plt.show()
    
    #print(time_step)
    
    return Num_steps, StanceBegins_idx, StancePhase

def weiberg_stride_length_heading_position(acc, gyr, time, step_event, stance_phase, ver, idx_fig):
    # Constants
    K = 0.2  # Weinberg constant dependent on each person or walking mode

    # Extracting data sizes and frequencies
    time_exp=time[-1]-time[0]
    print(time_exp)
    
    num_samples_acc = acc.shape[0]
    print(num_samples_acc)
    freq_acc = np.ceil(num_samples_acc / time_exp)
    print(freq_acc)

    num_samples_gyr = gyr.shape[0]
    freq_gyr = np.ceil(num_samples_gyr / time_exp)
    
    

    # Step 1: Magnitude of accelerometer data
    m_acc = np.sqrt(acc[:, 0]**2 + acc[:, 1]**2 + acc[:, 2]**2)

    # Step 2: Low-pass filter
    cutoff_freq = 3  # Hz
    b, a = butter(4, cutoff_freq / freq_acc, btype='low')
    m_acc = filtfilt(b, a, m_acc)

    # Step 3: Weiberg's algorithm for stride length estimation
    stride_lengths = []
    for i in range(len(step_event)):
        sample_step_event = step_event[i]
        acc_max = np.max(m_acc[:sample_step_event])
        acc_min = np.min(m_acc[:sample_step_event])
        bounce = (acc_max - acc_min)**(1/4)
        stride_length = bounce * K * 2
        stride_lengths.append(stride_length)

    # Step 4: Heading direction (Thetas) after each step
    # Initialize rotation matrix at initial sample
    w = np.arange(0, np.ceil(20 * freq_acc), dtype=int)  # Window for initial rest assumption
    acc_mean = np.mean(acc[w, :], axis=0)
    roll_ini = np.arctan2(acc_mean[1], acc_mean[2]) * 180 / np.pi
    pitch_ini = -np.arctan2(acc_mean[0], np.sqrt(acc_mean[1]**2 + acc_mean[2]**2)) * 180 / np.pi
    yaw_ini = 0
    rot_gs = np.zeros((3, 3, num_samples_acc))
    rot_z = np.array([[np.cos(yaw_ini*np.pi/180), -np.sin(yaw_ini*np.pi/180), 0],
                      [np.sin(yaw_ini*np.pi/180), np.cos(yaw_ini*np.pi/180), 0],
                      [0, 0, 1]])
    rot_y = np.array([[np.cos(pitch_ini*np.pi/180), 0, np.sin(pitch_ini*np.pi/180)],
                      [0, 1, 0],
                      [-np.sin(pitch_ini*np.pi/180), 0, np.cos(pitch_ini*np.pi/180)]])
    rot_x = np.array([[1, 0, 0],
                      [0, np.cos(roll_ini*np.pi/180), -np.sin(roll_ini*np.pi/180)],
                      [0, np.sin(roll_ini*np.pi/180), np.cos(roll_ini*np.pi/180)]])
    rot_gs[:, :, 0] = np.dot(rot_z, np.dot(rot_y, rot_x))

    # Propagate rotation matrix to all samples using gyroscope data
    for i in range(1, num_samples_gyr):
        skew_gyros = np.array([[0, -gyr[i, 2], gyr[i, 1]],
                               [gyr[i, 2], 0, -gyr[i, 0]],
                               [-gyr[i, 1], gyr[i, 0], 0]])  # Skew-symmetric matrix
        rot_gs[:, :, i] = np.dot(rot_gs[:, :, i - 1], expm(skew_gyros / freq_gyr))  # Using matrix exponential

    # Calculate heading direction (Thetas)
    thetas = np.zeros(len(step_event))
    step_event_gyro = np.floor(np.array(step_event) * freq_gyr / freq_acc).astype(int)
    for k in range(len(step_event)):
        thetas[k] = np.arctan2(rot_gs[1, 0, step_event_gyro[k]], rot_gs[0, 0, step_event_gyro[k]])

    # Step 5: Positions after integration (PDR results)
    positions = np.zeros((len(step_event), 2))
    for k in range(len(step_event)):
        if k == 0:
            positions[k, 0] = stride_lengths[k] * np.cos(thetas[k])
            positions[k, 1] = stride_lengths[k] * np.sin(thetas[k])
        else:
            positions[k, 0] = positions[k - 1, 0] + stride_lengths[k] * np.cos(thetas[k])
            positions[k, 1] = positions[k - 1, 1] + stride_lengths[k] * np.sin(thetas[k])
    
    positions = np.vstack((np.array([0, 0]), positions))  # Adding initial position (0,0)

    # Plotting (if ver is True)
    if ver:
        #plt.figure(idx_fig)
        #plt.plot(stride_lengths, 'bo-', label='StrideLengths (m)')
        #plt.plot(thetas, 'rx-', label='Thetas (rad)')
        #plt.legend()
        #plt.title('StrideLengths and Thetas')
        #plt.xlabel('Steps')
        #plt.grid(True)
        #idx_fig += 1

        plt.figure(idx_fig)
        plt.plot(positions[:, 0], positions[:, 1], 'bo-', label='Positions')
        plt.plot(positions[0, 0], positions[0, 1], 'bs', markersize=8, markerfacecolor=[0, 0, 1])
        plt.plot(positions[-1, 0], positions[-1, 1], 'bo', markersize=8, markerfacecolor=[0, 0, 1])
        plt.title('Positions')
        plt.xlabel('East (m)')
        plt.ylabel('North (m)')
        plt.axis('equal')
        plt.grid(True)
        idx_fig += 1

        plt.show()

    return thetas, positions

def PDR(testfile):
    test=pd.read_csv(testfile, delimiter=';')
    Acc_Magn_temp = test[['ACCE_MOD']].values.tolist()
    Gyr_Magn_temp = test[['GYRO_MOD']].values.tolist()
    ACCE=test[['ACCE_X','ACCE_Y','ACCE_X']].values
    GYRO=test[['GYRO_X','GYRO_Y','GYRO_X']].values
    time_temp = test[['timestamp']].values.tolist()
    POSI_X= test[['POSI_X']].values.tolist()
    POSI_Y= test[['POSI_Y']].values.tolist()

    Acc_Magn=[]
    Gyr_Magn=[]
    time=[]
    X=[]
    Y=[]

    for i in range(len(Acc_Magn_temp)):
        Acc_Magn.append(Acc_Magn_temp[i][0])
        Gyr_Magn.append(Gyr_Magn_temp[i][0])
        time.append(time_temp[i][0])
        X.append(POSI_X[i][0])
        Y.append(POSI_Y[i][0])


    index_start=0
    X = test[['POSI_X']].values
    while X[index_start] == 0:
        index_start += 1
    print(index_start)

    ACCE=ACCE[index_start:]
    GYRO=GYRO[index_start:]
    time=time[index_start:]
    Acc_Magn=Acc_Magn[index_start:]
    Gyr_Magn=Gyr_Magn[index_start:]

    a,Steps,Stance=step_detection_accelerometer(Acc_Magn, time, plot=False, fig_idx=1)

    thetas, positions = weiberg_stride_length_heading_position(ACCE,GYRO,time,Steps,Stance,1,1)

    return thetas, positions 