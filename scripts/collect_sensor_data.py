import json
import os
import numpy as np
from datetime import datetime
from config import config
from .send_email import send_email

def get_data_file_path() -> str:
    """Retourne le chemin absolu de data/sensor_data.json dans project/."""
    data_dir = os.path.join(config.get_project_root(), 'data')
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, 'sensor_data.json')

def aggregate_axis(data_list, axes):
    agg = {}
    for axis in axes:
        values = [d.get(axis, 0) for d in data_list if isinstance(d, dict)]
        agg[f'mean_{axis}'] = float(np.mean(values)) if values else 0.0
        agg[f'std_{axis}'] = float(np.std(values)) if values else 0.0
    return agg

def collect_sensor_data(data):
    try:
        # Récupérer et agréger les capteurs
        aggregated_data = {
            "room": data.get("room"),
            "timestamp": datetime.utcnow().isoformat(),
            "client_ip": data.get("client_ip"),
        }

        if "accelerometer" in data:
            aggregated_data["accelerometer"] = aggregate_axis(data["accelerometer"], ['x', 'y', 'z'])

        if "gyroscope" in data:
            aggregated_data["gyroscope"] = aggregate_axis(data["gyroscope"], ['alpha', 'beta', 'gamma'])

        if "magnetometer" in data:
            aggregated_data["magnetometer"] = aggregate_axis(data["magnetometer"], ['x', 'y', 'z'])

        if "barometer" in data:
            aggregated_data["barometer"] = aggregate_axis(data["barometer"], ['pressure'])

        if "wifi" in data:
            # Option simple : conserver tel quel
            aggregated_data["wifi"] = data["wifi"]

        if "gps" in data:
            aggregated_data["gps"] = data["gps"]

        # Chemin du fichier
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(project_root, 'data')
        os.makedirs(data_dir, exist_ok=True)
        file_path = os.path.join(data_dir, 'sensor_data.json')

        # Sauvegarde en JSONL
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(aggregated_data) + '\n')

        return True

    except Exception as e:
        print(f"❌ Failed to collect sensor data: {e}")
        return False

def read_sensor_data() -> list:
    """
    Lit et retourne la liste des enregistrements JSONL.
    """
    file_path = get_data_file_path()
    if not os.path.exists(file_path):
        print("ℹ️  No data file found")
        return []

    entries = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"⚠️  Error on line {i}: {e}")
    print(f"📊 {len(entries)} entries read from {file_path}")
    return entries

def get_data_by_room(room: str) -> list:
    """
    Filtre les données pour une salle donnée.
    """
    return [d for d in read_sensor_data() if d.get('room') == str(room)]

if __name__ == "__main__":
    # Test rapide
    test = {
        "room": "201",
        "accelerometer": {"x":1,"y":2,"z":3},
        "gyroscope": {"alpha":0.1,"beta":0.2,"gamma":0.3}
    }
    collect_sensor_data(test)
    read_sensor_data()
