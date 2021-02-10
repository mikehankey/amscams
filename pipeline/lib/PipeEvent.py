import os
from lib.PipeUtil import load_json_file, save_json_file, cfe, convert_filename_to_date_cam
from DynaDB import load_meteor_obs_day,  search_obs, insert_meteor_event, search_events, delete_event, delete_obs
import glob
import datetime
from lib.PipeAutoCal import fn_dir
from lib.PipeDetect import get_trim_num
import boto3
from boto3.dynamodb.conditions import Key



def solve_day(day, json_conf):
   amsid = json_conf['site']['ams_id']
   meteor_index = "/mnt/ams2/meteors/" + day + "/" + day + "-" + amsid + ".meteors"
   mid = load_json_file(meteor_index)
   for data in mid:
      meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot, msm = data
      if msm == 1:
         #cmd = "./cartmap.py " + meteor_file
         cmd = "./Process.py simple_solve " + meteor_file
         os.system(cmd)
         cmd = "./KML.py " + meteor_file
         os.system(cmd)


def make_obs_object(mse):

   nsinfo = load_json_file("../conf/network_station_info.json")

   obs = {}
   for i in range(0, len(mse['stations'])):
      station = mse['stations'][i]
      file = mse['files'][i]
      fn, dir = fn_dir(file)

      if station not in obs:
         obs[station] = {}
      if fn not in obs[station]:

         obs[station][fn] = {}
         obs[station][fn]['loc'] = nsinfo[station]['loc']
         obs[station][fn]['times'] = []
         obs[station][fn]['fns'] = []
         obs[station][fn]['xs'] = []
         obs[station][fn]['ys'] = []
         obs[station][fn]['azs'] = []
         obs[station][fn]['els'] = []
         obs[station][fn]['ras'] = []
         obs[station][fn]['decs'] = []
         obs[station][fn]['ints'] = []
      mfd = mse['mfds'][i]
      if "meteor_frame_data" in mfd:
         for mc in range(0, len(mfd['meteor_frame_data'])):
            data = mfd['meteor_frame_data'][mc]
            dt, fnum, x, y, w, h, oint, ra, dec, az, el = data
            obs[station][fn]['times'].append(dt)
            obs[station][fn]['fns'].append(fnum)
            obs[station][fn]['xs'].append(x)
            obs[station][fn]['ys'].append(y)
            obs[station][fn]['ints'].append(oint)
            obs[station][fn]['ras'].append(ra)
            obs[station][fn]['decs'].append(dec)
            obs[station][fn]['azs'].append(az)
            obs[station][fn]['els'].append(el)
            print("DATA:", fn, data)

   for station in obs:
       for file in obs[station]:
         print(station, file, obs[station][file] )

   return(obs)




def get_network_info(json_conf):
   amsid = json_conf['site']['ams_id']
   ms = json_conf['site']['multi_station_sync']
   station_info = {}
   for ts in ms:
      local_dir = "/mnt/ams2/meteor_archive/" + ts + "/CAL/"
      cloud_dir = "/mnt/archive.allsky.tv/" + ts + "/CAL/"
      if cfe(local_dir,1) == 0:
         os.makedirs(local_dir)
      local_file = local_dir + "as6.json"
      cloud_file = cloud_dir + "as6.json"
      if cfe(local_file) == 0:
         if cfe(cloud_file) == 1:
            os.system("cp " + cloud_file + " " + local_file)
      print(local_file)
      js = load_json_file(local_file)
      loc = []
      loc.append(js['site']['device_lat'])
      loc.append(js['site']['device_lng'])
      loc.append(js['site']['device_alt'])
      station_info[ts] = {}
      station_info[ts]['loc'] = loc
   
   station_info[amsid] = {}
   loc = []
   loc.append(json_conf['site']['device_lat'])
   loc.append(json_conf['site']['device_lng'])
   loc.append(json_conf['site']['device_alt'])
   station_info[amsid]['loc'] = loc
   save_json_file("../conf/network_station_info.json", station_info)
   print("saved: ", "../conf/network_station_info.json")

      
