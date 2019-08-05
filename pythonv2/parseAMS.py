#!/usr/bin/python3

from datetime import datetime
import datetime as ddt
import pymap3d as pm
import os
from sympy import Point3D, Line3D, Segment3D, Plane
import sys
import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import simplekml
from lib.WebCalib import HMS2deg
from lib.UtilLib import calc_radiant

from mpl_toolkits import mplot3d
import math
#from lib.FileIO import load_json_file, save_json_file
#from lib.WebCalib import HMS2deg

#wgs84 = pm.Ellipsoid('wgs84');
vfact = 100000


kml = simplekml.Kml()


fp = open("ams-events.txt", "r")
c = 0
gc = 0
for line in fp:
   line = line.replace("\n", "")   
   line = line.replace("\"", "")   
   data = line.split("\t") 
   print(data)
   event_time, start_lat, start_lon, start_alt, end_lat, end_lon, end_alt, vel = data
   arg_date, arg_time = event_time.split(" ")
   rah,dech,az,el,track_dist,entry_angle = calc_radiant(float(end_lon),float(end_lat),float(end_alt),float(start_lon),float(start_lat),float(start_alt),arg_date, arg_time)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra,dec= HMS2deg(str(rah),str(dech))

   #print(c,event_time, nlat, nlon, alt, vel, vx,vy,vz, rad_energy, imp_energy, x,y,z, vpx, vpy,vpz, vlat,vlon,valt, ra, dec)
   dd = arg_date.replace("-", "")
   tt = arg_time.replace(":", "") + ".0"
   etime = dd + "-" + tt
   cmd = "cd /home/ams/dvida/WesternMeteorPyLib/wmpl/Trajectory; ./runOrb.py " + str(ra) + " " + str(dec) + " " + str(vel) + " " + str(etime) + " " + str(start_lat) + " " + str(start_lon) + " " + str(start_alt)
   print(cmd)
   os.system(cmd)
   print(etime, ra,dec)
   desc = event_time + "\n" 
   desc = desc + "RA: " + str(ra)+ "\n" 
   desc = desc + "DEC: " + str(dec)+ "\n" 
   line = kml.newlinestring(name=event_time, description=desc, coords=[(start_lon,start_lat,start_alt*1000),(end_lon,end_lat,end_alt)])
   line.altitudemode = simplekml.AltitudeMode.relativetoground
   line.linestyle.color = "FF0000FF"
   line.linestyle.width= 5
   gc = gc + 1
   #else: 
   #   print("BAD:", line)
   
   c = c + 1

   kml.save("ams-bolides.kml")


