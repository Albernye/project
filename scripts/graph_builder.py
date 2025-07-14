"""
Graphs builder script for corridor management in a building layout.
This script reads room positions from a CSV file, groups them into corridors,
and builds a graph structure representing the corridors and their connections.
It also saves the graph to a JSON file for later use.
"""

import pandas as pd
import math
import os
import json
from collections import defaultdict

def euclidean(x1, y1, x2, y2):
    """Calcule la distance euclidienne entre deux points."""
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

def group_rooms_by_corridor(rooms_data, y_tolerance=0.001):
    """
    Groupe les salles par couloir basé sur leur position Y.
    
    Args:
        rooms_data: Liste de tuples (room_name, x, y)
        y_tolerance: Tolérance pour considérer deux salles sur le même couloir
    
    Returns:
        Dict avec les couloirs comme clés et les salles comme valeurs
    """
    corridors = defaultdict(list)
    
    # Grouper par Y approximatif
    for room, x, y in rooms_data:
        # Arrondir Y pour gérer les petites variations
        corridor_key = round(y, 3)
        corridors[corridor_key].append((room, x, y))
    
    # Trier chaque couloir par position X
    for corridor_key in corridors:
        corridors[corridor_key].sort(key=lambda item: item[1])
    
    return corridors

def create_corridor_nodes(corridors):
    """
    Crée les points de couloir pour chaque groupe de salles.
    
    Args:
        corridors: Dict des couloirs groupés
    
    Returns:
        Dict des points de couloir avec leurs coordonnées
    """
    corridor_nodes = {}
    
    for corridor_id, (corridor_key, rooms) in enumerate(corridors.items()):
        corridor_name = f"couloir-{corridor_id + 1}"
        
        # Calculer les points de couloir
        corridor_points = []
        for i, (room, x, y) in enumerate(rooms):
            point_name = f"{corridor_name}-point-{i + 1}"
            corridor_points.append((point_name, x, corridor_key))
        
        corridor_nodes[corridor_name] = {
            'points': corridor_points,
            'rooms': rooms,
            'y_level': corridor_key
        }
    
    return corridor_nodes

def connect_nearby_rooms(graph, room_positions, max_distance=0.01):
    """
    Connecte directement les salles qui sont très proches les unes des autres.
    
    Args:
        graph: Graphe existant
        room_positions: Positions des salles
        max_distance: Distance maximale pour considérer deux salles comme adjacentes
    """
    rooms = list(room_positions.keys())
    
    for i, room1 in enumerate(rooms):
        for j, room2 in enumerate(rooms[i+1:], i+1):
            x1, y1 = room_positions[room1]
            x2, y2 = room_positions[room2]
            
            dist = euclidean(x1, y1, x2, y2)
            
            # Si les salles sont très proches, les connecter directement
            if dist <= max_distance:
                graph[room1].append((room2, dist))
                graph[room2].append((room1, dist))
                print(f"Connexion directe ajoutée: {room1} ↔ {room2} ({dist:.4f}m)")

def build_graph(room_csv_path):
    """
    Construit le graphe des couloirs à partir d'un fichier CSV.
    
    Args:
        room_csv_path: Chemin vers le fichier CSV des positions des salles
    
    Returns:
        Tuple (graph, room_positions, corridor_structure)
    """
    # Lire les données
    df = pd.read_csv(room_csv_path)
    rooms_data = [(row['room'], row['position_x'], row['position_y']) 
                  for _, row in df.iterrows()]
    
    # Grouper par couloir
    corridors = group_rooms_by_corridor(rooms_data)
    corridor_structure = create_corridor_nodes(corridors)
    
    # Construire le graphe
    graph = defaultdict(list)
    room_positions = {}
    
    # Ajouter les connexions dans chaque couloir
    for corridor_name, corridor_info in corridor_structure.items():
        points = corridor_info['points']
        rooms = corridor_info['rooms']
        
        # Connecter les points de couloir entre eux
        for i in range(len(points) - 1):
            point1_name, x1, y1 = points[i]
            point2_name, x2, y2 = points[i + 1]
            
            dist = euclidean(x1, y1, x2, y2)
            graph[point1_name].append((point2_name, dist))
            graph[point2_name].append((point1_name, dist))
        
        # Connecter chaque salle à son point de couloir correspondant
        for i, (room, room_x, room_y) in enumerate(rooms):
            point_name, corridor_x, corridor_y = points[i]
            
            # Distance de la salle au point de couloir
            dist = euclidean(room_x, room_y, corridor_x, corridor_y)
            graph[room].append((point_name, dist))
            graph[point_name].append((room, dist))
            
            # Stocker la position de la salle
            room_positions[room] = (room_x, room_y)
    
    # Connecter les salles très proches directement (comme 2-19 et 2-20)
    connect_nearby_rooms(graph, room_positions, max_distance=0.01)
    
    return dict(graph), room_positions, corridor_structure

def save_graph_to_json(graph, room_positions, corridor_structure, output_path):
    """
    Sauvegarde le graphe dans un fichier JSON pour réutilisation.
    
    Args:
        graph: Le graphe construit
        room_positions: Positions des salles
        corridor_structure: Structure des couloirs
        output_path: Chemin de sauvegarde
    """
    data = {
        'graph': graph,
        'room_positions': room_positions,
        'corridor_structure': corridor_structure
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_graph_from_json(json_path):
    """
    Charge un graphe depuis un fichier JSON.
    
    Args:
        json_path: Chemin vers le fichier JSON
    
    Returns:
        Tuple (graph, room_positions, corridor_structure)
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data['graph'], data['room_positions'], data['corridor_structure']

if __name__ == "__main__":
    # Chemin vers le fichier CSV
    csv_path = os.path.join(os.path.dirname(__file__), '../data/room_positions.csv')
    
    # Construire le graphe
    graph, room_positions, corridor_structure = build_graph(csv_path)
    
    # Afficher les informations
    print("Graphe construit avec succès!")
    print(f"Nombre de nœuds: {len(graph)}")
    print(f"Nombre de salles: {len(room_positions)}")
    print(f"Nombre de couloirs: {len(corridor_structure)}")
    
    # Afficher la structure des couloirs
    for corridor_name, info in corridor_structure.items():
        print(f"\n{corridor_name}:")
        print(f"  Niveau Y: {info['y_level']}")
        print(f"  Nombre de salles: {len(info['rooms'])}")
        print(f"  Salles: {[room[0] for room in info['rooms']]}")
    
    # Sauvegarder le graphe
    output_path = os.path.join(os.path.dirname(__file__), '../data/corridor_graph.json')
    save_graph_to_json(graph, room_positions, corridor_structure, output_path)
    print(f"\nGraphe sauvegardé dans: {output_path}")
