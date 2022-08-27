import os
import simplekml
import math
import boto3
from boto3.dynamodb.conditions import Key, Attr
import requests
import redis
import simplejson as json
import glob
import cv2
from lib.PipeUtil import cfe, load_json_file, convert_filename_to_date_cam, save_json_file, calc_dist,fn_dir
#from lib.PipeAutoCal import get_catalog_stars, update_center_radec
import numpy as np
from lib.cognito import signup_new_user, verify_new_user
from decimal import Decimal
import pymap3d as pm
from sympy import Point3D, Line3D, Segment3D, Plane

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

class EventInspect():
    def __init__(self, event_id):
        self.data = {}
        self.data['event_id'] = event_id
        self.DATA_DIR = "/mnt/f/"
        self.home_dir = os.getcwd() + "/" 
        self.cloud_missing_data_file = "/mnt/archive.allsky.tv/EVENTS/ALL_MISSING_DATA.json"
        self.missing_data_file = self.DATA_DIR + "EVENTS/ALL_MISSING_DATA.json"

        self.dynamodb = boto3.resource('dynamodb')
        self.r = redis.Redis("allsky-redis.d2eqrc.0001.use1.cache.amazonaws.com", port=6379, decode_responses=True)
        self.API_URL = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi"
        event_day = self.data['event_id'][0:8]
        self.y = event_day[0:4]
        self.m = event_day[4:6]
        self.d = event_day[6:8]
        self.event_day = self.y + "_" + self.m + "_" + self.d
        self.event_dir = self.DATA_DIR + "EVENTS/" + self.y + "/" + self.m + "/" + self.d + "/" + self.data['event_id'] + "/"
        self.cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS/" + self.y + "/" + self.m + "/" + self.d + "/" + self.data['event_id'] + "/"


          
    def event_inspect(self):
       print("DATA:", self.data)
       print("INSPECT EVENT")
       inspect_file = self.event_dir +  self.data['event_id'] + "-INSPECT.json"
       if cfe(inspect_file) == 1:
          inspect_data = load_json_file(inspect_file)
       else:
          inspect_data = {} 
       event_data = self.get_dyna_event()
       obs_data = []
       station_data = {}
       for i in range(0,len(event_data['stations'])):
          print(event_data.keys())
          stid = event_data['stations'][i]
          vid = event_data['files'][i]
          lat = event_data['lats'][i]
          lon = event_data['lons'][i]

          obs = self.get_dyna_obs(stid, vid)

          obs['lat'] = lat
          obs['lon'] = lon
          obs_data.append(obs)
          if stid not in station_data:
             station_data[stid] = obs
       print("EVD:", event_data)

       obs_lines = [] 
       station_points = {}
       obs_dirs = []
       bad_obs = []
       for obs in obs_data:
          obs_good = 0
          station_id = obs['station_id']
          sd_video_file = obs['sd_video_file']
          obs_key = station_id + "_" + sd_video_file
          if "meteor_frame_data" in obs:
             if len(obs["meteor_frame_data"]) >= 3:
                print("OBS:", obs.keys())
                obs_good = 1
                lat = obs['lat']
                lon = obs['lon']
                alt = 0
                station_points[station_id] = [lat,lon]
                az1 = obs['meteor_frame_data'][0][9]
                el1 = obs['meteor_frame_data'][0][10]
                az2 = obs['meteor_frame_data'][-1][9]
                el2 = obs['meteor_frame_data'][-1][10]
                print(az1,el1,az2,el2)
                if (az1 == 0 and el1 == 0 ) or (az2 == 0 or el2 == 0):
                   print("BAD OBS!")
                   obs['bad'] = "NO METEOR FRAME DATA."
                   bad_obs.append(obs_key)
                   continue
                obs_dirs.append((obs['station_id'], obs['sd_video_file'], lat,lon,alt,az1,el1,az2,el2)) 
                start_lat2, start_lon2, start_alt2 = self.find_point_from_az_dist(lat,lon,az1,el1,100)
                end_lat2, end_lon2, end_alt2 = self.find_point_from_az_dist(lat,lon,az2,el2,100)
                obs_key = obs['station_id'] + "_" + obs['sd_video_file']
                obs_lines.append((obs_key,"start", lat,lon,0,start_lat2,start_lon2,start_alt2))
                obs_lines.append((obs_key,"end",lat,lon,0,end_lat2,end_lon2,end_alt2))

       obs_points = []
       #if "best_plane_points" in inspect_data:
       #   all_plane_points = inspect_data['best_plane_points']
       #else:
       all_plane_points = self.plane_point_intersections(obs_dirs)

       bad_plane_points = []
       good_plane_points = []
       for row in all_plane_points:
          alt1 = row[4]
          alt2 = row[7]
          if 50000 < alt1 < 150000 and 10000 <= alt2 <= 140000:
             good_plane_points.append(row)
          else:
             bad_plane_points.append(row)

       all_plane_points = good_plane_points
       for row in bad_plane_points:
          print("BAD:", row)


       mobs = self.column(all_plane_points,0)
       sobs = self.column(all_plane_points,1)
       start_lats = self.column(all_plane_points,2)
       start_lons = self.column(all_plane_points,3)
       start_alts = self.column(all_plane_points,4)
       end_lats = self.column(all_plane_points,5)
       end_lons = self.column(all_plane_points,6)
       end_alts = self.column(all_plane_points,7)

       std_start_lat = np.std(start_lats)
       std_start_lon = np.std(start_lons)
       std_start_alts = np.std(start_alts)

       std_end_lat = np.std(end_lats)
       std_end_lon = np.std(end_lons)
       std_end_alts = np.std(end_alts)


       print("START LAT,LON,ALT", np.median(start_lats), np.median(start_lons), np.median(start_alts))
       print("START STD", np.std(start_lats), np.std(start_lons), np.std(start_alts))
       print("SLATS:", start_lats)
       print("SLONS:", start_lons)
       print("SALTS:", start_alts)
       print("END LAT,LON,ALT", np.median(end_lats), np.median(end_lons), np.median(end_alts))
       print("END STD", np.std(end_lats), np.std(end_lons), np.std(end_alts))
       print("ELATS:", end_lats)
       print("ELONS:", end_lons)
       print("EALTS:", end_alts)
       c = 0
       for i in range(0,len(start_lats)):
          slat = start_lats[i]
          slon = start_lons[i]
          salt = start_alts[i]
          elat = end_lats[i]
          elon = end_lons[i]
          ealt = end_alts[i]
          s_lat_diff = abs(slat - np.median(start_lats))
          s_lon_diff = abs(slon - np.median(start_lons))
          s_alt_diff = abs(salt - np.median(start_alts))
          e_lat_diff = abs(elat - np.median(end_lats))
          e_lon_diff = abs(elon - np.median(end_lons))
          e_alt_diff = abs(ealt - np.median(end_alts))
          if s_lat_diff >= np.std(start_lats) or s_lon_diff > np.std(start_lons) or s_alt_diff > np.std(start_alts) or e_lat_diff > np.std(end_lats) or e_lon_diff > np.std(end_lons) or e_alt_diff > np.std(end_alts) :
             print("*** OUTLIER", lat, lon, alt, mobs[c],sobs[c])
             print("*** SDIFFS", s_lat_diff, s_lon_diff, s_alt_diff)
             print("*** S STDs", np.std(start_lats) , np.std(start_lons) , np.std(start_alts))
             print("*** eDIFFS", e_lat_diff, e_lon_diff, e_alt_diff)
             print("*** E STDs", np.std(end_lats) , np.std(end_lons) , np.std(end_alts))
             bad_obs.append(mobs[c])
             bad_obs.append(sobs[c])


          #else:
          #   print("SLAT INLIER", lat, diff, mobs[c], sobs[c])
          c += 1

       bad_dict = {}
       for bobs in bad_obs:
          print(bobs)
          el = bobs.split("_")
          station_id = el[0]
          sd_video_file = bobs.replace(station_id + "_", "")
          if bobs not in bad_dict:
             bad_dict[bobs] = 1
          else:
             bad_dict[bobs] += 1

       bad_scores = []
       for bkey in bad_dict:
          print("BAD OBS:", bkey, bad_dict[bkey])
          bad_scores.append(bad_dict[bkey])
       med_bad_score = np.median(bad_scores)

       ignore_obs = {}
       for bkey in bad_dict:
          el = bkey.split("_")
          st_id = el[0]
          if bad_dict[bkey] >= (med_bad_score * 2):
             ignore_obs[bkey] = bad_dict[bkey]
             print("IGNORE:", med_bad_score, bkey, bad_dict[bkey])
             obs_points.append((station_data[st_id]['lat'],station_data[st_id]['lon'],0,"BAD" + st_id, "ff0000ff"))


       best_plane_points = []
       for row in all_plane_points:
          mob = row[0]
          sob = row[1]
          if mob in ignore_obs or sob in ignore_obs:
             print("IGNORE:", mob, sob)
          else:
             obs_points.append((row[2],row[3],row[4],"", "ff00ff00"))
             obs_points.append((row[5],row[6],row[7],"", "ff0000ff"))
             print("GOOD:", row)
             best_plane_points.append(row)

       all_plane_points = best_plane_points


       obs_points.append((np.median(start_lats), np.median(start_lons), np.median(start_alts), "START", "FF154360"))
       obs_points.append((np.median(end_lats), np.median(end_lons), np.median(end_alts), "END", "FF7E5109"))

       obs_lines.append(("AS7 Trajectory", "traj", np.median(start_lats), np.median(start_lons), np.median(start_alts)/1000,np.median(end_lats), np.median(end_lons), np.median(end_alts)/1000))

    
       resp = {} 
       resp['event_data'] = event_data
       resp['obs_data'] = obs_data
       resp['obs_lines'] = obs_lines
       resp['obs_points'] = obs_points
       resp['ignore_obs'] = ignore_obs
       resp['best_plane_points'] = best_plane_points

       save_json_file(inspect_file, resp)
       kml_file = self.event_dir +  self.event_id + "-OBS.kml"
       kml_cloud_file = kml_file.replace(self.DATA_DIR, "archive.allsky.tv")
       resp['kml_link'] = "https://" + kml_cloud_file.replace("/mnt/", "")

       #for st in station_points:
       #   lat,lon = station_points[st]
       #   obs_points.append((lat,lon,0,st,"white"))
         

       self.make_easykml(kml_file, obs_points, obs_lines, {}, "AS7 Inspector")
       kml_cloud_file = kml_file.replace(self.DATA_DIR, "archive.allsky.tv")
       os.system("cp " + kml_file + " " + kml_cloud_file)
       print(kml_file)
       return(resp)

    def make_final_kml(self):
       kml_files = glob.glob(self.event_dir + "*.kml")
       all_kml = ""
       kml_c = 0
       print("KML FIELS:", kml_files)
       for kml_file in kml_files:
          if "merged" in kml_file:
             continue
          fp = open(kml_file)
          lc = 0
          for line in fp:
             if kml_c == 0 :
                if "</Document>" not in line and "</kml>" not in line :
                   # first
                   all_kml += line
             elif kml_c > 0 and kml_c < len(kml_files) - 1 and lc > 2 and ("</Document>" not in line and "</kml>" not in line):
                all_kml += line
                # middle
             elif lc > 2:
                all_kml += line
                #last kml
             lc += 1
          kml_c += 1
       if "</kml>" not in all_kml:
          all_kml += "</Document></kml>"
       fpout = open(self.event_dir + self.data['event_id'] + "-merged.kml", "w")
       fpout.write(all_kml)
       fpout.close()
       print(self.event_dir + self.data['event_id'] + "-merged.kml")

    def make_easykml(self,kml_file, points={}, lines={}, polys={}, main_folder_name="main"):
       colors = [
          'FF641E16',
          'FF512E5F',
          'FF154360',
          'FF0E6251',
          'FF145A32',
          'FF7D6608',
          'FF78281F',
          'FF4A235A',
          'FF1B4F72',
          'FF0B5345',
          'FF186A3B',
          'FF7E5109'
       ]

       kml = simplekml.Kml()
       folder = kml.newfolder(name=main_folder_name)
       cc = 0
       for data in lines:
          #slat,slon,salt,sdesc =lines[key]['start_lat'], lines[key]['start_lon'],lines[key]['start_alt'], lines[key]['desc']
          #elat,elon,ealt,edesc =lines[key]['end_lat'], lines[key]['end_lon'],lines[key]['end_alt'], lines[key]['desc']
          sdesc, ltype, slat,slon,salt,elat,elon,ealt = data
          salt = salt * 1000
          ealt = ealt * 1000
          line = folder.newlinestring(name=sdesc + "_" + ltype  , description="", coords=[(slon,slat,salt),(elon,elat,ealt)])
          line.altitudemode = simplekml.AltitudeMode.relativetoground
          if ltype == "start":
             line.linestyle.color = colors[0]
          elif ltype == "traj":
             line.linestyle.color = "ff0000ff"
          else:
             line.linestyle.color = colors[1]
          line.linestyle.width=  5
          #print("LINE:", slat,slon,salt,sdesc, elat,elon,ealt,edesc)
          cc = cc + 1
          if cc >= len(colors):
             cc = 0

       for data in points:
          #lat,lon,alt,desc =points[key]['lat'], points[key]['lon'],points[key]['alt'], points[key]['desc']
          lat,lon,alt,desc,color = data
          if "BAD" in desc:
             status = "BAD"
             desc = desc.replace("BAD", "")
          else:
             status = "GOOD"


          point = folder.newpoint(name=desc,coords=[(lon,lat,alt)])
          if status == "BAD":
             point.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/forbidden.png'
          else:
             point.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
          point.style.iconstyle.color=color
       kml.save(kml_file)

    def plane_point_intersections(self, obs):
       wgs84 = pm.Ellipsoid('wgs84');
       all_plane_points = []
       combos = {}
       for row in obs:
          m_station_id, m_sd_video_file, m_lat,m_lon,m_alt,m_az1,m_el1,m_az2,m_el2 = row
          m_obs_key = m_station_id + "_" + m_sd_video_file
          # convert obs location to ecef
          m_x, m_y, m_z = pm.geodetic2ecef(float(m_lat), float(m_lon), float(m_alt), wgs84)
          m_sveX, m_sveY, m_sveZ, m_svlat, m_svlon,m_svalt = self.find_vector_point(float(m_lat), float(m_lon), float(m_alt), m_az1, m_el1, 1000000)
          m_eveX, m_eveY, m_eveZ, m_evlat, m_evlon,m_evalt = self.find_vector_point(float(m_lat), float(m_lon), float(m_alt), m_az2, m_el2, 1000000) 

          try:
             plane = Plane( \
                Point3D(m_x,m_y,m_z), \
                Point3D(m_sveX,m_sveY,m_sveZ), \
                Point3D(m_eveX,m_eveY,m_eveZ))
          except:
             continue
             
          for row in obs:
             s_station_id, s_sd_video_file, s_lat,s_lon,s_alt,s_az1,s_el1,s_az2,s_el2 = row
             if s_station_id == m_station_id:
                continue
             s_obs_key = s_station_id + "_" + s_sd_video_file
             combo = "".join(sorted([s_obs_key,m_obs_key]))
             if combo in combos:
                print("ALREADY DONE THIS COMBO SKIP!:", combo)
                continue
             combos[combo] = 1
             s_x, s_y, s_z = pm.geodetic2ecef(float(s_lat), float(s_lon), float(s_alt), wgs84)
             s_sveX, s_sveY, s_sveZ, s_svlat, s_svlon,s_svalt = self.find_vector_point(float(s_lat), float(s_lon), float(s_alt), s_az1, s_el1, 1000000)
             s_eveX, s_eveY, s_eveZ, s_evlat, s_evlon,s_evalt = self.find_vector_point(float(s_lat), float(s_lon), float(s_alt), s_az2, s_el2, 1000000) 


             start_line = Line3D(Point3D(s_x,s_y,s_z),Point3D(s_sveX,s_sveY,s_sveZ))
             end_line = Line3D(Point3D(s_x,s_y,s_z),Point3D(s_eveX,s_eveY,s_eveZ))
             inter = plane.intersection(start_line)

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


             inter = plane.intersection(end_line)

             if hasattr(inter[0], 'p1'):
                p1 = inter[0].p1
                p2 = inter[0].p2
                if p1[2] < p2[2]:
                   ex = float((eval(str(p1[0]))))
                   ey = float((eval(str(p1[1]))))
                   ez = float((eval(str(p1[2]))))
                else:
                   ex = float((eval(str(p2[0]))))
                   ey = float((eval(str(p2[1]))))
                   ez = float((eval(str(p2[2]))))
             else:
                ex = float((eval(str(inter[0].x))))
                ey = float((eval(str(inter[0].y))))
                ez = float((eval(str(inter[0].z))))

             slat, slon, salt = pm.ecef2geodetic(sx,sy,sz, wgs84)
             elat, elon, ealt = pm.ecef2geodetic(ex,ey,ez, wgs84)

             print("RESULT:", m_obs_key, s_obs_key, slat,slon,salt,elat,elon,ealt)
             all_plane_points.append(( m_obs_key, s_obs_key, slat,slon,salt,elat,elon,ealt))

       return(all_plane_points)
       # for each obs create a plane. 
       # then for each obs that does not belong to the same stations
       # find the intersection points for the plane and start/end vector of the obs
    def column(self,matrix, i):
        return [row[i] for row in matrix]       

    def find_vector_point(self,lat,lon,alt,az,el,factor=1000000):

       wgs84 = pm.Ellipsoid('wgs84');
       sveX, sveY, sveZ = pm.aer2ecef(az,el,1000000, lat, lon, alt, wgs84)
       svlat, svlon, svalt = pm.ecef2geodetic(float(sveX), float(sveY), float(sveZ), wgs84)
       return(sveX,sveY,sveZ,svlat,svlon,svalt)

    def find_point_from_az_dist(self, lat,lon,az,el,est_alt):
       import math
       # figure out the distance for 100km based on the el 
       dist = est_alt / math.tan(math.radians(el))
       print("EL/DIST IS ", el, dist)

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
       print("END POINT:", lat2,lon2)
       return(lat2, lon2, est_alt)

    def get_dyna_obs(self, station_id, sd_video_file):
       dynamodb = boto3.resource('dynamodb')
       table = dynamodb.Table("meteor_obs")
       response = table.get_item(Key={'station_id': station_id, 'sd_video_file': sd_video_file})
       #event_data = json.loads(json.dumps(response['Item']), parse_float=Decimal)
       response['Item'] = json.loads(json.dumps(response['Item'],cls=DecimalEncoder))
       return(response['Item'])

    def get_dyna_event(self):
       dynamodb = boto3.resource('dynamodb')
       table = dynamodb.Table('x_meteor_event')
       print("SELF.DATA:", self.data)
       event_day = self.data['event_id'][0:8]
       y = event_day[0:4]
       m = event_day[4:6]
       d = event_day[6:8]
       event_day = y + "_" + m + "_" + d
       self.event_dir = self.DATA_DIR + "EVENTS/" + y + "/" + m + "/" + d + "/" + self.data['event_id'] + "/"
       if cfe(self.event_dir,1) == 0:
          os.makedirs(self.event_dir)
       self.event_id = self.data['event_id']

       try:
           response = table.get_item(Key={'event_day': event_day, 'event_id': self.data['event_id']})
       except ClientError as e:
          print(e.response['Error']['Message'])
       #event_data = json.loads(json.dumps(response['Item']), parse_float=Decimal)
       print(response)
       response['Item'] = json.loads(json.dumps(response['Item'],cls=DecimalEncoder))
       return(response['Item'])

    def get_obs(self, station_id, sd_video_file):
       url = self.API_URL + "?cmd=get_obs&station_id=" + station_id + "&sd_video_file=" + sd_video_file
       response = requests.get(url)
       content = response.content.decode()
       content = content.replace("\\", "")
       if content[0] == "\"":
          content = content[1:]
          content = content[0:-1]
       if "not found" in content:
          data = {}
          data['aws_status'] = False
       else:
          data = json.loads(content)
          data['aws_status'] = True
       return(data)


    def update_event_sol(self):
       # dynamodb = 
       dynamodb = boto3.resource('dynamodb')
       event_id = self.data['event_id']
       sol_data = self.data['sol_data']
       obs_data = self.data['obs_data']
       status = self.data['status']
       sol_data = json.loads(json.dumps(sol_data), parse_float=Decimal)
       #obs_data_save = json.loads(json.dumps(obs_data), parse_float=Decimal)
       if dynamodb is None:
          dynamodb = boto3.resource('dynamodb')

       table = dynamodb.Table("x_meteor_event")
       event_day = event_id[0:8]
       y = event_day[0:4]
       m = event_day[4:6]
       d = event_day[6:8]
       event_day = y + "_" + m + "_" + d

       if "obs" in sol_data:
          del sol_data['obs']
       for key in obs_data:
          for fkey in obs_data[key]:

          #obs_data[key][fkey]['calib'][6] = float(obs_data[key][fkey]['calib'][6])
             if key in obs_data:
                if fkey in obs_data[key]:
                   if 'calib' in obs_data[key][fkey]:
                      del obs_data[key][fkey]['calib']

       obs_data = json.loads(json.dumps(obs_data), parse_float=Decimal)

       #obs_data = {}
       #sol_data = {}

       response = table.update_item(
          Key = {
            'event_day': event_day ,
            'event_id': event_id
          },
          UpdateExpression="set solve_status=:status, solution=:sol_data, obs=:obs_data  ",
          ExpressionAttributeValues={
            ':status': status ,
            ':sol_data': sol_data,
            ':obs_data': obs_data
          },
          ReturnValues="UPDATED_NEW"
       )
         #':obs_data': obs_data,
       print("UPDATED EVENT WITH SOLUTION.")
       url = API_URL + "?recache=1&cmd=get_event&event_id=" + event_id
       response = requests.get(url)
       content = response.content.decode()
       content = content.replace("\\", "")
       return response


