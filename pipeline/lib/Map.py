from mpl_toolkits.basemap import Basemap
from PIL import Image
import io
import matplotlib.pyplot as plt
import numpy as np
import math
import cv2
from math import sin, cos , asin, sqrt, acos, pi, atan2, degrees


def geo_intersec_point(x1, y1, brng1, x2, y2, brng2):
   
   """
       This function calculate the intersection point if exists of two points\r\n
           given their coordinates (latitude and longitude in DD format) and bearings in degrees.\r\n
       x1      (float)     : Longitude of the first point (DD format).\r\n
       y1      (float)     : Latitude of the first point (DD format).\r\n
       brng1   (float)     : Bearing of the first point (degrees format).\r\n
       x1      (float)     : Longitude of the second point (DD format).\r\n
       y1      (float)     : Latitude of the second point (DD format).\r\n
       brng1   (float)     : Bearing of the second point (degrees format).\r\n
       return :\r\n
       error   (Bool)      : True if an error is detected.\r\n
       result  (dict, str) :  if error is True, return error message.
                              if error is False, return coordinates of intersection\r
                              point in a dict struct (DD format).\r\n
   """
   
   # Check for errors
   # Check data type
   #check_type((float, int), x1 = x1, y1 = y1, brng1 = brng1)
   #check_type((float, int), x2 = x2, y2 = y2, brng2 = brng2)
   
   # Convert to np.radians (sin, cos and tan works with radians)
   lon1 = np.radians(float(x1))
   lat1 = np.radians(float(y1))
   brng1 = np.radians(float(brng1))
   
   lon2 = np.radians(float(x2))
   lat2 = np.radians(float(y2))
   brng2 = np.radians(float(brng2))
   
   # Calculate the angular distance between point 1 and point 2
   dlon = lon2 - lon1 # Distance between longitude points
   dlat = lat2 - lat1 # Distance between latitude points
   
   # Great-circle distance between point 1 and point 2
   haversine = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
   
   # angular distance between point 1 and point 2
   ang_dist_1_2 = 2 * asin(sqrt(haversine))
   
   # Calculate the initial and final bearings between point 1 and point 2
   initial_bearing = acos((sin(lat2) - sin(lat1) * cos(ang_dist_1_2)) / (sin(ang_dist_1_2) * cos(lat1)))
   final_bearing = acos((sin(lat1) - sin(lat2) * cos(ang_dist_1_2)) / (sin(ang_dist_1_2) * cos(lat2)))
   
   # Adjust initial and final bearings
   if sin(x2 - x1) > 0:
       bearing_1_2 = initial_bearing
       bearing_2_1 = (2 * pi) - final_bearing
   
   else:
       bearing_1_2 = (2 * pi) - initial_bearing
       bearing_2_1 = final_bearing
   
   
   # Angles between different points
   ang_1 = brng1 - bearing_1_2    # angle p2<--p1-->p3
   ang_2 = bearing_2_1 - brng2    # angle p1<--p2-->p3
   
   # Check for ambiguous or inifite intersection
   # infinite intersections   
   if sin(ang_1) == 0 and sin(ang_2) == 0:
       return  True, "infinite intersections"
   
   # ambiguous intersection (antipodal/360°)
   if sin(ang_1) * sin(ang_2) < 0:
       return  True, "ambiguous intersections"
   
   # if no errors, calculte intersection point angle, latitude and longitude
   ang_3 = acos(-cos(ang_1) * cos(ang_2) + sin(ang_1) * sin(ang_2) * cos(ang_dist_1_2))    # angle p1<--p3-->p2
   
   # angular distance between point 1 and intersection point (point 3)
   ang_dist_1_3 = atan2(sin(ang_dist_1_2) * sin(ang_1) * sin(ang_2), cos(ang_2) + cos(ang_1) * cos(ang_3))
   
   # Latitude of point 3
   lat3 = asin(sin(lat1) * cos(ang_dist_1_3) + cos(lat1) * sin(ang_dist_1_3) * cos(brng1))
   
   # Longitude of point 3
   delta_long_1_3 = atan2(sin(brng1) * sin(ang_dist_1_3) * cos(lat1), cos(ang_dist_1_3) - sin(lat1) * sin(lat3))
   lon3 = lon1 + delta_long_1_3
   
   # Convert to degrees
   lon3 = degrees(lon3)
   lat3 = degrees(lat3)
   
   # Return error flag as False and intersection points longitude and latitude
   return False, {"x3" : lon3, "y3" : lat3}
   
def make_map(pts, lns):

    print("POINTS:", pts)
    print("LINES:", lns)

    plats = []
    plons = []
    plabs = []
    pcolors = []
    pmarkers = []


    for data in pts:
       if len(data) == 3:
          lat,lon,label = data
          color = "red"
          marker = "+"
       if len(data) == 5:
          lat,lon,label,color,marker = data
       plats.append(float(lat))
       plons.append(float(lon))
       plabs.append(label)
       pcolors.append(color)
       pmarkers.append(marker)

    lon_diff = int(abs(max(plons)) - abs(min(plons)))
    lat_diff = int(abs(max(plats)) - abs(min(plats)))
    center_lat = np.mean(plats)
    center_lon = np.mean(plons)
    llclon = round(center_lon - 7,2)
    urclon = round(center_lon + 7,2)
    llclat = round(center_lat - 4,2)
    urclat = round(center_lat + 4,2)

    print("MAP SHAPE llc/urc lon/lat:", llclon, urclon, llclat, urclat)

    # testing lines here
    """
    bearing = 70
    d = 300
    lp_lat1, lp_lon1 = find_point_from_point_bearing_dist(plats[0],plons[0], bearing, d)
    """
    m = Basemap(projection='mill',llcrnrlat=llclat,urcrnrlat=urclat,\
                llcrnrlon=llclon,urcrnrlon=urclon,resolution='h')
    #m.shadedrelief()
    m.bluemarble()
    try:
       m.drawcoastlines()
    except:
       print("Draw coastlines failed.")
    m.drawcountries(color='#006600')
    m.drawstates(color='#006600')
    m.fillcontinents(color='black',lake_color='blue')
    #m.drawmapboundary(fill_color='#FFFFFF')
    #plt.figure(figsize=(5,5))
    lons, lats = m(plons, plats)
    #plt.tight_layout()
    for i in range(0, len(plats)):
       m.plot(lons[i], lats[i], marker=pmarkers[i], color=pcolors[i], zorder=5)
       plt.text(lons[i], lats[i], plabs[i], size=7, color="#fcfcfc")

    for data in lns:
       llats = []
       llons = []
       lat1, lon1,lat2,lon2,cl= data
       lon1,lat1,lon2,lat2 = float(lon1),float(lat1),float(lon2),float(lat2)
       llats.append(lat1)
       llats.append(lat2)
       llons.append(lon1)
       llons.append(lon2)
       lon, lat= m(llons, llats)
       m.plot(lon,lat, 'k', color=cl)

    #plt.show()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor="black")
    buf.seek(0)
    im = Image.open(buf)
    plt.cla()
    plt.close()

    #im.show()
    #buf.close()

    try:
       return_img = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)
    except:
       return_img = np.zeros((1080,1920,3),dtype=np.uint8)
    return(return_img)

if __name__ == "__main__":
   points = [[40,-76,'AMS1'],[39,-77,'AMS2']]
   lines = []
   buf = make_map(points, lines)
   #cv2.imshow('pepe', buf)
   #cv2.waitKey(0)
