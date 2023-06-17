from lib.PipeUtil import load_json_file, save_json_file, cfe, bound_cnt, convert_filename_to_date_cam, do_photo
from lib.PipeAutoCal import get_image_stars, get_catalog_stars , pair_stars, eval_cnt, update_center_radec, fn_dir
from lib.PipeDetect import fireball, apply_frame_deletes, find_object, analyze_object, make_base_meteor_json, fireball_fill_frame_data, calib_image, apply_calib, grid_intensity_center, make_roi_video_mfd
from lib.PipeVideo import ffprobe, load_frames_fast, load_frames_simple

import os
import cv2
   #ny = int(int(y) / hdm_y)
from FlaskLib.FlaskUtils import parse_jsid
import glob
import numpy as np
#def vid_to_frames(vid, out_dir, suffix, ow, oh ):
   #/usr/bin/ffmpeg -i /mnt/ams2/meteors/2020_10_18/2020_10_18_10_28_12_000_010006-trim-0501.mp4 -vf 'scale=960:640' /mnt/ams2/CACHE/2020/10/2020_10_18_10_28_12_000_010006-trim-0501/2020_10_18_10_28_12_000_010006-trim-0501-half-%04d.jpg > /dev/null 2>&1

def update_meteor_cal_params(meteor_file, cal_file, json_conf):
   # This function / api call will swap the calparams in a meteor file 
   # with the calparams in the provided file. 
   # use it for the "Swap Calibration" buttons on the meteor detail page
   # api call is : /API/update_meteor_cal_params?meteor_file=XXX&calib_file=YYY
   mdir = "/mnt/ams2/meteors/" + meteor_file[0:10] + "/" 
   cal_dir = "/mnt/ams2/cal/freecal/" + cal_file + "/"

   mjf = mdir + meteor_file
   mjrf = mdir + meteor_file.replace(".json", "-reduced.json")
   cf = cal_dir + cal_file + "-stacked-calparams.json"


   if os.path.exists(cf) is True:
      cal_params= load_json_file(cf)
   else:
      resp = {}
      resp['msg'] = "FAIL CF!" + cf
      return(resp)

   if os.path.exists(mjf) is True:
      mj = load_json_file(mjf)
      ostars = []
      if "cp" in mj:
         if mj['cp'] is not None:
            if "user_stars" in mj['cp']:
               ostars = mj['cp']['user_stars']
   else:
      resp = {}
      resp['msg'] = "FAIL MJF!" + mjf
      return(resp)
   if os.path.exists(mjrf) is True:
      mjr = load_json_file(mjrf)
   else:
      resp = {}
      resp['msg'] = "FAIL MJRF!" + mjrf
      return(resp)

   # Don't forget to update the ra_dec_center
   cp = update_center_radec(meteor_file,cal_params,json_conf)
   cp['user_stars'] =  ostars
   mj['cp'] = cal_params
   mjr['cal_params'] = cal_params
 
   save_json_file(mjf, mj)
   save_json_file(mjrf, mjr)
   #print("Meteor File updated with new calib!")
   if len(ostars) > 5:
      os.system("./recal.py refit_meteor " + meteor_file)
   resp = {}
   resp['msg'] = "ALL GOOD!"
   return(resp)
   # we need to update the az/el meteor frame data with new calparams

