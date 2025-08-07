import json
import logging
from pathlib import Path
from datetime import datetime, timezone 
from typing import List, Any, Dict
import pandas as pd
import csv
import config

# =============================================================================
# 1) LOGGING
# =============================================================================
def get_logger(name: str=__name__, verbose: bool=False) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S"
    )
    return logging.getLogger(name)

logger = get_logger(verbose=True)

# =============================================================================
# 2) SAFE I/O (CSV & JSON)
# =============================================================================
def read_csv_safe(path: Path, **kwargs) -> pd.DataFrame:
    try:
        return pd.read_csv(path, **kwargs)
    except Exception as e:
        logging.warning(f"read_csv_safe {path.name}: {e}")
        return pd.DataFrame()

def write_csv_safe(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)

def read_json_safe(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return []

def write_json_safe(obj: Any, path: Path | str):
    """
    Write a JSON object to a file, ensuring the directory exists.
    """
    p = Path(path) if not isinstance(path, Path) else path
    p.parent.mkdir(parents=True, exist_ok=True)
    temp_path = p.with_suffix(p.suffix + ".tmp")
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    temp_path.rename(p)

# =============================================================================
# 3) DEFAULTS GENERATORS
# =============================================================================
def default_pdr_row() -> Dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat()+"Z",
        "POSI_X":    config.DEFAULT_POSXY[0],
        "POSI_Y":    config.DEFAULT_POSXY[1],
        "floor":     config.DEFAULT_FLOOR
    }

def default_fingerprint_row() -> Dict[str, int]:
    return {f"AP{i}": config.DEFAULT_RSSI for i in range(1, config.DEFAULT_AP_N+1)}

def default_qr_event(room: str,
                     lon: float | None = None,
                     lat: float | None = None) -> dict:
    """
    Create a default QR event with the current timestamp and room position.
    If lon or lat are None, use the default position from config.
    """
    if lon is None or lat is None:
        lon, lat = config.DEFAULT_POSXY

    return {
        "room": room,
        "timestamp": datetime.now(timezone.utc).isoformat()+"Z",
        "position": [lon, lat],
    }


# =============================================================================
# 4) CONCATENATE AND FILL
# =============================================================================
def concat_fill(dfs: List[pd.DataFrame]) -> pd.DataFrame:
    """Concatenate DataFrames, filling missing columns with NA."""
    if not dfs:
        return pd.DataFrame()
    all_cols = set().union(*(df.columns for df in dfs))
    for df in dfs:
        for c in all_cols - set(df.columns):
            df[c] = pd.NA
    return pd.concat(dfs, ignore_index=True)

# =============================================================================
# 5) ROOM POSITIONING
# =============================================================================

def load_room_positions(csv_file_path):
    """Load the room positions from a CSV file."""
    room_positions = {}
    try:
        with open(csv_file_path, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                room_positions[row['room']] = (float(row['position_x']), float(row['position_y']))
    except FileNotFoundError:
        print(f"⚠️ File {csv_file_path} not found")
    except Exception as e:
        print(f"⚠️ Error loading positions: {e}")
    return room_positions

# Cache for room positions
_room_positions_cache = None

def get_room_position(room_number: str) -> tuple[float, float]:
    """
    Return (longitude, latitude) for the requested room number,
    from data/room_positions.csv.
    """
    global _room_positions_cache
    if _room_positions_cache is None:
        project_root = Path(__file__).resolve().parent.parent
        csv_path = project_root / "data" / "room_positions.csv"
        
        if not csv_path.exists():
            logger.warning(f"[get_room_position] room_positions.csv not found: {csv_path}")
            logger.warning("               Using default coordinates (0.0, 0.0)")
            return (0.0, 0.0)

        logger.debug(f"[get_room_position] Loading {csv_path}")
        _room_positions_cache = load_room_positions(csv_path)
        logger.info(f"[get_room_position] {_room_positions_cache!r} positions loaded")

    if room_number not in _room_positions_cache:
        logger.warning(f"[get_room_position] Room '{room_number}' not found in cache")
        return (0.0, 0.0)
    
    coord = _room_positions_cache[room_number]
    logger.debug(f"[get_room_position] '{room_number}' -> {coord}")
    return coord

def get_qr_reset_position(qr_code):
    """Return the position of a room based on a QR code."""
    room_number = qr_code.split('_')[-1].replace('.png', '')
    return get_room_position(room_number)