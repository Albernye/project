import sys
import os
import logging
from pathlib import Path
from datetime import datetime, timezone
import json
import csv
import pandas as pd
from flask import Flask, render_template, request, jsonify

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.geolocate import get_latest_positions
from algorithms.fusion import fuse, reset_kalman
from services.record_realtime import record_realtime
from algorithms.pathfinding import PathFinder
from services.utils import get_room_position
from services.update_live import update_qr, update_localization_files
from services.send_email import send_email
import config as cfg

# Logging configuration
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

app = Flask(__name__)

logger.info(f"DEFAULT_POSXY = {cfg.DEFAULT_POSXY}")

# Gloval variables for position tracking
current_position = None
previous_position = None
position_history = []

def get_project_root():
    """Return the root directory of the project"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_corridor_data():
    """Load the corridor graph data from JSON file"""
    try:
        with open('data/graph/corridor_graph.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("File corridor_graph.json not found")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return None

def normalize_room_id(room_id):
    """
    Normalize room identifiers to floor-room format,
    for example:
      - "201" -> "2-01"
      - "2-01" -> "2-01"
      - "15"  -> "0-15" 
    """
    if not room_id:
        return None

    # Case already in "X-YY" format
    if '-' in room_id:
        parts = room_id.split('-')
        if len(parts)==2 and parts[0].isdigit() and parts[1].isdigit():
            floor, num = int(parts[0]), int(parts[1])
            return f"{floor}-{num:02d}"
        else:
            return None

    # CCompact case "FNN" (3 digits): F = floor, NN = number
    if len(room_id) == 3 and room_id.isdigit():
        floor = int(room_id[0])
        num   = int(room_id[1:])
        return f"{floor}-{num:02d}"

    # Case two digits "NN": default floor to 2 (current floor)
    if room_id.isdigit():
        num = int(room_id)
        return f"2-{num:02d}"

    logger.warning(f"Invalid room ID: {room_id}")
    return None

def get_node_position(node_id, corridor_data):
    """Retrieve the position of a node (room or corridor point)"""
    # If it's a room
    if node_id.startswith('2-'):
        try:
            return get_room_position(node_id)
        except Exception as e:
            logger.warning(f"Position not found for room {node_id}: {e}")
            return None

    # If it's a corridor point
    if corridor_data and 'corridor_structure' in corridor_data:
        for corridor_name, corridor_info in corridor_data['corridor_structure'].items():
            for point_name, x, y in corridor_info.get('points', []):
                if point_name == node_id:
                    return [x, y]

    logger.warning(f"Position not found for node {node_id}")
    return None

# Load corridor data
corridor_data = load_corridor_data()
pathfinder = PathFinder(corridor_data['graph']) if corridor_data else None

@app.route('/position')
def get_position():
    """Return the current fused position"""
    room = request.args.get('room')
    if not room:
        return jsonify({"error": "Missing 'room' parameter"}), 400
    try:
        pdr_pos, finger_pos, qr_reset = get_latest_positions()
        fused_pos = fuse(pdr_pos, qr_reset, room=room)
        pos_list = list(map(float, fused_pos)) if fused_pos else [0.0, 0.0, 0.0]
        return jsonify({
            "position": pos_list,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sources": {"pdr": bool(pdr_pos), "fingerprint": False, "qr_reset": bool(qr_reset)}
        })
    except Exception as e:
        logger.error(f"Error in /position: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/route')
def get_route():
    """Calculate a route between two rooms"""
    if not pathfinder:
        return jsonify({"error": "Navigation system unavailable"}), 503

    start_room = request.args.get('from')
    end_room = request.args.get('to')
    
    if not start_room or not end_room:
        return jsonify({"error": "Parameters 'from' and 'to' are required"}), 400

    # Normalize room IDs
    start_node = normalize_room_id(start_room)
    end_node = normalize_room_id(end_room)
    
    if not start_node or not end_node:
        return jsonify({"error": "Invalid room IDs"}), 400
    
    try:
        result = pathfinder.find_shortest_path(start_node, end_node)
        
        if not result:
            return jsonify({"error": "Route not found"}), 404

        # Convert to GeoJSON
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
        logger.exception("Error calculating route")  # Log the exception
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    return """
    <h1>🏢 Indoor Navigation System</h1>
    <p>Scan a QR code to access a room!</p>
    <p>Direct test: <a href="/location?room=201">/location?room=201</a></p>
    <hr>
    <h2>API Endpoints:</h2>
    <ul>
        <li><strong>GET /position</strong> - Current position</li>
        <li><strong>GET /route?from=01&to=10</strong> - Route</li>
        <li><strong>POST /collect_sensor_data</strong> - Collect sensor data</li>
        <li><strong>GET /data</strong> - Visualize data</li>
    </ul>
    """

@app.route('/location')
def location():
    """Home page for a specific room"""
    room = request.args.get('room')
    if not room:
        return "❌ Missing 'room' parameter", 400

    # More robust validation
    normalized_room = normalize_room_id(room)
    if not normalized_room:
        return f"❌ Invalid room number: {room}", 400
    
    try:
        room_num = int(normalized_room[2:])  # Remove "2-" to get the number
        if not (1 <= room_num <= 25):  # Assume rooms 01-25
            return f"❌ Room {room} not available. Available rooms: 01-25", 400
    except ValueError:
        return "❌ Invalid room number format", 400
    
    return render_template('index.html', room=room)

@app.route('/collect_sensor_data', methods=['POST'])
def collect_sensor_data_route():
    """
    Collect and process raw sensor data.
    Save CSV files by sensor, then trigger post-processing.
    """
    # 1) Read and validate JSON
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"status": "error", "message": "No JSON payload received"}), 400

    # 2) Enrichment & normalization
    data['client_ip'] = request.remote_addr
    room_raw = data.get('room', '')
    normalized_room = normalize_room_id(room_raw) or room_raw

    # 3) Prepare raw files folder
    folder = Path(get_project_root()) / 'data' / 'recordings' / normalized_room
    folder.mkdir(parents=True, exist_ok=True)

    # 4) Save raw files
    sensor_types = ['accelerometer', 'gyroscope', 'magnetometer', 'wifi']
    last_filename = None
    for sensor_type in sensor_types:
        readings = data.get(sensor_type, [])
        if not isinstance(readings, list):
            continue

        for idx, reading in enumerate(readings):
            last_filename = folder / f"{sensor_type}_{idx}.csv"
            with open(last_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if sensor_type == 'wifi':
                    writer.writerow(['ssid', 'rssi', 'timestamp'])
                    writer.writerow([
                        reading.get('ssid', 'unknown'),
                        reading.get('rssi', 0),
                        datetime.now(timezone.utc).isoformat() + 'Z'
                    ])
                else:
                    writer.writerow(['x', 'y', 'z', 'timestamp'])
                    writer.writerow([
                        reading.get('x', 0.0),
                        reading.get('y', 0.0),
                        reading.get('z', 0.0),
                        datetime.now(timezone.utc).isoformat() + 'Z'
                    ])
                logger.debug(f"Wrote raw file: {last_filename}")

    # 5) If no file was written, return error 400
    if last_filename is None:
        return jsonify({"status": "error", "message": "No sensor data in payload"}), 400

    logger.info(f"Raw sensor files saved under {folder}")

    # 6) Post-processing
    #    Do not let the main route fail in case of internal error here
    try:
        # If you want, pass a DataFrame built here
        df = None
        update_localization_files(df, normalized_room, normalized_room)
    except Exception:
        logger.exception("Post-processing failed for collect_sensor_data")

    # 7) Return success
    return jsonify({
        "status": "success",
        "message": "Sensor data collected and processed (raw files saved, post-processing attempted)",
        "room": normalized_room
    }), 200
    
@app.route("/scan_qr", methods=["POST"])
def scan_qr():
    data = request.get_json()
    logger = app.logger
    logger.info(f"QR scan data: {data}")
    room = data.get("room")
    room_norm = normalize_room_id(room)

    update_qr(room_norm, logger)

    # Email alert logic
    recipient = None  # Use default from config/email_config
    subject = f"QR Scan Alert: Room {room_norm}"
    body = f"QR code scanned for room {room_norm} at {datetime.now().isoformat()}"
    try:
        email_success = send_email(subject, body, to_email=recipient)
        if email_success:
            logger.info(f"Email alert sent for QR scan: {room_norm}")
            status = "reset applique, email sent"
        else:
            logger.error(f"Email alert failed for QR scan: {room_norm}")
            status = "reset applique, email failed"
    except Exception as e:
        logger.error(f"Exception during email alert: {e}")
        status = "reset applique, email error"

    return {"status": status, "room": room_norm}, 200

@app.route('/data')
def view_data():
    """Display collected data"""
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
    """Update the current position based on received data"""
    global current_position, previous_position, position_history

    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        data['client_ip'] = request.remote_addr
        room = data.get('room', 'unknown')

        # Save raw data
        normalized_room = normalize_room_id(room)
        folder_name = normalized_room if normalized_room else f"2-{room}"
        folder = Path(get_project_root()) / 'data' / 'raw' / folder_name
        
        try:
            success = record_realtime(folder, data['client_ip'])
            if not success:
                logger.warning("Failed to save sensor data")
        except Exception as e:
            logger.error(f"Error in record_realtime: {e}")

        # Retrieve latest positions
        try:
            pdr_pos, finger_pos, qr_reset = get_latest_positions()
        except Exception as e:
            logger.error(f"Error in get_latest_positions: {e}")
            pdr_pos = finger_pos = qr_reset = None

        # Fusion Kalman
        try:
            fused_position = fuse(pdr_pos, qr_reset, room=room)
        except Exception as e:
            logger.error(f"Error in Kalman fusion: {e}")
            fused_position = None

        # Update global state
        if fused_position is not None:
            previous_position = current_position
            current_position = fused_position
            position_history.append(current_position)

            # Limit history
            if len(position_history) > 100:
                position_history = position_history[-100:]

        response = {
            "status": "success",
            "position": list(current_position) if current_position is not None else [0.0, 0.0],
            "room": folder_name
        }

        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in updating position: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/confirm_position', methods=['POST'])
def confirm_position():
    """Confirm the current position in a specific room"""
    data = request.get_json() or {}
    room = data.get('room')
    if not room:
        return jsonify({"status": "error", "message": "Missing room"}), 400
    normalized = normalize_room_id(room)
    if not normalized:
        return jsonify({"status": "error", "message": "Invalid room"}), 400
    pos = data.get('position')
    if pos:
        current = pos
    else:
        current = get_room_position(normalized)
    reset_kalman()
    return jsonify({"status": "success", "position": current})

@app.route('/health')
def health_check():
    """Health check endpoint to verify system status"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pathfinder_available": pathfinder is not None,
        "corridor_data_loaded": corridor_data is not None
    })

if __name__ == '__main__':
    logger.info("🌐 Starting Flask server...")
    if not pathfinder:
        logger.warning("⚠️ Pathfinder not available - check corridor_graph.json")
    app.run(host='0.0.0.0', port=5000, debug=True)
