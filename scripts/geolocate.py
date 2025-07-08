import json
import math
import os
from config import config

BASELINE_DIR = os.path.join(config.get_project_root(), 'data', 'sensor_data')
LIVE_FILE    = os.path.join(config.get_project_root(), 'data', 'sensor_data.json')

def load_baseline():
    """Charge tous les fichiers room_XXX.json et retourne dict {room: [entries]}."""
    baseline = {}
    for fname in os.listdir(BASELINE_DIR):
        if not fname.startswith('room_') or not fname.endswith('.json'):
            continue
        room = fname[len('room_'):-len('.json')]
        with open(os.path.join(BASELINE_DIR, fname), 'r', encoding='utf-8') as f:
            baseline[room] = json.load(f)
    return baseline


def load_latest_live():
    """
    Retourne la dernière entrée depuis sensor_data.json, ou None si pas de données.
    """
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
    for sensor in ('accelerometer', 'gyroscope', 'magnetometer', 'barometer'):
        val = entry.get(sensor)
        if isinstance(val, dict):
            for k, v in val.items():
                feat[f"{sensor}_{k}"] = v
        else:
            # skip non-dict sensor data
            continue
    return feat


def predict_position(k=3):
    """
    Prédit la position basée sur la dernière mesure live.
    Retourne une position estimée (longitude, latitude, étage).
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

    # Calcul des distances
    distances = []
    for room, entries in baseline.items():
        for e in entries:
            e_feat = aggregate_entry(e)
            common_keys = set(live_feat) & set(e_feat)
            if not common_keys:
                continue
            a = {k: live_feat[k] for k in common_keys}
            b = {k: e_feat[k] for k in common_keys}
            distances.append((room, euclidean(a, b), e.get('gps', None)))

    if not distances:
        raise RuntimeError("No baseline data available for prediction")

    # k plus proches voisins
    distances.sort(key=lambda x: x[1])
    topk = distances[:k]

    # Calculer la position moyenne des k plus proches voisins
    total_weight = sum(1/d for _, d, _ in topk)
    weighted_sum_x = 0.0
    weighted_sum_y = 0.0
    weighted_sum_z = 0.0

    for room, d, gps in topk:
        if gps:
            weight = 1/d if d > 0 else 1.0
            weighted_sum_x += gps['longitude'] * weight
            weighted_sum_y += gps['latitude'] * weight
            weighted_sum_z += gps['floor'] * weight

    if total_weight > 0:
        avg_x = weighted_sum_x / total_weight
        avg_y = weighted_sum_y / total_weight
        avg_z = weighted_sum_z / total_weight
    else:
        # Si aucun voisin n'a de position GPS, utiliser une position par défaut pour la salle prédite
        votes = {}
        for room, d, _ in topk:
            votes[room] = votes.get(room, 0) + 1
        best_room = sorted(votes.items(), key=lambda x: -x[1])[0][0]
        # Ici, nous aurions besoin d'une table de correspondance entre les salles et leurs positions
        avg_x, avg_y, avg_z = get_room_position(best_room)  # Fonction à implémenter

    return (avg_x, avg_y, avg_z), topk

def get_room_position(room):
    """
    Retourne la position par défaut pour une salle donnée.
    À implémenter avec les vraies coordonnées des salles.
    """
    # Exemple de données fictives
    room_positions = {
        '201': (10.0, 20.0, 1),
        '202': (10.0, 25.0, 1),
        '203': (15.0, 20.0, 1),
        # Ajouter d'autres salles...
    }
    return room_positions.get(room, (0.0, 0.0, 0))


if __name__ == '__main__':
    position, neighbors = predict_position()
    print(f"Predicted position: {position}, neighbors: {neighbors}")
