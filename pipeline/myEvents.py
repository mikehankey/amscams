from Classes.Events import Events
import json
import requests
import cv2
import os
from Classes.MultiStationObs import MultiStationObs
from lib.PipeUtil import load_json_file, save_json_file
#from Classes.AIDB import AllSkyDB 
import sys



def load_stations():
   my_network = {}
   json_conf = load_json_file("../conf/as6.json")
   my_lat = float(json_conf['site']['device_lat'])
   my_lon = float(json_conf['site']['device_lng'])
   from lib.PipeUtil import dist_between_two_points
   url = "https://archive.allsky.tv/EVENTS/ALL_STATIONS.json"
   response = requests.get(url)
   content = response.content.decode()
   stations =json.loads(content)
   for station in stations:
      t_station_id = station['station_id']
      try:
         slat = float(station['lat'])
         slon = float(station['lon'])
         alt = float(station['alt'])
      except:
         slat = 0
         slon = 0

      dist = int(dist_between_two_points(my_lat, my_lon, slat, slon))
      if dist < 300:
         print("***", t_station_id, dist)
         my_network[t_station_id] = {}
         my_network[t_station_id]['dist_to_me'] = dist
         my_network[t_station_id]['lat'] = slat
         my_network[t_station_id]['lon'] = slon
         my_network[t_station_id]['alt'] = alt
         my_network[t_station_id]['operator'] = station['operator_name']
         my_network[t_station_id]['city'] = station['city']
      else:
         print(t_station_id, dist)
      json_conf['my_network'] = my_network
   save_json_file("../conf/as6.json", json_conf)
   return(stations)

def all_days(year):
   mdir = "/mnt/ams2/meteors/"
   mdirs = os.listdir(mdir)
   for md in sorted(mdirs,reverse=True):
      print(md)
      if year in md:
         if os.path.isdir(mdir + md) is True:
            cmd = "python3 myEvents.py " + md
            os.system(cmd)

def update_mj(root_fn, ev_data):
   date = root_fn[0:10]
   mjf = "/mnt/ams2/meteors/" + date + "/" + root_fn + ".json"
   mj = load_json_file(mjf)
   mj['multi_station_event'] = ev_data
   mj['event_id'] = ""
   mj['solve_status'] = ""
   
   save_json_file(mjf, mj)
   print("Saved", mjf)
   print("EV:", ev_data)
   print(root_fn)

def sync_meteor(EV, root_fn, cloud_files, mdir, cloud_dir):
   ms_dir = mdir.replace("/meteors/", "/METEOR_SCAN/")
   types = ["prev.jpg", "180p.mp4", "360p.jpg", "360p.mp4"] #, "1080p.jpg", "1080p.mp4"]
   missing = []
   cmds = []
   #print("CLOUD FILES:", cloud_files)
   #for cf in cloud_files:
   #   print(cf)
   #input('xxx')
   for cf in sorted(cloud_files):
      if root_fn in cf:
         for t in types:
            media_file = EV.station_id + "_" + root_fn + "-" + t 
            if media_file in cloud_files:
               print("CLOUD FILE EXISTS:", cf)
            else:

               if os.path.exists(ms_dir + media_file) is True:
                  #print("LOCAL FILE FOUND!", ms_dir + media_file)
                  cmd = "cp " + ms_dir + media_file + " " + cloud_dir + media_file
                  print(cmd)
                  cmds.append(cmd)
                  os.system(cmd)
               else:
                  print("NEED TO MAKE!", ms_dir + media_file)
                  if "360p.jpg" in media_file :

                     stack_file = media_file.replace("-360p.jpg", "-stacked.jpg")
                     stack_file = stack_file.replace(EV.station_id + "_", "")
                     stack_file = stack_file.replace("METEOR_SCAN", "meteors")
                     if os.path.exists(mdir + stack_file):
                        print("LOADING:", mdir + stack_file)
                        sd_stack_img = cv2.imread(mdir + stack_file)
                        sd_stack_img = cv2.resize(sd_stack_img, (640,360))
                        cv2.imwrite(ms_dir + media_file,sd_stack_img,[cv2.IMWRITE_JPEG_QUALITY, 80])
                        print("saved", ms_dir + media_file)
                     else:
                        print("Failed to read stack:", mdir + stack_file)
                     #except:
                     #   print("Could not save image.")

                  if "1080p.jpg" in media_file :
                   
                     mjf = media_file.replace("-1080p.jpg", ".json")
                     mjf = mjf.replace(EV.station_id + "_", "")
                     mjf = mjf.replace("METEOR_SCAN", "meteors")
                     mj = load_json_file(mdir + mjf)
                     hd_trim = mj['hd_trim']
                     hd_stack_file = hd_trim.replace(".mp4", "-stacked.jpg")
                     hd_stack_img = cv2.imread(hd_stack_file)
                     print('saved', ms_dir + media_file)
                     cv2.imwrite(ms_dir + media_file,hd_stack_img,[cv2.IMWRITE_JPEG_QUALITY, 80])
           
               missing.append(ms_dir + media_file)
   #exit()
   #for mf in missing:
   #   print("MISSING:", mf)

