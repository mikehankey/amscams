"""


   Library for holding scan and stack data processing functions.
   These are the functions used to 'process' incoming video files. 
   Steps in pipe line processing are:
      - scan file and make subframes and then calculate the sum, max vals and max positions for each frame
      - save data in -vals.json
      - make stack file with remaining data 
   Works day and night
   Reads files in : /mnt/ams2/SD
   Puts files in : /mnt/ams2/SD/proc2 when done. 
   Creates -meteor.json files in the proc2/YYYY_MM_DD/data dir

   scan_and_stack -- is just for making the files
   process_meteors -- finishes the meteors, finds the HD and saves the meteor in old and new dirs.

"""

import datetime
import cv2
from PIL import ImageFont, ImageDraw, Image, ImageChops
import numpy as np
import ephem

from lib.VideoLib import get_masks

def find_best_cat_stars(cat_stars, ix,iy, frame, cp_file):
   cx1,cy1,cx2,cy2 = bound_cnt(ix,iy,frame.shape[1],frame.shape[0], 5)
   intensity = int(np.sum(frame[cy1:cy2,cx1:cx2]))
   min_dist = 999
   min_star = None
   for cat_star in cat_stars:
      name,mag,ra,dec,new_cat_x,new_cat_y = cat_star

      dist = calc_dist((new_cat_x, new_cat_y), (ix,iy))
      if dist < min_dist and mag < 4:
         #print("DIST:", dist, cat_star)
         min_dist = dist
         min_star = cat_star
   name,mag,ra,dec,new_cat_x,new_cat_y = min_star
   px_dist = 0
   #cat_image_star = ((name.decode("unicode_escape"),mag,ra,dec,new_cat_x,new_cat_y,ix,iy,intensity,min_dist,cp_file))
   cat_image_star = ((name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,intensity,min_dist,cp_file))
   return(cat_image_star)


def day_or_night(capture_date, json_conf):

   device_lat = json_conf['site']['device_lat']
   device_lng = json_conf['site']['device_lng']

   obs = ephem.Observer()

   obs.pressure = 0
   obs.horizon = '-0:34'
   obs.lat = device_lat
   obs.lon = device_lng
   obs.date = capture_date

   sun = ephem.Sun()
   sun.compute(obs)

   (sun_alt, x,y) = str(sun.alt).split(":")

   saz = str(sun.az)
   (sun_az, x,y) = saz.split(":")
   if int(sun_alt) < -1:
      sun_status = "night"
   else:
      sun_status = "day"
   return(sun_status)


def convert_filename_to_date_cam(file):
   el = file.split("/")
   filename = el[-1]
   if "trim" in filename:
      filename, xxx = filename.split("-")[:2]
   filename = filename.replace(".mp4" ,"")

   data = filename.split("_")
   fy,fm,fd,fh,fmin,fs,fms,cam = data[:8]
   f_date_str = fy + "-" + fm + "-" + fd + " " + fh + ":" + fmin + ":" + fs
   f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
   return(f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs)


