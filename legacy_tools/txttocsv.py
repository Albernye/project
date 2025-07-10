import glob
import os
import numpy as np
import csv
import pandas as pd
import matplotlib.pyplot as plt
import math
import warnings


def latlon_to_cartesian(latitudes, longitudes):
    # Assume the first point as the origin
    origin_lat = latitudes[0]
    origin_lon = longitudes[0]
    
    cartesian_coords = [(0, 0)]  # The first point is the origin
    
    for lat, lon in zip(latitudes[1:], longitudes[1:]):
        # Calculate distance from the origin to the current point
        distance = haversine_distance(origin_lat, origin_lon, lat, lon)
        
        # Calculate the angle from the origin to the current point
        angle = math.atan2(lat - origin_lat, lon - origin_lon)
        
        # Convert polar coordinates (distance, angle) to Cartesian coordinates (x, y)
        x = distance * math.cos(angle)
        y = distance * math.sin(angle)
        
        cartesian_coords.append((x, y))
    
    return cartesian_coords

def haversine_distance(lat1, lon1, lat2, lon2):


    # Radius of the Earth in kilometers
    R = 6371.0
    
    # Convert latitude and longitude from degrees to radians
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)
    
    # Compute the differences between latitudes and longitudes
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    # Distance in kilometers
    distance = R * c
    return distance

def txttoFPCSV (txtfilepath, csvfilepath):
    testingsets = glob.glob(os.path.join(txtfilepath,  '*.txt')) 

    for testingset in testingsets:    
        with open(testingset, 'r') as file:
            timestamp=[]
            indexPOSI=[]
            lengyro=0
            timeWIFI=[]
            timeWIFIindex=[]
            WIFI_MAC=[]
            WIFI_DB=[]
            POSI_LAT=[]
            POSI_LONG=[]
            POSI_Z=[]
            for line in file:
            
                if line[:4] == "POSI":
                    indexPOSI.append(lengyro)
                    seg=line.split(';')
                    POSI_LAT.append(float(seg[3]))
                    POSI_LONG.append(float(seg[4]))
                    POSI_Z.append(float(seg[5])*4+8)
                
                if line[:4] == "GYRO":
                    lengyro+=1
                
                if line[:4] == "WIFI":
                    seg=line.split(';')
                    if float(seg[1]) not in timeWIFI:
                        timeWIFIindex.append(lengyro)
                    timeWIFI.append(float(seg[1]))
                    WIFI_MAC.append(seg[4])
                    WIFI_DB.append(float(seg[6]))
                
            
