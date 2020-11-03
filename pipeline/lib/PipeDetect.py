''' 

   Pipeline Detection Routines

'''
import scipy.optimize

import glob
from datetime import datetime as dt
import datetime
#import math
import os
from lib.PipeAutoCal import fn_dir
from lib.PipeVideo import ffmpeg_splice, find_hd_file, load_frames_fast, find_crop_size, ffprobe
from lib.PipeUtil import load_json_file, save_json_file, cfe, get_masks, convert_filename_to_date_cam, buffered_start_end, get_masks, compute_intensity , bound_cnt
from lib.DEFAULTS import *
from lib.PipeMeteorTests import big_cnt_test, calc_line_segments, calc_dist, unq_points, analyze_intensity, calc_obj_dist, meteor_direction, meteor_direction_test, check_pt_in_mask, filter_bad_objects, obj_cm, meteor_dir_test, ang_dist_vel
from lib.PipeImage import stack_frames

import numpy as np
import cv2

json_conf = load_json_file(AMS_HOME + "/conf/as6.json")

def biggest_cnts(cnts, count=5):
   ci = []
   cij = []
   for cx,cy,cw,ch in cnts:
      size = cw * ch
      ci.append((cx,cy,cw,ch,size))
      ci = sorted(ci , key=lambda x: (x[4]), reverse=True)
   for cx,cy,cw,ch,size in ci:
      #print("BIGGEST CNTS:", cx,cy,cw,ch,size)
      inside = 0
      if len(cij) > 0:
         inside = check_cnt_inside(cij, (cx,cy,cw,ch))
      if inside == 0:
         cij.append((cx,cy,cw,ch))
   return(cij[0:count])

def check_cnt_inside(cnt_list, this_cnt):
   tx,ty,tw,th = this_cnt
   ctx = tx + (tw/2)
   cty = ty + (th/2)
   inside = 0
   bl = 50
   for x,y,w,h in cnt_list:
      if w > bl:
         bl = w   
      if h > bl:
         bl = h   
      x1,y1,x2,y2 = bound_cnt(x, y,1920,1080, bl)
      if x1 < tx < x2 and y1 < ty < y2:
         inside = 1
      if x1 < tx + tw < x2 and y1 < ty + th < y2:
         inside = 1
      if x1 < ctx < x2 and y1 < cty < y2:
         inside = 1
      if inside == 0:
         dist = calc_dist((tx,ty),(x1,y1))
         dist2 = calc_dist((tx,ty),(x2,y1))
         dist3 = calc_dist((tx,ty),(x1,y2))
         dist4 = calc_dist((tx,ty),(x2,y2))
         dist5 = calc_dist((tx,ty),(tx,y1))
         dist6 = calc_dist((tx,ty),(tx,y2))
         dist7 = calc_dist((tx,ty),(x1,ty))
         dist8 = calc_dist((tx,ty),(x2,ty))
         min_dist = min(dist,dist2,dist3,dist4,dist5,dist6,dist7,dist8)
         #print("NOT INSIDE MIN DIST:", min_dist)
         if min_dist < 10:
            inside = 1
   return(inside)


def best_thresh(img, thresh, i=0):
   cnts,rects = find_contours_in_frame(img, thresh=thresh)
   for cnt in cnts:
      x,y,w,h = cnt
      #if w >= img.shape[1]:
      #   thresh = thresh + 50
   for i in range(1,20):
      thresh = thresh + (i*10)
      cnts,rects = find_contours_in_frame(img, thresh=thresh)
      if len(cnts) < 15:
         return(thresh)
      if thresh > 200:
         thresh = 200
   return(thresh)

def verify_meteor(meteor_file, json_conf):
   fn, dir = fn_dir(meteor_file)
   base = fn.split("-")[0]
   day = fn[0:10]
   sd_dir = "/mnt/ams2/SD/proc2/" + day + "/" 
   files = glob.glob(sd_dir + base + "*trim*.mp4")
   print(files)
   media = {}
   for file in files:
      w,h,frames = ffprobe(file)
      media[file] = (w,h,frames)

   meteors = {}
   SD = 0
   sd_stack_img = None
   hd_stack_img = None
   sd_images = {}
   hd_images = {}
   for file in media:
      if "crop" not in file and "HD" not in file:
         print(file, media[file])
         best_meteor,sd_stack_img,bad_objs = fireball(file, json_conf)
         if best_meteor is not None:
            sd_images[file] = sd_stack_img
            meteors[file] = best_meteor
            SD = 1
   if len(meteors) == 0:
      print("Sorry we found no meteors here.")
      return(None)

   # if we made it this far we have at least found the meteor in one file
   # lets check the HD files to see if we have a meteor there too
   HD = 0
   for file in media:
      if "HD" in file and "crop" not in file:
         best_meteor, stack_img,bad_objs = fireball(file, json_conf)
         if best_meteor is not None:
            best_meteor, hd_stack_img, bad_objs = fireball(file, json_conf)
            if best_meteor is not None:
               hd_images[file] = hd_stack_img
               meteors[file] = best_meteor
               HD = 1

   if SHOW == 1:
      for file in sd_images:
         print("SD IMGS:", file) 
         cv2.imshow('pepe', sd_images[file])
      for file in hd_images:
         print("HD IMGS:", file) 
         cv2.imshow('pepe', hd_images[file])

   for file in meteors:
      print(file, meteors[file])


   if SD == 1 and HD == 1:
      print("WIN! we have SD and HD meteors.")
   if SD == 0 and HD == 1:
      print("we have only HD meteors.")
   if SD == 1 and HD == 0:
      print("we have only SD meteors.")
   for file in meteors:
      print("METEOR:", file, media[file])
      print(meteors[file])
   save_old_meteor(meteors, media, sd_images, hd_images)

def obj_to_mj(sd_file, hd_file, sd_objects, hd_objects):
   sd_fn, dir = fn_dir(sd_file)
   if hd_file is not None and hd_file != 0:
      hd_fn, dir = fn_dir(hd_file)
   date = sd_fn[0:10]
   mdir = "/mnt/ams2/meteors/" + date + "/" 
   mj = {}
   mj['meteor'] = 1
   mj['sd_trim'] = sd_file
   mj['sd_stack'] = mdir + sd_fn.replace(".mp4", "-stacked.png")
   mj['sd_objects'] = sd_objects
   mj['hd_trim'] = hd_file
   if hd_file != "":
      mj['hd_stack'] = mdir + hd_fn.replace(".mp4", "-stacked.png")
   else:
      mj['hd_stack'] = ""
      
   mj['hd_objects'] = hd_objects
   mj['trim_clip'] = sd_file
   mj['sd_video_file'] = sd_file
   mj['org_sd_vid'] = sd_file
   mj['orig_hd_vid'] = hd_file
   mj['hd_video_file'] = hd_file
   return(mj)

def save_old_meteor(meteors, media, sd_images, hd_images):
   for key in sd_images:
      print("SD IMG:", key)
   for key in hd_images:
      print("HD IMG:", key)
   mj = {}
   for file in meteors:
      if meteors[file] is None:
         continue
      print("METEOR FILE:", file, meteors[file])

      fn, dir = fn_dir(file)
      date = fn[0:10]
      mdir = "/mnt/ams2/meteors/" + date + "/" 
      w,h,num_frames = media[file]
      print("WH:", w, h)
      if int(w) == 1920:
         HD = 1
         mj['hd_trim'] = mdir + fn
         mj['hd_video_file'] = mdir + fn 
         mj['org_hd_vid'] = file 
         mj['hd_stack'] = mdir + fn.replace(".mp4", "-stacked.png")
         mj['hd_objects'] = meteors[file]
         #mj['hd_objects'].append(meteors[file][id])
         mj['meteor'] = 1
         mj['archive_file'] = ""
         hd_stack_img = hd_images[file]
         hd_stack_img = cv2.resize(hd_stack_img, (THUMB_W, THUMB_H))
      else:
         SD = 1
         mj['sd_trim'] = mdir + fn 
         mj['archive_file'] = ""
         mj['org_sd_vid'] = file 
         mj['sd_video_file'] = mdir + fn 
         mj['trim_clip'] = mdir + fn 
         mj['sd_stack'] = mdir + fn.replace(".mp4", "-stacked.png")
         mj['sd_objects'] = []
         mj['sd_objects'].append( meteors[file])
         #for id in meteors[file]:
         #   print("SD OBJ:", meteors[file][id])
         #   mj['sd_objects'].append(meteors[file][id])
         print("FILE:", file)
         sd_stack_img = sd_images[file]
         sd_stack_img_tn = cv2.resize(sd_stack_img, (THUMB_W, THUMB_H))
         obj_img = sd_stack_img.copy()
         min_x = min(mj['sd_objects'][0]['oxs'])
         min_y = min(mj['sd_objects'][0]['oys'])
         max_x = max(mj['sd_objects'][0]['oxs'])
         max_y = max(mj['sd_objects'][0]['oys'])
         cv2.rectangle(obj_img, (min_x, min_y), (max_x, max_y), (255,255,255), 3, cv2.LINE_AA)
         obj_tn = cv2.resize(obj_img, (THUMB_W, THUMB_H))
   if "hd_trim" not in mj:
      # Here we find trim and detect the HD meteor
      for obj in mj['sd_objects']:
         dur_fr = (len(obj['oxs'])) 
      hd_trim = find_hd(mj['sd_trim'],dur_fr, mj['sd_objects'][0]['ofns'][0])
      best_meteor, hd_stack_img, bad_objs  = fireball(file, json_conf)
      print("HD TRIM:", hd_trim)
      print("BEST HD METEOR:", best_meteor)
      if best_meteor is not None:
         # We found the HD file and obj so copy it into the meteor dir and update the json
         mj['hd_objects'] = []
         mj['hd_objects'].append( best_meteor)
         fn, dir = fn_dir(hd_trim)
         mj['hd_trim'] = mdir + fn
         mj['hd_video_file'] = mdir + fn 
         mj['org_hd_vid'] = file 
         mj['hd_stack'] = mdir + fn.replace(".mp4", "-stacked.png")
         hd_stack_img_tn = cv2.resize(hd_stack_img, (THUMB_W, THUMB_H))
         cmd = "cp " + hd_trim + " " + mdir + fn
         print(cmd)
         os.system(cmd)

      else:
         mj['hd_trim'] = "0"
   print(mj)
   fn,dir = fn_dir(mj['sd_trim'])
   date = fn[0:10]
   mdir = "/mnt/ams2/meteors/" + date + "/" 
   js = fn.replace(".mp4", ".json")
   save_json_file(mdir + js, mj)
   # copy vids
   if "sd_trim" in mj:
      cmd = "cp " + mj['org_sd_vid'] + " " + mdir
      os.system(cmd)
      print(sd_stack_img.shape)
      print(mj['sd_stack'])
      cv2.imwrite(mj['sd_stack'], sd_stack_img)
      cv2.imwrite(mj['sd_stack'].replace(".png", "-tn.png"), sd_stack_img_tn)
      cv2.imwrite(mj['sd_stack'].replace(".png", "-obj-tn.png"), obj_tn)
   if "hd_trim" in mj:
      if mj['hd_trim'] != "0":
         cmd = "cp " + mj['org_hd_vid'] + " " + mdir
         os.system(cmd)
         cv2.imwrite(mj['hd_stack'], hd_stack_img)
         cv2.imwrite(mj['hd_stack'].replace(".png", "-tn.png"), hd_stack_img_tn)
   print("Saved json:", js)



