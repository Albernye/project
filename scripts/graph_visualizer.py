"""
Visualiseur de graphe de couloirs.
Ce module permet de visualiser le graphe construit et les chemins trouvés.
"""

import json
import matplotlib.pyplot as plt
import networkx as nx
from typing import List
import sys
from pathlib import Path

class GraphVisualizer:
    """Classe pour visualiser les graphes de couloirs."""
    def __init__(self, graph_data_path: str, background_image: str = None):
        """
        Initialise le visualiseur avec les données du graphe.
        Args:
            graph_data_path: Chemin vers le fichier JSON du graphe
            background_image: Chemin optionnel vers l'image de fond (plan d'étage)
        """
        with open(graph_data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.graph = data['graph']
        self.room_positions = data['room_positions']
        self.corridor_structure = data['corridor_structure']
        self.background_image = background_image

        # Créer le graphe NetworkX et positions
        self.nx_graph = nx.Graph()
        self.pos = {}
        self._build_networkx_graph()

    def _build_networkx_graph(self):
        """Construit le graphe NetworkX pour la visualisation."""
        for room, (x, y) in self.room_positions.items():
            self.nx_graph.add_node(room, node_type='room')
            self.pos[room] = (x, y)
        for corridor_name, info in self.corridor_structure.items():
            for point_name, x, y in info['points']:
                self.nx_graph.add_node(point_name, node_type='corridor')
                self.pos[point_name] = (x, y)
        for node, neighbors in self.graph.items():
            for neighbor, weight in neighbors:
                self.nx_graph.add_edge(node, neighbor, weight=weight)

    def visualize_graph(self,
                         figsize=(20, 12),
                         node_size_room=800,
                         node_size_corridor=250,
                         font_size=12,
                         save_path: str = None,
                         show_bg=True):
        """
        Visualise le graphe complet.
        """
        plt.figure(figsize=figsize, dpi=300)

        # Fond de plan si fourni
        if show_bg and self.background_image and Path(self.background_image).exists():
            img = plt.imread(self.background_image)
            xs = [x for x, y in self.pos.values()]
            ys = [y for x, y in self.pos.values()]
            xmin, xmax = min(xs) - 1, max(xs) + 1
            ymin, ymax = min(ys) - 1, max(ys) + 1
            plt.imshow(img, extent=[xmin, xmax, ymin, ymax], alpha=0.3, origin='upper')
            plt.gca().invert_yaxis()

        room_nodes = [n for n in self.nx_graph.nodes if n.startswith('2-')]
        corridor_nodes = [n for n in self.nx_graph.nodes if n.startswith('couloir')]

        nx.draw_networkx_edges(self.nx_graph, self.pos, edge_color='gray', alpha=0.15)
        nx.draw_networkx_nodes(self.nx_graph, self.pos, nodelist=room_nodes,
                               node_color='lightblue', node_size=node_size_room,
                               node_shape='s', alpha=0.9, label='Salles')
        nx.draw_networkx_nodes(self.nx_graph, self.pos, nodelist=corridor_nodes,
                               node_color='lightcoral', node_size=node_size_corridor,
                               node_shape='o', alpha=0.6, label='Points couloir')
        labels = {n: n for n in room_nodes}
        nx.draw_networkx_labels(self.nx_graph, self.pos, labels,
                               font_size=font_size, font_weight='bold')

        plt.legend(scatterpoints=1)
        plt.axis('equal')
        plt.tight_layout()
        plt.grid(alpha=0.3)

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, bbox_inches='tight')
            print(f"✅ Graphe complet enregistré dans {save_path}")
        plt.close()

    def visualize_path(self,
                       path: List[str],
                       figsize=(20, 12),
                       node_size_room=800,
                       node_size_corridor=250,
                       font_size=12,
                       save_path: str = None):
        """Visualise un chemin spécifique sur le graphe."""
        if not path:
            print("Chemin vide, impossible de visualiser")
            return

        plt.figure(figsize=figsize, dpi=300)
        room_nodes = [n for n in self.nx_graph.nodes if n.startswith('2-')]
        corridor_nodes = [n for n in self.nx_graph.nodes if n.startswith('couloir')]

        nx.draw_networkx_edges(self.nx_graph, self.pos, edge_color='gray', alpha=0.1)
        nx.draw_networkx_nodes(self.nx_graph, self.pos, nodelist=room_nodes,
                               node_color='lightgray', node_size=node_size_room)
        nx.draw_networkx_nodes(self.nx_graph, self.pos, nodelist=corridor_nodes,
                               node_color='lightgray', node_size=node_size_corridor)

        path_edges = list(zip(path[:-1], path[1:]))
        nx.draw_networkx_edges(self.nx_graph, self.pos, edgelist=path_edges,
                               edge_color='red', width=3)
        rooms = [n for n in path if n.startswith('2-')]
        corridors = [n for n in path if n.startswith('couloir')]
        if rooms:
            nx.draw_networkx_nodes(self.nx_graph, self.pos, nodelist=rooms,
                                   node_color='red', node_size=node_size_room)
        if corridors:
            nx.draw_networkx_nodes(self.nx_graph, self.pos, nodelist=corridors,
                                   node_color='orange', node_size=node_size_corridor)
        nx.draw_networkx_labels(self.nx_graph, self.pos,
                               {n: n for n in rooms},
                               font_size=font_size, font_weight='bold')

        plt.title(f"Chemin: {path[0]} → {path[-1]}")
        plt.axis('equal')
        plt.tight_layout()
        plt.grid(alpha=0.3)

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, bbox_inches='tight')
            print(f"✅ Chemin enregistré dans {save_path}")
        plt.close()

    def show_corridor_structure(self):
        print("=== Structure des couloirs ===")
        for name, info in self.corridor_structure.items():
            print(f"\n{name}: ")
            print(f"  Niveau Y: {info['y_level']}")
            print(f"  Nombre de salles: {len(info['rooms'])}")
            print(f"  Salles: {[r[0] for r in info['rooms']]}" )
            print(f"  Points de couloir: {len(info['points'])}")

    def analyze_connectivity(self):
        print("=== Analyse de connectivité ===")
        print(f"Nombre total de nœuds: {self.nx_graph.number_of_nodes()}")
        print(f"Nombre total d'arêtes: {self.nx_graph.number_of_edges()}")
        comps = list(nx.connected_components(self.nx_graph))
        print(f"Nombre de composantes connexes: {len(comps)}")
        print("✅ Graphe entièrement connecté" if len(comps) == 1 else "⚠️ Graphe non connecté")

    def find_isolated_nodes(self) -> List[str]:
        isolated = list(nx.isolates(self.nx_graph))
        print(f"✅ Aucun nœud isolé" if not isolated else f"⚠️ Nœuds isolés: {isolated}")
        return isolated

