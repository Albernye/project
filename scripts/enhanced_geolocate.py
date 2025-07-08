import json
import math
import os
import numpy as np
from datetime import datetime, timedelta
from collections import deque
from config import config

BASELINE_DIR = os.path.join(config.get_project_root(), 'data', 'sensor_data_aggregated')
LIVE_FILE = os.path.join(config.get_project_root(), 'data', 'sensor_data.json')

class KalmanFilter:
    """Simple 2D Kalman Filter for position tracking"""
    
    def __init__(self, process_noise=0.1, measurement_noise=1.0):
        # State: [x, y, vx, vy]
        self.state = np.array([0.0, 0.0, 0.0, 0.0])
        
        # State covariance matrix
        self.P = np.eye(4) * 100
        
        # Process noise
        self.Q = np.eye(4) * process_noise
        
        # Measurement noise
        self.R = np.eye(2) * measurement_noise
        
        # State transition matrix (constant velocity model)
        self.F = np.array([
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])
        
        # Measurement matrix (observe position only)
        self.H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ])
    
    def predict(self, dt=1.0):
        """Predict next state"""
        # Update state transition matrix with time step
        self.F[0, 2] = dt
        self.F[1, 3] = dt
        
        # Predict state
        self.state = self.F @ self.state
        
        # Predict covariance
        self.P = self.F @ self.P @ self.F.T + self.Q
        
        return self.state[:2]  # Return position only
    
    def update(self, measurement, measurement_noise=None):
        """Update with measurement"""
        if measurement_noise is not None:
            R = np.eye(2) * measurement_noise
        else:
            R = self.R
        
        # Innovation
        y = measurement - self.H @ self.state
        
        # Innovation covariance
        S = self.H @ self.P @ self.H.T + R
        
        # Kalman gain
        K = self.P @ self.H.T @ np.linalg.inv(S)
        
        # Update state
        self.state = self.state + K @ y
        
        # Update covariance
        self.P = (np.eye(4) - K @ self.H) @ self.P
        
        return self.state[:2]  # Return position only
    
    def get_position(self):
        """Get current position estimate"""
        return self.state[:2]
    
    def get_velocity(self):
        """Get current velocity estimate"""
        return self.state[2:]