def crop_video(in_file, x,y,w,h):
   json_conf = load_json_file("../conf/as6.json")
   in_file = "/mnt/ams2" + in_file
   sf = in_file.replace(".mp4", "-stacked.jpg")
   print ("STACK:", sf)
   #hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(out_file, json_conf, 0, 0, 1, 1,[])
   vw,vh,frames = ffprobe(in_file)
   vw,vh = int(vw),int(vh)
   hdm_x = 960 / int(vw)
   hdm_y = 540/ int(vh)
   nx = int(int(x) / hdm_x)
   ny = int(int(y) / hdm_y)
   nw  = int(int(w)  )
   nh  = int(int(h) )
   print("ORG XY:", x,y)
   print("ORG WH:", w,h)
   print("V WH:", vw, vh )
   print("HDMXY:", hdm_x, hdm_y)
   print("NEW XY:", nx,ny)
   print("NEW WH:", nw,nh)

   if cfe(sf) == 1:
      print("SF", sf)
      img = cv2.imread(sf)
      cv2.rectangle(img, (int(nx), int(ny)), (int(nx+nw) , int(ny+nh) ), (255, 255, 255), 1)
      nf = sf.replace(".jpg", "-test.jpg")
      print("saved", nf)
      #cv2.imwrite(nf, img)

   out_file = in_file.replace(".mp4", "-crop.mp4")
   cmd = "./FFF.py crop_video " + in_file + " " + out_file + " " + str(nx) + "," + str(ny) + "," + str(nw) + "," + str(nh)
   os.system(cmd)
   cv2.waitKey(0)
   if cfe(out_file) == 0:
      # crop failed. 
      resp['status'] = 0
      return resp
   else:
      # crop worked, lets load the crop frames and try to auto detect inside here
      resp = {}
      objects = {}
      resp['status'] = 1
      hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(out_file, json_conf, 0, 0, 1, 1,[])
      fn = 0
      mean_val = np.mean(sum_vals[0:10])
      if mean_val < 50:
         mean_val = 50
      for val in sum_vals:
         print("FN:", fn, mean_val, val,max_vals[fn])
         if val >= mean_val * 2 and max_vals[fn] > 10: 
            x,y = pos_vals[fn]
            x = int(x)
            y = int(y)
            rx1,ry1,rx2,ry2 = bound_cnt(x,y,vw,vh, 10)
            roi_img = hd_frames[fn][ry1:ry2,rx1:rx2]
            adj_x, adj_y = grid_intensity_center(roi_img, 20, fn)
            x = x + adj_x + nx
            y = y + adj_y + ny

            object, objects = find_object(objects, fn,x-5, y-5, 10, 10, sum_vals[fn], 0, 0, None )
            objects[object] = analyze_object(objects[object], 1, 1)

            print( object, fn, val, pos_vals[fn])

         fn += 1

   meteors = []
   for object in objects:
      if objects[object]['report']['meteor'] == 1:
         print("METEOR:",objects[object])
         meteors.append(objects[object])

   if len(meteors) == 0 and len(objects) == 1:
      for obj in objects:
         meteors.append(objects[obj])

   if len(meteors) >= 2:
      merge_x = []
      merge_y = []
      merge_w = []
      merge_h = []
      merge_int = []
      most_frames_obj = 0
      most_frames = 0
      for meteor in meteors:
         ff = len(meteor['ofns'])
         if ff > most_frames:
            most_frames = ff
            bm = meteor
      meteors = []
      meteors.append(bm)
         

   if len(meteors) == 1:
      # the auto detect worked, resave the json file and make a reduced.json, then make the crop frames cache files 

      jsf = in_file.replace(".mp4", ".json")
      best_meteor = meteors[0]
      o_frames,o_color_frames,o_subframes,o_sum_vals,o_max_vals,o_pos_vals = load_frames_fast(in_file, json_conf, 0, 0, 1, 1,[])
      best_meteor, frame_data = fireball_fill_frame_data(in_file,best_meteor, o_frames)
      if cfe(jsf) == 1:
         mj = load_json_file(jsf)
         if "hd_trim" in mj:
            hd_trim = mj['hd_trim']
         else:
            hd_trim = None
         if "cp" in "mj":
            cp = mj['cp']
      else:
         mj = None
         hd_trim = None
         cp = None 
      hd_img = cv2.resize(o_frames[0],(1920,1080))
      cp = calib_image(in_file, hd_img, json_conf)
      if cp is not None:
         best_meteor = apply_calib(in_file, best_meteor, cp, json_conf)

      base_js, base_jsr = make_base_meteor_json(in_file, hd_trim,best_meteor)
      if "user_mods" in mj:
         base_js['user_mods'] = mj['user_mods']

      jsfr = jsf.replace(".json", "-reduced.json")
      base_jsr['cal_params'] = cp
      base_js['cp'] = cp
      base_js['best_meteor'] = best_meteor
      save_json_file(jsf, base_js)
      save_json_file(jsfr, base_jsr)
  
   cmd = "./Process.py roi_mfd " + in_file + " >/mnt/ams2/tmp/api.points 2>&1"
   print(cmd)
   os.system(cmd)


   return(resp)

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