if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(ROOT))

    DATA_DIR = ROOT / 'data'
    JSON_PATH = DATA_DIR / 'corridor_graph.json'
    BACK_IMG  = ROOT / 'assets' / 'OBuilding_Floor2.png'
    GRAPH_IMG = DATA_DIR / 'corridor_graph_visualization.png'
    PATH_IMG  = DATA_DIR / 'path_2-10_to_2-04.png'

    if not JSON_PATH.exists():
        print("❌ Fichier introuvable:", JSON_PATH)
        sys.exit(1)

    print(f"📁 Utilisation du JSON : {JSON_PATH}")

    try:
        viz = GraphVisualizer(str(JSON_PATH), background_image=str(BACK_IMG))
        viz.show_corridor_structure()
        viz.analyze_connectivity()
        viz.find_isolated_nodes()

        viz.visualize_graph(save_path=str(GRAPH_IMG))

        from algorithms.pathfinding import load_pathfinder_from_json
        pathfinder = load_pathfinder_from_json(str(JSON_PATH))
        result = pathfinder.find_shortest_path('2-10', '2-04')
        if result:
            print(f"\nChemin 2-10 → 2-04 : {result['distance']:.2f} m")
            print("Détail :", " → ".join(result['path']))
            viz.visualize_path(result['path'], save_path=str(PATH_IMG))
        else:
            print("❌ Aucun chemin trouvé entre 2-10 et 2-04")

    except ModuleNotFoundError as mnf:
        print("ImportError:", mnf)
    except Exception as e:
        print("Erreur inattendue:", e)
        import traceback; traceback.print_exc()