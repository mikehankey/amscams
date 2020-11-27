from lib.PipeUtil import load_json_file, save_json_file, cfe
import os

def delete_meteor(amsid, data):
   print("YO")

def update_meteor_points(sd_video_file,frames):
   json_file = "/mnt/ams2/" + sd_video_file.replace(".mp4", ".json")
   rjson_file = json_file.replace(".json", "-reduced.json")
 
   mj = load_json_file(json_file)
   if "user_mods" in  mj:
      user_mods = mj['user_mods']
   else:
      user_mods = {}
      user_mods['frames'] = {}
   for row in frames:
 
      fn = row['fn']
      x = row['x']
      y = row['y']
      user_mods['frames'][fn] = [x,y]
   mj['user_mods'] = user_mods
   save_json_file(json_file, mj)
   resp = {
      "msg": "frames updated." 
   }
   cmd = "./Process.py roi_mfd /mnt/ams2/" + sd_video_file + " >/mnt/ams2/tmp/api.points 2>&1"
   os.system(cmd)
   mjr = load_json_file(rjson_file)
   resp['status'] = 1
   if "cal_params" in mj:
      resp['calib'] = mj['cal_params']
   if "meteor_frame_data" in mj:
      resp['frames'] = mjr['meteor_frame_data']

   return(resp)
   #for frame in frames:

def update_user_stars(amsid, data):
   print("YO")

def find_stars_in_pic(amsid, data):
   print("YO")

def blind_solve(amsid, data):
   print("YO")

def delete_cal(amsid, data):
   print("YO")

def update_cal_params(amsid, data):
   print("YO")
   

