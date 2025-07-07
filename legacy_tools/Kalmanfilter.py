import pandas as pd
import numpy as np
import json
import warnings
import math
import csv
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt
from scipy.linalg import expm
from sklearn.neighbors import KNeighborsRegressor
from datetime import datetime
import os
from bisect import bisect_right

# Suppress warnings
warnings.filterwarnings('ignore')

def find_most_recent_index(timestamps, reference_time):
    """Find the most recent timestamp index for a given reference time"""
    pos = bisect_right(timestamps, reference_time)
    return pos - 1 if pos > 0 else None

def latlon_to_xy(latitude, longitude, origin_latitude, origin_longitude):
    """Convert latitude/longitude to local XY coordinates"""
    R = 6371000  # Earth radius in meters
    
    lat_rad = math.radians(latitude)
    lon_rad = math.radians(longitude)
    origin_lat_rad = math.radians(origin_latitude)
    origin_lon_rad = math.radians(origin_longitude)
    
    delta_lon = lon_rad - origin_lon_rad
    delta_lat = lat_rad - origin_lat_rad
    
    x = delta_lon * math.cos(origin_lat_rad) * R
    y = delta_lat * R
    
    return x, y

def kalman_filter_predict(xk_1, Pk_1, A, B, u, Q):
    """Kalman filter prediction step"""
    xk_pred = A @ xk_1 + B @ u
    Pk_pred = A @ Pk_1 @ A.T + Q
    return xk_pred, Pk_pred

def kalman_filter_update(xk_pred, Pk_pred, zk, H, R):
    """Kalman filter update step"""
    innovation = zk - H @ xk_pred
    S = H @ Pk_pred @ H.T + R
    Kk = Pk_pred @ H.T @ np.linalg.inv(S)
    xk = xk_pred + Kk @ innovation
    Pk = (np.eye(len(Pk_pred)) - Kk @ H) @ Pk_pred
    return xk, Pk

def kalman_filter_3d(stride_lengths, thetas, wifi_positions, q, r):
    """
    3D Kalman filter for sensor fusion
    Args:
        stride_lengths: Array of stride lengths from PDR
        thetas: Array of heading angles from PDR
        wifi_positions: Array of WiFi-based positions (x, y, z)
        q: Process noise variance
        r: Measurement noise variance
    """
    if len(stride_lengths) == 0 or len(wifi_positions) == 0:
        return np.array([])
    
    # Initialize state [x, y, z, theta]
    xk = np.array([0.0, 0.0, wifi_positions[0, 2], 0.0])
    Pk = np.eye(4) * 1.0
    
    # State transition matrix
    A = np.eye(4)
    
    # Measurement matrix (observe x, y, z)
    H = np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0]
    ])
    
    # Process noise covariance
    Q = np.eye(4) * q
    
    # Measurement noise covariance
    R = np.eye(3) * r
    
    estimated_positions = []
    
    for k in range(len(stride_lengths)):
        # Control input (stride length and heading change)
        L = stride_lengths[k]
        theta_current = thetas[k] if k < len(thetas) else 0.0
        
        # Control matrix
        B = np.array([
            [np.cos(xk[3]), 0],
            [np.sin(xk[3]), 0],
            [0, 0],
            [0, 1]
        ])
        
        # Control vector
        u = np.array([L, theta_current - xk[3] if k > 0 else theta_current])
        
        # Prediction step
        xk_pred, Pk_pred = kalman_filter_predict(xk, Pk, A, B, u, Q)
        
        # Update step with WiFi measurement
        if k < len(wifi_positions):
            zk = wifi_positions[k]
            xk, Pk = kalman_filter_update(xk_pred, Pk_pred, zk, H, R)
        else:
            xk, Pk = xk_pred, Pk_pred
        
        # Update heading in state
        xk[3] = theta_current
        
        # Store estimated position
        estimated_positions.append(xk[:3].copy())
    
    return np.array(estimated_positions)