def restore_meteor(jsid, data):
   resp = {}
   json_conf = load_json_file("../conf/as6.json")
   amsid = json_conf['site']['ams_id']
   video_file = jsid + ".mp4"
   json_file = video_file.replace(".mp4", ".json")
   sd_root = jsid
   day = jsid[0:10]
   trash_dir = "/mnt/ams2/trash/" + day + "/" 
   non_meteor_dir = "/mnt/ams2/non_meteors/" + day + "/" 
   meteor_dir = "/mnt/ams2/meteors/" + day + "/" 
   print("JSON FILE IS ", day, json_file)
   print("T", trash_dir + json_file)
   print("NM", non_meteor_dir + json_file)
   if os.path.exists(trash_dir + json_file) is True:
      rest_dir = trash_dir
      rest_file = rest_dir + json_file
   elif os.path.exists(non_meteor_dir + json_file) is True:
      rest_dir = non_meteor_dir
      rest_file = rest_dir + json_file
   else:
      rest_file = None
   print(rest_file)
   mj = load_json_file(rest_file)
   mj['hc'] = 1
   save_json_file(rest_dir + json_file, mj)
   if "hd_trim" in mj:
      hd_root, hd_dir = fn_dir(mj['hd_trim'])
      hd_root = hd_root.replace(".mp4", "")
      hd_cmd = "mv " + rest_dir + hd_root + "* " + meteor_dir
      os.system(hd_cmd)
      print(hd_cmd)
   sd_cmd = "mv " + rest_dir + sd_root + "* " + meteor_dir
   os.system(sd_cmd)
   print(sd_cmd)


   print("RESTORE:", video_file, json_file)
   return("OK" + sd_root + " " + hd_root)

def delete_meteor(jsid, data):
   resp = {}
   print("DELETE:", jsid, data)
   json_conf = load_json_file("../conf/as6.json")
   amsid = json_conf['site']['ams_id']
   video_file = parse_jsid(jsid)
   json_file = video_file.replace(".mp4", ".json")
   trash_file = json_file.replace(".json", ".trash")
   print("VID:", video_file)

   vid_fn = video_file.split("/")[-1]
   date = vid_fn[0:10]
   nmc_dir = "/mnt/ams2/non_meteors_confirmed/" + date + "/"
   if os.path.exists(nmc_dir) is False:
      os.makedirs(nmc_dir)
   # for non meteors copy stack_thumb, stack_file and orig sd_vid
   # for training reasons only
   cmd = "cp " + video_file + " " + nmc_dir
   os.system(cmd)

   cmd = "cp " + video_file.replace(".mp4", "-stacked.jpg") + " " + nmc_dir
   os.system(cmd)

   cmd = "cp " + video_file.replace(".mp4", "-stacked-tn.jpg") + " " + nmc_dir
   os.system(cmd)

   resp['msg'] = "deleted."
   delete_log = "/mnt/ams2/SD/proc2/json/" + amsid + ".del"
   if cfe(delete_log) == 1:
      try:
         del_data = load_json_file(delete_log)
      except:
         del_data = {}
   else:
      del_data = {}
   fn, dir = fn_dir(video_file)
   el = fn.split(".")
   base = el[0]
   del_data[base] = 1

   save_json_file(delete_log, del_data)
   os.system("mv " + json_file + " " + trash_file)

   return resp

def delete_meteors(data):
   resp = {}
   json_conf = load_json_file("../conf/as6.json")
   amsid = json_conf['site']['ams_id']
   detections = data['detections'].split(";")
   delete_log = "/mnt/ams2/SD/proc2/json/" + amsid + ".del"
   if cfe(delete_log) == 1:
      try:
         del_data = load_json_file(delete_log)
      except:
         del_data = {}
         os.system("rm " + delete_log)
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

def parse_meteor_file(filename):
   if "/" in filename:
      fn = filename.split("/")[-1]
   else:
      fn = filename
   date = fn[0:10]
   path = "/mnt/ams2/meteors/" + date + "/" 
   return(path, fn)