def fireball(video_file, json_conf):
   objects = {}
   hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, 1, 1,[])
   i = 0
   med_file = video_file.replace(".mp4", "-med.jpg")
   if cfe(med_file) == 0:
      median_frame = cv2.convertScaleAbs(np.median(np.array(hd_frames), axis=0))
       
      median_frame = cv2.GaussianBlur(median_frame, (7, 7), 0)
      cv2.imwrite(med_file, median_frame)
   else:
      median_frame = cv2.imread(med_file)
      median_frame = cv2.cvtColor(median_frame, cv2.COLOR_BGR2GRAY)
   for frame in hd_frames:
      meteor_on = 0
      subframe = cv2.subtract(frame, median_frame)
      bx,by = pos_vals[i]
      bx1,by1,bx2,by2 = bound_cnt(bx, by,frame.shape[1],frame.shape[0], 50)

      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(subframe)
      avg_val = np.mean(subframe)
      half_max = ((max_val - avg_val) / 4) + avg_val

      thresh = best_thresh(subframe, half_max, i)
      cnts,rects = find_contours_in_frame(subframe, thresh=thresh)
      if len(cnts) > 2:
         cnts = biggest_cnts(cnts, 10)
      #cnts = get_contours_in_image(subframe)

      for cx,cy,cw,ch in cnts:
         cv2.rectangle(subframe, (cx, cy), (cx+cw, cy+ch), (255,255,255), 3, cv2.LINE_AA)
         ccx = cx + int(cw / 2)
         ccy = cy + int(ch / 2)
         cnt_img = frame[cy:cy+ch,cx:cx+cw]
         cnt_int = int(np.sum(cnt_img))
         #object, objects = find_object(objects, i,ccx, ccy, cw, ch, cnt_int, 1, 0, None)
         object, objects = find_object(objects, i,cx, cy, cw, ch, cnt_int, 1, 0, None)
         objects[object] = analyze_object(objects[object], 1,1)
         #if "class" in objects[object]:
         #   if objects[object]['class'] != 'star':
         #      print(objects[object]['report'])
         if "meteor" in objects[object]:
            if objects[object]['meteor'] == 1 and objects[object]['non_meteor'] == 0:
               objects[object]['class'] = 'meteor'

         if "class" in objects[object]['report']: 
            #desc += " - " + objects[object]['report']['class'] + " " + str(objects[object]['report']['meteor']) + str(objects[object]['report']['non_meteor']) + str(objects[object]['report']['bad_items']) + str(objects[object]['oxs'])
            if objects[object]['report']['meteor'] == 1 and objects[object]['report']['non_meteor'] == 0:
                objects[object]['report']['class'] = "meteor"
                rx1,ry1,rx2,ry2 = bound_cnt(ccx, ccy,frame.shape[1],frame.shape[0], 50)
                cv2.rectangle(subframe, (rx1, ry1), (rx2, ry2), (255,0,0), 1, cv2.LINE_AA)
            desc = str(object) + " - " + objects[object]['report']['class'] #+ " " + str(objects[object]['report']['meteor']) + str(objects[object]['report']['non_meteor']) 
            cv2.putText(subframe, str(desc),  (ccx-10,ccy-10), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
            meteor_on = 1
            #print("CNTS METEOR:", object)
      


      if meteor_on == 1:

         if SHOW == 1:
            sframe = cv2.resize(subframe, (1280, 720))
            desc = "Frame:" + str(i)
            cv2.putText(sframe, desc,  (10,40), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
            desc = str(sum_vals[i]) + " " + str(max_vals[i]) + " " + str(pos_vals[i]) + " " + str(len(cnts))
            cv2.putText(sframe, desc,  (10,70), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
            cv2.imshow('pepe', sframe)
            cv2.waitKey(30)
         i += 1

   m = 0
   meteors = []
   for obj in objects:

      objects[obj] = analyze_object(objects[obj], 1,1)
      if objects[obj]['report']['meteor'] == 1:
         print(obj, "FRAMES:", len(objects[obj]['ofns']))
         m += 1
         meteors.append(objects[obj])
         for r in objects[obj]['report']:
            print("Report:", r, objects[obj]['report'][r])


   for meteor in meteors:
      meteor = analyze_object(meteor, 1,1)


   if m > 1:
      best_meteor = dom_meteor(meteors, json_conf)
   if m == 1:
      best_meteor = meteors[0]
   else: 
      best_meteor = None
   print("DONE:", best_meteor)
   if best_meteor is None:
      return(None, None, objects)

   # draw cnts on image 
   for i in range(0, len(best_meteor['oxs'])):
      fn = best_meteor['ofns'][i] 
      #fn = ff + i
      img = hd_frames[fn]
      x = best_meteor['oxs'][i]
      y = best_meteor['oys'][i]
      w = best_meteor['ows'][i]
      h = best_meteor['ohs'][i]
      cx = x + int(w/2)
      cy = y + int(h/2)
      lim = 50
      if w > lim:
         lim = w + 10
      if h > lim:
         lim = h + 10
      rx1,ry1,rx2,ry2 = bound_cnt(cx, cy,1920,1080, lim)
      
      if SHOW == 1:
         cv2.rectangle(img, (x, y), (x+w, y+h), (255,0,0), 1, cv2.LINE_AA)
         cv2.rectangle(img, (rx1, ry1), (rx2, ry2), (128,0,0), 1, cv2.LINE_AA)

         sframe = cv2.resize(img, (1280, 720))
         desc = "Frame:" + str(fn)
         cv2.putText(sframe, desc,  (10,20), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         cv2.imshow('pepe', sframe)
         cv2.waitKey(30)

   stack_img = stack_frames(hd_color_frames)
   if SHOW == 1:
      cv2.imshow('pepe', stack_img)
      cv2.waitKey(60)

   return(best_meteor, stack_img, objects )


def dom_meteor(meteors, json_conf):
   mcache = {}
   scores = {}
   durs = []
   sizes = []
   dists = []
   for m in meteors:
      id = m['obj_id']
      mcache[id] = m
      maxw = max(m['ows'])
      maxh = max(m['ohs'])
      size = maxw * maxh

      durs.append((id, m['report']['cm']))
      sizes.append((id, size))
      dists.append((id, m['report']['ang_dist']))
      print(m)

   sorted_durs = sorted(durs, key=lambda x: (x[1]), reverse=True)
   sorted_sizes = sorted(sizes, key=lambda x: (x[1]), reverse=True)
   sorted_dists = sorted(dists, key=lambda x: (x[1]), reverse=True)
   m1 =  sorted_durs[0][0]
   m2 =  sorted_sizes[0][0]
   m3 =  sorted_dists[0][0]
   if m1 not in scores:
      scores[m1] = 1
   else:
      scores[m1] += 1
   if m2 not in scores:
      scores[m2] = 1
   else:
      scores[m2] += 1
   if m3 not in scores:
      scores[m3] = 1
   else:
      scores[m3] += 1
   print("\n*******DOM DUR*********\n")
   print(mcache[m1])
   print("\n*******DOM SIZE*********\n")
   print(mcache[m2])
   print("\n*******DOM DIST*********\n")
   print(mcache[m3])
   print("Longest dur :", sorted_durs[0])
   print("Biggest Size:", sorted_sizes[0])
   print("Longest Dist:", sorted_dists[0])
   bm = 0
   bs = 0
   for m in scores:
      score = scores[m]
      if score > bs:
         bs = score
         mb = m
   best_meteor = mcache[m]
   return(best_meteor)
  
def first_last_dist(obj, objects):
   fx = objects[obj]['xs'][0]
   fy = objects[obj]['ys'][0]
   lx = objects[obj]['xs'][-1]
   ly = objects[obj]['ys'][-1]
   dist = calc_dist((fx,fy),(lx,ly))
   return(dist)

def frames_to_image(frames):
   h,w = frames[0].shape[:2]
   print(w,h)
   total = len(frames)
   fr_per_row = int(1920 / w)  
   cols = int(total / fr_per_row ) + 1
   print("FRAMES PER ROW:", fr_per_row)
   print("COLS :", cols)
   big_img_w = int(w * fr_per_row) + 1
   big_img_h = int(h * cols) 
   print("SIZE NEEDED FOR BIG IMAGE:", big_img_w, big_img_h)

   big_img = np.zeros((big_img_h,big_img_w),dtype=np.uint8)
   i = 0
   col = 0
   row = 0
   for frame in frames: 
      print("COL:", col, cols)
      print("ROW:", row, cols)
      if col >= fr_per_row:
         col = 0
         row += 1
   
      px1 = col * w 
      py1 = row * h 
      px2 = px1 + w
      py2 = py1 + h
      big_img[py1:py2,px1:px2] = frame
      cv2.imshow('pepe', big_img)
      cv2.waitKey(90)

      col += 1
   
def make_roi_image(frame, thresh_frame, x1,y1,x2,y2):
   marked_frame = frame.copy()
   cv2.rectangle(marked_frame, (x1, y1), (x2, y2), (255,0,0), 1, cv2.LINE_AA)
   roi_img = frame[y1:y2,x1:x2] 
   roi_sub_img = thresh_frame[y1:y2,x1:x2] 
   roi_big_img = cv2.resize(roi_img, (300, 300))
   roi_big_sub_img = cv2.resize(roi_sub_img, (300, 300))
   roi_scale_x = 300 / roi_img.shape[1] 
   roi_scale_y = 300 / roi_img.shape[0] 
   return(marked_frame, roi_img, roi_big_img, roi_big_sub_img, roi_scale_x, roi_scale_y)


def get_leading_cnt(dom_dir, x_dir, y_dir, cnt_x, cnt_y, cnt_w, cnt_h):
   if dom_dir == 'x':
      if x_dir == 'left_to_right':
         # we want the far right side of original cnt x+w
         nx = cnt_x + cnt_w


      elif x_dir == 'right_to_left':
         # we want the far left side of original cnt x
         nx = cnt_x 
      else:
         # no x movement (center cnt) x + (cnt_w/2)
         nx = int(cnt_w/2) + cnt_x 

      if y_dir == 'up_to_down':
         #pick bottom side
         ny = int(cnt_y) + int(cnt_h)
         if cnt_h > 4:
            ny -= int(cnt_h/4)
      elif y_dir == 'down_to_up':
         ny = int(cnt_h) 
      else:
         ny = int(cnt_y) + int(cnt_h)
  


   if dom_dir == 'y':
      if y_dir == 'up_to_down':
          # we want the far down side of original cnt y+h
          ny = cnt_y + cnt_h
 
      elif y_dir == 'down_to_up':
         # we want the far top side of original cnt y
          ny = cnt_y
      else:
         # no x movement (center cnt) x + (cnt_w/2)
         ny = int(cnt_h/2) + cnt_y
      if x_dir == 'left_to_right':
          nx = int(cnt_w) + cnt_x - int(cnt_w/5)
      elif x_dir == 'right_to_left':
          nx = cnt_x + int(cnt_w/5)
      else:
         nx = cnt_x + int(cnt_w/2)


   return(nx,ny)


def get_roi_cnts(meteor, image, median_image, ox,oy, dom_dir, x_dir, y_dir):


   (show_frame, sub_frame, show_subframe, thresh_img, avg_val, max_val, thresh_val) = make_subframe(image, median_image)
   rx1,ry1,rx2,ry2 = bound_cnt(ox, oy,image.shape[1],image.shape[0], 50)
   cnt_img = thresh_img[ry1:ry2,rx1:rx2]
   cnts = get_contours_in_image(cnt_img)

   show_image = cv2.cvtColor(image,cv2.COLOR_GRAY2BGR)
   show_cnt_img = show_image[ry1:ry2,rx1:rx2]

   for x,y,w,h in cnts:
      cv2.rectangle(show_cnt_img, (x,y), (x+w, y+h), (100,0,0), 1, cv2.LINE_AA)


   #if len(cnts) > 1:
   #   cnts,dom_dir,x_dir,y_dir = get_best_cnt(cnts, meteor)
   shift_x = 0
   shift_y = 0
   w= 5
   h = 5
   for x,y,w,h in cnts:
      #lcx, lcy = get_leading_cnt(dom_dir, x_dir, y_dir, x, y, w, h)
      shift_x = x - 50  
      shift_y = y - 50
      #cv2.circle(show_cnt_img,(lcx,lcy), 10, (255,255,255), 1)
      #cv2.rectangle(show_cnt_img, (x,y), (x+w, y+h), (100,0,0), 1, cv2.LINE_AA)
      #cv2.rectangle(show_cnt_img, (lcx-4,lcy-4), (lcx+4, lcx+4), (100,0,0), 1, cv2.LINE_AA)

   if len(cnts) > 0 :

      off_frame = check_off_frame(image, rx1+shift_x,ry1+shift_y,rx2+shift_x,ry2+shift_y)
      if off_frame == 0:
         new_cnt_img = thresh_img[ry1+shift_y:ry2+shift_y,rx1+shift_x:rx2+shift_x]

         # THIS SHOULD BE THE REFINED x,y inside the "crop" frame.
         new_cnt = [ ox+shift_x, oy+shift_y, w, h]
         #big_cnt = cv2.resize(show_cnt_img, (300, 300))
         #big_new_cnt = cv2.resize(new_cnt_img, (300, 300))
         #cv2.waitKey(30)
         return(new_cnt)

   return(None)


def check_off_frame(frame, x1,y1,x2,y2):
   h,w = frame.shape[:2]
   if x1 < 0 or y1 < 0 or x2 < 0 or y2 < 0:
      return(1)
   if x1 > w or y1 > h or x2 > w or y2 > h:
      return(1)
   return(0)

def get_dist_info(crop_frames, ofns, oxs, oys):
   cx1 = 0
   cy1 = 0
   x_dist = []
   y_dist = []
   # get the distance info for all points (move to function)
   fn = 0
   mc = 0
   last_x = None
   for frame in crop_frames:
      if ofns[0] <= fn <= ofns[-1]:
         inside_meteor = 1
      else:
         inside_meteor = 0
      if inside_meteor == 1 and fn in ofns:

         if last_x is not None:
            xd = oxs[mc] - cx1 - last_x
            yd = oys[mc] - cy1 -  last_y
            fr_diff = fn - last_fn
            if last_fn > 1:
               xd = int(xd/fr_diff)
               yd = int(yd/fr_diff)
            x_dist.append(xd)
            y_dist.append(yd)

         last_x = oxs[mc]-cx1
         last_y = oys[mc]-cy1
         last_fn = ofns[mc]
         mc = mc + 1
      elif inside_meteor == 1 and fn not in ofns:
         print("MISSING A GAP FRAME HERE!", fn, inside_meteor, ofns)

      fn = fn + 1
   med_x = np.median(x_dist)
   med_y = np.median(y_dist)
   return(x_dist, y_dist, med_x, med_y)

def refine_meteor_points(meteor, crop_frames, json_conf):
   fn = 0
   mc = 0
   ofns = meteor['ofns']
   oxs = meteor['oxs']
   oys = meteor['oys']
   ohs = meteor['ows']
   ows = meteor['ohs']
   print(meteor)
   cx1,cy1,cx2,cy2,mx,my = meteor['cropbox_1080']
   inside_meteor = 0
   x_dist = []
   y_dist = []
   dist = []
   last_x = None
   last_y = None
   gap_frames = []

   median_frame = cv2.convertScaleAbs(np.median(np.array(crop_frames), axis=0))
   median_frame = cv2.GaussianBlur(median_frame, (7, 7), 0)

   #(dom_dir, quad, ideal_pos, ideal_roi_big_img) = get_movement_info(meteor, 10, 10)
   dom_dir, x_dir, y_dir = get_move_info(meteor, 10, 10)
   past_cnts = []

   dist_x, dist_y, med_x, med_y = get_dist_info(crop_frames, ofns, oxs, oys)


   # redraw the frames filling in est position for all frames and gap frames based on the start x,y and med_dist
   nfns = []
   nxs = []
   nys = []
   exs = []
   eys = []
   start_x = oxs[0]
   start_y = oys[0] 
   c = 0
   ic = 0
   for i in range(ofns[0], ofns[-1]+1):
      ex = int(start_x+med_x*ic)
      ey = int(start_y+med_y*ic)
      exs.append(ex)
      eys.append(ey)

      if i in ofns:
         ox = oxs[c]
         oy = oys[c]
         xd = ox - ex
         yd = oy - ey
         if xd > 200:
            #nxs.append(ex)
            nxs.append(ox)
         else:
            nxs.append(ox)
         if yd > 200:
            #nys.append(ey)
            nys.append(oy)
         else:
            nys.append(oy)
         c += 1
         ic += 1
      else:
         nxs.append(ex)
         nys.append(ey)
         ic += 1
      nfns.append(i)
      

   # now step through each frame and look for a cnt near the point.  
   # if you find one, update the shift_x, shift_y 
   new_cnts = []
   past_cnts = []
   c = 0
   for i in range(nfns[0], nfns[-1]+1):
      frame = crop_frames[i]
     
      (show_frame, sub_frame, show_subframe, thresh_img, avg_val, max_val, thresh_val) = make_subframe(frame, median_frame,2,past_cnts,dom_dir,x_dir,y_dir)
      off_frame = check_off_frame(frame, nxs[c]-cx1, nys[c]-cy1, 10, 10)
      if off_frame == 1:
         
         new_cnts.append(None)
         continue
      cnts = get_roi_cnts(meteor, frame, median_frame, nxs[c]-cx1, nys[c]-cy1, dom_dir, x_dir, y_dir)
      new_cnts.append(cnts)
      if cnts is not None:
         # update the final x,y for the 'leading edge' and blob center 
         # BLOB CENTER X,Y
         nxs[c] = cnts[0] + int(cnts[2]/2)
         nys[c] = cnts[1] + int(cnts[3]/2)
         # LEADING X,Y 
         lcx, lcy = get_leading_cnt(dom_dir, x_dir, y_dir, cnts[0], cnts[1], cnts[2], cnts[3])
         past_cnts.append(cnts)
      else:
         lcy = None
         lcx = None
         past_cnts.append((nxs[c],nys[c],10,10))
      #if lcy is not None:
      #   cv2.circle(frame,(lcx, lcy), 2, (0,0,255), 1)
      #cv2.circle(frame,(nxs[c], nys[c]), 10, (255,255,255), 1)
      #cv2.imshow('final-check-new_cnts', frame)
      #cv2.waitKey(30)
      c += 1


   status, nfns, nxs, nys, new_cnts = check_last_frame(nfns, nxs, nys, new_cnts)
   status, nfns, nxs, nys, new_cnts = check_last_frame(nfns, nxs, nys, new_cnts)
   status, nfns, nxs, nys, new_cnts = check_last_frame(nfns, nxs, nys, new_cnts)
   status, nfns, nxs, nys, new_cnts = check_last_frame(nfns, nxs, nys, new_cnts)

   # We should be almost done here just check to see how it looks and apply the leading x,y area?
   c = 0
   leading_xs = []
   leading_ys = []
   for i in range(nfns[0], nfns[-1]+1):
      frame = crop_frames[i]
      show_frame = cv2.cvtColor(frame,cv2.COLOR_GRAY2BGR)
      x = nxs[c]
      y = nys[c]
      if new_cnts[c] is not None:
         sx, sy, cw, ch = new_cnts[c]
         #cx = x - (sx -50)
         #cy = y - (sy -50)
         cx = x
         cy = y
      else:
         cx = x
         cy = y
         cw = 10
         ch = 10
      leading_xs.append(cx)
      leading_ys.append(cy)
      c += 1
      #cv2.rectangle(show_frame, (cx-2, cy-2), (cx+2, cy+2), (255,0,0), 1, cv2.LINE_AA) 
      #cv2.imshow('final final', show_frame)
      #cv2.waitKey(30)
   return(nfns, nxs,nys,new_cnts)


def check_last_frame(fns, xs, ys, new_cnts):
   lf = len(fns) - 1
   if new_cnts[lf] is None:
      fns.pop(lf)
      xs.pop(lf)
      ys.pop(lf)
      new_cnts.pop(lf)
      status = 0
   else:
      status = 1
   return(status, fns, xs, ys, new_cnts)

def block_past_cnts(img, cnts):
   for x,y,w,h in cnts:
      img[y:y+h,x:x+w] = 0
   return(img)


def make_subframe(frame, median_frame, thresh_div=2, past_cnts=None,dom_dir=None,x_dir=None,y_dir=None):
   show_frame = frame.copy()
   show_frame = cv2.cvtColor(show_frame,cv2.COLOR_GRAY2BGR)
   subframe = cv2.subtract(frame, median_frame)
   print("DOM:", dom_dir, x_dir, y_dir)
   print("PAST CNT:", past_cnts)
   if past_cnts is not None:
      for cnt in past_cnts:
         if cnt is not None:
            x,y,w,h = cnt
            if dom_dir is None:
               subframe[y:y+h,x:x+w] = 0
            else:
               if dom_dir == "x":
                  if x_dir == "right_to_left":
                     subframe[0:subframe.shape[0],x:subframe.shape[1]] = 0
                  else:
                     print("XY CNT:", x,y,w,h)
                     subframe[y:y+h,0:x] = 0
   cv2.imshow("SUB", subframe)
   cv2.waitKey(30)

   avg_val = np.mean(subframe)
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(frame)
   thresh = max_val - int(max_val / thresh_div)
   thresh = find_best_thresh(subframe, max_val)
   _, threshold = cv2.threshold(subframe.copy(), thresh, 255, cv2.THRESH_BINARY)

   cnts = get_contours_in_image(threshold)
   print("LEN CNTS:", len(cnts))
   if len(cnts) == 0:
      thresh = thresh - 10
      _, threshold = cv2.threshold(subframe.copy(), thresh, 255, cv2.THRESH_BINARY)
      cnts = get_contours_in_image(threshold)
      print("NEW LEN CNTS:", len(cnts))
   if len(cnts) > 1:
      thresh = thresh + 10
      _, threshold = cv2.threshold(subframe.copy(), thresh, 255, cv2.THRESH_BINARY)
      cnts = get_contours_in_image(threshold)
      print("NEW LEN CNTS:", len(cnts))


   show_subframe = cv2.cvtColor(subframe,cv2.COLOR_GRAY2BGR)

   return(show_frame, subframe, show_subframe, threshold, avg_val, max_val, threshold)

def find_best_thresh(subframe, thresh):
   tvals = []
   tvals2 = []
   last_cnts = None
   # starting at max val lower thresh until there is more than 1 cnt, the step before this is the ideal thresh
   for i in range(0, 50):
      thresh = thresh - 5
      _, threshold = cv2.threshold(subframe.copy(), thresh, 255, cv2.THRESH_BINARY)
      cnts = get_contours_in_image(threshold)
      last_thresh = thresh
      last_cnts = len(cnts)
      if len(cnts) <= 1:
         tvals.append((thresh,len(cnts)))
      elif len(cnts) == 2:
         tvals2.append((thresh,len(cnts)))
      #print("THRESH:", thresh, last_thresh, len(cnts), last_cnts)
      if thresh < 5:
         break
   if len(tvals) > 0:
      temp = sorted(tvals, key=lambda x: (x[0]), reverse=False)
   elif len(tvals2) > 0:
      temp = sorted(tvals2, key=lambda x: (x[0]), reverse=False)
   else:
      # NO BEST THRESH
      return(20)

   best_thresh = temp[0][0]
   print("BEST THRESH!", best_thresh)
   return(best_thresh)


def refine_all_meteors(day, json_conf):
   mfs = glob.glob("/mnt/ams2/meteors/" + day + "/*.json")
   for mf in mfs:
      if "reduced" not in mf:
         print("REFINE:", mf)
         refine_meteor(mf, json_conf)

def refine_meteor(meteor_file, json_conf):
   console_image = np.zeros((720,1280),dtype=np.uint8)
   color_console_image = np.zeros((720,1280,3),dtype=np.uint8)
   leading_xs = []
   leading_ys = []
   intensity = []
   max_pxs = []
   js = load_json_file(meteor_file)

   # first make sure we are dealing with a  'good' meteor. 
   # if detection info is missing re-decect and confirm the crop is good.
   if "hd_trim" in js:
      hd_trim = js['hd_trim']
      sd_trim = meteor_file.replace(".json", ".mp4")
      hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hd_trim, json_conf, 0, 0, [], 1,[])
   if "cropbox_1080" in js:
      print("CROP:", js['cropbox_1080'])
      cx1, cy1, cx2, cy2, mx1, mx2 = js['cropbox_1080']
   else:
      print("NO CROP BOX!", meteor_file)
      exit()
  
   # make the crop frames 
   crop_file = hd_trim.replace(".mp4", "-crop.mp4")
   if True:
      crop_frames = []
      for hd_frame in hd_frames:
         cf = hd_frame[cy1:cy2,cx1:cx2]
         crop_frames.append(cf)
      SHOW = 0
      hd_objects, crop_frames = detect_meteor_in_clip(crop_file, crop_frames, 0, cx1, cy1, 1)
      hd_meteors = []
      for id in hd_objects:
         hd_objects[id] = analyze_object(hd_objects[id], 1,1)
         hd_objects[id]['cropbox_1080'] = js['cropbox_1080']
         if hd_objects[id]['report']['meteor'] == 1:
            hd_meteors.append(hd_objects[id])

   # make sure we have a meteor here. If not try to detect in the SD obj. 
   # TODO: still need to handle re-crop from the SD
   if len(hd_meteors) == 0:
      print("NO METEORS? MAYBE CROP LOCATION WAS BAD. TRY REFINDING IT. ")
      sd_frames,sd_color_frames,sd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(sd_trim, json_conf, 0, 1, [], 1,[])
      sd_objects, frames = detect_meteor_in_clip(sd_trim, sd_frames, 0, 0, 0, 0)
      return(None, None, None, None) 
      for id in hd_objects:
         print(hd_objects[id]['ofns'])
         print(hd_objects[id]['oint'])
         print(hd_objects[id]['report'])
         # log failure

   sfn = hd_meteors[0]['ofns'][0]
   lfn = hd_meteors[0]['ofns'][-1]
   print("FIRST/LAST:", sfn, lfn)


   # since we might be dealing with more than 1 meteor per file, 
   # process all meteors in the array.

   for meteor in hd_meteors:
      # check to see if our crop is ok, if not we need to redo it. 
      #print("OXS:", meteor['oxs'][0] - cx1, cx2-cx1)
      #print("OYS:", meteor['oys'][0] - cy1, cy2-cy1)
      #print("OXS:", meteor['oxs'][-1] - cx1)
      #print("OYS:", meteor['oys'][-1] - cy1)

      nfns, nxs, nys, new_cnts = refine_meteor_points(meteor, crop_frames, json_conf)


   print("REFINED METEOR:")
   print("NFNS:", nfns)
   print("NXS:", nxs)
   print("NYS:", nys)
   print("NCNT:", new_cnts)
   meteor['final'] = {}
   meteor['final']['fns'] = nfns
   for i in range(0, len(nfns)):
      if new_cnts[i] is not None:
         new_cnts[i][0] + cx1
         new_cnts[i][1] + cy1
         nxs[i] += cx1
         nys[i] += cy1
   meteor['final']['xs'] = nxs
   meteor['final']['ys'] = nys
   meteor['final']['cnts'] = new_cnts

   dist_x, dist_y, med_x, med_y = get_dist_info(crop_frames, nfns, nxs, nys)
   print("XD:", med_x, dist_x)
   print("YD:", med_y, dist_y)

   (dom_dir, quad, ideal_pos, ideal_roi_big_img) = get_movement_info(meteor, 10, 10)
   dom_dir, x_dir, y_dir = get_move_info(meteor, 10, 10)

   past_cnts = []
   median_frame = cv2.convertScaleAbs(np.median(np.array(hd_frames), axis=0))
   roi_size = 25 
   for i in range(0, len(nfns)):
      fn = nfns[i]
      frame= hd_frames[fn]
      x = nxs[i]
      y = nys[i]
      if new_cnts[i] is not None:
         cnt_w = new_cnts[i][2]
         cnt_h = new_cnts[i][3]
      else:
         cnt_w = 10
         cnt_h = 10


      rx1,ry1,rx2,ry2 = bound_cnt(x,y,frame.shape[1],frame.shape[0], roi_size)
      r_w = rx2 - rx1
      r_h = ry2 - ry1
      scale_x = 300 / (rx2-rx1)
      scale_y = 300 / (ry2-ry1)
      if cnt_h > cnt_w:
         line_w = int(int(cnt_w * scale_x) )
      else:
         line_w = int(int(cnt_h * scale_y) )
      adj_x = int(int(cnt_w/ 4) * scale_x)
      adj_y = int(int(cnt_h/ 4) * scale_y)

      (dom_dir, quad, ideal_pos, ideal_roi_big_img) = get_movement_info(meteor, int(cnt_w*scale_x), int(cnt_h*scale_y)) 
      # line should change based on x/y dir??
      adj_y = 0
      adj_x = 0
      if x_dir == 'left_to_right':
         # add the adj
         line_start_x = 150 - int(adj_x)
      else:
         line_start_x = 150 + int(adj_x)
      if y_dir == 'up_to_down':
         # add the adj
         line_start_y = 150 - int(adj_y)
      else:
         line_start_y = 150 + int(adj_y)
   
      line_w = 5
      med_multi = get_med_multi(line_start_x, line_start_y, med_x,med_y, max(cnt_w, cnt_h))
      
      cv2.line(ideal_roi_big_img, (line_start_x,line_start_y), (line_start_x-int(med_x*3),line_start_y-int(med_y*3)), (255,255,255), line_w)
      (show_frame, sub_frame, show_subframe, thresh_img, avg_val, max_val, thresh_val) = make_subframe(frame, median_frame,2,past_cnts,dom_dir,x_dir,y_dir)
      aroi_x1, aroi_y1, aroi_x2, aroi_y2, shift_x, shift_y = align_images(thresh_img, ideal_roi_big_img, rx1,ry1,rx2,ry2,cnt_w,cnt_h,dom_dir,x_dir,y_dir)
      if -10 <= shift_x < 10 and -10 <= shift_y <= 10:
         print("ADJUST SHIFT", shift_x, shift_y)
         nxs[i] = nxs[i] + shift_x
         nys[i] = nys[i] + shift_y
      if new_cnts[i] is not None:
         past_cnts.append((new_cnts[i][0]+cx1,new_cnts[i][1]+cy1,new_cnts[i][2],new_cnts[i][3]))
      else:
         past_cnts.append((nxs[i],nys[i],10,10))
   
   meteor['final']['xs'] = nxs
   meteor['final']['ys'] = nys

   make_roi_comp_img(hd_color_frames, meteor)

def get_med_multi(line_start_x, line_start_y, med_x,med_y, max_size):
   print("GET MED MULTI:")

def make_roi_comp_img(frames, meteor):

   stack_img = stack_frames(frames)
   stack_img.setflags(write=1) 
   fns = meteor['final']['fns']
   xs = meteor['final']['xs']
   ys = meteor['final']['ys']
   cnts = meteor['final']['cnts']
   dc = 0
   # determine ROI big size based on number of frames
   tf = len(fns)
   roi_size = 25 
   roi_big_size = 100 
   i_per_row = int(1920 / roi_big_size)
   i_per_row = i_per_row - 1
   rows = int(tf / i_per_row)
   rows += 1
   comp_h = rows * roi_big_size
   rimgs = []
   roi_row = np.zeros((comp_h,1920,3),dtype=np.uint8)
   rc = 0
   ic = 0
   for i in range(fns[0], fns[-1]+1):
      frame = frames[i]
      y_start = rc * roi_big_size
      fn = fns[dc]
      x = xs[dc]
      y = ys[dc]
      stack_img[y,x] = [0,0,255]
      rx1,ry1,rx2,ry2 = bound_cnt(x,y,frame.shape[1],frame.shape[0], roi_size)
      cnt = cnts[dc]
      rimg = frame[ry1:ry2,rx1:rx2]
      sx = ic * roi_big_size 
      ex = (ic * roi_big_size) + roi_big_size

      rimg_big = cv2.resize(rimg, (roi_big_size, roi_big_size))
      roi_scale_x = roi_big_size / rimg.shape[1] 
      roi_scale_y = roi_big_size / rimg.shape[0] 
      print("IMG:", rimg_big.shape)
      #roi_row[0:100,0:100] = rimg_big
      cv2.line(rimg_big, (0,50), (100,50), (100,100,100), 1)
      cv2.line(rimg_big, (50,0), (50,100), (100,100,100), 1)
      roi_row[y_start:y_start+roi_big_size,sx:ex] = rimg_big
      


      rimgs.append(rimg_big)
      if ic >= i_per_row:
         rc += 1
         ic = 0
      else:
         ic += 1

      dc += 1
   fh = rows * roi_big_size
   fy = 1080 - fh
   fy2 = 1080
   stack_img[fy:fy2,0:1920] = roi_row
   cv2.imshow('FINAL STACK', stack_img)
   cv2.waitKey(0)
   

   

def old_delete():
   fn = 0
   mc = 0
   lxs = []
   lys = []
   print("LEN FRAMES:", len(meteor['ofns']))
   print("LEN LEADING XS:", len(lead_xs))
   for frame in hd_color_frames:
      if meteor['ofns'][0] <= fn < meteor['ofns'][-1] :
         if fn in meteor['ofns']:
            color_console_image = np.zeros((720,1280,3),dtype=np.uint8)
            if len(meteor['ofns']) == len(lead_xs):
               lx = lead_xs[mc] + cx1
               ly = lead_ys[mc] + cy1
               print("CROP TOP:", cx1, cy1)
               print("ORG POINTS:", meteor['oxs'][mc],  meteor['oys'][mc])
               print("LEAD POINTS:", lx,  ly)
            else:
               # leading x,y refine didn't work?
               print(meteor['ofns'])
               print(meteor['oxs'])
               print(meteor['oys'])
               lx = meteor['oxs'][mc]
               ly = meteor['oys'][mc]
            lxs.append(lx)
            lys.append(ly)
            rx1,ry1,rx2,ry2 = bound_cnt(lx,ly,frame.shape[1],frame.shape[0], 10)
            print("ROI", ry1,ry2,rx1,rx2)
            cv2.rectangle(frame, (lx-5, ly-5), (lx+5, ly+5), (0,0,255), 1, cv2.LINE_AA)
            cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (255,255,0), 1, cv2.LINE_AA)
            cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (255,0,0), 1, cv2.LINE_AA)
            # orig meteor x,y
            cv2.rectangle(frame, (meteor['oxs'][mc]-2, meteor['oys'][mc]-2), (meteor['oxs'][mc]+2, meteor['oys'][mc]+2), (0,255,0), 1, cv2.LINE_AA)

            full_frame_sm = cv2.resize(frame, (640, 360))
            crop_frame = frame[cy1:cy2,cx1:cx2]
            crop_frame = cv2.resize(crop_frame, (640, 360))
            roi_frame = frame[ry1:ry2,rx1:rx2]
            print("ROI", ry1,ry2,rx1,rx2)
          
            roi_frame = cv2.resize(roi_frame, (300, 300))
            color_console_image[0:360,0:640] = full_frame_sm
            color_console_image[0:360,640:1280] = crop_frame 
            color_console_image[360:660,490:790] = roi_frame 
            cv2.imshow('Final', color_console_image)
            cv2.waitKey(800)
            mc += 1
         else:
            print("GAP / MISSING FRAME DETECTED:", fn)
      fn += 1
   return(lxs, lys, intensity, max_pxs)

def align_images(full_frame, ideal_roi, rx1,ry1,rx2,ry2,orig_w,orig_h,dom_dir,x_dir,y_dir) :

   orig_x = int((rx1 + rx2)/2)
   orig_y = int((ry1 + ry2)/2)

   poly = np.zeros(shape=(2,), dtype=np.float64)
   shift_x = 0
   shift_y = 0



   #ideal_roi[0:300,149:151] = 255
   #ideal_roi[149:151,0:300] = 255
   axis_reduce = 0
   if axis_reduce == 1:
   
      # align the y with center
      lowest_sub  = 9999999999
      best_shift_y = 0
      for i in range (-30,30):
         if ry1 + i > 0 and ry2+i < full_frame.shape[0]:
            new_roi= full_frame[ry1+i:ry2+i,rx1+0:rx2+0]
            new_roi_big = cv2.resize(new_roi, (300, 300))
            sub = cv2.subtract(ideal_roi, new_roi_big)
            if np.sum(sub) < lowest_sub:
               lowest_sub = np.sum(sub)
               best_shift_y = i
            #cv2.imshow('sub', sub)
            #cv2.waitKey(30)

      # align the x with center
      lowest_sub  = 9999999999
      best_shift_x = 0
      for i in range (-30,30):
         if rx1 + i > 0 and rx2+i < full_frame.shape[1]:
            new_roi= full_frame[ry1:ry2,rx1+i:rx2+i]
            new_roi_big = cv2.resize(new_roi, (300, 300))
            sub = cv2.subtract(ideal_roi, new_roi_big)
            if np.sum(sub) < lowest_sub:
               lowest_sub = np.sum(sub)
               best_shift_x = i
            #cv2.imshow('sub', sub)
            #cv2.waitKey(30)


   #rx1 = rx1 + best_shift_x
   #ry1 = ry1 + best_shift_y
   #rx2 = rx2 + best_shift_x
   #ry2 = ry2 + best_shift_y
   
   # REDUCE BOTH AXIS
   res = scipy.optimize.minimize(reduce_align_roi_images, poly, args=(full_frame,ideal_roi,rx1,ry1,rx2,ry2,orig_x,orig_y,orig_w,orig_h,dom_dir,x_dir,y_dir), method='Nelder-Mead')
   new_poly = res['x']
   shift_x = int(new_poly[0] * ((rx1+1)**2))
   shift_y = int(new_poly[1] * ((ry1+1)**2))
   print("NEW SHIFT:", shift_x, shift_y)

   new_rx1 = rx1+shift_x
   new_ry1 = ry1+shift_y
   new_rx2 = rx2+shift_x
   new_ry2 = ry2+shift_y

   #cv2.rectangle(full_frame, (rx1, ry1), (rx2, ry2), (100,100,100), 1, cv2.LINE_AA)
   #cv2.rectangle(full_frame, (new_rx1, new_ry1), (new_rx2, new_ry2), (100,100,255), 1, cv2.LINE_AA)
   #cv2.imshow('pepe', full_frame)
   #cv2.waitKey(30)





   return(new_rx1,new_ry1,new_rx2,new_ry2, shift_x, shift_y)


def get_leading_corner(x,y,w,h,dom_dir, x_dir, y_dir):
   if x_dir == "right_to_left":
      corner_x = x 
   elif x_dir == "left_to_right":
      corner_x = x + w
   else:
      corner_x = x + int(w/2)
   if y_dir == "up_to_down":
      corner_y = y + h 
   elif y_dir == "down_to_up":
      corner_y = y 
   else:
      corner_y = y + int(h/2)
   return(corner_x, corner_y)

def reduce_align_roi_images(poly, full_frame, ideal_roi, rx1,ry1,rx2,ry2, x,y,w,h,dom_dir,x_dir,y_dir):
   #shift image per poly and then re-subtract to minimize alignment 
   show_img = np.zeros((300,900),dtype=np.uint8)
   shift_x = int(poly[0] * ((rx1+1)**2))
   shift_y = int(poly[1] * ((ry1+1)**2))

   org_roi= full_frame[ry1:ry2,rx1:rx2]
   org_roi_big = cv2.resize(org_roi, (300, 300))
   org_roi_val = np.sum(org_roi_big)

   mx = int((rx1+shift_x+rx2+shift_x)/2)
   my = int((ry1+shift_y+ry2+shift_y)/2)
   corner_x, corner_y = get_leading_corner(x-rx1+shift_x,y-ry1+shift_y,w,h,dom_dir,x_dir,y_dir)
   center_dist_from_center = calc_dist((mx-rx1,my-ry1),(25,25))
   corner_dist_from_center = calc_dist((corner_x,corner_y),(25,25))

   #print("CENTER:", mx-rx1, my-ry1, center_dist_from_center)
   #print("CORNER:", corner_x, corner_y, corner_dist_from_center)

   if center_dist_from_center <= 0:
      center_dist_from_center = 1

   sf_y1 = ry1+shift_y 
   sf_y2 = ry2+shift_y
   sf_x1 = rx1+shift_x
   sf_x2 = rx2+shift_x
   if sf_x1 <= 0:
      print("BOUNDS PROB x1", shift_x, shift_y)
      print("SF 1 X/Y", sf_x1, sf_y1)
      sf_x1 = 0
      #exit()
   if sf_x2 >= full_frame.shape[1]:
      sf_x1 = full_frame.shape[0] - (sf_x2 - sf_x1)
      sf_x2 = full_frame.shape[0]
      print("BOUNDS PROB x2", sf_x1, sf_x2)
      #exit()
   if sf_y1 <= 0:
      print("BOUNDS PROB y1")
      sf_y1 = 0
      #exit()
   if sf_y2 >= full_frame.shape[0]:
      print("BOUNDS PROB y2", sf_y2, full_frame.shape)
      sf_y1 = full_frame.shape[0] - (sf_y2 - sf_y1)
      sf_y2 = full_frame.shape[0]
      #exit()
   #cv2.imshow('pepe', full_frame)
   #cv2.waitKey(30)
 
   new_roi= full_frame[sf_y1:sf_y2,sf_x1:sf_x2]

   new_roi_big = cv2.resize(new_roi, (300, 300))

   sub = cv2.subtract(ideal_roi, new_roi_big)
   new_val = np.sum(new_roi_big)  
   dif_val = org_roi_val - new_val
   sub_val = np.sum(sub) 

   cv2.line(sub, (0,150), (int(300),int(150)), (100,100,100), 1)
   cv2.line(sub, (150,0), (int(150),int(300)), (100,100,100), 1)

   show_img[0:300,0:300] = ideal_roi
   show_img[0:300,300:600] = new_roi_big
   show_img[0:300,600:900] = sub
   if center_dist_from_center > 20:
      center_dist_from_center = 999

   score = sub_val + (center_dist_from_center**2)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(100)

   return(score)


def get_move_info(meteor, cnt_w, cnt_h):
   moving_x = meteor['oxs'][0] - meteor['oxs'][-1]
   moving_y = meteor['oys'][0] - meteor['oys'][-1]
   if abs(moving_x) > abs(moving_y):
      dom_dir = "x"
   else:
      dom_dir = "y"
   if moving_x > 0:
      x_dir = "right_to_left"
   else:
      x_dir = "left_to_right"
   if moving_y > 0:
      y_dir = "down_to_up"
   else:
      y_dir = "up_to_down"
   if moving_x == 0:
      x_dir = None
   if moving_y == 0:
      y_dir = None

   qw = int(cnt_w/3)
   qh = int(cnt_h/3)

   return(dom_dir, x_dir, y_dir)


def get_movement_info(meteor, cnt_w, cnt_h):
   moving_x = meteor['oxs'][0] - meteor['oxs'][-1]
   moving_y = meteor['oys'][0] - meteor['oys'][-1]
   if abs(moving_x) > abs(moving_y):
      dom_dir = "x"
   else:
      dom_dir = "y"
   if moving_x > 0:
      x_dir = "right_to_left"
   else:
      x_dir = "left_to_right"
   if moving_y > 0:
      y_dir = "down_to_up"
   else:
      y_dir = "up_to_down"
   if moving_x == 0:
      x_dir = None
   if moving_y == 0:
      y_dir = None

   qw = int(cnt_w/3)
   qh = int(cnt_h/3)
   if y_dir is None:
      # The meteor is moving perfectly horizontally
      ideal_y1 = 150 - qh
      ideal_y2 = 150 + qh
      y_quad_loc = "center"
   if x_dir is None:
      # The meteor is moving perfectly vertically 
      ideal_x1 = 150 - qw
      ideal_x2 = 150 + qw
      x_quad_loc = "center"

   # based on the dom dir and x,y movement choose the best ROI quad for placing the meteor
   if x_dir == "right_to_left":
      x_quad_loc = "left" 
      ideal_x1 = 150 - qw
      ideal_x2 = 150 - qw + cnt_w
   if x_dir == "left_to_right":
      x_quad_loc = "right" 
      ideal_x1 = 150 + qw - cnt_w
      ideal_x2 = 150 + qw
   if y_dir == "up_to_down":
      y_quad_loc = "top"
      ideal_y1 = 150+qh - cnt_h
      ideal_y2 = 150+qh
   if y_dir == "down_to_up":
      y_quad_loc = "bottom"
      ideal_y1 = 150 - qh
      ideal_y2 = 150 - qh + cnt_h
   

   ideal = [ideal_x1, ideal_y1, ideal_x2, ideal_y2]
   quad = [x_quad_loc, y_quad_loc]

   ideal_img = np.zeros((300,300),dtype=np.uint8)
   #ideal_img[ideal_y1:ideal_y2, ideal_x1:ideal_x2] = 255
   #cv2.imshow("IDEAL", ideal_img)
   #cv2.waitKey(0)
   return(dom_dir, quad, ideal, ideal_img)


def get_best_cnt(cnts, meteor):
   moving_x = meteor['oxs'][0] - meteor['oxs'][-1]
   moving_y = meteor['oys'][0] - meteor['oys'][-1]
   if abs(moving_x) > abs(moving_y):
      dom_dir = "x"
   else: 
      dom_dir = "y"
   if moving_x > 0:
      x_dir = "right_to_left"
   else:
      x_dir = "left_to_right"
   if moving_y > 0:
      y_dir = "down_to_up"
   else:
      y_dir = "up_to_down"
   if moving_x == 0:
      x_dir = None
   if moving_y == 0:
      y_dir = None

   #print("Dom direction:", dom_dir)
   #print("Moving X:", moving_x)
   #print("Moving Y:", moving_y)
   #print("X Dir:", x_dir)
   #print("Y DirY:", y_dir)
   # Biggness override - if one cnt is way bigger than all the others (3x or more) 
   # use that as the best / dom 
   temp = sorted(cnts, key=lambda x: (x[2]+x[3]), reverse=True)
   best_cnt = temp[0]
   return([best_cnt], dom_dir, x_dir, y_dir)

   if dom_dir == "x":
      if x_dir == "right_to_left":
         # pick cnt with lowest x val 
         temp = sorted(cnts, key=lambda x: x[0], reverse=False)
         best_cnt= temp[0]
         return([best_cnt], dom_dir, x_dir, y_dir)
      else: 
         temp = sorted(cnts, key=lambda x: x[0], reverse=True)
         best_cnt= temp[0]
         return([best_cnt], dom_dir, x_dir, y_dir)

   if dom_dir == "y":
      if y_dir == "top_to_bottom":
         # pick cnt with highest y val 
         temp = sorted(cnts, key=lambda x: x[1], reverse=True)
         best_cnt= temp[0]
         return([best_cnt], dom_dir, x_dir, y_dir)
      else: 
         temp = sorted(cnts, key=lambda x: x[1], reverse=False)
         best_cnt= temp[0]
         return([best_cnt], dom_dir, x_dir, y_dir)

   
   # if we made it this far, then the x or y dir is perfectly veritical or horizontal
   # in this case we should use the dom dir val
   # figure out later

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
   return(object)
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

   print("BAD FRAMES:", bad_frames)
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
   #print("Start analyze")
   if hd == 0:
      # if we are working with an HD file we need to mute the HD Multipliers
      global HDM_X, HDM_Y
      HDM_X = 1
      HDM_Y = 1

   bad_items = []
   good_items = []

   #if "report" not in object:
   obj_id = object['obj_id'] 
   if True:
      object['report'] = {}
      object['report']['non_meteor'] = 0
      object['report']['meteor'] = 0
      object['report']['bad_items'] = []


   # basic initial tests for vals-detect/stict = 0, if these all pass the clip should be video detected
   object['report']['cm'] = obj_cm(object['ofns'])
   # consecutive motion filter 
   if object['report']['cm'] < 3:
      object['report']['non_meteor'] = 1
      object['report']['meteor'] = 0

   object['report']['unq_perc'], object['report']['unq_points'] = unq_points(object)
   if object['report']['unq_points'] > 3 and object['report']['unq_perc'] < .6 :
      object['report']['non_meteor'] = 1
      object['report']['meteor'] = 0
      object['report']['bad_items'].append("Unq Points/Perc too low. " + str(object['report']['unq_points']) + " / " + str(object['report']['unq_perc']) )
   if object['report']['unq_points']  <= 3 and object['report']['unq_perc'] < .8 :
      object['report']['non_meteor'] = 1
      object['report']['meteor'] = 0
      object['report']['bad_items'].append("Unq Points/Perc too low. " + str(object['report']['unq_points']) + " / " + str(object['report']['unq_perc']) )

   object['report']['object_px_length'], object['report']['line_segments'], object['report']['x_segs'], object['report']['ms'], object['report']['bs'] = calc_line_segments(object)
   med_seg = np.median(object['report']['line_segments'])
   bad_segs = 0
   for seg in object['report']['line_segments']:
      if seg <= 0:
         bad_segs += 1
      med_diff = abs(med_seg - seg)
      if med_diff > med_seg * 3:
         bad_segs += 1

   bad_seg_perc = bad_segs / len(object['oxs'])
   if bad_seg_perc > .5:
      object['report']['non_meteor'] = 1
      object['report']['meteor'] = 0
      object['report']['class'] = "unknown"
      object['report']['bad_seg_perc'] = bad_seg_perc
      object['report']['bad_items'].append("Bad seg perc too high. " + str(object['report']['bad_seg_perc']) )

   object['report']['min_max_dist'] = calc_dist((min(object['oxs']), min(object['oys'])), (max(object['oxs']),max(object['oys']) ))

   #object = clean_bad_frames(object)


   # ANG DIST / VEL
   # HD PXSCALE = 155 arcseconds per pixel 
   hd_pxscale = 155
   pxscale = 155
   if hd == 0:
      sd_pxscale = hd_pxscale * (2.25)
      pxscale = sd_pxscale

   #if object['report']['non_meteor'] == 0:
   if True:
      ang_dist, ang_vel = ang_dist_vel(object['oxs'],object['oys'], [],[],pxscale)
      object['report']['ang_dist'] = ang_dist
      object['report']['ang_vel'] = ang_vel

      # filter out detections that don't match ang vel or ang sep desired values
      if float(ang_vel) > .5 and float(ang_vel) < 80:
         foo = 1
      else:
         object['report']['non_meteor'] = 1
         object['report']['meteor'] = 0
         object['report']['bad_items'].append("bad ang vel: " + str(ang_vel))

      if ang_dist < .3:
         object['report']['non_meteor'] = 1
         object['report']['meteor'] = 0
         object['report']['bad_items'].append("bad ang sep: " + str(ang_dist))



   if (object['report']['unq_perc'] < .1 or object['report']['min_max_dist'] <= 3) and len(object['oxs']) > 3:
      object['report']['class'] = "star"
   else:
      if "class" not in object['report']:
         object['report']['class'] = "unknown"



   if strict == 0:
      if object['report']['non_meteor'] == 0 :
         object['report']['meteor'] = 1 
      return(object)

   


   object['report']['big_perc'] = big_cnt_test(object, hd)
   if object['report']['big_perc'] > .5:
      object['report']['non_meteor'] = 1
      object['report']['meteor'] = 0
      object['report']['bad_items'].append("Big Perc % too high. " + str(object['report']['big_perc']))

   # meteor dir tests
   if len(object['ofns']) > 4:
      object['report']['dir_test_perc'] = meteor_dir_test(object['oxs'],object['oys'])
   else:
      object['report']['dir_test_perc'] = 1

   # NOT SURE THIS WORKS?!
   if object['report']['dir_test_perc'] < .80:
      object['report']['non_meteor'] = 1
      object['report']['meteor'] = 0
      object['report']['bad_items'].append("% direction too low. " + str(object['report']['dir_test_perc']))

   # intensity
   #if sum(object['oint']) < 0:
      # DISABLED FOR NOW
   #   object['report']['non_meteor'] = 0
   #   object['report']['bad_items'].append("Negative intensity, possible bird. ")
    
                                         
   (max_times, pos_neg_perc, perc_val) = analyze_intensity(object['oint'])
   object['report']['int_pos_neg_perc'] = pos_neg_perc
   object['report']['int_max_times'] = max_times
   object['report']['pos_perc'] = perc_val
   if pos_neg_perc < .5:
      object['report']['non_meteor'] = 1
      object['report']['meteor'] = 0
      object['report']['bad_items'].append("% pos/neg intensity too low. " + str(object['report']['int_pos_neg_perc']))


   if object['report']['non_meteor'] == 0 :
      print("*********** METEOR DETECTED *********", obj_id )
      object['report']['meteor'] = 1
      object['report']['class'] = "meteor"

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

def min_cnt_dist(x,y,w,h,tx,ty,tw,th):
   ds = []
   ctx = tx+int(tw/2)
   cty = ty+int(th/2)
   cx = x+int(w/2)
   cy = y+int(h/2)

   dist = calc_dist((x,y), (tx,ty))
   ds.append(dist)
   dist = calc_dist((x,y), (tx+tw,ty+th))
   ds.append(dist)
   dist = calc_dist((x+w,y+h), (tx,ty))
   ds.append(dist)
   dist = calc_dist((x+w,y+h), (tx+tw,ty+th))
   ds.append(dist)
   dist = calc_dist((cx,cy), (ctx,cty))
   ds.append(dist)
   dist = calc_dist((x,y), (ctx,cty))
   ds.append(dist)
   dist = calc_dist((x+w,y), (ctx,cty))
   ds.append(dist)
   dist = calc_dist((x,y+h), (ctx,cty))
   ds.append(dist)
   dist = calc_dist((x+w,y+h), (ctx,cty))
   ds.append(dist)
   return(min(ds))

def find_object(objects, fn, cnt_x, cnt_y, cnt_w, cnt_h, intensity=0, hd=0, sd_multi=1, cnt_img=None ):
   matched = {}
   if hd == 1:
      obj_dist_thresh = 75 
   else:
      obj_dist_thresh = 35

   center_x = cnt_x + int(cnt_w/2)
   center_y = cnt_y + int(cnt_h/2)

   found = 0
   max_obj = 0
   closest_objs = []
   dist_objs = []
   for obj in objects:
      if 'oxs' in objects[obj]:
         ofns = objects[obj]['ofns']
         oxs = objects[obj]['oxs']
         oys = objects[obj]['oys']
         ows = objects[obj]['ows']
         ohs = objects[obj]['ohs']
         if len(oxs) < 2:
            check = len(oxs)
         else:
            check = 2 
         for ii in range(0, check):
            oi = len(oxs) - ii - 1
            #oi = ii
            hm = int(ohs[oi] / 2)
            wm = int(ows[oi] / 2)
            lfn = int(ofns[-1] )
            #dist = calc_obj_dist((cnt_x,cnt_y,cnt_w,cnt_h),(oxs[oi], oys[oi], ows[oi], ohs[oi]))
            t_center_x = oxs[oi] + int(ows[oi]/2) 
            t_center_y = oys[oi] + int(ohs[oi]/2) 
            c_dist = calc_dist((center_x,center_y),(t_center_x, t_center_y))
            dist = min_cnt_dist(cnt_x,cnt_y,cnt_w,cnt_h,oxs[oi],oys[oi],ows[oi],ohs[oi])
            dist_objs.append((obj,dist))
            last_frame_diff = fn - lfn
            if "report" in objects[obj]:
               if objects[obj]['report']['class'] == "meteor" and len(objects[obj]['oxs']) > 3:
                  # only add this new point to the meteor if it is not equal to the last point and if the last_seg and current dist are reasonable.
                  last_x = objects[obj]['oxs'][-1]
                  last_y = objects[obj]['oys'][-1]
                  last_x2 = objects[obj]['oxs'][-2]
                  last_y2 = objects[obj]['oys'][-2]
                  last_seg_dist = calc_dist((last_x,last_y), (last_x2, last_y2))
                  this_seg_dist = calc_dist((last_x,last_y), (cnt_x, cnt_y))
                  abs_diff = abs(last_seg_dist - this_seg_dist)
                  #if last_x == cnt_x and last_y == cnt_y:
                  #   # don't add duplicate points to an existing meteor. (This might cause problems??)
                  #   continue
                  if abs_diff > last_seg_dist * 3:
                     # don't add points to meteors if they are more than 3x farther away than the last seg dist
                     continue
               if objects[obj]['report']['class'] == "star":
                  # only match object if dist is within 5 px
                  if dist > 5:
                     continue 


            if dist < obj_dist_thresh and last_frame_diff < 10:
               #if this is linked to a meteor only associate if the point is further from the start than the last recorded point
               found = 1
               found_obj = obj
               #if obj not in matched:
               closest_objs.append((obj,dist))
               matched[obj] = 1

      if obj > max_obj:
         max_obj = obj

   if len(closest_objs) > 1:

      ci = sorted(closest_objs , key=lambda x: (x[1]), reverse=False)
      found =1 
      found_obj = ci[0][0]
      #c = input("Continue")
      #exit()

   if found == 0:
      dist_objs = sorted(dist_objs, key=lambda x: (x[1]), reverse=False)
    
      obj_id = max_obj + 1
      #if obj_id > 10:
      #   cc = input("cont")
      #if obj_id > 20:
      #   c = input("Continue")
      objects[obj_id] = {}
      objects[obj_id]['obj_id'] = obj_id
      objects[obj_id]['ofns'] = []
      objects[obj_id]['oxs'] = []
      objects[obj_id]['oys'] = []
      objects[obj_id]['ows'] = []
      objects[obj_id]['ohs'] = []
      objects[obj_id]['oint'] = []
      objects[obj_id]['ofns'].append(fn)
      objects[obj_id]['oxs'].append(cnt_x)
      objects[obj_id]['oys'].append(cnt_y)
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
      if fn not in objects[found_obj]['ofns']:
         objects[found_obj]['ofns'].append(fn)
         objects[found_obj]['oxs'].append(cnt_x)
         objects[found_obj]['oys'].append(cnt_y)
         objects[found_obj]['ows'].append(cnt_w)
         objects[found_obj]['ohs'].append(cnt_h)
         objects[found_obj]['oint'].append(intensity)

   #objects[found_obj] = analyze_object_old(objects[found_obj], hd, sd_multi, 1)
   #if objects[found_obj]['report']['meteor_yn'] == 'Y':
   #   max_int = max(objects[found_obj]['oint'])
   #   if max_int > 25000:
   #      objects[found_obj]['report']['obj_class'] = "fireball"

   return(found_obj, objects)

def msk_fr(masks,frame):
   for msk in masks:
      mx1 = msk[0] 
      my1 = msk[1] 
      mx2 = msk[0] + msk[2]
      my2 = msk[1] + msk[3]
      frame[my1:my2,mx1:mx2] = [0]
   return(frame)

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
   
def re_detect(date):
   files = glob.glob("/mnt/ams2/meteors/" + date + "/*.json")
   data_dir = "/mnt/ams2/SD/proc2/" + date + "/data/" 
   for file in files:

      fn,dir= fn_dir(file)
      root = fn.split("-")[0]
      vals_file = data_dir + root + "-vals.json"
      mm_file = data_dir + root + "-maybe-meteors.json"
      cmd = "cd /home/ams/amscams/pythonv2/; ./flex-detect.py dv " + vals_file
      os.system(cmd)
      if cfe(mm_file):
         cmd = "cd /home/ams/amscams/pythonv2/; ./flex-detect.py vm " + mm_file 
         os.system(cmd)
      #exit() 

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

def find_hd(sd_trim_file, dur, meteor_start_frame=0):
   PIPE_OUT = PIPELINE_DIR + "IN/"
   if cfe(PIPE_OUT, 1) == 0:
      os.makedirs(PIPE_OUT)
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(sd_trim_file)
   sdfn = sd_trim_file.split("/")[-1]
   sd_trim_num = get_trim_num(sd_trim_file) 
   print("SD FILE TIME:", f_datetime)
   print("SD TRIM NUM:", sd_trim_num)
   extra_trim_sec = int(sd_trim_num) / 25
   print("EXTRA TRIM SECONDS:", sd_trim_num)
   sd_trim_start = f_datetime + datetime.timedelta(seconds=extra_trim_sec)
   if meteor_start_frame > 0:
      mext = (meteor_start_frame / 25) + extra_trim_sec
      meteor_event_start = f_datetime + datetime.timedelta(seconds=mext)

      sd_start_min_before = sd_trim_start + datetime.timedelta(seconds=-60)
      sd_start_min_after = sd_trim_start + datetime.timedelta(seconds=+60)
   else:
      meteor_event_start = sd_trim_start
      mext = extra_trim_sec

   # get the HD files within +/- 1 min of the SD trim start time for this cam
   print("SD TRIM START TIME:", sd_trim_start)
   print("SD METEOR START TIME:", meteor_event_start)
   date_wild = sd_trim_start.strftime("%Y_%m_%d_%H")
   #date_wild_before = sd_start_min_before.strftime("%Y_%m_%d_%H_%M")
   #date_wild_after = sd_start_min_after.strftime("%Y_%m_%d_%H_%M")
   print("CAM:", cam)
   print("DATE WILD:", date_wild)
   hd_wild = "/mnt/ams2/HD/" + date_wild + "*" + cam + ".mp4"
   #hd_wild_before = "/mnt/ams2/HD/" + date_wild_before + "*" + cam + ".mp4"
   #hd_wild_after = "/mnt/ams2/HD/" + date_wild_after + "*" + cam + ".mp4"
   print("HD WILD:", hd_wild)
   hd_matches = glob.glob(hd_wild)

   best_hd_matches = []

   for hd_file in hd_matches:
      (hd_datetime, hd_cam, hd_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(hd_file)
      hd_time_diff = (hd_datetime - sd_trim_start).total_seconds()

      print("SD/HD TIME DIFF:", hd_time_diff)
      if -60 <= hd_time_diff <= 0:
         best_hd_matches.append((hd_file, hd_time_diff))
      #if hd_time_diff > 0:
      #   hd_matches_before = glob.glob(hd_wild_before)

   hd_trim_out = None
   print("BEST HD FILE:", best_hd_matches)
   if len(best_hd_matches) > 0:
      temp = sorted(best_hd_matches, key=lambda x: (x[1]), reverse=True)
      best_hd_matches = [temp[0]]
      print("SORTED BEST HD FILE:", best_hd_matches)

   if len(best_hd_matches) == 1:
      hd_file = best_hd_matches[0][0]

      w,h,frames = ffprobe(hd_file)
      print(w,h,frames)
      hd_time_diff = best_hd_matches[0][1]
      hd_trim_start = (abs(hd_time_diff) * 25) 
      print("HD TRIM START:", hd_trim_start)
      hdfn, dir = fn_dir(hd_file)
      hd_trim_end = hd_trim_start + dur + 100
      print("HD TRIM OUT:", hd_trim_out)
      #if cfe(hd_trim_out) == 0:
      if True:
         print(hd_trim_start, hd_trim_end, hd_file)
         hd_trim_start, hd_trim_end, status = buffer_start_end(hd_trim_start, hd_trim_end, 10, 1499)
         hdfn = hdfn.replace(".mp4", "-trim-" + "{:04d}".format(int(hd_trim_start)) + ".mp4")
         hd_trim_out = PIPE_OUT + hdfn
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

   past_cnts = []

   print("DETECT METEORS IN VIDEO FILE:", trim_clip)
   if trim_clip is None: 
      return(objects, []) 

   if frames is None :
      print("LOAD FRAMES FAST...")  
      frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(trim_clip, json_conf, 0, 1, [], 0,[])

   median_frame = cv2.convertScaleAbs(np.median(np.array(frames), axis=0))
   if len(median_frame.shape) == 3:
      median_frame = cv2.cvtColor(median_frame, cv2.COLOR_BGR2GRAY)
   median_frame = cv2.GaussianBlur(median_frame, (7, 7), 0)
   _, threshold = cv2.threshold(median_frame.copy(), 50, 255, cv2.THRESH_BINARY)
   mask_cnts= get_contours_in_image(threshold)


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
      aframe = cv2.subtract(aframe, median_frame) 
      #aframe = msk_fr(mask_cnts, aframe)
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

   fn = 0
   for frame in frames:

      if len(frame.shape) == 3:
         frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      if fn == 0:
         if len(frame.shape) == 3:
            aframe = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         else:
            aframe = frame.copy()

      #print(frame.shape, median_frame.shape)
      frame = cv2.subtract(frame, median_frame) 

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

      if len(past_cnts) > 0:
         image_diff = msk_fr(past_cnts, image_diff)
         #cv2.imshow("ID", image_diff)
         #cv2.waitKey(30)
      cnts,rects = find_contours_in_frame(image_diff, thresh)
      icnts = []
      if len(cnts) < 5 and fn > 0:
         for (cnt) in cnts:
            px_diff = 0
            x,y,w,h = cnt
            if w > 1 and h > 1:

               past_cnts.append((x,y,w,h))
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
      
      cv2.putText(show_frame, str(fn),  (10,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      show_frame = cv2.convertScaleAbs(show_frame)
      show = 1
      if SHOW == 1:
         cv2.imshow('Detect Meteor In Clip', show_frame)
         cv2.waitKey(30)
      fn += 1



   if SHOW == 1:
      cv2.destroyAllWindows()

   return(objects, frames)   

def get_contours_in_image(frame ):
   cont = [] 
   if len(frame.shape) > 2:
      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
   cnt_res = cv2.findContours(frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      if w > 1 or h > 1:
         cont.append((x,y,w,h))
   return(cont)

def find_contours_in_frame(frame, thresh=25 ):
   contours = [] 
   result = []
   _, threshold = cv2.threshold(frame.copy(), thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(threshold.copy(), None , iterations=4)
   threshold = cv2.convertScaleAbs(thresh_obj)
   #cv2.imshow('THRE', threshold)
   #cv2.waitKey(30)
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
      #cv2.imshow('pepe', threshold)
      #cv2.waitKey(0)

      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res

   # now of these contours, remove any that are too small or don't have a recognizable blob
   # or have a px_diff that is too small

   rects = []
   recs = []
   if len(cnts) < 250:
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
   #cv2.waitKey(30)

   return(contours, recs)

