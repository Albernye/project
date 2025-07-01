from flask import Flask, render_template, request, jsonify
import json
import os
from scripts.collect_sensor_data import collect_sensor_data
from scripts.geolocate import predict_room
from datetime import datetime

app = Flask(__name__)

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
        data_file = os.path.join(project_root, 'data', 'sensor_data.json')
        if not os.path.exists(data_file):
            return jsonify({"message": "No data collected yet"})

        entries = []
        with open(data_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except:
                        continue

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


if __name__ == '__main__':
    print("🌐 Démarrage du serveur Flask…")
    app.run(host='0.0.0.0', port=5000, debug=True)
