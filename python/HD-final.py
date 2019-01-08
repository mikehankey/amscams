#!/usr/bin/python3

import time
import cv2
import sys
import numpy as np
from detectlib import id_object
from detectlib import test_object2

def eval_cnt(cnt_img):
   cnth,cntw = cnt_img.shape
   max_px = np.max(cnt_img)
   avg_px = np.mean(cnt_img)
   px_diff = max_px - avg_px
   min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)
   mx, my = max_loc


   #cv2.imshow('pepe', fwhm_img)
   #cv2.waitKey(0)
   return(max_px, avg_px,px_diff,max_loc)

def FWHM(X,Y):
   d = Y - (max(Y) / 2)
   indexes = np.where(d>0)[0]
   try:
      return(abs(X[indexes[-1]] - X[indexes[0]]))
   except:
      return(0)



def preload_image_acc(frames):
   alpha = .9
   gframe = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
   image_acc = np.empty(np.shape(gframe))
   for frame in frames:

      if len(frame.shape) == 3:
         frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

      frame = cv2.GaussianBlur(frame, (7, 7), 0)
      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), frame,)
      hello = cv2.accumulateWeighted(frame, image_acc, alpha)

   #cv2.imshow('pepe', cv2.convertScaleAbs(image_acc))
   #cv2.waitKey(1)

   return(image_acc)



def load_video_frames(trim_file):
   #(f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(trim_file)
   #print("LOAD: ", f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs)
   #if "HD" in trim_file:
   #   masks = get_masks(cam, 1)
   #else:
   #   masks = get_masks(cam, 0)

   cap = cv2.VideoCapture(trim_file)
   time.sleep(2)
   print("CAP OPEN", trim_file)

   frames = []
   gray_frames = []
   frame_count = 0
   go = 1
   while go == 1:
      _ , frame = cap.read()
      if frame is None:
         if frame_count <= 5:
            cap.release()
            return(frames)
         else:
            go = 0
      else:
         #if len(frame.shape) == 3:
         #   gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         # apply masks for frame detection
         #for mask in masks:
         #   mx,my,mw,mh = mask.split(",")
         #   frame[int(my):int(my)+int(mh),int(mx):int(mx)+int(mw)] = 0

         frames.append(frame)
         #gray_frames.append(gray_frame)
         frame_count = frame_count + 1
 
   cap.release()
   return(frames)

