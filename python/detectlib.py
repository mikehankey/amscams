#!/usr/bin/python3 
import math
from PIL import Image, ImageChops
import numpy as np
import datetime
import json
import cv2
# Library for detect function


json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)
proc_dir = json_conf['site']['proc_dir']

def get_image(image_file):
   open_cv_image = cv2.imread(image_file,1)   
   return(open_cv_image)

def get_masks(this_cams_id):
   my_masks = []
   cameras = json_conf['cameras']
   for camera in cameras:
      if str(cameras[camera]['cams_id']) == str(this_cams_id):
         masks = cameras[camera]['masks']
         for key in masks:
            my_masks.append((masks[key]))

#   print(my_masks)

   return(my_masks)


def convert_filename_to_date_cam(file):
   el = file.split("/")
   filename = el[-1]
   filename = filename.replace(".mp4" ,"")
   if "-" in filename:
      xxx = filename.split("-")
      filename = xxx[0]
   fy,fm,fd,fh,fmin,fs,fms,cam = filename.split("_")
   f_date_str = fy + "-" + fm + "-" + fd + " " + fh + ":" + fmin + ":" + fs
   f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
   return(f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs)


def load_video_frames(trim_file):

   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(trim_file)
   masks = get_masks(cam)

   cap = cv2.VideoCapture(trim_file)

   frames = []
   frame_count = 0
   go = 1
   while go == 1:
      _ , frame = cap.read()
      if frame is None:
         if frame_count <= 1:
            cap.release()
            print("Bad file.")
            return(frames)
         else:
            go = 0
      else:
         if len(frame.shape) == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         # apply masks for frame detection
         for mask in masks:
            mx,my,mw,mh = mask.split(",")
            frame[int(my):int(my)+int(mh),int(mx):int(mx)+int(mw)] = 0

         frames.append(frame)
         frame_count = frame_count + 1
   #cv2.imwrite("/mnt/ams2/tests/test" + str(frame_count) + ".png", frames[0])
   cap.release()
   return(frames)

