''' 

   Pipeline Detection Routines

'''
import glob
from datetime import datetime as dt
import datetime
#import math
import os
from lib.PipeVideo import ffmpeg_splice, find_hd_file, load_frames_fast, find_crop_size, ffprobe
from lib.PipeUtil import load_json_file, save_json_file, cfe, get_masks, convert_filename_to_date_cam, buffered_start_end, get_masks, compute_intensity , bound_cnt
from lib.DEFAULTS import *
from lib.PipeMeteorTests import big_cnt_test, calc_line_segments, calc_dist, unq_points, analyze_intensity, calc_obj_dist, meteor_direction, meteor_direction_test, check_pt_in_mask, filter_bad_objects, obj_cm, meteor_dir_test, ang_dist_vel

import numpy as np
import cv2

json_conf = load_json_file(AMS_HOME + "/conf/as6.json")

def objects_to_clips(meteor_objects):
   clips = []
   good_objs = []
   for obj in meteor_objects:
      if len(obj['ofns']) > 2:
         ok = 1
         for clip in clips:
            if abs(obj['ofns'][0] - clip) < 25:
               ok = 0
         if ok == 1:
            clips.append(obj['ofns'][0])
            good_objs.append(obj)

   return(good_objs)


def clean_bad_frames(object):
   #print("CLEAN BEFORE:", object)
   if len(object['ofns']) < 5:
      return(object)
   bad_frames = {} 
   for i in range(0,len(object['ofns'])-1):
      last_i = len(object['ofns']) - 1 - i
      if i < 4:
         if object['report']['line_segments'][last_i] <= 0 :
            bad_frames[last_i] = 1
         if object['oint'][last_i] < 10:
            bad_frames[last_i] = 1

   #print("BAD FRAMES:", bad_frames)
   # check for a gap at the from 
   first_frame_diff = object['ofns'][1] - object['ofns'][0]
   if False:
      if first_frame_diff > 1:
         # REMOVE FIRST FRAME 
         bf = 0
         object['ofns'].pop(bf)
         object['oxs'].pop(bf)
         object['oys'].pop(bf)
         object['ows'].pop(bf)
         object['ohs'].pop(bf)
         object['oint'].pop(bf)
         object['report']['object_px_length'].pop(bf)
         object['report']['line_segments'].pop(bf)
         object['report']['x_segs'].pop(bf)
         object['report']['ms'].pop(bf)
         object['report']['bs'].pop(bf)


   no = {}
   if len(bad_frames) == 0:
      return(object)
   if len(bad_frames) > 0:
      no['ofns'] = []
      no['oxs'] = []
      no['oys'] = []
      no['ows'] = []
      no['ohs'] = []
      no['oint'] = []
      no['report'] = {}
      no['report']['object_px_length'] = []
      no['report']['line_segments'] = []
      no['report']['x_segs'] = []
      no['report']['ms'] = []
      no['report']['bs'] = []
   for i in range(0, len(object['ofns'])):
      if i < min(bad_frames.keys()):
         #print("ADD GOOD FRAME.", i, object['ofns'][i])
         no['ofns'].append(object['ofns'][i])
         no['oxs'].append(object['oxs'][i])
         no['oys'].append(object['oys'][i])
         no['ows'].append(object['ows'][i])
         no['ohs'].append(object['ohs'][i])
         no['oint'].append(object['oint'][i])
         no['report']['object_px_length'].append(object['report']['object_px_length'][i])
         no['report']['line_segments'].append(object['report']['line_segments'][i])
         no['report']['x_segs'].append(object['report']['x_segs'][i])
         no['report']['ms'].append(object['report']['ms'][i])
         no['report']['bs'].append(object['report']['bs'][i])
   if len(bad_frames) > 0:
      o = object 
      o['ofns'] =  no['ofns']
      o['oxs'] =    no['oxs']
      o['oys'] =   no['oys']
      o['ows'] =   no['ows']
      o['ohs'] =   no['ohs']
      o['oint'] =  no['oint']
      o['report']['object_px_length'] =      no['report']['object_px_length']
      o['report']['line_segments'] =    no['report']['line_segments']
      o['report']['x_segs'] =  no['report']['x_segs']
      o['report']['ms'] =  no['report']['ms']
      o['report']['bs'] =  no['report']['bs']
      object = o


   #print("CLEAN AFTER:", object)
   #print("NEW OBJ :", no)
   return(object) 


