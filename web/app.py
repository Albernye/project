from flask import Flask, render_template, request, jsonify
import json
import os
import csv
import numpy as np
from scripts.enhanced_geolocate import (
    update_position_with_fusion,
    predict_room,
    enhanced_predict_position,
    get_room_position
)
from scripts.enhanced_pdr import enhanced_PDR_from_csv
from scripts.collect_sensor_data import collect_sensor_data
# predict_room now imported from enhanced_geolocate
from scripts.route import route_between
from datetime import datetime

app = Flask(__name__)

# Initialize position tracking variables
current_position = None
previous_position = None
position_history = []

# Configuration of the Flask application
def get_project_root():
    """Return the root directory of the project"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@app.route('/')
def home():
    return """
    <h1>🏢 Indoor Navigation System</h1>
    <p>Scan a QR code to access a room!</p>
    <p>Or test directly: <a href="/location?room=201">/location?room=201</a></p>
    """

@app.route('/location')
def location():
    room = request.args.get('room')
    if not room:
        return "❌ Missing 'room' parameter", 400
    try:
        room_num = int(room)
        if not (201 <= room_num <= 225):
            return f"❌ Room {room} not available. Available rooms: 201-225", 400
    except ValueError:
        return "❌ Invalid room number", 400
    return render_template('index.html', room=room)

@app.route('/collect_sensor_data', methods=['POST'])
def collect_sensor_data_route():
    """
    Reçoit les données capteurs, délègue la sauvegarde + envoi d'email,
    et renvoie le statut.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        data['client_ip'] = request.remote_addr

        success = collect_sensor_data(data)
        if not success:
            raise RuntimeError("collect_sensor_data() failed")

        return jsonify({
            "status": "success",
            "message": "Data collected and emailed successfully"
        })

    except Exception as e:
        print(f"❌ Error during collection: {e}")
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }), 500

@app.route('/data')
def view_data():
    """
    Endpoint debug : liste les données JSONL collectées.
    """
    try:
        project_root = get_project_root()
        data_file = os.path.join(project_root, 'data', 'sensor_data.csv')
        if not os.path.exists(data_file):
            return jsonify({"message": "No data collected yet"})

        entries = []
        with open(data_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                entries.append(dict(row))

        return jsonify({
            "total_entries": len(entries),
            "last_10_entries": entries[-10:]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/locate', methods=['GET'])
def locate():
    try:
        room, neighbors = predict_room()
        return jsonify({
            "status": "success",
            "predicted_room": room,
            "neighbors": neighbors
        })
    except RuntimeError as re:
        # Missing live data → 400
        return jsonify({
            "status": "error",
            "message": str(re)
        }), 400
    except Exception as e:
        # Any other error → 500
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
@app.route('/route', methods=['GET'])
def route():
    """
    GET /route?from=ID1&to=ID2
    Retourne GeoJSON FeatureCollection.
    """
    try:
        start = int(request.args.get('from', 0))
        end   = int(request.args.get('to',   0))
    except ValueError:
        return jsonify({"status":"error","message":"Invalid node IDs"}), 400

    try:
        geojson = route_between(start, end)
        return jsonify({"status":"success", "route": geojson})
    except Exception as e:
        return jsonify({"status":"error", "message": str(e)}), 500

@app.route('/update_position', methods=['POST'])
def update_position():
    """
    Reçoit les données des capteurs en temps réel, calcule la position PDR,
    détecte la dérive et déclenche le recalage si nécessaire.
    Retourne la position mise à jour.
    """
    global current_position, previous_position, position_history

    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        # Sauvegarder les données (optionnel, selon vos besoins)
        data['client_ip'] = request.remote_addr
        success = collect_sensor_data(data)
        if not success:
            print("Warning: Failed to save sensor data")

        # Save sensor data to temp file for processing
        temp_file_path = os.path.join(get_project_root(), 'data', 'temp_sensor_data.csv')
        with open(temp_file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['sensor_type', 'x', 'y', 'z', 'timestamp', 'room', 'client_ip'])
            # Écrire les données brutes selon le nouveau format
            for sensor in ['accelerometer', 'gyroscope', 'magnetometer']:
                if sensor in data:
                    for entry in data[sensor]:
                        writer.writerow([
                            sensor,
                            entry.get('x', entry.get('alpha', 0.0)),
                            entry.get('y', entry.get('beta', 0.0)),
                            entry.get('z', entry.get('gamma', 0.0)),
                            datetime.utcnow().isoformat() + 'Z',
                            data.get("room", "unknown"),
                            data.get("client_ip")
                        ])

        # Process with enhanced PDR
        try:
            headings, pdr_positions, stride_lengths, pdr_metadata, _ = enhanced_PDR_from_csv(temp_file_path)
            latest_pdr_position = pdr_positions[-1] if len(pdr_positions) > 0 else None
        except Exception as e:
            print(f"❌ PDR processing error: {e}")
            latest_pdr_position = None
            pdr_metadata = {}

        # Get WiFi fingerprinting position
        try:
            wifi_position, _, wifi_confidence = enhanced_predict_position()
        except Exception as e:
            print(f"❌ WiFi positioning error: {e}")
            wifi_position = None
            wifi_confidence = 0.0

        # Fuse positions using enhanced system
        fusion_result = update_position_with_fusion(
            pdr_position=latest_pdr_position,
            wifi_position=wifi_position,
            pdr_metadata=pdr_metadata,
            force_wifi_correction=False
        )

        # Update global position state
        current_position = fusion_result['position']
        if previous_position is None:
            previous_position = current_position
        position_history.append(current_position)

        # Prepare response
        response = {
            "status": "success",
            "position": current_position.tolist(),
            "drift_detected": fusion_result['drift_detected'],
            "drift_distance": fusion_result['drift_distance'],
            "source": fusion_result['source'],
            "pdr_confidence": fusion_result['pdr_confidence'],
            "wifi_confidence": fusion_result['wifi_confidence']
        }

        # Handle drift correction
        if fusion_result['drift_detected']:
            response["message"] = "Drift detected. Please scan a QR code to confirm position."
            response["suggested_position"] = wifi_position.tolist() if wifi_position is not None else current_position.tolist()

        return jsonify(response)

    except Exception as e:
        print(f"❌ Error during position update: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
@app.route('/confirm_position', methods=['POST'])
def confirm_position():
    try:
        data = request.get_json()
        if not data or 'room' not in data:
            return jsonify({"status": "error", "message": "Missing room parameter"}), 400

        room_number = data['room']
        position = data.get('position', None)

        # Ici, nous pourrions mettre à jour la position actuelle avec la position confirmée
        # Par exemple, placer l'utilisateur au centre de la salle confirmée
        global current_position
        if position is not None:
            current_position = position
        else:
            # Obtenir la position par défaut pour la salle confirmée
            current_position = get_room_position(room_number)[:2]  # Ignorer l'étage pour l'instant

        # Mettre à jour l'état PDR
        if hasattr(app, 'pdr_state') and app.pdr_state is not None:
            app.pdr_state['last_position'] = current_position

        return jsonify({
            "status": "success",
            "message": f"Position confirmed in room {room_number}"
        })

    except Exception as e:
        print(f"❌ Error confirming position: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == '__main__':
    print("🌐 Démarrage du serveur Flask…")
    app.run(host='0.0.0.0', port=5000, debug=True)