#============== Same approximation with latitude and longitude =============
 
        POSI_lat_approx = []
        POSI_long_approx = []
        POSI_Z_approx= []

        for i in range(indexPOSI[0] - 1):
            POSI_lat_approx.append(POSI_LAT[0])
            POSI_long_approx.append(POSI_LONG[0])
            POSI_Z_approx.append(POSI_Z[0])

        for i in range(len(POSI_LONG) - 1):
            if i == 0:
                POSI_lat_approx.append(POSI_LAT[i])
                POSI_long_approx.append(POSI_LONG[i])
                POSI_Z_approx.append(POSI_Z[i])

            num_pts = indexPOSI[i + 1] - indexPOSI[i]
            distz= POSI_Z[i+1] - POSI_Z[i]
            dist = ((POSI_LONG[i + 1] - POSI_LONG[i]) ** 2 + (POSI_LAT[i + 1] - POSI_LAT[i]) ** 2) ** 0.5
            if distz != 0 and dist != 0:
                step_distz = distz / num_pts               
                angle = math.atan2(POSI_LAT[i + 1] - POSI_LAT[i], POSI_LONG[i + 1] - POSI_LONG[i])
                step_dist = dist / num_pts
                for j in range(1, num_pts):
                    new_lat = POSI_lat_approx[-1] + step_dist * math.sin(angle)
                    new_long = POSI_long_approx[-1] + step_dist * math.cos(angle)
                    new_Z= POSI_Z_approx[-1]+step_distz
                    POSI_lat_approx.append(new_lat)
                    POSI_long_approx.append(new_long)
                    POSI_Z_approx.append(new_Z)
            elif distz == 0 and dist != 0:
                angle = math.atan2(POSI_LAT[i + 1] - POSI_LAT[i], POSI_LONG[i + 1] - POSI_LONG[i])
                step_dist = dist / num_pts
                lastPOSI_Z_approx = POSI_Z_approx[-1]
                for j in range(1, num_pts):
                    new_lat = POSI_lat_approx[-1] + step_dist * math.sin(angle)
                    new_long = POSI_long_approx[-1] + step_dist * math.cos(angle)
                    POSI_lat_approx.append(new_lat)
                    POSI_long_approx.append(new_long)
                    POSI_Z_approx.append(lastPOSI_Z_approx)
            elif distz != 0 and dist == 0: 
                lastPOSI_lat_approx = POSI_lat_approx[-1]
                lastPOSI_long_approx = POSI_long_approx[-1]
                step_distz = distz / num_pts
                for j in range(1, num_pts):
                    new_Z= POSI_Z_approx[-1]+step_distz
                    POSI_Z_approx.append(new_Z)
                    POSI_lat_approx.append(lastPOSI_lat_approx)
                    POSI_long_approx.append(lastPOSI_long_approx)
            else:
                for j in range(1, num_pts):
                    POSI_lat_approx.append(POSI_LAT[i])
                    POSI_long_approx.append(POSI_LONG[i])
                    POSI_Z_approx.append(POSI_Z[i])

        lastPOSI_lat_approx = POSI_LAT[-1]
        lastPOSI_long_approx = POSI_LONG[-1]
        lastPOSI_Z_approx = POSI_Z[-1]

        POSI_lat_approx.append(lastPOSI_lat_approx)
        POSI_long_approx.append(lastPOSI_long_approx)
        POSI_Z_approx.append(lastPOSI_Z_approx)

# Assuming lengyro is the length you want POSI_lat_approx and POSI_long_approx to be extended to
        for i in range(len(POSI_lat_approx), lengyro):
            POSI_lat_approx.append(lastPOSI_lat_approx)
            POSI_long_approx.append(lastPOSI_long_approx)
            POSI_Z_approx.append(lastPOSI_Z_approx)
        
            
#=========================== Sorting data =================================    

        DataWIFI=[WIFI_MAC, WIFI_DB]
           
         
            
#=========================== Dealing with WIFI data ========================

        headerWIFI=['time','long','lat','Z']
        
        timeWIFI_norep=[]
        for time in timeWIFI:
            if time not in  timeWIFI_norep:
                 timeWIFI_norep.append(time)
        
        for address in WIFI_MAC:
            if address not in headerWIFI:
                headerWIFI.append(address)
        
        WIFI_DATApos=[]

        for i in range(len(WIFI_DB)):
            WIFI_DATApos.append({'timestamp': timeWIFI[i], 'MAC': WIFI_MAC[i], 'value': WIFI_DB[i]})
    
        data_dict = {}

# Populate the dictionary
        for entry in WIFI_DATApos:
            timestamp = entry['timestamp']
            mac = entry['MAC']
            value = entry['value']
    
            if timestamp not in data_dict:
                data_dict[timestamp] = {}
            data_dict[timestamp][mac] = value

# Convert the dictionary to a DataFrame
        df = pd.DataFrame.from_dict(data_dict, orient='index').sort_index()

        df = df.fillna(-100) #if the wifi access is not found

