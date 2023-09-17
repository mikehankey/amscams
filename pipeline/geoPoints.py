from geojson import Point , LineString, Polygon, Feature, FeatureCollection, dumps
import sys
import datetime
import json
import requests
import os
import time
from lib.PipeUtil import load_json_file, save_json_file, get_template

def load_events(date):
   trajs = []
   y,m,d = date.split("_")
   ev_dir = "/mnt/f/EVENTS/" + y + "/" + m + "/" + d + "/" 
   ev_file = ev_dir + date + "_ALL_EVENTS.json"
   events = load_json_file(ev_file) 
   # disable events for now
   events = []
   for ev in events:
      #print(ev)
      obs = obs_preview(ev)
      if "traj" in ev:
         t = ev['traj']
         trajs.append((ev['event_id'], t['start_lat'], t['start_lon'], t['start_ele'], t['end_lat'], t['end_lon'], t['end_ele'], t['v_avg'], obs))
         print((ev['event_id'], t['start_lat'], t['start_lon'], t['start_ele'], t['end_lat'], t['end_lon'], t['end_ele']), obs)
   return(trajs)       

def obs_preview(ev):
   obs = []
   for i in range(0, len(ev['stations'])):
      st = ev['stations'][i]
      vid = ev['files'][i]
      oid = st + "_" + vid
      sds = len(ev['start_datetime'][i])
      obs.append((oid, sds))
   obs = sorted(obs, key=lambda x: (x[1]), reverse=True)
   return(obs)   

all_points = []

date = sys.argv[1]
y,m,d = date.split("_")
ev_dir = "/mnt/f/EVENTS/" + y + "/" + m + "/" + d + "/" 
latest_geojson_file = "/mnt/f/EVENTS/LATEST.geojson"
geo_events_file = ev_dir + date + "_GEO_EVENTS.geojson"
trajs = load_events(date)

# mute events for now
trajs = []

for row in trajs:
   event_id, slat, slon, salt, elat,elon,ealt, vavg,obs = row
   my_feature = Feature(geometry=Point((round(float(slon),1), round(float(slat),1))))
   my_feature['properties']['marker_type'] = "meteor_event" 
   my_feature['properties']['event_id'] = event_id
   my_feature['properties']['traj'] = [round(slat,1),round(slon,1),round(salt,1),round(elat,1),round(elon,1),round(ealt,1)]
   my_feature['properties']['vavg'] = round(vavg,1)
   my_feature['properties']['obs'] = obs
   all_points.append(my_feature)

tdata = FeatureCollection(all_points)


map_temp = get_template("aws-map-template.html")
stations_file = "/mnt/f/EVENTS/ALL_STATIONS.json"
stations_check_file = "/mnt/f/EVENTS/LAST_STATIONS_CHECK.json"
latest_geojson_file = "/mnt/f/EVENTS/LATEST.geojson"
today = datetime.datetime.now().strftime("%Y_%m_%d")

yest = datetime.datetime.now().strftime("%Y%m%d")
map_temp = map_temp.replace("{YESTERDAY}", yest)


stations = load_json_file(stations_file)
if os.path.exists(stations_check_file) is True:
   stations_check = load_json_file(stations_check_file)
else:
   stations_check = {}