def check_for_motion(frames, video_file):
   cv2.namedWindow('pepe')
   # find trim number
   el = video_file.split("/")
   fn = el[-1]
   st = fn.split("trim")
   print("ST:", st)
   stf = st[1].split(".")

   trim_num = int(stf[0])
   print("TRIM NUM: ", trim_num)
   tfc = trim_num
   frame_file_base = video_file.replace(".mp4", "")
   frame_data = []
   last_frame = None
   image_acc = None
   frame_count = 1
   good_cnts = []
   max_cons_motion = 0
   cons_motion = 0
   moving_objects = None
   object = None
   stacked_image = None

   for frame in frames:
      data_str = []
      data_str.append(trim_num)
      data_str.append(frame_count)
      nice_frame = frame.copy()


      stacked_image = stack_image_PIL(nice_frame, stacked_image)
      stacked_image_np = np.asarray(stacked_image)

      if len(frame.shape) == 3:
         frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      gray_frame = frame
      frame_file = frame_file_base + "-fr" + str(frame_count) + ".png"

      frame = cv2.GaussianBlur(frame, (7, 7), 0)

      # setup image accumulation
      if last_frame is None:
         last_frame = frame
      if image_acc is None:
         image_acc = np.empty(np.shape(frame))

      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), frame,)
      alpha = .4
      hello = cv2.accumulateWeighted(frame, image_acc, alpha)
      _, threshold = cv2.threshold(image_diff, 5, 255, cv2.THRESH_BINARY)
      thresh_obj = cv2.dilate(threshold, None , iterations=4)
      (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      good_cnts = []
      cnt_cnt = 0
      #print("CNT:", frame_count, len(cnts))
      # START CNT LOOP
      for (i,c) in enumerate(cnts):
         bad_cnt = 0
         x,y,w,h = cv2.boundingRect(cnts[i])

         if w <= 1 and h <= 1:
            bad_cnt = 1
         if w >= 630 or h >= 400:
            bad_cnt = 1


         if bad_cnt == 0:
            x2 = x + w
            y2 = y + h
            cnt_img = gray_frame[y:y2,x:x2]
            cnt_x, cnt_y,cnt_w,cnt_h =  find_center(cnt_img) 
            adj_x = x + cnt_x
            adj_y = y + cnt_y
            print("XY/CENTER XY", x,y,cnt_x,cnt_y, adj_x,adj_y)
            fx = test_cnt_flux(cnt_img, frame_count, cnt_cnt)
            bf = examine_cnt(cnt_img)
            if fx == 0 or bf < 1.5:
               bad_cnt = 1 

         if bad_cnt == 0:


            if frame_count > 15 and fx == 1 and bf >= 1.5:
               object, moving_objects = find_object(tfc,(adj_x,adj_y,cnt_w,cnt_h,fx), moving_objects)
            

            if object != None and bad_cnt == 0:

               x2 = x + w
               y2 = y + h
               #print("CNT SHAPE: ", cnt_img.shape[0], cnt_img.shape[1])
               if cnt_img.shape[0] > 0 and cnt_img.shape[1] > 0:
                  fx = test_cnt_flux(cnt_img, frame_count, cnt_cnt)
               else:
                  fx = 0
               if fx == None:
                  print("BAD FX: ", frame_count, cnt_cnt)
               if fx == 0:
                  bad_cnt = 1

            #cv2.imwrite("/mnt/ams2/tests/cnt" + str(frame_count) + "-" + str(cnt_cnt) + ".png", cnt_img)

            if bad_cnt == 0:


               good_cnts.append((frame_count,adj_x,adj_y,w,h,fx))
               #cv2.rectangle(nice_frame, (x, y), (x + w, y + w), (255, 0, 0), 2)
               #cv2.putText(nice_frame, str(object),  (x,y), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

               #cv2.rectangle(stacked_image_np, (x, y), (x + w, y + w), (255, 0, 0), 2)
               #cv2.putText(stacked_image_np, str(object),  (x,y), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
            
               stacked_image = Image.fromarray(stacked_image_np)
               cnt_cnt = cnt_cnt + 1
      # END CNT LOOP!
      if len(good_cnts) > 10:
         print ("NOISE!", video_file,frame_count, len(good_cnts))
         good_cnts = []
         #cv2.imwrite(frame_file, nice_frame)
         #frame_file_tn = frame_file.replace(".png", "-tn.png")
         #thumbnail = cv2.resize(nice_frame, (0,0), fx=0.5, fy=0.5)
         #cv2.imwrite(frame_file_tn, thumbnail)

      data_str.append(good_cnts)
      data_str.append(cons_motion)
      frame_data.append(data_str)
      if cons_motion > max_cons_motion:
         max_cons_motion = cons_motion
      if len(good_cnts) >= 1:
         cons_motion = cons_motion + 1
         #print ("CNT: ", frame_count, x,y,w,h,cons_motion)
      else:
         cons_motion = 0
      frame_count = frame_count + 1
      tfc = tfc + 1
      cv2.imshow('pepe', nice_frame)
      cv2.waitKey(1)
      #print(frame_count, len(good_cnts), cons_motion)


   cv2.imshow('pepe', stacked_image_np)
   cv2.waitKey(0)

   return(max_cons_motion, frame_data, moving_objects, stacked_image)

def object_report (trim_file, frame_data):
   fc =1
   tfc =1
   moving_objects = None
   found_objects = []
   for fd in frame_data:
      #print (str(fd[0]) + "," + str(fd[1]) + "," )

      fd_temp = sorted(fd[2], key=lambda x: x[3], reverse=True)
      if len(fd_temp) > 0 and len(fd_temp) < 8:
         #print("FDTEMP:", fd_temp)
         for fn,x,y,w,h,fx in fd_temp:
            object, moving_objects = find_object(tfc, (x,y,w,h,fx), moving_objects)
      fc = fc + 1
      tfc = tfc + 1
   try:
      if moving_objects is None:
         moving_objects = []
   except:
      moving_objects = []


   for object in moving_objects:
      status = []
      hist = object[3]
      first = hist[0]
      last = hist[-1]
      p1 = first[1], first[2]
      p2 = last[1], last[2]
      hist_len = len(object[3]) - 1
      elp_frms = last[0] - first[0]

      if elp_frms > 0:
         len_test = hist_len / elp_frms
      else:
         len_test = 0

      if hist_len > 3:
         slope = find_slope(p1,p2)
         dist = calc_dist(p1,p2)
      else:
         slope = "na"
         dist = 0
      if elp_frms > 0 and dist != "na":
         px_per_frame =dist / elp_frms
      else:
         px_per_frame = 0
      if len_test < .5 or len_test > 2:
         status.append(('reject', 'object flickers like a plane.'))
      if elp_frms > 200:
         status.append(('reject', 'object exists for too long to be a meteor.'))
      if px_per_frame <= .59:
         status.append(('reject', 'object does not move fast enough to be a meteor.'))
      if dist < 4:
         status.append(('reject', 'object does not move far enough to be a meteor.'))
      if hist_len < 3:
         status.append(('reject', 'object does not exist long enough.'))
      # (frame_num, count, first_frame, last_frame, slope, distance, elapsed_frames, px_per_frames, status)
      obj_data = (object[0],  hist_len,  first, last,  slope, dist,  elp_frms,  px_per_frame,  status)
      found_objects.append(obj_data)
   return(found_objects, moving_objects)

def find_center(cnt_img):
   max_px = np.max(cnt_img)
   mean_px = np.mean(cnt_img)
   max_diff = max_px - mean_px
   thresh = max_diff / 2
   _, threshold = cv2.threshold(cnt_img, thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(threshold, None , iterations=4)
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   # START CNT LOOP
   for (i,c) in enumerate(cnts):
      bad_cnt = 0
      x,y,w,h = cv2.boundingRect(cnts[i])

      if w <= 1 and h <= 1:
         bad_cnt = 1
      if w >= 630 or h >= 400:
         bad_cnt = 1

   nx = x + (w /2)
   ny = y + (h /2)
   print("CENTER X,Y", nx,ny)
   return(int(nx),int(ny),w,h)
   

def find_object(fn, pt, moving_objects):
   x,y,w,h,fx = pt
   prox_match = 0
   if moving_objects is None:
      lenstr = "0"
   else:
      lenstr = str(len(moving_objects))

   #print ("<h4>Current Known Objects that could match x,y " + str(x) + "," + str(y) + " " + lenstr + "</h4>")
   if moving_objects is None:
      # there are no objects yet, so just add this one and return.
      oid = 0
      mo = []
      moving_objects = np.array([ [[oid],[x],[y],[[fn,x,y,w,h,fx],[fn,x,y,w,h,fx]] ]])
      return(oid, moving_objects)
   else:
      # match based on proximity to pixel history of each object
      #print("MOVING OBJECTS:", moving_objects[0])
      rowc = 0
      match_id = None
      for (oid,ox,oy,hist) in moving_objects:
         found_in_hist = check_hist(x,y,hist)
         #print("<BR>FOUND IN HIST?" , found_in_hist, "<BR>")
         if found_in_hist == 1:
            prox_match = 1
            match_id = oid

   #can't find match so make new one
   if prox_match == 0:
      oid = new_obj_id((x,y), moving_objects)
      moving_objects = np.append(moving_objects, [ [[oid],[x],[y],[[fn,x,y,w,h,fx],[fn,x,y,w,h,fx]]] ], axis=0)
   else:
      oid,ox,oy,hist = moving_objects[match_id][0]
      hist.append([fn,x,y,w,h,fx])
      moving_objects[match_id][0] = [ [[oid],[ox],[oy],[hist]] ]

   return(oid, moving_objects)

def last_meteor_check (obj, moving_objects, frame_data, frames):
   print("LAST METEOR CHECK!")
   object_id = obj[0][0]
   print("OBJ ID: ", object_id)
   print("OBJ : ", obj)
   #print("MOVING OBJECTS: ", moving_objects)

   flx_check_total = 0
   fx_pass = 0
   avg_tbf = 0
   obj_hist = []
   for object in moving_objects:
      #print("MV OBJECT: ", object)
      this_object_id = object[0][0]
      #print ("THIS OBJECT ID: ", this_object_id, object_id)
      if object_id == this_object_id:
         #print("OBJ MATCH:", object)
         this_hist = object[3]
         #print("HIST", this_hist)
         for hist in this_hist:
            fn, x,y,w,h,fx = hist
            print("HIST: ", fn, x,y,w,h,fx)
            flx_check_total = flx_check_total + fx
         if len(hist) > 1:
            fx_perc = flx_check_total / len(this_hist)
         if fx_perc > .6:
            fx_pass = 1
            obj_hist = this_hist
         #print ("FX PERC?:", flx_check_total, len(hist) ,fx_perc)

   # Examine each cnt to tell if it has a bright centroid or streak
   # or is more anomolous

   tbf = 0
   if fx_pass == 1:
      # make cnts images for each cnt (so we can examine/debug)
      for fn,x,y,w,h,fx in obj_hist:
         image = frames[fn]
         x2 = x + w + 5
         y2 = y + h + 5
         x1 = x  - 5
         y1 = y  - 5
         if x1 < 0:
            x1 = 0
         if y1 < 0:
            y1 = 0
         if x2 > image.shape[1]:
            x2 = image.shape[1]
         if y2 > image.shape[0]:
            y2 = image.shape[0]
         #print("IMG: ", y,y2,x,x2)
         if w > 1 and h > 1:
            print ("XY12: ", y1, y2, x1, x2)
            cnt_img = image[y1:y2,x1:x2]
            brightness_factor = examine_cnt(cnt_img)
            tbf = tbf + brightness_factor
         cv2.imwrite("/mnt/ams2/tests/cnt" + str(fn) + ".jpg", cnt_img)

      if len(obj_hist) > 0:
         avg_tbf = tbf / len(obj_hist)

   if avg_tbf > 1.7:
      print ("YES passed the cnt brightness tests")
      fx_pass = 1
   else:
      fx_pass = 0


   return(fx_pass)


def examine_cnt(cnt_img):
   max_px = np.max(cnt_img)
   avg_px = np.mean(cnt_img)
   if avg_px > 0:
      brightness_factor = max_px / avg_px
   return(brightness_factor)


def ffmpeg_trim (filename, trim_start_sec, dur_sec, outfile):
   print ("TRIMMING METEOR!")
   if int(trim_start_sec) < 10:
      trim_start_sec = "0" + str(trim_start_sec)
   if int(dur_sec) < 10:
      dur_sec = "0" + str(dur_sec)

   #outfile = filename.replace(".mp4", out_file_suffix + ".mp4")
   cmd = "/usr/bin/ffmpeg -i " + filename + " -y -ss 00:00:" + str(trim_start_sec) + " -t 00:00:" + str(dur_sec) + " -c copy " + outfile
   print (cmd)
   os.system(cmd)
   return(outfile)

def test_cnt_flux(cnt_img, frame_count,cnt_cnt):
   hull = 0
   brightness_passed = 0
   corner_passed = 0
   img_min = cnt_img.min()
   img_max = cnt_img.max()
   img_avg = cnt_img.mean()
   img_diff = img_max - img_avg
   thresh = int(img_avg + (img_diff / 2))
   thresh = img_avg
   img_avg_diff = img_max - img_min
   if img_max / img_avg < 1.5:
      # Failed brightness check
      print("Failed brightness check.", img_max, img_avg)

      return(0)
   #print("TEST Countour Flux, should be light in center and dark on edges all around.", img_min,img_max,img_avg)

   lc = cnt_img[0,0]
   brc = cnt_img[-1,-1]
   rc = cnt_img[0,-1]
   blc = cnt_img[-1,0]
   total = int(lc) + int(brc) + int(rc) + int(blc)
   avg = total / 4
   passed = 0
   if img_min > 0:
      if img_max / img_min > 1.5:
         #print ("FLUX TEST: ", frame_count, cnt_cnt, avg, lc)
         brightness_passed = 1
      else:
         brightness_passed = 0

   # cnt in cnt test
   _, threshold = cv2.threshold(cnt_img, thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(threshold, None , iterations=4)
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnts) == 1:
      #BLOB DETECT INSIDE CNT
      params = cv2.SimpleBlobDetector_Params()
      params.filterByArea = True
      params.filterByInertia = False
      #params.filterByConvexity = False
      params.filterByCircularity = True
      params.minCircularity= .5
      params.minArea = 1

      params.minThreshold = img_min + 5
      params.maxThreshold = 255
      params.filterByConvexity = True
      params.minConvexity = .95
      detector = cv2.SimpleBlobDetector_create(params)
      keypoints = detector.detect(cnt_img)
      hull = len(keypoints)
      cnt_found = 1
   else:
      hull = 999
      cnt_found = 0


   # corner test
   if (avg - 10 < lc < avg + 10) and (avg - 10 < brc < avg + 10) and (avg - 10 < rc < avg + 10) and (avg - 10 < blc < avg + 10):
      corner_passed = 1
   else:
      corner_passed = 0
   if hull == 1:
      shull = 1
   else:
      shull = 0
   score = brightness_passed + corner_passed + cnt_found + shull
   if score >= 3:
      cv2.imwrite("/mnt/ams2/tests/cnt" + str(frame_count) + "_" + str(cnt_cnt) + "-" + str(brightness_passed) + "-" + str(corner_passed) + "-" + str(cnt_found) + "-" + str(hull) + ".png", cnt_img)

   if score >= 3:
      return(1)
   else:
      return(0)


def new_obj_id(pt, moving_objects):
   x,y = pt
   print ("<BR> MOVING OBJS : ", moving_objects)
   if len(moving_objects) > 0:
      max_id = np.max(moving_objects, axis=0)
      new_id = max_id[0][0] + 1
   else:
      new_id = 1
   return(new_id)


def check_hist(x,y,hist):

   for (fn,hx,hy,hw,hh,hf) in hist:
      if hx - 20 <= x <= hx + 20 and hy - 20 <= y <= hy +20:
         return(1)
   return(0)

def stack_stack(image, stacked_image):
   h,w = image.shape
   print(w,h)
   for x in range(0,w-1):
      for y in range(0,h-1):
         sp = stacked_image[y,x]
         ip = image[y,x]
         if ip > sp:
            stacked_image_PIL[y,x] = image[y,x]
            #stacked_image[y,x] = image[y,x]

def stack_frames(frames):
   stacked_image = None   
   fc = 1
   for frame in frames:
      print("Stacking trim...", fc)
      if stacked_image == None:
         stacked_image = frame
      stacked_image = stack_stack(frame, stacked_image)
      fc = fc + 1
   return(stacked_image)

def stack_image_PIL(pic1, pic2):
   if len(pic1.shape) == 3:
      pic1 = cv2.cvtColor(pic1, cv2.COLOR_BGR2GRAY)
   frame_pil = Image.fromarray(pic1)
   if pic2 is None:
      stacked_image = frame_pil 
#np.asarray(frame_pil)
   else: 
      stacked_image = pic2 

   stacked_image=ImageChops.lighter(stacked_image,frame_pil)
   return(stacked_image)

def find_color(oc):
   if oc == 0:
      colors = 255,0,0
   if oc == 1:
      colors = 0,255,0
   if oc == 2:
      colors = 0,0,255
   if oc == 3: 
      colors = 255,255,0
   if oc == 4: 
      colors = 255,255,255
   
   return(colors)

def test_object(object):
   status = []
   # distance of object
   # object speed / pixels per frame
   # linear motion -- does the object move in the same direction
   # straight line -- do 3 or more points fit a line

   oid, start_x, start_y, hist = object
   straight_line = 99
   slope = 0
   dist = 0
   hist = object[3]
   first = hist[0]
   last = hist[-1]
   p1 = first[1], first[2]
   p2 = last[1], last[2]
   hist_len = len(object[3]) - 1
   elp_frms = last[0] - first[0]
   cns_mo = 0
   max_cns_mo = 0
   last_fn = None

   # length test
   if hist_len < 2:
      len_test = 0
   else:
      len_test = 1

   # does the object pass consecutive motion test
   if elp_frms > 0:
      cm_test = (hist_len-1) / elp_frms
   else:
      cm_test = 0

   if hist_len > 3:
      slope = find_slope(p1,p2)
      dist = calc_dist(p1,p2)

   if hist_len > 2:
      if hist_len > 3:
         ix = int(hist_len/2)
      else:
         ix = 1
      straight_line = compute_straight_line(hist[0][0],hist[0][1],hist[ix][0],hist[ix][1],hist[-1][0],hist[-1][1])
      for line in hist:
         fn, x,y,w,h,fx = line 
         #find_center(x,y,w,h,img_cnt)
         if last_fn is not None:
            if fn - 1 == last_fn:
               cns_mo = cns_mo + 1
               if cns_mo > max_cns_mo:
                  max_cns_mo = cns_mo
            else:
               if cns_mo > max_cns_mo:
                  max_cns_mo = cns_mo
               cns_mo = 0
         print(line)
         last_fn = fn

   if max_cns_mo > 0:
      max_cns_mo = max_cns_mo + 1
   if max_cns_mo > 0:
      px_per_frame = dist / max_cns_mo 
   else:
      px_per_frame = 0
     

   print ("Object ID: ", oid)
   print("-----------------")
   print ("CM Test: ", cm_test)
   print ("Cons Mo: ", max_cns_mo)
   print ("LEN Test: ", len_test)
   print ("Dist: ", dist)
   print ("Slope: ", slope)
   print ("Straight: ", straight_line)
   print ("PX Per Frame: ", px_per_frame)
   print("")
   meteor_yn = 0
   if cm_test > .5 and max_cns_mo >= 3 and px_per_frame >= .6 and dist > 5 and straight_line < 1:
      print("METEOR")
      meteor_yn = 1
   return(meteor_yn)

def compute_straight_line(x1,y1,x2,y2,x3,y3):
   print ("COMP STRAIGHT", x1,y1,x2,y2,x3,y3)
   if x1 - x2 != 0:
      a = (y1 - y2) / (x1 - x2)
   else:
      a = 0
   if x1 - x3 != 0:
      b = (y1 - y3) / (x1 - x3)
   else:
      b = 0
   straight_line = a - b
   if (straight_line < 1):
      straight = "Y"
   else:
      straight = "N"
   return(straight_line)
 

def calc_dist(p1,p2):
   x1,y1 = p1
   x2,y2 = p2
   dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
   return dist


def find_slope(p1,p2):
   (x1,y1) = p1
   (x2,y2) = p2
   top = y2 - y1
   bottom = x2 - y2
   if bottom > 0:
      slope = top / bottom
   else:
      slope = "na"
   #print(x1,y1,x2,y2,slope)
   return(slope)

def meteor_in_trim(frames, moving_objects, trim_file):
   for object in moving_objects:
      oid, start_x, start_y, hist = object
      meteor_yn = test_object(object, frames)
      if meteor_yn == 1:
         save_meteor()
      else:
         reject_meteor()
    
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

def draw_obj_image(stacked_image_np, moving_objects):
   colors = None
   stacked_image_np_gray = stacked_image_np
   stacked_image_np = cv2.cvtColor(stacked_image_np, cv2.COLOR_GRAY2RGB)
   oc = 0
   for object in moving_objects:
    
      meteor_yn = test_object(object)
      oid, start_x, start_y, hist = object
      if len(hist) - 1 > 1:
         colors = find_color(oc)
         print("HIST:", oid, hist)
         min_x, min_y, max_x, max_y = object_box(object, stacked_image_np_gray) 
         cv2.rectangle(stacked_image_np, (min_x, min_y), (max_x, max_y), (255,255,255), 2)
         for line in hist:
            fn, x,y,w,h,fx = line 
            print(x,y)
            dd = int(w + h / 2)
            #cv2.rectangle(stacked_image_np, (x, y), (x + 3, y + 3), (colors), 2)
            cv2.circle(stacked_image_np, (x,y), dd, (255), 1)
            #cv2.putText(stacked_image_np, str(oid),  (x,y), cv2.FONT_HERSHEY_SIMPLEX, .4, (colors), 1)
         if meteor_yn == 1:
            cv2.putText(stacked_image_np, str("Meteor"),  (min_x,min_y- 5), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
         oc = oc + 1
 
   return(stacked_image_np)
