"""This module provides functions to handle sensor data extraction, reading, and processing.
It includes functions to extract room information, list sensor files, read sensor CSV files,
calculate statistics, merge sensor data, and add geographical information to the data.
"""

import numpy as np
import pandas as pd
from pathlib import Path

from services.utils import get_logger, get_room_position
import config

logger = get_logger(__name__)


def extract_room(folder_name: str) -> str:
    """Extract the room number from the folder name (ex: '2-1_something' -> '2-01')"""
    base = folder_name.split('_', 1)[0]
    parts = base.split('-')
    room = f"{parts[0]}-{parts[1].zfill(2)}" if len(parts) >= 2 else base
    logger.debug(f"Extracted room '{room}' from folder '{folder_name}'")
    return room


def list_sensor_files(folder: Path) -> list[Path]:
    """List valid sensor files in a folder."""
    files: list[Path] = []
    for f in folder.glob("*.csv"):
        key = f.stem.lower().replace('_0', '').replace(config.UNCALIBRATED_SUFFIX, '')
        if key in config.SENSOR_MAPPING:
            files.append(f)
            logger.debug(f"Sensor file matched: {f.name} as {key}")
        else:
            logger.warning(f"Ignoring unrecognized sensor file: {f.name}")
    return files


def read_sensor_csv(file: Path, room: str) -> pd.DataFrame | None:
    """Read and standardize a sensor CSV for the given room."""
    df: pd.DataFrame | None = None
    for enc in ('utf-8', 'latin-1', 'cp1252'):
        try:
            df = pd.read_csv(file, encoding=enc, engine='python', on_bad_lines='skip')
            logger.debug(f"Loaded {file.name} with encoding {enc}")
            break
        except Exception:
            continue
    if df is None or df.empty:
        logger.warning(f"Empty or unreadable file: {file.name}")
        return None

    df.columns = df.columns.str.strip()
    name = file.stem.lower()
    unc = name.endswith(config.UNCALIBRATED_SUFFIX)
    key = name.replace('_0', '').replace(config.UNCALIBRATED_SUFFIX, '')
    sensor = config.SENSOR_MAPPING.get(key)
    if not sensor:
        logger.warning(f"Unknown sensor key '{key}' in file {file.name}")
        return None

    df['sensor_type'] = sensor + (config.UNCALIBRATED_SUFFIX if unc else '')
    df['room'] = room
    df['source_file'] = file.name

    # Timestamp
    if 'seconds_elapsed' in df.columns:
        df['timestamp'] = pd.to_numeric(df['seconds_elapsed'], errors='coerce')
    elif 'time' in df.columns:
        df['timestamp'] = pd.to_numeric(df['time'], errors='coerce')
    elif 'timestamp' in df.columns:
        df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
    else:
        logger.error(f"No time column in {file.name}")
        return None

    # Numeric conversion
    numeric_cols = ['x','y','z','pressure','relativeAltitude','alpha','beta','gamma']
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    return df


def calculate_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate aggregated stats (mean, std, percentiles) by sensor."""
    records: list[dict] = []
    for sensor in df['sensor_type'].unique():
        sub = df[df['sensor_type'] == sensor]
        numeric = [c for c in sub.select_dtypes(include='number').columns if c not in ['timestamp','room']]
        if not numeric:
            continue
        desc = sub[numeric].describe(percentiles=[.25, .5, .75])
        base = {'sensor_type': sensor, 'room': sub['room'].iat[0], 'data_points': len(sub)}
        for col in numeric:
            base[f"{col}_mean"] = desc.at['mean', col]
            base[f"{col}_std"]  = desc.at['std', col]
            base[f"{col}_min"]  = desc.at['min', col]
            base[f"{col}_max"]  = desc.at['max', col]
            for pct,label in [('25%','25th'),('50%','50th'),('75%','75th')]:
                base[f"{col}_{label}"] = desc.at[pct, col] if pct in desc.index else None
        records.append(base)
    return pd.DataFrame(records)


def merge_sensor_data(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    """Merge and synchronize timestamped data from multiple sensors."""
    prepared: list[pd.DataFrame] = []
    for df in dfs:
        if df is None or df.empty:
            continue
        sensor = df['sensor_type'].iat[0]
        if 'timestamp' not in df:
            logger.warning(f"Skipping {sensor}: no timestamp")
            continue
        # determine prefix
        if sensor.startswith('accelerometer'):
            pref, mod = 'ACCE','ACCE_MOD'
        elif sensor.startswith('gyroscope'):
            pref, mod = 'GYRO','GYRO_MOD'
        elif sensor.startswith('magnetometer'):
            pref, mod = 'MAGN','MAGN_MOD'
        else:
            logger.debug(f"Ignoring sensor type {sensor}")
            continue
        cols = ['x','y','z']
        if not all(c in df for c in cols):
            logger.warning(f"Missing xyz for {sensor}")
            continue
        tmp = df[['timestamp']+cols].dropna().set_index('timestamp')
        tmp = tmp.rename(columns={ 'x':f'{pref}_X','y':f'{pref}_Y','z':f'{pref}_Z' })
        tmp[mod] = (tmp[f'{pref}_X']**2 + tmp[f'{pref}_Y']**2 + tmp[f'{pref}_Z']**2)**0.5
        prepared.append(tmp)
    if not prepared:
        logger.error("No valid sensor data to merge.")
        return pd.DataFrame()
    merged = prepared[0]
    for part in prepared[1:]:
        merged = merged.join(part, how='outer')
    merged = merged.sort_index().interpolate(method='index').ffill().bfill().reset_index()
    # select columns
    expected = ['timestamp','ACCE_X','ACCE_Y','ACCE_Z','ACCE_MOD',
                'GYRO_X','GYRO_Y','GYRO_Z','GYRO_MOD',
                'MAGN_X','MAGN_Y','MAGN_Z','MAGN_MOD']
    cols = [c for c in expected if c in merged]
    return merged[cols]


def add_room_geo(df: pd.DataFrame, room: str) -> pd.DataFrame:
    """Add long, lat, POSI_X, POSI_Y at the beginning of the DataFrame."""
    if df is None or df.empty:
        return df
    lon, lat = get_room_position(room)
    df.insert(1, 'long', lon)
    df.insert(2, 'lat', lat)
    df.insert(3, 'POSI_X', 0.0)
    df.insert(4, 'POSI_Y', 0.0)
    return df