"""
PDR-Only Simulation with Monte Carlo RMSE Analysis
"""
import numpy as np
import matplotlib.pyplot as plt
from algorithms.PDR import pdr_delta

def simulate_imu_movement(duration=10, fs=100):
    time = np.linspace(0, duration, int(duration * fs))

    accel_x = np.sin(2 * np.pi * 0.5 * time) + np.random.normal(0, 0.2, len(time))
    accel_y = np.zeros_like(time) + np.random.normal(0, 0.1, len(time))
    accel_z = np.sin(2 * np.pi * 0.5 * time) + 9.8 + np.random.normal(0, 0.2, len(time))
    accel = np.column_stack([accel_x, accel_y, accel_z])

    gyro_z = np.cumsum(np.sin(2 * np.pi * 0.1 * time) + np.random.normal(0, 0.05, len(time))) * 0.05
    gyro = np.column_stack([np.zeros_like(time), np.zeros_like(time), gyro_z])

    return accel, gyro, time

def run_simulation(accel, gyro, fs):
    dx, dy = pdr_delta(accel, gyro, fs)
    positions = np.cumsum(np.column_stack((dx, dy)), axis=0)
    positions = np.vstack((np.array([0, 0]), positions))
    return positions

def true_trajectory(time, fs):
    accel = np.column_stack([
        np.sin(2 * np.pi * 0.5 * time),
        np.zeros_like(time),
        np.sin(2 * np.pi * 0.5 * time) + 9.8
    ])
    gyro = np.column_stack([
        np.zeros_like(time),
        np.zeros_like(time),
        np.cumsum(np.sin(2 * np.pi * 0.1 * time)) * 0.05
    ])
    return run_simulation(accel, gyro, fs)

def monte_carlo_rmse(n_runs=50, duration=10, fs=100):
    time = np.linspace(0, duration, int(duration * fs))
    true_positions = true_trajectory(time, fs)

    rmses = []
    for i in range(n_runs):
        accel_sim, gyro_sim, _ = simulate_imu_movement(duration, fs)
        est_positions = run_simulation(accel_sim, gyro_sim, fs)

        rmse = np.sqrt(np.mean((est_positions[1:] - true_positions[1:])**2, axis=0))
        total_rmse = np.linalg.norm(rmse)
        rmses.append(total_rmse)

    rmses = np.array(rmses)
    return rmses

if __name__ == "__main__":
    runs = 100
    rmses = monte_carlo_rmse(runs)

    print(f"Mean RMSE over {runs} runs: {rmses.mean():.3f} m")
    print(f"Std RMSE: {rmses.std():.3f} m")
    print(f"Min RMSE: {rmses.min():.3f} m, Max RMSE: {rmses.max():.3f} m")

    # Plot distribution
    plt.figure(figsize=(8, 5))
    plt.hist(rmses, bins=15, edgecolor='k', alpha=0.7)
    plt.axvline(rmses.mean(), color='r', linestyle='--', label=f"Mean = {rmses.mean():.3f} m")
    plt.title("Distribution of RMSE (Monte Carlo PDR Simulation)")
    plt.xlabel("RMSE (m)")
    plt.ylabel("Frequency")
    plt.legend()
    plt.grid(True)
    plt.show()
