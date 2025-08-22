"""
PDR-Only from csv simulation
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from algorithms.fingerprint import set_origin, local_to_ll
from algorithms.PDR import (
    step_detection_accelerometer,
    weiberg_stride_length_heading_position
)

def run_pdr_simulation(merged_csv_path: str):
    # 1) Load the merged CSV
    df = pd.read_csv(merged_csv_path)
    accel = df[['ACCE_X','ACCE_Y','ACCE_Z']].values
    gyro  = df[['GYRO_X','GYRO_Y','GYRO_Z']].values
    times = df['timestamp'].values
    fs    = 1.0 / np.mean(np.diff(times))

    # 2) Detect steps once
    magnitude = np.linalg.norm(accel, axis=1)
    t = np.arange(len(magnitude)) / fs
    num_steps, step_indices, stance = step_detection_accelerometer(
        magnitude, t, plot=False
    )

    print(f"Detected {num_steps} steps at indices {step_indices[:5]}...")

    # 3) Compute entire PDR trajectory once
    thetas, positions = weiberg_stride_length_heading_position(
        accel, gyro, t, step_indices, stance, ver=False, idx_fig=0
    )
    
    # 4) Plot the trajectory
    x0, y0 = 2.175568, 41.406368  
    pos = positions + np.array([x0, y0])
    set_origin(x0, y0)
    end_pos = local_to_ll(pos[-1, 0], pos[-1, 1])

    print(f"Final estimated position: ({end_pos[0]:.6f}, {end_pos[1]:.6f})")
    plt.figure(figsize=(6,6))
    plt.plot(pos[:,0], pos[:,1], '-o', markersize=4, label='PDR Estimated')
    plt.plot(pos[0,0], pos[0,1], 'ks', label='Start')
    plt.plot(pos[-1,0], pos[-1,1], 'k*', label='End')
    plt.title("PDR-Only Trajectory from current.csv")
    plt.xlabel("X (m)")
    plt.ylabel("Y (m)")
    plt.axis('equal')
    plt.grid(True)
    plt.legend()
    plt.show()

if __name__ == "__main__":
    run_pdr_simulation("data/pdr_traces/current.csv")