def dyna_events_for_month(wild, json_conf):
   files = glob.glob("/mnt/ams2/meteors/" + wild + "*")
   for file in files:
      day = file.split("/")[-1]
      dyna_events_for_day(day, json_conf)

def dyna_events_for_day(day, json_conf):

   dynamodb = boto3.resource('dynamodb')

   amsid = json_conf['site']['ams_id']
   my_station = json_conf['site']['ams_id']
   stations = json_conf['site']['multi_station_sync']
   if my_station not in stations:
      stations.append(my_station)

   # Load up events for today
   date = day
   le_dir = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/EVENTS/" + date + "/"
   event_file = le_dir + date + "_events.json"
   dy_events = load_json_file(event_file)
   dy_keys = {}
   for event in dy_events:
      dy_keys[event['event_id']] = event

   all_data = {}
   for station in stations:
      obs_file = le_dir + station + "_" + date + ".json"
      all_data[station] = load_json_file(obs_file)


   # first get all existing known events
   events = {}


   # loop over all obs from all stations 
   # if obs does not have a registered event id register the new event in events table and update related obs with event id
   #  
   if cfe("/mnt/ams2/EVENTS/" + day, 1) == 0:
      os.makedirs("/mnt/ams2/EVENTS/" + day ) 

   all_obs = {}
   for station in sorted(stations):
      #print("getting dyna data for:", station)
      #all_data[station] = search_obs(dynamodb, station, day)
      for item in all_data[station]:
         sd_video_file = item['sd_video_file']
         key = station + "_" + sd_video_file
         all_obs[key] = 1 

   #save_json_file("/mnt/ams2/EVENTS/" + day + "_obs.json", all_data)
   #print("/mnt/ams2/EVENTS/" + day + "_obs.json", all_data)

   # now check each event and make sure it belongs to this cluster of stations
   # also make sure the obs files are still valid (haven't been deleted).

   my_events = {}
   evd = 0
   for event in dy_events:
      in_network = 0
      for station in stations:
         if station in event['stations']:
            in_network += 1
      if in_network == 0: 
         print("This event is not part of our local network, skip it.")
         continue
      # check if the obs are sill valid.
      for i in range(0, len(event['stations'])):
         station = event['stations'][i]
         file = event['files'][i]
         key = station + "_" + file 
         if key in all_obs:
            print("OBS IS GOOD") 
         else:
            print("OBS IS NOT GOOD", event['event_id'], station) 
            delete_event(dynamodb, day, event['event_id']) 
            evd += 1

   meteors = []
   for station in all_data:
      for item in all_data[station]:
         if item['event_start_time'] == "":
            (f_datetime, cam, f_date_str,fy,fm,fd, max_h, fmin, fs) = convert_filename_to_date_cam(item['sd_video_file'])
            trim_num = int(get_trim_num(item['sd_video_file']))
            extra_sec = int(trim_num) / 25
            start_time_dt = f_datetime + datetime.timedelta(0,extra_sec)
            start_time_dt_str = start_time_dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            item['event_start_time'] = start_time_dt_str

         meteor = [item['station_id'],item['sd_video_file'], item['event_start_time']]
         meteors.append((item['station_id'],item['sd_video_file'], item['event_start_time']))
   meteors = sorted(meteors, key=lambda x: (x[2]), reverse=False)
   events = {}


   for meteor in meteors:
      id, events = check_make_event(meteor, events)
      #print(meteor)

   for eid in events:
      total_stations = len(set(events[eid]['stations']))
      events[eid]['total_stations'] = total_stations
      if total_stations > 1: 
         print("MULTI", eid, events[eid])
         min_time = min(events[eid]['start_datetime'])
         day = min_time[0:10]
         day = day.replace("-", "_")
         min_time = min_time.replace("-", "")
         min_time = min_time.replace(":", "")
         min_time = min_time.replace(" ", "_")
         if "." in min_time:
            rt, xx = min_time.split(".")
            min_time = rt
         wmpl_id = min_time
         events[eid]['event_day'] = day
         events[eid]['event_id'] = wmpl_id
         print("MIN TIME:", wmpl_id, day, events[eid])
         print("EID:", wmpl_id)
         if wmpl_id not in dy_keys:
            print("INSERT NEW METEOR EVENT!", wmpl_id)
            insert_meteor_event(dynamodb, wmpl_id, events[eid])
         else:
            print("EVENT ID ALREADY EXISTS IN THE DYNA DATA!")
            print(dy_keys[wmpl_id])
      #else:
      #   print("SINGLE STATION:", eid, events[eid])


   # Now update my meteor files with the mse info
   for eid in events:
      if "event_id" in events[eid]:
         for i in range(0, len(events[eid]['stations'])):
            st = events[eid]['stations'][i]
            file = events[eid]['files'][i]
            event_id = events[eid]['event_id']
            if st == amsid:
               print("\nFILE:", file)
               #print("THIS FILE IS MINE AND SHOULD BE UPDATED WITH EVENT INFO!")
               day = file[0:10]
               md = "/mnt/ams2/meteors/" + day + "/"  
               mf = md + file
               mf = mf.replace(".mp4", ".json")
               mj = load_json_file(mf)
               mj['multi_station_event'] = events[eid]
               if event_id not in dy_keys:
                  print("EVENT ID NOT FOUND IN DYKEYS. new event?:", event_id, mf)
                  dy_keys[event_id] = events[eid]
               dyd = dy_keys[event_id]
               if "solve_status" in dyd:
                  if "SUC" in dyd['solve_status']:
                     dyd['solve_status'] = "SUCCESS"
                     if "solution" in dyd:
                        event_dir = dyd['solution']['sol_dir'].replace("/mnt/ams2/meteor_archive/", "http://archive.allsky.tv/")
                        print("UPDATING MSE FOR SOLVED EVENT:")
                        print( eid, event_id, st, file, dyd['solve_status'], event_dir, dyd['solution']['orb']['link'])
                        mj['multi_station_event']['event_id'] = event_id
                        mj['multi_station_event']['solve_status'] = "SUCCESS"
                        mj['multi_station_event']['event_file'] = event_dir + "/index.html"
                        if "http" in dyd['solution']['orb']['link']:
                           mj['multi_station_event']['orb_file'] = event_dir + dyd['solution']['orb']['link']
                     else:
                        print("EVENT FAILED!?", syd['solve_status'])
                        mj['multi_station_event']['solve_status'] = "FAILED"
                  else:
                     print("UPDATING MSE FOR EVENT SOLUTION MISSING!:")
                     print(event_id, st, file, dyd['solve_status'] )
                     mj['multi_station_event']['solve_status'] = "WMPL FAILED"
               else:
                  print("UPDATING MSE FOR UN-SOLVED EVENT:", eid, event_id, st, file)
                  mj['multi_station_event']['solve_status'] = "NOT RUN"
               print("saving:", mf)
               save_json_file(mf, mj)
               #exit()
   os.system("./Process.py sync_prev_all " + date)
   


