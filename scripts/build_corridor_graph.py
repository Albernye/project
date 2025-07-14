' This script builds a corridor graph from room positions and visualizes it using NetworkX and Matplotlib.'
# It reads room positions from a CSV file, calculates distances, and constructs a graph representation.
# The graph is then visualized with nodes representing rooms and corridor points.'

import pandas as pd
import math
import os
import networkx as nx
import matplotlib.pyplot as plt

def euclidean(x1, y1, x2, y2):
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

def build_graph(room_csv_path):
    df = pd.read_csv(room_csv_path)
    rooms = df['room'].tolist()
    xs = df['position_x'].tolist()
    ys = df['position_y'].tolist()
    corridor_y = sum(ys) / len(ys)
    corridor_nodes = []
    for i, x in enumerate(xs):
        corridor_nodes.append((f'couloir-{i+1}', x, corridor_y))
    graph = {}
    for i in range(len(corridor_nodes) - 1):
        n1, x1, y1 = corridor_nodes[i]
        n2, x2, y2 = corridor_nodes[i+1]
        dist = euclidean(x1, y1, x2, y2)
        graph.setdefault(n1, []).append((n2, dist))
        graph.setdefault(n2, []).append((n1, dist))
    for i, room in enumerate(rooms):
        room_x, room_y = xs[i], ys[i]
        corridor_name, cx, cy = corridor_nodes[i]
        dist = euclidean(room_x, room_y, cx, cy)
        graph.setdefault(room, []).append((corridor_name, dist))
        graph.setdefault(corridor_name, []).append((room, dist))
    return graph, rooms, xs, ys, corridor_nodes

if __name__ == "__main__":
   
    csv_path = os.path.join(os.path.dirname(__file__), '../data/room_positions.csv')
    graph, rooms, xs, ys, corridor_nodes = build_graph(csv_path)

    G = nx.Graph()
    pos = {}

    # Ajouter les salles
    for room, x, y in zip(rooms, xs, ys):
        G.add_node(room)
        pos[room] = (x, y)

    # Ajouter les points du couloir
    for name, x, y in corridor_nodes:
        G.add_node(name)
        pos[name] = (x, y)

    # Ajouter les arêtes
    for node, edges in graph.items():
        for neighbor, _ in edges:
            G.add_edge(node, neighbor)

    plt.figure(figsize=(12, 6))
    nx.draw(G, pos, with_labels=True, node_size=400, node_color='skyblue', font_size=8)
    plt.title("Graphe des salles et du couloir central")
    plt.show()