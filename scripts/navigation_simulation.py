"""
Simulation complète du flux de navigation intérieure avec :
- Erreur de PDR
- Correction par fingerprinting WiFi
- Fusion Kalman
- Demande de réinitialisation QR
"""

import numpy as np
import matplotlib.pyplot as plt
from algorithms.fusion import fuse, reset_kalman
from algorithms.pathfinding import load_pathfinder_from_json
from scripts.utils import get_room_position

def simulate_navigation(start_room, end_room):
    # Chargement du graphe de navigation
    pathfinder = load_pathfinder_from_json("data/graph/corridor_graph.json")
    
    # Calcul du chemin optimal
    path_result = pathfinder.find_shortest_path(start_room, end_room)
    if not path_result:
        raise ValueError("Aucun chemin trouvé entre les salles")
    
    path = path_result['path']
    print(f"🛣️ Itinéraire calculé: {' → '.join(path)}")
    
    # Positions réelles des salles
    true_positions = [get_room_position(room) for room in path]
    
    # Simulation de données capteurs
    timesteps = 50
    sigma_pdr_drift = 0.15  # Erreur de dérive du PDR
    sigma_fingerprint = 2.0  # Bruit mesure WiFi
    
    # Initialisation
    reset_kalman()
    current_room_index = 0
    qr_requested = False
    positions = []
    
    plt.figure(figsize=(12, 8))
    
    for step in range(timesteps):
        # Simulation mouvement réel (linéaire entre les salles)
        progress = step / timesteps
        current_room_index = min(int(progress * len(path)), len(path)-1)
        true_pos = np.array(true_positions[current_room_index])
        
        # Génération données PDR bruitées (dx, dy) avec conversion explicite
        pdr_delta = (
            float(true_pos[0] + np.random.normal(0, sigma_pdr_drift)),
            float(true_pos[1] + np.random.normal(0, sigma_pdr_drift)),
            0  # Pas de changement d'étage
        )
        
        # Génération fingerprinting bruité (x, y) avec conversion explicite
        finger_pos = (
            float(true_pos[0] + np.random.normal(0, sigma_fingerprint)),
            float(true_pos[1] + np.random.normal(0, sigma_fingerprint)),
            2  # Étage fixe
        )
        
        # Fusion Kalman avec données formatées
        fused_pos = fuse(pdr_delta, finger_pos, room=path[current_room_index])
        positions.append(fused_pos[:2])
        
        # Détection erreur nécessitant réinitialisation QR
        error = np.linalg.norm(fused_pos[:2] - true_pos)
        if error > 5.0 and not qr_requested:  # Seuil d'erreur
            print(f"🚨 Erreur importante ({error:.1f}m) - Demande réinitialisation QR")
            qr_pos = get_room_position(path[current_room_index])
            fuse(None, None, qr_reset=qr_pos, room=path[current_room_index])
            qr_requested = True
        
        # Visualisation
        color = 'red' if qr_requested else 'blue'
        plt.plot(fused_pos[0], fused_pos[1], 'o', color=color, alpha=0.5)
    
    # Affichage de la trajectoire
    positions = np.array(positions)
    plt.plot(positions[:,0], positions[:,1], 'g--', label='Trajectoire estimée')
    true_positions = np.array(true_positions)
    plt.plot(true_positions[:,0], true_positions[:,1], 'k-', label='Chemin réel')
    
    plt.title("Simulation Navigation 201 → 205\n[PDR ➔ Fingerprint ➔ Kalman ➔ QR Reset]")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.legend()
    plt.grid(True)
    plt.savefig('data/simulation_result.png')
    print("✅ Simulation terminée - Visualisation sauvegardée dans data/simulation_result.png")

if __name__ == "__main__":
    simulate_navigation("2-01", "2-05")
