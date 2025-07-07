import json
import os
from datetime import datetime
import numpy as np

def aggregate_axis(data_list, axes):
    agg = {}
    for axis in axes:
        values = [d.get(axis, 0) for d in data_list if isinstance(d, dict)]
        agg[f'mean_{axis}'] = float(np.mean(values)) if values else 0.0
        agg[f'std_{axis}']  = float(np.std(values))  if values else 0.0
    return agg

def collect_sensor_data(data):
    try:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        room = data.get("room", "unknown")

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # 1️⃣ Save raw in data/recordings/door_<room>/
        raw_dir = os.path.join(project_root, 'data','recordings', f'door_{room}')
        os.makedirs(raw_dir, exist_ok=True)
        raw_path = os.path.join(raw_dir, f'recording_{ts}.json')
        with open(raw_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 2️⃣ Aggregate and write JSON array to data/sensor_data.json
        aggregated = {
            "room": room,
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "client_ip": data.get("client_ip"),
        }
        if "accelerometer" in data:
            aggregated["accelerometer"] = aggregate_axis(data["accelerometer"], ['x','y','z'])
        if "gyroscope" in data:
            aggregated["gyroscope"]     = aggregate_axis(data["gyroscope"], ['alpha','beta','gamma'])
        if "magnetometer" in data:
            aggregated["magnetometer"]  = aggregate_axis(data["magnetometer"], ['x','y','z'])
        if "barometer" in data:
            aggregated["barometer"]     = aggregate_axis(data["barometer"], ['pressure'])
        if "wifi" in data:
            aggregated["wifi"] = data["wifi"]
        if "gps" in data:
            aggregated["gps"]  = data["gps"]

        json_path = os.path.join(project_root, 'data', 'sensor_data.json')
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)
                if not isinstance(existing, list):
                    existing = []
        except (FileNotFoundError, json.JSONDecodeError):
            existing = []
        existing.append(aggregated)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:
        print(f"❌ Failed to collect sensor data: {e}")
        return False