def analyze_object(object, hd = 0, sd_multi = 1, final=0):
   # HD scale pix is .072 degrees per px
   # SD scale pix is .072 * sd_multi
   pix_scale = .072  # for HD

   if hd == 1:
      deg_multi = 1
      sd = 0
   else:
      deg_multi = 3
      sd = 1

   bad_items = []
   perc_big = big_cnt_test(object, hd)
   if "ofns" not in object:
      if "report" not in object:
         object['report'] = {}
         object['report']['meteor_yn'] = "no"
      else:
         object['report']['meteor_yn'] = "no"
      return(object)
   if len(object['ofns']) == 0:
      if "report" not in object:
         object['report'] = {}
         object['report']['meteor_yn'] = "no"
      else:
         object['report']['meteor_yn'] = "no"
      return(object)

   object = calc_leg_segs(object)
   unq_perc = unq_points(object)

   if len(object['ofns']) > 4:
      dir_test_perc = meteor_dir_test(object['oxs'],object['oys'])
   else:
      dir_test_perc = 0


   id = object['obj_id']
   meteor_yn = "Y"
   obj_class = "undefined"
   ff = object['ofns'][0]
   lf = object['ofns'][-1]
   elp = (lf - ff ) + 1
   min_x = min(object['oxs'])
   max_x = max(object['oxs'])
   min_y = min(object['oys'])
   max_y = max(object['oys'])
   max_int = max(object['oint'])
   min_int = min(object['oint'])
   max_h = max(object['ohs'])
   max_w = max(object['ows'])
   #max_x = max_x + max_w
   #max_h = max_y + max_h

   int_max_times, int_neg_perc, int_perc_list = anal_int(object['oint'])

   med_int = float(np.median(object['oint']))
   intense_neg = 0
   for intense in object['oint']:
      if intense < 0:
         intense_neg = intense_neg + 1
   min_max_dist = calc_dist((min_x, min_y), (max_x,max_y))
   if len(object['ofns']) > 0:
      if final == 0:

         dist_per_elp = min_max_dist / len(object['ofns'])
      else:
         if elp > 0:
            dist_per_elp = min_max_dist / elp
         else:
            dist_per_elp = 0
   else:
      dist_per_elp = 0

   if len(object['ofns']) > 3 and perc_big >= .75 and len(object['ofns']) < 10:
      moving = "moving"
      meteor_yn = "no"
      obj_class = "car or object"
      bad_items.append("too many big percs")

   if elp > 5 and dist_per_elp < .1 :
      moving = "not moving"
      meteor_yn = "no"
      obj_class = "star"
      bad_items.append("too short and too slow")
   else:
      moving = "moving"
   if min_max_dist > 12 and dist_per_elp < .1:
      moving = "slow moving"
      meteor_yn = "no"
      obj_class = "plane"
      bad_items.append("too long and too slow")

   #cm
   fc = 0
   cm = 1
   max_cm = 1
   last_fn = None
   for fn in object['ofns']:
      if last_fn is not None:
         if last_fn + 1 == fn or last_fn + 2 == fn:
            cm = cm + 1
            if cm > max_cm :
               max_cm = cm

      fc = fc + 1
      last_fn = fn
   if len(object['ofns']) > 1:
      x_dir_mod,y_dir_mod = meteor_dir(object['oxs'][0], object['oys'][0], object['oxs'][-1], object['oys'][-1])
   else:
      x_dir_mod = 0
      y_dir_mod = 0

   if len(object['ofns'])> 0:
      cm_to_len = max_cm / len(object['ofns'])
   else:
      meteor_yn = "no"
      obj_class = "plane"
      bad_items.append("0 frames")
   if cm_to_len < .4:
      meteor_yn = "no"
      obj_class = "plane"
      bad_items.append("cm/len < .4.")

   if len(object['ofns']) >= 300:
      # if cm_to_len is acceptable then skip this.
      if cm_to_len < .6:
         meteor_yn = "no"
         obj_class = "plane"
         bad_items.append("more than 300 frames in event and cm/len < .6.")



   # classify the object

   if max_cm <= 3 and elp > 5 and min_max_dist < 8 and dist_per_elp < .01:
      obj_class = "star"
   if elp > 5 and min_max_dist > 8 and dist_per_elp >= .01 and dist_per_elp < 1:
      obj_class = "plane"
   if elp > 300:
      meteor_yn = "no"
      bad_items.append("more than 300 frames in event.")
   if max_cm < 4:
      neg_perc = intense_neg / max_cm
      if intense_neg / max_cm > .3:
         meteor_yn = "no"
         bad_items.append("too much negative intensity for short event." + str(intense_neg))

   if max_cm > 0:
      neg_perc = intense_neg / max_cm
      if intense_neg / max_cm > .5:
         meteor_yn = "no"
         bad_items.append("too much negative intensity." + str(intense_neg))
   else:
      neg_perc = 0
   if elp < 2:
      meteor_yn = "no"
      bad_items.append("less than 2 frames in event.")
   if perc_big > .75 and len(object['ofns']) < 10:
      meteor_yn = "no"
      bad_items.append("too many big cnts." + str(perc_big))
   if max_cm < 3:
      meteor_yn = "no"
      bad_items.append("less than 2 consecutive motion.")
   if dist_per_elp > 5:
      meteor_yn = "Y"
   if med_int < 5 and med_int != 0:
      meteor_yn = "no"
      obj_class = "bird"
      bad_items.append("low or negative median intensity.")
   if dir_test_perc < .5 and dir_test_perc != 0 and elp > 10:
      #meteor_yn = "no"
      #obj_class = "noise"
      bad_items.append("direction test failed." + str(dir_test_perc))
   if unq_perc < .5:
      meteor_yn = "no"
      obj_class = "star or plane"
      bad_items.append("unique points test failed." + str(unq_perc))

   if max_cm > 0:
      elp_max_cm = elp / max_cm
      if elp / max_cm >3:
         obj_class = "plane"
         meteor_yn = "no"
         bad_items.append("elp to cm to high." + str(elp / max_cm))
   else:
      elp_max_cm = 0
   ang_vel = ((dist_per_elp * deg_multi) * pix_scale) * 25
   ang_dist = ((min_max_dist * deg_multi) * pix_scale)

   if ang_dist < .2:
      meteor_yn = "no"
      bad_items.append("bad angular distance below .2.")
   if ang_vel < .9:
      meteor_yn = "no"
      bad_items.append("bad angular velocity below .9")

   #YOYO
   if dir_test_perc < .6 and max_cm > 10:
      meteor_yn = "no"
      obj_class = "star"
      bad_items.append("dir test perc to low for this cm")

   if max_cm < 5 and elp_max_cm > 1.5 and neg_perc > 0:
      meteor_yn = "no"
      obj_class = "plane"
      bad_items.append("low max cm, high neg_perc, high elp_max_cm")

   if ang_vel < 1.5 and elp_max_cm > 2 and cm < 3:
      meteor_yn = "no"
      bad_items.append("short distance, many gaps, low cm")
      obj_class = "plane"


   if elp > 0:
      if min_max_dist * deg_multi < 1 and max_cm <= 3 and cm / elp < .75 :
         meteor_yn = "no"
         bad_items.append("short distance, many gaps, low cm")

   if meteor_yn == "Y" and final == 1:
      if max_cm - elp < -30:
         meteor_yn = "no"
         obj_class = "plane"
         bad_items.append("to many elp frames compared to cm.")


   if len(bad_items) >= 1:
      meteor_yn = "no"
      if obj_class == 'meteor':
         obj_class = "not sure"

   if meteor_yn == "no":
      meteory_yn = "no"
   else:
      meteory_yn = "Y"
      obj_class = "meteor"


   # create meteor 'like' score
   score = 0
   if meteor_yn == "Y":
      avg_line_res = poly_fit(object)
   else:
      avg_line_res = 0

   if avg_line_res > 13:
      meteor_yn = "no"
      obj_class = "noise"
      bad_items.append("bad average line res " + str(avg_line_res))

   if max_cm == elp == len(object['ofns']):
      score = score + 1
   if dir_test_perc == 2:
      score = score + 1
   if max_cm >= 5:
      score = score + 1
   if avg_line_res <= 1:
      score = score + 1
   if ang_vel > 2:
      score = score + 1
   if obj_class == "meteor":
      score = score + 5
   else:
      score = score - 3

   object['report'] = {}

   if meteor_yn == "Y":
      print("CLASSIFY HD/SD (HD should be 0):", sd)
      class_rpt = classify_object(object, sd)
      object['report']['classify'] = class_rpt
      object['report']['meteor_yn'] = meteor_yn

      #object['report']['angular_sep_px'] = class_rpt['ang_sep_px']
      #object['report']['angular_vel_px'] = class_rpt['ang_vel_px']
      #object['report']['angular_sep'] = class_rpt['ang_sep_deg']
      #object['report']['angular_vel'] = class_rpt['ang_vel_deg']
      #object['report']['segs'] = class_rpt['segs']
      #object['report']['bad_seg_perc'] = class_rpt['bad_seg_perc']
      #object['report']['neg_int_perc'] = class_rpt['neg_int_perc']
      #object['report']['meteor_yn'] = class_rpt['meteor_yn']
      #object['report']['bad_items'] = class_rpt['bad_items']
   else:
      object['report']['meteor_yn'] = meteor_yn

   object['report']['elp'] = elp
   object['report']['min_max_dist'] = min_max_dist
   object['report']['dist_per_elp'] = dist_per_elp
   object['report']['moving'] = moving
   object['report']['dir_test_perc'] = dir_test_perc
   object['report']['max_cm'] = max_cm
   object['report']['elp_max_cm'] = elp_max_cm
   object['report']['max_fns'] = len(object['ofns'])
   object['report']['neg_perc'] = neg_perc
   object['report']['avg_line_res'] = avg_line_res
   object['report']['obj_class'] = obj_class
   object['report']['bad_items'] = bad_items
   object['report']['x_dir_mod'] = x_dir_mod
   object['report']['y_dir_mod'] = y_dir_mod
   object['report']['score'] = score

   return(object)