def valid_events(ev_data):
   valid_events = {}
   print("VALID EV:", ev_data)

   if isinstance(ev_data['stations'], str) is True:
      ev_data['stations'] = json.loads(ev_data['stations'])
   if isinstance(ev_data['obs'], str) is True:
      ev_data['obs'] = json.loads(ev_data['obs'])
   for i in range(0,len(ev_data['stations'])):
      station = ev_data['stations'][i]
      obs_file = ev_data['obs'][i]

def do_station_events(EV,date):
   print("Station Events", date)
   EV.date = ev_date
   EV.year = ev_date.split("_")[0]
   EV.month = ev_date.split("_")[1]
   EV.day = ev_date.split("_")[2]
   EV.cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS/" + EV.year + "/" + EV.month + "/" + EV.day + "/"
   mdir = "/mnt/ams2/meteors/" + ev_date + "/"
   station_events_cloud_file = EV.cloud_event_dir + EV.date + "_STATION_EVENTS.info" 
   station_events_local_file = mdir + EV.date + "_STATION_EVENTS.info" 
   if os.path.exists(station_events_local_file) is False:
      os.system("cp " + station_events_cloud_file + " " + station_events_local_file)
   if os.path.exists(station_events_local_file):
      station_events_data = load_json_file(station_events_local_file)
   else:
      station_events_data = {}
   if EV.station_id in station_events_data:
      for obs_id in station_events_data[EV.station_id]:
         print(EV.station_id, obs_id, station_events_data[EV.station_id][obs_id])

def do_day(EV, date):
   do_station_events(EV, date)

   EV.do_ms_day(date)
   EV.date = ev_date
   EV.year = ev_date.split("_")[0]
   EV.month = ev_date.split("_")[1]
   EV.day = ev_date.split("_")[2]
   ev_html = ""
   mdir = "/mnt/ams2/meteors/" + ev_date + "/"
   ms_vdir = "/METEOR_SCAN/" + ev_date + "/"
   cloud_dir = "/mnt/archive.allsky.tv/" + EV.station_id + "/METEORS/" + EV.year + "/" + EV.date + "/"


   print("CLOUD DIR:", cloud_dir)
   if os.path.exists(cloud_dir) is True:
      cloud_files = os.listdir(cloud_dir)
   else:
      cloud_files = []
   for mso in EV.my_ms_obs:
      print("Multi Station Obs:", mso )
      MSO.load_obs(mso)
      ev_html += "<img src=" + ms_vdir + EV.station_id + "_" + mso + "-ROI.jpg>\n"
      # for each MSO we should make sure ALL content is uploaded 
      # We should also check the AI?
   if os.path.exists("/mnt/ams2/" + ms_vdir) is False:
      os.makedirs("/mnt/ams2/" + ms_vdir)
   fp = open("/mnt/ams2/" + ms_vdir + "events.html", "w")
   fp.write(ev_html)
   print("saved /mnt/ams2/" + ms_vdir + "events.html")
   save_json_file("/mnt/ams2/meteors/" + ev_date + "/" + ev_date + "_MY_MS_OBS.info", EV.my_ms_obs)
   for mm in sorted(EV.min_cnt):
      valid_events(EV.min_cnt[mm])
      if isinstance(EV.min_cnt[mm]['times'], str) is True:
         EV.min_cnt[mm]['times'] = json.loads(EV.min_cnt[mm]['times'])
      if isinstance(EV.min_cnt[mm]['stations'], str) is True:
         EV.min_cnt[mm]['stations'] = json.loads(EV.min_cnt[mm]['stations'])
      if len(set(EV.min_cnt[mm]['stations'])) >= 2:
      
         for i in range(0,len(EV.min_cnt[mm]['times'])):
            st = EV.min_cnt[mm]['stations'][i]
            if st == EV.station_id:
               obs_file = EV.min_cnt[mm]['obs'][i]
               sync_meteor(EV, obs_file, cloud_files,mdir, cloud_dir)
               update_mj(obs_file, EV.min_cnt[mm])


EV = Events()
#AIDB = AllSkyDB()
load_stations()
MSO = MultiStationObs()
ev_date = sys.argv[1]
if ev_date == "all":
   all_days("2022")
else:
   do_day(EV, ev_date)
