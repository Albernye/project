import pytest
from unittest.mock import patch, MagicMock
import json
import csv
from web.app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_position(client):
    """Test endpoint /position avec paramètre room requis"""
    with patch("web.app.get_latest_positions", return_value=((1.0, 2.0, 0.0), (1.0, 2.0, 0.0), (1.0, 2.0, 0.0))):
        with patch("web.app.fuse", return_value=[1.0, 2.0, 0.0]):
            # Test avec paramètre room
            resp = client.get('/position?room=201')
            assert resp.status_code == 200
            
            data = json.loads(resp.data)
            assert 'position' in data
            assert 'timestamp' in data
            assert 'sources' in data
            assert isinstance(data['position'], list)
            assert len(data['position']) == 3  # [x, y, z] ou [lat, lon, alt]

def test_position_missing_room(client):
    """Test endpoint /position sans paramètre room (doit échouer)"""
    resp = client.get('/position')
    assert resp.status_code == 400
    
    data = json.loads(resp.data)
    assert 'error' in data
    assert 'Missing \'room\' parameter' in data['error']

def test_position_with_different_rooms(client):
    """Test endpoint /position avec différents formats de numéro de salle"""
    test_rooms = ['201', '2-01', '15', '301']
    
    with patch("web.app.get_latest_positions", return_value=((1.0, 2.0, 0.0), (1.0, 2.0, 0.0), None)):
        with patch("web.app.fuse", return_value=[1.0, 2.0, 0.0]):
            for room in test_rooms:
                resp = client.get(f'/position?room={room}')
                assert resp.status_code == 200
                
                data = json.loads(resp.data)
                assert 'position' in data
                assert isinstance(data['position'], list)

def test_route(client):
    """Test endpoint /route"""
    mock_pathfinder_instance = MagicMock()
    mock_pathfinder_instance.find_shortest_path.return_value = {
        'path': ['2-01', 'corridor_point_1', '2-02'],
        'distance': 15.5,
        'segment_distances': [7.5, 8.0]
    }
    
    with patch("web.app.pathfinder", mock_pathfinder_instance), \
         patch("web.app.get_node_position") as mock_get_pos, \
             patch("web.app.corridor_data", new={'graph': {'nodes': [], 'edges': []}, 'corridor_structure': {'corridor1': {'points': [['corridor_point_1', 0, 0]]}}}):
        
        mock_get_pos.side_effect = [
                [10.0, 20.0],   # 2-01
                [15.0, 25.0],   # corridor_point_1 (premier segment)
                [15.0, 25.0],   # corridor_point_1 (second segment)
                [20.0, 30.0]    # 2-02
            ]
        
        resp = client.get('/route?from=01&to=02')
        assert resp.status_code == 200
        
        data = json.loads(resp.data)
        assert 'type' in data
        assert data['type'] == 'FeatureCollection'
        assert 'features' in data
        assert 'total_distance' in data
        assert 'path' in data
        
        mock_pathfinder_instance.find_shortest_path.assert_called_once_with('2-01', '2-02')

def test_route_missing_params(client):
    """Test endpoint /route sans paramètres requis"""
    # Test sans paramètres
    resp = client.get('/route')
    assert resp.status_code == 400
    
    # Test avec seulement 'from'
    resp = client.get('/route?from=01')
    assert resp.status_code == 400
    
    # Test avec seulement 'to'
    resp = client.get('/route?to=02')
    assert resp.status_code == 400

def test_route_pathfinder_unavailable(client):
    """Test endpoint /route quand pathfinder n'est pas disponible"""
    with patch("web.app.pathfinder", None):
        resp = client.get('/route?from=01&to=02')
        assert resp.status_code == 503
        
        data = json.loads(resp.data)
        assert 'error' in data
        assert 'Système de navigation indisponible' in data['error']

def test_home(client):
    """Test endpoint home"""
    resp = client.get('/')
    assert resp.status_code == 200
    # Convertir en string pour la comparaison
    content = resp.data.decode('utf-8')
    assert 'Système de Navigation Indoor' in content

def test_location(client):
    """Test endpoint /location avec paramètre room"""
    with patch("web.app.render_template", return_value="<html>Test</html>"):
        resp = client.get('/location?room=201')
        assert resp.status_code == 200

def test_location_missing_room(client):
    """Test endpoint /location sans paramètre room"""
    resp = client.get('/location')
    assert resp.status_code == 400
    content = resp.data.decode('utf-8')
    assert 'Missing \'room\' parameter' in content

def test_location_invalid_room(client):
    """Test endpoint /location avec numéro de salle invalide"""
    resp = client.get('/location?room=invalid')
    assert resp.status_code == 400
    content = resp.data.decode('utf-8')
    assert 'Invalid room number' in content

