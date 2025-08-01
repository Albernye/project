"""
QR-Only from json simulation
"""

import json
import matplotlib.pyplot as plt
from pathlib import Path

from algorithms.fingerprint import set_origin, ll_to_local
from scripts.utils import read_json_safe, cfg

def run_qr_simulation(qr_json_path: str,
                      origin_lon: float,
                      origin_lat: float):
    # 1) Initialize local origin
    set_origin(origin_lon, origin_lat)

    # 2) Load QR events
    events = read_json_safe(Path(qr_json_path))
    if not events:
        print("⚠️ No QR events found in", qr_json_path)
        return

    # 3) Extract and convert positions
    xs, ys = [], []
    for ev in events:
        pos = ev.get("position")
        if isinstance(pos, (list, tuple)) and len(pos) >= 2:
            lon, lat = float(pos[0]), float(pos[1])
            x, y = ll_to_local(lon, lat)
            xs.append(x)
            ys.append(y)
        else:
            print(f"⚠️ Skipping invalid QR event: {ev}")

    if not xs:
        print("⚠️ No valid positions to plot.")
        return
    
    # 4) Plot
    plt.figure(figsize=(6,6))
    plt.plot(xs, ys, 's-', label='QR resets')
    plt.scatter(xs[0], ys[0], c='green', marker='o', label='First reset')
    plt.scatter(xs[-1], ys[-1], c='red', marker='x', label='Last reset')
    plt.title("QR‐only Simulation")
    plt.xlabel("X (m) relative to origin")
    plt.ylabel("Y (m) relative to origin")
    plt.legend()
    plt.axis('equal')
    plt.grid(True)
    plt.show()

def main():
    qr_path = str(cfg.QR_EVENTS)
    run_qr_simulation(qr_path,
                      origin_lon=cfg.DEFAULT_POSXY[0],
                      origin_lat=cfg.DEFAULT_POSXY[1])

if __name__ == "__main__":
    main()
