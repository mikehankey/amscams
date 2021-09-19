#!/usr/bin/python3

import os
import sys
from lib.PipeUtil import get_file_info, load_json_file, save_json_file, cfe
json_conf = load_json_file("../conf/as6.json")

def update_all_obs_events(json_conf):
   station_id = json_conf['site']['ams_id']

   local_event_dir = "/mnt/ams2/EVENTS/OBS/STATIONS/" 
   update_log_file = local_event_dir + "all_obs_events_update_log.json"
   corrupt_log_file = local_event_dir + "corrupted_obs_files.json"
   if cfe(update_log_file) == 1:
      update_log = load_json_file(update_log_file)
   else:
      update_log = {}
   if cfe(local_event_dir,1) == 0:
      os.makedirs(local_event_dir)
   all_obs_events_cloud_file = "/mnt/archive.allsky.tv/EVENTS/OBS/STATIONS/" + station_id + "_EVENTS.json"
   all_obs_events_local_file = "/mnt/ams2/EVENTS/OBS/STATIONS/" + station_id + "_EVENTS.json"
   if cfe(all_obs_events_local_file) == 0:
      if cfe(all_obs_events_cloud_file) == 1:
         os.system("cp " + all_obs_events_cloud_file + " " + all_obs_events_local_file)
   else:
      # we already have the 'bulk' all events obs table for our station
      # but we should probably updated with the days since the last time it 
      # was updated
      # after major updates / back runs / or full sync requests we should re-grab the entire file
      # and re-apply it
      # We should also keep track of the events/obs we have already updated locally so we don't
      # do them over and over!
      # For now do nothing...
      size, tdiff = get_file_info(all_obs_events_local_file)
      print("The obs_events file is this many minutes old.", tdiff)
      if tdiff / 60 > 12:
         print("We should update the local obs files for events created in the last 24 hours.")
   all_obs_events = load_json_file(all_obs_events_local_file)
   corrupt = {}
   for key in all_obs_events:
      print(key, all_obs_events[key])
      if key in update_log:
         if update_log[key] == all_obs_events[key]:
            print("This obs is up-to-date with the event data.", key)
            continue
      json_file = "/mnt/ams2/meteors/" + key[0:10] + "/" + key + ".json"
      if cfe(json_file) == 0:
         print("THIS OBS NO LONGER EXISTS. IT MUST BE DELETED?")
         continue
      try:
         mj = load_json_file(json_file)
      except:
         corrupt[key] = 1
         continue
      if "multi_station_event" in mj:
         local_event_id = mj['multi_station_event']['event_id']
         local_event_status = mj['multi_station_event']['solve_status']
         event_id, solve_status = all_obs_events[key].split(":")
         if event_id != local_event_id or local_event_status != solve_status:
            mj['multi_station_event']['event_id'] = event_id
            mj['multi_station_event']['solve_status'] = solve_status
            save_json_file(json_file,mj)
            print("Event solve or id changed. Saving event info to:", json_file)
            update_log[key] = all_obs_events[key]
         else:
            print("This event is up-to-date", json_file)
            update_log[key] = all_obs_events[key]

      else:
         mj['multi_station_event'] = {}
         mj['multi_station_event']['event_id'] = event_id
         mj['multi_station_event']['solve_status'] = solve_status
         print("Local event info missing. Saving event info to:", json_file)
         save_json_file(json_file,mj)
         update_log[key] = all_obs_events[key]
   save_json_file(update_log_file, update_log)
   save_json_file(corrupt_log_file, corrupt)
   print("SAVED:", update_log_file)
      

update_all_obs_events(json_conf)