# To convert the DataFrame to a NumPy array
        WIFI_TABpos = df.values
        
        LONG=[]
        LAT=[]
        Z=[]
        
        for i in range(len(timeWIFIindex)):
            LONG.append(POSI_long_approx[timeWIFIindex[i]])
            LAT.append(POSI_lat_approx[timeWIFIindex[i]])
            if POSI_Z_approx[timeWIFIindex[i]] <= 0.5:
                Z.append(0)
                
            elif 0.5 < POSI_Z_approx[timeWIFIindex[i]] <=3.5:
                Z.append(POSI_Z_approx[timeWIFIindex[i]])
                
            elif 3.5 < POSI_Z_approx[timeWIFIindex[i]] <=4.5:   
                Z.append(4)
            
            elif 4.5 < POSI_Z_approx[timeWIFIindex[i]] <=7.5:
                Z.append(POSI_Z_approx[timeWIFIindex[i]])
                
            else:
                Z.append(8)
        
        
        firstcolL=[timeWIFI_norep,LONG,LAT,Z]
        firstcol=np.array(firstcolL)
        firstcol=np.transpose(firstcol)
        
        WIFI_FIN=np.hstack((firstcol, WIFI_TABpos))
        
#======================= CSV wifi files ===================================

        with open(csvfilepath+testingset[-31:-4]+'WIFI.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            writer.writerow(headerWIFI)
            for row in WIFI_FIN:
                writer.writerow(row)    

def txttoIMUCSV (txtfilepath, csvfilepath):
    Header = ['time','long','lat','Z','POSI_X','POSI_Y','ACCE_X','ACCE_Y','ACCE_Z','MOD_ACCE','GYRO_X','GYRO_Y','GYRO_Z','MOD_GYRO','MAGN_X',\
          'MAGN_Y','MAGN_Z','MOD_MAGN','AHRS_X','AHRS_Y','AHRS_Z',\
          'AHRS_Q2','AHRS_Q3','AHRS_Q4','GNSS_LAT','GNSS_LONG'] 

    testingsets = glob.glob(os.path.join(txtfilepath,  '*.txt')) 

    for testingset in testingsets:
        with open(testingset, 'r') as file:    
            timestamp=[]
            ACCE_X=[]
            ACCE_MOD=[]
            GYRO_MOD=[]
            MAGN_MOD=[]
            ACCE_Y=[]
            ACCE_Z=[]
            indexPOSI=[]
            lengyro=1
            GYRO_X=[]
            GYRO_Y=[]
            GYRO_Z=[]
            MAGN_X=[]
            MAGN_Y=[]
            MAGN_Z=[]
            AHRS_X=[]
            AHRS_Y=[]
            AHRS_Z=[]
            AHRS_Q2=[]
            AHRS_Q3=[]
            AHRS_Q4=[]
            POSI_LAT=[]
            POSI_LONG=[]
            POSI_Z=[]
            GNSS_LAT=[]
            GNSS_LONG=[]
            POSI_X=[]
            POSI_Y=[]
        
            for line in file:
            
                if line[:4] == "POSI":
                    indexPOSI.append(lengyro)
                    seg=line.split(';')
                    POSI_LAT.append(float(seg[3]))
                    POSI_LONG.append(float(seg[4]))
                    POSI_Z.append(4*int(seg[5])+8)
                
                if line[:4] == "ACCE":
                    seg=line.split(';')
                    lenACCE=len(ACCE_X)
                    if lenACCE!=0:
                        lastACCE_X=ACCE_X[-1]
                        lastACCE_Y=ACCE_Y[-1]
                        lastACCE_Z=ACCE_Z[-1]
                        lastACCE_MOD=ACCE_MOD[-1]
                        for i in range (lenACCE,(lengyro-1)):
                            ACCE_X.append(lastACCE_X)
                            ACCE_Y.append(lastACCE_Y)
                            ACCE_Z.append(lastACCE_Z)
                            ACCE_MOD.append(lastACCE_MOD)
                    else:
                        for i in range (lengyro-1):
                            ACCE_X.append(None)
                            ACCE_Y.append(None)
                            ACCE_Z.append(None)
                            ACCE_MOD.append(None)
                    ACCE_X.append(float(seg[3]))
                    ACCE_Y.append(float(seg[4]))
                    ACCE_Z.append(float(seg[5]))
                    ACCE_MOD.append(math.sqrt(float(seg[3])**2 + float(seg[4])**2 + float(seg[5])**2))

                if line[:4] == "GYRO":
                    seg=line.split(';')
                    if len(GYRO_X)==0:
                        timestamp.append(float(seg[1]))
                        GYRO_X.append(float(seg[3]))
                        GYRO_Y.append(float(seg[4]))
                        GYRO_Z.append(float(seg[5]))
                        GYRO_MOD.append(math.sqrt(float(seg[3])**2 + float(seg[4])**2 + float(seg[5])**2))
                    
                    else:
                        timestamp.append(float(seg[1]))
                        GYRO_X.append(float(seg[3]))
                        GYRO_Y.append(float(seg[4]))
                        GYRO_Z.append(float(seg[5]))
                        GYRO_MOD.append(math.sqrt(float(seg[3])**2 + float(seg[4])**2 + float(seg[5])**2))
                        lengyro+=1
                
                if line[:4] == "MAGN":
                    seg=line.split(';')
                    lenMAGN=len(MAGN_X)
                    if lenMAGN!=0:
                        lastMAGN_X=MAGN_X[-1]
                        lastMAGN_Y=MAGN_Y[-1]
                        lastMAGN_Z=MAGN_Z[-1]
                        lastMAGN_MOD=MAGN_MOD[-1]
                        for i in range (lenMAGN,(lengyro-1)):
                            MAGN_X.append(lastMAGN_X)
                            MAGN_Y.append(lastMAGN_Y)
                            MAGN_Z.append(lastMAGN_Z)
                            MAGN_MOD.append(lastMAGN_MOD)
                    else:
                        for i in range (lengyro-1):
                            MAGN_X.append(None)
                            MAGN_Y.append(None)
                            MAGN_Z.append(None)
                            MAGN_MOD.append(None)
                    MAGN_X.append(float(seg[3]))
                    MAGN_Y.append(float(seg[4]))
                    MAGN_Z.append(float(seg[5]))
                    MAGN_MOD.append(math.sqrt(float(seg[3])**2 + float(seg[4])**2 + float(seg[5])**2))
                
                
                if line[:4] == "AHRS":
                    seg=line.split(';')
                    lenAHRS=len(AHRS_X)
                    if lenAHRS!=0:
                        lastAHRS_X=AHRS_X[-1]
                        lastAHRS_Y=AHRS_Y[-1]
                        lastAHRS_Z=AHRS_Z[-1]
                        lastAHRS_Q2=AHRS_Q2[-1]
                        lastAHRS_Q3=AHRS_Q3[-1]
                        lastAHRS_Q4=AHRS_Q4[-1]
                        for i in range (lenAHRS,(lengyro-1)):
                            AHRS_X.append(lastAHRS_X)
                            AHRS_Y.append(lastAHRS_Y)
                            AHRS_Z.append(lastAHRS_Z)
                            AHRS_Q2.append(lastAHRS_Q2)
                            AHRS_Q3.append(lastAHRS_Q3)
                            AHRS_Q4.append(lastAHRS_Q4)
                    else:
                        for i in range (lengyro-1):
                            AHRS_X.append(None)
                            AHRS_Y.append(None)
                            AHRS_Z.append(None)
                            AHRS_Q2.append(None)
                            AHRS_Q3.append(None)
                            AHRS_Q4.append(None)
                    AHRS_X.append(float(seg[3]))
                    AHRS_Y.append(float(seg[4]))
                    AHRS_Z.append(float(seg[5]))
                    AHRS_Q2.append(float(seg[6]))
                    AHRS_Q3.append(float(seg[7]))
                    AHRS_Q4.append(float(seg[8]))
            
                if line[:4] == "GNSS":
                    seg=line.split(';')
                    lenGNSS=len(GNSS_LAT)
                    if lenGNSS!=0:
                        lastGNSS_LAT=GNSS_LAT[-1]
                        lastGNSS_LONG=GNSS_LONG[-1]
                        for i in range (lenGNSS,(lengyro-1)):
                            GNSS_LAT.append(lastGNSS_LAT)
                            GNSS_LONG.append(lastGNSS_LONG)
                    else:
                        for i in range (lengyro-1):
                            GNSS_LAT.append(None)
                            GNSS_LONG.append(None)
                        
                    GNSS_LAT.append(float(seg[3]))
                    GNSS_LONG.append(float(seg[4]))
                

                
#=========================== Positioning conversion ========================
                
        temp=latlon_to_cartesian(POSI_LAT,POSI_LONG)


        for x,y in temp:
            POSI_X.append(x)
            POSI_Y.append(y)
    
        POSI_Xapprox = []
        POSI_Yapprox = []

        for i in range(indexPOSI[0]-1):
            POSI_Xapprox.append(POSI_X[0])
            POSI_Yapprox.append(POSI_Y[0])
    
        for i in range(len(POSI_X) - 1):
            if i == 0:
                POSI_Xapprox.append(POSI_X[i])
                POSI_Yapprox.append(POSI_Y[i])
    
            num_pts = indexPOSI[i + 1] - indexPOSI[i]
            dist = ((POSI_X[i + 1] - POSI_X[i]) ** 2 + (POSI_Y[i + 1] - POSI_Y[i]) ** 2) ** 0.5
            if dist != 0:
                angle = math.atan2(POSI_Y[i + 1] - POSI_Y[i], POSI_X[i + 1] - POSI_X[i])
                step_dist = dist / num_pts
                for j in range(1, num_pts):
                    newX = POSI_Xapprox[-1] + step_dist * math.cos(angle)
                    newY = POSI_Yapprox[-1] + step_dist * math.sin(angle)
                    POSI_Xapprox.append(newX)
                    POSI_Yapprox.append(newY)
            
            else:
                for j in range(1, num_pts):
                    POSI_Xapprox.append(POSI_X[i])
                    POSI_Yapprox.append(POSI_Y[i])
                    
        lastPOSI_Xapprox=POSI_X[-1]
        lastPOSI_Yapprox=POSI_Y[-1]

        POSI_Xapprox.append(lastPOSI_Xapprox)
        POSI_Yapprox.append(lastPOSI_Yapprox)

        for i in range(len(POSI_Xapprox),lengyro):
            POSI_Xapprox.append(lastPOSI_Xapprox)
            POSI_Yapprox.append(lastPOSI_Yapprox)
            
#============== Same approximation with latitude and longitude =============

        POSI_lat_approx = []
        POSI_long_approx = []
        POSI_Z_approx= []

        for i in range(indexPOSI[0] - 1):
            POSI_lat_approx.append(POSI_LAT[0])
            POSI_long_approx.append(POSI_LONG[0])
            POSI_Z_approx.append(POSI_Z[0])

        for i in range(len(POSI_LONG) - 1):
            if i == 0:
                POSI_lat_approx.append(POSI_LAT[i])
                POSI_long_approx.append(POSI_LONG[i])
                POSI_Z_approx.append(POSI_Z[i])

            num_pts = indexPOSI[i + 1] - indexPOSI[i]
            distz= POSI_Z[i+1] - POSI_Z[i]
            dist = ((POSI_LONG[i + 1] - POSI_LONG[i]) ** 2 + (POSI_LAT[i + 1] - POSI_LAT[i]) ** 2) ** 0.5
            if distz != 0 and dist != 0:
                step_distz = distz / num_pts               
                angle = math.atan2(POSI_LAT[i + 1] - POSI_LAT[i], POSI_LONG[i + 1] - POSI_LONG[i])
                step_dist = dist / num_pts
                for j in range(1, num_pts):
                    new_lat = POSI_lat_approx[-1] + step_dist * math.sin(angle)
                    new_long = POSI_long_approx[-1] + step_dist * math.cos(angle)
                    new_Z= POSI_Z_approx[-1]+step_distz
                    POSI_lat_approx.append(new_lat)
                    POSI_long_approx.append(new_long)
                    POSI_Z_approx.append(new_Z)
            elif distz == 0 and dist != 0:
                angle = math.atan2(POSI_LAT[i + 1] - POSI_LAT[i], POSI_LONG[i + 1] - POSI_LONG[i])
                step_dist = dist / num_pts
                lastPOSI_Z_approx = POSI_Z_approx[-1]
                for j in range(1, num_pts):
                    new_lat = POSI_lat_approx[-1] + step_dist * math.sin(angle)
                    new_long = POSI_long_approx[-1] + step_dist * math.cos(angle)
                    POSI_lat_approx.append(new_lat)
                    POSI_long_approx.append(new_long)
                    POSI_Z_approx.append(lastPOSI_Z_approx)
            elif distz != 0 and dist == 0: 
                lastPOSI_lat_approx = POSI_lat_approx[-1]
                lastPOSI_long_approx = POSI_long_approx[-1]
                step_distz = distz / num_pts
                for j in range(1, num_pts):
                    new_Z= POSI_Z_approx[-1]+step_distz
                    POSI_Z_approx.append(new_Z)
                    POSI_lat_approx.append(lastPOSI_lat_approx)
                    POSI_long_approx.append(lastPOSI_long_approx)
            else:
                for j in range(1, num_pts):
                    POSI_lat_approx.append(POSI_LAT[i])
                    POSI_long_approx.append(POSI_LONG[i])
                    POSI_Z_approx.append(POSI_Z[i])

        lastPOSI_lat_approx = POSI_LAT[-1]
        lastPOSI_long_approx = POSI_LONG[-1]
        lastPOSI_Z_approx = POSI_Z[-1]

        POSI_lat_approx.append(lastPOSI_lat_approx)
        POSI_long_approx.append(lastPOSI_long_approx)
        POSI_Z_approx.append(lastPOSI_Z_approx)

# Assuming lengyro is the length you want POSI_lat_approx and POSI_long_approx to be extended to
        for i in range(len(POSI_lat_approx), lengyro):
            POSI_lat_approx.append(lastPOSI_lat_approx)
            POSI_long_approx.append(lastPOSI_long_approx)
            POSI_Z_approx.append(lastPOSI_Z_approx)
        
        Z=[]
        
        for i in range(len(POSI_Z_approx)):
            if POSI_Z_approx[i] <= 0.5:
                Z.append(0)
                
            elif 0.5 < POSI_Z_approx[i] <=3.5:
                Z.append(POSI_Z_approx[i])
                
            elif 3.5 < POSI_Z_approx[i] <=4.5:   
                Z.append(4)
            
            elif 4.5 < POSI_Z_approx[i] <=7.5:
                Z.append(POSI_Z_approx[i])
                
            else:
                Z.append(8)
            
#=========================== Sorting data =================================    


        DataL = [timestamp, POSI_long_approx, POSI_lat_approx, Z, POSI_Xapprox, POSI_Yapprox, ACCE_X, ACCE_Y, ACCE_Z, ACCE_MOD, GYRO_X, GYRO_Y, GYRO_Z, GYRO_MOD, MAGN_X, 
         MAGN_Y, MAGN_Z, MAGN_MOD ,AHRS_X,AHRS_Y,AHRS_Z,
          AHRS_Q2,AHRS_Q3,AHRS_Q4,GNSS_LAT,GNSS_LONG]

           
            
#============================= lists completion ===========================
            
        for lis in DataL: 
            lenght=len(lis)
            if lenght==0:
                for i in range (lengyro):
                    lis.append(None)
            else:
                lastelem=lis[-1]
                for i in range(lenght,lengyro):
                    lis.append(lastelem)

#=================== Replacing Nones by the next value ====================                    

        for lst in DataL:
            first_non_none = None
    
    # Find the first non-None value
            for value in lst:
                if value is not None:
                    first_non_none = value
                    break
    
    # Replace each None value with the first non-None value encountered
            for i in range(len(lst)):
                if lst[i] is None:
                    lst[i] = first_non_none   

#============================== CSV file ================================

        Data=np.array(DataL)
        Data=np.transpose(Data)

        with open(csvfilepath+testingset[-31:-4]+'.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            writer.writerow(Header)
            for row in Data:
                writer.writerow(row)
            




