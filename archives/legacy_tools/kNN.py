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

def euclidean_distance_3d(lon1, lat1, z1, lon2, lat2, z2):
    """
    Calculate the Euclidean distance between two points in 3D space
    given their longitudes, latitudes in decimal degrees, and altitudes in meters.

    Returns the distance in meters.
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    
    # Earth radius in meters
    radius_earth = 6371000
    
    # Convert spherical coordinates to Cartesian coordinates
    x1 = radius_earth * math.cos(lat1) * math.cos(lon1)
    y1 = radius_earth * math.cos(lat1) * math.sin(lon1)
    z1 = z1  # altitude in meters
    
    x2 = radius_earth * math.cos(lat2) * math.cos(lon2)
    y2 = radius_earth * math.cos(lat2) * math.sin(lon2)
    z2 = z2  # altitude in meters
    
    # Calculate Euclidean distance in 3D
    distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)
    
    return distance

def kNN(k, trainfile, testfile):

    knn = KNeighborsRegressor(n_neighbors=k) 
    train = pd.read_csv(trainfile, delimiter=';')
    POSI_train = train[['long','lat','Z']].values
    RSSI_train = train.drop(columns=['time','long', 'lat','Z']).values

    test = pd.read_csv(testfile, delimiter=';')
    fps = test[...] #select the fingerprints from the csv file, it varies from one to another
    POSI = test[...]
     
    knn.fit(RSSI_train, POSI_train)

    pred=knn.predict(fps)

    distances=[euclidean_distance_3d(pred[i][0], pred[i][1], pred[i][2], POSI[i,0], POSI[i,1], POSI[i,2]) for i in range(len(pred))]
    mean=np.mean(distances) 

    return mean

