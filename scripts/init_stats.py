"""
Initialization script for sensor statistics and processed data.:
- Path data/raw/2-XX_*/
- Calculates statistics for each room:
   • processed CSV for PDR + fingerprint: data/processed/room_<room>_processed.csv
   • aggregated stats by sensor:     data/stats/room_<room>.csv
- Concatenates all stats into knn_train.csv for global fingerprinting.

Usage:
    python init_stats.py [--verbose]
"""
import argparse
import pandas as pd
import logging
from pathlib import Path
import config as cfg
from services.sensors import (
    extract_room,
    list_sensor_files,
    read_sensor_csv,
    calculate_stats,
    merge_sensor_data,
    add_room_geo,
)

def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure le logging avec format cohérent"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    return logging.getLogger(__name__)

def validate_sensor_data(df: pd.DataFrame, filename: str) -> bool:
    """Valide les données d'un capteur"""
    if df is None or df.empty:
        return False

    if len(df) < cfg.MIN_ROWS:
        logging.warning(f"File {filename} has only {len(df)} rows (min: {cfg.MIN_ROWS})")
        return False
    
    # Vérifications additionnelles selon vos besoins
    required_cols = ['timestamp']  # Adapter selon vos colonnes critiques
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logging.warning(f"File {filename} missing columns: {missing_cols}")
        return False
    
    return True

def process_room_data(folder: Path, room: str, processed_dir: Path) -> bool:
    """
    Manage the processing of a room's raw data:
    
    Args:
        folder: Folder containing raw data for the room
        room: Room identifier
        processed_dir: Output folder for processed data

    Returns:
        True if processing succeeded, False otherwise
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Processing raw/{folder.name} → room {room}")

    # Load sensor files
    dfs = []
    sensor_files = list_sensor_files(folder)
    
    if not sensor_files:
        logger.warning(f"No sensor files found in {folder}")
        return False
    
    for sensor_file in sensor_files:
        try:
            df = read_sensor_csv(sensor_file, room)
            
            if not validate_sensor_data(df, sensor_file.name):
                logger.warning(f"Skip invalid file {sensor_file.name}")
                continue
                
            dfs.append(df)
            logger.info(f"Loaded {sensor_file.name} ({len(df)} rows)")
            
        except Exception as e:
            logger.error(f"Error reading {sensor_file.name}: {e}")
            continue
    
    if not dfs:
        logger.error(f"No valid sensor data for room {room}")
        return False

    # Generate the processed CSV
    try:
        logger.info("Merging sensor data...")
        merged = merge_sensor_data(dfs)
        
        if merged.empty:
            logger.error(f"merge_sensor_data returned empty for {room}")
            return False
        
        logger.info("Adding geo columns...")
        processed = add_room_geo(merged, room)

        # Save the processed file
        out_proc = processed_dir / f"room_{room}_processed.csv"
        processed.to_csv(out_proc, index=False)
        logger.info(f"Export: {out_proc}")

        # Calculate aggregated stats
        logger.info("Calculating stats...")
        all_df = pd.concat(dfs, ignore_index=True)
        stats = calculate_stats(all_df)
        
        if not stats.empty:
            out_stats = cfg.STATS_DIR / f"room_{room}.csv"
            stats.to_csv(out_stats, index=False)
            logger.info(f"Stats: {out_stats}")
        else:
            logger.warning(f"No stats generated for {room}")
            
        return True
        
    except Exception as e:
        logger.exception(f"Error processing room {room}: {e}")

def process_route_data(folder: Path, route_name: str, processed_dir: Path) -> bool:
    """
    Manage the processing of a route's raw data:
      - Load all sensor CSVs
      - merge_sensor_data to obtain ACCE_*, GYRO_*, MAGN_* on the same timestamp index
      - Save to processed/route_<N>_processed.csv
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Processing raw/{folder.name} → route {route_name}")

    # 1. Load all sensor files
    dfs = []
    for f in list_sensor_files(folder):
        df = read_sensor_csv(f, route_name)
        if df is None or df.empty:
            logger.warning(f"Skip invalid file {f.name}")
        else:
            dfs.append(df)
            logger.info(f"Loaded {f.name}: {len(df)} rows")

    if not dfs:
        logger.error(f"No valid sensor data in {folder}")
        return False

    # 2. Merge on timestamp
    try:
        logger.info("Merging sensor data for route...")
        merged = merge_sensor_data(dfs)
        if merged.empty:
            logger.error("merge_sensor_data returned empty")
            return False

        # 3. Save without geo
        out_file = processed_dir / f"route_{route_name}_processed.csv"
        merged.to_csv(out_file, index=False)
        logger.info(f"Exported {out_file}")

        return True

    except Exception as e:
        logger.exception(f"Error processing route {route_name}: {e}")
        return False

