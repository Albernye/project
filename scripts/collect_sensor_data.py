import csv
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
        raw_path = os.path.join(raw_dir, f'recording_{ts}.csv')
        with open(raw_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Écrire l'en-tête
            writer.writerow(['sensor_type', 'x', 'y', 'z', 'timestamp', 'room', 'client_ip'])
            
            # Écrire les données brutes
            for sensor in ['accelerometer', 'gyroscope', 'magnetometer']:
                if sensor in data:
                    for entry in data[sensor]:
                        writer.writerow([
                            sensor,
                            entry.get('x', entry.get('alpha', 0.0)),
                            entry.get('y', entry.get('beta', 0.0)),
                            entry.get('z', entry.get('gamma', 0.0)),
                            ts,
                            room,
                            data.get("client_ip")
                        ])
            
            if 'barometer' in data:
                for entry in data['barometer']:
                    writer.writerow([
                        'barometer',
                        entry.get('pressure', 0.0),
                        '', '',  # Colonnes vides pour y,z
                        ts,
                        room,
                        data.get("client_ip")
                    ])

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

        csv_path = os.path.join(project_root, 'data', 'sensor_data.csv')
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        # Créer l'en-tête si le fichier n'existe pas
        header = ['room', 'timestamp', 'client_ip'] 
        header += [f'{sensor}_{stat}_{axis}' 
                 for sensor in ['accelerometer', 'gyroscope', 'magnetometer'] 
                 for stat in ['mean', 'std'] 
                 for axis in (['x','y','z'] if sensor != 'gyroscope' else ['alpha','beta','gamma'])]
        header += ['barometer_mean_pressure', 'barometer_std_pressure']
        
        # Écrire les données
        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=header)
            if f.tell() == 0:
                writer.writeheader()
            
            row = {
                'room': room,
                'timestamp': aggregated['timestamp'],
                'client_ip': aggregated.get("client_ip")
            }
            
            for sensor in ['accelerometer', 'gyroscope', 'magnetometer']:
                if sensor in aggregated:
                    for stat in ['mean', 'std']:
                        for axis in aggregated[sensor]:
                            if axis.startswith(f'{stat}_'):
                                row[axis] = aggregated[sensor][axis]
            
            if 'barometer' in aggregated:
                for stat in ['mean', 'std']:
                    row[f'barometer_{stat}_pressure'] = aggregated['barometer'].get(f'{stat}_pressure', 0.0)
            
            writer.writerow(row)

        return True

    except Exception as e:
        print(f"❌ Failed to collect sensor data: {e}")
        return False
