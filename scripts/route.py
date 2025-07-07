import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_conn():
    # Adapt connection parameters as needed
    return psycopg2.connect(
        dbname="city_routing",
        user=os.getenv("PGUSER", "user"),
        password=os.getenv("PGPASSWORD", "user"),
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432")
    )

def route_between(start_id: int, end_id: int):
    """
    Compute shortest path between two nodes using pgRouting and return GeoJSON.
    """
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # First, check if the nodes exist
        print(f"🔍 Checking if nodes {start_id} and {end_id} exist...")
        cur.execute("SELECT id FROM public.indoor_lines WHERE source = %s OR target = %s", (start_id, start_id))
        start_exists = cur.fetchone()
        cur.execute("SELECT id FROM public.indoor_lines WHERE source = %s OR target = %s", (end_id, end_id))
        end_exists = cur.fetchone()
        
        print(f"Start node {start_id} exists: {start_exists is not None}")
        print(f"End node {end_id} exists: {end_exists is not None}")
        
        if not start_exists or not end_exists:
            print("❌ One or both nodes don't exist in the graph")
            # Return empty but valid GeoJSON
            return {
                'type': 'FeatureCollection', 
                'features': [{
                    'type': 'Feature',
                    'geometry': {'type': 'LineString', 'coordinates': []},
                    'properties': {'start': start_id, 'end': end_id, 'error': 'Nodes not found'}
                }]
            }
        
        # Try the routing query
        sql = """
        SELECT di.seq, di.node, di.edge, di.cost,
               ST_AsGeoJSON(l.geom)::json AS geom
        FROM pgr_dijkstra(
            'SELECT id, source, target, cost, reverse_cost FROM public.indoor_lines',
            %s, %s, directed := false
        ) AS di
        JOIN public.indoor_lines AS l
        ON di.edge = l.id
        ORDER BY di.seq;
        """
        
        print(f"🔍 Executing pgRouting query from {start_id} to {end_id}...")
        cur.execute(sql, (start_id, end_id))
        rows = cur.fetchall()
        
        print(f"📊 pgRouting returned {len(rows)} rows")
        
        if not rows:
            print("❌ No route found between these nodes")
            # Return empty but valid GeoJSON
            return {
                'type': 'FeatureCollection', 
                'features': [{
                    'type': 'Feature',
                    'geometry': {'type': 'LineString', 'coordinates': []},
                    'properties': {'start': start_id, 'end': end_id, 'error': 'No route found'}
                }]
            }
        
        # Build a single LineString from all segments
        coords = []
        for i, row in enumerate(rows):
            geom = row['geom']
            print(f"Row {i}: edge={row['edge']}, geom_type={geom.get('type')}, coords_count={len(geom.get('coordinates', []))}")
            
            if geom['type'] == 'LineString':
                # For LineString, coordinates is an array of [lon, lat] pairs
                if i == 0:
                    # First segment: add all coordinates
                    coords.extend(geom['coordinates'])
                else:
                    # Subsequent segments: skip first coordinate to avoid duplication
                    coords.extend(geom['coordinates'][1:])
            elif geom['type'] == 'Point':
                # For Point, coordinates is a single [lon, lat] pair
                coords.append(geom['coordinates'])
        
        print(f"📍 Final coordinates count: {len(coords)}")
        
        feature = {
            'type': 'Feature',
            'geometry': {'type': 'LineString', 'coordinates': coords},
            'properties': {'start': start_id, 'end': end_id}
        }
        
        return {'type': 'FeatureCollection', 'features': [feature]}
        
    except Exception as e:
        print(f"❌ Error in route_between: {e}")
        # Return empty but valid GeoJSON with error info
        return {
            'type': 'FeatureCollection', 
            'features': [{
                'type': 'Feature',
                'geometry': {'type': 'LineString', 'coordinates': []},
                'properties': {'start': start_id, 'end': end_id, 'error': str(e)}
            }]
        }
    finally:
        conn.close()

if __name__ == '__main__':
    # Simple CLI test
    import sys
    if len(sys.argv) != 3:
        print('Usage: route.py <start_id> <end_id>')
        sys.exit(1)
    start, end = map(int, sys.argv[1:])
    gj = route_between(start, end)
    print(json.dumps(gj, indent=2))