def analyze_object(object, hd = 0, strict = 0):
   ''' 
      perform various tests to classify the type of object
      when strict == 1 perform more meteor strict tests
   '''


   if hd == 0:
      # if we are working with an HD file we need to mute the HD Multipliers
      global HDM_X, HDM_Y
      HDM_X = 1
      HDM_Y = 1

   bad_items = []
   good_items = []

   if "report" not in object:
      object['report'] = {}
      object['report']['non_meteor'] = 0
      object['report']['meteor'] = 0
      object['report']['bad_items'] = []


   # basic initial tests for vals-detect/stict = 0, if these all pass the clip should be video detected
   object['report']['cm'] = obj_cm(object['ofns'])
   # consecutive motion filter 
   if object['report']['cm'] < 3:
      object['report']['non_meteor'] = 1

   object['report']['unq_perc'], object['report']['unq_points'] = unq_points(object)
   if object['report']['unq_points']  < 2 or object['report']['unq_perc'] < .5:
      object['report']['non_meteor'] = 1
      object['report']['bad_items'].append("Unq Points/Perc too low. " + str(object['report']['unq_points']) + " / " + str(object['report']['unq_perc']) )

   object['report']['object_px_length'], object['report']['line_segments'], object['report']['x_segs'], object['report']['ms'], object['report']['bs'] = calc_line_segments(object)

   object['report']['min_max_dist'] = calc_dist((min(object['oxs']), min(object['oys'])), (max(object['oxs']),max(object['oys']) ))

   object = clean_bad_frames(object)


   # ANG DIST / VEL
   # HD PXSCALE = 155 arcseconds per pixel 
   hd_pxscale = 155
   pxscale = 155
   if hd == 0:
      sd_pxscale = hd_pxscale * (2.25)
      pxscale = sd_pxscale

   if object['report']['non_meteor'] == 0:
      ang_dist, ang_vel = ang_dist_vel(object['oxs'],object['oys'], [],[],pxscale)
      object['report']['ang_dist'] = ang_dist
      object['report']['ang_vel'] = ang_vel

      # filter out detections that don't match ang vel or ang sep desired values
      if float(ang_vel) > .5 and float(ang_vel) < 80:
         foo = 1
      else:
         object['report']['non_meteor'] = 1
         object['report']['bad_items'].append("bad ang vel: " + str(ang_vel))

      if ang_dist < .3:
         object['report']['non_meteor'] = 1
         object['report']['bad_items'].append("bad ang sep: " + str(ang_dist))

   if object['report']['non_meteor'] == 1 :
      return(object)

   if strict == 0:
      #print("INITIAL METEOR DETECTED!")
      if object['report']['non_meteor'] == 0 :
         object['report']['meteor'] = 1 
      return(object)
 
   print("************STRICT*************") 

   # more tests for video based detection 

   # big cnt perc test
   object['report']['big_perc'] = big_cnt_test(object, hd)
   if object['report']['big_perc'] > .5:
      object['report']['non_meteor'] = 1
      object['report']['bad_items'].append("Big Perc % too high. " + str(object['report']['big_perc']))

   # meteor dir tests
   if len(object['ofns']) > 4:
      object['report']['dir_test_perc'] = meteor_dir_test(object['oxs'],object['oys'])
   else:
      object['report']['dir_test_perc'] = 1

   # NOT SURE THIS WORKS?!
   if object['report']['dir_test_perc'] < .80:
      object['report']['non_meteor'] = 0
      object['report']['bad_items'].append("% direction too low. " + str(object['report']['dir_test_perc']))

   # intensity
   if sum(object['oint']) < 0:
      object['report']['non_meteor'] = 1
      object['report']['bad_items'].append("Negative intensity, possible bird. ")
    
                                         
   (max_times, pos_neg_perc, perc_val) = analyze_intensity(object['oint'])
   object['report']['int_pos_neg_perc'] = pos_neg_perc
   object['report']['int_max_times'] = max_times
   object['report']['pos_perc'] = perc_val
   if pos_neg_perc < .5:
      object['report']['non_meteor'] = 1
      object['report']['bad_items'].append("% pos/neg intensity too low. " + str(object['report']['int_pos_neg_perc']))


   if object['report']['non_meteor'] == 0:
      print("*********** METEOR DETECTED *********")
      object['report']['meteor'] = 1

   print("END ANAL")   
   return(object)    

def analyze_object_old(object, hd = 0, sd_multi = 1, final=0):
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
      dir_test_perc = meteor_direction_test(object['oxs'],object['oys'])
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

   int_max_times, int_neg_perc, int_perc_list = analyze_intensity(object['oint'])

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
      x_dir_mod,y_dir_mod = meteor_direction(object['oxs'][0], object['oys'][0], object['oxs'][-1], object['oys'][-1])
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




