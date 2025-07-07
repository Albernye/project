import pandas as pd
import numpy as np
import glob
import warnings
import math
import csv
import matplotlib.pyplot as plt
from scipy.signal import butter
import scipy.linalg
from sklearn.neighbors import KNeighborsRegressor 
from bisect import bisect_right
from scipy.signal import butter, filtfilt
from scipy.linalg import expm


def find_most_recent_index(timestamps, reference_time):
    # Find the position where reference_time would fit
    pos = bisect_right(timestamps, reference_time)

    # If pos is 0, it means no valid timestamp exists
    return pos - 1 if pos > 0 else None

def euclidean_distance_3d(lon1, lat1, z1, lon2, lat2, z2):
    """
    Calculate the Euclidean distance between two points in 3D space
    given their longitudes, latitudes in decimal degrees, and altitudes in meters.

    Returns the distance in meters.
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    
    # Earth radius in meters
    radius_earth = 6371000
    
    # Convert spherical coordinates to Cartesian coordinates
    x1 = radius_earth * math.cos(lat1) * math.cos(lon1)
    y1 = radius_earth * math.cos(lat1) * math.sin(lon1)
    z1 = z1  # altitude in meters
    
    x2 = radius_earth * math.cos(lat2) * math.cos(lon2)
    y2 = radius_earth * math.cos(lat2) * math.sin(lon2)
    z2 = z2  # altitude in meters
    
    # Calculate Euclidean distance in 3D
    distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)
    
    return distance


def kalman_filter_predict1(xk_1, Pk_1, A, Q):
    xk_pred = A @ xk_1 
    Pk_pred = A @ Pk_1 @ A.T + Q
    return xk_pred, Pk_pred

def kalman_filter_predict2(xk_1, Pk_1, A, B, u, Q):
    xk_pred = A @ xk_1 + B @ u
    Pk_pred = A @ Pk_1 @ A.T + Q
    return xk_pred, Pk_pred

def kalman_filter_update(xk_pred, Pk_pred, zk, H, R):
    Kk = Pk_pred @ H.T @ np.linalg.inv(H @ Pk_pred @ H.T + R)
    xk = xk_pred + Kk @ (zk - H @ xk_pred)
    Pk = (np.eye(len(Pk_pred)) - Kk @ H) @ Pk_pred
    return xk, Pk

def kalman_filter3d(stride_lengths, thetas, positions, q, r):
    # State vector [x, y, theta]. Initial state assumed to be [0, 0, 0].
    xk = np.array([0, 0, positions[0,0], 0])
    Pk = np.eye(4)
    
    # State transition matrix
    A = np.eye(4)
    
    # Measurement matrix
    H = np.array([
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 1, 0]
    ])
    
    # Process noise covariance matrix
    Q = np.eye(4)*q
    
    # Measurement noise covariance matrix
    R = np.eye(3)*r
    
    estimated_positions = []
    for k in range(len(positions)):
        # Control input
        L = stride_lengths[k]
        delta_theta = thetas[k]
        B = np.array([
            [np.cos(xk[2]), 0],
            [np.sin(xk[2]), 0],
            [0, 0],
            [0, 1]
        ])
        u = np.array([L, delta_theta])
        
        # Prediction step
        xk_pred, Pk_pred = kalman_filter_predict2(xk, Pk, A, B, u, Q)
        
        # Update step
        zk = positions[k]
        xk, Pk = kalman_filter_update(xk_pred, Pk_pred, zk, H, R)
        
        # Store estimated position
        estimated_positions.append(xk[:3])
    
    estimated_positions = np.array(estimated_positions)
    return estimated_positions

from scipy.signal import butter, filtfilt

def step_detection_accelerometer(magnitude, time, plot=True, fig_idx=1):
    fps=np.zeros((1,fp.shape[1]))
    XX=[]
    YY=[]
    ZZ=[]
    long=[]
    lat=[]
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
            idx = find_most_recent_index(timeFP,time[ii])
            fps=np.vstack((fps,fp[idx]))
            long.append(longFP[idx][0])
            lat.append(latFP[idx][0])
            XX.append(POSI_X[ii][0])
            YY.append(POSI_Y[ii][0])
            ZZ.append(ZIMU[ii])
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
    fps=fps[1:,:]
    
    return Num_steps, StanceBegins_idx, StancePhase, fps, XX, YY, ZZ, long, lat

def latlon_to_xy(latitude, longitude, origin_latitude, origin_longitude):
    
    # Radius of the Earth in meters
    R = 6371000
    
    # Convert degrees to radians
    lat_rad = math.radians(latitude)
    lon_rad = math.radians(longitude)
    origin_lat_rad = math.radians(origin_latitude)
    origin_lon_rad = math.radians(origin_longitude)
    
    # Calculate differences
    delta_lon = lon_rad - origin_lon_rad
    delta_lat = lat_rad - origin_lat_rad
    
    # Calculate x, y using the planar approximation
    x = delta_lon * math.cos(origin_lat_rad) * R
    y = delta_lat * R
    
    return x, y

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
        plt.plot(positions[0, 0], positions[0, 1], 'ys', markersize=8, markerfacecolor=[0, 0, 1])
        plt.plot(positions[-1, 0], positions[-1, 1], 'yo', markersize=8, markerfacecolor=[0, 0, 1])
        plt.title('SL + Theta: Positions of trajectories in the global coordinate frame (G)')
        plt.xlabel('East (m)')
        plt.ylabel('North (m)')
        plt.axis('equal')
        plt.grid(True)
        idx_fig += 1

        plt.show()

    return thetas, positions, stride_lengths


def KalmanFilter(IMUfile, FPfile, knntrainfile, q, r):
    testIMU=pd.read_csv(IMUfile, delimiter=';')
    testFP=pd.read_csv(FPfile, delimiter=';')

    Acc_Magn_temp = testIMU[['MOD_ACCE']].values.tolist()
    Gyr_Magn_temp = testIMU[['MOD_GYRO']].values.tolist()
    ACCE=testIMU[['ACCE_X','ACCE_Y','ACCE_Z']].values
    GYRO=testIMU[['GYRO_X','GYRO_Y','GYRO_X']].values
    time_temp = testIMU[['time']].values.tolist()
    POSI_X= testIMU[['POSI_X']].values.tolist()
    POSI_Y= testIMU[['POSI_Y']].values.tolist()
    longIMU=testIMU[['long']].values.tolist()
    latIMU=testIMU[['lat']].values.tolist()
    ZIMUt=testIMU[['Z']].values.tolist()


    longFP = testFP[['long']].values.tolist()
    latFP = testFP[['lat']].values.tolist()
    ZtFP=testFP[['Z']].values.tolist()
    timeFParr=testFP[['time']].values.tolist()
    fp=testFP.drop(columns=['time','long', 'lat','Z']).values
    timeFP=[]
    ZFP=[]
    for i in range(len(timeFParr)):
        timeFP.append(timeFParr[i][0])
        ZFP.append(ZtFP[i][0])

    
    Acc_Magn=[]
    Gyr_Magn=[]
    ACCZ=[]
    time=[]

    for i in range(len(Acc_Magn_temp)):
        Acc_Magn.append(Acc_Magn_temp[i][0])
        Gyr_Magn.append(Gyr_Magn_temp[i][0])
        time.append(time_temp[i][0])
        ACCZ.append(ACCE[i,2])


    index_start=0
    X = testIMU[['POSI_X']].values
    while X[index_start] == 0:
        index_start += 1
    
    ACCE=ACCE[index_start:]
    GYRO=GYRO[index_start:]
    ACCZ=ACCZ[index_start:]
    time=time[index_start:]
    Acc_Magn=Acc_Magn[index_start:]
    Gyr_Magn=Gyr_Magn[index_start:]
    POSI_X= POSI_X[index_start:]
    POSI_Y= POSI_Y[index_start:]
    longIMU= longIMU[index_start:]
    latIMU = latIMU[index_start:]
    ZIMUt = ZIMUt[index_start:]

    origin_lat=latFP[0][0]
    origin_lon=longFP[0][0]

    ZIMU= []
    for i in range(len(ZIMUt)):
        ZIMU.append(ZIMUt[i][0])

    a, Steps, Stance, fps, XX, YY, ZZ, long, lat=step_detection_accelerometer(Acc_Magn, time, plot=False, fig_idx=1)
    
    thetas, positions, SL = weiberg_stride_length_heading_position(ACCE,GYRO,time,Steps,Stance,1,1)

    k = 3
        
    knn = KNeighborsRegressor(n_neighbors=k)

    train = pd.read_csv(knntrainfile, delimiter=';')
                   
    # Extract positions and RSSI values
    POSI_train = train[['long','lat','Z']].values
    RSSI_train = train.drop(columns=['long', 'lat','Z']).values

    knn.fit(RSSI_train, POSI_train)

    pred=knn.predict(fps)
    predxy=[latlon_to_xy(pred[i,1],pred[i,0],origin_lat,origin_lon) for i in range(len(pred))]
    predxy=np.hstack((np.array([predxy[i][0] for i in range(len(predxy))]).reshape(-1,1),np.array([predxy[i][1] for i in range(len(predxy))]).reshape(-1,1)))
    predxyz=np.hstack((predxy,np.array([pred[i,2] for i in range(len(pred))]).reshape(-1,1)))

    fusedkal=kalman_filter3d(SL, thetas, predxyz, q, r)

    # Create a 3D plot
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Plotting the data
    ax.plot(fusedkal[:,0], fusedkal[:,1], fusedkal[:,2], color='y', marker='o', linestyle='-', linewidth=2, markersize=5)
    # Labeling the axes

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')

    # Title
    ax.set_title('3D Plot of X, Y and Z')

    # Show plot
    plt.show()