def find_object(objects, fn, cnt_x, cnt_y, cnt_w, cnt_h, intensity=0, hd=0, sd_multi=1, cnt_img=None):
   #if fn < 5:
   #   return(0, objects)
   if hd == 1:
      obj_dist_thresh = 20
   else:
      obj_dist_thresh = 10

   center_x = cnt_x
   center_y = cnt_y

   found = 0
   max_obj = 0
   for obj in objects:
      if 'oxs' in objects[obj]:
         ofns = objects[obj]['ofns']
         oxs = objects[obj]['oxs']
         oys = objects[obj]['oys']
         ows = objects[obj]['ows']
         ohs = objects[obj]['ohs']
         for oi in range(0, len(oxs)):
            hm = int(ohs[oi] / 2)
            wm = int(ows[oi] / 2)
            lfn = int(ofns[-1] )
            dist = calc_obj_dist((cnt_x,cnt_y,cnt_w,cnt_h),(oxs[oi], oys[oi], ows[oi], ohs[oi]))

            last_frame_diff = fn - lfn
            if dist < obj_dist_thresh and last_frame_diff < 10:
               found = 1
               found_obj = obj
      if obj > max_obj:
         max_obj = obj
   if found == 0:
      obj_id = max_obj + 1
      objects[obj_id] = {}
      objects[obj_id]['obj_id'] = obj_id
      objects[obj_id]['ofns'] = []
      objects[obj_id]['oxs'] = []
      objects[obj_id]['oys'] = []
      objects[obj_id]['ows'] = []
      objects[obj_id]['ohs'] = []
      objects[obj_id]['oint'] = []
      objects[obj_id]['ofns'].append(fn)
      objects[obj_id]['oxs'].append(center_x)
      objects[obj_id]['oys'].append(center_y)
      objects[obj_id]['ows'].append(cnt_w)
      objects[obj_id]['ohs'].append(cnt_h)
      objects[obj_id]['oint'].append(intensity)
      found_obj = obj_id
   if found == 1:
      if objects[found_obj]['report']['obj_class'] == "meteor":
         # only add if the intensity is positive and the forward motion compared to the last highest FM is greater.
         fm_last = calc_dist((objects[found_obj]['oxs'][0],objects[found_obj]['oys'][0]), (objects[found_obj]['oxs'][-1],objects[found_obj]['oys'][-1]))
         fm_this = calc_dist((objects[found_obj]['oxs'][0],objects[found_obj]['oys'][0]), (center_x, center_y))
         fm = fm_this - fm_last
         if intensity > 10 and fm > 0:
            objects[found_obj]['ofns'].append(fn)
            objects[found_obj]['oxs'].append(center_x)
            objects[found_obj]['oys'].append(center_y)
            objects[found_obj]['ows'].append(cnt_w)
            objects[found_obj]['ohs'].append(cnt_h)
            objects[found_obj]['oint'].append(intensity)

      else:
         objects[found_obj]['ofns'].append(fn)
         objects[found_obj]['oxs'].append(center_x)
         objects[found_obj]['oys'].append(center_y)
         objects[found_obj]['ows'].append(cnt_w)
         objects[found_obj]['ohs'].append(cnt_h)
         objects[found_obj]['oint'].append(intensity)

   objects[found_obj] = analyze_object(objects[found_obj], hd, sd_multi, 1)
   if objects[found_obj]['report']['meteor_yn'] == 'Y':
      max_int = max(objects[found_obj]['oint'])
      if max_int > 25000:
         objects[found_obj]['report']['obj_class'] = "fireball"

   return(found_obj, objects)




