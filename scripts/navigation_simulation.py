import numpy as np
import matplotlib.pyplot as plt
from algorithms.PDR import pdr_delta

def simulate_movement(duration=10, fs=100):
    """
    Simule des données d'accéléromètre et de gyroscope.

    Args:
        duration (float): Durée de la simulation en secondes.
        fs (float): Fréquence d'échantillonnage en Hz.

    Returns:
        accel: Données simulées de l'accéléromètre.
        gyro: Données simulées du gyroscope.
        time: Temps associé aux données.
    """
    time = np.linspace(0, duration, int(duration * fs))

    # Simuler des mouvements sinusoïdaux pour chaque axe de l'accéléromètre
    accel = np.column_stack([
        np.sin(2 * np.pi * 0.5 * time),  # Mouvement périodique sur l'axe X
        np.zeros_like(time),              # Pas de mouvement sur l'axe Y
        np.sin(2 * np.pi * 0.5 * time) + 9.8  # Ajout de la gravité sur l'axe Z
    ])

    # Simuler une rotation variable pour le gyroscope pour un changement de direction réaliste
    gyro_z = np.linspace(0, 2 * np.pi, len(time))  # Rotation variable pour simuler un changement de direction
    gyro = np.column_stack([
        np.zeros_like(time),  # Pas de rotation autour de l'axe X
        np.zeros_like(time),  # Pas de rotation autour de l'axe Y
        np.sin(gyro_z) * 0.1  # Rotation variable autour de l'axe Z
    ])

    return accel, gyro, time

def run_simulation(accel, gyro, fs):
    """
    Exécuter la simulation PDR avec les données simulées.

    Args:
        accel: Données de l'accéléromètre.
        gyro: Données du gyroscope.
        fs (float): Fréquence d'échantillonnage en Hz.

    Returns:
        positions: Positions calculées (trajectoire).
    """
    dx, dy = pdr_delta(accel, gyro, fs)

    # Calculer la trajectoire totale en cumulant les deltas
    positions = np.cumsum(np.column_stack((dx, dy)), axis=0)

    # Ajouter la position initiale
    positions = np.vstack((np.array([0, 0]), positions))
    return positions

def plot_trajectory(positions):
    """
    Tracer la trajectoire simulée.

    Args:
        positions: Positions (trajectoire) à tracer.
    """
    plt.figure(figsize=(8, 6))
    plt.plot(positions[:, 0], positions[:, 1], 'bo-', label='Trajectoire')
    plt.plot(positions[0, 0], positions[0, 1], 'bs', markersize=8, label='Début')
    plt.plot(positions[-1, 0], positions[-1, 1], 'go', markersize=8, label='Fin')
    plt.title('Simulation de la trajectoire PDR')
    plt.xlabel('Position X (m)')
    plt.ylabel('Position Y (m)')
    plt.axis('equal')
    plt.legend()
    plt.grid(True)
    plt.show()

# Exécutez la simulation
duration = 10  # Durée de la simulation (secondes)
fs = 100       # Fréquence d'échantillonnage (Hz)

accel_sim, gyro_sim, time_sim = simulate_movement(duration, fs)
positions = run_simulation(accel_sim, gyro_sim, fs)
plot_trajectory(positions)
