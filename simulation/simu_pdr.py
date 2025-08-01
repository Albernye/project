"""
PDR-Only Simulation
"""
import numpy as np
import matplotlib.pyplot as plt
from algorithms.PDR import pdr_delta

def simulate_imu_movement(duration=10, fs=100):
    time = np.linspace(0, duration, int(duration * fs))

    # Mouvement complexe sur X avec bruit
    accel_x = np.sin(2 * np.pi * 0.5 * time) + np.random.normal(0, 0.2, len(time))
    # Petit mouvement latéral sur Y avec bruit
    accel_y = np.zeros_like(time) + np.random.normal(0, 0.1, len(time))
    # Gravité et mouvement sur Z avec bruit
    accel_z = np.sin(2 * np.pi * 0.5 * time) + 9.8 + np.random.normal(0, 0.2, len(time))

    accel = np.column_stack([accel_x, accel_y, accel_z])

    # Rotation variable avec bruit autour de Z
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
    plt.plot(positions[:, 0], positions[:, 1], 'bo-', label='PDR Estimé')
    plt.plot(true_positions[:, 0], true_positions[:, 1], 'ro-', label='Vrai Mouvement')
    plt.plot(positions[0, 0], positions[0, 1], 'bs', markersize=8, label='Début')
    plt.plot(positions[-1, 0], positions[-1, 1], 'go', markersize=8, label='Fin')
    plt.title('Trajectoire PDR vs Vrai Mouvement')
    plt.xlabel('Position X (m)')
    plt.ylabel('Position Y (m)')
    plt.axis('equal')
    plt.legend()
    plt.grid(True)
    plt.show()

# Simulation
duration = 10  # Durée de la simulation (secondes)
fs = 100       # Fréquence d'échantillonnage (Hz)
accel_sim, gyro_sim, time_sim = simulate_imu_movement(duration, fs)

# Calcul de la trajectoire PDR
positions = run_simulation(accel_sim, gyro_sim, fs)

# "Vrai" mouvement simulé (ici, on utilise une version simplifiée sans bruit pour comparaison)
# Dans un cas réel, vous auriez besoin d'une trajectoire de référence précise.
true_accel = np.column_stack([
    np.sin(2 * np.pi * 0.5 * time_sim),  # Mouvement sur X sans bruit
    np.zeros_like(time_sim),              # Pas de mouvement sur Y
    np.sin(2 * np.pi * 0.5 * time_sim) + 9.8  # Mouvement sur Z sans bruit
])

true_gyro = np.column_stack([
    np.zeros_like(time_sim),
    np.zeros_like(time_sim),
    np.cumsum(np.sin(2 * np.pi * 0.1 * time_sim)) * 0.05  # Rotation sur Z sans bruit
])

true_positions = run_simulation(true_accel, true_gyro, fs)

# Tracer les trajectoires
plot_trajectories(positions, true_positions)

# Calculer l'erreur quadratique moyenne (RMSE)
rmse = np.sqrt(np.mean((positions[1:] - true_positions[1:])**2, axis=0))
print(f"Erreur quadratique moyenne (RMSE): dx={rmse[0]:.2f}, dy={rmse[1]:.2f}")
