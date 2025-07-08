import pandas as pd
import numpy as np
import json
import warnings
import math
import csv
import matplotlib.pyplot as plt
import scipy.linalg
from scipy.signal import butter, filtfilt
from scipy.linalg import expm
from datetime import datetime
import os

def step_detection_accelerometer(magnitude, time, plot=True, fig_idx=1):
    """
    Détection des pas basée sur l'accéléromètre
    """
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
        StancePhase[ii:ii + 10] = np.ones(10)  # Assume support phase is the 10 following samples

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
    
    return Num_steps, StanceBegins_idx, StancePhase

def weiberg_stride_length_heading_position(acc, gyr, time, step_event, stance_phase, ver, idx_fig):
    """
    Calcul des positions PDR basé sur l'algorithme de Weinberg
    """
    # Constants - Paramètre K à ajuster selon votre démarche
    K = 0.4  # Augmenté de 0.2 à 0.4 pour des pas plus longs (à calibrer)

    # Extracting data sizes and frequencies
    time_exp = time[-1] - time[0]
    print(f"Durée d'enregistrement: {time_exp:.2f} secondes")
    
    num_samples_acc = acc.shape[0]
    print(f"Nombre d'échantillons accéléromètre: {num_samples_acc}")
    freq_acc = np.ceil(num_samples_acc / time_exp)
    print(f"Fréquence accéléromètre: {freq_acc} Hz")

    num_samples_gyr = gyr.shape[0]
    freq_gyr = np.ceil(num_samples_gyr / time_exp)
    print(f"Fréquence gyroscope: {freq_gyr} Hz")

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
        if sample_step_event < len(m_acc):
            # Calculer sur une fenêtre autour du pas détecté
            window_start = max(0, sample_step_event - 20)
            window_end = min(len(m_acc), sample_step_event + 20)
            
            acc_max = np.max(m_acc[window_start:window_end])
            acc_min = np.min(m_acc[window_start:window_end])
            bounce = (acc_max - acc_min)**(1/4)
            stride_length = bounce * K
            stride_lengths.append(stride_length)
        else:
            stride_lengths.append(0.7)  # Longueur par défaut si échantillon invalide

    # Step 4: Heading direction (Thetas) after each step
    # Initialize rotation matrix at initial sample
    w = np.arange(0, min(int(np.ceil(5 * freq_acc)), len(acc)), dtype=int)  # Fenêtre réduite
    if len(w) > 0:
        acc_mean = np.mean(acc[w, :], axis=0)
        roll_ini = np.arctan2(acc_mean[1], acc_mean[2]) * 180 / np.pi
        pitch_ini = -np.arctan2(acc_mean[0], np.sqrt(acc_mean[1]**2 + acc_mean[2]**2)) * 180 / np.pi
        yaw_ini = 0
    else:
        roll_ini = pitch_ini = yaw_ini = 0

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
    for i in range(1, min(num_samples_gyr, num_samples_acc)):
        # Conversion des angles du gyroscope (alpha, beta, gamma) vers (wx, wy, wz)
        # Note: Adaptation selon votre format {"alpha": 1.0, "beta": 0.5, "gamma": -0.2}
        skew_gyros = np.array([[0, -gyr[i, 2], gyr[i, 1]],
                               [gyr[i, 2], 0, -gyr[i, 0]],
                               [-gyr[i, 1], gyr[i, 0], 0]])  # Skew-symmetric matrix
        
        # Vérifier que la fréquence est valide
        if freq_gyr > 0:
            rot_gs[:, :, i] = np.dot(rot_gs[:, :, i - 1], expm(skew_gyros / freq_gyr))

    # Calculate heading direction (Thetas)
    thetas = np.zeros(len(step_event))
    step_event_gyro = np.floor(np.array(step_event) * freq_gyr / freq_acc).astype(int)
    
    for k in range(len(step_event)):
        gyro_idx = min(step_event_gyro[k], num_samples_acc - 1)
        thetas[k] = np.arctan2(rot_gs[1, 0, gyro_idx], rot_gs[0, 0, gyro_idx])

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
        plt.figure(idx_fig)
        plt.plot(positions[:, 0], positions[:, 1], 'bo-', label='Positions PDR')
        plt.plot(positions[0, 0], positions[0, 1], 'gs', markersize=10, label='Départ')
        plt.plot(positions[-1, 0], positions[-1, 1], 'rs', markersize=10, label='Arrivée')
        plt.title(f'Tracé PDR - {len(step_event)} pas détectés')
        plt.xlabel('Est (m)')
        plt.ylabel('Nord (m)')
        plt.axis('equal')
        plt.grid(True)
        plt.legend()
        plt.show()

    return thetas, positions, stride_lengths