def step_detection_accelerometer(magnitude, time, plot=True, fig_idx=1):
    """
    Step detection based on accelerometer magnitude
    """
    if len(magnitude) == 0 or len(time) == 0:
        return 0, [], np.array([])
    
    # Calculate sample rate
    num_samples = len(magnitude)
    time_exp = time[-1] - time[0]
    if time_exp <= 0:
        return 0, [], np.array([])
    
    freq_Acc = np.ceil(num_samples / time_exp)  # samples/s or Hz
    
    # Apply low-pass Butterworth filter
    order_filter = 4
    cutoff_freq = 2.0  # Hz
    nyquist = freq_Acc / 2
    if cutoff_freq >= nyquist:
        cutoff_freq = nyquist * 0.9
    
    b, a = butter(order_filter, cutoff_freq / nyquist, btype='low')
    Acc_mag_filt = filtfilt(b, a, magnitude)
    
    # Detect steps
    threshold_acc = 0.4  # Threshold of 0.4 m/s^2
    threshold_acc_discard = 2.0  # Threshold above which indicates excessive movement
    gravity = 9.8
    Acc_filt_binary = np.zeros(len(magnitude))
    Acc_filt_detrend = np.zeros(len(magnitude))
    
    for ii in range(1, len(magnitude)):
        gravity = 0.999 * gravity + 0.001 * magnitude[ii]
        Acc_filt_detrend[ii] = Acc_mag_filt[ii] - gravity
        
        if Acc_filt_detrend[ii] > threshold_acc and Acc_filt_detrend[ii] < threshold_acc_discard:
            Acc_filt_binary[ii] = 1  # Up phases of body (start step)
        else:
            if Acc_filt_detrend[ii] < -threshold_acc:
                if ii > 0 and Acc_filt_binary[ii-1] == 1:
                    Acc_filt_binary[ii] = 0
                else:
                    Acc_filt_binary[ii] = -1  # Down phases of body (end step)
            else:
                Acc_filt_binary[ii] = 0  # Between upper and lower threshold

    step_count = 0
    StanceBegins_idx = []
    time_step = []
    StepDect = np.zeros(len(magnitude))
    steps = np.full(len(magnitude), np.nan)
    
    window = int(0.4 * freq_Acc)  # Samples in window to consider 0.4 seconds
    
    for ii in range(window + 2, len(magnitude)):
        if (Acc_filt_binary[ii] == -1 and Acc_filt_binary[ii - 1] == 0 and 
            np.sum(Acc_filt_binary[ii - window:ii - 2]) > 1):
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
        end_idx = min(ii + 10, num_samples)
        StancePhase[ii:end_idx] = 1
    
    # Plotting
    if plot:
        plt.figure(fig_idx)
        plt.plot(time, magnitude, 'r-', label='|Acc|')
        plt.plot(time, Acc_mag_filt, 'b-', label='lowpass(|Acc|)')
        plt.plot(time, Acc_filt_detrend, 'c-', label='detrend(lowpass(|Acc|))')
        plt.plot(time, Acc_filt_binary, 'gx-', label='Binary')
        plt.plot(time, steps, 'ro', markersize=8, label='Detected Steps')
        plt.title('Step Detection from Accelerometer')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Acceleration (m/s²)')
        plt.legend()
        plt.grid(True)
        plt.show()
    
    return step_count, StanceBegins_idx, StancePhase

