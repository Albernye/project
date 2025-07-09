import os
import pandas as pd
from pathlib import Path
from config import config

# Paths
project_root = Path(config.get_project_root())
RAW_DATA_DIR = project_root / "data" / "sensor_data_raw"
OUTPUT_DIR = project_root / "data" / "sensor_data_aggregated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def get_room_from_folder_name(folder_name: str) -> str:
    """Extrait le numéro de salle du nom du dossier selon le format IPIN"""
    try:
        part = folder_name.split("_")[0]
        floor, number = part.split("-")
        return f"{floor}{int(number):02d}"
    except Exception as e:
        print(f"⚠️ Impossible de déterminer la salle depuis '{folder_name}': {e}")
        return None

def process_session(session_dir: Path):
    """Traite un dossier de session et génère un CSV agrégé"""
    room = get_room_from_folder_name(session_dir.name)
    if not room:
        return

    try:
        # Lire tous les fichiers CSV du dossier
        dfs = []
        for csv_file in session_dir.glob('*.csv'):
            sensor_type = csv_file.stem.replace('Uncalibrated', '')
            df = pd.read_csv(csv_file)
            df['sensor_type'] = sensor_type
            dfs.append(df)

        if not dfs:
            print(f"Aucune donnée CSV trouvée dans {session_dir.name}")
            return

        combined_df = pd.concat(dfs, ignore_index=True)

        # Nettoyage des colonnes
        numeric_cols = combined_df.select_dtypes(include='number').columns
        combined_df = combined_df[numeric_cols + ['sensor_type']]

        # Calcul des statistiques
        stats = combined_df.groupby('sensor_type').agg(['mean', 'std', 'min', 'max'])

        # Sauvegarder en CSV
        output_file = OUTPUT_DIR / f"room_{room}.csv"
        stats.to_csv(output_file, index=True)
        print(f"✅ Statistiques CSV générées pour la salle {room}")

    except Exception as e:
        print(f"❌ Erreur lors du traitement de {session_dir.name}: {e}")

def main():
    """Point d'entrée principal"""
    if not RAW_DATA_DIR.exists():
        print(f"❌ Répertoire source introuvable: {RAW_DATA_DIR}")
        return

    for session_folder in RAW_DATA_DIR.iterdir():
        if session_folder.is_dir():
            process_session(session_folder)

if __name__ == '__main__':
    main()