def find_object(objects, fn, cnt_x, cnt_y, cnt_w, cnt_h, intensity=0, hd=0, sd_multi=1, cnt_img=None ):

   if hd == 1:
      obj_dist_thresh = 100
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
      #if objects[found_obj]['report']['obj_class'] == "meteor":
      #if True:
      #   # only add if the intensity is positive and the forward motion compared to the last highest FM is greater.
      #   fm_last = calc_dist((objects[found_obj]['oxs'][0],objects[found_obj]['oys'][0]), (objects[found_obj]['oxs'][-1],objects[found_obj]['oys'][-1]))
      #   fm_this = calc_dist((objects[found_obj]['oxs'][0],objects[found_obj]['oys'][0]), (center_x, center_y))
      #   fm = fm_this - fm_last
      #   if intensity > 10 and fm > 0:
      #      objects[found_obj]['ofns'].append(fn)
      #      objects[found_obj]['oxs'].append(center_x)
      #      objects[found_obj]['oys'].append(center_y)
      #      objects[found_obj]['ows'].append(cnt_w)
      #      objects[found_obj]['ohs'].append(cnt_h)
      #      objects[found_obj]['oint'].append(intensity)

      #else:
         objects[found_obj]['ofns'].append(fn)
         objects[found_obj]['oxs'].append(center_x)
         objects[found_obj]['oys'].append(center_y)
         objects[found_obj]['ows'].append(cnt_w)
         objects[found_obj]['ohs'].append(cnt_h)
         objects[found_obj]['oint'].append(intensity)

   #objects[found_obj] = analyze_object_old(objects[found_obj], hd, sd_multi, 1)
   #if objects[found_obj]['report']['meteor_yn'] == 'Y':
   #   max_int = max(objects[found_obj]['oint'])
   #   if max_int > 25000:
   #      objects[found_obj]['report']['obj_class'] = "fireball"

   return(found_obj, objects)



