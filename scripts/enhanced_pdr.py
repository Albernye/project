import pandas as pd
import numpy as np
import csv
import pandas as pd
import warnings
import math
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, find_peaks
from scipy.linalg import expm
from datetime import datetime
import os
from collections import deque

class EnhancedPDR:
    """Enhanced Pedestrian Dead Reckoning with improved accuracy"""
    
    def __init__(self, sample_rate=50.0, step_threshold=0.4, max_threshold=2.0):
        self.sample_rate = sample_rate
        self.step_threshold = step_threshold
        self.max_threshold = max_threshold
        
        # Adaptive parameters
        self.gravity_estimate = 9.8
        self.gravity_alpha = 0.999  # Low-pass filter for gravity estimation
        
        # Step detection parameters
        self.min_step_interval = 0.3  # Minimum time between steps (seconds)
        self.max_step_interval = 2.0  # Maximum time between steps (seconds)
        
        # Stride length parameters
        self.base_stride_factor = 0.45  # Base Weinberg factor
        self.adaptive_stride = True
        self.user_height = 1.75  # Default height in meters
        
        # Heading correction parameters
        self.use_magnetometer = True
        self.heading_smoothing = 0.1
        
        # Position tracking
        self.position_history = deque(maxlen=100)
        self.velocity_history = deque(maxlen=10)
        
    def adaptive_filter_design(self, signal, sample_rate):
        """Design adaptive filter based on signal characteristics"""
        # Analyze signal frequency content
        fft = np.fft.fft(signal)
        freqs = np.fft.fftfreq(len(signal), 1/sample_rate)
        
        # Find dominant frequency
        dominant_freq = freqs[np.argmax(np.abs(fft[1:len(fft)//2])) + 1]
        
        # Adaptive cutoff frequency
        if abs(dominant_freq) > 0:
            cutoff = min(3.0, max(1.0, abs(dominant_freq) * 1.5))
        else:
            cutoff = 2.0
            
        return cutoff
    
    def enhanced_step_detection(self, magnitude, time, plot=False):
        """Enhanced step detection with adaptive thresholding and peak detection"""
        num_samples = len(magnitude)
        if num_samples < 10:
            return 0, [], np.zeros(num_samples)
        
        # Adaptive filtering
        cutoff_freq = self.adaptive_filter_design(magnitude, self.sample_rate)
        b, a = butter(4, cutoff_freq / (self.sample_rate / 2), btype='low')
        filtered_magnitude = filtfilt(b, a, magnitude)
        
        # Adaptive gravity estimation
        gravity_filtered = np.zeros_like(magnitude)
        gravity_filtered[0] = magnitude[0]
        
        for i in range(1, len(magnitude)):
            gravity_filtered[i] = (self.gravity_alpha * gravity_filtered[i-1] + 
                                 (1 - self.gravity_alpha) * magnitude[i])
        
        # Detrend signal
        detrended = filtered_magnitude - gravity_filtered
        
        # Adaptive thresholding based on signal statistics
        signal_std = np.std(detrended)
        adaptive_threshold = max(self.step_threshold, signal_std * 0.5)
        
        # Peak detection approach
        peaks, properties = find_peaks(
            detrended,
            height=adaptive_threshold,
            distance=int(self.min_step_interval * self.sample_rate),
            prominence=adaptive_threshold * 0.3
        )
        
        # Filter peaks based on temporal constraints
        valid_peaks = []
        if len(peaks) > 0:
            valid_peaks.append(peaks[0])
            
            for i in range(1, len(peaks)):
                time_diff = (peaks[i] - valid_peaks[-1]) / self.sample_rate
                if (self.min_step_interval <= time_diff <= self.max_step_interval):
                    valid_peaks.append(peaks[i])
        
        # Create step detection array
        step_detection = np.zeros(num_samples)
        step_times = []
        
        for peak in valid_peaks:
            if peak < num_samples:
                step_detection[peak] = 1
                step_times.append(time[peak])
        
        # Stance phase estimation
        stance_phase = np.zeros(num_samples)
        for peak in valid_peaks:
            start_idx = max(0, peak - 5)
            end_idx = min(num_samples, peak + 10)
            stance_phase[start_idx:end_idx] = 1
        
        if plot:
            plt.figure(figsize=(12, 8))
            plt.subplot(3, 1, 1)
            plt.plot(time, magnitude, 'r-', label='Raw |Acc|')
            plt.plot(time, filtered_magnitude, 'b-', label='Filtered |Acc|')
            plt.plot(time, gravity_filtered, 'g--', label='Gravity Estimate')
            plt.legend()
            plt.title('Accelerometer Processing')
            
            plt.subplot(3, 1, 2)
            plt.plot(time, detrended, 'c-', label='Detrended')
            plt.axhline(y=adaptive_threshold, color='r', linestyle='--', label=f'Threshold: {adaptive_threshold:.2f}')
            plt.axhline(y=-adaptive_threshold, color='r', linestyle='--')
            plt.legend()
            plt.title('Step Detection Signal')
            
            plt.subplot(3, 1, 3)
            plt.plot(time, step_detection, 'ro', markersize=8, label='Detected Steps')
            plt.plot(time, stance_phase, 'g-', alpha=0.3, label='Stance Phase')
            plt.legend()
            plt.title('Step Detection Results')
            plt.xlabel('Time (s)')
            
            plt.tight_layout()
            plt.show()
        
        return len(valid_peaks), valid_peaks, stance_phase
    
    def adaptive_stride_length(self, acc_magnitude, step_indices, user_height=None):
        """Calculate adaptive stride length using multiple methods"""
        if user_height is None:
            user_height = self.user_height
            
        stride_lengths = []
        
        for i, step_idx in enumerate(step_indices):
            # Method 1: Enhanced Weinberg
            window_start = max(0, step_idx - 20)
            window_end = min(len(acc_magnitude), step_idx + 20)
            
            acc_max = np.max(acc_magnitude[window_start:window_end])
            acc_min = np.min(acc_magnitude[window_start:window_end])
            
            # Enhanced Weinberg with height adaptation
            bounce = (acc_max - acc_min) ** 0.25
            height_factor = (user_height / 1.75) ** 0.5  # Normalize to average height
            weinberg_stride = bounce * self.base_stride_factor * height_factor
            
            # Method 2: Frequency-based estimation
            if i > 0:
                step_time = (step_idx - step_indices[i-1]) / self.sample_rate
                step_frequency = 1.0 / step_time if step_time > 0 else 2.0
                
                # Empirical relationship: stride_length = a * frequency + b
                freq_stride = max(0.3, min(1.2, 0.8 - 0.2 * step_frequency))
            else:
                freq_stride = weinberg_stride
            
            # Method 3: Acceleration variance-based
            acc_var = np.var(acc_magnitude[window_start:window_end])
            var_stride = max(0.4, min(1.0, 0.6 + acc_var * 0.1))
            
            # Weighted combination
            if self.adaptive_stride:
                weights = [0.5, 0.3, 0.2]  # Weinberg, frequency, variance
                combined_stride = (weights[0] * weinberg_stride + 
                                 weights[1] * freq_stride + 
                                 weights[2] * var_stride)
            else:
                combined_stride = weinberg_stride
            
            # Clamp to reasonable range
            stride_length = max(0.3, min(1.2, combined_stride))
            stride_lengths.append(stride_length)
        
        return stride_lengths
    
    def enhanced_heading_estimation(self, acc, gyr, mag, step_indices, time):
        """Enhanced heading estimation with magnetometer fusion"""
        num_samples = len(acc)
        headings = []
        
        # Initialize rotation matrix
        if len(acc) > 10:
            init_window = min(50, len(acc) // 10)
            acc_mean = np.mean(acc[:init_window], axis=0)
            
            # Initial orientation from accelerometer
            roll_init = np.arctan2(acc_mean[1], acc_mean[2])
            pitch_init = -np.arctan2(acc_mean[0], 
                                   np.sqrt(acc_mean[1]**2 + acc_mean[2]**2))
            yaw_init = 0.0
        else:
            roll_init = pitch_init = yaw_init = 0.0

        # Create initial rotation matrix
        rot_matrices = np.zeros((3, 3, num_samples))
        
        # Initial rotation matrix
        rot_z = np.array([[np.cos(yaw_init), -np.sin(yaw_init), 0],
                          [np.sin(yaw_init), np.cos(yaw_init), 0],
                          [0, 0, 1]])
        rot_y = np.array([[np.cos(pitch_init), 0, np.sin(pitch_init)],
                          [0, 1, 0],
                          [-np.sin(pitch_init), 0, np.cos(pitch_init)]])
        rot_x = np.array([[1, 0, 0],
                          [0, np.cos(roll_init), -np.sin(roll_init)],
                          [0, np.sin(roll_init), np.cos(roll_init)]])
        
        rot_matrices[:, :, 0] = rot_z @ rot_y @ rot_x
        
        # Propagate rotation using gyroscope
        dt = 1.0 / self.sample_rate
        
        for i in range(1, min(len(gyr), num_samples)):
            # Create skew-symmetric matrix from gyroscope data
            omega = gyr[i]  # [wx, wy, wz] or [alpha, beta, gamma]
            
            # Handle different gyroscope data formats
            if len(omega) >= 3:
                wx, wy, wz = omega[0], omega[1], omega[2]
            else:
                wx = wy = wz = 0.0
            
            skew_omega = np.array([[0, -wz, wy],
                                   [wz, 0, -wx],
                                   [-wy, wx, 0]])
            
            # Update rotation matrix
            rot_matrices[:, :, i] = rot_matrices[:, :, i-1] @ expm(skew_omega * dt)
            
            # Magnetometer correction (if available and enabled)
            if self.use_magnetometer and mag is not None and len(mag) > i:
                mag_reading = mag[i]
                if len(mag_reading) >= 3 and not all(v == 0 for v in mag_reading):
                    # Simple magnetometer heading correction
                    mag_heading = np.arctan2(mag_reading[1], mag_reading[0])
                    current_heading = np.arctan2(rot_matrices[1, 0, i], rot_matrices[0, 0, i])
                    
                    # Apply smoothing to magnetometer correction
                    heading_diff = mag_heading - current_heading
                    # Normalize angle difference
                    heading_diff = np.arctan2(np.sin(heading_diff), np.cos(heading_diff))
                    
                    # Apply correction with smoothing
                    correction_angle = heading_diff * self.heading_smoothing
                    correction_matrix = np.array([[np.cos(correction_angle), -np.sin(correction_angle), 0],
                                                  [np.sin(correction_angle), np.cos(correction_angle), 0],
                                                  [0, 0, 1]])
                    
                    rot_matrices[:, :, i] = correction_matrix @ rot_matrices[:, :, i]
        
        # Extract headings at step events
        for step_idx in step_indices:
            if step_idx < num_samples:
                heading = np.arctan2(rot_matrices[1, 0, step_idx], rot_matrices[0, 0, step_idx])
                headings.append(heading)
        
        return headings
    
    def calculate_positions(self, stride_lengths, headings, initial_position=(0, 0)):
        """Calculate positions from stride lengths and headings"""
        positions = [np.array(initial_position)]
        
        for i, (stride, heading) in enumerate(zip(stride_lengths, headings)):
            dx = stride * np.cos(heading)
            dy = stride * np.sin(heading)
            
            new_position = positions[-1] + np.array([dx, dy])
            positions.append(new_position)
            
            # Store in history for velocity estimation
            self.position_history.append(new_position.copy())
        
        return np.array(positions)
    
    def estimate_velocity(self, positions, time_steps):
        """Estimate velocity from position history"""
        if len(positions) < 2:
            return np.array([0.0, 0.0])
        
        # Calculate velocity from recent positions
        recent_positions = positions[-5:]  # Last 5 positions
        if len(recent_positions) >= 2:
            dt = np.mean(np.diff(time_steps[-len(recent_positions):]))
            if dt > 0:
                velocity = (recent_positions[-1] - recent_positions[0]) / (dt * (len(recent_positions) - 1))
                self.velocity_history.append(velocity)
                return velocity
        
        return np.array([0.0, 0.0])
    
    def process_json_data(self, json_data, plot=False, user_height=None):
        """Process JSON sensor data and return PDR results"""
        
        # Extract sensor data
        acc_data = json_data.get('accelerometer', [])
        gyr_data = json_data.get('gyroscope', [])
        mag_data = json_data.get('magnetometer', [])
        
        if not acc_data:
            raise ValueError("No accelerometer data found")
        
        # Convert to numpy arrays
        acc_array = np.array([[sample.get('x', 0), sample.get('y', 0), sample.get('z', 0)] 
                             for sample in acc_data])
        
        gyr_array = np.array([[sample.get('alpha', 0), sample.get('beta', 0), sample.get('gamma', 0)] 
                             for sample in gyr_data]) if gyr_data else np.zeros_like(acc_array)
        
        mag_array = np.array([[sample.get('x', 0), sample.get('y', 0), sample.get('z', 0)] 
                             for sample in mag_data]) if mag_data else None
        
        # Generate time array
        num_samples = len(acc_array)
        time_array = np.arange(num_samples) / self.sample_rate
        
        # Calculate accelerometer magnitude
        acc_magnitude = np.linalg.norm(acc_array, axis=1)
        
        # Enhanced step detection
        num_steps, step_indices, stance_phase = self.enhanced_step_detection(
            acc_magnitude, time_array, plot=plot
        )
        
        if num_steps == 0:
            return {
                'num_steps': 0,
                'positions': np.array([[0, 0]]),
                'headings': [],
                'stride_lengths': [],
                'confidence': 0.0,
                'metadata': {
                    'total_distance': 0.0,
                    'avg_stride': 0.0,
                    'duration': time_array[-1] if len(time_array) > 0 else 0.0
                }
            }
        
        # Calculate adaptive stride lengths
        stride_lengths = self.adaptive_stride_length(acc_magnitude, step_indices, user_height)
        
        # Enhanced heading estimation
        headings = self.enhanced_heading_estimation(acc_array, gyr_array, mag_array, step_indices, time_array)
        
        # Calculate positions
        positions = self.calculate_positions(stride_lengths, headings)
        
        # Calculate confidence based on consistency
        confidence = self.calculate_confidence(stride_lengths, headings, acc_magnitude, step_indices)
        
        # Metadata
        total_distance = np.sum(stride_lengths)
        avg_stride = np.mean(stride_lengths) if stride_lengths else 0.0
        duration = time_array[-1] if len(time_array) > 0 else 0.0
        
        return {
            'num_steps': num_steps,
            'positions': positions,
            'headings': headings,
            'stride_lengths': stride_lengths,
            'confidence': confidence,
            'metadata': {
                'total_distance': total_distance,
                'avg_stride': avg_stride,
                'duration': duration,
                'step_frequency': num_steps / duration if duration > 0 else 0.0,
                'stride_variance': np.var(stride_lengths) if stride_lengths else 0.0,
                'heading_stability': np.std(headings) if headings else 0.0
            }
        }
    
    def calculate_confidence(self, stride_lengths, headings, acc_magnitude, step_indices):
        """Calculate confidence score for PDR results"""
        if not stride_lengths or not headings:
            return 0.0
        
        # Stride consistency (lower variance = higher confidence)
        stride_consistency = 1.0 / (1.0 + np.var(stride_lengths))
        
        # Heading stability (lower variance = higher confidence)
        heading_stability = 1.0 / (1.0 + np.var(headings)) if len(headings) > 1 else 0.5
        
        # Step regularity (consistent timing = higher confidence)
        if len(step_indices) > 1:
            step_intervals = np.diff(step_indices) / self.sample_rate
            interval_consistency = 1.0 / (1.0 + np.var(step_intervals))
        else:
            interval_consistency = 0.5
        
        # Signal quality (good signal-to-noise ratio = higher confidence)
        signal_quality = min(1.0, np.std(acc_magnitude) / 2.0)
        
        # Combined confidence
        confidence = (stride_consistency * 0.3 + 
                     heading_stability * 0.3 + 
                     interval_consistency * 0.2 + 
                     signal_quality * 0.2)
        
        return min(1.0, confidence)

def enhanced_PDR_from_csv(csv_file_path, plot=True, user_height=None, sample_rate=50.0):
    """
    Enhanced PDR processing function compatible with CSV input
    """
    # Load CSV data
    df = pd.read_csv(csv_file_path)
    # Conversion vers le format attendu
    sensor_data = {
        'accelerometer': [],
        'gyroscope': [],
        'magnetometer': []
    }
    
    for _, row in df.iterrows():
        sensor_type = row['sensor_type']
        entry = {
            'x': row.get('x', row.get('alpha', 0.0)),
            'y': row.get('y', row.get('beta', 0.0)),
            'z': row.get('z', row.get('gamma', 0.0))
        }
        sensor_data[sensor_type].append(entry)
    
    # Create enhanced PDR instance
    pdr = EnhancedPDR(sample_rate=sample_rate)
    
    # Process data
    results = pdr.process_json_data(sensor_data, plot=plot, user_height=user_height)
    
    # Return in compatible format
    return (
        results['headings'],
        results['positions'],
        results['stride_lengths'],
        results['metadata'],
        None  # No state for compatibility
    )

def batch_process_enhanced(data_folder, room_filter=None, plot=False):
    """
    Batch process recordings with enhanced PDR
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
                
            print(f"\n=== Enhanced PDR processing for room {room_num} ===")
            results[room_num] = []
            
            for filename in os.listdir(door_path):
                if filename.endswith('.json'):
                    file_path = os.path.join(door_path, filename)
                    
                    try:
                        headings, positions, stride_lengths, metadata, _ = enhanced_PDR_from_csv(
                            file_path, plot=plot
                        )
                        
                        if positions is not None and len(positions) > 0:
                            results[room_num].append({
                                'filename': filename,
                                'positions': positions,
                                'headings': headings,
                                'stride_lengths': stride_lengths,
                                'metadata': metadata
                            })
                            
                            print(f"  ✅ {filename}: {metadata['num_steps']} steps, "
                                  f"{metadata['total_distance']:.2f}m total distance")
                    except Exception as e:
                        print(f"  ❌ Error processing {filename}: {e}")
    
    return results

if __name__ == '__main__':
    # Test with sample data
    sample_data = {
        'accelerometer': [
            {'x': 0.1, 'y': 0.2, 'z': 9.8},
            {'x': 0.2, 'y': 0.3, 'z': 9.7},
            # Add more sample data...
        ],
        'gyroscope': [
            {'alpha': 0.01, 'beta': 0.02, 'gamma': 0.01},
            {'alpha': 0.02, 'beta': 0.01, 'gamma': 0.02},
            # Add more sample data...
        ]
    }
    
    pdr = EnhancedPDR()
    try:
        results = pdr.process_json_data(sample_data, plot=False)
        print(f"Enhanced PDR Results:")
        print(f"  Steps detected: {results['num_steps']}")
        print(f"  Total distance: {results['metadata']['total_distance']:.2f}m")
        print(f"  Confidence: {results['confidence']:.2f}")
    except Exception as e:
        print(f"Error: {e}")
