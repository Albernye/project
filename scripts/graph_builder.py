"""
Builder for corridor graphs.
This module reads room positions from a CSV and builds a graph
representing the topology of a building's corridors.
"""

import pandas as pd
import math
import os
import json
import sys
from collections import defaultdict

def euclidean(x1, y1, x2, y2):
    """Calculate the Euclidean distance between two points."""
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

def group_rooms_by_corridor(rooms_data, y_tolerance=0.001):
    """
    Group rooms by corridor based on their Y position.
    
    Args:
        rooms_data: List of tuples (room_name, x, y)
        y_tolerance: Tolerance for considering two rooms on the same corridor

    Returns:
        Dict with corridors as keys and rooms as values
    """
    corridors = defaultdict(list)

    # Group by approximate Y
    for room, x, y in rooms_data:
        # Round Y to handle small variations
        corridor_key = round(y, 3)
        corridors[corridor_key].append((room, x, y))

    # Sort each corridor by X position
    for corridor_key in corridors:
        corridors[corridor_key].sort(key=lambda item: item[1])
    
    return corridors

def create_corridor_nodes(corridors):
    """
    Create corridor nodes from grouped rooms.
    
    Args:
        corridors: Dict of grouped corridors

    Returns:
        Dict of corridor points with their coordinates
    """
    corridor_nodes = {}
    
    for corridor_id, (corridor_key, rooms) in enumerate(corridors.items()):
        corridor_name = f"couloir-{corridor_id + 1}"

        # Calculate corridor points
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
    Connect directly adjacent rooms that are very close to each other.

    Args:
        graph: Existing graph
        room_positions: Positions of the rooms
        max_distance: Maximum distance to consider two rooms as adjacent
    """
    rooms = list(room_positions.keys())
    
    for i, room1 in enumerate(rooms):
        for j, room2 in enumerate(rooms[i+1:], i+1):
            x1, y1 = room_positions[room1]
            x2, y2 = room_positions[room2]
            
            dist = euclidean(x1, y1, x2, y2)

            # If rooms are very close, connect them directly
            if dist <= max_distance:
                graph[room1].append((room2, dist))
                graph[room2].append((room1, dist))
                print(f"Direct connection added: {room1} ↔ {room2} ({dist:.4f}m)")

def build_graph(room_csv_path):
    """
    Build the corridor graph from a CSV file.

    Args:
        room_csv_path: Path to the CSV file containing room positions

    Returns:
        Tuple (graph, room_positions, corridor_structure)
    """
    # Read the data
    df = pd.read_csv(room_csv_path)
    rooms_data = [(row['room'], row['position_x'], row['position_y']) 
                  for _, row in df.iterrows()]

    # Group by corridor
    corridors = group_rooms_by_corridor(rooms_data)
    corridor_structure = create_corridor_nodes(corridors)

    # Build the graph
    graph = defaultdict(list)
    room_positions = {}

    # Add connections within each corridor
    for corridor_name, corridor_info in corridor_structure.items():
        points = corridor_info['points']
        rooms = corridor_info['rooms']

        # Connect corridor points to each other
        for i in range(len(points) - 1):
            point1_name, x1, y1 = points[i]
            point2_name, x2, y2 = points[i + 1]
            
            dist = euclidean(x1, y1, x2, y2)
            graph[point1_name].append((point2_name, dist))
            graph[point2_name].append((point1_name, dist))

        # Connect each room to its corresponding corridor point
        for i, (room, room_x, room_y) in enumerate(rooms):
            point_name, corridor_x, corridor_y = points[i]

            # Distance from the room to the corridor point
            dist = euclidean(room_x, room_y, corridor_x, corridor_y)
            graph[room].append((point_name, dist))
            graph[point_name].append((room, dist))

            # Store the position of the room
            room_positions[room] = (room_x, room_y)

    # Connect very close rooms directly (like 2-19 and 2-20)
    connect_nearby_rooms(graph, room_positions, max_distance=0.01)
    
    return dict(graph), room_positions, corridor_structure

def save_graph_to_json(graph, room_positions, corridor_structure, output_path):
    """
    Save the graph to a JSON file for reuse.

    Args:
        graph: The constructed graph
        room_positions: Positions of the rooms
        corridor_structure: Structure of the corridors
        output_path: Path to the output file
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
    Load a graph from a JSON file.

    Args:
        json_path: Path to the JSON file

    Returns:
        Tuple (graph, room_positions, corridor_structure)
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data['graph'], data['room_positions'], data['corridor_structure']

if __name__ == "__main__":
    # Paths to the CSV files (multiple possibilities)
    possible_csv_paths = [
        os.path.join(os.path.dirname(__file__), '../data/room_positions.csv'),
        os.path.join(os.getcwd(), 'data/room_positions.csv'),
        'data/room_positions.csv',
        '../data/room_positions.csv'
    ]
    
    csv_path = None
    for path in possible_csv_paths:
        if os.path.exists(path):
            csv_path = path
            break
    
    if csv_path is None:
        print("❌ File room_positions.csv not found in the following locations:")
        for path in possible_csv_paths:
            print(f"  - {os.path.abspath(path)}")
        print("\nPlease create the CSV file with the room positions first.")
        sys.exit(1)

    print(f"📁 Using CSV file: {os.path.abspath(csv_path)}")

    # Build the graph
    graph, room_positions, corridor_structure = build_graph(csv_path)

    # Display the information
    print("Graph built successfully!")
    print(f"Number of nodes: {len(graph)}")
    print(f"Number of rooms: {len(room_positions)}")
    print(f"Number of corridors: {len(corridor_structure)}")

    # Display the corridor structure
    for corridor_name, info in corridor_structure.items():
        print(f"\n{corridor_name}:")
        print(f"  Y Level: {info['y_level']}")
        print(f"  Number of Rooms: {len(info['rooms'])}")
        print(f"  Rooms: {[room[0] for room in info['rooms']]}")

    # Determine the output path
    output_dir = os.path.dirname(csv_path)
    output_path = os.path.join(output_dir, 'corridor_graph.json')

    # Save the graph
    save_graph_to_json(graph, room_positions, corridor_structure, output_path)
    print(f"\n✅ Graph saved to: {os.path.abspath(output_path)}")