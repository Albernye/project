"""
PDR-Only Simulation
"""
import numpy as np
import matplotlib.pyplot as plt
from algorithms.PDR import pdr_delta

def simulate_imu_movement(duration=10, fs=100):
    time = np.linspace(0, duration, int(duration * fs))

    # Complex movement simulation
    accel_x = np.sin(2 * np.pi * 0.5 * time) + np.random.normal(0, 0.2, len(time))
    # Small lateral movement on Y with noise
    accel_y = np.zeros_like(time) + np.random.normal(0, 0.1, len(time))
    # Gravity and movement on Z with noise
    accel_z = np.sin(2 * np.pi * 0.5 * time) + 9.8 + np.random.normal(0, 0.2, len(time))

    accel = np.column_stack([accel_x, accel_y, accel_z])

    # Rotation variable with noise around Z
    gyro_z = np.cumsum(np.sin(2 * np.pi * 0.1 * time) + np.random.normal(0, 0.05, len(time))) * 0.05
    gyro = np.column_stack([
        np.zeros_like(time),
        np.zeros_like(time),
        gyro_z
    ])

    return accel, gyro, time

def run_simulation(accel, gyro, fs):
    dx, dy = pdr_delta(accel, gyro, fs)
    positions = np.cumsum(np.column_stack((dx, dy)), axis=0)
    positions = np.vstack((np.array([0, 0]), positions))
    return positions

def plot_trajectories(positions, true_positions):
    plt.figure(figsize=(8, 6))
    plt.plot(positions[:, 0], positions[:, 1], 'bo-', label='Estimated PDR Trajectory')
    plt.plot(true_positions[:, 0], true_positions[:, 1], 'ro-', label='True Movement')
    plt.plot(positions[0, 0], positions[0, 1], 'bs', markersize=8, label='Start')
    plt.plot(positions[-1, 0], positions[-1, 1], 'go', markersize=8, label='End')
    plt.title('PDR Trajectory vs True Movement')
    plt.xlabel('Position X (m)')
    plt.ylabel('Position Y (m)')
    plt.axis('equal')
    plt.legend()
    plt.grid(True)
    plt.show()

# Simulation
duration = 10  # Duration of the simulation (seconds)
fs = 100       # Frequency of sampling (Hz)
accel_sim, gyro_sim, time_sim = simulate_imu_movement(duration, fs)

# Calculate PDR trajectory
positions = run_simulation(accel_sim, gyro_sim, fs)

# "True" simulated movement (here, we use a simplified version without noise for comparison)
# In a real case, you would need an accurate reference trajectory.
true_accel = np.column_stack([
    np.sin(2 * np.pi * 0.5 * time_sim),  # Movement on X without noise
    np.zeros_like(time_sim),              # No movement on Y
    np.sin(2 * np.pi * 0.5 * time_sim) + 9.8  # Movement on Z without noise
])

true_gyro = np.column_stack([
    np.zeros_like(time_sim),
    np.zeros_like(time_sim),
    np.cumsum(np.sin(2 * np.pi * 0.1 * time_sim)) * 0.05  # Rotation on Z without noise
])

true_positions = run_simulation(true_accel, true_gyro, fs)

# Draw the trajectories
# plot_trajectories(positions, true_positions)
# plt.figure(figsize=(8, 6))
# plt.plot(positions[:, 0], positions[:, 1], 'bo-', label='Estimated PDR Trajectory')
# plt.plot(true_positions[:, 0], true_positions[:, 1], 'ro-', label='True Movement')
# plt.plot(positions[0, 0], positions[0, 1], 'bs', markersize=8, label='Start')
# plt.plot(positions[-1, 0], positions[-1, 1], 'go', markersize=8, label='End')
# plt.title('PDR Trajectory vs True Movement')
# plt.xlabel('Position X (m)')
# plt.ylabel('Position Y (m)')
# plt.axis('equal')
# plt.legend()
# plt.grid(True)
# plt.show()

# Calculate RMSE
rmse = np.sqrt(np.mean((positions[1:] - true_positions[1:])**2, axis=0))
# print('RMSE:', rmse)
