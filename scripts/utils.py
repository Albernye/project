"""
Fonctions partagées et configuration des chemins - Version adaptée aux formats réels
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timezone 
from typing import List, Any, Dict, Optional
import pandas as pd
import numpy as np
import csv

# Mapping capteurs et suffixe
SENSOR_MAPPING = { 
    'accelerometer': 'accelerometer', 
    'gyroscope': 'gyroscope', 
    'magnetometer': 'magnetometer',
    'barometer': 'barometer', 
    'gravity': 'gravity', 
    'orientation': 'orientation',
    'compass': 'compass', 
    'pedometer': 'pedometer', 
    'microphone': 'microphone' 
}
UNCALIBRATED_SUFFIX = 'uncalibrated'

# =============================================================================
# 1) CONFIGURATION CENTRALISÉE
# =============================================================================
class Config:
    BASE_DIR       = Path(__file__).resolve().parent.parent
    DATA_DIR       = BASE_DIR / 'data'
    RAW_DIR        = DATA_DIR / 'raw'
    PROCESSED_DIR  = DATA_DIR / 'processed'
    STATS_DIR      = DATA_DIR / 'stats'
    RECORDINGS_DIR = DATA_DIR / 'recordings'
    PDR_TRACE      = DATA_DIR / 'pdr_traces' / 'current.csv'
    PDR_COLUMNS    = ('timestamp', 'POSI_X', 'POSI_Y', 'floor')
    FP_CURRENT     = RECORDINGS_DIR / 'current_fingerprints.csv'
    QR_EVENTS      = DATA_DIR / 'qr_events.json'
    ROOM_POS_CSV   = DATA_DIR / 'room_positions.csv'
    
    MIN_ROWS       = 10
    ROOM_PREFIX    = "2-"
    GLOBAL_KNN     = "knn_train.csv"
    
    DEFAULT_FLOOR  = 2
    DEFAULT_POSXY  = (0.0, 0.0)
    DEFAULT_RSSI   = -80
    DEFAULT_AP_N   = 5
    USE_SIMULATED_IMU = True
    SIM_DURATION      = 10.0
    SIM_FS            = 100.0

cfg = Config()

logger = logging.getLogger(__name__)

# =============================================================================
# 2) LOGGING
# =============================================================================
def get_logger(name: str=__name__, verbose: bool=False) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S"
    )
    return logging.getLogger(name)


# =============================================================================
# 3) SAFE I/O (CSV & JSON)
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
    Écrit un objet JSON de façon atomique en s'assurant que le dossier existe.
    """
    p = Path(path) if not isinstance(path, Path) else path
    p.parent.mkdir(parents=True, exist_ok=True)
    temp_path = p.with_suffix(p.suffix + ".tmp")
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    temp_path.rename(p)

# =============================================================================
# 4) DEFAULTS GENERATORS
# =============================================================================
def default_pdr_row() -> Dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat()+"Z",
        "POSI_X":    cfg.DEFAULT_POSXY[0],
        "POSI_Y":    cfg.DEFAULT_POSXY[1],
        "floor":     cfg.DEFAULT_FLOOR
    }

def default_fingerprint_row() -> Dict[str, int]:
    return {f"AP{i}": cfg.DEFAULT_RSSI for i in range(1, cfg.DEFAULT_AP_N+1)}

def default_qr_event(room: str,
                     lon: float | None = None,
                     lat: float | None = None) -> dict:
    """
    Crée un événement QR pour la salle `room`.
    Si (lon, lat) sont fournis, on les utilise ;
    sinon on tombe sur DEFAULT_POSXY.
    """
    if lon is None or lat is None:
        lon, lat = cfg.DEFAULT_POSXY

    return {
        "room": room,
        "timestamp": datetime.now(timezone.utc).isoformat()+"Z",
        "position": [lon, lat],
    }


# =============================================================================
# 5) CONCATÉNATION GÉNÉRIQUE
# =============================================================================
def concat_fill(dfs: List[pd.DataFrame]) -> pd.DataFrame:
    """Concatène des DataFrames en gérant les colonnes manquantes."""
    if not dfs:
        return pd.DataFrame()
    all_cols = set().union(*(df.columns for df in dfs))
    for df in dfs:
        for c in all_cols - set(df.columns):
            df[c] = pd.NA
    return pd.concat(dfs, ignore_index=True)

# =============================================================================
# 6) POSITION DES SALLES
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
        print(f"⚠️ Fichier {csv_file_path} non trouvé")
    except Exception as e:
        print(f"⚠️ Erreur lors du chargement des positions: {e}")
    return room_positions

# Cache pour les positions des salles
_room_positions_cache = None

def get_room_position(room_number: str) -> tuple[float, float]:
    """
    Retourne (longitude, latitude) pour la salle demandée,
    à partir de data/room_positions.csv.
    """
    global _room_positions_cache
    if _room_positions_cache is None:
        project_root = Path(__file__).resolve().parent.parent
        csv_path = project_root / "data" / "room_positions.csv"
        
        if not csv_path.exists():
            logger.warning(f"[get_room_position] room_positions.csv non trouvé: {csv_path}")
            logger.warning("               Utilisation des coordonnées par défaut (0.0, 0.0)")
            return (0.0, 0.0)
        
        logger.debug(f"[get_room_position] Chargement de {csv_path}")
        _room_positions_cache = load_room_positions(csv_path)
        logger.info(f"[get_room_position] {_room_positions_cache!r} positions chargées")
    
    if room_number not in _room_positions_cache:
        logger.warning(f"[get_room_position] Salle '{room_number}' non trouvée dans cache")
        return (0.0, 0.0)
    
    coord = _room_positions_cache[room_number]
    logger.debug(f"[get_room_position] '{room_number}' -> {coord}")
    return coord

def get_qr_reset_position(qr_code):
    """Return the position of a room based on a QR code."""
    room_number = qr_code.split('_')[-1].replace('.png', '')
    return get_room_position(room_number)