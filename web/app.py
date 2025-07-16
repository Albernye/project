import sys
import os
import logging
from pathlib import Path
from datetime import datetime, timezone

# Ajouter le répertoire racine au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify
import json
import csv

from scripts.geolocate import get_latest_positions
from algorithms.fusion import fuse, reset_kalman
from scripts.record_realtime import record_realtime
from algorithms.pathfinding import PathFinder
from scripts.utils import get_room_position

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Variables globales pour le suivi de position
current_position = None
previous_position = None
position_history = []

def get_project_root():
    """Return the root directory of the project"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_corridor_data():
    """Charge les données du graphe de couloirs avec gestion d'erreurs"""
    try:
        with open('data/graph/corridor_graph.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Fichier corridor_graph.json introuvable")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de parsing JSON: {e}")
        return None

def normalize_room_id(room_id):
    """
    Normalise les identifiants de salle au format floor-room,
    par exemple :
      - "201" -> "2-01"
      - "2-01" -> "2-01"
      - "15"  -> "0-15" 
    """
    if not room_id:
        return None

    # Cas déjà au format "X-YY"
    if '-' in room_id:
        parts = room_id.split('-')
        if len(parts)==2 and parts[0].isdigit() and parts[1].isdigit():
            floor, num = int(parts[0]), int(parts[1])
            return f"{floor}-{num:02d}"
        else:
            return None

    # Cas compact "FNN" (3 chiffres) : F = floor, NN = numéro
    if len(room_id) == 3 and room_id.isdigit():
        floor = int(room_id[0])
        num   = int(room_id[1:])
        return f"{floor}-{num:02d}"

    # Cas deux chiffres "NN" : étage par défaut à 2 (étage courant)
    if room_id.isdigit():
        num = int(room_id)
        return f"2-{num:02d}"

    logger.warning(f"ID de salle invalide: {room_id}")
    return None

def get_node_position(node_id, corridor_data):
    """Récupère la position d'un nœud (salle ou point de couloir)"""
    # Si c'est une salle
    if node_id.startswith('2-'):
        try:
            return get_room_position(node_id)
        except Exception as e:
            logger.warning(f"Position introuvable pour la salle {node_id}: {e}")
            return None
    
    # Si c'est un point de couloir
    if corridor_data and 'corridor_structure' in corridor_data:
        for corridor_name, corridor_info in corridor_data['corridor_structure'].items():
            for point_name, x, y in corridor_info.get('points', []):
                if point_name == node_id:
                    return [x, y]
    
    logger.warning(f"Position introuvable pour le nœud {node_id}")
    return None

# Chargement du graphe de navigation
corridor_data = load_corridor_data()
pathfinder = PathFinder(corridor_data['graph']) if corridor_data else None

@app.route('/position')
def get_position():
    """Renvoie la position actuelle fusionnée"""
    try:
        pdr_pos, finger_pos, qr_reset = get_latest_positions()

        # Recupère le numéro de la salle depuis les paramètres de la requête
        room = request.args.get('room')
        if not room:
            return jsonify({"error": "Missing 'room' parameter"}), 400
        
        # Fusion Kalman
        fused_pos = fuse(pdr_pos, finger_pos, qr_reset, room=room)

        # S'assure que c'est une liste de floats [lat, lon]
        if fused_pos is not None:
            pos_list = list(map(float, fused_pos))
        else:
            pos_list = [0.0, 0.0]
            
        return jsonify({
            "position": pos_list,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sources": {
                "pdr": pdr_pos is not None,
                "fingerprint": finger_pos is not None,
                "qr_reset": qr_reset is not None
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de position: {e}")
        return jsonify({
            "error": str(e),
            "position": [0.0, 0.0],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 500

@app.route('/route')
def get_route():
    """Calcule un itinéraire entre deux salles"""
    if not pathfinder:
        return jsonify({"error": "Système de navigation indisponible"}), 503
    
    start_room = request.args.get('from')
    end_room = request.args.get('to')
    
    if not start_room or not end_room:
        return jsonify({"error": "Paramètres 'from' et 'to' requis"}), 400
    
    # Normalisation des IDs de salle
    start_node = normalize_room_id(start_room)
    end_node = normalize_room_id(end_room)
    
    if not start_node or not end_node:
        return jsonify({"error": "IDs de salle invalides"}), 400
    
    try:
        result = pathfinder.find_shortest_path(start_node, end_node)
        
        if not result:
            return jsonify({"error": "Itinéraire introuvable"}), 404
            
        # Conversion en GeoJSON
        features = []
        for i in range(len(result['path'])-1):
            current_node = result['path'][i]
            next_node = result['path'][i+1]
            
            start_pos = get_node_position(current_node, corridor_data)
            end_pos = get_node_position(next_node, corridor_data)
            
            if start_pos and end_pos:
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [start_pos[0], start_pos[1]],
                            [end_pos[0], end_pos[1]]
                        ]
                    },
                    "properties": {
                        "from": current_node,
                        "to": next_node,
                        "segment_distance": result.get('segment_distances', [0])[i] if i < len(result.get('segment_distances', [])) else 0
                    }
                })
        
        return jsonify({
            "type": "FeatureCollection",
            "features": features,
            "total_distance": result['distance'],
            "path": result['path']
        })
        
    except Exception as e:
        logger.exception("Erreur lors du calcul d'itinéraire")  # Log la trace complète
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    return """
    <h1>🏢 Système de Navigation Indoor</h1>
    <p>Scannez un QR code pour accéder à une salle !</p>
    <p>Test direct : <a href="/location?room=201">/location?room=201</a></p>
    <hr>
    <h2>API Endpoints:</h2>
    <ul>
        <li><strong>GET /position</strong> - Position actuelle</li>
        <li><strong>GET /route?from=01&to=10</strong> - Itinéraire</li>
        <li><strong>POST /collect_sensor_data</strong> - Collecte données capteurs</li>
        <li><strong>GET /data</strong> - Visualisation données</li>
    </ul>
    """

@app.route('/location')
def location():
    """Page d'accueil pour une salle spécifique"""
    room = request.args.get('room')
    if not room:
        return "❌ Missing 'room' parameter", 400
    
    # Validation plus robuste
    normalized_room = normalize_room_id(room)
    if not normalized_room:
        return f"❌ Invalid room number: {room}", 400
    
    try:
        room_num = int(normalized_room[2:])  # Enlever "2-" pour avoir le numéro
        if not (1 <= room_num <= 25):  # Supposons salles 01-25
            return f"❌ Room {room} not available. Available rooms: 01-25", 400
    except ValueError:
        return "❌ Invalid room number format", 400
    
    return render_template('index.html', room=room)

@app.route('/collect_sensor_data', methods=['POST'])
def collect_sensor_data_route():
    """Collecte et traite les données de capteurs"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        data['client_ip'] = request.remote_addr
        room = data.get('room', 'unknown')
        
        # Normalisation du nom de salle
        normalized_room = normalize_room_id(room)
        folder_name = normalized_room if normalized_room else f"2-{room}"

        folder = Path(get_project_root()) / 'data' / 'recordings' / folder_name
        folder.mkdir(parents=True, exist_ok=True)

        # Sauvegarde des données de capteurs
        sensor_types = ['accelerometer', 'gyroscope', 'magnetometer']
        for sensor_type in sensor_types:
            if sensor_type in data:
                readings = data[sensor_type]
                if isinstance(readings, list):
                    for i, reading in enumerate(readings):
                        filename = folder / f"{sensor_type}_{i}.csv"
                        with open(filename, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow(['x', 'y', 'z', 'timestamp'])
                            writer.writerow([
                                reading.get('x', 0.0),
                                reading.get('y', 0.0),
                                reading.get('z', 0.0),
                                datetime.now(timezone.utc).isoformat() + 'Z'
                            ])

        # Traitement des données en temps réel
        try:
            success = record_realtime(folder, data['client_ip'])
            if not success:
                logger.warning("record_realtime a échoué, mais les données sont sauvegardées")
        except Exception as e:
            logger.error(f"Erreur record_realtime: {e}")

        return jsonify({
            "status": "success",
            "message": "Data collected and processed successfully",
            "room": folder_name
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la collecte: {e}")
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }), 500

@app.route('/data')
def view_data():
    """Affiche les données collectées"""
    try:
        project_root = get_project_root()
        data_file = Path(project_root) / 'data' / 'sensor_data.csv'
        
        if not data_file.exists():
            return jsonify({"message": "No data collected yet"})

        entries = []
        with open(data_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                entries.append(dict(row))

        return jsonify({
            "total_entries": len(entries),
            "last_10_entries": entries[-10:],
            "data_file": str(data_file)
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la lecture des données: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/update_position', methods=['POST'])
def update_position():
    """Met à jour la position actuelle en fonction des données reçues"""
    global current_position, previous_position, position_history

    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        data['client_ip'] = request.remote_addr
        room = data.get('room', 'unknown')
        
        # Sauvegarde des données brutes
        normalized_room = normalize_room_id(room)
        folder_name = normalized_room if normalized_room else f"2-{room}"
        folder = Path(get_project_root()) / 'data' / 'raw' / folder_name
        
        try:
            success = record_realtime(folder, data['client_ip'])
            if not success:
                logger.warning("Failed to save sensor data")
        except Exception as e:
            logger.error(f"Erreur record_realtime: {e}")

        # Récupération des dernières positions
        try:
            pdr_pos, finger_pos, qr_reset = get_latest_positions()
        except Exception as e:
            logger.error(f"Erreur get_latest_positions: {e}")
            pdr_pos = finger_pos = qr_reset = None

        # Fusion Kalman
        try:
            fused_position = fuse(pdr_pos, finger_pos, qr_reset, room=room)
        except Exception as e:
            logger.error(f"Erreur fusion Kalman: {e}")
            fused_position = None

        # Mise à jour de l'état global
        if fused_position is not None:
            previous_position = current_position
            current_position = fused_position
            position_history.append(current_position)
            
            # Limiter l'historique
            if len(position_history) > 100:
                position_history = position_history[-100:]

        response = {
            "status": "success",
            "position": list(current_position) if current_position is not None else [0.0, 0.0],
            "room": folder_name
        }

        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de position: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/confirm_position', methods=['POST'])
def confirm_position():
    """Confirme la position actuelle dans une salle spécifique"""
    global current_position
    
    try:
        data = request.get_json()
        if not data or 'room' not in data:
            return jsonify({"status": "error", "message": "Missing room parameter"}), 400

        room_number = data['room']
        position = data.get('position', None)
        
        normalized_room = normalize_room_id(room_number)
        if not normalized_room:
            return jsonify({"status": "error", "message": "Invalid room number"}), 400

        if position is not None:
            current_position = position
        else:
            # Utiliser la position par défaut de la salle
            try:
                current_position = get_room_position(normalized_room)
            except Exception as e:
                logger.error(f"Erreur récupération position salle: {e}")
                current_position = [0.0, 0.0]

        # Reset du filtre de Kalman
        try:
            reset_kalman()
        except Exception as e:
            logger.warning(f"Erreur reset Kalman: {e}")

        return jsonify({
            "status": "success",
            "message": f"Position confirmed in room {normalized_room}",
            "position": current_position
        })
        
    except Exception as e:
        logger.error(f"Erreur confirmation position: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/health')
def health_check():
    """Endpoint de santé pour vérifier le statut du système"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pathfinder_available": pathfinder is not None,
        "corridor_data_loaded": corridor_data is not None
    })

if __name__ == '__main__':
    logger.info("🌐 Démarrage du serveur Flask…")
    if not pathfinder:
        logger.warning("⚠️ Pathfinder non disponible - vérifiez corridor_graph.json")
    app.run(host='0.0.0.0', port=5000, debug=True)