def events_for_day(day, json_conf):
   amsid = json_conf['site']['ams_id']
   year = day[0:4]
   event_dir = "/mnt/ams2/meteor_archive/" + amsid + "/EVENTS/" + year + "/" + day + "/"  
   cmd = "rm " + event_dir + "*AMS*"
   os.system(cmd)
   cloud_dir = "/mnt/archive.allsky.tv/" 
   if cfe(event_dir, 1) == 0:
      os.makedirs(event_dir)
   network_sites = json_conf['site']['multi_station_sync']
   print("EVD:", day)
   my_idx = "/mnt/ams2/meteors/" + day + "/" + day + "-" + amsid + ".meteors"
   my_detail = "/mnt/ams2/meteors/" + day + "/" + day + "-" + amsid + "-detail.meteors"
   os.system("cp " + my_idx + " " + event_dir)
   os.system("cp " + my_detail + " " + event_dir)
   print("cp " + my_idx + " " + event_dir)
   print("cp " + my_detail + " " + event_dir)

   for ns in network_sites:
      print(ns)
      idx_file = day + "-" + ns + ".meteors"
      detail_file = day + "-" + ns + "-detail.meteors.gz"
      cloud_idx_file = cloud_dir + ns + "/METEORS/" + year + "/" + day + "/" + day + "-" + ns + ".meteors"
      cloud_detail_file = cloud_dir + ns + "/METEORS/" + year + "/" + day + "/" + day + "-" + ns + "-detail.meteors.gz"
      cmd = "rsync -auv " + cloud_idx_file + " " + event_dir + idx_file
      print(cmd)
      os.system(cmd)
      cmd = "rsync -av " + cloud_detail_file + " " + event_dir + detail_file
      print(cmd)
      os.system(cmd)
      cmd = "gunzip -kf " + event_dir + detail_file
      print("GUNZIP:", cmd)
      os.system(cmd)

   station_files = glob.glob(event_dir + "*.meteors")
   meteors = []
   meteor_details = {}

   for file in station_files:
      el = file.split("-AMS")
      station = el[1]
      station = station.replace(".meteors", "")
      station = station.replace("-detail", "")
      station = "AMS" + station

      if "detail" in file:
         print("loading:", station, file)
         #if station not in meteor_details:
         details = load_json_file(file)
         meteor_details[station] = details 


   for station in meteor_details:
      print(station)
      for key in meteor_details[station]:
         #print(key, meteor_details[station][key])
         print(station, key, len(meteor_details[station][key]))

   #exit()

   for file in station_files:
      el = file.split("-AMS")
      station = el[1]
      station = station.replace(".meteors", "")
      station = "AMS" + station
      if "detail" in file:
         continue
      print("LOADING:", file)
      sm = load_json_file(file)
      print("LOADED:", file)
      for data in sm:
         print("DATA:", data)
         (meteor, reduced, start_time, dur, ang_vel, ang_dist, hotspot, msm) = data
         meteors.append((station,meteor, reduced, start_time, dur, ang_vel, ang_dist, hotspot, msm))
   meteors = sorted(meteors, key=lambda x: (x[3]), reverse=False)
   events = {}
   for meteor in meteors:
      id, events = check_make_event(meteor, events)
   msc = 1
   for event in events:
      ust = set(events[event]['stations'])
      ustl = list(ust)
      ts = len(ustl)
      print("STATIONS:", events[event]['stations'])
      print("TS:", ts)
      events[event]['total_stations'] = ts
      if ts >= 2:
         print(events[event]['files'])
         msc += 1
         events[event]['mse_id'] = msc
         events[event]['event_id'] = event

   save_json_file(event_dir + day + "_events.json", events)
   print("EVENTS:", event_dir + day + "_events.json", events)

   station_files = glob.glob(event_dir + "*.meteors")
   meteors = []
   for file in station_files:
      if "detail" in file:
         continue
      el = file.split("-AMS")
      station = el[1]
      station = station.replace(".meteors", "")
      station = "AMS" + station
      sm = load_json_file(file)
      print("LOAD:", file)
      for data in sm:
         print("DATA:", data)
         (meteor, reduced, start_time, dur, ang_vel, ang_dist, hotspot, msm) = data
         meteors.append((station,meteor, reduced, start_time, dur, ang_vel, ang_dist, hotspot, msm))
   meteors = sorted(meteors, key=lambda x: (x[3]), reverse=False)
   events = {}
   for meteor in meteors:
      id, events = check_make_event(meteor, events)
   msc = 1
   for event in events:
      ust = set(events[event]['stations'])
      ustl = list(ust)
      ts = len(ustl)
      print("STATIONS:", events[event]['stations'])
      print("TS:", ts)
      events[event]['total_stations'] = ts
      if ts >= 2:
         print(events[event]['files'])
         msc += 1
         events[event]['mse_id'] = msc
         events[event]['event_id'] = event
         if "mfds" not in events[event]:
            events[event]['mfds'] = []
         for cc in range (0, len(events[event]['stations'])):
            st = events[event]['stations'][cc]
            fl = events[event]['files'][cc]
            if st in meteor_details:
               mfd = meteor_details[st][fl]
            else:
               print(events[event])
               print("FILE MISSING MFD!", st, fl)
               continue
               mfd = []
            events[event]['mfds'].append(mfd)
         obs = make_obs_object(events[event])
         events[event]['obs'] = obs

   save_json_file(event_dir + day + "_events.json", events)
   print("SAVED:", event_dir + day + "_events.json")
   print("Total Obs:", len(meteors))
   print("Total Events:", len(events))
   print("Total MS events:", msc)


   for event_id in events:
      if amsid in events[event_id]['stations']:
         for i in range(0, len(events[event_id]['stations'])):
            obs_file = events[event_id]['files'][i]
            ts = events[event_id]['stations'][i]
            if ts == amsid:
             
               print("STATIONS:", events[event_id]['stations'])
               print("TOTAL STATIONS:", events[event_id]['total_stations'])
               print("MY FILE!:", events[event_id]['files'][i])
               js = load_json_file(events[event_id]['files'][i])
               if events[event_id]['total_stations'] > 1:
                  js['multi_station_event'] = events[event_id]
                  js['multi_station_event']['event_id'] = event_id
                  save_json_file(events[event_id]['files'][i], js)
                  print("EVENT FOUND", events[event_id]['files'][i])
               elif "multi_station_event" in js: 
                  del js['multi_station_event']
                  save_json_file(events[event_id]['files'][i], js)
                  print("NO EVENT FOUND", events[event_id]['files'][i])

