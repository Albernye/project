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


def predict_room(k=3):
    """Prédit la salle basée sur la dernière mesure live."""
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
            distances.append((room, euclidean(a, b)))

    if not distances:
        raise RuntimeError("No baseline data available for prediction")

    # k plus proches voisins
    distances.sort(key=lambda x: x[1])
    topk = distances[:k]
    votes = {}
    for room_, d in topk:
        votes[room_] = votes.get(room_, 0) + 1

    # Sélection du meilleur
    best = sorted(votes.items(), key=lambda x: (-x[1], next(d for r, d in topk if r == x[0])))[0][0]
    return best, topk


if __name__ == '__main__':
    room, neighbors = predict_room()
    print(f"Predicted room: {room}, neighbors: {neighbors}")