def detect_in_vals(vals_file, masks=None, vals_data=None):

   (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(vals_file)

   if masks is None:
      masks = get_masks(cam, json_conf,0)
 
   video_file = vals_file.replace("-vals.json", ".mp4")
   video_file = video_file.replace("data/", "")
   if vals_data is None:
      data = load_json_file(vals_file)
   else:
      data = vals_data
   events = []
   data_x = []
   data_y = []
   cm =0
   last_i = None
   objects = {}
   total_frames = len(data['max_vals'])
   # examine basic values for each frame and find possible meteor detections
   for i in range(0,len(data['max_vals'])):
      x,y = data['pos_vals'][i]
      max_val = data['max_vals'][i]
      if max_val > 10:
         if last_i is not None and  last_i + 1 == i:
            cm += 1
         else:
            cm = 0
         masked = check_pt_in_mask(masks, x, y)
         if masked == 0:
            data_x.append(x)
            data_y.append(y)
            object, objects = find_object(objects, i,x, y, SD_W, SD_H, max_val, 0, 0, None)
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

   # remove most eroneous objects
   objects = filter_bad_objects(objects)

   # analyze the objects for a first run meteor detection (strict=0) 
   for id in objects:
      objects[id] = analyze_object(objects[id], 0,0)
   objects = filter_bad_objects(objects)

   # merge object detections into trim clips
   objects = objects_to_trims(objects, video_file)
   return(events, objects, total_frames)

def buffer_start_end(start,end,buf_size, total_frames):
   start = start - buf_size
   end = end + buf_size
   status = "good"
   if start < 0:
      start = 0
      status = "start_truncated"
   if end >= total_frames:
      end = total_frames
      status = "end_truncated"
   return(start, end, status)

def crop_video(video_file, x, y, w, h, crop_out_file = None): 
   if crop_out_file is None:
      crop_out_file = video_file.replace(".mp4", "-crop.mp4")
   crop = "crop=" + str(w) + ":" + str(h) + ":" + str(x) + ":" + str(y)

   cmd = "/usr/bin/ffmpeg -i " + video_file + " -filter:v \"" + crop + "\" -y " + crop_out_file + " > /dev/null 2>&1"
   print("CMD:", cmd)
   os.system(cmd)
   return(crop_out_file)

def json_rpt(obj):
   print("")
   for key in obj:
      if key == "report":
         for rk in obj[key]:
            print(rk, obj[key][rk])
      else:
         print(key, obj[key])
   print("")
   

def detect_all(vals_file):
   video_file = vals_file.replace("-vals.json", ".mp4") 
   video_file = video_file.replace("data/", "") 
   try:
      w,h,tf = ffprobe(video_file)
   except:
      print("BAD VIDEO FILE?!", video_file)
      return()
   w = int(w)
   h = int(h)
   hdm_x = 1920 / w 
   hdm_y = 1080 / h

   # GET THE EVENTS AND OBJECTS FROM THE VALS FILE
   events, objects,total_frames, = detect_in_vals(vals_file)
   obj_events = []
   for id in objects:
      obj = objects[id]
      oev = {}
      oev['frames'] = [obj['ofns'][0], obj['ofns'][-1]]
      oev['pos_vals'] = []
      for i in range(0, len(obj['oxs'])):
         x = obj['oxs'][i]
         y = obj['oys'][i]
         oev['pos_vals'].append((x,y))
      obj_events.append(oev)

   print("EVENTS:",  len(events))
   print("OBJECTS:",  len(objects))
   print("EVENTS:",  events)
   print("OBJECTS:",  objects)


   #exit()

   # FOR EACH EVENT MAKE AN SD TRIM FILE AND TRIM CROP FILE
   trim_files, crop_files, crop_boxes,durs = trim_events(vals_file, obj_events, total_frames, w, h, hdm_x, hdm_y)
   print("TRIM FILES:", trim_files) 
   print("CROP FILES:", crop_files) 
   print("CROP BOXES:", crop_boxes) 

   good_meteors = []
   # FOR EACH TRIM FILE RUN VIDEO METEOR DETECTION
   tc = 0
   for trim_file in trim_files:
      crop_file = crop_files[tc]
      crop_x = crop_boxes[tc][0]
      crop_y = crop_boxes[tc][1]
      sd_objects, frames = detect_meteor_in_clip(crop_file, None, 0, crop_x , crop_y , 0)
      mf = 0
      for id in sd_objects:
         sd_objects[id] = analyze_object(sd_objects[id], 0,1)
         if sd_objects[id]['report']['meteor'] == 1:
            mf= 1
            good_meteors.append((trim_file, crop_boxes[tc], sd_objects[id]))
      if mf == 0:
         PIPE_OUT = PIPELINE_DIR + "IN/"
         PIPE_FAILED = PIPELINE_DIR + "FAILED/"
         if cfe(PIPE_FAILED, 1) == 0:
            os.makedirs(PIPE_FAILED)
         #tfn = trim_file.split("/")[-1]
         #tdir = trim_file.replace(tfn, "")
         rpt_file = trim_file.replace(".mp4", "-failed.json")
         failed_data = {}
         failed_data['sd_objects'] = sd_objects
         failed_data['sd_crop_box'] = crop_boxes[tc]
         save_json_file(rpt_file, failed_data)
         twild = trim_file.replace(".mp4", "*")
         cmd = "mv " + twild + " " + PIPE_FAILED
         print(cmd)
         #os.system(cmd)
         exit()
         

      tc += 1

   for gm in good_meteors:
      trim_file, crop_box, obj = gm
      json_rpt(obj)

   if len(good_meteors) == 0:
      print("NO METEORS DETECT")
      return()
   

   # FOR EACH TRIM IF THERE IS A METEOR DETECTION GRAB AND SYNC THE HD FILE
   tc = 0
   for trim_file, crop_boxes, sd_objs in good_meteors:
      hd_trim = find_hd(trim_file,durs[tc])
      frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hd_trim, json_conf, 0, 1, [], 0,[])
      sx1,sy1,sx2,sy2 = crop_boxes
      nw = (sx2 - sx1) * 2
      nh = (sy2 - sy1) * 2
      print("NEW W/H:", nw,nh) 

      mx = int(int((sx1 + sx2) * hdm_x) / 2)
      my = int(int((sy1 + sy2) * hdm_y) / 2)

      cx1 = int(mx - nw/2) 
      cy1 = int(my - nh/2) 
      cx2 = int(mx + nw/2) 
      cy2 = int(my + nh/2) 

      cv2.rectangle(frames[0], (mx-5, my-5), (mx+5, my+5), (255,255,255), 1, cv2.LINE_AA)
      cv2.rectangle(frames[0], (cx1, cy1), (cx2, cy2), (100,100,100), 1, cv2.LINE_AA)
      cv2.imshow('pepe', frames[0])
      cv2.waitKey(90)
   
      if hd_trim is not None:
         print("TRIM HD CROP FILE:", hd_trim, cx1,cy1,cx2-cx1, cy2-cy1)
         hd_crop_out_file = crop_video(hd_trim, cx1, cy1, cx2-cx1, cy2-cy1)
      else:
         print("HD TRIM:", hd_trim)
      tc += 1

   # NOW WE SHOULD ALREADY HAVE AN SD METEOR. 
   # LETS TRY TO FIND IT IN THE HD CROP
   # IF WE FAIL, THEN WE WILL JUST USE THE SD METEOR AND UPSCALE THINGS TO WORK
   # ELSE WE WILL USE THE HD DETECT INFO

   for trim_file, crop_box, sd_objs in good_meteors:
      rpt_file = trim_file.replace(".mp4", "-meteor.json")
      md = {}
      md['sd_cropbox'] = crop_box
      md['sd_trim_file'] = trim_file
      md['sd_objs'] = sd_objs
      save_json_file(rpt_file, md)

   

