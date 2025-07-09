"""
Initialisation (preprocessing) des données brutes a priori :
Parcourt data/raw/2-XX_*/
Calcule et exporte statistiques agrégées par salle dans data/stats/room_<room>.csv
Usage : python init_stats.py
"""
import argparse
import pandas as pd
from pathlib import Path
from utils import extract_room, list_sensor_files, read_sensor_csv, calculate_stats, RAW_DATA_DIR, STATS_DIR

def init_stats():
    if not RAW_DATA_DIR.exists():
        print(f"❌ Dossier raw introuvable: {RAW_DATA_DIR}")
        return
    for folder in sorted(RAW_DATA_DIR.iterdir()):
        if not folder.is_dir() or not folder.name.startswith('2-'):
            continue
        room = extract_room(folder.name)
        dfs = [read_sensor_csv(f, room) for f in list_sensor_files(folder)]
        dfs = [d for d in dfs if d is not None]
        if not dfs:
            print(f"⚠️ Pas de données valides pour {folder.name}")
            continue
        all_df = pd.concat(dfs, ignore_index=True)
        stats_df = calculate_stats(all_df)
        out = STATS_DIR / f"room_{room}.csv"
        stats_df.to_csv(out, index=False)
        print(f"✅ Stats exportées: {out}")

if __name__ == '__main__':
    init_stats()