class PositionFusion:
    """Enhanced position fusion with Kalman filtering and confidence weighting"""
    
    def __init__(self):
        self.kalman = KalmanFilter()
        self.position_history = deque(maxlen=50)  # Keep last 50 positions
        self.last_update_time = None
        self.wifi_confidence_threshold = 0.7
        self.pdr_confidence_threshold = 0.5
        
    def calculate_wifi_confidence(self, distances, wifi_data=None):
        """Calculate confidence score for WiFi fingerprinting result"""
        if not distances:
            return 0.0
        
        # Base confidence on distance spread
        min_dist = distances[0][1]
        max_dist = distances[-1][1] if len(distances) > 1 else min_dist
        
        # Lower spread = higher confidence
        spread = max_dist - min_dist
        spread_confidence = 1.0 / (1.0 + spread)
        
        # Confidence based on absolute distance
        distance_confidence = 1.0 / (1.0 + min_dist)
        
        # WiFi signal quality confidence
        wifi_confidence = 1.0
        if wifi_data:
            # Higher RSSI values (less negative) = better signal = higher confidence
            avg_rssi = np.mean([ap.get('rssi', -100) for ap in wifi_data])
            wifi_confidence = max(0.1, (avg_rssi + 100) / 50)  # Normalize -100 to -50 dBm
        
        # Combined confidence
        total_confidence = (spread_confidence * 0.4 + 
                          distance_confidence * 0.4 + 
                          wifi_confidence * 0.2)
        
        return min(1.0, total_confidence)
    
    def calculate_pdr_confidence(self, step_count, stride_variance, heading_stability):
        """Calculate confidence score for PDR result"""
        # More steps = higher confidence (up to a point)
        step_confidence = min(1.0, step_count / 10.0)
        
        # Lower stride variance = higher confidence
        stride_confidence = 1.0 / (1.0 + stride_variance)
        
        # More stable heading = higher confidence
        heading_confidence = max(0.1, 1.0 - heading_stability)
        
        return (step_confidence * 0.4 + 
                stride_confidence * 0.3 + 
                heading_confidence * 0.3)
    
    def detect_drift(self, pdr_position, wifi_position, pdr_confidence, wifi_confidence):
        """Enhanced drift detection with confidence weighting"""
        if pdr_position is None or wifi_position is None:
            return False, 0.0
        
        # Calculate Euclidean distance
        distance = np.linalg.norm(np.array(pdr_position) - np.array(wifi_position[:2]))
        
        # Adaptive threshold based on confidence
        base_threshold = 2.0  # meters
        confidence_factor = (pdr_confidence + wifi_confidence) / 2.0
        adaptive_threshold = base_threshold * (2.0 - confidence_factor)  # Lower confidence = higher threshold
        
        # Consider velocity for dynamic threshold
        velocity = np.linalg.norm(self.kalman.get_velocity())
        velocity_threshold = base_threshold + velocity * 0.5  # Higher velocity = higher threshold
        
        final_threshold = max(adaptive_threshold, velocity_threshold)
        
        drift_detected = distance > final_threshold
        
        return drift_detected, distance
    
    def fuse_positions(self, pdr_position, wifi_position, pdr_confidence, wifi_confidence):
        """Fuse PDR and WiFi positions with confidence weighting"""
        if pdr_position is None and wifi_position is None:
            return None
        
        if pdr_position is None:
            return wifi_position[:2]
        
        if wifi_position is None:
            return pdr_position
        
        # Normalize confidences
        total_confidence = pdr_confidence + wifi_confidence
        if total_confidence == 0:
            # Equal weighting if no confidence info
            pdr_weight = wifi_weight = 0.5
        else:
            pdr_weight = pdr_confidence / total_confidence
            wifi_weight = wifi_confidence / total_confidence
        
        # Weighted fusion
        fused_x = pdr_weight * pdr_position[0] + wifi_weight * wifi_position[0]
        fused_y = pdr_weight * pdr_position[1] + wifi_weight * wifi_position[1]
        
        return np.array([fused_x, fused_y])
    
    def temporal_smoothing(self, new_position):
        """Apply temporal smoothing to reduce noise"""
        if len(self.position_history) == 0:
            return new_position
        
        # Simple moving average with recent positions
        recent_positions = list(self.position_history)[-5:]  # Last 5 positions
        recent_positions.append(new_position)
        
        smoothed = np.mean(recent_positions, axis=0)
        return smoothed
    
    def update_position(self, pdr_position=None, wifi_position=None, 
                       pdr_confidence=0.5, wifi_confidence=0.5, 
                       force_wifi_correction=False):
        """Main position update function with enhanced fusion"""
        current_time = datetime.now()
        
        # Calculate time delta
        if self.last_update_time:
            dt = (current_time - self.last_update_time).total_seconds()
        else:
            dt = 1.0
        
        self.last_update_time = current_time
        
        # Predict next position using Kalman filter
        predicted_position = self.kalman.predict(dt)
        
        # Detect drift
        drift_detected = False
        drift_distance = 0.0
        
        if pdr_position is not None and wifi_position is not None:
            drift_detected, drift_distance = self.detect_drift(
                pdr_position, wifi_position, pdr_confidence, wifi_confidence
            )
        
        # Determine measurement and confidence
        if force_wifi_correction or (drift_detected and wifi_confidence > self.wifi_confidence_threshold):
            # Use WiFi position for correction
            measurement = wifi_position[:2]
            measurement_noise = 1.0 / max(0.1, wifi_confidence)
            source = "wifi_correction"
        elif pdr_position is not None and pdr_confidence > self.pdr_confidence_threshold:
            # Use PDR position
            measurement = pdr_position
            measurement_noise = 1.0 / max(0.1, pdr_confidence)
            source = "pdr"
        elif wifi_position is not None:
            # Fallback to WiFi
            measurement = wifi_position[:2]
            measurement_noise = 1.0 / max(0.1, wifi_confidence)
            source = "wifi_fallback"
        else:
            # No measurement available, use prediction
            measurement = predicted_position
            measurement_noise = 2.0
            source = "prediction"
        
        # Update Kalman filter
        filtered_position = self.kalman.update(measurement, measurement_noise)
        
        # Apply temporal smoothing
        smoothed_position = self.temporal_smoothing(filtered_position)
        
        # Store in history
        self.position_history.append(smoothed_position.copy())
        
        return {
            'position': smoothed_position,
            'drift_detected': drift_detected,
            'drift_distance': drift_distance,
            'source': source,
            'pdr_confidence': pdr_confidence,
            'wifi_confidence': wifi_confidence,
            'kalman_position': filtered_position,
            'predicted_position': predicted_position
        }

# Global fusion instance
position_fusion = PositionFusion()

def load_baseline():
    """Charge tous les fichiers room_XXX.json et retourne dict {room: [entries]}."""
    baseline = {}
    if not os.path.exists(BASELINE_DIR):
        return baseline
        
    for fname in os.listdir(BASELINE_DIR):
        if not fname.startswith('room_') or not fname.endswith('.json'):
            continue
        room = fname[len('room_'):-len('.json')]
        try:
            with open(os.path.join(BASELINE_DIR, fname), 'r', encoding='utf-8') as f:
                baseline[room] = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            continue
    return baseline

