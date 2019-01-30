import cv2

import numpy as np
from lib.MeteorTests import meteor_test_moving, find_min_max_dist, max_xy
from lib.ImageLib import median_frames, mask_frame, preload_image_acc, adjustLevels
from lib.UtilLib import calc_dist,find_slope
from lib.VideoLib import get_masks




def object_report(objects):
   object_report = "OBJECT REPORT\n"
   object_report = object_report + "-------------\n"
   for object in objects:
      if object['oid'] != 'None':
         object_report = object_report + "Object:\t\t{:s}\n".format(str(object['oid']))
         object_report = object_report + "Clip Len:\t\t{:s}\n".format(str(object['total_frames']))
         object_report = object_report + "Hist Length:\t{:d}\n".format(len(object['history']))
         object_report = object_report + "First/Last:\t{:s}\n".format(str(object['first_last']))
         object_report = object_report + "Meteor Y/N:\t{:s}\n".format(str(object['meteor']))
         object_report = object_report + "Test Results:\n"
         for test in object['test_results']:
            (test_name, status, test_res) = test
            object_report = object_report + "   {:s}\t{:s}\t{:s}\n".format(str(test_name),str(status),str(test_res))
         object_report = object_report + "\nHistory\n"
         for hist in object['history']:
             
            object_report = object_report + "   {:d}\t{:d}\t{:d}\t{:d}\t{:d}\n".format(hist[0],hist[1],hist[2],hist[3],hist[4])
   return(object_report)


#def test_object(object, trim_file, stacked_np):
#   w,h = stacked_np.shape
#   object['status'] = []
#   oid, start_x, start_y, hist = object







def make_new_object(oid, fc, x,y,w,h,max_x,max_y):
   object = {}
   object['oid'] = oid
   object['fc'] = fc
   object['x'] = x
   object['y'] = y
   object['w'] = w
   object['h'] = h
   object['history'] = []
   object['history'].append([fc,x,y,w,h,max_x,max_y])
   return(object)

def save_object(object,objects):
   new_objects = []
   for obj in objects:
      if object['oid'] == obj['oid']:
         new_objects.append(object)
      else:
         new_objects.append(obj)
   return(new_objects)

def find_in_hist(object,x,y,object_hist, hd = 0):
   oid = object['oid']
   found = 0
   if hd == 1:
      md = 40
   else:
      md = 25

   # check if this object_hist is stationary already.
   if len(object_hist) > 1:
      moving,desc = meteor_test_moving(object_hist)
   else:
      moving = 0

   if moving == 1:
      fx = object_hist[0][1]
      fy = object_hist[0][2]
      lx = object_hist[-1][1]
      ly = object_hist[-1][2]
      first_last_slope = find_slope((fx,fy), (lx,ly))
      first_this_slope = find_slope((fx,fy), (x,y))
      last_this_slope = find_slope((lx,ly), (x,y))
      if int(oid) == 3:
         slope_diff = abs(abs(first_last_slope) - abs(first_this_slope))
         if slope_diff > 1:
            #print("SLOPE FAILED: ", first_last_slope, first_this_slope, slope_diff)
            return(0)
         #else:
         #   print("SLOPE PASSED: ", first_last_slope, first_this_slope, slope_diff)
 
   if len(object_hist) >=4:
      object_hist = object_hist[-3:]

   for fc,ox,oy,w,h,mx,my in object_hist:
      
      #if int(oid) == 3:
      #   print("MATCHING OID 3 X,Y", x,y," to ",ox,oy)
      cox = ox + int(w/2)
      coy = oy + int(h/w)
      if ox - md <= x <= ox + md and oy -md <= y <= oy + md:
         found = 1
         return(1)

   # if not found double distance and try again but only if moving!
   if moving == 1:
      md = md * 1.1
      for fc,ox,oy,w,h,mx,my in object_hist:
         cox = ox + mx
         coy = oy + my
         #print(cox-md,cox+md,coy-md,coy+md,x,y)
         if cox - md <= x <= cox + md and coy -md <= y <= coy + md:
            found = 1
            return(1)


   return(found)





def center_point(x,y,w,h):
   cx = x + (w/2)
   cy = y + (h/2)
   return(cx,cy)



def eval_cnt(cnt_img):
   cnth,cntw = cnt_img.shape
   max_px = np.max(cnt_img)
   avg_px = np.mean(cnt_img)
   px_diff = max_px - avg_px
   min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)
   mx, my = max_loc
   mx = mx - 5
   my = my - 5
   return(max_px, avg_px,px_diff,(mx,my))