def weiberg_stride_length_heading_position(acc, gyr, time, step_event, stance_phase, ver=True, idx_fig=1):
    """
    Weinberg algorithm for stride length and heading estimation
    """
    if len(step_event) == 0:
        return np.array([]), np.array([]).reshape(0, 2), np.array([])
    
    # Weinberg constant (to be calibrated for each person)
    K = 0.4
    
    # Calculate frequencies
    time_exp = time[-1] - time[0]
    if time_exp <= 0:
        return np.array([]), np.array([]).reshape(0, 2), np.array([])
    
    num_samples_acc = acc.shape[0]
    freq_acc = np.ceil(num_samples_acc / time_exp)
    
    num_samples_gyr = gyr.shape[0]
    freq_gyr = np.ceil(num_samples_gyr / time_exp)
    
    print(f"Recording duration: {time_exp:.2f} seconds")
    print(f"Accelerometer frequency: {freq_acc} Hz")
    print(f"Gyroscope frequency: {freq_gyr} Hz")
    
    # Calculate accelerometer magnitude
    m_acc = np.sqrt(acc[:, 0]**2 + acc[:, 1]**2 + acc[:, 2]**2)
    
    # Apply low-pass filter
    cutoff_freq = 3  # Hz
    nyquist = freq_acc / 2
    if cutoff_freq >= nyquist:
        cutoff_freq = nyquist * 0.9
    
    b, a = butter(4, cutoff_freq / nyquist, btype='low')
    m_acc = filtfilt(b, a, m_acc)
    
    # Weinberg stride length estimation
    stride_lengths = []
    for i in range(len(step_event)):
        sample_step_event = step_event[i]
        if sample_step_event < len(m_acc):
            # Calculate over a window around the detected step
            window_start = max(0, sample_step_event - 20)
            window_end = min(len(m_acc), sample_step_event + 20)
            acc_max = np.max(m_acc[window_start:window_end])
            acc_min = np.min(m_acc[window_start:window_end])
            
            if acc_max > acc_min:
                bounce = (acc_max - acc_min)**(1/4)
                stride_length = bounce * K
                stride_lengths.append(max(stride_length, 0.3))  # Minimum stride length
            else:
                stride_lengths.append(0.7)  # Default stride length
        else:
            stride_lengths.append(0.7)
    
    # Initialize rotation matrix
    w = np.arange(0, min(int(np.ceil(5 * freq_acc)), len(acc)), dtype=int)
    if len(w) > 0:
        acc_mean = np.mean(acc[w, :], axis=0)
        roll_ini = np.arctan2(acc_mean[1], acc_mean[2])
        pitch_ini = -np.arctan2(acc_mean[0], np.sqrt(acc_mean[1]**2 + acc_mean[2]**2))
        yaw_ini = 0
    else:
        roll_ini = pitch_ini = yaw_ini = 0
    
    rot_gs = np.zeros((3, 3, num_samples_acc))
    
    # Initial rotation matrix
    rot_z = np.array([[np.cos(yaw_ini), -np.sin(yaw_ini), 0],
                      [np.sin(yaw_ini), np.cos(yaw_ini), 0],
                      [0, 0, 1]])
    rot_y = np.array([[np.cos(pitch_ini), 0, np.sin(pitch_ini)],
                      [0, 1, 0],
                      [-np.sin(pitch_ini), 0, np.cos(pitch_ini)]])
    rot_x = np.array([[1, 0, 0],
                      [0, np.cos(roll_ini), -np.sin(roll_ini)],
                      [0, np.sin(roll_ini), np.cos(roll_ini)]])
    
    rot_gs[:, :, 0] = rot_z @ rot_y @ rot_x
    
    # Propagate rotation matrix using gyroscope data
    for i in range(1, min(num_samples_gyr, num_samples_acc)):
        skew_gyros = np.array([[0, -gyr[i, 2], gyr[i, 1]],
                               [gyr[i, 2], 0, -gyr[i, 0]],
                               [-gyr[i, 1], gyr[i, 0], 0]])
        
        if freq_gyr > 0:
            rot_gs[:, :, i] = rot_gs[:, :, i - 1] @ expm(skew_gyros / freq_gyr)
    
    # Calculate heading directions
    thetas = np.zeros(len(step_event))
    step_event_gyro = np.floor(np.array(step_event) * freq_gyr / freq_acc).astype(int)
    
    for k in range(len(step_event)):
        gyro_idx = min(step_event_gyro[k], num_samples_acc - 1)
        thetas[k] = np.arctan2(rot_gs[1, 0, gyro_idx], rot_gs[0, 0, gyro_idx])
    
    # Calculate positions using PDR
    positions = np.zeros((len(step_event), 2))
    for k in range(len(step_event)):
        if k == 0:
            positions[k, 0] = stride_lengths[k] * np.cos(thetas[k])
            positions[k, 1] = stride_lengths[k] * np.sin(thetas[k])
        else:
            positions[k, 0] = positions[k - 1, 0] + stride_lengths[k] * np.cos(thetas[k])
            positions[k, 1] = positions[k - 1, 1] + stride_lengths[k] * np.sin(thetas[k])
    
    # Add initial position
    positions = np.vstack((np.array([0, 0]), positions))
    
    # Plotting
    if ver:
        plt.figure(idx_fig)
        plt.plot(positions[:, 0], positions[:, 1], 'bo-', label='PDR Positions')
        plt.plot(positions[0, 0], positions[0, 1], 'gs', markersize=10, label='Start')
        plt.plot(positions[-1, 0], positions[-1, 1], 'rs', markersize=10, label='End')
        plt.title(f'PDR Trajectory - {len(step_event)} steps detected')
        plt.xlabel('East (m)')
        plt.ylabel('North (m)')
        plt.axis('equal')
        plt.grid(True)
        plt.legend()
        plt.show()
    
    return thetas, positions, stride_lengths

