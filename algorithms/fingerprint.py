# This code is a copy of finalAlgo.py from Louis Royet's project on Indoor Navigation System
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
from sklearn.neighbors import KNeighborsRegressor 

# coordinates of the staircases and elevators
stair1 = np.array([11.111628329564, 49.461219385271])
stair2 = np.array([11.111567743893, 49.46132292478])
stair3 = np.array([11.110539036217, 49.460948188642])
stair4 = np.array([11.110502094597, 49.460927758279])
elev1 = np.array([11.110965447828, 49.461147209486])
elev2 = np.array([11.110972802127, 49.461149154074])

# Global variables for coordinate transformation
ORIGIN_LON, ORIGIN_LAT = 0.0, 0.0

def euclidean_distance(lon1, lat1, lon2, lat2):
    """
    Calculate the Euclidean distance between two points
    on the Earth's surface given their longitudes and latitudes
    in decimal degrees.
    
    Returns the distance in meters.
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    
    # Earth radius in meters
    radius_earth = 6371000
    
    # Convert spherical coordinates to Cartesian coordinates
    x1 = radius_earth * math.cos(lat1) * math.cos(lon1)
    y1 = radius_earth * math.cos(lat1) * math.sin(lon1)
    x2 = radius_earth * math.cos(lat2) * math.cos(lon2)
    y2 = radius_earth * math.cos(lat2) * math.sin(lon2)
    
    # Calculate Euclidean distance
    distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    return distance

def fingerprint(knntrainfile, FPfile, kP, kZ, R):
    # Lecture unique du fichier FP
    fps = pd.read_csv(FPfile, delimiter=';')
    rssi_cols = [c for c in fps.columns if c.startswith('rssi')]
    
    train = pd.read_csv(knntrainfile, delimiter=';')
    train_rssi_cols = [c for c in train.columns if c.startswith('rssi')]
    
    # Prendre l'intersection des colonnes RSSI
    common_cols = list(set(rssi_cols) & set(train_rssi_cols))
    common_cols.sort()  # Assurer l'ordre cohérent
    
    fps = fps[common_cols].values
    knnP = KNeighborsRegressor(n_neighbors=kP)
    knnZ = KNeighborsRegressor(n_neighbors=kZ)
    POSI_train = train[['long','lat']].values
    Z_train = train[['Z']].values
    RSSI_train = train[common_cols].values
    knnP.fit(RSSI_train, POSI_train)
    knnZ.fit(RSSI_train, Z_train)
    predP=knnP.predict(fps)
    predZ=knnZ.predict(fps)
    pred = np.hstack((predP,predZ))
    #Floor changes variance
    for i in range(1,pred.shape[0]-1):
        if euclidean_distance(pred[i,0],pred[i,1],stair1[0],stair1[1]) > R and \
            euclidean_distance(pred[i,0],pred[i,1],stair2[0],stair2[1]) > R and \
            euclidean_distance(pred[i,0],pred[i,1],stair3[0],stair3[1]) > R and \
            euclidean_distance(pred[i,0],pred[i,1],stair4[0],stair4[1]) > R and \
            euclidean_distance(pred[i,0],pred[i,1],elev1[0],elev1[1]) > R and \
            euclidean_distance(pred[i,0],pred[i,1],elev2[0],elev2[1]) > R and \
            pred[i,2] != pred[i-1,2] :
            pred[i,2] = pred[i-1,2]
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    # Plotting the data
    ax.plot(pred[:,0], pred[:,1], pred[:,2], color='r', marker='o', markersize=5)
    # Labeling the axes
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_zlabel('Z')
    # Title
    ax.set_title('3D Plot of long, lat and Z')
    # Show plot
    plt.show()
    return pred

# === NOUVELLES FONCTIONS AJOUTÉES ===

def set_origin(lon0: float, lat0: float):
    """
    Set the origin for local coordinate transformation.
    
    Args:
        lon0: Origin longitude in decimal degrees
        lat0: Origin latitude in decimal degrees
    """
    global ORIGIN_LON, ORIGIN_LAT
    ORIGIN_LON, ORIGIN_LAT = lon0, lat0

def ll_to_local(lon: float, lat: float) -> tuple:
    """
    Convert longitude/latitude to local meter coordinates using equirectangular approximation.
    
    Args:
        lon: Longitude in decimal degrees
        lat: Latitude in decimal degrees
    
    Returns:
        tuple: (x, y) coordinates in meters relative to origin
    """
    R = 6371000  # Earth radius (m)
    x = (lon - ORIGIN_LON) * math.cos(math.radians(ORIGIN_LAT)) * R
    y = (lat - ORIGIN_LAT) * R
    return x, y

def fingerprint_with_local_coords(knntrainfile, FPfile, kP, kZ, R):
    """
    Execute Louis Royet's fingerprint algorithm and return results in local coordinates.
    
    Args:
        knntrainfile: Path to KNN training file
        FPfile: Path to fingerprint file
        kP: Number of neighbors for position estimation
        kZ: Number of neighbors for floor estimation  
        R: Radius threshold for stair/elevator proximity
        
    Returns:
        numpy.ndarray: Array with shape (n_samples, 3) containing [x, y, floor] 
                      where x,y are in meters relative to origin
    """
    # Execute original fingerprint function
    pred_geo = fingerprint(knntrainfile, FPfile, kP, kZ, R)
    
    # Convert to local coordinates
    pred_local = np.zeros_like(pred_geo)
    for i in range(pred_geo.shape[0]):
        x, y = ll_to_local(pred_geo[i, 0], pred_geo[i, 1])
        pred_local[i, 0] = x
        pred_local[i, 1] = y
        pred_local[i, 2] = pred_geo[i, 2]  # Floor remains the same
    
    return pred_local

def get_last_position(knntrainfile, FPfile, kP, kZ, R):
    """
    Get the last estimated position in local coordinates (x, y, floor).
    
    Args:
        knntrainfile: Path to KNN training file
        FPfile: Path to fingerprint file
        kP: Number of neighbors for position estimation
        kZ: Number of neighbors for floor estimation
        R: Radius threshold for stair/elevator proximity
        
    Returns:
        tuple: (x, y, floor) where x,y are in meters and floor is integer
    """
    # Get trajectory in local coordinates
    trajectory = fingerprint_with_local_coords(knntrainfile, FPfile, kP, kZ, R)
    
    # Return last position
    last_pos = trajectory[-1]
    x, y, floor = last_pos[0], last_pos[1], int(round(last_pos[2]))
    
    return x, y, floor

# === EXEMPLE D'UTILISATION ===
if __name__ == "__main__":
    # Définir l'origine des coordonnées (coordonnées du centre du bâtiment par exemple)
    set_origin(11.110965, 49.461147)  # Près de l'ascenseur 1
    
    # Exemple d'utilisation (remplacer par vos vrais fichiers)
    train_file = "knn_train.csv"
    fp_file = "fingerprint.csv"
    
    try:
        # Méthode 1: Utiliser la fonction originale de Louis Royet
        print("=== Fonction originale de Louis Royet ===")
        pred_original = fingerprint(train_file, fp_file, kP=3, kZ=3, R=10.0)
        print(f"Dernière position (lon, lat, floor): {pred_original[-1]}")
        
        # Méthode 2: Obtenir seulement la dernière position en coordonnées locales
        print("\n=== Dernière position en coordonnées locales ===")
        x, y, floor = get_last_position(train_file, fp_file, kP=3, kZ=3, R=10.0)
        print(f"Dernière position (x, y, floor): ({x:.2f}m, {y:.2f}m, {floor})")
        
        # Méthode 3: Obtenir toute la trajectoire en coordonnées locales
        print("\n=== Trajectoire complète en coordonnées locales ===")
        trajectory_local = fingerprint_with_local_coords(train_file, fp_file, kP=3, kZ=3, R=10.0)
        print(f"Nombre de points: {len(trajectory_local)}")
        print(f"Première position (x, y, floor): ({trajectory_local[0,0]:.2f}m, {trajectory_local[0,1]:.2f}m, {int(trajectory_local[0,2])})")
        print(f"Dernière position (x, y, floor): ({trajectory_local[-1,0]:.2f}m, {trajectory_local[-1,1]:.2f}m, {int(trajectory_local[-1,2])})")
        
    except FileNotFoundError:
        print("Veuillez fournir les bons chemins vers vos fichiers de données.")
        print("Exemple d'utilisation:")
        print("set_origin(11.110965, 49.461147)")
        print("x, y, floor = get_last_position('train.csv', 'fp.csv', 3, 3, 10.0)")