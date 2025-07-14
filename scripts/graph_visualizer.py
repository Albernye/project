"""
Visualiseur de graphe de couloirs.
Ce module permet de visualiser le graphe construit et les chemins trouvés.
"""

import json
import matplotlib.pyplot as plt
import networkx as nx
from typing import Dict, List, Optional, Tuple
import os

class GraphVisualizer:
    """Classe pour visualiser les graphes de couloirs."""
    
    def __init__(self, graph_data_path: str):
        """
        Initialise le visualiseur avec les données du graphe.
        
        Args:
            graph_data_path: Chemin vers le fichier JSON du graphe
        """
        with open(graph_data_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        self.graph = self.data['graph']
        self.room_positions = self.data['room_positions']
        self.corridor_structure = self.data['corridor_structure']
        
        # Créer le graphe NetworkX
        self.nx_graph = nx.Graph()
        self.pos = {}
        
        self._build_networkx_graph()
    
    def _build_networkx_graph(self):
        """Construit le graphe NetworkX pour la visualisation."""
        # Ajouter les salles
        for room, (x, y) in self.room_positions.items():
            self.nx_graph.add_node(room, node_type='room')
            self.pos[room] = (x, y)
        
        # Ajouter les points de couloir
        for corridor_name, corridor_info in self.corridor_structure.items():
            for point_name, x, y in corridor_info['points']:
                self.nx_graph.add_node(point_name, node_type='corridor')
                self.pos[point_name] = (x, y)
        
        # Ajouter les arêtes
        for node, neighbors in self.graph.items():
            for neighbor, weight in neighbors:
                self.nx_graph.add_edge(node, neighbor, weight=weight)
    
    def visualize_graph(self, figsize=(15, 10), save_path=None):
        """
        Visualise le graphe complet.
        
        Args:
            figsize: Taille de la figure
            save_path: Chemin de sauvegarde (optionnel)
        """
        plt.figure(figsize=figsize)
        
        # Séparer les types de nœuds
        room_nodes = [n for n in self.nx_graph.nodes() if n.startswith('2-')]
        corridor_nodes = [n for n in self.nx_graph.nodes() if n.startswith('couloir')]
        
        # Dessiner les nœuds
        nx.draw_networkx_nodes(self.nx_graph, self.pos, 
                              nodelist=room_nodes, 
                              node_color='lightblue', 
                              node_size=300,
                              label='Salles')
        
        nx.draw_networkx_nodes(self.nx_graph, self.pos,
                              nodelist=corridor_nodes,
                              node_color='lightcoral',
                              node_size=100,
                              label='Points couloir')
        
        # Dessiner les arêtes
        nx.draw_networkx_edges(self.nx_graph, self.pos, 
                              edge_color='gray', 
                              alpha=0.6)
        
        # Ajouter les labels
        nx.draw_networkx_labels(self.nx_graph, self.pos, 
                               font_size=8)
        
        plt.title("Graphe des couloirs")
        plt.legend()
        plt.axis('equal')
        plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def visualize_path(self, path: List[str], figsize=(15, 10), save_path=None):
        """
        Visualise un chemin spécifique sur le graphe.
        
        Args:
            path: Liste des nœuds du chemin
            figsize: Taille de la figure
            save_path: Chemin de sauvegarde (optionnel)
        """
        if not path:
            print("Chemin vide, impossible de visualiser")
            return
        
        plt.figure(figsize=figsize)
        
        # Tous les nœuds en gris
        room_nodes = [n for n in self.nx_graph.nodes() if n.startswith('2-')]
        corridor_nodes = [n for n in self.nx_graph.nodes() if n.startswith('couloir')]
        
        nx.draw_networkx_nodes(self.nx_graph, self.pos,
                              nodelist=room_nodes,
                              node_color='lightgray',
                              node_size=300)
        
        nx.draw_networkx_nodes(self.nx_graph, self.pos,
                              nodelist=corridor_nodes,
                              node_color='lightgray',
                              node_size=100)
        
        # Arêtes en gris
        nx.draw_networkx_edges(self.nx_graph, self.pos,
                              edge_color='gray',
                              alpha=0.3)
        
        # Mettre en évidence le chemin
        path_nodes_rooms = [n for n in path if n.startswith('2-')]
        path_nodes_corridors = [n for n in path if n.startswith('couloir')]
        
        if path_nodes_rooms:
            nx.draw_networkx_nodes(self.nx_graph, self.pos,
                                  nodelist=path_nodes_rooms,
                                  node_color='red',
                                  node_size=400)
        
        if path_nodes_corridors:
            nx.draw_networkx_nodes(self.nx_graph, self.pos,
                                  nodelist=path_nodes_corridors,
                                  node_color='orange',
                                  node_size=150)
        
        # Arêtes du chemin
        path_edges = [(path[i], path[i+1]) for i in range(len(path)-1)]
        nx.draw_networkx_edges(self.nx_graph, self.pos,
                              edgelist=path_edges,
                              edge_color='red',
                              width=3)
        
        # Labels
        nx.draw_networkx_labels(self.nx_graph, self.pos, font_size=8)
        
        plt.title(f"Chemin: {path[0]} → {path[-1]}")
        plt.axis('equal')
        plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def show_corridor_structure(self):
        """Affiche la structure des couloirs détectés."""
        print("=== Structure des couloirs ===")
        for corridor_name, info in self.corridor_structure.items():
            print(f"\n{corridor_name}:")
            print(f"  Niveau Y: {info['y_level']}")
            print(f"  Nombre de salles: {len(info['rooms'])}")
            print(f"  Salles: {[room[0] for room in info['rooms']]}")
            print(f"  Points de couloir: {len(info['points'])}")
    
    def analyze_connectivity(self):
        """Analyse la connectivité du graphe."""
        print("=== Analyse de connectivité ===")
        print(f"Nombre total de nœuds: {len(self.nx_graph.nodes())}")
        print(f"Nombre total d'arêtes: {len(self.nx_graph.edges())}")
        
        # Composantes connexes
        components = list(nx.connected_components(self.nx_graph))
        print(f"Nombre de composantes connexes: {len(components)}")
        
        if len(components) > 1:
            print("⚠️  Le graphe n'est pas entièrement connecté!")
            for i, component in enumerate(components):
                rooms_in_component = [n for n in component if n.startswith('2-')]
                print(f"  Composante {i+1}: {len(rooms_in_component)} salles")
                if len(rooms_in_component) <= 10:
                    print(f"    Salles: {sorted(rooms_in_component)}")
        else:
            print("✅ Le graphe est entièrement connecté")
    
    def find_isolated_nodes(self):
        """Trouve les nœuds isolés."""
        isolated = list(nx.isolates(self.nx_graph))
        if isolated:
            print(f"⚠️  Nœuds isolés trouvés: {isolated}")
        else:
            print("✅ Aucun nœud isolé")
        return isolated

if __name__ == "__main__":
    # Chemin vers le fichier JSON
    json_path = os.path.join(os.path.dirname(__file__), '../data/corridor_graph.json')
    
    try:
        visualizer = GraphVisualizer(json_path)
        
        # Analyser la structure
        visualizer.show_corridor_structure()
        visualizer.analyze_connectivity()
        visualizer.find_isolated_nodes()
        
        # Visualiser le graphe
        visualizer.visualize_graph(save_path='../data/corridor_graph_visualization.png')
        
        # Exemple de visualisation de chemin (si possible)
        from algorithms.pathfinding import load_pathfinder_from_json
        pathfinder = load_pathfinder_from_json(json_path)
        
        result = pathfinder.find_shortest_path('2-10', '2-19')
        if result:
            print(f"\nChemin trouvé de 2-10 à 2-19:")
            print(f"Distance: {result['distance']:.2f}m")
            print(f"Chemin: {' → '.join(result['path'])}")
            visualizer.visualize_path(result['path'], save_path='../data/path_2-10_to_2-19.png')
        else:
            print("\n❌ Aucun chemin trouvé de 2-10 à 2-19")
            print("Ceci confirme le problème de connectivité!")
    
    except FileNotFoundError:
        print(f"Fichier non trouvé: {json_path}")
        print("Exécutez d'abord graph_builder.py pour créer le graphe.")
    except Exception as e:
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()