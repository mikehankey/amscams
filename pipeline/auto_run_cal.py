#!/usr/bin/python3
import datetime
import os
from lib.PipeUtil import load_json_file, save_json_file, cfe
run = 0
json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']
cal_sys_hist_file = "/mnt/ams2/cal/freecal/" + station_id + "_cal_sys_hist.json"
if cfe(cal_sys_hist_file) == 1:
   cal_sys_hist = load_json_file(cal_sys_hist_file)
else:
   cal_sys_hist = {}
   cal_sys_hist['cams'] = {} 

if cfe("/mnt/ams2/cal/plots", 1) == 0:
   run = 1
else:
   print("Plots exist.")
   for cam_num in json_conf['cameras']:
      cams_id = json_conf['cameras'][cam_num]['cams_id']
      if cams_id not in cal_sys_hist['cams']:
         cal_sys_hist['cams'][cams_id] = {}

      mp_file = "/mnt/ams2/cal/multi_poly-" + station_id + "-" + cams_id + ".info"
      sdb_file = "/mnt/ams2/cal/star_db-" + station_id + "-" + cams_id + ".info"
      if cfe(sdb_file) == 1:
         sdb = load_json_file(sdb_file)
      if cfe(mp_file) == 1:
         mpc = load_json_file(mp_file)
         res_px = (mpc['x_fun'] + mpc['y_fun']) / 2
         res_deg = (mpc['x_fun_fwd'] + mpc['y_fun_fwd']) / 2
         cal_sys_hist['cams'][cams_id]['res_px'] = res_px
         cal_sys_hist['cams'][cams_id]['res_deg'] = res_deg
         cal_sys_hist['cams'][cams_id]['total_stats'] = len(sdb)
         print("RES:", cams_id, res_px, res_deg)
         if res_px > 1:
            run = 1
cal_sys_hist['last_updated'] = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
save_json_file(cal_sys_hist_file, cal_sys_hist)
print("SAVED:", cal_sys_hist_file )

if run == 1:
   print("WE SHOULD RUN THE LATEST CALS.")
   os.system("./Process.py deep_init all")
else:
   print("It looks like the calib is good to go!")
