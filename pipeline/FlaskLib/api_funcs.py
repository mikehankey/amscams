from lib.PipeUtil import load_json_file, save_json_file, cfe, bound_cnt
from lib.PipeAutoCal import get_image_stars, get_catalog_stars , pair_stars, eval_cnt, update_center_radec, fn_dir
from lib.PipeDetect import fireball, apply_frame_deletes
import os
import cv2
from FlaskLib.FlaskUtils import parse_jsid
import glob

def delete_frame(meteor_file, fn):
   resp = {}
   date = meteor_file[0:10]
   meteor_dir = "/mnt/ams2/meteors/" + date + "/"
   if "json" in meteor_file:
      meteor_vid = meteor_file.replace(".json", ".mp4")
      jsf = meteor_dir + meteor_file
   else:
      jf = meteor_file.replace(".mp4", ".json")
      jsf = meteor_dir + jf 
      meteor_vid = meteor_file
   mj = load_json_file(jsf)
   jsrf = jsf.replace(".json", "-reduced.json")
   if "user_mods" not in mj:
      mj['user_mods'] = {}
      mj['user_mods']['user_stars'] = []
      mj['user_mods']['frames'] = {}
      mj['user_mods']['del_frames'] = []
   else:
      if "del_frames" not in mj['user_mods']:
         mj['user_mods']['del_frames'] = []
   mj['user_mods']['del_frames'].append(fn)
   resp = {}
   resp['status'] = 1
   resp['msg'] = "frame deleted."

   if "best_meteor" in mj:
      print("BEST METEOR EXISTS IN MJ")
      if "cp" in mj['best_meteor']:
         print("CP EXISTS IN BEST METEOR")
         mj['cal_params'] = mj['best_meteor']['cp']
         del(mj['best_meteor']['cp'])

   
   print("MJCAL:", mj['cp'])
   mj,mjr = apply_frame_deletes(jsf,mj,None,None)
   save_json_file(jsf, mj)
   save_json_file(jsrf, mjr)
   return(resp)


def reduce_meteor(meteor_file):
   resp = {}
   date = meteor_file[0:10]
   meteor_dir = "/mnt/ams2/meteors/" + date + "/"
   if "json" in meteor_file:
      meteor_vid = meteor_file.replace(".json", ".mp4")
   else:
      meteor_vid = meteor_file
   
   cmd = "./Process.py fireball " + meteor_dir + meteor_vid + " > /mnt/ams2/trash/fb.txt 2>&1"
   print(cmd)
   os.system(cmd)
   resp['msg'] = "reduced."
   resp['status'] = 1 
   resp['sd_meteor_frame_data'] =  []
   return resp

def delete_meteor(jsid, data):
   resp = {}
   json_conf = load_json_file("../conf/as6.json")
   amsid = json_conf['site']['ams_id']
   video_file = parse_jsid(jsid)
   print("VID:", video_file)
   resp['msg'] = "deleted."
   delete_log = "/mnt/ams2/SD/proc2/json/" + amsid + ".del"
   if cfe(delete_log) == 1:
      del_data = load_json_file(delete_log)
   else:
      del_data = {}
   fn, dir = fn_dir(video_file)
   el = fn.split(".")
   base = el[0]
   del_data[base] = 1

   save_json_file(delete_log, del_data)


   return resp

def delete_meteors(data):
   resp = {}
   json_conf = load_json_file("../conf/as6.json")
   amsid = json_conf['site']['ams_id']
   detections = data['detections'].split(";")
   delete_log = "/mnt/ams2/SD/proc2/json/" + amsid + ".del"
   if cfe(delete_log) == 1:
      del_data = load_json_file(delete_log)
   else:
      del_data = {} 
   for det in detections:
      if len(det) < 5:
         continue
      video_file = parse_jsid(det)
      fn, dir = fn_dir(video_file)
      el = fn.split(".")
      base = el[0]
      del_data[base] = 1
  
   save_json_file(delete_log, del_data) 
   resp['msg'] = "deleted multi."
   return resp