def get_trim_num(file):
   el = file.split("-trim") 
   at = el[1]
   at = at.replace("-SD.mp4", "")
   at = at.replace("-crop", "")
   at = at.replace("-HD.mp4", "")
   at = at.replace(".mp4", "")
   at = at.replace("-", "")
   return(at)

def find_hd(sd_trim_file, dur):
   PIPE_OUT = PIPELINE_DIR + "IN/"
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(sd_trim_file)
   sdfn = sd_trim_file.split("/")[-1]
   sd_trim_num = get_trim_num(sd_trim_file) 
   print("SD FILE TIME:", f_datetime)
   print("SD TRIM NUM:", sd_trim_num)
   extra_trim_sec = int(sd_trim_num) / 25
   print("EXTRA TRIM SECONDS:", sd_trim_num)
   sd_trim_start = f_datetime + datetime.timedelta(seconds=extra_trim_sec)
   sd_start_min_before = sd_trim_start + datetime.timedelta(seconds=-60)
   sd_start_min_after = sd_trim_start + datetime.timedelta(seconds=+60)

   # get the HD files within +/- 1 min of the SD trim start time for this cam
   print("SD TRIM START TIME:", sd_trim_start)
   date_wild = sd_trim_start.strftime("%Y_%m_%d_%H_%M")
   date_wild_before = sd_start_min_before.strftime("%Y_%m_%d_%H_%M")
   date_wild_after = sd_start_min_after.strftime("%Y_%m_%d_%H_%M")
   print("CAM:", cam)
   print("DATE WILD:", date_wild)
   hd_wild = "/mnt/ams2/HD/" + date_wild + "*" + cam + ".mp4"
   hd_wild_before = "/mnt/ams2/HD/" + date_wild_before + "*" + cam + ".mp4"
   hd_wild_after = "/mnt/ams2/HD/" + date_wild_after + "*" + cam + ".mp4"
   print("HD WILD:", hd_wild)
   hd_matches = glob.glob(hd_wild)

   best_hd_matches = []

   for hd_file in hd_matches:
      (hd_datetime, hd_cam, hd_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(hd_file)
      hd_time_diff = (hd_datetime - sd_trim_start).total_seconds()

      print("SD/HD TIME DIFF:", hd_time_diff)
      if -60 <= hd_time_diff <= 0:
         best_hd_matches.append((hd_file, hd_time_diff))
      if hd_time_diff > 0:
         hd_matches_before = glob.glob(hd_wild_before)

         for hd_file in hd_matches_before:
            (hd_datetime, hd_cam, hd_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(hd_file)
            hd_time_diff = (hd_datetime - sd_trim_start).total_seconds()
            print("BEFORE SD/HD TIME DIFF:", hd_time_diff)
            if -60 <= hd_time_diff <= 0:
               best_hd_matches.append((hd_file,hd_time_diff))

   print("BEST HD FILE:", best_hd_matches)
   if len(best_hd_matches) == 1:
      hd_file = best_hd_matches[0][0]
      hd_time_diff = best_hd_matches[0][1]
      hd_trim_start = abs(hd_time_diff) * 25
      hd_trim_end = hd_trim_start + dur
      hd_trim_out = PIPE_OUT + sdfn
      hd_trim_out = hd_trim_out.replace("-SD", "-HD")
      print("HD TRIM OUT:", hd_trim_out)
      if cfe(hd_trim_out) == 0:
         hd_trim_start, hd_trim_end, status = buffer_start_end(hd_trim_start, hd_trim_end, 10, 1499)
         trim_min_file(hd_file, hd_trim_out, hd_trim_start, hd_trim_end)
      (hd_datetime, hd_cam, hd_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(hd_file)

   # We should only need the after file if the current file worked but the hd time is at the EOF

   return(hd_trim_out)



def trim_min_file(video_file, trim_out_file, trim_start_num, trim_end_num):
   cmd = """ /usr/bin/ffmpeg -i """ + video_file + """ -vf select="between(n\,""" + str(trim_start_num) + """\,""" + str(trim_end_num) + """),setpts=PTS-STARTPTS" -y """ + trim_out_file + " >/dev/null 2>&1"
   print("CMD:", cmd)
   os.system(cmd)


def trim_events(video_file, events, total_frames, sd_w, sd_h, hdm_x, hdm_y):

   PIPE_OUT = PIPELINE_DIR + "IN/"
   

   if "vals" in video_file:
      video_file = video_file.replace("-vals.json", ".mp4") 
      video_file = video_file.replace("data/", "") 
   vfn = video_file.split("/")[-1]
   sd_min_dir = video_file.replace(vfn, "trim_files/")
   if cfe(PIPE_OUT, 1) == 0:
      os.makedirs(PIPE_OUT)

   #print("TRIM EVENTS")
   trim_files = []
   crop_files = []
   crop_boxes = []
   durations = []
   for ev in events:
      start, end = ev['frames']
      start, end, status = buffer_start_end(start, end, 10, total_frames)
      dur = end - start
      trim_out_file = PIPE_OUT + vfn.replace(".mp4", "-trim-" + str(start) + "-SD.mp4")
      if cfe(trim_out_file) == 0: 
         trim_min_file(video_file, trim_out_file, start, end)
      xs = [i[0] for i in ev['pos_vals']]
      ys = [i[1] for i in ev['pos_vals']]
      (cx1, cy1, cx2, cy2, mx,my) = find_crop_size(min(xs),min(ys),max(xs),max(ys), sd_w, sd_h, hdm_x, hdm_y )
     
      cw = cx2 - cx1 
      ch = cy2 - cy1 
      crop_out_file = trim_out_file.replace(".mp4", "-crop.mp4")
      print("SD CROP BOUNDS:", cx1, cy1, cx2, cy2)
      print("SD CROP SIZE:", cw, ch)
      print("CROP OUT FILE:", crop_out_file)

      if cfe(crop_out_file) == 0: 
         crop_out_file = crop_video(trim_out_file, cx1, cy1, cw, ch)
      print("TRIM :", start, end, video_file)
      print("CROP:", cx1,cy1, cx2,cy2,cw,ch, crop_out_file)

      trim_files.append(trim_out_file)
      crop_files.append(crop_out_file)
      crop_boxes.append((cx1,cy1,cx2,cy2))
      durations.append(dur)

   return(trim_files, crop_files, crop_boxes, durations)
      
     

def trim_meteors_from_min_file(objects):
   # for each object that might be a meteor 
   # trim out the SD clip
   # run video detect on SD clip
   # if it passes on SD
   # find HD file and trim it
   # make an HD crop version
   # run video detect on HD (crop) file
 
   all_clips = {}
   for id in objects:
      # analyze object with strict=0 to confirm meteor
      objects[id] = analyze_object(objects[id], 0,0)
      # If it is a potential meteor split out the SD file
      if objects[id]['report']['non_meteor'] == 0:
         objects[id]['sd_video_file'] = video_file
    
         video_outfile = "/mnt/ams2/tests/" + objects[id]['trim_file'] 
         jpg_outfile = "/mnt/ams2/tests/" + objects[id]['trim_file'] + "-%04d.jpg"
         jpg_outfile = jpg_outfile.replace(".mp4", "")

         start_trim = "{:04d}".format(objects[id]['clip_start_fn'])
         end_trim = objects[id]['clip_start_fn']
         test_outfile = jpg_outfile.replace("%04d", start_trim)

         buf_size = 5
         buf_start, buf_end = buffered_start_end(objects[id]['clip_start_fn'],objects[id]['clip_end_fn'], total_frames, buf_size)

         # dump SD frames
         if cfe(test_outfile) == 0:
            ffmpeg_splice(video_file, buf_start, buf_end, jpg_outfile)
         # dump SD video 
         if cfe(video_outfile) == 0:
            ffmpeg_splice(video_file, buf_start, buf_end, video_outfile)
         objects[id]['sd_trim_file'] = video_outfile

         all_clips[video_outfile] = {}




         
         #obj_report(objects[id])

   # run video meteor detect on the SD video trim
   for video_outfile in all_clips:
      sd_objects, frames = detect_meteor_in_clip(video_outfile, None, fn = 0, crop_x = 0, crop_y = 0, hd_in = 0)
      sd_objects = filter_bad_objects(sd_objects)
      for id in sd_objects:
         # analyze objects with strict=1 to verify meteor
         sd_objects[id] = analyze_object(sd_objects[id], 0, 1)
         sd_objects[id]['sd_video_file'] = video_outfile
         sd_objects[id]['trim_file'] = video_outfile
         obj_report(sd_objects[id])


   return(events,objects)

def objects_to_trims(objects, video_file):
   trim_clips = [] 
   rm_objs = [] 
   oc = 0
   for id in objects:
      merge_clip = 0
      if len(trim_clips) == 0:
         tc = {}
         start = objects[id]['ofns'][0]
         end   = objects[id]['ofns'][-1]
         tc['start'] = start
         tc['end'] = end 
         trim_file = video_file.split("/")[-1]
         trim_file = trim_file.replace(".mp4", "-trim-" + "{:04d}".format(start) + ".mp4")
         objects[id]['trim_file'] = trim_file
         objects[id]['clip_start_fn'] = tc['start']
         objects[id]['clip_end_fn'] = tc['end']
         trim_clips.append(tc)
      else:
         # check if the last trim clip is within 25 frames of this clip. If it is merge this one into the last one
         last_end = trim_clips[oc-1]['end']
         last_start = trim_clips[oc-1]['start']
         start = objects[id]['ofns'][0]
         end = objects[id]['ofns'][-1]


         if tc['start'] - last_end < 25:
            merge_clip = 1
            trim_clips[oc-1]['end']= objects[id]['ofns'][-1]
            objects[id]['trim_file'] = trim_file
            objects[id]['clip_start_fn'] = last_start 
            objects[id]['clip_end_fn'] = end 
            objects[last_obj_id]['clip_end_fn'] = end


            objects[id]['obj_end_fn'] = tc['end']
         else:
            tc = {}
            tc['start'] = objects[id]['ofns'][0]
            tc['end']   = objects[id]['ofns'][-1]
            trim_clips.append(tc)

            trim_file = video_file.split("/")[-1]
            trim_file = trim_file.replace(".mp4", "-trim-" + "{:04d}".format(start) + ".mp4")
            objects[id]['trim_file'] = trim_file
            objects[id]['clip_start_fn'] = tc['start']
            objects[id]['clip_end_fn'] = tc['end']
         
      if merge_clip != 1:  
         oc += 1
      last_obj_id = id
   return(objects)      

def obj_report(object):
   print("")
   if "sd_video_file" in object:
      print("Video File:           :    {:s} ".format(str(object['sd_video_file'])))
   else:
      print("WARNING: no sd_video_file in object.")
   if "trim_file" in object:
      print("Trim File:            :    {:s} ".format(str(object['trim_file'])))
      print("WARNING: no trim_file in object.")
   print("Start                 :    {:s} ".format(str(object['ofns'][0])))
   print("End                   :    {:s} ".format(str(object['ofns'][-1])))
   print("Frames                :    {:s} ".format(str(object['ofns'])))
   print("Xs                    :    {:s} ".format(str(object['oxs'])))
   print("Ys                    :    {:s} ".format(str(object['oys'])))
   print("Intensity             :    {:s} ".format(str(object['oint'])))
   for field in object['report']:
      print("{:18s}    :    {:s} ".format(field, str(object['report'][field])))


#   print("Consecutive Motion    :    {:s} ".format(str(object['report']['cm'])))
#   print("Unique Points         :    {:s} ".format(str(object['report']['unq_points'])))
#   print("Unique Percent        :    {:s} ".format(str(object['report']['unq_perc'])))
#   print("Object PX Length      :    {:s} ".format(str(object['report']['object_px_length'])))
#   print("Object Line Segments  :    {:s} ".format(str(object['report']['line_segments'])))
#   print("Object X Segments     :    {:s} ".format(str(object['report']['x_segs'])))
#   print("Object Ms             :    {:s} ".format(str(object['report']['ms'])))
#   print("Object Bs             :    {:s} ".format(str(object['report']['bs'])))
#   print("Object Non-Meteor     :    {:s} ".format(str(object['report']['non_meteor'])))
#   print("Bad Items             :    {:s} ".format(str(object['report']['bad_items'])))
#object['report']['object_px_length'], object['report']['line_segments'], object['report']['x_segs'], object['report']['ms'], object['report']['bs']

def detect_meteor_in_clip(trim_clip, frames = None, fn = 0, crop_x = 0, crop_y = 0, hd_in = 0 ):
   objects = {}
   print("DETECT METEORS IN VIDEO FILE:", trim_clip)
   if trim_clip is None: 
      return(objects, []) 

   if frames is None :
      print("LOAD FRAMES FAST...")  
      frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(trim_clip, json_conf, 0, 1, [], 0,[])
   if len(frames) == 0:
      return(objects, []) 

   if frames[0].shape[1] == 1920 or hd_in == 1:
      hd = 1
      sd_multi = 1
   else:
      hd = 0
      sd_multi = 1920 / frames[0].shape[1]
   if len(frames[0].shape) == 3:
      aframe = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
      image_acc = aframe
   else:
      image_acc = frames[0]
   image_acc = np.float32(image_acc)

   #for i in range(0,len(frames)):
   #   if len(frame.shape) == 3:
   #      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
   #   frame = frames[i]
 
#      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)
#      alpha = .5
#      hello = cv2.accumulateWeighted(blur_frame, image_acc, alpha)

   # preload the bg
   for frame in frames:
      if len(frame.shape) == 3:
         frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      frame = np.float32(frame)
      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)
      alpha = .5


      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), blur_frame,)
      hello = cv2.accumulateWeighted(blur_frame, image_acc, alpha)


   for frame in frames:
      if len(frame.shape) == 3:
         frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      if len(frames[0].shape) == 3:
         aframe = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
      else:
         aframe = frames[0].copy()
      show_frame = frame.copy()
      frame = np.float32(frame)
      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)
      alpha = .5


      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), blur_frame,)
      hello = cv2.accumulateWeighted(blur_frame, image_acc, alpha)

      show_frame = frame.copy()
      avg_px = np.mean(image_diff)
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(image_diff)
      thresh = max_val - 10
      if thresh < 5:
         thresh = 5

      cnts,rects = find_contours_in_frame(image_diff, thresh)
      icnts = []
      if len(cnts) < 5 and fn > 0:
         for (cnt) in cnts:
            px_diff = 0
            x,y,w,h = cnt
            if w > 1 and h > 1:
               intensity,mx,my,cnt_img = compute_intensity(x,y,w,h,frame,aframe)
               cx = int(mx) 
               cy = int(my) 
               cv2.circle(show_frame,(cx+crop_x,cy+crop_y), 10, (255,255,255), 1)
               object, objects = find_object(objects, fn,cx+crop_x, cy+crop_y, w, h, intensity, hd, sd_multi, cnt_img)

               objects[object]['trim_clip'] = trim_clip
               cv2.rectangle(show_frame, (x, y), (x+w, y+h), (255,255,255), 1, cv2.LINE_AA)
               #desc = str(fn) + " " + str(intensity) + " " + str(objects[object]['obj_id']) + " " + str(objects[object]['report']['obj_class']) #+ " " + str(objects[object]['report']['ang_vel'])
               desc = str(fn) + " " + str(intensity) + " " + str(objects[object]['obj_id'])  
               cv2.putText(show_frame, desc,  (x,y), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      
      show_frame = cv2.convertScaleAbs(show_frame)
      show = 1
      if show == 1:
         cv2.imshow('Detect Meteor In Clip', show_frame)
         cv2.waitKey(90)
      fn = fn + 1



   if show == 1:
      cv2.destroyAllWindows()

   return(objects, frames)   

def find_contours_in_frame(frame, thresh=25 ):
   contours = [] 
   result = []
   _, threshold = cv2.threshold(frame.copy(), thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(threshold.copy(), None , iterations=4)
   threshold = cv2.convertScaleAbs(thresh_obj)
   cnt_res = cv2.findContours(threshold.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   show_frame = cv2.resize(threshold, (0,0),fx=.5, fy=.5)
   if len(cnts) > 20:
      thresh = thresh +5 
      _, threshold = cv2.threshold(frame.copy(), thresh, 255, cv2.THRESH_BINARY)
      thresh_obj = cv2.dilate(threshold.copy(), None , iterations=4)
      threshold = cv2.convertScaleAbs(thresh_obj)
      cnt_res = cv2.findContours(threshold.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res

   # now of these contours, remove any that are too small or don't have a recognizable blob
   # or have a px_diff that is too small

   rects = []
   recs = []
   if len(cnts) < 50:
      for (i,c) in enumerate(cnts):
         px_diff = 0

         x,y,w,h = cv2.boundingRect(cnts[i])
        

         if w > 1 or h > 1 and (x > 0 and y > 0):

            cnt_frame = frame[y:y+h, x:x+w]
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_frame)
            avg_val = np.mean(cnt_frame)
            if max_val - avg_val > 5 and (x > 0 and y > 0):
               rects.append([x,y,x+w,y+h])
               contours.append([x,y,w,h])

   #rects = np.array(rects)



   if len(rects) > 2:
      recs, weights = cv2.groupRectangles(rects, 0, .05)
      rc = 0
      for res in recs:
         rc = rc + 1

   #cv2.imshow("pepe", threshold)
   #cv2.waitKey(0)

   return(contours, recs)

