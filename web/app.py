from flask import Flask, render_template, request, jsonify
import json
import os
import csv
from datetime import datetime
from scripts.geolocate import get_latest_positions
from project.algorithms.fusion import fuse, reset_kalman
from scripts.record_realtime import record_realtime
from algorithms.PDR import PDR

app = Flask(__name__)

# Initialize position tracking variables
current_position = None
previous_position = None
position_history = []

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
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        data['client_ip'] = request.remote_addr
        room = data.get('room', 'unknown')
        folder = os.path.join(get_project_root(), 'data', 'raw', f"2-{room}")

        if not os.path.exists(folder):
            os.makedirs(folder)

        # Save sensor data to individual files
        for sensor_type, readings in data.items():
            if sensor_type in ['accelerometer', 'gyroscope', 'magnetometer']:
                for i, reading in enumerate(readings):
                    filename = os.path.join(folder, f"{sensor_type}_{i}.csv")
                    with open(filename, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(['x', 'y', 'z', 'timestamp'])
                        writer.writerow([
                            reading.get('x', 0.0),
                            reading.get('y', 0.0),
                            reading.get('z', 0.0),
                            datetime.utcnow().isoformat() + 'Z'
                        ])

        # Call record_realtime to process the data
        success = record_realtime(folder, data['client_ip'])
        if not success:
            raise RuntimeError("collect_sensor_data() failed")

        return jsonify({
            "status": "success",
            "message": "Data collected and processed successfully"
        })
    except Exception as e:
        print(f"❌ Error during collection: {e}")
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }), 500

@app.route('/data')
def view_data():
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

@app.route('/update_position', methods=['POST'])
def update_position():
    global current_position, previous_position, position_history

    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        data['client_ip'] = request.remote_addr

        # Assume record_realtime processes and saves the data
        success = record_realtime(data['client_ip'])
        if not success:
            print("Warning: Failed to save sensor data")

        # Retrieve latest positions for PDR and Wi-Fi fingerprinting
        pdr_pos, finger_pos, qr_reset = get_latest_positions()

        # Fusion using Kalman filter
        fused_position = fuse(pdr_pos, finger_pos, qr_reset)

        # Update global position state
        current_position = fused_position
        if previous_position is None:
            previous_position = current_position
        position_history.append(current_position)

        response = {
            "status": "success",
            "position": current_position.tolist()
        }

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

        global current_position
        if position is not None:
            current_position = position
        else:
            # Assuming a function get_room_position exists which gets the default room position
            # Placeholder: replace with actual implementation
            current_position = [0, 0]  # Example placeholder

        # Reset Kalman Filter if needed
        reset_kalman()

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