def check_for_motion2(frames, video_file, cams_id, json_conf, show = 0):

   objects = []
   if show == 1:
      cv2.namedWindow('pepe')

   masks = get_masks(cams_id, json_conf)
   med_stack_all = median_frames(frames[0:25])
   masked_pixels, marked_med_stack = find_bright_pixels(med_stack_all)
   frame_height, frame_width = frames[0].shape
   fc = 0

   image_acc = preload_image_acc(frames)
   thresh = 25
   fc = 0
   for orig_frame in frames:
      frame = orig_frame.copy()
      frame = mask_frame(frame, masked_pixels, masks)
      frame = adjustLevels(frame, 10,1,255)
      frame = cv2.convertScaleAbs(frame)

      nice_frame = frame.copy()
      if len(frame.shape) == 3:
         frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      gray_frame = frame.copy()
      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)

      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), frame,)
      alpha = .5
      hello = cv2.accumulateWeighted(frame, image_acc, alpha)
      _, threshold = cv2.threshold(image_diff.copy(), thresh, 255, cv2.THRESH_BINARY)

      thresh_obj = cv2.dilate(threshold.copy(), None , iterations=4)
      cnt_res = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res 
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res 


      if len(cnts) < 50:
         for (i,c) in enumerate(cnts):
            px_diff = 0
            x,y,w,h = cv2.boundingRect(cnts[i])
            if w < 400 and h < 400 and x != 0 and y != 0:
               y2 = y + h
               x2 = x + w
               if y - 5 > 0:
                  y = y - 5
               if x - 5 > 0:
                  x = x - 5
               if y2 + 5 < frame_height :
                  y2 = y2 + 5
               if x2 + 5 < frame_width:
                  x2 = x2 + 5

               cnt_img = gray_frame[y:y2,x:x2]
               max_px, avg_px, px_diff,max_loc = eval_cnt(cnt_img)
               mx,my = max_loc
               #if px_diff > 10:
               #   fwhm = find_fwhm(x+mx,y+my, gray_frame)

               if px_diff > 10 and fc > 5 :
                  object, objects = id_object(cnts[i], objects,fc, max_loc)

                  cv2.putText(nice_frame, str(object['oid']),  (x-5,y-5), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
                  cv2.rectangle(nice_frame, (x, y), (x + w, y + h), (255, 0, 0,.02), 2)
         if show == 1 and fc % 2 == 0:
            show_frame = cv2.resize(nice_frame, (0,0), fx=0.5, fy=0.5)
            cv2.imshow('pepe', show_frame)
            cv2.waitKey(1)
      fc = fc + 1
   return(objects)

def id_object(cnt, objects, fc,max_loc, is_hd=0):

   mx,my= max_loc
   mx = mx - 1
   my = my - 1
   x,y,w,h = cv2.boundingRect(cnt)
   cx,cy = center_point(x,y,w,h)
   #print("ID OBJECT NEAR POINT:", cx,cy)
   #print("\tLEN OBJECTS:", len(objects))

   if len(objects) == 0:
      oid = 1
      object = make_new_object(oid, fc,x,y,w,h,mx,my)
      objects.append(object)
      return(object, objects)


   # Find object or make new one
   obj_found = 0
   matches = []


   for obj in objects:
      moid = obj['oid']
      oid = obj['oid']
      ox = obj['x']
      oy = obj['y']
      object_hist = obj['history']
      bx = x + mx
      by = y + my
      found = find_in_hist(obj,x,y,object_hist, is_hd)
      if found == 1:
         matches.append(obj)
      #else:
   if len(matches) == 0:
      # NOT FOUND MAKE NEW
      max_id = max(objects, key=lambda x:x['oid'])
      oid= max_id['oid'] + 1
      object = make_new_object(oid,fc,x,y,w,h,mx,my)
      objects.append(object)
      return(object, objects)

   if len(matches) == 1:
      object = matches[0]
      object_hist = object['history']
      this_hist = [fc,x,y,w,h,mx,my]
      if len(object_hist) <= 1500:
         object_hist.append(this_hist)
      object['history'] = object_hist
      objects = save_object(object,objects)
      obj_found = 1
      return(object, objects)

   if len(matches) > 1:
      #print(fc, "MORE THAN ONE MATCH for",x,y, len(matches))
      #print("--------------------")
      #print(matches)
      #print("--------------------")
      min_dist = 1000
      match_total_hist = 0
      for match in matches:
         match_hist = match['history']
         last_hist = match_hist[-1]
         match_x = last_hist[1]
         match_y = last_hist[2]
         dist_to_obj = calc_dist((bx,by),(match_x,match_y))
         if dist_to_obj < min_dist:
            best_dist_obj = match
            min_dist = dist_to_obj
         if len(match_hist) > match_total_hist:
            best_hist_obj = match
            match_total_hist = len(match_hist)

      object = best_hist_obj
      object_hist = object['history']
      this_hist = [fc,x,y,w,h,mx,my]
      if len(object_hist) <= 150:
         object_hist.append(this_hist)
      object['history'] = object_hist
      objects = save_object(object,objects)
      return(object, objects)

def find_bright_pixels(med_stack_all):
   max_px = np.max(med_stack_all)
   avg_px = np.mean(med_stack_all)
   pdif = max_px - avg_px
   pdif = int(pdif / 10) + avg_px
   #star_bg = 255 - cv2.adaptiveThreshold(med_stack_all, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 3)

   _, star_bg = cv2.threshold(med_stack_all, pdif, 255, cv2.THRESH_BINARY)
   #star_bg = cv2.GaussianBlur(star_bg, (7, 7), 0)
   #thresh_obj = cv2.dilate(star_bg, None , iterations=4)
   thresh_obj= cv2.convertScaleAbs(star_bg)
   (cnt_res) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res

   masked_pixels = []
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      cx = int(x + (w/2))
      cy = int(y + (h/2))
      masked_pixels.append((cx,cy))
      cv2.rectangle(star_bg, (x, y), (x + w, y + w), (255, 0, 0), 2)
   #med_stack_all = np.median(np.array(frames), axis=0)
   return(masked_pixels, star_bg)

def object_box(object, stacked_image_np):
   oid, start_x, start_y, hist = object
   im_h, im_w = stacked_image_np.shape
   max_x = 0
   max_y = 0
   min_x = im_w
   min_y = im_h
   for line in hist:
      fn, x,y,w,h,fx = line
      mx = x + w
      my = y + h
      if my > max_y:
         max_y = my
      if y < min_y:
         min_y = y
      if mx > max_x:
         max_x = mx
      if x < min_x:
         min_x = x
   max_x = max_x + 10
   max_y = max_y + 10
   min_x = min_x - 10
   min_y = min_y - 10
   if max_x > im_w:
      max_x = im_w
   if max_y > im_h:
      max_y = im_h
   if min_x < 0:
      min_x = 0
   if min_y < 0:
      min_y = 0
   return(int(min_x), int(min_y), int(max_x),int(max_y))


