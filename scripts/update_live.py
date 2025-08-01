" This script updates the live data for a specific room by processing PDR, fingerprint, and QR event data."
# It reads the latest data from CSV files, updates the PDR trace, fingerprint current data"

import argparse
from pathlib import Path
from datetime import datetime, timezone 
import pandas as pd
from scripts.utils import (
    cfg, get_logger,
    read_csv_safe, write_csv_safe,
    read_json_safe, write_json_safe,
    default_pdr_row, default_fingerprint_row, get_room_position, default_qr_event
)

def update_pdr(room, logger):
    src = cfg.PROCESSED_DIR / f"room_{room}_processed.csv"
    dst = cfg.PDR_TRACE
    df  = read_csv_safe(src)
    if not df.empty:
        cols = [c for c in cfg.PDR_COLUMNS if c in df.columns]
        write_csv_safe(df.tail(1)[cols], dst)
        logger.info(f"PDR updated ← {src.name}")
    else:
        write_csv_safe(pd.DataFrame([default_pdr_row()]), dst)
        logger.warning("PDR default created")

def update_fp(room, logger):
    # if we don’t yet have a global knn_train.csv, skip fingerprint
    knn_path = cfg.STATS_DIR / cfg.GLOBAL_KNN
    if not knn_path.exists():
        logger.warning(f"No knn_train.csv found at {knn_path}, skipping FP update")
        # write default RSSI row so geolocate sees “no FP data”
        write_csv_safe(pd.DataFrame([default_fingerprint_row()]), cfg.FP_CURRENT)
        return

    src = cfg.RECORDINGS_DIR / f"door_{room.replace('-','_')}" / 'latest.csv'
    dst = cfg.FP_CURRENT
    df  = read_csv_safe(src)
    if not df.empty:
        ap = [c for c in df.columns if c.lower().startswith('ap')]
        write_csv_safe(pd.DataFrame([df[ap].mean()]), dst)
        logger.info(f"FP updated ← {src.name}")
    else:
        write_csv_safe(pd.DataFrame([default_fingerprint_row()]), dst)
        logger.warning("Fingerprint default created")

def update_qr(room, logger):
    """Mise à jour complète du fichier QR"""
    try:
        # 1. Lire le fichier existant
        events_path = cfg.QR_EVENTS
        logger.info(f"Début mise à jour QR pour salle {room}")
        logger.info(f"Chemin fichier: {events_path}")

        # 2. Récupérer la position réelle de la salle
        try:
            lon, lat = get_room_position(room)
            if lon == 0.0 and lat == 0.0:  # Position par défaut
                logger.warning(f"Aucune position trouvée pour la salle {room}")
                lon, lat = cfg.DEFAULT_POSXY
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la position: {str(e)}")
            lon, lat = cfg.DEFAULT_POSXY  

        logger.info(f"Position utilisée pour le reset: ({lon}, {lat})")

        # 3. Créer le nouvel événement
        new_event = default_qr_event(room, lon, lat)

        # 4. **Écraser complètement le fichier avec le seul nouvel événement**
        write_json_safe([new_event], events_path)
        logger.info("Fichier QR écrasé avec un seul nouvel événement")

        # 5. Vérification
        saved_events = read_json_safe(events_path)
        if saved_events != [new_event]:
            logger.error("Problème: l'événement sauvegardé ne correspond pas à l'attendu")
        else:
            logger.info(f"Événement correctement sauvegardé: {saved_events[-1]}")

    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des événements QR: {e}")
        raise


def update_localization_files(df: pd.DataFrame, folder_name: str, room: str):
    """
    Met à jour les fichiers de localisation (pdr_traces.csv, fingerprint.csv, qr_map.csv) avec les données traitées.
    """
    logger = get_logger(__name__)

    # Sauvegarde des données traitées
    processed_file = cfg.PROCESSED_DIR / f"room_{room}_processed.csv"
    write_csv_safe(df, processed_file)

    # Mise à jour des fichiers
    update_pdr(room, logger)

    fp_src = Path(cfg.RECORDINGS_DIR) / folder_name / 'latest.csv'
    if fp_src.exists():
        update_fp(room, logger)
    else:
        logger.warning(f"Pas de fichier fingerprint trouvé pour {room}")

    update_qr(room, logger)

    logger.info(f"Fichiers de localisation mis à jour pour la salle {room}")



def main(room, verbose=False):
    logger = get_logger(__name__, verbose)
    logger.info(f"Updating live for room {room}")
    update_pdr(room, logger)
    update_fp(room, logger)
    logger.info("Uncomment below to log QR resets")
    update_qr(room, logger)

if __name__=="__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--room",default="2-01")
    p.add_argument("-v","--verbose",action="store_true")
    args = p.parse_args()
    main(args.room, args.verbose)
