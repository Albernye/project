import argparse
import pandas as pd
from pathlib import Path
from scripts.utils import (
    cfg, get_logger,
    read_csv_safe, write_csv_safe,
    read_json_safe, write_json_safe,
    default_pdr_row, default_fingerprint_row, default_qr_event
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
    events = read_json_safe(cfg.QR_EVENTS)
    events.append(default_qr_event(room))
    write_json_safe(events, cfg.QR_EVENTS)
    logger.info("QR event appended")

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