def show_cat_stars (video_file, hd_stack_file, points):

   json_conf = load_json_file("../conf/as6.json")
   cp = None
   if "cal" in video_file:
      app_type = "calib"
   else:
      app_type = "meteor"

   if app_type == "meteor":
      mjf = "/mnt/ams2/" + video_file.replace(".mp4", ".json")
      mjrf = "/mnt/ams2/" + video_file.replace(".mp4", "-reduced.json")
      mj = load_json_file(mjf)
      mjr = load_json_file(mjrf)
      if "cp" in mj:
         cp = mj['cp']
      elif "best_meteor" in mj:
         if "cp" in mj['best_meteor']:
            mj['cp'] = mj['best_meteor']['cp']
            cp = mj['cp']
      c = update_center_radec(video_file,cp,json_conf)
      if "hd_stack" in mj:
         hd_img = cv2.imread(mj['hd_stack'], 0)
         print("HD IMG:", hd_img.shape)
   else:
      cal_r = video_file.replace("-half-stack.png", "")
      cal_root = "/mnt/ams2" + cal_r 
      cps = glob.glob(cal_root + "*calparams.json")
      sfs = glob.glob(cal_root + "*stacked.png")
      stack_file = sfs[0]
      cpf = cps[0]
      cp = load_json_file(cpf)
      hd_img = cv2.imread(stack_file, 0)

   if cp is None:
      resp = {
         "status" : 0
      }
      return(resp)

   pts = points.split("|")
   user_stars = []
   for pt in pts:
      ddd = pt.split(",")
      if len(ddd) != 2:
         continue
      sx, sy = pt.split(",")
      sx = int(float(sx)) + 5
      sy = int(float(sy)) + 5
      sx = int(float(sx)) * 2
      sy = int(float(sy)) * 2
      rx1,ry1,rx2,ry2 = bound_cnt(sx,sy,hd_img.shape[1],hd_img.shape[0], 10)
      cnt_img = hd_img[ry1:ry2, rx1:rx2]
      cv2.imwrite("/mnt/ams2/test.jpg", cnt_img)
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_img)
      # subtract away 1/2 shape for center pos starting point
      #mx = mx - 5
      #my = my - 5
      #mx = 0
      #my = 0
      grid_val = max_val - 25
      #max_px, avg_px, px_diff,max_loc,grid_int = eval_cnt(cnt_img, grid_val)
      #nsx = rx1 + max_loc[0]
      #nsy = ry1 + max_loc[1]
      nsx = rx1 + mx
      nsy = ry1 + my
      print("CLOSE IMAGE STAR LOCATION:", sx, sy, nsx, nsy, mx, my)
      user_stars.append((nsx,nsy,999))

   cp['user_stars'] = user_stars
   cp = pair_stars(cp, video_file, json_conf, hd_img)

   resp = {}

   if app_type == "meteor":
      if "user_mods" not in mj:
         mj['user_mods'] = {}
      if "user_stars" not in mj['user_mods']:
         mj['user_mods']['user_stars'] = user_stars
      else:
         mj['user_mods']['user_stars'] = user_stars
      mj['cp'] = cp
      mjr['cal_params'] = cp
      save_json_file(mjf, mj)
      save_json_file(mjrf, mjr)
      resp['crop_box'] = mjr['crop_box']
   else:
      resp['crop_box'] = [0,0,0,0]
      if "user_mods" not in cp:
         cp['user_mods'] = {}
      cp['user_mods']['user_stars'] = cp['user_stars']
      save_json_file(cpf, cp)
      print("SAVED CALPARAMS IN:", cpf)


   resp['msg'] = "good"
   resp['status'] = 1
   resp['cp'] = cp
   return(resp)


def update_meteor_points(sd_video_file,frames):
   json_file = "/mnt/ams2/" + sd_video_file.replace(".mp4", ".json")
   rjson_file = json_file.replace(".json", "-reduced.json")
 
   mj = load_json_file(json_file)
   if "user_mods" in  mj:
      user_mods = mj['user_mods']
   else:
      user_mods = {}
   if "frames" not in user_mods:
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
   print("COMMAND:", cmd)
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
   