def load_latest_live():
    """Retourne la dernière entrée depuis sensor_data.json, ou None si pas de données."""
    if not os.path.exists(LIVE_FILE) or os.path.getsize(LIVE_FILE) == 0:
        return None
    try:
        with open(LIVE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, list) or not data:
            return None
        return data[-1]
    except json.JSONDecodeError:
        return None

def euclidean(a, b):
    """Distance Euclidienne entre deux dicts de mêmes clés numériques."""
    return math.sqrt(sum((a[k] - b[k])**2 for k in a.keys()))

def aggregate_entry(entry):
    """Transforme une entrée agrégée (stats) en vecteur de features plat."""
    feat = {}
    # Process IMU sensors
    for sensor in ('accelerometer', 'gyroscope', 'magnetometer', 'barometer'):
        val = entry.get(sensor)
        if isinstance(val, dict):
            for k, v in val.items():
                if isinstance(v, (int, float)):
                    feat[f"{sensor}_{k}"] = v

    # Process WiFi RSSI with device normalization
    if 'wifi' in entry:
        rssi_values = [ap.get('rssi', -100) for ap in entry['wifi'] if ap.get('ssid')]
        if rssi_values:
            avg_rssi = np.mean(rssi_values)
            # Normalize between device types using hyperbolic tangent
            feat['wifi_normalized'] = np.tanh((avg_rssi + 90) / 40)  # Maps -90dBm to ~0, -50dBm to ~1
            feat['wifi_ap_count'] = len(rssi_values)
    return feat

def enhanced_predict_position(k=5, use_wifi_weighting=True):
    """
    Version améliorée de la prédiction de position avec pondération WiFi
    """
    baseline = load_baseline()
    if not baseline:
        raise RuntimeError("No baseline data available for prediction")

    live = load_latest_live()
    if live is None:
        raise RuntimeError("No live sensor data available")

    # Ensure sensors exist
    if not isinstance(live, dict) or all(not live.get(s) for s in ['accelerometer','gyroscope','magnetometer','barometer']):
        raise RuntimeError("Live data missing required sensor measurements")

    live_feat = aggregate_entry(live)
    wifi_data = live.get('wifi', [])

    # Calcul des distances avec pondération WiFi améliorée
    distances = []
    for room, entries in baseline.items():
        for e in entries:
            e_feat = aggregate_entry(e)
            common_keys = set(live_feat) & set(e_feat)
            if not common_keys:
                continue
            
            # Distance des capteurs IMU
            a = {k: live_feat[k] for k in common_keys}
            b = {k: e_feat[k] for k in common_keys}
            imu_distance = euclidean(a, b)
            
            # Distance WiFi si disponible
            wifi_distance = 0.0
            wifi_weight = 0.0
            
            if use_wifi_weighting and wifi_data and e.get('wifi'):
                baseline_wifi = {ap['ssid']: ap['rssi'] for ap in e['wifi']}
                live_wifi = {ap['ssid']: ap['rssi'] for ap in wifi_data}
                
                # Calculer la distance WiFi pour les APs communs
                common_aps = set(baseline_wifi.keys()) & set(live_wifi.keys())
                if common_aps:
                    wifi_distances = []
                    for ap in common_aps:
                        wifi_distances.append(abs(baseline_wifi[ap] - live_wifi[ap]))
                    wifi_distance = np.mean(wifi_distances)
                    wifi_weight = len(common_aps) / max(len(baseline_wifi), len(live_wifi))
            
            # Distance combinée
            if wifi_weight > 0:
                combined_distance = (1 - wifi_weight) * imu_distance + wifi_weight * wifi_distance / 10.0
            else:
                combined_distance = imu_distance
            
            distances.append((room, combined_distance, e.get('gps', None), wifi_weight))

    if not distances:
        raise RuntimeError("No baseline data available for prediction")

    # k plus proches voisins
    distances.sort(key=lambda x: x[1])
    topk = distances[:k]

    # Calculer la position moyenne pondérée
    total_weight = 0.0
    weighted_sum_x = 0.0
    weighted_sum_y = 0.0
    weighted_sum_z = 0.0

    for room, d, gps, wifi_w in topk:
        if gps and 'longitude' in gps and 'latitude' in gps:
            # Poids basé sur l'inverse de la distance + bonus WiFi
            base_weight = 1.0 / (d + 0.1)
            wifi_bonus = 1.0 + wifi_w * 0.5  # Bonus jusqu'à 50% pour WiFi
            weight = base_weight * wifi_bonus
            
            total_weight += weight
            weighted_sum_x += gps['longitude'] * weight
            weighted_sum_y += gps['latitude'] * weight
            weighted_sum_z += gps.get('floor', 2) * weight

    if total_weight > 0:
        avg_x = weighted_sum_x / total_weight
        avg_y = weighted_sum_y / total_weight
        avg_z = weighted_sum_z / total_weight
    else:
        # Fallback: utiliser la salle la plus probable
        votes = {}
        for room, d, _, _ in topk:
            votes[room] = votes.get(room, 0) + 1
        best_room = sorted(votes.items(), key=lambda x: -x[1])[0][0]
        avg_x, avg_y, avg_z = get_room_position(best_room)

    # Calculer la confiance WiFi
    wifi_confidence = position_fusion.calculate_wifi_confidence(
        [(room, d) for room, d, _, _ in topk], wifi_data
    )

    return (avg_x, avg_y, avg_z), topk, wifi_confidence

