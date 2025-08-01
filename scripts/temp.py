import re
import sys
from pathlib import Path
import pandas as pd
from scripts.sensors import merge_sensor_data
from datetime import datetime, timezone
from scripts.utils import write_json_safe, cfg

# Usage: python scripts/convert_and_merge.py <input_txt> <output_csv>
RAW_LOG = Path("data/logfile_2025_07_22_16_07_24.txt")  # e.g. data/logfile_2025_07_22_16_07_24.txt
OUT_CSV = Path("data/merged.csv")   # e.g. data/processed/merged.csv

# 1) Initialize containers for each tag
fields_map = { 'ACCE':'accelerometer', 'GYRO':'gyroscope', 'MAGN':'magnetometer',
               'AHRS':'orientation', 'POSI':'posi' }
data = { tag: [] for tag in fields_map }

# Regex to split tag;app_ts;sensor_ts;fields...
line_re = re.compile(r'^(?P<tag>\w+);(?P<app_ts>[\d\.]+);(?P<sensor_ts>[\d\.]+);(?P<fields>.*)$')

with RAW_LOG.open() as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('%'):
            continue
        m = line_re.match(line)
        if not m:
            continue

        tag = m.group('tag')
        if tag not in fields_map:
            continue
        try:
            sensor_ts = float(m.group('sensor_ts'))
        except ValueError:
            continue
        fields = m.group('fields').split(';')

        # ACCE, GYRO, MAGN: expect at least x,y,z
        if tag in ('ACCE','GYRO','MAGN'):
            if len(fields) < 3:
                continue
            try:
                x,y,z = map(float, fields[0:3])
            except ValueError:
                continue
            data[tag].append({'timestamp': sensor_ts, 'x': x, 'y': y, 'z': z})

        # AHRS: orientation as Pitch, Roll, Yaw
        elif tag == 'AHRS':
            if len(fields) < 3:
                continue
            try:
                pitch, roll, yaw = map(float, fields[0:3])
            except ValueError:
                continue
            data['AHRS'].append({'timestamp': sensor_ts, 'x': pitch, 'y': roll, 'z': yaw})

        # POSI: ground truth reference
        elif tag == 'POSI':
            # fields: [counter, latitude, longitude, floor, building]
            if len(fields) < 4:
                continue
            try:
                lat = float(fields[1]); lon = float(fields[2]); floor = float(fields[3])
            except ValueError:
                continue
            # store as x=posi_x,y=posi_y,z=floor
            data['POSI'].append({'timestamp': sensor_ts, 'x': lon, 'y': lat, 'z': floor})

# 2) Build DataFrames for merge

dfs = []
for tag, rows in data.items():
    if not rows:
        continue
    df = pd.DataFrame(rows)
    # assign sensor_type matching scripts.sensors expectations
    df['sensor_type'] = fields_map[tag]
    dfs.append(df)

if not dfs:
    print("❌ No valid sensor data parsed.")
    sys.exit(1)

# 3) Merge on timestamp
merged = merge_sensor_data(dfs)

# 4) Write output CSV
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
merged.to_csv(OUT_CSV, index=False)
print(f"✅ merged.csv written to {OUT_CSV}")


POSI_LINES = [
   "POSI;3.9976;1;2.175568;41.406368;2.0;0",
   "POSI;6.2209;2;2.175853;41.406368;2.0;0",
   "POSI;11.6488;3;2.177411;41.406368;2.0;0",
   "POSI;16.7875;4;2.178838;41.406368;2.0;0",
   "POSI;21.4581;5;2.180352;41.406368;2.0;0",
   "POSI;26.4183;6;2.181820;41.406369;2.0;0",
   "POSI;31.2228;7;2.183336;41.406369;2.0;0",
   "POSI;40.2019;8;2.186315;41.406368;2.0;0",
   "POSI;44.9803;9;2.187797;41.406369;2.0;0",
   "POSI;49.7183;10;2.189231;41.406369;2.0;0",
   "POSI;54.1182;11;2.190744;41.406369;2.0;0",
   "POSI;58.8740;12;2.192236;41.406368;2.0;0",
   "POSI;63.1015;13;2.194291;41.406351;0;0",
   "POSI;64.6014;14;2.193380;41.406336;2.0;0",
   "POSI;68.8934;15;2.191907;41.406336;2.0;0",
   "POSI;73.2928;16;2.190453;41.406336;2.0;0",
   "POSI;77.6695;17;2.189007;41.406336;2.0;0",
   "POSI;99.7171;18;2.186124;41.406336;2.0;0",
   "POSI;107.4535;19;2.185429;41.406315;2.0;0",
   "POSI;109.6596;20;2.185429;41.406328;2.0;0",
   "POSI;116.0639;21;2.183629;41.406336;2.0;0",
   "POSI;120.1166;22;2.182259;41.406336;2.0;0",
   "POSI;124.1760;23;2.180889;41.406336;0;0",
   "POSI;128.3037;24;2.179417;41.406336;2.0;0",
   "POSI;132.7240;25;2.177903;41.406336;2.0;0"
]

def convert_posi_to_qr(posi_lines: list[str]) -> None:
    """
    Convertit les lignes POSI en events QR et écrit data/qr_events.json
    """
    events = []
    for lin in posi_lines:
        parts = lin.split(";")
        if parts[0] != "POSI" or len(parts) < 7:
            continue  # ignorer les lignes mal formées
        _, app_ts, counter, lon, lat, floor, _ = parts
        iso_ts = datetime.fromtimestamp(float(app_ts), timezone.utc).isoformat() + "Z"
        room = f"2-{int(counter):02d}"
        events.append({
            "type":      "qr",
            "timestamp": iso_ts,
            "position":  [float(lon), float(lat)],
            "floor":     int(float(floor)),
            "room":      room
        })

    write_json_safe(events, cfg.QR_EVENTS)
    print(f"{len(events)} QR events saved to {cfg.QR_EVENTS}")

def main():
    # → ton code existant qui lit, merge et écrit merged.csv
    merged = merge_sensor_data(dfs)
    merged.to_csv("data/merged.csv", index=False)
    print("✅ merged.csv written to data/merged.csv")

    # → puis, enchaîne sur la conversion QR :
    convert_posi_to_qr(POSI_LINES)

if __name__ == "__main__":
    main()