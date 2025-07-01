import os
import json
import csv
import statistics
from pathlib import Path
from config import config

# Paths
project_root = Path(config.get_project_root())
RAW_DATA_DIR = project_root / "data" / "sensor_data_raw"
OUTPUT_DIR   = project_root / "data" / "sensor_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Determine room from folder name, e.g. "2-1_08-36-19" -> "201"
def get_room_from_folder_name(folder_name: str) -> str:
    try:
        part = folder_name.split("_")[0]  # "2-1"
        floor, number = part.split("-")
        return f"{floor}{int(number):02d}"
    except Exception as e:
        print(f"⚠️ Could not derive room from '{folder_name}': {e}")
        return None

# Read CSV file into list of dicts
def read_csv_file(file_path: Path) -> list:
    try:
        with file_path.open(newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return [row for row in reader]
    except FileNotFoundError:
        return []

# Read metric with fallback to Uncalibrated variant
def read_metric(session_dir: Path, metric: str) -> list:
    primary = read_csv_file(session_dir / f"{metric}.csv")
    if primary:
        return primary
    fallback = read_csv_file(session_dir / f"{metric}Uncalibrated.csv")
    if fallback:
        print(f"ℹ️ Using uncalibrated data for {metric} in {session_dir.name}")
        return fallback
    return []

# Aggregate list of records by computing basic statistics for given keys
def summarize(records: list, keys: list) -> dict:
    stats = {}
    for k in keys:
        try:
            values = [float(r[k]) for r in records if r.get(k) not in (None, '')]
            if not values:
                continue
            stats[f"{k}_mean"] = statistics.mean(values)
            stats[f"{k}_std"]  = statistics.stdev(values) if len(values) > 1 else 0.0
            stats[f"{k}_min"]  = min(values)
            stats[f"{k}_max"]  = max(values)
        except Exception:
            continue
    return stats

# Dynamically detect numeric fields and summarize
# Exclude only 'time' field but keep 'seconds_elapsed'
def summarize_dynamic(records: list) -> dict:
    """
    Dynamically summarize numeric fields, excluding the exact 'time' column but keeping other numeric keys.
    """
    if not records:
        return {}
    keys = []
    for k, v in records[0].items():
        # exclude only the 'time' column
        if k.lower() == "time":
            continue
        try:
            float(v)
            keys.append(k)
        except Exception:
            continue
    return summarize(records, keys)

# Process a session folder, aggregate sensors, and append to room JSON

def process_folder(session_dir: Path):
    room = get_room_from_folder_name(session_dir.name)
    if not room:
        return

    entry = {"room": room, "session": session_dir.name}

    # Sensors to aggregate
    metrics = ["Magnetometer", "Barometer", "Accelerometer", "Gyroscope"]
    for metric in metrics:
        data = read_metric(session_dir, metric)
        if not data:
            entry[metric.lower()] = {}
        else:
            # choose keys: standard for known metrics, else dynamic
            standard_keys = {
                "Magnetometer": ["x","y","z"],
                "Barometer":    ["pressure"],
                "Accelerometer":["x","y","z"],
                "Gyroscope":    ["alpha","beta","gamma"]
            }
            keys = standard_keys.get(metric)
            if keys and all(k in data[0] for k in keys):
                entry[metric.lower()] = summarize(data, keys)
            else:
                entry[metric.lower()] = summarize_dynamic(data)

    # Write to per-room file
    output_file = OUTPUT_DIR / f"room_{room}.json"
    try:
        if output_file.exists():
            existing = json.loads(output_file.read_text(encoding='utf-8'))
        else:
            existing = []
        existing.append(entry)
        output_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"✅ Added aggregated data for room {room}")
    except Exception as e:
        print(f"❌ Error writing {output_file}: {e}")

# Main loop

def main():
    if not RAW_DATA_DIR.exists():
        print(f"❌ RAW_DATA_DIR does not exist: {RAW_DATA_DIR}")
        return
    for session in sorted(RAW_DATA_DIR.iterdir()):
        if session.is_dir():
            process_folder(session)

if __name__ == '__main__':
    main()