def test_collect_sensor_data(client):
    """Test endpoint /collect_sensor_data"""
    test_data = {
        'room': '201',
        'accelerometer': [{'x': 1.0, 'y': 2.0, 'z': 3.0}],
        'gyroscope': [{'x': 0.1, 'y': 0.2, 'z': 0.3}],
        'magnetometer': [{'x': 10.0, 'y': 20.0, 'z': 30.0}]
    }
    
    with patch("web.app.record_realtime", return_value=True):
        resp = client.post('/collect_sensor_data', 
                          data=json.dumps(test_data),
                          content_type='application/json')
        assert resp.status_code == 200
        
        data = json.loads(resp.data)
        assert data['status'] == 'success'
        assert 'room' in data

def test_collect_sensor_data_no_data(client):
    """Test endpoint /collect_sensor_data sans données"""
    # Test avec données vides
    resp = client.post('/collect_sensor_data', 
                      data=json.dumps({}),
                      content_type='application/json')
    
    # Le serveur peut retourner 400 ou 500 selon l'implémentation
    # Vérifions qu'il y a bien une erreur
    assert resp.status_code in [400, 500]
    
    # Test avec pas de données du tout
    resp = client.post('/collect_sensor_data')
    assert resp.status_code in [400, 500]

def test_update_position(client):
    """Test endpoint /update_position"""
    test_data = {
        'room': '201',
        'accelerometer': [{'x': 1.0, 'y': 2.0, 'z': 3.0}]
    }
    
    with patch("web.app.record_realtime", return_value=True):
        with patch("web.app.get_latest_positions", return_value=(None, None, None)):
            with patch("web.app.fuse", return_value=[1.0, 2.0, 0.0]):
                resp = client.post('/update_position', 
                                  data=json.dumps(test_data),
                                  content_type='application/json')
                assert resp.status_code == 200
                
                data = json.loads(resp.data)
                assert data['status'] == 'success'
                assert 'position' in data

def test_confirm_position(client):
    """Test endpoint /confirm_position"""
    test_data = {
        'room': '201',
        'position': [1.0, 2.0, 0.0]
    }
    
    with patch("web.app.reset_kalman"):
        resp = client.post('/confirm_position', 
                          data=json.dumps(test_data),
                          content_type='application/json')
        assert resp.status_code == 200
        
        data = json.loads(resp.data)
        assert data['status'] == 'success'
        assert 'position' in data

def test_confirm_position_missing_room(client):
    """Test endpoint /confirm_position sans paramètre room"""
    test_data = {}
    
    resp = client.post('/confirm_position', 
                      data=json.dumps(test_data),
                      content_type='application/json')
    assert resp.status_code == 400

def test_health_check(client):
    """Test endpoint /health"""
    resp = client.get('/health')
    assert resp.status_code == 200
    
    data = json.loads(resp.data)
    assert 'status' in data
    assert data['status'] == 'healthy'
    assert 'timestamp' in data
    assert 'pathfinder_available' in data
    assert 'corridor_data_loaded' in data

def test_data_endpoint(client):
    """Test endpoint /data"""
    # Test quand le fichier n'existe pas
    with patch("web.app.Path") as mock_path_class:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_class.return_value.__truediv__.return_value.__truediv__.return_value = mock_path_instance
        
        resp = client.get('/data')
        assert resp.status_code == 200
        
        data = json.loads(resp.data)
        assert 'message' in data
        assert data['message'] == 'No data collected yet'
    
    # Test quand le fichier existe
    with patch("web.app.Path") as mock_path_class:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_class.return_value.__truediv__.return_value.__truediv__.return_value = mock_path_instance
        
        # Mock du contenu du fichier CSV
        mock_csv_content = [
            {'timestamp': '2023-01-01', 'x': '1.0', 'y': '2.0'},
            {'timestamp': '2023-01-02', 'x': '1.1', 'y': '2.1'}
        ]
        
        with patch("builtins.open", create=True) as mock_open:
            with patch("csv.DictReader", return_value=mock_csv_content):
                resp = client.get('/data')
                assert resp.status_code == 200
                
                data = json.loads(resp.data)
                assert 'total_entries' in data
                assert 'last_10_entries' in data
                assert 'data_file' in data

def test_normalize_room_id():
    """Test de la fonction normalize_room_id"""
    from web.app import normalize_room_id
    
        # Test cas normaux
    assert normalize_room_id('201') == '2-01'
    assert normalize_room_id('2-01') == '2-01'
    assert normalize_room_id('15') == '2-15'
    assert normalize_room_id('301') == '3-01'
    
    # Test cas invalides
    assert normalize_room_id('invalid') is None
    assert normalize_room_id('') is None
    assert normalize_room_id(None) is None
    assert normalize_room_id('1-invalid') is None

if __name__ == '__main__':
    pytest.main([__file__])