def get_med_frame(video_file, mj):
   med_file = video_file.replace(".mp4", "-med.jpg")
   hd_video_file = None
   if mj is not None:
      if "hd_trim" in mj:
         hd_vid = mj['hd_trim']
         if os.path.exists(hd_vid) is True:
            hd_video_file = hd_vid
            print("FOUND HD VID:", hd_vid)
         else: 
            hd_video_file = None 
            print("NOT FOUND HD VID:", hd_vid)

   if cfe(med_file) == 0:
      if hd_video_file is not None:
         print("LOAD HD FRAMES:", hd_video_file)
         hd_frames = load_frames_simple(hd_video_file)
      else:
         print("LOAD SD FRAMES:", hd_video_file)
         hd_frames = load_frames_simple(video_file)

      print("VIDEO FILE:", video_file)

      median_frame = cv2.convertScaleAbs(np.median(np.array(hd_frames), axis=0))
      hd_img = cv2.resize(median_frame,(1920,1080))
      hd_img = cv2.cvtColor(hd_img, cv2.COLOR_BGR2GRAY)

      #median_frame = cv2.GaussianBlur(median_frame, (7, 7), 0)
      print("WROTE MED FILE:", med_file)
      cv2.imwrite(med_file, median_frame)
   else:
      median_frame = cv2.imread(med_file)
      median_frame = cv2.cvtColor(median_frame, cv2.COLOR_BGR2GRAY)
      hd_img = cv2.resize(median_frame,(1920,1080))

   return(hd_img)

