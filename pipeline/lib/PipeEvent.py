import os
from lib.PipeUtil import load_json_file, save_json_file, cfe
import glob
import datetime

def events_for_day(day, json_conf):
   amsid = json_conf['site']['ams_id']
   year = day[0:4]
   event_dir = "/mnt/ams2/meteor_archive/" + amsid + "/EVENTS/" + year + "/" + day + "/"  
   cloud_dir = "/mnt/archive.allsky.tv/" 
   if cfe(event_dir, 1) == 0:
      os.makedirs(event_dir)
   network_sites = json_conf['site']['multi_station_sync']
   print("EVD:", day)
   my_idx = "/mnt/ams2/meteors/" + day + "/" + day + "-" + amsid + ".meteors"
   os.system("cp " + my_idx + " " + event_dir)
   for ns in network_sites:
      print(ns)
      idx_file = day + "-" + ns + ".meteors"
      cloud_idx_file = cloud_dir + ns + "/METEOR/" + year + "/" + day + "/" + day + "-" + ns + ".meteors"
      cmd = "rsync -auv " + cloud_idx_file + " " + event_dir + idx_file
      print(cmd)
      #os.system(cmd)

   station_files = glob.glob(event_dir + "*.meteors")
   meteors = []
   for file in station_files:
      el = file.split("-AMS")
      station = el[1]
      station = station.replace(".meteors", "")
      station = "AMS" + station
      sm = load_json_file(file)
      for data in sm:
         (meteor, reduced, start_time, dur, ang_vel, ang_dist, hotspot) = data
         meteors.append((station,meteor, reduced, start_time, dur, ang_vel, ang_dist, hotspot))
   meteors = sorted(meteors, key=lambda x: (x[3]), reverse=False)
   events = {}
   for meteor in meteors:
      id, events = check_make_event(meteor, events)
   msc = 1
   for event in events:
      ust = len(set(events[event]['stations']))
      events[event]['total_stations'] = ust
      if ust >= 2:
         print(events[event]['files'])
         msc += 1
         events[event]['mse_id'] = msc

   save_json_file(event_dir + day + "_events.json", events)
   print("Total Obs:", len(meteors))
   print("Total Events:", len(events))
   print("Total MS events:", msc)
   for event_id in events:
      if amsid in events[event_id]['stations']:
         #print("MY event:", events[event_id]['stations'], events[event_id]['files'])
         for i in range(0, len(events[event_id]['stations'])):
            ts = events[event_id]['stations'][i]
            if ts == amsid:
               print("MY FILE!:", events[event_id]['files'][i])
               js = load_json_file(events[event_id]['files'][i])
               js['multi_station_event'] = events[event_id]
               save_json_file(events[event_id]['files'][i], js)
               print("SAVED", events[event_id]['files'][i])

def check_make_event(data, events):
   station,meteor, reduced, start_time, dur, ang_vel, ang_dist, hotspot = data
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
      if abs(time_diff) < 60:
         print("MATCH", station, event_id, start_datetime, event_datetime, (start_datetime - event_datetime).total_seconds())
         events[event_id]['start_datetime'].append(start_time) 
         events[event_id]['stations'].append(station) 
         events[event_id]['files'].append(meteor) 

         return(event_id, events)
      else:
         foo = 1
         #print("NO MATCH.", start_datetime, event_datetime, (start_datetime - event_datetime).total_seconds())

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


