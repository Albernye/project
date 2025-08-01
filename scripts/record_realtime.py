"""
Collecte en temps réel des données capteurs et les stocke horodatées.
Usage : record_realtime(folder: Path, client_ip: str) -> bool
"""
from pathlib import Path
from datetime import datetime, timezone
import logging
import pandas as pd

from scripts.sensors import extract_room, list_sensor_files, read_sensor_csv
from scripts.utils import cfg, get_logger

logger = get_logger(__name__)

def record_realtime(folder: Path, client_ip: str = None) -> bool:
    """
    Lit tous les CSV de `folder`, concatène et écrit un fichier horodaté dans DATA/recordings.
    Args:
        folder: dossier contenant les CSV bruts
        client_ip: adresse du client (optionnelle, pour logging)
    Returns:
        True si un enregistrement a été créé, False sinon.
    """
    room = extract_room(folder.name)
    files = list_sensor_files(folder)
    logger.info(f"Détection de {len(files)} fichiers capteurs dans {folder.name}")

    dfs = []
    for f in files:
        df = read_sensor_csv(f, room)
        if df is not None and not df.empty:
            dfs.append(df)
        else:
            logger.warning(f"Fichier invalide ou vide ignoré: {f.name}")

    if not dfs:
        logger.warning(f"Aucune donnée valide pour la salle {room}")
        return False

    all_df = pd.concat(dfs, ignore_index=True)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    output_dir = cfg.RECORDINGS_DIR / f"door_{room}"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"recording_{timestamp}.csv"

    all_df.to_csv(output_file, index=False)
    logger.info(f"Enregistrement créé: {output_file}")
    return True