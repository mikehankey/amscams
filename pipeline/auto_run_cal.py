#!/usr/bin/python3
import os
from lib.PipeUtil import load_json_file, save_json_file, cfe
run = 0
json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']
if cfe("/mnt/ams2/cal/plots", 1) == 0:
   run = 1
else:
   print("Plots exist.")
   for cam_num in json_conf['cameras']:
      cams_id = json_conf['cameras'][cam_num]['cams_id']
      mp_file = "/mnt/ams2/cal/multi_poly-" + station_id + "-" + cams_id + ".info"
      if cfe(mp_file) == 1:
         mpc = load_json_file(mp_file)
         res_px = (mpc['x_fun'] + mpc['y_fun']) / 2
         res_deg = (mpc['x_fun_fwd'] + mpc['y_fun_fwd']) / 2
         print("RES:", cams_id, res_px, res_deg)
         if res_px > 1:
            run = 1
if run == 1:
   print("WE SHOULD RUN THE LATEST CALS.")
   os.system("./Process.py deep_init all")
else:
   print("It looks like the calib is good to go!")
