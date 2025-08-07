" This script updates the live data for a specific room by processing PDR, fingerprint, and QR event data."
# It reads the latest data from CSV files, updates the PDR trace, fingerprint current data"

import argparse
from pathlib import Path 
import pandas as pd
from services.utils import (
    get_logger,
    read_csv_safe, write_csv_safe,
    read_json_safe, write_json_safe,
    default_pdr_row, default_fingerprint_row, get_room_position, default_qr_event
)
import config

def update_pdr(room, logger):
    src = config.PROCESSED_DIR / f"room_{room}_processed.csv"
    dst = config.PDR_TRACE
    df  = read_csv_safe(src)
    if not df.empty:
        cols = [c for c in config.PDR_COLUMNS if c in df.columns]
        write_csv_safe(df.tail(1)[cols], dst)
        logger.info(f"PDR updated ← {src.name}")
    else:
        write_csv_safe(pd.DataFrame([default_pdr_row()]), dst)
        logger.warning("PDR default created")

# def update_fp(room, logger):
#     # if we don’t yet have a global knn_train.csv, skip fingerprint
#     knn_path = config.STATS_DIR / config.GLOBAL_KNN
#     if not knn_path.exists():
#         logger.warning(f"No knn_train.csv found at {knn_path}, skipping FP update")
#         # write default RSSI row so geolocate sees “no FP data”
#         write_csv_safe(pd.DataFrame([default_fingerprint_row()]), config.FP_CURRENT)
#         return

#     src = config.RECORDINGS_DIR / f"door_{room.replace('-','_')}" / 'latest.csv'
#     dst = config.FP_CURRENT
#     df  = read_csv_safe(src)
#     if not df.empty:
#         ap = [c for c in df.columns if c.lower().startswith('ap')]
#         write_csv_safe(pd.DataFrame([df[ap].mean()]), dst)
#         logger.info(f"FP updated ← {src.name}")
#     else:
#         write_csv_safe(pd.DataFrame([default_fingerprint_row()]), dst)
#         logger.warning("Fingerprint default created")

def update_qr(room, logger):
    """Update the QR events file for a specific room."""
    try:
        # 1. Read the existing file
        events_path = config.QR_EVENTS_FILE
        logger.info(f"Starting QR update for room {room}")
        logger.info(f"File path: {events_path}")

        # 2. Get the actual position of the room
        try:
            lon, lat = get_room_position(room)
            if lon == 0.0 and lat == 0.0:  # Default position
                logger.warning(f"No position found for room {room}")
                lon, lat = config.DEFAULT_POSXY
        except Exception as e:
            logger.error(f"Error retrieving position: {str(e)}")
            lon, lat = config.DEFAULT_POSXY

        logger.info(f"Position used for reset: ({lon}, {lat})")

        # 3. Create the new event
        new_event = default_qr_event(room, lon, lat)

        # 4. **Overwrite the file with the new event**
        write_json_safe([new_event], events_path)
        logger.info("QR file overwritten with a single new event")

        # 5. Verification
        saved_events = read_json_safe(events_path)
        if saved_events != [new_event]:
            logger.error("Problem: saved event does not match expected")
        else:
            logger.info(f"Event correctly saved: {saved_events[-1]}")

    except Exception as e:
        logger.error(f"Error updating QR events: {e}")
        raise


def update_localization_files(df: pd.DataFrame, folder_name: str, room: str):
    """
    Update localization files (pdr_traces.csv, fingerprint.csv, qr_map.csv) with processed data.
    """
    logger = get_logger(__name__)

    # Save processed data
    processed_file = config.PROCESSED_DIR / f"room_{room}_processed.csv"
    write_csv_safe(df, processed_file)

    # Update files
    update_pdr(room, logger)

    # update_fp(room, logger)

    update_qr(room, logger)

    logger.info(f"Localization files updated for room {room}")


def main(room, verbose=False):
    logger = get_logger(__name__, verbose)
    logger.info(f"Updating live for room {room}")
    update_pdr(room, logger)
    # update_fp(room, logger)
    logger.info("Uncomment below to log QR resets")
    update_qr(room, logger)

if __name__=="__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--room",default="2-01")
    p.add_argument("-v","--verbose",action="store_true")
    args = p.parse_args()
    main(args.room, args.verbose)