for st in stations:
   station_id = st['station_id']
   op_status = st['op_status']
   latest_url = "/mnt/archive.allsky.tv/" + station_id + "/LATEST/" + today + "/"
   if op_status != 'ACTIVE':
      continue

   # get last weather/info file
   doit = True 
   if station_id not in stations_check:
      doit = True
   elif "last_check" in stations_check[station_id]:
      if time.time() - stations_check[station_id]['last_check'] > 15 * 60:
         doit = True
   if doit is True:
      try:
         url = "https://archive.allsky.tv/" + station_id + "/LATEST/current_weather.json" 
         response = requests.get(url)
         content = json.loads(response.content.decode())
      except: 
         content = None
      #print(station_id, response)
      stations_check[station_id] = {}
      stations_check[station_id]['weather_info'] = content 
      stations_check[station_id]['last_check'] = time.time()
   else:
      print("CONT:",  stations_check[station_id])
      content = stations_check[station_id]['weather_info']

   if content is not None: 
      last_ping =  content['datetime']
      last_ping_dt =  datetime.datetime.strptime(content['datetime'], "%Y_%m_%d_%H_%M")
      ping_time_elp_days = abs(((datetime.datetime.now() - last_ping_dt).total_seconds()) / 60 / 60 / 24)
      print("ELP:", datetime.datetime.now() , last_ping_dt, ping_time_elp_days)
   else:
      last_ping = "1999_01_31_23_59" 
      last_ping_dt =  datetime.datetime.strptime(last_ping, "%Y_%m_%d_%H_%M")
      ping_time_elp_days = abs(((datetime.datetime.now() - last_ping_dt).total_seconds()) / 60 / 60 / 24)
   print(st['operator_name'], op_status, station_id, last_ping)


   #try:
   if st['lon'] != "" and st['lat'] != "":
      #print(st['station_id'], st['lat'], st['lon'])
      my_feature = Feature(geometry=Point((round(float(st['lon']),1), round(float(st['lat']),1))))
      cams = []
      if "cameras" not in st:
         st['cameras'] = []
      for cc in st['cameras']:
         if type(cc) == str:
            cams.append(st['cameras'][cc])
         else:
            cams.append(cc['cam_id'])
      if len(cams) == 8:
         zcam = cams[-2] 
         #print(cams)
         #print(zcam)
         #input("ZCAM8")
      elif len(cams) > 0  :
         zcam = max(cams) 
      else:
         zcam = "none" 

      # get / check latest picture header
      if doit is True :
         try:
         #if True:

            url = "https://archive.allsky.tv/" + station_id + "/LATEST/" + zcam + ".jpg"
            response = requests.head(url)
            if station_id == "AMS152":
               print(respopnse)
            if response is not None and "Last-Modified" in response.headers:
               content = response.headers['Last-Modified']
               el = content.split(",")
               tdate = el[1]
               last_pic_update_dt = datetime.datetime.strptime(tdate, " %d %b %Y %H:%M:%S GMT")
               last_pic_update = last_pic_update_dt.strftime("%Y_%m_%d_%H_%M")
               last_pic_elp_days = abs(((datetime.datetime.now() - last_pic_update_dt).total_seconds()) / 60 / 60 / 24)
               my_feature['properties']['last_pic_update'] = last_pic_update 
               my_feature['properties']['last_pic_elp_days'] = last_pic_elp_days
               print(last_pic_update, last_pic_elp_days)
            else:
               last_pic_update = "1999_01_31_23_59" 
               last_pic_elp_days = 9999
               my_feature['properties']['last_pic_update'] = last_pic_update 
               my_feature['properties']['last_pic_elp_days'] = last_pic_elp_days
               print(response.headers)
         except: 
            content = None
            print(url)
            my_feature['properties']['last_pic_update'] = last_pic_update 
            my_feature['properties']['last_pic_elp_days'] = last_pic_elp_days

      my_feature['properties']['station_id'] = station_id  
      my_feature['properties']['marker_type'] = "station" 
      my_feature['properties']['cams'] = cams 
      my_feature['properties']['message'] = station_id  
      my_feature['properties']['iconSize'] = [100,100] 
      my_feature['properties']['station_id'] = station_id
      my_feature['properties']['operator_name'] = st['operator_name'] 
      my_feature['properties']['last_ping_elp_days'] = float(ping_time_elp_days)
      my_feature['properties']['last_ping'] = last_ping
      my_feature['properties']['city'] = st['city'] 
      my_feature['properties']['state'] = st['state'] 
      print(st)
      if "country" in st:
         my_feature['properties']['country'] = st['country'] 
      my_feature['properties']['zcam'] = zcam 
      all_points.append(my_feature)
   #except:
   #   print("BAD/MISSING LAT/LON", st['station_id'], st['lat'], st['lon'])
   #input(st['station_id'] + " " +  st['op_status'])
jdata = FeatureCollection(all_points)
save_json_file ("/mnt/f/EVENTS/stations.geojson", jdata)
print("/mnt/f/EVENTS/stations.geojson" )
map_temp = map_temp.replace("{GEOJSON}", dumps(jdata))
print(map_temp)
fpout = open("/mnt/ams2/aws-map-out.html", "w")
fpout.write(map_temp)
fpout.close()
save_json_file(stations_check_file, stations_check)
save_json_file(latest_geojson_file, jdata)
save_json_file(geo_events_file, jdata)
print("SAVED:")
print(stations_check_file)
print(latest_geojson_file)
print(geo_events_file)

cmd = "scp -i /home/ams/pem/ALLSKYTV-EAST.pem /mnt/ams2/geoViewer.html ubuntu@52.2.45.103:/home/ubuntu/allsky.com/htdocs/map.html"
cmd = "scp -i /home/ams/pem/ALLSKYTV-EAST.pem /mnt/ams2/aws-map-out.html ubuntu@52.2.45.103:/home/ubuntu/allsky.com/htdocs/aws-map-out.html"
print(cmd)
os.system(cmd)