# def build_global_training_set() -> bool:
#     """
#     Build the global kNN training set from per-room stats.
    
#     Returns:
#         True if construction succeeded, False otherwise
#     """
#     logger = logging.getLogger(__name__)
#     logger.info("Building global kNN training set...")

#     stat_files = sorted(cfg.STATS_DIR.glob("room_*.csv"))

#     if not stat_files:
#         logger.error("No per-room stats found, knn_train.csv skipped")
#         return False
    
#     try:
#         # Concatenation with missing column handling
#         dfs = []
#         all_columns = set()
#
#         # First pass: identify all columns
#         for stat_file in stat_files:
#             try:
#                 df_room = pd.read_csv(stat_file)
#                 if not df_room.empty:
#                     all_columns.update(df_room.columns)
#                     dfs.append((stat_file, df_room))
#             except Exception as e:
#                 logger.error(f"Error reading {stat_file}: {e}")
#                 continue
        
#         if not dfs:
#             logger.error("No valid stat files found")
#             return False

#         # Second pass: harmonize columns
#         harmonized_dfs = []
#         for stat_file, df_room in dfs:
#             # Add missing columns
#             for col in all_columns - set(df_room.columns):
#                 df_room[col] = None
#
#             # Rearrange columns in a consistent order
#             df_room = df_room.reindex(columns=sorted(all_columns))
#             harmonized_dfs.append(df_room)
#
#         # Final concatenation
#         harmonized_dfs = [df.dropna(axis=1, how='all')  # remove completely empty columns
#             for df in harmonized_dfs
#             if not df.empty and df.dropna(how='all', axis=1).shape[1] > 0
#         ]

#         df_knn = pd.concat(harmonized_dfs, ignore_index=True)
        
#         # Sauvegarde
#         out_knn = cfg.RECORDINGS_DIR / cfg.GLOBAL_KNN
#         df_knn.to_csv(out_knn, index=False)
        
#         logger.info(f"Global training file: {out_knn} ({len(df_knn)} rows, {len(all_columns)} columns)")
#         return True
        
#     except Exception as e:
#         logger.error(f"Error building global training set: {e}")
#         return False

def init_stats(verbose: bool = False) -> None:
    """
    Main function to initialize sensor statistics and processed data.
    
    Args:
        verbose: Enable detailed logging
    """
    logger = setup_logging(verbose)

    # Prepare directories
    processed_dir = cfg.PROCESSED_DIR
    processed_dir.mkdir(exist_ok=True, parents=True)
    cfg.STATS_DIR.mkdir(exist_ok=True, parents=True)

    # Process rooms
    processed_rooms = []
    processed_routes = []
    total_folders = 0

    for folder in sorted(cfg.RAW_DIR.iterdir()):
        if not folder.is_dir():
            continue

        total_folders += 1

        if folder.name.startswith(cfg.ROOM_PREFIX):
            try:
                room = extract_room(folder.name)
                if process_room_data(folder, room, processed_dir):
                    processed_rooms.append(room)
            except Exception as e:
                logger.error(f"Error processing room folder {folder.name}: {e}")
                continue

        elif folder.name.startswith("Route-"):
            try:
                route_name = folder.name.split("-")[-1]
                if process_route_data(folder, route_name, processed_dir):
                    processed_routes.append(route_name)
            except Exception as e:
                logger.error(f"Error processing route folder {folder.name}: {e}")
                continue

    # Build global training set
    # global_success = build_global_training_set()

    # Final report
    logger.info(f"Processing complete:")
    logger.info(f"  - Folders found: {total_folders}")
    logger.info(f"  - Rooms processed: {len(processed_rooms)}")
    logger.info(f"  - Routes processed: {len(processed_routes)}")
    # logger.info(f"  - Global training set: {'✅' if global_success else '❌'}")
    
    if processed_rooms:
        logger.info(f"  - Processed rooms: {', '.join(processed_rooms)}")
    
    if processed_routes:
        logger.info(f"  - Processed routes: {', '.join(processed_routes)}")
    
    if len(processed_rooms) == 0 and len(processed_routes) == 0:
        logger.warning("No data were successfully processed!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Init sensor stats & processed data")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    init_stats(args.verbose)