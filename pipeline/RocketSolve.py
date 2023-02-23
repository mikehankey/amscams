"""

script for solving rocket launches and re-entries 

"""

import os
import glob 
from lib.PipeUtil import load_json_file, save_json_file
from Classes.Stations import Stations

# export frames for these times
exp_times = []

ST = Stations()
ST.load_station_data()
project_dir = "/mnt/f/meteorite_falls/2022_12_30_Korea_Rocket/"

obs_folders = os.listdir(project_dir)
good_obs_file = project_dir + "20221230_090705-GOOD_OBS.json"
good_obs = {}
for folder in obs_folders:
   print("FOLDER:", project_dir + folder)
   if os.path.isdir(project_dir + folder) and "AMS" in folder:
      print("FOUND FOLDER:", folder)
      
      wild = project_dir + folder + "/*frame_data.json"
      files = glob.glob(wild)
      station_id, cam = folder.split("-")
      data = load_json_file(files[0])

      #print("DATA KEYS:", data['frame_data'].keys())

      if station_id not in good_obs:
         good_obs[station_id] = {}
      if files[0] not in good_obs[station_id]:
         good_obs[station_id][files[0]] = {}
         good_obs[station_id][files[0]]['loc'] = ST.station_loc[station_id]
         good_obs[station_id][files[0]]['calib'] = []
         good_obs[station_id][files[0]]['times'] = []
         good_obs[station_id][files[0]]['xs'] = []
         good_obs[station_id][files[0]]['ys'] = []
         good_obs[station_id][files[0]]['azs'] = []
         good_obs[station_id][files[0]]['els'] = []
         good_obs[station_id][files[0]]['gc_azs'] = []
         good_obs[station_id][files[0]]['gc_els'] = []
         good_obs[station_id][files[0]]['ints'] = []
         good_obs[station_id][files[0]]['ras'] = []
         good_obs[station_id][files[0]]['decs'] = []
 
      #icnts.append((frame_time_str,cx,cy,radius,img_ra,img_dec,img_az,img_el,star_flux))
      frame_data = data['frame_data']
      for fn in frame_data:
         if "icnts" in frame_data[fn]:
            for icnt in frame_data[fn]['icnts']:
               timestamp = icnt[0].split(" ")[-1]
               hour, minute, second = timestamp.split(":")
               if minute != "14":
                  continue
               xsec = float(second)
               if xsec >= 59.9:
                  continue
               if ".000" in second:
                  frame_time_str,cx,cy,radius,img_ra,img_dec,img_az,img_el,star_flux = icnt
                  print(fn, frame_time_str,cx,cy,img_az, img_el,star_flux)
                  good_obs[station_id][files[0]]['times'].append(frame_time_str) 
                  good_obs[station_id][files[0]]['xs'].append(cx) 
                  good_obs[station_id][files[0]]['ys'].append(cy) 
                  good_obs[station_id][files[0]]['azs'].append(img_az) 
                  good_obs[station_id][files[0]]['els'].append(img_el) 
                  good_obs[station_id][files[0]]['gc_azs'].append(img_az) 
                  good_obs[station_id][files[0]]['gc_els'].append(img_el) 

                  good_obs[station_id][files[0]]['ints'].append(star_flux) 
                  good_obs[station_id][files[0]]['ras'].append(img_ra) 
                  good_obs[station_id][files[0]]['decs'].append(img_dec) 
                  
            #print(fn, frame_data[fn]['icnts'])

      save_json_file(good_obs_file, good_obs)
