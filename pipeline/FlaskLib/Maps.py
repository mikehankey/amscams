import io
from PIL import Image
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
import numpy as np
import math

def make_map(points, lines):
    plats = []
    plons = []
    plabs = []
    pts = points.split(";")
    if lines is not None:
       lns = lines.split(";")
    else:
       lns = []

    for data in pts:
       lat,lon,label = data.split(",")
       print(data)
       plats.append(float(lat))
       plons.append(float(lon))
       plabs.append(label)
    center_lat = np.mean(plats)
    center_lon = np.mean(plons)
    llclon = center_lon - 5 
    urclon = center_lon + 5 
    llclat = center_lat - 3 
    urclat = center_lat + 3 
  
    # testing lines here
    """
    bearing = 70
    d = 300
    lp_lat1, lp_lon1 = find_point_from_point_bearing_dist(plats[0],plons[0], bearing, d)
    """
    m = Basemap(projection='mill',llcrnrlat=llclat,urcrnrlat=urclat,\
                llcrnrlon=llclon,urcrnrlon=urclon,resolution='h')
    #m.shadedrelief()
    m.drawcoastlines()
    m.drawcountries()
    m.drawstates()
    m.fillcontinents(color='#add8e6',lake_color='#FFFFFF')
    #m.drawmapboundary(fill_color='#FFFFFF')

    lons, lats = m(plons, plats)

    for i in range(0, len(plats)):
       m.plot(lons[i], lats[i], marker='o', color='r', zorder=5)
       plt.text(lons[i], lats[i], plabs[i], size=15)
    for data in lns:
       llats = []
       llons = []
       lat1, lon1,lat2,lon2,cl= data.split(",")
       lon1,lat1,lon2,lat2 = float(lon1),float(lat1),float(lon2),float(lat2)
       llats.append(lat1)
       llats.append(lat2)
       llons.append(lon1)
       llons.append(lon2)
       lon, lat= m(llons, llats)
       m.plot(lon,lat, 'k', color=cl)

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    #im = Image.open(buf)
    #im.show()
    #buf.close()
    return(buf)


def find_point_from_point_bearing_dist(lat,lon, bearing, d):
   R = 6378.1 #Radius of the Earth
   brng = math.radians(bearing) #Bearing is 90 degrees converted to radians.

   #lat2  52.20444 - the lat result I'm hoping for
   #lon2  0.36056 - the long result I'm hoping for.

   lat1 = math.radians(lat) #Current lat point converted to radians
   lon1 = math.radians(lon) #Current long point converted to radians

   lat2 = math.asin( math.sin(lat1)*math.cos(d/R) +
     math.cos(lat1)*math.sin(d/R)*math.cos(brng))

   lon2 = lon1 + math.atan2(math.sin(brng)*math.sin(d/R)*math.cos(lat1),
             math.cos(d/R)-math.sin(lat1)*math.sin(lat2))

   dlat2 = math.degrees(lat2)
   dlon2 = math.degrees(lon2)
   return(dlat2, dlon2)