def load_json_recording(json_file_path):
    """
    Load JSON recording and extract IMU data
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return np.array([]), np.array([]), np.array([]), {}
    
    # Extract accelerometer data
    acc_data = data.get('accelerometer', [])
    if acc_data:
        acc_array = np.array([[sample.get('x', 0), sample.get('y', 0), sample.get('z', 0)] 
                             for sample in acc_data])
    else:
        acc_array = np.array([])
    
    # Extract gyroscope data
    gyr_data = data.get('gyroscope', [])
    if gyr_data:
        # Convert alpha, beta, gamma to x, y, z
        gyr_array = np.array([[sample.get('alpha', 0), sample.get('beta', 0), sample.get('gamma', 0)] 
                             for sample in gyr_data])
    else:
        gyr_array = np.array([])
    
    # Generate timestamps
    num_samples = len(acc_data)
    if num_samples > 0:
        sample_rate = 50.0  # Adjust according to your sensors
        time_array = np.arange(num_samples) / sample_rate
    else:
        time_array = np.array([])
    
    return acc_array, gyr_array, time_array, data

def extract_wifi_features(wifi_data):
    """
    Extract WiFi RSSI features from JSON data
    """
    if not wifi_data:
        return np.array([])
    
    # Create a dictionary of AP MAC addresses to RSSI values
    wifi_dict = {}
    for ap in wifi_data:
        mac = ap.get('BSSID', '')
        rssi = ap.get('level', -100)  # Default to -100 if no RSSI
        wifi_dict[mac] = rssi
    
    # Convert to feature vector (you may need to standardize AP order)
    features = list(wifi_dict.values())
    return np.array(features)

def PDR_from_json(json_file_path, plot=True, K_parameter=0.4):
    """
    PDR function adapted for JSON recording files
    """
    print(f"Processing file: {json_file_path}")
    
    # Load data
    acc_array, gyr_array, time_array, raw_data = load_json_recording(json_file_path)
    
    if len(acc_array) == 0:
        print("No accelerometer data found in file")
        return None, None, None, None
    
    # Calculate accelerometer magnitude
    acc_magnitude = np.sqrt(acc_array[:, 0]**2 + acc_array[:, 1]**2 + acc_array[:, 2]**2)
    
    # Step detection
    num_steps, step_indices, stance_phase = step_detection_accelerometer(
        acc_magnitude, time_array, plot=plot, fig_idx=1
    )
    
    print(f"Number of steps detected: {num_steps}")
    
    if num_steps == 0:
        print("No steps detected")
        return np.array([]), np.array([]), np.array([]), raw_data
    
    # Calculate PDR positions
    thetas, positions, stride_lengths = weiberg_stride_length_heading_position(
        acc_array, gyr_array, time_array, step_indices, stance_phase,
        ver=plot, idx_fig=2
    )
    
    # Metadata
    metadata = {
        'room': raw_data.get('room', 'unknown'),
        'num_steps': num_steps,
        'total_distance': np.sum(stride_lengths) if len(stride_lengths) > 0 else 0,
        'duration': time_array[-1] if len(time_array) > 0 else 0,
        'avg_step_length': np.mean(stride_lengths) if len(stride_lengths) > 0 else 0,
        'wifi_aps': len(raw_data.get('wifi', [])),
        'gps_available': 'gps' in raw_data and raw_data['gps'] is not None
    }
    
    print(f"Total distance traveled: {metadata['total_distance']:.2f} m")
    print(f"Average step length: {metadata['avg_step_length']:.2f} m")
    
    return thetas, positions, stride_lengths, metadata

def integrated_positioning_system(json_file_path, wifi_training_data=None, plot=True, q=0.1, r=1.0):
    """
    Integrated positioning system combining PDR and WiFi fingerprinting with Kalman filtering
    
    Args:
        json_file_path: Path to JSON recording file
        wifi_training_data: Training data for WiFi fingerprinting (DataFrame or file path)
        plot: Whether to show plots
        q: Process noise covariance
        r: Measurement noise covariance
    """
    print(f"Processing integrated positioning for: {json_file_path}")
    
    # Step 1: PDR processing
    thetas, positions, stride_lengths, metadata = PDR_from_json(json_file_path, plot=False)
    
    if positions is None or len(positions) == 0:
        print("No PDR data available")
        return None, None
    
    # Step 2: WiFi fingerprinting (if training data available)
    wifi_positions = None
    if wifi_training_data is not None:
        try:
            # Load training data
            if isinstance(wifi_training_data, str):
                train_data = pd.read_csv(wifi_training_data, delimiter=';')
            else:
                train_data = wifi_training_data
            
            # Extract training features and positions
            position_cols = ['long', 'lat', 'Z']
            if all(col in train_data.columns for col in position_cols):
                train_positions = train_data[position_cols].values
                train_features = train_data.drop(columns=position_cols).values
                
                # Load test data WiFi features
                _, _, _, raw_data = load_json_recording(json_file_path)
                wifi_data = raw_data.get('wifi', [])
                
                if wifi_data:
                    # Extract WiFi features from test data
                    test_features = extract_wifi_features(wifi_data)
                    
                    if len(test_features) > 0:
                        # KNN positioning
                        knn = KNeighborsRegressor(n_neighbors=3)
                        knn.fit(train_features, train_positions)
                        
                        # Create WiFi positions for each step
                        wifi_positions = np.array([knn.predict([test_features])[0] 
                                                 for _ in range(len(stride_lengths))])
                        
                        # Convert to local coordinates if needed
                        if len(wifi_positions) > 0:
                            origin_lat, origin_lon = wifi_positions[0, 1], wifi_positions[0, 0]
                            wifi_xy = np.array([latlon_to_xy(pos[1], pos[0], origin_lat, origin_lon) 
                                              for pos in wifi_positions])
                            wifi_positions = np.column_stack((wifi_xy, wifi_positions[:, 2]))
                
        except Exception as e:
            print(f"Error in WiFi fingerprinting: {e}")
    
    # Step 3: Kalman filtering fusion
    if wifi_positions is not None and len(wifi_positions) > 0:
        print("Applying Kalman filter fusion...")
        fused_positions = kalman_filter_3d(stride_lengths, thetas, wifi_positions, q, r)
    else:
        print("Using PDR only (no WiFi data)")
        # Convert PDR positions to 3D (assuming ground level)
        fused_positions = np.column_stack((positions[1:, :], np.zeros(len(positions) - 1)))
    
    # Step 4: Plotting
    if plot and len(fused_positions) > 0:
        fig = plt.figure(figsize=(15, 5))
        
        # 2D trajectory
        ax1 = fig.add_subplot(131)
        ax1.plot(positions[:, 0], positions[:, 1], 'b-o', label='PDR', markersize=4)
        if wifi_positions is not None:
            ax1.plot(wifi_positions[:, 0], wifi_positions[:, 1], 'r-s', label='WiFi', markersize=4)
        ax1.plot(fused_positions[:, 0], fused_positions[:, 1], 'g-^', label='Fused', markersize=4)
        ax1.set_xlabel('East (m)')
        ax1.set_ylabel('North (m)')
        ax1.set_title('2D Trajectory Comparison')
        ax1.legend()
        ax1.grid(True)
        ax1.axis('equal')
        
        # 3D trajectory
        ax2 = fig.add_subplot(132, projection='3d')
        ax2.plot(fused_positions[:, 0], fused_positions[:, 1], fused_positions[:, 2], 
                'g-o', label='Fused 3D', markersize=4)
        ax2.set_xlabel('East (m)')
        ax2.set_ylabel('North (m)')
        ax2.set_zlabel('Height (m)')
        ax2.set_title('3D Fused Trajectory')
        
        # Step lengths
        ax3 = fig.add_subplot(133)
        ax3.plot(stride_lengths, 'b-o', markersize=4)
        ax3.set_xlabel('Step Number')
        ax3.set_ylabel('Stride Length (m)')
        ax3.set_title('Step Lengths')
        ax3.grid(True)
        
        plt.tight_layout()
        plt.show()
    
    return fused_positions, metadata

def batch_process_recordings(data_folder, wifi_training_file=None, room_filter=None):
    """
    Process all JSON recordings in a folder
    """
    results = {}
    
    for door_folder in os.listdir(data_folder):
        if door_folder.startswith('door_'):
            room_num = door_folder.split('_')[1]
            if room_filter and room_num != room_filter:
                continue
                
            door_path = os.path.join(data_folder, door_folder)
            if not os.path.isdir(door_path):
                continue
                
            print(f"\n=== Processing room {room_num} ===")
            results[room_num] = []
            
            for filename in os.listdir(door_path):
                if filename.endswith('.json'):
                    file_path = os.path.join(door_path, filename)
                    try:
                        positions, metadata = integrated_positioning_system(
                            file_path, wifi_training_file, plot=False
                        )
                        
                        if positions is not None and len(positions) > 0:
                            results[room_num].append({
                                'filename': filename,
                                'positions': positions,
                                'metadata': metadata
                            })
                    except Exception as e:
                        print(f"Error processing {filename}: {e}")
    
    return results