def check_make_event(data, events):
   if len(data) == 3:
      station,meteor, start_time = data
   else:
      station,meteor, start_time = data[0], data[1], data[3]
   if "." in start_time:
      start_datetime = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S.%f")
   else:
      start_datetime = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
   if len(events) == 0:
      event_id = 1
      events[event_id] = {}
      events[event_id]['start_datetime'] = [] 
      events[event_id]['start_datetime'].append(start_time) 
      events[event_id]['stations'] = [] 
      events[event_id]['stations'].append(station) 
      events[event_id]['files'] = [] 
      events[event_id]['files'].append(meteor) 
      return(event_id, events)

   # look for matching event 
   for event_id in events:
      event_dt = events[event_id]['start_datetime'][0] 
      if "." in event_dt:
         event_datetime = datetime.datetime.strptime(event_dt, "%Y-%m-%d %H:%M:%S.%f")
      else:
         event_datetime = datetime.datetime.strptime(event_dt, "%Y-%m-%d %H:%M:%S")
      time_diff = (start_datetime - event_datetime).total_seconds()
      if abs(time_diff) < 2:
         #print("MATCH", station, event_id, start_datetime, event_datetime, (start_datetime - event_datetime).total_seconds())
         events[event_id]['start_datetime'].append(start_time) 
         events[event_id]['stations'].append(station) 
         events[event_id]['files'].append(meteor) 

         return(event_id, events)

   # not the 1st and not found so make a new one
   this_id = max(events.keys()) + 1

   if True:
      event_id = this_id
      events[event_id] = {}
      events[event_id]['start_datetime'] = [] 
      events[event_id]['start_datetime'].append(start_time) 
      events[event_id]['stations'] = [] 
      events[event_id]['stations'].append(station) 
      events[event_id]['files'] = [] 
      events[event_id]['files'].append(meteor) 
      return(event_id, events)


