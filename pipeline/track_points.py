import time
from sympy import Point3D, Line3D
import sys
import json
import os
import math
import numpy 
import pymap3d as pm
from trianglesolver import solve, degree
from lib.PipeUtil import dist_between_two_points, load_json_file, save_json_file, get_template, check_running
import simplekml
from lib.kmlcolors import *
from prettytable import PrettyTable as pt

def find_vector_point(lat,lon,alt,az,el,factor=1000000):
   #sveX1, sveY1, sveZ1, svlat1, svlon1,svalt1 = find_vector_point(float(lat1), float(lon1), float(alt1), saz1, sel1, 1000000)

   wgs84 = pm.Ellipsoid('wgs84');
   sveX, sveY, sveZ = pm.aer2ecef(az,el,factor, lat, lon, alt, wgs84)
   svlat, svlon, svalt = pm.ecef2geodetic(float(sveX), float(sveY), float(sveZ), wgs84)
   return(sveX,sveY,sveZ,svlat,svlon,svalt)

def find_point_from_az_dist(lat,lon,az,dist):

   R = 6378.1 #Radius of the Earth
   brng = math.radians(az) #Bearing is 90 degrees converted to radians.
   d = dist #Distance in km


   lat1 = math.radians(lat) #Current lat point converted to radians
   lon1 = math.radians(lon) #Current long point converted to radians

   lat2 = math.asin( math.sin(lat1)*math.cos(d/R) +
   math.cos(lat1)*math.sin(d/R)*math.cos(brng))

   lon2 = lon1 + math.atan2(math.sin(brng)*math.sin(d/R)*math.cos(lat1),
      math.cos(d/R)-math.sin(lat1)*math.sin(lat2))

   lat2 = math.degrees(lat2)
   lon2 = math.degrees(lon2)

   return(lat2, lon2)

def get_bearing(lat1, long1, lat2, long2):
    dLon = (long2 - long1)
    x = math.cos(math.radians(lat2)) * math.sin(math.radians(dLon))
    y = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(dLon))
    brng = numpy.arctan2(x,y)
    brng = numpy.degrees(brng)

    return brng