def predict_position(k=3):
    """Fonction de compatibilité avec l'ancienne API"""
    position, neighbors, confidence = enhanced_predict_position(k)
    return position, neighbors

def predict_room(k=3):
    """Prédit la salle basée sur la dernière mesure live"""
    try:
        position, neighbors, confidence = enhanced_predict_position(k)
        
        # Voter pour la salle la plus probable
        votes = {}
        for room, distance, _, _ in neighbors:
            weight = 1.0 / (distance + 0.1)
            votes[room] = votes.get(room, 0) + weight
        
        if votes:
            best_room = sorted(votes.items(), key=lambda x: -x[1])[0][0]
            return best_room, neighbors
        else:
            raise RuntimeError("No room prediction possible")
            
    except Exception as e:
        raise RuntimeError(f"Room prediction failed: {e}")

def get_room_position(room):
    """
    Retourne la position par défaut pour une salle donnée.
    Coordonnées réelles du bâtiment UOC (à ajuster selon vos mesures)
    """
    # Coordonnées approximatives basées sur le plan d'étage
    room_positions = {
        '201': (2.1936, 41.4067, 2),
        '202': (2.1937, 41.4067, 2),
        '203': (2.1938, 41.4067, 2),
        '204': (2.1939, 41.4067, 2),
        '205': (2.1940, 41.4067, 2),
        '206': (2.1941, 41.4067, 2),
        '207': (2.1942, 41.4067, 2),
        '208': (2.1943, 41.4067, 2),
        '209': (2.1943, 41.4068, 2),
        '210': (2.1942, 41.4068, 2),
        '211': (2.1941, 41.4068, 2),
        '212': (2.1940, 41.4068, 2),
        '213': (2.1939, 41.4068, 2),
        '214': (2.1938, 41.4068, 2),
        '215': (2.1937, 41.4068, 2),
        '216': (2.1936, 41.4068, 2),
        '217': (2.1935, 41.4068, 2),
        '218': (2.1934, 41.4068, 2),
        '219': (2.1933, 41.4068, 2),
        '220': (2.1932, 41.4068, 2),
        '221': (2.1931, 41.4068, 2),
        '222': (2.1930, 41.4068, 2),
        '223': (2.1929, 41.4068, 2),
        '224': (2.1928, 41.4068, 2),
        '225': (2.1927, 41.4068, 2),
    }
    return room_positions.get(room, (2.1935, 41.4067, 2))

def update_position_with_fusion(pdr_position=None, wifi_position=None, 
                               pdr_metadata=None, force_wifi_correction=False):
    """
    Interface principale pour la fusion de positions avec le système amélioré
    """
    # Calculer les confidences
    pdr_confidence = 0.5
    if pdr_metadata:
        step_count = pdr_metadata.get('num_steps', 0)
        stride_lengths = pdr_metadata.get('stride_lengths', [])
        stride_variance = np.var(stride_lengths) if stride_lengths else 1.0
        heading_stability = 0.5  # À calculer depuis les données gyroscope
        
        pdr_confidence = position_fusion.calculate_pdr_confidence(
            step_count, stride_variance, heading_stability
        )
    
    wifi_confidence = 0.5
    if wifi_position:
        try:
            _, neighbors, wifi_confidence = enhanced_predict_position()
        except:
            wifi_confidence = 0.3
    
    # Mettre à jour la position avec fusion
    result = position_fusion.update_position(
        pdr_position=pdr_position,
        wifi_position=wifi_position,
        pdr_confidence=pdr_confidence,
        wifi_confidence=wifi_confidence,
        force_wifi_correction=force_wifi_correction
    )
    
    return result

if __name__ == '__main__':
    try:
        position, neighbors, confidence = enhanced_predict_position()
        print(f"Predicted position: {position}")
        print(f"WiFi confidence: {confidence:.2f}")
        print(f"Top neighbors: {neighbors[:3]}")
    except Exception as e:
        print(f"Error: {e}")
