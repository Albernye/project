" This script updates the live data for a specific room by processing PDR, fingerprint, and QR event data."
# It reads the latest data from CSV files, updates the PDR trace, fingerprint current data"

import argparse
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
    """Version corrigée avec validation complète"""
    try:
        # 1. Lire le fichier existant
        events_path = cfg.QR_EVENTS
        logger.info(f"Début mise à jour QR pour salle {room}")
        logger.info(f"Chemin fichier: {events_path}")

        current_events = read_json_safe(events_path)
        if not isinstance(current_events, list):
            current_events = []
            logger.warning("Fichier QR corrompu - réinitialisé à une liste vide")

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

        # 4. Ajouter et sauvegarder
        current_events.append(new_event)
        write_json_safe(current_events, events_path)
        logger.info(f"Mise à jour réussie. Nouveau total: {len(current_events)} événements")

        # 5. Vérification
        saved_events = read_json_safe(events_path)
        if len(saved_events) != len(current_events):
            logger.error("Problème: nombre d'événements différent après sauvegarde")
        else:
            last_event = saved_events[-1]
            logger.info(f"Dernier événement sauvegardé: {last_event}")

    except Exception as e:
        logger.error(f"Échec de la mise à jour QR: {str(e)}", exc_info=True)
        raise  # Pour s'assurer que l'erreur est visible


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
