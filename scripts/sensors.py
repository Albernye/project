"""This module provides functions to handle sensor data extraction, reading, and processing.
It includes functions to extract room information, list sensor files, read sensor CSV files,
calculate statistics, merge sensor data, and add geographical information to the data.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from scripts.utils import SENSOR_MAPPING, UNCALIBRATED_SUFFIX, get_logger,get_room_position

logger = get_logger(__name__)


def extract_room(folder_name: str) -> str:
    """Extrait le numéro de salle du nom du dossier (ex: '2-1_quelquechose' -> '2-01')"""
    base = folder_name.split('_', 1)[0]
    parts = base.split('-')
    return f"{parts[0]}-{parts[1].zfill(2)}" if len(parts) >= 2 else base

def list_sensor_files(folder: Path):
    """Liste les fichiers de capteurs, prenant en compte les suffixes _0"""
    candidates = {f.stem.lower(): f for f in folder.glob("*.csv")}
    files = []
    for name, f in candidates.items():
        # Supprime _0 si présent
        key = name.replace('_0', '').replace(UNCALIBRATED_SUFFIX, '')
        if key not in SENSOR_MAPPING:
            print(f"❌ '{key}' not in SENSOR_MAPPING")
            continue
        print(f"✅ Match found: '{key}'")
        files.append(f)
    return files


def read_sensor_csv(file: Path, room: str) -> pd.DataFrame:
    """Lit un fichier CSV de capteur et standardise les colonnes selon le format réel"""
    # Tentative de lecture avec différents encodages
    for enc in ('utf-8', 'latin-1', 'cp1252'):
        try: 
            df = pd.read_csv(file, encoding=enc, engine='python', on_bad_lines='skip')
            break
        except Exception as e:
            continue
    else: 
        print(f"❌ Impossible de lire {file.name}")
        return None
    
    if df.empty: 
        return None
    
    # Standardisation des noms de colonnes
    df.columns = df.columns.str.strip()
    
    # Identification du capteur

    name = file.stem.lower()
    unc = name.endswith(UNCALIBRATED_SUFFIX)
    key = name.replace('_0', '').replace(UNCALIBRATED_SUFFIX, '')
    sensor = SENSOR_MAPPING.get(key)
    
    if not sensor:
        print(f"❌ '{key}' not found in SENSOR_MAPPING") 
        return None
    
    df['sensor_type'] = sensor + (UNCALIBRATED_SUFFIX if unc else '')
    df['room'] = room
    df['source_file'] = file.name
    
    # Conversion du timestamp - utiliser seconds_elapsed si disponible, time ou timestamp sinon
    if 'seconds_elapsed' in df.columns:
        df['timestamp'] = pd.to_numeric(df['seconds_elapsed'], errors='coerce')
    elif 'time' in df.columns:
        # Convertir le timestamp nanosecondes en secondes depuis le début
        df['timestamp'] = pd.to_numeric(df['time'], errors='coerce')
    elif 'timestamp' in df.columns:
        df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
    else:
        print(f"⚠️ Pas de colonne temporelle trouvée dans {file.name}")
        return None
    
    # Conversion des colonnes numériques selon le type de capteur
    numeric_cols = ['x', 'y', 'z', 'pressure', 'relativeAltitude', 'alpha', 'beta', 'gamma']
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    
    return df

def calculate_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule les statistiques agrégées par type de capteur"""
    stats = []
    for sensor in df['sensor_type'].unique():
        sub = df[df['sensor_type'] == sensor]
        numeric_cols = [c for c in sub.select_dtypes(include='number').columns 
                       if c not in ['room', 'timestamp']]
        if not numeric_cols:
            continue
        
        desc = sub[numeric_cols].describe(percentiles=[.25, .5, .75])
        base = {
            'sensor_type': sensor,
            'room': sub['room'].iat[0],
            'data_points': len(sub)
        }
        
        for col in numeric_cols:
            base[f"{col}_mean"] = desc.loc['mean', col]
            base[f"{col}_std"] = desc.loc['std', col]
            base[f"{col}_min"] = desc.loc['min', col]
            base[f"{col}_max"] = desc.loc['max', col]
            # Utilisation des labels string pour les percentiles
            for pct, label in [('25%', '25th'), ('50%', '50th'), ('75%', '75th')]:
                if pct in desc.index:
                    base[f"{col}_{label}"] = desc.loc[pct, col]
                else:
                    base[f"{col}_{label}"] = None
        stats.append(base)
    return pd.DataFrame(stats)

