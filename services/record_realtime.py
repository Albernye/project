"""
Collect real-time sensor data from a specified folder, concatenate the data, and save it to a timestamped CSV file in the recordings directory.
This script is designed to be run as a standalone module.
"""
from pathlib import Path
from datetime import datetime, timezone
import logging
import pandas as pd

from services.sensors import extract_room, list_sensor_files, read_sensor_csv
from services.utils import get_logger
import config

logger = get_logger(__name__)

def record_realtime(folder: Path, client_ip: str = None) -> bool:
    """
    Read all CSV files from `folder`, concatenate them, and write a timestamped file to DATA/recordings.
    Args:
        folder: directory containing raw CSV files
        client_ip: client IP address (optional, for logging)
    Returns:
        True if a recording was created, False otherwise.
    """
    room = extract_room(folder.name)
    files = list_sensor_files(folder)
    logger.info(f"Detected {len(files)} sensor files in {folder.name}")

    dfs = []
    for f in files:
        df = read_sensor_csv(f, room)
        if df is not None and not df.empty:
            dfs.append(df)
        else:
            logger.warning(f"Invalid or empty file ignored: {f.name}")

    if not dfs:
        logger.warning(f"No valid data for room {room}")
        return False

    all_df = pd.concat(dfs, ignore_index=True)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    
    output_dir = config.RECORDINGS_DIR / f"door_{room}"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"recording_{timestamp}.csv"
    all_df.to_csv(output_file, index=False)
    logger.info(f"Recording created: {output_file}")
    return True