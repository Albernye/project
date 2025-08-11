"""
Fingerprint-Only Simulation
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from algorithms.fingerprint import set_origin, fingerprint_with_local_coords, ll_to_local

def generate_knn_train(path):
    df = pd.DataFrame({
        'rssi1': [-50, -55, -53, -58],
        'rssi2': [-60, -65, -63, -68],
        'long':  [11.1100, 11.1105, 11.1110, 11.1115],
        'lat':   [49.4600, 49.4605, 49.4610, 49.4615],
        'Z':     [0,      0,       1,       1]
    })
    df.to_csv(path, sep=';', index=False)

def generate_fp_scans(path, num_scans=20):
    # ground‐truth long/lat for evaluation only, but they are NOT written
    lons = np.linspace(11.1100, 11.1115, num_scans)
    lats = np.linspace(49.4600, 49.4615, num_scans)
    # simulate RSSI from each train point with noise
    rssi1 = np.linspace(-50, -58, num_scans) + np.random.normal(0,1,num_scans)
    rssi2 = np.linspace(-60, -68, num_scans) + np.random.normal(0,1,num_scans)
    df = pd.DataFrame({'rssi1': rssi1, 'rssi2': rssi2})
    df.to_csv(path, sep=';', index=False)
    return lons, lats

def main():
    try:
     knn_path = "simulation/knn_train_sim.csv"
     fp_path  = "simulation/fp_sim.csv"

    # 1) build toy training set
     generate_knn_train(knn_path)

    # 2) generate only-RSSI scans (we keep the true lons/lats in memory for reference)
     true_lons, true_lats = generate_fp_scans(fp_path, num_scans=20)

    # 3) set origin to first training point
     train = pd.read_csv(knn_path, sep=';')
     set_origin(train.long.iloc[0], train.lat.iloc[0])

    # 4) run fingerprint → local‐coords
     traj_local = fingerprint_with_local_coords(
        knn_path, fp_path, kP=2, kZ=2, R=5.0
    )

    # 5) reconstruct true ground‐truth in local coords
     true_local = np.vstack([
        ll_to_local(lon, lat)
        for lon, lat in zip(true_lons, true_lats)
    ])

    # 6) plot / compare
  
     plt.plot(true_local[:,0],   true_local[:,1],   'k--', label='True Path')
     plt.plot(traj_local[:,0],    traj_local[:,1],    'ro-', label='Fingerprint Est.')
     plt.legend(); plt.axis('equal'); plt.show()
    
    finally:
        for p in (knn_path, fp_path):
            if os.path.exists(p):
                os.remove(p)
                print(f"Temporary file {p} removed.")
        print("🔥 Temporary CSVs removed.")

if __name__ == "__main__":
    main()
