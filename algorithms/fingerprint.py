# This code is a copy of finalAlgo.py from Louis Royet's project on Indoor Navigation System

import pandas as pd
import numpy as np
import glob
import os
import warnings
import math
import csv
import matplotlib.pyplot as plt
from scipy.signal import butter
import scipy.linalg
from sklearn.neighbors import KNeighborsRegressor 

# coordinates of the staircases and elevators
stair1 = np.array([11.111628329564, 49.461219385271])
stair2 = np.array([11.111567743893, 49.46132292478])
stair3 = np.array([11.110539036217, 49.460948188642])
stair4 = np.array([11.110502094597, 49.460927758279])
elev1 = np.array([11.110965447828, 49.461147209486])
elev2 = np.array([11.110972802127, 49.461149154074])


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
