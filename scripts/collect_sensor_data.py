import json
import os
from datetime import datetime
from config import config
from .send_email import send_email

def get_data_file_path() -> str:
    """Retourne le chemin absolu de data/sensor_data.json dans project/."""
    data_dir = os.path.join(config.get_project_root(), 'data')
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, 'sensor_data.json')

def collect_sensor_data(data: dict) -> bool:
    try:
        # Ensure timestamp & client_ip
        data.setdefault('timestamp', datetime.now().isoformat())
        data.setdefault('client_ip', None)

        file_path = get_data_file_path()

        # Load existing array, or start fresh if file missing/empty/invalid
        all_data = []
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    all_data = json.load(f)
                    if not isinstance(all_data, list):
                        raise ValueError("File does not contain a JSON array")
            except (json.JSONDecodeError, ValueError) as e:
                print(f"⚠️ Warning: could not parse existing JSON, starting new array ({e})")
                all_data = []

        # Append new record
        all_data.append(data)

        # Write back full JSON array
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)

        print(f"✅ Data saved as JSON array to: {file_path}")

        # Send email
        subject = f"IndoorNav – Data for room {data.get('room')}"
        body    = json.dumps(data, indent=2, ensure_ascii=False)
        send_email(subject, body)

        return True

    except Exception as e:
        print(f"❌ Error during saving: {e}")
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
