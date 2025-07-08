from flask import Flask, render_template, request, jsonify
import json
import os
import numpy as np
from legacy_tools import PDR_from_json
from scripts.geolocate import load_baseline, load_latest_live, get_room_position
from scripts.geolocate import predict_position
from scripts.collect_sensor_data import collect_sensor_data
from scripts.geolocate import predict_room
from scripts.route import route_between
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

        # Traiter les données avec PDR pour obtenir la nouvelle position
        # Note: Nous devons adapter PDR_from_json pour accepter directement les données plutôt qu'un fichier
        # Pour l'instant, nous allons sauvegarder les données dans un fichier temporaire
        temp_file_path = os.path.join(get_project_root(), 'data', 'temp_sensor_data.json')
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Appliquer PDR
        thetas, positions, stride_lengths, metadata, new_state = PDR_from_json(
            temp_file_path, plot=False, incremental=True, previous_state=getattr(app, 'pdr_state', None)
        )

        # Mettre à jour l'état PDR dans l'application Flask
        app.pdr_state = new_state

        if positions is not None and len(positions) > 0:
            # Mettre à jour la position actuelle
            current_position = positions[-1]  # Dernière position calculée

            # Calculer la distance depuis la dernière position
            if previous_position is not None:
                distance = np.linalg.norm(np.array(current_position) - np.array(previous_position))
            else:
                distance = 0

            # Détecter la dérive
            if distance > 2.0:  # Seuil de 2 mètres
                print(f"🚨 Drift detected: {distance:.2f} meters")

                # Recalage par fingerprinting Wi-Fi
                try:
                    position, neighbors = predict_position()
                    print(f"Wi-Fi fingerprinting suggests position: {position}")

                    # Corriger la position actuelle
                    current_position = position[:2]  # Utiliser uniquement longitude et latitude, ignorer l'étage pour l'instant

                    # Mettre à jour la position dans l'état PDR
                    if app.pdr_state is not None:
                        app.pdr_state['last_position'] = current_position

                except Exception as e:
                    print(f"⚠️ Wi-Fi fingerprinting failed: {e}")

                # Proposer un scan QR pour confirmation
                return jsonify({
                    "status": "success",
                    "position": current_position.tolist(),
                    "drift_detected": True,
                    "suggested_position": position,
                    "message": "Drift detected. Please scan a QR code to confirm your position."
                })

            # Mettre à jour l'historique des positions
            previous_position = current_position
            position_history.append(current_position)

            return jsonify({
                "status": "success",
                "position": current_position.tolist(),
                "drift_detected": False
            })

        else:
            return jsonify({
                "status": "error",
                "message": "No position calculated from PDR"
            }), 400

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
