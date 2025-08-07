"""
Algorithms for pathfinding in corridor graphs.
This module contains the implementation of Dijkstra and other optimal
pathfinding algorithms.
"""

import heapq
import json
from typing import Dict, List, Tuple, Optional

class PathFinder:
    """Class for pathfinding algorithms."""
    
    def __init__(self, graph: Dict[str, List[Tuple[str, float]]]):
        """
        Initialize the PathFinder with a graph.
        
        Args:
            graph: Dictionary representing the graph
                   {node: [(neighbor, weight), ...]}
        """
        self.graph = graph
    
    def dijkstra(self, start: str, end: str) -> Tuple[float, List[str]]:
        """
        Implementation of Dijkstra's algorithm.

        Args:
            start: Starting node
            end: Target node
        
        Returns:
            Tuple (distance, path)

        Raises:
            KeyError: If a node does not exist in the graph
        """
        if start not in self.graph:
            raise KeyError(f"Starting node '{start}' not found in the graph")
        if end not in self.graph:
            raise KeyError(f"Target node '{end}' not found in the graph")

        # Initialization
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

            # If we reached the target
            if current_node == end:
                break

            # Examine the neighbors
            for neighbor, weight in self.graph[current_node]:
                if neighbor in visited:
                    continue
                
                distance = current_distance + weight
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    predecessors[neighbor] = current_node
                    heapq.heappush(priority_queue, (distance, neighbor))
        
        # Rebuild the path
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
        Find the shortest path between two nodes.

        Args:
            start: Starting node
            end: Target node

        Returns:
            Dict containing the distance, path, and metadata
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
        Find all paths from a given node.

        Args:
            start: Starting node
            max_distance: Maximum distance to consider

        Returns:
            Dict {destination: {'distance': float, 'path': List[str]}}
        """
        if start not in self.graph:
            raise KeyError(f"Starting node '{start}' not found in the graph")
        
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

        # Rebuild all paths
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
    Load a PathFinder from a JSON file.

    Args:
        json_path: Path to the graph's JSON file

    Returns:
        Instance of PathFinder
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return PathFinder(data['graph'])

if __name__ == "__main__":
    import os
    import sys

    # Load the graph from JSON (multiple possibilities)
    possible_paths = [
        os.path.join(os.path.dirname(__file__), '../data/graph/corridor_graph.json'),
        os.path.join(os.getcwd(), 'data/graph/corridor_graph.json'),
        'data/graph/corridor_graph.json',
        '../data/graph/corridor_graph.json'
    ]
    
    json_path = None
    for path in possible_paths:
        if os.path.exists(path):
            json_path = path
            break
    
    if json_path is None:
        print("❌ File corridor_graph.json not found in the following locations:")
        for path in possible_paths:
            print(f"  - {os.path.abspath(path)}")
        print("\nPlease run graph_builder.py first to create the graph.")
        sys.exit(1)

    print(f"📁 Using file: {os.path.abspath(json_path)}")

    try:
        pathfinder = load_pathfinder_from_json(json_path)

        # Example usage
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        rooms = list(data['room_positions'].keys())
        
        if len(rooms) >= 2:
            start_room = rooms[0]
            end_room = rooms[-1]

            print(f"Searching for path between {start_room} and {end_room}")

            result = pathfinder.find_shortest_path(start_room, end_room)
            
            if result:
                print(f"Distance: {result['distance']:.2f}m")
                print(f"Path: {' -> '.join(result['path'])}")
                print(f"Number of nodes: {result['nodes_count']}")
            else:
                print("No path found")

        # Example: all paths from the first room
        if rooms:
            first_room = rooms[0]
            print(f"\nAll paths from {first_room}:")

            all_paths = pathfinder.find_all_paths_from_node(first_room, max_distance=100)
            
            for destination, info in sorted(all_paths.items(), key=lambda x: x[1]['distance']):
                print(f"  -> {destination}: {info['distance']:.2f}m")
    
    except FileNotFoundError:
        print(f"File not found: {json_path}")
        print("Please run graph_builder.py first to create the graph.")
    except Exception as e:
        print(f"Error: {e}")
