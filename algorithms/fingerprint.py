import pandas as pd
import numpy as np
import math
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsRegressor

# Local coordinate origin (lon0, lat0) for planar projection
def set_origin(lon0: float, lat0: float):
    global ORIGIN_LON, ORIGIN_LAT
    ORIGIN_LON, ORIGIN_LAT = lon0, lat0


def ll_to_local(lon: float, lat: float) -> tuple:
    """
    Convert longitude/latitude to local meter coordinates using equirectangular approximation.
    """
    R = 6371000  # Earth radius (m)
    x = (lon - ORIGIN_LON) * math.cos(math.radians(ORIGIN_LAT)) * R
    y = (lat - ORIGIN_LAT) * R
    return x, y

ORIGIN_LON, ORIGIN_LAT = 0.0, 0.0  # set via set_origin() before use

def fingerprint(knn_train_file: str, fp_file: str, kP: int = 3, kZ: int = 3) -> tuple:
    """
    Perform Wi-Fi fingerprinting to estimate (x, y, floor).

    Returns:
        (x, y, floor)
    """
    # Load fingerprint and training data
    fp_df = pd.read_csv(fp_file, delimiter=';')
    train_df = pd.read_csv(knn_train_file, delimiter=';')

    # Identify common RSSI columns
    rssi_cols = sorted(set(c for c in fp_df if c.startswith('rssi')) & set(c for c in train_df if c.startswith('rssi')))

    # Extract features and ground truth
    fp_rssi = fp_df[rssi_cols].values
    train_rssi = train_df[rssi_cols].values
    train_coords = train_df[['long', 'lat']].values
    train_floor = train_df['Z'].values.reshape(-1, 1)

    # Scale RSSI
    scaler = StandardScaler().fit(train_rssi)
    train_norm = scaler.transform(train_rssi)
    fp_norm = scaler.transform(fp_rssi)

    # kNN regressors
    knn_xy = KNeighborsRegressor(n_neighbors=kP)
    knn_z  = KNeighborsRegressor(n_neighbors=kZ)
    knn_xy.fit(train_norm, train_coords)
    knn_z.fit(train_norm, train_floor)

    pred_xy = knn_xy.predict(fp_norm)
    pred_z  = knn_z.predict(fp_norm)

    # Last measurement
    lon, lat = pred_xy[-1]
    floor = int(round(pred_z[-1, 0]))

    # Convert to local meters
    x, y = ll_to_local(lon, lat)
    return x, y, floor