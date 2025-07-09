"""
Fonctions partagées et configuration des chemins
"""
import pandas as pd
from pathlib import Path
from datetime import datetime

# Chemins projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
STATS_DIR = PROJECT_ROOT / "data" / "stats"
RECORDINGS_DIR = PROJECT_ROOT / "data" / "recordings"

# Mapping capteurs et suffixe
SENSOR_MAPPING = { 'accelerometer':'accelerometer', 'gyroscope':'gyroscope', 'magnetometer':'magnetometer',
                   'barometer':'barometer', 'gravity':'gravity', 'orientation':'orientation',
                   'compass':'compass', 'pedometer':'pedometer', 'microphone':'microphone' }
UNCALIBRATED_SUFFIX = 'uncalibrated'

     
# Mapping capteurs et suffixe
def extract_room(folder_name: str) -> str:
    base = folder_name.split('_',1)[0]
    parts = base.split('-')
    return f"{parts[0]}-{parts[1].zfill(2)}" if len(parts)>=2 else base


def list_sensor_files(folder: Path):
    candidates = {f.stem.lower(): f for f in folder.glob("*.csv")}
    files = []
    for name,f in candidates.items():
        key = name.replace(UNCALIBRATED_SUFFIX,'')
        if key not in SENSOR_MAPPING: continue
        if not name.endswith(UNCALIBRATED_SUFFIX):
            unc = key+UNCALIBRATED_SUFFIX
            if unc in candidates and f.stat().st_size<50 and candidates[unc].stat().st_size>=50:
                continue
        files.append(f)
    return files


def read_sensor_csv(file: Path, room: str) -> pd.DataFrame:
    for enc in ('utf-8','latin-1','cp1252'):
        try: df = pd.read_csv(file, encoding=enc, engine='python', on_bad_lines='skip'); break
        except: continue
    else: return None
    if df.empty: return None
    df.columns = df.columns.str.strip().str.lower().str.replace('[^a-z0-9_]','_',regex=True)
    name,unc = file.stem.lower(), file.stem.lower().endswith(UNCALIBRATED_SUFFIX)
    key = name.replace(UNCALIBRATED_SUFFIX,'')
    sensor = SENSOR_MAPPING.get(key)
    if not sensor: return None
    df['sensor_type']=sensor+(UNCALIBRATED_SUFFIX if unc else '')
    df['room']=room; df['source_file']=file.name
    if 'timestamp' in df.columns: df['timestamp']=pd.to_datetime(df['timestamp'],errors='coerce')
    for c in ['x','y','z','alpha','beta','gamma','pressure','rssi']:
        if c in df.columns: df[c]=pd.to_numeric(df[c],errors='coerce')
    return df


def calculate_stats(df: pd.DataFrame) -> pd.DataFrame:
    stats = []
    for sensor in df['sensor_type'].unique():
        sub = df[df['sensor_type'] == sensor]
        numeric_cols = [c for c in sub.select_dtypes(include='number').columns if c != 'room']
        if not numeric_cols:
            continue
        desc = sub[numeric_cols].describe(percentiles=[.25, .5, .75])
        base = {
            'sensor_type': sensor,
            'room': sub['room'].iat[0],
            'data_points': len(sub)
        }
        for col in numeric_cols:
            # Statistics available: count, mean, std, min, 25%, 50%, 75%, max
            base[f"{col}_mean"] = desc.loc['mean', col]
            base[f"{col}_std"] = desc.loc['std', col]
            base[f"{col}_min"] = desc.loc['min', col]
            base[f"{col}_max"] = desc.loc['max', col]
            # Use string labels for percentiles
            for pct, label in [('25%', '25th'), ('50%', '50th'), ('75%', '75th')]:
                if pct in desc.index:
                    base[f"{col}_{label}"] = desc.loc[pct, col]
                else:
                    base[f"{col}_{label}"] = None
        stats.append(base)
    return pd.DataFrame(stats)
