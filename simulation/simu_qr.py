"""
QR-Only Simulation
"""

import json
import time
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from scripts.utils import write_json_safe, read_json_safe, get_room_position
from algorithms.fingerprint import set_origin, ll_to_local

def simulate_qr_sequence(room_list, interval_s=1.0, temp_json="simulation/qr_sim.json"):
    events = []
    t0 = time.time()
    for i, room in enumerate(room_list):
        lon, lat = get_room_position(room)
        events.append({
            "room": room,
            "timestamp": (t0 + i*interval_s),
            "position": [lon, lat]
        })
    write_json_safe(events, temp_json)
    return Path(temp_json)

def replay_qr(temp_json):
    raw = read_json_safe(temp_json)
    local_pts = []
    for ev in raw:
        lon, lat = ev["position"]
        x,y = ll_to_local(lon, lat)
        local_pts.append((x,y))
    return np.array(local_pts)

def plot_qr(local_pts, rooms):
    plt.figure(figsize=(6,6))
    plt.plot(local_pts[:,0], local_pts[:,1], 'ro-', label="QR-only path")
    for xy, room in zip(local_pts, rooms):
        plt.text(xy[0], xy[1], room, fontsize=9, ha='right')
    plt.title("QR-Only Simulation")
    plt.xlabel("X (m)")
    plt.ylabel("Y (m)")
    plt.axis("equal")
    plt.grid(True)
    plt.legend()
    plt.show()

def main():
    # 1) set origin to your building center
    set_origin(2.192236, 41.406368)
    
    # 2) choose a sequence of rooms
    rooms = ["2-01", "2-02", "2-03", "2-04", "2-05"]
    
    # 3) simulate & save events
    json_path = simulate_qr_sequence(rooms, interval_s=2.0)
    print(f"🔖 QR events JSON: {json_path}")
    
    # 4) replay & collect local positions
    local_pts = replay_qr(json_path)
    print("▶️ Replayed QR local positions:", local_pts)
    
    # 5) plot
    plot_qr(local_pts, rooms)
    
    # 6) cleanup
    json_path.unlink()
    print("🗑️ Removed QR simulation JSON")

if __name__ == "__main__":
    main()
