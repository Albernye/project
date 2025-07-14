"""
Algorithmes de recherche de chemin pour les graphes de couloirs.
Ce module contient l'implémentation de Dijkstra et d'autres algorithmes
de recherche de chemin optimaux.
"""

import heapq
import json
from typing import Dict, List, Tuple, Optional

class PathFinder:
    """Classe pour les algorithmes de recherche de chemin."""
    
    def __init__(self, graph: Dict[str, List[Tuple[str, float]]]):
        """
        Initialise le PathFinder avec un graphe.
        
        Args:
            graph: Dictionnaire représentant le graphe
                  {node: [(neighbor, weight), ...]}
        """
        self.graph = graph
    
    def dijkstra(self, start: str, end: str) -> Tuple[float, List[str]]:
        """
        Implémentation de l'algorithme de Dijkstra.
        
        Args:
            start: Nœud de départ
            end: Nœud d'arrivée
        
        Returns:
            Tuple (distance, chemin)
        
        Raises:
            KeyError: Si un nœud n'existe pas dans le graphe
        """
        if start not in self.graph:
            raise KeyError(f"Nœud de départ '{start}' introuvable dans le graphe")
        if end not in self.graph:
            raise KeyError(f"Nœud d'arrivée '{end}' introuvable dans le graphe")
        
        # Initialisation
        distances = {node: float('inf') for node in self.graph}
        distances[start] = 0
        priority_queue = [(0, start)]
        predecessors = {}
        visited = set()
        
        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)
            
            if current_node in visited:
                continue
            
            visited.add(current_node)
            
            # Si on atteint la destination
            if current_node == end:
                break
            
            # Examiner les voisins
            for neighbor, weight in self.graph[current_node]:
                if neighbor in visited:
                    continue
                
                distance = current_distance + weight
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    predecessors[neighbor] = current_node
                    heapq.heappush(priority_queue, (distance, neighbor))
        
        # Reconstruction du chemin
        if end not in predecessors and start != end:
            return float('inf'), []
        
        path = []
        current = end
        while current is not None:
            path.insert(0, current)
            current = predecessors.get(current)
        
        return distances[end], path
    
    def find_shortest_path(self, start: str, end: str) -> Optional[Dict]:
        """
        Trouve le chemin le plus court entre deux nœuds.
        
        Args:
            start: Nœud de départ
            end: Nœud d'arrivée
        
        Returns:
            Dict contenant la distance, le chemin et les métadonnées
        """
        try:
            distance, path = self.dijkstra(start, end)
            
            if not path:
                return None
            
            return {
                'distance': distance,
                'path': path,
                'start': start,
                'end': end,
                'nodes_count': len(path),
                'edges_count': len(path) - 1
            }
        
        except KeyError as e:
            print(f"Erreur: {e}")
            return None
    
    def find_all_paths_from_node(self, start: str, max_distance: float = float('inf')) -> Dict:
        """
        Trouve tous les chemins depuis un nœud donné.
        
        Args:
            start: Nœud de départ
            max_distance: Distance maximale à considérer
        
        Returns:
            Dict {destination: {'distance': float, 'path': List[str]}}
        """
        if start not in self.graph:
            raise KeyError(f"Nœud de départ '{start}' introuvable dans le graphe")
        
        distances = {node: float('inf') for node in self.graph}
        distances[start] = 0
        priority_queue = [(0, start)]
        predecessors = {}
        paths = {}
        
        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)
            
            if current_distance > distances[current_node]:
                continue
            
            if current_distance > max_distance:
                continue
            
            for neighbor, weight in self.graph[current_node]:
                distance = current_distance + weight
                if distance < distances[neighbor] and distance <= max_distance:
                    distances[neighbor] = distance
                    predecessors[neighbor] = current_node
                    heapq.heappush(priority_queue, (distance, neighbor))
        
        # Reconstruire tous les chemins
        for end_node in self.graph:
            if end_node != start and distances[end_node] != float('inf'):
                path = []
                current = end_node
                while current is not None:
                    path.insert(0, current)
                    current = predecessors.get(current)
                
                paths[end_node] = {
                    'distance': distances[end_node],
                    'path': path
                }
        
        return paths

def load_pathfinder_from_json(json_path: str) -> PathFinder:
    """
    Charge un PathFinder depuis un fichier JSON.
    
    Args:
        json_path: Chemin vers le fichier JSON du graphe
    
    Returns:
        Instance de PathFinder
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return PathFinder(data['graph'])

if __name__ == "__main__":
    import os
    
    # Charger le graphe depuis le JSON
    json_path = os.path.join(os.path.dirname(__file__), '../data/corridor_graph.json')
    
    try:
        pathfinder = load_pathfinder_from_json(json_path)
        
        # Exemple d'utilisation
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        rooms = list(data['room_positions'].keys())
        
        if len(rooms) >= 2:
            start_room = rooms[0]
            end_room = rooms[-1]
            
            print(f"Recherche du chemin entre {start_room} et {end_room}")
            
            result = pathfinder.find_shortest_path(start_room, end_room)
            
            if result:
                print(f"Distance: {result['distance']:.2f}m")
                print(f"Chemin: {' -> '.join(result['path'])}")
                print(f"Nombre de nœuds: {result['nodes_count']}")
            else:
                print("Aucun chemin trouvé")
        
        # Exemple: tous les chemins depuis la première salle
        if rooms:
            first_room = rooms[0]
            print(f"\nTous les chemins depuis {first_room}:")
            
            all_paths = pathfinder.find_all_paths_from_node(first_room, max_distance=100)
            
            for destination, info in sorted(all_paths.items(), key=lambda x: x[1]['distance']):
                print(f"  -> {destination}: {info['distance']:.2f}m")
    
    except FileNotFoundError:
        print(f"Fichier non trouvé: {json_path}")
        print("Exécutez d'abord graph_builder.py pour créer le graphe.")
    except Exception as e:
        print(f"Erreur: {e}")