def detect_in_vals(vals_file):
   video_file = vals_file.replace("-vals.json", ".mp4")
   data = load_json_file(vals_file)
   events = []
   data_x = []
   data_y = []
   cm =0
   last_i = None
   objects = {}
   for i in range(0,len(data['max_vals'])):
      x,y = data['pos_vals'][i]
      max_val = data['max_vals'][i]
      if max_val > 10:
         if last_i is not None and  last_i + 1 == i:
            cm += 1
         else:
            cm = 0
         data_x.append(x)
         data_y.append(y)
         print(i, x,y, max_val, cm)
         object, objects = find_object(objects, i,0, 0, SD_W, SD_H, 0, 0, 0, None)
      else:
         if cm >= 3:
            e_end = i
            e_start = i - cm
            #e_start -= 5
            #e_end += 5
            event = {}
            event['frames'] = [e_start,e_end]
            event['pos_vals'] = data['pos_vals'][e_start:e_end]
            event['max_vals'] = data['max_vals'][e_start:e_end]
            event['sum_vals'] = data['sum_vals'][e_start:e_end]
            events.append(event)
         cm = 0
      last_i = i

   for ev in events:
      print(ev)
   for obj in objects:
      print(obj, objects[obj]['ofns'], objects[obj]['report']['meteor_yn'], objects[obj]['report']['bad_items']  )

   # find the HD and trim & crop the clips
   #events = process_events(video_file,events)
   exit()
   # find the objects in each cropped clip
   for ev in events:
      print(ev)
      sd_trim,sd_crop,hd_trim,hd_crop,crop_info = ev['event_files']
      hd_motion_objects,hd_meteor_frames = detect_meteor_in_clip(hd_crop, None, 0,crop_info[0],crop_info[1], 1)
      sd_motion_objects,sd_meteor_frames = detect_meteor_in_clip(sd_trim, None, 0,0,0,0)
      print("EVENT FRAMES: ", ev['frames'])
      print("HD MOTION OBJECTS:", len(sd_motion_objects))
      for id in hd_motion_objects:
         obj = hd_motion_objects[id]
         if obj['report']['meteor_yn'] == 'Y':
            print(obj['ofns'])
            print(obj['report'])
            print("EV:", ev['event_files'])

      print("SD MOTION OBJECTS:", len(sd_motion_objects))
      for id in sd_motion_objects:
         obj = sd_motion_objects[id]
         if obj['report']['meteor_yn'] == 'Y':
            print(obj['ofns'])
            print(obj['report'])
            print("EV:", ev['event_files'])

   return()

