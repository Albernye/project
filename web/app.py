import sys
import os
import logging
from pathlib import Path
from datetime import datetime, timezone
import json
import csv
import traceback
from flask import Flask, render_template, request, jsonify

# Add parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import custom modules
from services.geolocate import get_latest_positions, initialize_coordinate_system
from algorithms.fusion import fuse, reset_kalman
from services.record_realtime import record_realtime
from algorithms.pathfinding import PathFinder
from services.utils import get_room_position, read_json_safe, write_json_safe
from services.update_live import update_qr, update_localization_files
from services.send_email import send_email
import config as cfg

# Global flag to indicate if a QR reset is pending
qr_reset_pending = False

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

# Initialize Flask application
app = Flask(__name__)

logger.info(f"DEFAULT_POSXY = {cfg.DEFAULT_POSXY}")

# Global variables for position tracking
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
    Normalize room identifiers to floor-room format.
    Examples:
      - "201" -> "2-01"
      - "2-01" -> "2-01" 
      - "15"  -> "0-15"
    
    Args:
        room_id (str): Room identifier to normalize
        
    Returns:
        str: Normalized room ID in "F-NN" format, or None if invalid
    """
    if not room_id:
        return None

    # Case: already in "X-YY" format
    if '-' in room_id:
        parts = room_id.split('-')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            floor, num = int(parts[0]), int(parts[1])
            return f"{floor}-{num:02d}"
        else:
            return None

    # Case: compact format "FNN" (3 digits): F = floor, NN = number
    if len(room_id) == 3 and room_id.isdigit():
        floor = int(room_id[0])
        num = int(room_id[1:])
        return f"{floor}-{num:02d}"

    # Case: two digits "NN": default floor to 2 (current floor)
    if room_id.isdigit():
        num = int(room_id)
        return f"2-{num:02d}"

    logger.warning(f"Invalid room ID: {room_id}")
    return None

def get_node_position(node_id, corridor_data):
    """
    Retrieve the position of a node (room or corridor point).
    
    Args:
        node_id (str): Node identifier
        corridor_data (dict): Corridor graph data
        
    Returns:
        list: [longitude, latitude] coordinates or None if not found
    """
    # If it's a room (starts with floor number)
    if node_id.startswith('2-'):
        try:
            position = get_room_position(node_id)
            # get_room_position returns [lon, lat, floor], we only need [lon, lat]
            return position[:2]
        except Exception as e:
            logger.warning(f"Position not found for room {node_id}: {e}")
            return None

    # If it's a corridor point
    if corridor_data and 'corridor_structure' in corridor_data:
        for corridor_name, corridor_info in corridor_data['corridor_structure'].items():
            for point_name, x, y in corridor_info.get('points', []):
                if point_name == node_id:
                    return [x, y]  # Return [longitude, latitude]

    logger.warning(f"Position not found for node {node_id}")
    return None

# Load corridor data and initialize pathfinder with scale factor
corridor_data = load_corridor_data()
pathfinder = PathFinder(corridor_data['graph'], scale_factor=1000.0) if corridor_data else None

@app.route('/position')
def get_position():
    """
    Return the current fused position based on sensor data.
    
    Query Parameters:
        room (str): Room identifier for context
        
    Returns:
        JSON: Current position, timestamp, and data sources
    """
    global qr_reset_pending
    
    room = request.args.get('room')
    if not room:
        return jsonify({"error": "Missing 'room' parameter"}), 400

    # Normalize room identifier
    normalized_room = normalize_room_id(room)
    if not normalized_room:
        return jsonify({"error": f"Invalid room number: {room}"}), 400

    room = normalized_room
    
    try:
        # Get latest position data from sensors
        result = get_latest_positions()
        if not result or len(result) != 3:
            pdr_pos, finger_pos, qr_reset = None, None, None
        else:
            pdr_pos, finger_pos, qr_reset = result

        def to_float_list(pos):
            """Convert position to standardized float list format"""
            if pos is None:
                return [0.0, 0.0, 0.0]
            if isinstance(pos, (list, tuple)) and all(isinstance(x, (int, float)) for x in pos):
                return list(map(float, pos))
            try:
                import numpy as np
                if isinstance(pos, np.ndarray):
                    return pos.astype(float).tolist()
            except ImportError:
                pass
            return [0.0, 0.0, 0.0]

        # Apply QR reset if pending (one-time application)
        if qr_reset_pending and qr_reset:
            try:
                fused_pos = fuse(pdr_pos, qr_reset, room=room)
            except Exception as fuse_err:
                logger.error(f"Error in fuse(): {fuse_err}")
                fused_pos = [0.0, 0.0, 0.0]
            qr_reset_pending = False
        else:
            # Use only PDR data for fusion
            try:
                fused_pos = fuse(pdr_pos, None, room=room)
            except Exception as fuse_err:
                logger.error(f"Error in fuse(): {fuse_err}")
                fused_pos = [0.0, 0.0, 0.0]

        # Ensure position is in correct format
        pos_list = to_float_list(fused_pos)
        if not isinstance(pos_list, list) or not all(isinstance(x, float) for x in pos_list):
            logger.error(f"Invalid position format: {pos_list}")
            pos_list = [0.0, 0.0, 0.0]

        # Extract walked distance from PDR data
        walked_distance = None
        if pdr_pos and len(pdr_pos) == 3:
            walked_distance = pdr_pos[2]

        return jsonify({
            "position": pos_list,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sources": {
                "pdr": bool(pdr_pos), 
                "fingerprint": False, 
                "qr_reset": bool(qr_reset)
            },
            "walked_distance": walked_distance
        })
        
    except Exception as e:
        logger.error(f"Error in /position: {e}", exc_info=True)
        return jsonify({"error": str(e), "position": [0.0, 0.0, 0.0]}), 500

@app.route('/route')
def get_route():
    """
    Calculate a route between two rooms using pathfinding algorithm.
    
    Query Parameters:
        from (str): Starting room identifier
        to (str): Destination room identifier
        
    Returns:
        JSON: GeoJSON FeatureCollection with route segments
    """
    if not pathfinder:
        return jsonify({"error": "Navigation system unavailable"}), 503

    start_room = request.args.get('from')
    end_room = request.args.get('to')
    
    if not start_room or not end_room:
        return jsonify({"error": "Parameters 'from' and 'to' are required"}), 400

    # Normalize room identifiers
    start_node = normalize_room_id(start_room)
    end_node = normalize_room_id(end_room)
    
    if not start_node or not end_node:
        return jsonify({"error": "Invalid room IDs"}), 400
    
    try:
        # Calculate shortest path
        result = pathfinder.find_shortest_path(start_node, end_node)
        
        if not result:
            return jsonify({"error": "Route not found"}), 404

        # Convert path to GeoJSON format with correct coordinate handling
        features = []
        segment_distances = []
        
        for i in range(len(result['path']) - 1):
            current_node = result['path'][i]
            next_node = result['path'][i + 1]
            
            # Get positions for current and next nodes
            start_pos = get_node_position(current_node, corridor_data)
            end_pos = get_node_position(next_node, corridor_data)
            
            if start_pos and end_pos:
                # Calculate segment distance in meters
                import math
                segment_distance = math.sqrt(
                    (end_pos[0] - start_pos[0])**2 + 
                    (end_pos[1] - start_pos[1])**2
                ) * pathfinder.scale_factor
                
                segment_distances.append(segment_distance)
                
                # Create GeoJSON LineString feature
                # IMPORTANT: Coordinates must be in [longitude, latitude] format for GeoJSON
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [start_pos[0], start_pos[1]],  # [lon, lat] format
                            [end_pos[0], end_pos[1]]       # [lon, lat] format
                        ]
                    },
                    "properties": {
                        "from": current_node,
                        "to": next_node,
                        "segment_distance": segment_distance,
                        "segment_index": i
                    }
                })
        
        # Calculate total distance
        total_distance = sum(segment_distances)
        
        # Create GeoJSON FeatureCollection
        geojson_response = {
            "type": "FeatureCollection",
            "features": features,
            "properties": {
                "total_distance": total_distance,
                "segment_count": len(features),
                "start_room": start_node,
                "end_room": end_node
            },
            "total_distance": total_distance,  # Keep for backward compatibility
            "path": result['path'],
            "segment_distances": segment_distances
        }
        
        logger.info(f"Route calculated: {start_node} -> {end_node}, distance: {total_distance:.2f}m")
        return jsonify(geojson_response)
        
    except Exception as e:
        logger.exception("Error calculating route")
        return jsonify({"error": str(e)}), 500
    
@app.route('/change_room', methods=['POST'])
def change_room():
    """
    Handle room change events from URL changes.
    This is called when the user navigates to a different room URL.
    
    Request Body (JSON):
        room (str): New room identifier
        
    Returns:
        JSON: Confirmation of room change
    """
    global qr_reset_pending
    
    try:
        data = request.get_json()
        if not data or 'room' not in data:
            return jsonify({"error": "Missing room parameter"}), 400

        room = str(data['room'])
        normalized_room = normalize_room_id(room)
        
        if not normalized_room:
            return jsonify({"error": f"Invalid room format: {room}"}), 400

        logger.info(f"Room changed to: {normalized_room}")
        
        # Get room coordinates for QR reset
        try:
            lon, lat, floor = get_room_position(normalized_room)
            
            # Create QR scanning event for room change
            qr_event = {
                "type": "qr",
                "room": normalized_room,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "position": [float(lon), float(lat)]
            }
            
            # Flag QR reset for next position polling
            qr_reset_pending = True
            
            # Save QR event
            write_json_safe([qr_event], cfg.QR_EVENTS_FILE)
            logger.info(f"QR event written for room change: {qr_event}")
            
        except Exception as e:
            logger.warning(f"Could not get position for room {normalized_room}: {e}")
        
        return jsonify({
            "success": True,
            "room": normalized_room,
            "message": f"Room changed to {normalized_room}"
        }), 200
        
    except Exception as e:
        logger.error(f"Error in /change_room: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    """Home page with API documentation"""
    return """
    <h1>🏢 Indoor Navigation System</h1>
    <p>Scan a QR code to access a room!</p>
    <p>Direct test: <a href="/location?room=201">/location?room=201</a></p>
    <hr>
    <h2>API Endpoints:</h2>
    <ul>
        <li><strong>GET /position?room=XXX</strong> - Get current fused position</li>
        <li><strong>GET /route?from=01&to=10</strong> - Calculate route between rooms</li>
        <li><strong>POST /collect_sensor_data</strong> - Collect and process sensor data</li>
        <li><strong>POST /scan_qr</strong> - Process QR code scanning</li>
        <li><strong>GET /data</strong> - Visualize collected data</li>
        <li><strong>GET /health</strong> - System health check</li>
    </ul>
    """

@app.route('/location')
def location():
    """
    Room-specific page for indoor navigation interface.
    
    Query Parameters:
        room (str): Room identifier
        
    Returns:
        HTML: Navigation interface for the specified room
    """
    room = request.args.get('room')
    if not room:
        return "❌ Missing 'room' parameter", 400

    # Validate and normalize room identifier
    normalized_room = normalize_room_id(room)
    if not normalized_room:
        return f"❌ Invalid room number: {room}", 400
    
    try:
        # Extract room number and validate range
        room_num = int(normalized_room[2:])  # Remove "2-" prefix
        if not (1 <= room_num <= 25):  # Assume valid room range 01-25
            return f"❌ Room {room} not available. Available rooms: 01-25", 400
    except ValueError:
        return "❌ Invalid room number format", 400
    
    return render_template('index.html', room=room)

@app.route('/collect_sensor_data', methods=['POST'])
def collect_sensor_data_route():
    """
    Collect and process raw sensor data from mobile devices.
    Save data as CSV files organized by sensor type, then trigger post-processing.
    
    Request Body (JSON):
        room (str): Room identifier
        accelerometer (list): Accelerometer readings
        gyroscope (list): Gyroscope readings  
        magnetometer (list): Magnetometer readings
        wifi (list): WiFi scan results
        
    Returns:
        JSON: Processing status and results
    """
    # Read and validate JSON payload
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"status": "error", "message": "No JSON payload received"}), 400

    # Enrich data with client information
    data['client_ip'] = request.remote_addr
    room_raw = data.get('room', '')
    normalized_room = normalize_room_id(room_raw) or room_raw

    # Create directory structure for raw sensor files
    folder = Path(get_project_root()) / 'data' / 'recordings' / normalized_room
    folder.mkdir(parents=True, exist_ok=True)

    # Process and save sensor data by type
    sensor_types = ['accelerometer', 'gyroscope', 'magnetometer', 'wifi']
    last_filename = None
    
    for sensor_type in sensor_types:
        readings = data.get(sensor_type, [])
        if not isinstance(readings, list):
            continue

        # Save each reading as a separate CSV file
        for idx, reading in enumerate(readings):
            last_filename = folder / f"{sensor_type}_{idx}.csv"
            with open(last_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write appropriate headers based on sensor type
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

    # Return error if no data was processed
    if last_filename is None:
        return jsonify({"status": "error", "message": "No sensor data in payload"}), 400

    logger.info(f"Raw sensor files saved under {folder}")

    # Attempt post-processing (don't let failures break the main route)
    try:
        df = None  # Could build DataFrame from collected data if needed
        update_localization_files(df, normalized_room, normalized_room)
    except Exception:
        logger.exception("Post-processing failed for collect_sensor_data")

    return jsonify({
        "status": "success",
        "message": "Sensor data collected and processed (raw files saved, post-processing attempted)",
        "room": normalized_room
    }), 200
    
@app.route('/scan_qr', methods=['POST'])
def scan_qr():
    """
    Process QR code scanning events and trigger position reset.
    Accepts both 'room' and 'qr_code' fields for compatibility.
    
    Request Body (JSON):
        room (str): Room identifier, OR
        qr_code (str): QR code filename
        
    Returns:
        JSON: Processing results with position and email status
    """
    global qr_reset_pending
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing request data"}), 400

        # Accept both 'room' and 'qr_code' fields for backward compatibility
        room_number = None
        qr_code = None
        
        if 'room' in data:
            room_number = str(data['room'])
            qr_code = f"room_{room_number}.png"
        elif 'qr_code' in data:
            qr_code = data['qr_code']
            room_number = qr_code.split('_')[-1].replace('.png', '')
        else:
            return jsonify({"error": "Missing 'room' or 'qr_code' in request"}), 400

        logger.info(f"QR scanned: {qr_code}")

        # Normalize room identifier
        normalized_room = normalize_room_id(room_number)
        if not normalized_room:
            return jsonify({"error": f"Invalid room format: {room_number}"}), 400

        # Get room coordinates
        try:
            lon, lat, floor = get_room_position(normalized_room)
        except Exception as e:
            logger.error(f"Failed to get position for room {normalized_room}: {e}")
            return jsonify({"error": "Room position not found"}), 404

        # Create QR scanning event
        qr_event = {
            "type": "qr",
            "room": normalized_room,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "position": [float(lon), float(lat)]
        }
        
        # Flag QR reset for next position polling
        qr_reset_pending = True

        # Save QR event (overwrite previous events - keep only latest)
        try:
            write_json_safe([qr_event], cfg.QR_EVENTS_FILE)
            logger.info(f"QR file overwritten with new event")
            logger.info(f"Event saved: {qr_event}")
        except Exception as e:
            logger.error(f"Failed to save QR event: {e}")
            return jsonify({"error": "Failed to save QR event"}), 500

        # Handle email notifications with robust error handling
        email_status = "not_configured"
        email_error = None
        
        try:
            if cfg.email_config.is_configured():
                try:
                    send_email(normalized_room, [lon, lat, floor])
                    email_status = "sent"
                    logger.info(f"Email alert sent for room {normalized_room}")
                except Exception as email_err:
                    email_status = "failed"
                    email_error = str(email_err)
                    logger.warning(f"Email sending failed: {email_err}")
            else:
                missing_vars = cfg.email_config.get_missing_vars()
                logger.info(f"Email not configured (missing: {missing_vars})")
                email_status = "not_configured"
        except ImportError as e:
            email_status = "unavailable"
            email_error = f"Email module not available: {e}"
            logger.warning(email_error)
        except Exception as e:
            email_status = "error"
            email_error = str(e)
            logger.error(f"Unexpected email error: {e}")

        # Build response
        response_data = {
            "success": True,
            "room": normalized_room,
            "position": [float(lon), float(lat), int(floor)],
            "timestamp": qr_event['timestamp'],
            "email_status": email_status
        }
        
        if email_error:
            response_data["email_error"] = email_error
            
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error in /scan_qr: {e}")
        logger.debug(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/data')
def visualize_data():
    """
    Endpoint to visualize collected sensor and positioning data.
    
    Returns:
        JSON: Aggregated data for visualization purposes
    """
    try:
        # Get current room from query parameters
        room = request.args.get('room')
        if room:
            normalized_room = normalize_room_id(room)
        else:
            normalized_room = None

        # Try to record real-time data if room is specified
        if normalized_room:
            try:
                folder = Path(get_project_root()) / 'data' / 'recordings' / normalized_room
                folder.mkdir(parents=True, exist_ok=True)
                
                # Record real-time sensor data
                success = record_realtime(folder, request.remote_addr)
                if not success:
                    logger.warning("Failed to save sensor data")
            except Exception as e:
                logger.error(f"Error in record_realtime: {e}")

        # Get latest position data from all sources
        try:
            pdr_pos, finger_pos, qr_reset = get_latest_positions()
        except Exception as e:
            logger.error(f"Error in get_latest_positions: {e}")
            pdr_pos = finger_pos = qr_reset = None

        # Perform Kalman fusion if room context is available
        fused_position = None
        if normalized_room:
            try:
                fused_position = fuse(pdr_pos, qr_reset, room=normalized_room)
            except Exception as e:
                logger.error(f"Error in Kalman fusion: {e}")

        # Update global position tracking state
        global current_position, previous_position, position_history
        if fused_position is not None:
            previous_position = current_position
            current_position = fused_position
            position_history.append(current_position)

            # Limit history to prevent memory issues
            if len(position_history) > 100:
                position_history = position_history[-100:]

        # Build response with current state
        response = {
            "status": "success",
            "position": list(current_position) if current_position is not None else [0.0, 0.0],
            "position_history": position_history,
            "room": normalized_room,
            "sources": {
                "pdr": pdr_pos is not None,
                "fingerprint": finger_pos is not None,
                "qr_reset": qr_reset is not None
            }
        }

        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in /data endpoint: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/confirm_position', methods=['POST'])
def confirm_position():
    """
    Manually confirm and set the current position for a specific room.
    This resets the Kalman filter with the confirmed position.
    
    Request Body (JSON):
        room (str): Room identifier
        position (list, optional): [x, y] coordinates
        
    Returns:
        JSON: Confirmation status and position
    """
    data = request.get_json() or {}
    room = data.get('room')
    
    if not room:
        return jsonify({"status": "error", "message": "Missing room parameter"}), 400
    
    # Normalize room identifier
    normalized = normalize_room_id(room)
    if not normalized:
        return jsonify({"status": "error", "message": "Invalid room identifier"}), 400
    
    # Use provided position or get default room position
    pos = data.get('position')
    if pos:
        current = pos
    else:
        try:
            current = get_room_position(normalized)
        except Exception as e:
            logger.error(f"Failed to get room position: {e}")
            return jsonify({"status": "error", "message": "Could not determine room position"}), 500
    
    # Reset Kalman filter with confirmed position
    try:
        reset_kalman()
        logger.info(f"Position confirmed for room {normalized}: {current}")
    except Exception as e:
        logger.error(f"Failed to reset Kalman filter: {e}")
        return jsonify({"status": "error", "message": "Failed to reset positioning system"}), 500
    
    return jsonify({"status": "success", "position": current, "room": normalized})

@app.route('/health')
def health_check():
    """
    Health check endpoint to verify system status and component availability.
    
    Returns:
        JSON: System health status and component availability
    """
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pathfinder_available": pathfinder is not None,
        "corridor_data_loaded": corridor_data is not None,
        "current_position": current_position,
        "qr_reset_pending": qr_reset_pending
    })

if __name__ == '__main__':
    # Initialize coordinate system before starting server
    initialize_coordinate_system()
    logger.info("🌐 Starting Flask server...")
    
    # Warn if pathfinder is not available
    if not pathfinder:
        logger.warning("⚠️ Pathfinder not available - check corridor_graph.json")
    
    # Start Flask development server
    app.run(host='0.0.0.0', port=5000, debug=True)
