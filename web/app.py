from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

@app.route('/location')
def location():
    room = request.args.get('room')
    return render_template('index.html', room=room)

@app.route('/collect_sensor_data', methods=['POST'])
def collect_sensor_data():
    data = request.json
    file_path = os.path.join('..', 'data', 'sensor_data.json')

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, 'a') as f:
        json.dump(data, f)
        f.write('\n')

    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