def track_points(sp, ep,jd):
   slat,slon,salt = sp
   elat,elon,ealt = ep
   tb = pt()
   tb.field_names = ["Field", "Value"]
   tb.add_row(["Start Point",  (slat,slon,salt)])
   tb.add_row(["End Point",  (elat,elon,ealt)])
   
   kml_file = jd['wind_file'].replace("_wind.csv", "-dfm-track.kml")

   wgs84 = pm.Ellipsoid('wgs84');

   # find sides and angles of track A = height, B=Adjacent, C=Hyponenous
   # side a is height
   # side b is ground 
   # side c is hypotenuse 
   # angle A is in the air -- zenith angle 
   # angle B is on the ground
   # angle C is 90

   side_a = (salt - ealt) / 1000
   side_b = dist_between_two_points(slat,slon,elat,elon)
   side_c = math.sqrt((side_a ** 2) + (side_b ** 2))

   # sides / angles
   a,b,c,A,B,C = solve(b=side_b, a=side_a, c=side_c)

   azimuth_heading = get_bearing(slat, slon, elat, elon)
   zenith_angle = A / degree

   tb.add_row(["Ground Track Distance:", side_b])
   tb.add_row(["Azimuth Heading:", azimuth_heading])
   tb.add_row(["Zenith Angle:", zenith_angle])

   # reverse the heading to go backward on the track
   if azimuth_heading > 180:
      rev_azimuth_heading = azimuth_heading - 180
   else:
      rev_azimuth_heading = azimuth_heading + 180
   
   pre_end_lat1, pre_end_lon1 = find_point_from_az_dist(elat,elon,rev_azimuth_heading,2)
   pre_end_lat2, pre_end_lon2 = find_point_from_az_dist(elat,elon,rev_azimuth_heading,4)
   post_end_lat1, post_end_lon1 = find_point_from_az_dist(elat,elon,azimuth_heading,2)
   post_end_lat2, post_end_lon2 = find_point_from_az_dist(elat,elon,azimuth_heading,4)

   # now find altitude for pre/post end 
   # need to find side a
   # side_a = (salt - ealt) / 1000
   # use side_b, angle C and angle A

   pre_side_b = dist_between_two_points(slat,slon,pre_end_lat1,pre_end_lon1)
   #pre_side_a = 80
   #pre1_a, pre1_b, pre1_c, pre1_A, pre1_B, pre1_C  = solve(b=pre_side_b, A=A, C=90*degree )

   traj_points = []
   sveX1, sveY1, sveZ1, svlat1, svlon1,svalt1 = find_vector_point(float(elat), float(elon), float(ealt), rev_azimuth_heading , zenith_angle , 10000)
   #traj_points.append((elat, elon,ealt))
   traj_points.append((svlat1, svlon1,svalt1,0,0))
   interval = 1000
   distance = 0
   go = True
   cc = 1 
   tb.add_row(["Main DFM Point: " , (elat, elon,ealt)])

   for i in range (-1,2):
      heading_val = i *  2
      for k in range (-1,2):
         zenith_val = k * 5

         print("HEADING/ZEN VAL:", i,k, heading_val, str(float(jd['heading_azimuth']) + float(heading_val)), zenith_val, str(float(jd['zenith_angle']) + float(zenith_val)))
         go = True
         distance = 0
         while go is True:
 
            sveX2, sveY2, sveZ2, svlat2, svlon2,svalt2 = find_vector_point(float(svlat1), float(svlon1), float(svalt1), rev_azimuth_heading +heading_val, zenith_angle-180 + zenith_val, distance)
            tb.add_row(["DFM Point: " + str(cc) , (svlat2, svlon2,svalt2)])
            traj_points.append((svlat2, svlon2,svalt2,heading_val,zenith_val))
            #print("\tHeading, Angle, Distance:", azimuth_heading, zenith_angle-90, distance)
            #print("\tVector lat/lon/alt:", svlat2, svlon2, svalt2)
            distance = distance + interval 
            if svalt2 <= 10000 or distance > 10000:
               go = False
            cc += 1

   kml = simplekml.Kml()
   colors = []
   for key in kml_colors:
      colors.append(kml_colors[key])

   for lat,lon,alt,heading_val,zenith_val in traj_points:
      prefix = str(int(heading_val)) + "_" + str(int(zenith_val))
      epnt = kml.newpoint(name=prefix + "_" + str(round((alt/1000),2)) + "km", coords=[(lon,lat,alt)])
      epnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/firedept.png'

   kline = kml.newlinestring(name="illuminate track", description="", coords=[(slon,slat,salt),(elon,elat,ealt)])
   kline.altitudemode = simplekml.AltitudeMode.clamptoground
   kline.linestyle.color = kml_colors['red']
   kline.linestyle.colormode = "normal"
   kline.linestyle.width = "3"

   kml.save(kml_file)
   print(tb)
   print("SAVED:", kml_file)

   # get config template
   template = get_template("DFM/config_file_template.cfg")
   # now make a DFM config file for each point in the traj run
   # also make a traj file for +/-5 x2 Zenith Angle 
   # also make a traj file for +/-5 x2 Heading AZ 

   input("Press Enter to run the DFM models!")

   # change up the heading +/- 5 degrees 
   commands = []
   if True:
      if True:
         for lat,lon,alt,heading_val,zenith_val in traj_points:
            run_name = str(float(alt/1000)) + "_" + str(float(jd['heading_azimuth']) + float(heading_val)) + "_" + str(float(jd['zenith_angle']) + float(zenith_val))
            tout = template.replace("{LAT}", str(lat))
            tout = tout.replace("{LON}", str(lon))
            tout = tout.replace("{ALT}", str(alt))
            tout = tout.replace("{RUN_NAME}", run_name)
            tout = tout.replace("{PROJECT_NAME}", jd['project_name'])
            tout = tout.replace("{MASS}", jd['mass'])
            tout = tout.replace("{ROCK_DENSITY}", jd['rock_density'])
            tout = tout.replace("{ZENITH_ANGLE}", str(float(jd['zenith_angle']) + zenith_val))
            tout = tout.replace("{HEADING_AZIMUTH}", str(float(jd['heading_azimuth']) + heading_val))
            tout = tout.replace("{EXPOSURE_TIME}", jd['exposure_time'])
            tout = tout.replace("{WIND_FILE}", jd['wind_file'])
            tout = tout.replace("{VEL}", jd['terminal_speed'])
            outfile = jd['project_dir'] + jd['project_name'] + "_" + run_name + ".cfg"
            fp = open(outfile, "w")
            fp.write(tout)
            fp.close()

            cmd = "cd /home/ams/DFN_darkflight/DFN_darkflight/; python3 DFN_DarkFlight.py -e " + outfile + " -w " + jd['wind_file']
            print(cmd)
            commands.append((cmd, outfile))
   print("Total DFM Runs Planned:", len(commands))
   print("Press [ENTER] to run or [CNTL-C] to quit!")  
   for cmd, outfile in commands:
      if True:
         if os.path.exists(outfile) is False:
            print(outfile, "doesn't exist. Sleep for a second.")
            time.sleep(2)
         if os.path.exists(outfile) is True:
            print(cmd)
            os.system(cmd + "&")
         else:
            print("SKIPPED RUN DUE TO MISSING cfg!", outfile)
         time.sleep(1) 
         running = check_running("python3")
         while running >= 16:
            print("waiting for processes to complete", running)  
            running = check_running("python3")
            time.sleep(15)
         
         #input("WROTE" )
   print(tb)

script, project_name = sys.argv
project_dir = "/home/ams/amscams/pipeline/DFM/" + project_name + "/" 
project_file = project_dir + project_name + ".json"
wind_file = project_dir + project_name + "_wind.csv"
jd = load_json_file(project_file)
jd['project_dir'] = project_dir
jd['project_file'] = project_file
jd['wind_file'] = wind_file 
print("Saved data keys:", jd.keys())
p1 = (float(jd['slat']),float(jd['slon']),float(jd['salt']))
p2 = (float(jd['elat']),float(jd['elon']),float(jd['ealt']))
track_points(p1,p2,jd)

# copy to extra dir
extra_dir = "/mnt/f/meteorite_falls/" + project_name + "/" 
if os.path.exists(extra_dir) is False:
   os.makedirs(extra_dir)
cmd = "cp " + project_dir + "*.kml " + extra_dir 
print(cmd)
os.system(cmd)