def merge_sensor_data(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    """
    Merge multiple sensor DataFrames into a single DataFrame with proper column naming.
    Gère les formats réels des fichiers CSV.
    """
    cleaned = []
    
    for df in dfs:
        if df.empty:
            continue
            
        sensor = df['sensor_type'].iloc[0]
        
        # Vérifier la colonne timestamp
        if 'timestamp' not in df.columns:
            print(f"⚠️ merge_sensor_data: missing timestamp column for {sensor}")
            continue

        # Déterminer le préfixe selon le capteur
        if sensor.startswith('accelerometer'):
            prefix = 'ACCE'
            mod_col = 'ACCE_MOD'
            required_cols = ['x', 'y', 'z']
        elif sensor.startswith('gyroscope'):
            prefix = 'GYRO'
            mod_col = 'GYRO_MOD'
            required_cols = ['x', 'y', 'z']
        elif sensor.startswith('magnetometer'):
            prefix = 'MAGN'
            mod_col = 'MAGN_MOD'
            required_cols = ['x', 'y', 'z']
        else:
            # On ignore les autres capteurs pour le moment
            print(f"⚠️ Capteur {sensor} non géré pour le merge")
            continue

        # Vérifier les colonnes x, y, z
        if not all(c in df.columns for c in required_cols):
            print(f"⚠️ merge_sensor_data: missing columns {required_cols} for {sensor}")
            continue

        # Créer un DataFrame temporaire avec les colonnes nécessaires
        tmp = df[['timestamp'] + required_cols].copy()
        tmp = tmp.dropna()  # Supprimer les lignes avec des NaN
        
        if tmp.empty:
            print(f"⚠️ Données vides après nettoyage pour {sensor}")
            continue
        
        # Utiliser timestamp comme index pour le merge
        tmp = tmp.set_index('timestamp')
        
        # Renommage selon le format attendu
        tmp = tmp.rename(columns={
            'x': f'{prefix}_X',
            'y': f'{prefix}_Y',
            'z': f'{prefix}_Z'
        })
        
        # Calcul de la magnitude (module)
        tmp[mod_col] = np.sqrt(
            tmp[f'{prefix}_X']**2 + 
            tmp[f'{prefix}_Y']**2 + 
            tmp[f'{prefix}_Z']**2
        )
        
        print(f"✅ Préparé {sensor}: {len(tmp)} échantillons")
        cleaned.append(tmp)

    if not cleaned:
        print("❌ Aucune donnée de capteur valide trouvée")
        return pd.DataFrame()

    print(f"🔗 Fusion de {len(cleaned)} capteurs...")
    
    # Fusion de tous les DataFrames sur le timestamp
    merged = cleaned[0]
    for i, other in enumerate(cleaned[1:], 1):
        print(f"  Fusion avec capteur {i+1}")
        merged = merged.join(other, how='outer')

    # Traitement des valeurs manquantes
    print(f"📊 Données fusionnées: {len(merged)} échantillons")
    merged = merged.sort_index()
    
    # Interpolation et remplissage des valeurs manquantes
    merged = merged.interpolate(method='index').ffill().bfill()

    # Reset index et garder le timestamp
    merged = merged.reset_index()
    merged = merged.rename(columns={'timestamp': 'timestamp'})
    
    # Sélection et ordre des colonnes selon le format attendu
    expected_cols = [
        'timestamp',
        'ACCE_X', 'ACCE_Y', 'ACCE_Z', 'ACCE_MOD',
        'GYRO_X', 'GYRO_Y', 'GYRO_Z', 'GYRO_MOD',
        'MAGN_X', 'MAGN_Y', 'MAGN_Z', 'MAGN_MOD'
    ]
    
    # Ne garder que les colonnes qui existent
    available_cols = [col for col in expected_cols if col in merged.columns]
    final_df = merged[available_cols]
    
    print(f"✅ Données finales: {len(final_df)} échantillons, {len(available_cols)} colonnes")
    return final_df

def add_room_geo(df: pd.DataFrame, room: str) -> pd.DataFrame:
    """
    Ajoute les colonnes géographiques : long, lat, POSI_X, POSI_Y
    """
    if df.empty:
        return df
        
    lon, lat = get_room_position(room)
    
    # Ajout des colonnes géographiques
    df['long'] = lon
    df['lat'] = lat
    df['POSI_X'] = 0.0
    df['POSI_Y'] = 0.0
    
    # Réorganisation des colonnes selon le format attendu
    geo_cols = ['timestamp', 'long', 'lat', 'POSI_X', 'POSI_Y']
    other_cols = [c for c in df.columns if c not in geo_cols]
    
    return df[geo_cols + other_cols]