"""
Collecte en temps réel :
Concatène les CSV d'un dossier raw spécifique
Exporte un enregistrement horodaté dans data/recordings/door_<room>/
Usage : python record_realtime.py --folder data/raw/2-XX_... [--client_ip <IP>]
"""
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd
from project.scripts.utils import extract_room, list_sensor_files, read_sensor_csv, RECORDINGS_DIR

def record_realtime(folder: Path, client_ip: str):
    room = extract_room(folder.name)
    dfs = [read_sensor_csv(f, room) for f in list_sensor_files(folder)]
    dfs = [d for d in dfs if d is not None]
    if not dfs:
        print(f"⚠️ Pas de données valides pour {folder.name}")
        return
    all_df = pd.concat(dfs, ignore_index=True)
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    rec_dir = RECORDINGS_DIR / f"door_{room}"
    rec_dir.mkdir(parents=True, exist_ok=True)
    rec_file = rec_dir / f"recording_{ts}.csv"
    all_df.to_csv(rec_file, index=False)
    print(f"✅ Enregistrement créé: {rec_file}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Enregistrement temps réel')
    parser.add_argument('--folder', type=str, required=True, help='Dossier raw à traiter')
    parser.add_argument('--client_ip', default='localhost', help='IP du client')
    args = parser.parse_args()
    folder = Path(args.folder)
    if not folder.exists():
        print(f"❌ Dossier introuvable: {folder}")
    else:
        record_realtime(folder, args.client_ip)