def show_cat_stars (video_file, hd_stack_file, points):
   (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(video_file)
   json_conf = load_json_file("../conf/as6.json")
   STATION_ID = json_conf['site']['ams_id']
   cp = None
   if "meteors" in video_file:
      app_type = "meteor"
   else:
      app_type = "calib"
   hd_img = None
   # use the median frame not the stack. 

   vid_path, vid_fn = parse_meteor_file(video_file)


   if app_type == "meteor":
      mjf = "/mnt/ams2/" + video_file.replace(".mp4", ".json")
      stack_file = "/mnt/ams2/" + video_file.replace(".mp4", "-stacked.jpg")
      mjrf = "/mnt/ams2/" + video_file.replace(".mp4", "-reduced.json")
      mj = load_json_file(mjf)

      hd_img = get_med_frame(vid_path + vid_fn, mj)

      if os.path.exists(mjrf) is True:
         mjr = load_json_file(mjrf)
      else: 
         mjr = None

      if "cp" in mj:
         cp = mj['cp']
      elif "best_meteor" in mj:
         if "cp" in mj['best_meteor']:
            mj['cp'] = mj['best_meteor']['cp']
            cp = mj['cp']
      elif mjr is not None: 
         if "cal_params" in mjr:
            cp = mjr['cal_params']
      else:
         print("THERE ARE NO CAL PARAMS!")
         resp = {}
         resp['msg'] = "bad - no cal params!"
         resp['status'] = 0
         return(resp)


      cp = update_center_radec(video_file,cp,json_conf)
      print("UPDATE CP:", video_file)
      print(cp['center_az'])
      print(cp['center_el'])
      print(cp['ra_center'])
      print(cp['dec_center'])
      print(cp['position_angle'])
      print(cp['pixscale'])
      mcp_file = "/mnt/ams2/cal/" + "multi_poly-" + STATION_ID + "-" + cam + ".info" 
      print("MCP:", mcp_file)
      if cfe(mcp_file) == 1:
         mcp = load_json_file(mcp_file)
         cp['x_poly'] = mcp['x_poly']
         cp['y_poly'] = mcp['y_poly']
         cp['x_poly_fwd'] = mcp['x_poly_fwd']
         cp['y_poly_fwd'] = mcp['y_poly_fwd']
         print("LOADED MCP")
      if hd_img is None and "hd_stack" in mj:
         hd_img = cv2.imread(mj['hd_stack'], 0)
         hd_img = cv2.resize(hd_img,(1920,1080))
         print("HD IMG:", mj['hd_stack'])
         print("HD IMG:", hd_img.shape)
      if "short_bright_stars" in cp:
         del (cp['short_bright_stars'])
   else:
      # APP TYPE IS CAL FILE NOT METEOR
      #hd_img = get_med_frame(video_file, None)
      cal_r = video_file.replace("-half-stack.png", "")
      cal_root = "/mnt/ams2" + cal_r 
      cps = glob.glob(cal_root + "*calparams.json")
      sfs = glob.glob(cal_root + "*stacked.png")
      if len(sfs) == 0:
         ttt = cal_root + ".png"
         if cfe(ttt) == 1:
            sfs.append(ttt)
         else:
            return("Problem can't find cal file")
      print("GLOB:" + cal_root + "*stacked.png")
      stack_file = sfs[0]
      cpf = cps[0]
      cp = load_json_file(cpf)
      if hd_img is None:
         hd_img = cv2.imread(stack_file, 0)
         hd_img = cv2.resize(hd_img,(1920,1080))
   
   if hd_img is None:
      hd_img = cv2.imread(stack_file, 0)
      hd_img = cv2.resize(hd_img,(1920,1080))

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
      #show_img = hd_img.copy()
      #cv2.rectangle(show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (255, 255, 255), 1)

      #print("HD IMG", hd_img.shape)
      cnt_img = hd_img[ry1:ry2, rx1:rx2]
      #cv2.imwrite("/mnt/ams2/test.jpg", cnt_img)
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

   print("1", video_file )
   # BUG HERE WITH CAL FILES
   cp = pair_stars(cp, video_file, json_conf, hd_img)
   print("2")
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
      print("SHOW CAT SAVE", mjf, mjrf)
      resp['crop_box'] = mjr['crop_box']
   else:
      resp['crop_box'] = [0,0,0,0]
      if "user_mods" not in cp:
         cp['user_mods'] = {}
      cp['user_mods']['user_stars'] = cp['user_stars']
      save_json_file(cpf, cp)
      print("SHOW CAT SAVE", cpf)

   resp['msg'] = "good"
   resp['status'] = 1
   resp['cp'] = cp
   print("RESP:", resp)
   return(resp)


def update_meteor_points(sd_video_file,frames):
   json_conf = load_json_file("../conf/as6.json")
   json_file = "/mnt/ams2/" + sd_video_file.replace(".mp4", ".json")
   full_vid = "/mnt/ams2/" + sd_video_file

   rjson_file = json_file.replace(".json", "-reduced.json")
 
   mj = load_json_file(json_file)
   if "user_mods" in  mj:
      user_mods = mj['user_mods']
   else:
      user_mods = {}
   if "frames" not in user_mods:
      user_mods['frames'] = {}
   edits = {}
   for row in frames:
 
      fn = row['fn']
      x = row['x']
      y = row['y']
      user_mods['frames'][fn] = [x,y]
      edits[fn] = [x,y]
   mj['user_mods'] = user_mods
   save_json_file(json_file, mj)
   resp = {
      "msg": "frames updated." 
   }
   #cmd = "./Process.py roi_mfd /mnt/ams2/" + sd_video_file + " >/mnt/ams2/tmp/api.points 2>&1"
   #print("COMMAND:", cmd)
   #os.system(cmd)
   make_roi_video_mfd("/mnt/ams2/" + sd_video_file, json_conf, edits)
   print("_________________________________________________DONE MAKE ROI VIDEO MFD__________________")
   #cmd = "./Learn.py add " + json_file + " >/mnt/ams2/tmp/api.points 2>&1 &"
   #print("COMMAND:", cmd)
   #os.system(cmd)

   mjr = load_json_file(rjson_file)
   resp['status'] = 1
   if "cal_params" in mj:
      resp['calib'] = mj['cal_params']
   if "cp" in mj:
      if "total_res_deg" in mj['cp'] :
         del(mj['cp']['total_res_deg'])
      resp['calib'] = mj['cp']
   if "meteor_frame_data" in mj:
      resp['frames'] = mjr['meteor_frame_data']
   vid_fn = json_file.split("/")[-1]
   vid_fn = vid_fn.replace(".json", ".mp4")
   #cmd = "./DynamoDB.py update_obs " + vid_fn + " >/mnt/ams2/tmp/api.points 2>&1 &"
   #print("COMMAND:", cmd)
   #os.system(cmd)
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
   

