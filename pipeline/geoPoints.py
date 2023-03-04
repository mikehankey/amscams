from geojson import Point , LineString, Polygon, Feature, FeatureCollection, dumps
import datetime
import json
import requests
import os
import time
from lib.PipeUtil import load_json_file, save_json_file, get_template

map_temp = get_template("aws-map-template.html")
stations_file = "/mnt/f/EVENTS/ALL_STATIONS.json"
stations_check_file = "/mnt/f/EVENTS/LAST_STATIONS_CHECK.json"
stations = load_json_file(stations_file)
if os.path.exists(stations_check_file) is True:
   stations_check = load_json_file(stations_check_file)
else:
   stations_check = {}

all_points = []
for st in stations:
   station_id = st['station_id']
   op_status = st['op_status']
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
      my_feature = Feature(geometry=Point((float(st['lon']), float(st['lat']))))
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

      if doit is True :
         try:
         #if True:

            url = "https://archive.allsky.tv/" + station_id + "/LATEST/" + zcam + ".jpg"
            response = requests.head(url)
            if response is not None and "Last-Modified" in response.headers:
               print(response.headers)
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
      my_feature['properties']['cams'] = cams 
      my_feature['properties']['message'] = station_id  
      my_feature['properties']['iconSize'] = [100,100] 
      my_feature['properties']['station_id'] = station_id
      my_feature['properties']['operator_name'] = st['operator_name'] 
      my_feature['properties']['last_ping_elp_days'] = float(ping_time_elp_days)
      my_feature['properties']['last_ping'] = last_ping
      my_feature['properties']['city'] = st['city'] 
      my_feature['properties']['state'] = st['state'] 
      my_feature['properties']['country'] = st['country'] 
      my_feature['properties']['zcam'] = zcam 
      all_points.append(my_feature)
   #except:
   #   print("BAD/MISSING LAT/LON", st['station_id'], st['lat'], st['lon'])
   #input(st['station_id'] + " " +  st['op_status'])
jdata = FeatureCollection(all_points)
save_json_file ("/mnt/f/EVENTS/stations.geo", jdata)
print("/mnt/f/EVENTS/stations.geo" )
map_temp = map_temp.replace("{GEOJSON}", dumps(jdata))
print(map_temp)
fpout = open("/mnt/ams2/aws-map-out.html", "w")
fpout.write(map_temp)
fpout.close()
save_json_file(stations_check_file, stations_check)
