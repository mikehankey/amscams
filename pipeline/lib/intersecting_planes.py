# Light functions to compute intersecting planes fast with low overhead / minimal includes etc. 

import numpy as np
import math


def threeDTrackPoint(lat,lon,alt, MeteorX, MeteorY,A0,B0, C0):

    # solve for another point higher up on the 3d track #


    t = alt / C0

    xxx = MeteorX + A0 * t;
    yyy = MeteorY + B0 * t;
    zzz = C0 * t;

    # convert x & y to lat & long
    xlat = lat + (yyy / 111.14)
    xlong = lon + xxx / (111.32*math.cos(lat * math.pi/ 180));


    return(xlat , xlong, alt)
    

def intersecting_planes(obs1,obs2):
    (lat1, lon1, alt1, az1_start, el1_start, az1_end,el1_end) = obs1
    (lat2, lon2, alt2, az2_start, el2_start, az2_end,el2_end) = obs2
    # CONVERT AZ/EL POINTS TO RADIANS
    az1_start = np.radians(az1_start)
    el1_start = np.radians(el1_start)
    az2_start = np.radians(az2_start)
    el2_start = np.radians(el2_start)
    
    az1_end = np.radians(az1_end)
    el1_end = np.radians(el1_end)
    az2_end = np.radians(az2_end)
    el2_end = np.radians(el2_end)
    
    # MAKE VECTORS FROM AZ/EL POINTS
    X1 = math.sin(az1_start) * math.cos(el1_start)
    Y1 = math.cos(az1_start) * math.cos(el1_start)
    Z1 = math.sin(el1_start)
    
    X2 = math.sin(az1_end) * math.cos(el1_end)
    Y2 = math.cos(az1_end) * math.cos(el1_end)
    Z2 = math.sin(el1_end)
    
    X3 = math.sin(az2_start) * math.cos(el2_start)
    Y3 = math.cos(az2_start) * math.cos(el2_start)
    Z3 = math.sin(el2_start)
    
    X4 = math.sin(az2_end) * math.cos(el2_end)
    Y4 = math.cos(az2_end) * math.cos(el2_end)
    Z4 = math.sin(el2_end)
    
    # MAKE PLANE 1
    A1 = (Y1*Z2) - (Y2*Z1)
    B1 = (X2*Z1) - (X1*Z2)
    C1 = (X1*Y2) - (X2*Y1)
    
    # MAKE PLANE2 
    A2 = (Y3*Z4) - (Y4*Z3)
    B2 = (X4*Z3) - (X3*Z4)
    C2 = (X3*Y4) - (X4*Y3)
    
    # Make OBS2 Relative to OBS1
    Obs2Z = alt2 - alt1;
    Obs2Y = (lat2 - lat1)*111.14
    Obs2X = (lon2 - lon1)*111.32*math.cos(((lat1+lat2)/2)*math.pi/180) 
    
    # Solve For Meteor
    MeteorY = A1*(A2*Obs2X + B2*Obs2Y+ C2*Obs2Z) / (A1 * B2 - A2 * B1)
    MeteorX = (-1 * B1 * MeteorY) / A1
    
    # Find impact location
    impact_lat = lat1 + (MeteorY / 111.14)
    impact_lon = lon1 + MeteorX / (111.32 * math.cos(lat1*math.pi/180))
    
    # Solve 3d Track
    
    A0 = (B1 * C2) - (B2 * C1)
    B0 = (A2 * C1) - (A1 * C2)
    C0 = (A1 * B2) - (A2 * B1)
    
    for a in range(0,10):
       alt = a * 10
       lat, lon, alt = threeDTrackPoint(lat1,lon1,alt, MeteorX, MeteorY,A0,B0, C0)
       print(lat,lon,alt)
       
       

lat1 = 39.9196600
lon1 = -76.7474100
alt1 = 0.3
az1_start =  101.5083300
el1_start =  36.13333
az1_end = 87.5908300
el1_end = 24.736380

lat2 = 39.676883
lon2 = -76.679617
alt2 = .3
az2_start = 56.91667
el2_start = 27.3667
az2_end = 56.51667
el2_end = 26.6333

obs1 = (lat1, lon1, alt1, az1_start, el1_start, az1_end,el1_end) 
obs2 = (lat2, lon2, alt2, az2_start, el2_start, az2_end,el2_end) 
intersecting_planes(obs1,obs2)
