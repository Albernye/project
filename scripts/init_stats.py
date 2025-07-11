"""
Initialisation (preprocessing) des données brutes a priori :
Parcourt data/raw/2-XX_*/
Calcule et exporte statistiques agrégées par salle dans data/stats/room_<room>.csv
Usage : python init_stats.py
"""
import argparse
import pandas as pd
from pathlib import Path
from utils import (
    extract_room, list_sensor_files, read_sensor_csv,
    calculate_stats, merge_sensor_data, add_room_geo,
    RAW_DATA_DIR, STATS_DIR
)

def init_stats():
    """Initialise les statistiques et traite les données brutes"""
    if not RAW_DATA_DIR.exists():
        print(f"❌ Raw folder not found: {RAW_DATA_DIR}")
        return
    
    # Créer le dossier processed s'il n'existe pas
    processed_dir = RAW_DATA_DIR.parent / 'processed'
    processed_dir.mkdir(exist_ok=True)
    STATS_DIR.mkdir(exist_ok=True)
    
    processed_count = 0
    
    for folder in sorted(RAW_DATA_DIR.iterdir()):
        if not folder.is_dir() or not folder.name.startswith('2-'):
            continue
            
        room = extract_room(folder.name)
        print(f"🔄 Processing {folder.name} -> room {room}")
        
        # Lire tous les fichiers de capteurs
        sensor_files = list_sensor_files(folder)
        if not sensor_files:
            print(f"⚠️ No sensor files found in {folder.name}")
            continue
            
        dfs = []
        for sensor_file in sensor_files:
            df = read_sensor_csv(sensor_file, room)
            if df is not None and not df.empty:
                dfs.append(df)
                print(f"  📊 Loaded {sensor_file.name}: {len(df)} rows")
            else:
                print(f"  ⚠️ Failed to load {sensor_file.name}")
        
        if not dfs:
            print(f"⚠️ No valid data for {folder.name}")
            continue
        
        # 1) Merge raw sensor data pour PDR/Fingerprint
        print(f"  🔗 Merging sensor data...")
        merged_df = merge_sensor_data(dfs)
        if merged_df.empty:
            print(f"⚠️ Merged data empty for {room}")
            continue
        
        print(f"  📊 Merged data shape: {merged_df.shape}")
        
        # 2) Ajout des colonnes géographiques
        print(f"  🌍 Adding geographical data...")
        processed_df = add_room_geo(merged_df, room)

        # 3) Export CSV « processed » prêt pour les algorithmes
        out_raw = processed_dir / f"room_{room}_processed.csv"
        processed_df.to_csv(out_raw, index=False)
        print(f"✅ Raw data for {room} exported to {out_raw}")
        
        # 4) Statistiques agrégées (optionnel)
        print(f"  📈 Calculating statistics...")
        all_df = pd.concat(dfs, ignore_index=True)
        stats_df = calculate_stats(all_df)
        
        if not stats_df.empty:
            out_stats = STATS_DIR / f"room_{room}.csv"
            stats_df.to_csv(out_stats, index=False)
            print(f"✅ Stats for {room} exported to {out_stats}")
        
        processed_count += 1
        print(f"  ✅ Room {room} processed successfully\n")
    
    print(f"🎉 Processing complete! {processed_count} rooms processed.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Initialize sensor data statistics')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    init_stats()