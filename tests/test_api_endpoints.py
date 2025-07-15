import pytest
from flask import Flask
import json
import os
import sys

# Ajoute le chemin du projet pour l'import de app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'web')))
from web.app import app as flask_app

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client

def test_position(client):
    resp = client.get('/position')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'position' in data

def test_route(client):
    resp = client.get('/route?from=201&to=202')
    assert resp.status_code in (200, 404)  # 404 si pas de chemin
    data = resp.get_json()
    assert 'features' in data or 'error' in data

def test_collect_sensor_data(client):
    payload = {
        "room": "201",
        "accelerometer": [{"x": 0, "y": 1, "z": 0}]
    }
    resp = client.post('/collect_sensor_data', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'success'

def test_update_position(client):
    payload = {"room": "201"}
    resp = client.post('/update_position', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'success'

def test_confirm_position(client):
    payload = {"room": "201", "position": [41.406, 2.195]}
    resp = client.post('/confirm_position', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'success'