def check_for_motion2(frames, video_file):

   objects = []
   cv2.namedWindow('pepe')
   med_stack_all = median_frames(frames[0:25])
   masked_pixels, marked_med_stack = find_bright_pixels(med_stack_all)
   if len(frames[0].shape) == 3:
      frame_height, frame_width,xx = frames[0].shape
   else:
      frame_height, frame_width = frames[0].shape
   fc = 0
   #for frame in frames:
   #   frame = mask_frame(frame, masked_pixels)
   #   frames[fc] = frame
   #   fc = fc + 1

   image_acc = preload_image_acc(frames)

   fc = 0
   for frame in frames:
      nice_frame = frame.copy()
      if len(frame.shape) == 3:
         frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      frame = mask_frame(frame, masked_pixels)
      gray_frame = frame.copy()
      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)

      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), frame,)
      alpha = .5
      hello = cv2.accumulateWeighted(frame, image_acc, alpha)
      _, threshold = cv2.threshold(image_diff.copy(), 30, 255, cv2.THRESH_BINARY)


      #thresh_obj = cv2.convertScaleAbs(threshold)
      thresh_obj = cv2.dilate(threshold.copy(), None , iterations=4)
      (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

      #if len(cnts) == 0:
      #   thresh_obj = cv2.dilate(threshold.copy(), None , iterations=4)
      #   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

      print("FRAME: ", fc, "Contours:", len(cnts))
      if len(cnts) < 150:
         for (i,c) in enumerate(cnts):
            px_diff = 0
            #print("\t\tFRAME: ", fc, "Contour:", i)
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

               if px_diff > 10 :
                  object, objects = id_object(cnts[i], objects,fc, max_loc)

                  cv2.putText(nice_frame, str(object['oid']),  (x-5,y-5), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

                  cv2.rectangle(nice_frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                  #hello = cv2.accumulateWeighted(nice_frame, nice_rec, .5)
                  #print("\t", x, y, w, h, px_diff)
               #else:
               #    print("FAILED PIX DIFF! ", fc, x,y,w,h)

      small_frame = cv2.resize(nice_frame, (0,0), fx=0.5, fy=0.5) 

      cv2.imshow('pepe', small_frame)
      cv2.waitKey(1)
      fc = fc + 1
   return(objects)

def median_frames(frames):
   if len(frames) > 200:
      med_stack_all = cv2.convertScaleAbs(np.median(np.array(frames[0:199]), axis=0))
   else:
      med_stack_all = cv2.convertScaleAbs(np.median(np.array(frames), axis=0))
   return(med_stack_all)


def find_bright_pixels(med_stack_all):
   if len(med_stack_all.shape) == 3:
      med_stack_all= cv2.cvtColor(med_stack_all, cv2.COLOR_BGR2GRAY)
   max_px = np.max(med_stack_all)
   avg_px = np.mean(med_stack_all)
   pdif = max_px - avg_px
   pdif = int(pdif / 10) + avg_px
   #star_bg = 255 - cv2.adaptiveThreshold(med_stack_all, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 3)

   _, star_bg = cv2.threshold(med_stack_all, pdif, 255, cv2.THRESH_BINARY)
   #star_bg = cv2.GaussianBlur(star_bg, (7, 7), 0)
   #thresh_obj = cv2.dilate(star_bg, None , iterations=4)
   thresh_obj= cv2.convertScaleAbs(star_bg)
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   masked_pixels = []
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      cx = int(x + (w/2))
      cy = int(y + (h/2))
      masked_pixels.append((cx,cy))
      cv2.rectangle(star_bg, (x, y), (x + w, y + w), (255, 0, 0), 2)
   #med_stack_all = np.median(np.array(frames), axis=0)
   return(masked_pixels, star_bg)

def mask_frame(frame, mp):
   px_val = np.mean(frame)
   for x,y in mp:
      frame[y-3:y+3,x-3:x+3] = px_val
   return(frame)

def boundbox(object, obj_data,img_w,img_h):
   min_x,min_y,max_x,max_y = obj_data['min_max_xy']
   ow = max_x - min_x
   oh = max_y - min_y
   ow = ow + (ow * 1.2)
   oh = oh + (oh * 1.2)
   if oh > ow:
      ow = oh
   else:
      oh = ow
   cx = (min_x + max_x) / 2
   cy = (min_y + max_y) / 2
   bmin_x = int(cx - (ow / 2 ))
   bmin_y = int(cy - (oh / 2 ))
   bmax_x = int(cx + (ow /2))
   bmax_y = int(cy + (oh /2))
   if bmin_x < 0:
      bmin_x = 0
   if bmin_y < 0:
      bmin_y = 0
   if bmax_x > img_w -1:
      bmax_x = img_w -1
   if bmax_y > img_h -1:
      bmax_y = img_h -1

   return(bmin_x,bmin_y,bmax_x,bmax_y)




file = sys.argv[1]

cv2.namedWindow('pepe')
file_base = file.replace(".mp4", "")
el = file_base.split("/")
filename_base = el[-1].replace(".mp4", "")
base_dir = file_base.replace(filename_base, "")
print("FILENAME BASE:", filename_base)
print("BASE DIR :", base_dir)
frames = load_video_frames(file)
time.sleep(3)
fc=0 
print("FRAMES:", len(frames))
if len(frames) == 0:
   print("NO FRAMES!")
   exit()

objects = check_for_motion2(frames, file)
img_h,img_w,xxx = frames[0].shape
max_hist = 0
if len(objects) == 0:
   print("No objects found!")
   exit()

good_objects = []
for object in objects:
   hist = object['history']
   status, reason, obj_data = test_object2(object)
   if status == 1:
      bmin_x, bmin_y,bmax_x,bmax_y = boundbox(object,obj_data,img_w,img_h)
      oid = object['oid']
      #cv2.putText(stacked_frame, str(oid),  (int(cx+5),int(cy+5)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
      print(object['oid'], status, reason)
      print(bmin_x,bmin_y,bmax_x,bmax_y)
      good_objects.append(object)
   else:
      print("FAILED:", object['oid'], object['history'])

if len(good_objects) > 1:
   print ("MERGE GOOD OBJECTS")

start_op = .2
fc = 0
for frame in frames:
   nice_rec = np.float32(frame)
   cv2.rectangle(frame, (bmin_x, bmin_y), (bmax_x, bmax_y), (255,255,255), 2)

   if start_op > 0:
      hello = cv2.accumulateWeighted(frame, nice_rec, start_op)
   

   nice_rec = cv2.convertScaleAbs(nice_rec)
   frame_file = "/mnt/ams2/HD/tmp3/sync/" + filename_base + "-" + "{0:05d}".format(fc) + ".png"
   cv2.imwrite(frame_file, nice_rec)
   print(frame_file)
   small_frame = cv2.resize(nice_rec, (0,0), fx=0.75, fy=0.75) 
   cv2.imshow('pepe', small_frame)
   cv2.waitKey(10)
   start_op = start_op -.01
   fc =fc + 1
   

