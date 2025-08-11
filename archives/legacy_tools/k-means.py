import numpy as np
from sklearn.cluster import KMeans
from sklearn.neighbors import KNeighborsRegressor 
from sklearn.neighbors import KNeighborsClassifier
import pandas as pd
import glob
import joblib
import warnings
import math
import csv
import matplotlib.pyplot as plt
from scipy.spatial.distance import cdist
import time


def find_relevant_clusters(clusters, rho):
    num_clusters = len(clusters)
    num_aps = clusters[0].shape[1]  # assuming all fingerprints have the same number of APs

    # Dictionary to store relevant clusters for each AP
    relevant_clusters = {i: [] for i in range(num_aps)}

    # Iterate over each cluster
    for cluster_idx, cluster in enumerate(clusters):
        # Iterate over each fingerprint in the cluster
        for fingerprint in cluster:
            r_max = np.max(fingerprint)  # Find the maximum RSS value in the fingerprint
            
            # Check each AP
            for ap_idx in range(num_aps):
                if abs(r_max - fingerprint[ap_idx]) <= rho:
                    relevant_clusters[ap_idx].append(cluster_idx)
                    
    
    for ap_idx in relevant_clusters:
        relevant_clusters[ap_idx] = list(set(relevant_clusters[ap_idx]))
    # Identify operative APs
    operative_aps = [ap for ap, clusters in relevant_clusters.items() if clusters]

    return relevant_clusters, operative_aps


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


def variant3Nur(num_clusters, rho, knn_k, trainfile, testfile):
    start_time = time.time()
    data = pd.read_csv(trainfile, delimiter= ';')
    
    fingerprints = data.drop(columns=['time','long','lat']).values
    POSI_fing = data.drop(columns=['time']).values
    
    kmeans = KMeans(num_clusters)
    kmeans.fit(fingerprints)
    
    cluster_labels = kmeans.labels_
    cluster_centers = kmeans.cluster_centers_
    clusters = [[] for _ in range(num_clusters)]
    clustersf1 = [[] for _ in range(num_clusters)]

# Iterate over each data point and assign it to the corresponding cluster
    for i, label in enumerate(cluster_labels):
        clusters[label].append(POSI_fing[i])
        clustersf1[label].append(fingerprints[i])
    

    clusters_arr = [np.vstack(cluster) for cluster in clusters]
    clustersf1_arr = [np.vstack(cluster) for cluster in clustersf1]

    relevant_clusters, operative_aps=find_relevant_clusters(clustersf1_arr, rho)
#print(relevant_clusters)
    
    knn_models = []
    
    for cluster in clusters_arr:
        RSSI = cluster[:, 2:]
        POSI = cluster[:, :2]
    
        if cluster.shape[0]>=knn_k:
            
            knn = KNeighborsRegressor(n_neighbors=knn_k)
            knn.fit(RSSI, POSI)
    
            knn_models.append(knn)
        
        
        else:
        
            knn = KNeighborsRegressor(n_neighbors=cluster.shape[0])
            knn.fit(RSSI, POSI)
        
            knn_models.append(knn)
    
    test = pd.read_csv(testfile, delimiter=';')
    test_rssi = test.drop(columns=['time','long','lat']).values
    actual_posi = test[['long','lat']].values
    
    n_items=fingerprints.shape[0]
    oversize_thresh=4*(n_items/num_clusters)
    
    predicted_posi = []

    for fp in test_rssi:
        op_idx = np.argmax(fp)
        relevant_cluster_indices = relevant_clusters[op_idx]

        min_distance = float('inf')
        best_cluster_idx = -1
    
        for cluster_idx in relevant_cluster_indices:
            centroid = cluster_centers[cluster_idx]
        
            distance = np.linalg.norm(fp - centroid)
        
            if distance < min_distance:
                min_distance = distance
                best_cluster_idx = cluster_idx
    
    #if the cluster is oversized
        if clustersf1_arr[best_cluster_idx].shape[0] >= oversize_thresh : 
            kmeansub = KMeans(5)
            kmeansub.fit(clustersf1_arr[best_cluster_idx])

            cluster_labelsub = kmeansub.labels_
            cluster_centersub = kmeansub.cluster_centers_
            clustersub = [[] for _ in range(5)]
            clustersubf1 = [[] for _ in range(5)]

        # Iterate over each data point and assign it to the corresponding cluster
            for i, label in enumerate(cluster_labelsub):
                clustersub[label].append(clusters_arr[best_cluster_idx][i])
                clustersubf1[label].append(clustersf1_arr[best_cluster_idx][i])
    

            clustersub_arr = [np.vstack(cluster) for cluster in clustersub]
            clustersubf1_arr = [np.vstack(cluster) for cluster in clustersubf1]
        
        #for i in range(5):
        #    print(clustersubf1_arr[i].shape)
        
            relevant_clustersub, operative_apsub=find_relevant_clusters(clustersubf1_arr, rho)

            knn_modelsub = []

        # Iterate over each cluster and create a kNN model
            for cluster in clustersub_arr:
                RSSIsub = cluster[:, 2:]
                POSIsub = cluster[:, :2]
            
                if cluster.shape[0]>=knn_k:
            
                    knnsub = KNeighborsRegressor(n_neighbors=knn_k)
                    knnsub.fit(RSSIsub, POSIsub)
    
                    knn_modelsub.append(knnsub)
        
        
                else:
        
                    knnsub = KNeighborsRegressor(n_neighbors=cluster.shape[0])
                    knnsub.fit(RSSIsub, POSIsub)
    
                    knn_modelsub.append(knnsub)
            
          
            relevant_cluster_indicesub = relevant_clustersub[op_idx]

            min_distance_sub = float('inf')
            best_cluster_idx_sub = -1
    
            for cluster_idx in relevant_cluster_indicesub:
                centroid = cluster_centersub[cluster_idx]
        
                distance_sub = np.linalg.norm(fp - centroid)
        
                if distance_sub < min_distance_sub:
                    min_distance_sub = distance_sub
                    best_cluster_idx_sub = cluster_idx
                
            pred = knn_modelsub[best_cluster_idx_sub].predict(fp.reshape(1, -1))
            predicted_posi.append(pred)
        
            
        else:
            pred = knn_models[best_cluster_idx].predict(fp.reshape(1, -1))
            predicted_posi.append(pred)
    
    predicted_posi = np.vstack(predicted_posi)

    distances_test=[euclidean_distance(predicted_posi[i][0], predicted_posi[i][1], actual_posi[i][0], actual_posi[i][1]) for i in range(len(predicted_posi))]
    mean=np.mean(distances_test)
    print(mean)
    end_time = time.time()
    time_spent = end_time - start_time
    print('loop time : ',time_spent)
    return mean, time_spent
    

