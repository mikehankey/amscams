import sqlite3
import os
import sys
import glob
from lib.PipeUtil import load_json_file, save_json_file

def load_calib_file(filename):
   cal_fn = filename.split("/")[-1]
   root_fn = cal_fn.split("-")[0]
   cal_dir = "/mnt/ams2/cal/freecal/" + root_fn + "/" 
   cal_file = cal_dir + + root_fn + "-stacked-calparams.json"
   print(cal_file)

def load_camera_calib(cam_id, cur):
   cal_root = "/mnt/ams2/cal/freecal/"
   cal_dirs = glob.glob(cal_root + "*" + cam_id + "*")
   for cdd in sorted(cal_dirs,reverse=True):
      if "trim" in cdd:
         continue
      cal_rfn = cdd.split("/")[-1]
      cal_file = cdd + "/" + cal_rfn + "-stacked-calparams.json"
      if os.path.exists(cal_file) is True:
         print("FOUND", cal_file)
      else:
         print("NOT FOUND:", cal_file)


if __name__ == "__main__":
   json_conf = load_json_file("../conf/as6.json")

   con = sqlite3.connect(json_conf['site']['ams_id']+ "_ALLSKY.db")
   con.row_factory = sqlite3.Row
   cur = con.cursor()
   cam_id = sys.argv[1]
   load_camera_calib(cam_id, cur)
