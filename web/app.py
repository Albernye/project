from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

# Configuration of the Flask application
def get_project_root():
    """Return the root directory of the project"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_data_file_path():
    """Return the path to the data file"""
    project_root = get_project_root()
    data_dir = os.path.join(project_root, 'data')
    return os.path.join(data_dir, 'sensor_data.json')

@app.route('/')
def home():
    """Home page"""
    return """
    <h1>🏢 Indoor Navigation System</h1>
    <p>Scan a QR code to access a room!</p>
    <p>Or test directly: <a href="/location?room=201">/location?room=201</a></p>
    """

@app.route('/location')
def location():
    """Page for room location"""
    room = request.args.get('room')

    # Basic validation
    if not room:
        return "❌ Missing 'room' parameter", 400

    # Check if it's a valid room number
    try:
        room_num = int(room)
        if not (201 <= room_num <= 225):
            return f"❌ Room {room} not available. Available rooms: 201-225", 400
    except ValueError:
        return "❌ Invalid room number", 400
    
    return render_template('index.html', room=room)

@app.route('/collect_sensor_data', methods=['POST'])
def collect_sensor_data():
    """Collect and save sensor data"""
    try:
        # Retrieve data
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400
        
        # Add server information
        data['server_timestamp'] = datetime.now().isoformat()
        data['client_ip'] = request.remote_addr
        
        # Prepare the file
        file_path = get_data_file_path()
        data_dir = os.path.dirname(file_path)

        # Create the data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)

        # Save the data (JSONL format - one line per entry)
        with open(file_path, 'a', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
            f.write('\n')

        print(f"✅ Data saved: {file_path}")
        print(f"📱 Room: {data.get('room', 'unknown')}")

        return jsonify({
            "status": "success",
            "message": "Data collected successfully",
            "timestamp": data['server_timestamp']
        })
        
    except Exception as e:
        print(f"❌ Error during collection: {e}")
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }), 500

@app.route('/data')
def view_data():
    """Endpoint to view collected data (debug)"""
    try:
        file_path = get_data_file_path()
        
        if not os.path.exists(file_path):
            return jsonify({"message": "No data collected yet"})
        
        # Read JSONL data
        data_entries = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data_entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        return jsonify({
            "total_entries": len(data_entries),
            "last_10_entries": data_entries[-10:] if data_entries else []
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🌐 Démarrage du serveur Flask...")
    print("📡 Serveur accessible sur :")
    print("   - http://localhost:5000")
    print("   - http://127.0.0.1:5000")
    print("🔗 Page test : http://localhost:5000/location?room=201")
    print("📊 Données collectées : http://localhost:5000/data")
    app.run(host='0.0.0.0', port=5000, debug=True)