def stack_stack(pic1, pic2):
   stacked_image=ImageChops.lighter(pic1,pic2)
   return(stacked_image)


def stack_frames_fast(frames, skip = 1, resize=None, sun_status="night", sum_vals=[]):
   if sum_vals is None:
      sum_vals= [1] * len(frames)
   stacked_image = None
   fc = 0
   for frame in frames:
      if (sun_status == 'night' and sum_vals[fc] > 0) or sun_status == 'day' or fc < 10:
         if resize is not None:
            frame = cv2.resize(frame, (resize[0],resize[1]))
         if fc % skip == 0:
            frame_pil = Image.fromarray(frame)
            if stacked_image is None:
               stacked_image = stack_stack(frame_pil, frame_pil)
            else:
               stacked_image = stack_stack(stacked_image, frame_pil)
      fc = fc + 1
   return(np.asarray(stacked_image))


def load_frames_fast(trim_file, json_conf, limit=0, mask=0,crop=(),color=0,resize=[], sun_status="night"):
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(trim_file)
   cap = cv2.VideoCapture(trim_file)

   if "HD" in trim_file:
      masks = get_masks(cam, json_conf,1)
   else:
      masks = get_masks(cam, json_conf,1)
   if "crop" in trim_file:
      masks = None

   color_frames = []
   frames = []
   subframes = []
   sum_vals = []
   pos_vals = []
   max_vals = []
   frame_count = 0
   last_frame = None
   go = 1
   while go == 1:
      if True :
         _ , frame = cap.read()
         if frame is None:
            if frame_count <= 5 :
               cap.release()
               return(frames,color_frames,subframes,sum_vals,max_vals,pos_vals)
            else:
               go = 0
         else:
            if color == 1:
               if sun_status == "day" and frame_count % 25 == 0:
                  color_frames.append(frame)
               else:
                  color_frames.append(frame)
            if limit != 0 and frame_count > limit:
               cap.release()
               return(frames,color_frames,subframes,sum_vals,max_vals,pos_vals)
            if len(resize) == 2:
               frame = cv2.resize(frame, (resize[0],resize[1]))

            if sun_status == "night":
               frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
               if mask == 1 and frame is not None:
                  if frame.shape[0] == 1080:
                     hd = 1
                  else:
                     hd = 0
                  masks = get_masks(cam, json_conf,hd)
                  frame = mask_frame(frame, [], masks, 5)

               if last_frame is not None:
                  if frame_count > 5:
                     last_frame = frames[-5]
                  subframe = cv2.subtract(frame, last_frame)
                  sum_val =cv2.sumElems(subframe)[0]

                  if sum_val > 10 :
                     _, thresh_frame = cv2.threshold(subframe, 15, 255, cv2.THRESH_BINARY)

                     sum_val =cv2.sumElems(thresh_frame)[0]
                  else: 
                     sum_val = 0
                  subframes.append(subframe)


                  if sum_val > 10:
                     min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(subframe)
                  else:
                     max_val = 0
                     mx = 0
                     my = 0
                  if frame_count < 5:
                     sum_val = 0
                     max_val = 0
                  sum_vals.append(sum_val)
                  max_vals.append(max_val)
                  pos_vals.append((mx,my))
               else:
                  blank_image = np.zeros((frame.shape[0] ,frame.shape[1]),dtype=np.uint8)
                  subframes.append(blank_image)
                  sum_val = 0
                  sum_vals.append(0)
                  max_vals.append(0)
                  pos_vals.append(0)

            frames.append(frame)
            last_frame = frame
      frame_count = frame_count + 1
   cap.release()
   return(frames, color_frames, subframes, sum_vals, max_vals,pos_vals)

