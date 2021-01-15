import numpy as np
from sympy import Point3D, Line3D, Segment3D, Plane
import pymap3d as pm
from lib.PipeUtil import load_json_file, save_json_file, cfe, calc_dist, convert_filename_to_date_cam
import io
from PIL import Image
#from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
import math
from geopy.distance import distance
from geopy.point import Point



def get_best_obs(obs):
   best_dist = 99999
   best_file = None
   for file in obs:
      if best_file is None:
         best_file = file

      mid_x = np.mean(obs[file]['xs'])
      mid_y = np.mean(obs[file]['ys'])
      dist_to_center = calc_dist((mid_x,mid_y), (1920/2, 1080/2))
      if dist_to_center < best_dist:
         best_file = file
         best_dist = dist_to_center


   print("BEST:", best_file)
   return(best_file)

def simple_solve(day, event_id, json_conf):
   nsinfo = load_json_file("../conf/network_station_info.json")
   event_id = str(event_id)
   amsid = json_conf['site']['ams_id']
   year = day[0:4]
   event_file = "/mnt/ams2/meteor_archive/" + amsid + "/EVENTS/" + year + "/" + day + "/" + day + "_events.json"
   events = load_json_file(event_file)
   solutions = []
   print(event_file)
   #for event in events:

   good_obs = [] 
   if True:
      if events[event_id]['total_stations'] >= 2:
         obs = events[event_id]['obs'] 
         best_obs = []
         for station in obs:
            if len(obs[station].keys()) > 1:
               # there is more than 1 obs from this station 
               # we need to pick the 'best' one. (the one closest to the center FOV)
               best_file = get_best_obs(obs[station])
            else:
               for file in obs[station]:
                  best_file = file
            if True:
               file = best_file
               #for file in obs[station]:
                  
               if len(obs[station][file]['azs']) >= 3:
                  obs[station][file]['loc'] = nsinfo[station]['loc']
                  obs[station][file]['file'] = file
                  obs[station][file]['station'] = station
                  good_obs.append(obs[station][file])
               print(event_id, station, obs[station][file]['azs'])
   if len(good_obs) == 2:
      print("We have two good obs. Solve them.")
      print(good_obs)
      #www = input('waiting.')
      station1 = good_obs[0]['station']
      station2 = good_obs[1]['station']
      file1 = good_obs[0]['file']
      file2 = good_obs[1]['file']
      (f_datetime, cam1, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(file1)
      (f_datetime, cam2, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(file2)
      station_key = station1 + "-" + cam1 + ":" + station2 + "-" + cam2
      sols = int_planes(good_obs[0], good_obs[1])
      solutions = []
      for sol in sols:
         solutions.append((station_key,sol))
   elif len(good_obs) > 2:
      for oo in range(0,len(good_obs)):
         if oo != 0:
            station1 = good_obs[0]['station']
            station2 = good_obs[1]['station']
            file1 = good_obs[0]['file']
            file2 = good_obs[1]['file']
            (f_datetime, cam1, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(file1)
            (f_datetime, cam2, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(file2)

            station_key = station1 + "-" + cam1 + ":" + station2 + "-" + cam2
            station_key = station1 + "," + station2
            sols = int_planes(good_obs[0], good_obs[oo])
            for sol in sols:
               solutions.append((station_key,sol))

   return(solutions)
   points = []
   lines = []

   for station_key, sol in solutions:
      slat,slon,salt,elat,elon,ealt = sol
      lines.append((slat,slon,elat,elon,'b'))

   for station in obs:
      lat,lon,alt = nsinfo[station]['loc']
      points.append((lat,lon,station))
   map = make_map(points, lines)
   

def int_planes(obs1, obs2):
   """
      obs1 = {}
      obs1['loc'] = [lat,lon,alt]
      obs1['start_azel'] = [start_az,start_el]
      obs1['end_azel'] = [end_az,end_el]
      obs2 = {}
      obs2['loc'] = [lat,lon,alt]
      obs2['start_azel'] = [start_az,start_el]
      obs2['end_azel'] = [end_az,end_el]
   """
   wgs84 = pm.Ellipsoid('wgs84');
   lat1,lon1,alt1 = obs1['loc']
   dur1 = len(obs1['azs'])
   saz1 = obs1['azs'][0]
   eaz1 = obs1['azs'][-1]
   sel1 = obs1['els'][0]
   eel1 = obs1['els'][-1]

   dur2 = len(obs2['azs'])
   saz2 = obs2['azs'][0]
   eaz2 = obs2['azs'][-1]
   sel2 = obs2['els'][0]
   eel2 = obs2['els'][-1]

   lat1,lon1,alt1 = obs1['loc']
   lat2,lon2,alt2 = obs2['loc']
   x1, y1, z1 = pm.geodetic2ecef(float(lat1), float(lon1), float(alt1), wgs84)
   x2, y2, z2 = pm.geodetic2ecef(float(lat2), float(lon2), float(alt2), wgs84)

   # convert station lat,lon,alt,az,el to start and end vectors
   sveX1, sveY1, sveZ1, svlat1, svlon1,svalt1 = find_vector_point(float(lat1), float(lon1), float(alt1), saz1, sel1, 1000000)
   eveX1, eveY1, eveZ1, evlat1, evlon1,evalt1 = find_vector_point(float(lat1), float(lon1), float(alt1), eaz1, eel1, 1000000)

   sveX2, sveY2, sveZ2, svlat2, svlon2,svalt2 = find_vector_point(float(lat2), float(lon2), float(alt2), saz2, sel2, 1000000)
   eveX2, eveY2, eveZ2, evlat2, evlon2,evalt2 = find_vector_point(float(lat2), float(lon2), float(alt2), eaz2, eel2, 1000000)

   obs1 = Plane( \
   Point3D(x1,y1,z1), \
   Point3D(sveX1,sveY1,sveZ1), \
   Point3D(eveX1,eveY1,eveZ1))

   obs2 = Plane( \
   Point3D(x2,y2,z2), \
   Point3D(sveX2,sveY2,sveZ2), \
   Point3D(eveX2,eveY2,eveZ2))


   plane1 = Plane( \
      Point3D(x1,y1,z1), \
      Point3D(sveX1,sveY1,sveZ1), \
      Point3D(eveX1,eveY1,eveZ1))

   plane2 = Plane( \
      Point3D(x2,y2,z2), \
      Point3D(sveX2,sveY2,sveZ2), \
      Point3D(eveX2,eveY2,eveZ2))

   start_line1 = Line3D(Point3D(x1,y1,z1),Point3D(sveX1,sveY1,sveZ1))
   end_line1 = Line3D(Point3D(x1,y1,z1),Point3D(eveX1,eveY1,eveZ1))

   start_line2 = Line3D(Point3D(x2,y2,z2),Point3D(sveX2,sveY2,sveZ2))
   end_line2 = Line3D(Point3D(x2,y2,z2),Point3D(eveX2,eveY2,eveZ2))

   #plane 2 line 1
   start_inter2 = plane2.intersection(start_line1)
   end_inter2 = plane2.intersection(end_line1)

   #plane 1 line 2
   start_inter1 = plane1.intersection(start_line2)
   end_inter1 = plane1.intersection(end_line2)

   sx1,sy1,sz1 = read_inter(start_inter1)
   ex1,ey1,ez1 = read_inter(end_inter1)


   sx2,sy2,sz2 = read_inter(start_inter2)
   ex2,ey2,ez2 = read_inter(end_inter2)


   slat, slon, salt = pm.ecef2geodetic(sx1,sy1,sz1, wgs84)
   elat, elon, ealt = pm.ecef2geodetic(ex1,ey1,ez1, wgs84)


   slat2, slon2, salt2 = pm.ecef2geodetic(sx2,sy2,sz2, wgs84)
   elat2, elon2, ealt2 = pm.ecef2geodetic(ex2,ey2,ez2, wgs84)

   print("SX:", sx1,sy1,sz1)
   print("EX:", ex1,ey1,ez1)

   print("START:", slat, slon,salt)
   print("END:", elat, elon,ealt)

   print("START2:", slat2, slon2,salt2)
   print("END2:", elat2, elon2,ealt2)


   a = Point(slon, slat, 0)
   b = Point(elon, elat, 0)
   dist1 = distance(a, b).km
   h = salt - ealt
   dist1 = math.sqrt(dist1**2 + h**2)

   a = Point(slon2, slat2, 0)
   b = Point(elon2, elat2, 0)
   dist2 = distance(a, b).km
   h = salt2 - ealt2
   dist2 = math.sqrt(dist2**2 + h**2)


   vel1 = dist1 / (dur2/25)

   vel2 = dist2 / (dur1/25)
   print("VEL1:", dist1, dur2, vel1 )
   print("VEL2:", dist2, dur1, vel2 )

   if dist1 > dist2:
      md = dist1
   else:
      md = dist2
   if dur1 > dur2 :
      mdu = dur1
   else:
      mdu = dur2
   vel = md / (mdu/25)


   solutions = []
   solutions.append((slat,slon,salt,elat,elon,ealt,dist1,dur2,vel1))
   solutions.append((slat2,slon2,salt2,elat2,elon2,ealt,dist2,dur1,vel2))
   return(solutions)


def read_inter(inter):

   if hasattr(inter[0], 'p1'):
      p1 = inter[0].p1
      p2 = inter[0].p2
      if p1[2] < p2[2]:
         sx = float((eval(str(p1[0]))))
         sy = float((eval(str(p1[1]))))
         sz = float((eval(str(p1[2]))))
      else:
         sx = float((eval(str(p2[0]))))
         sy = float((eval(str(p2[1]))))
         sz = float((eval(str(p2[2]))))
   else:
      sx = float((eval(str(inter[0].x))))
      sy = float((eval(str(inter[0].y))))
      sz = float((eval(str(inter[0].z))))


   return(sx,sy,sz)

def find_vector_point(lat,lon,alt,az,el,factor=1000000):

   wgs84 = pm.Ellipsoid('wgs84');
   sveX, sveY, sveZ = pm.aer2ecef(az,el,1000000, lat, lon, alt, wgs84)
   svlat, svlon, svalt = pm.ecef2geodetic(float(sveX), float(sveY), float(sveZ), wgs84)
   return(sveX,sveY,sveZ,svlat,svlon,svalt)


def make_map(pts, lns):
    plats = []
    plons = []
    plabs = []

    for data in pts:
       lat,lon,label = data
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
       lat1, lon1,lat2,lon2,cl= data
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
    im = Image.open(buf)
    #im.show()
    #buf.close()
    return(buf)