def load_json_recording(json_file_path):
    """
    Charge un fichier JSON d'enregistrement et extrait les données IMU
    """
    with open(json_file_path, 'r') as f:
        data = json.load(f)
    
    # Extraction des données accéléromètre
    acc_data = data.get('accelerometer', [])
    acc_array = np.array([[sample['x'], sample['y'], sample['z']] for sample in acc_data])
    
    # Extraction des données gyroscope
    gyr_data = data.get('gyroscope', [])
    # Conversion alpha, beta, gamma vers x, y, z
    gyr_array = np.array([[sample['alpha'], sample['beta'], sample['gamma']] for sample in gyr_data])
    
    # Génération des timestamps (si pas présents dans le JSON)
    num_samples = len(acc_data)
    if num_samples > 0:
        # Assumer une fréquence d'échantillonnage de 50 Hz (à ajuster selon vos capteurs)
        sample_rate = 50.0
        time_array = np.arange(num_samples) / sample_rate
    else:
        time_array = np.array([])
    
    return acc_array, gyr_array, time_array, data

def PDR_from_json(json_file_path, plot=True, K_parameter=0.4, incremental=False, previous_state=None):
    """
    Fonction PDR adaptée pour les fichiers JSON de votre projet
    Args:
        json_file_path: Chemin vers le fichier JSON d'enregistrement
        plot: Affichage des graphiques
        K_parameter: Paramètre de Weinberg à ajuster selon la démarche
        incremental: Si True, traite les données de manière incrémentielle
        previous_state: État précédent pour le traitement incrémentiel
    Returns:
        thetas: Directions des pas
        positions: Positions calculées par PDR
        stride_lengths: Longueurs des pas
        metadata: Métadonnées de l'enregistrement
        new_state: Nouveau état pour le traitement incrémentiel suivant
    """
    print(f"Traitement du fichier: {json_file_path}")

    # Chargement des données
    acc_array, gyr_array, time_array, raw_data = load_json_recording(json_file_path)

    if len(acc_array) == 0:
        print("Aucune donnée accéléromètre trouvée dans le fichier")
        return None, None, None, None, None

    if incremental and previous_state is not None:
        # Traitement incrémentiel
        pass  # À implémenter
    else:
        # Calcul de la magnitude de l'accéléromètre
        acc_magnitude = np.sqrt(acc_array[:, 0]**2 + acc_array[:, 1]**2 + acc_array[:, 2]**2)

        # Détection des pas
        num_steps, step_indices, stance_phase = step_detection_accelerometer(
            acc_magnitude, time_array, plot=plot, fig_idx=1
        )

        print(f"Nombre de pas détectés: {num_steps}")

        if num_steps == 0:
            print("Aucun pas détecté")
            return np.array([]), np.array([]), np.array([]), None, None

        # Calcul des positions PDR
        thetas, positions, stride_lengths = weiberg_stride_length_heading_position(
            acc_array, gyr_array, time_array, step_indices, stance_phase,
            ver=plot, idx_fig=2
        )

    # Métadonnées
    metadata = {
        'room': raw_data.get('room', 'unknown'),
        'num_steps': num_steps,
        'total_distance': np.sum(stride_lengths) if len(stride_lengths) > 0 else 0,
        'duration': time_array[-1] if len(time_array) > 0 else 0,
        'avg_step_length': np.mean(stride_lengths) if len(stride_lengths) > 0 else 0,
        'wifi_aps': len(raw_data.get('wifi', [])),
        'gps_available': 'gps' in raw_data and raw_data['gps'] is not None
    }

    print(f"Distance totale parcourue: {metadata['total_distance']:.2f} m")
    print(f"Longueur moyenne des pas: {metadata['avg_step_length']:.2f} m")

    new_state = {
        'last_position': positions[-1] if len(positions) > 0 else None,
        'last_time': time_array[-1] if len(time_array) > 0 else 0,
        # Ajouter d'autres éléments d'état nécessaires
    }

    return thetas, positions, stride_lengths, metadata, new_state

def batch_process_recordings(data_folder, room_filter=None):
    """
    Traite tous les enregistrements JSON d'un dossier

    Args:
        data_folder: Dossier contenant les enregistrements
        room_filter: Filtrer par numéro de salle (ex: "201")
    Returns:
        results: Dictionnaire avec les résultats par salle
    """
    results = {}
    
    # Parcourir tous les dossiers door_XXX
    for door_folder in os.listdir(data_folder):
        if door_folder.startswith('door_'):
            room_num = door_folder.split('_')[1]
            
            if room_filter and room_num != room_filter:
                continue
                
            door_path = os.path.join(data_folder, door_folder)
            if not os.path.isdir(door_path):
                continue
                
            print(f"\n=== Traitement de la salle {room_num} ===")
            results[room_num] = []
            
            # Traiter tous les fichiers JSON du dossier
            for filename in os.listdir(door_path):
                if filename.endswith('.json'):
                    file_path = os.path.join(door_path, filename)
                    
                    try:
                        thetas, positions, stride_lengths, metadata = PDR_from_json(
                            file_path, plot=False
                        )
                        
                        if positions is not None and len(positions) > 0:
                            results[room_num].append({
                                'filename': filename,
                                'positions': positions,
                                'thetas': thetas,
                                'stride_lengths': stride_lengths,
                                'metadata': metadata
                            })
                    except Exception as e:
                        print(f"Erreur lors du traitement de {filename}: {e}")
    
    return results
