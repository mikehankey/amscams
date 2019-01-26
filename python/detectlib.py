#!/usr/bin/python3 
from statistics import mean
import subprocess
import math
from PIL import Image, ImageChops
import numpy as np
import datetime
import json
import cv2
from pathlib import Path
import os
import time
from scipy import signal
from scipy.interpolate import splrep, sproot, splev

class MultiplePeaks(Exception): pass
class NoPeaksFound(Exception): pass
# Library for detect function


json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)
proc_dir = json_conf['site']['proc_dir']


def adjustLevels(img_array, minv, gamma, maxv, nbits=None):
    """ Adjusts levels on image with given parameters.
    Arguments:
        img_array: [ndarray] Input image array.
        minv: [int] Minimum level.
        gamma: [float] gamma value
        Mmaxv: [int] maximum level.
    Keyword arguments:
        nbits: [int] Image bit depth.
    Return:
        [ndarray] Image with adjusted levels.
    """

    if nbits is None:

        # Get the bit depth from the image type
        nbits = 8*img_array.itemsize


    input_type = img_array.dtype

    # Calculate maximum image level
    max_lvl = 2**nbits - 1.0

    # Limit the maximum level
    if maxv > max_lvl:
        maxv = max_lvl

    # Check that the image adjustment values are in fact given
    if (minv is None) or (gamma is None) or (maxv is None):
        return img_array

    minv = minv/max_lvl
    maxv = maxv/max_lvl
    interval = maxv - minv
    invgamma = 1.0/gamma

    # Make sure the interval is at least 10 levels of difference
    if interval*max_lvl < 10:

        minv *= 0.9
        maxv *= 1.1

        interval = maxv - minv



    # Make sure the minimum and maximum levels are in the correct range
    if minv < 0:
        minv = 0

    if maxv*max_lvl > max_lvl:
        maxv = 1.0


    img_array = img_array.astype(np.float64)

    # Reduce array to 0-1 values
    img_array = np.divide(img_array, max_lvl)

    # Calculate new levels
    img_array = np.divide((img_array - minv), interval)

    # Cut values lower than 0
    img_array[img_array < 0] = 0

    img_array = np.power(img_array, invgamma)

    img_array = np.multiply(img_array, max_lvl)

    # Convert back to 0-maxval values
    img_array = np.clip(img_array, 0, max_lvl)


    # Convert the image back to input type
    img_array.astype(input_type)


    return img_array



def magic_contrast(image):
   cv2.imwrite("/mnt/ams2/cal/tmp/temp.png", image)
   os.system("convert /mnt/ams2/cal/tmp/temp.png -sigmoidal-contrast 8 /mnt/ams2/cal/tmp/temp2.png")
   new_image = cv2.imread("/mnt/ams2/cal/tmp/temp2.png", 0)
   os.system("rm /mnt/ams2/cal/tmp/temp.png ")
   os.system("rm /mnt/ams2/cal/tmp/temp2.png ")
   #cv2.imshow('pepe', new_image)
   #cv2.waitKey(10)
   return(new_image)


def bigger_box(box, hd_stack, hd_stack_img):
   hd_mx = 2.727
   hd_my = 1.875
   img_h, img_w = hd_stack_img.shape

   if len(box) != 4:
      min_x,min_y,max_x,max_y = box.split(",")
   else:
      min_x,min_y,max_x,max_y = box
   min_x, min_y, max_x, max_y = int(min_x)*hd_mx, int(min_y)*hd_my, int(max_x)*hd_mx, int(max_y)*hd_my
   min_x, min_y, max_x, max_y = int(min_x), int(min_y), int(max_x), int(max_y)
   print(min_x,min_y,max_x,max_y)
   img_h, img_w = hd_stack_img.shape
   crop_h = int(max_y) - int(min_y)
   crop_w = int(max_x) - int(min_x)
   print("IMG W,H", img_w, img_h)
   if crop_h < 500 or crop_w < 500:
      print ("MAKE 300x300")
      # make the box 250x250
      center_x = int(crop_w / 2) + min_x
      center_y = int(crop_h / 2) + min_y
      min_x = center_x - 250
      min_y = center_y - 250
      max_x = center_x + 250
      max_y = center_y + 250
   else:
      print("KEEP BOX SIZE as is")

   if min_x <= 0:
      min_x = 1 
      max_x = 500
   if min_y <= 0:
      min_y = 1
      max_y = 500
   if max_x > img_w:
      max_x = img_w
      min_x = img_w - 500
   if max_y > img_h:
      max_y = img_h
      min_y = img_h - 500


   print("MX", min_x,min_y,max_x,max_y)
   new_crop_image = hd_stack_img[min_y:max_y,min_x:max_y]
   cv2.rectangle(hd_stack_img, (min_x, min_y), (max_x,max_y), (255, 0, 0), 2)
   #cv2.imshow('pepe', hd_stack_img)
   #cv2.waitKey(0)
   return(hd_stack_img, (min_x,min_y,max_x,max_y))



def cfe(file,dir = 0):
   if dir == 0:
      file_exists = Path(file)
      if file_exists.is_file() is True:
         return(1)
      else:
         return(0)
   if dir == 1:
      file_exists = Path(file)
      if file_exists.is_dir() is True:
         return(1)
      else:
         return(0)

def setup_dirs(filename):
   el = filename.split("/")
   fn = el[-1]
   working_dir = filename.replace(fn, "")
   data_dir = working_dir + "/data/"
   images_dir = working_dir + "/images/"
   file_exists = Path(data_dir)
   if file_exists.is_dir() == False:
      os.system("mkdir " + data_dir)

   file_exists = Path(images_dir)
   if file_exists.is_dir() == False:
      os.system("mkdir " + images_dir)


def get_image(image_file):
   open_cv_image = cv2.imread(image_file,1)   
   return(open_cv_image)

def get_masks(this_cams_id, hd = 0):
   hdm_x = 2.7272
   hdm_y = 1.875
   my_masks = []
   cameras = json_conf['cameras']
   for camera in cameras:
      if str(cameras[camera]['cams_id']) == str(this_cams_id):
         masks = cameras[camera]['masks']
         for key in masks:
            if hd == 1:
               print("HD MASK")
               #mask_el = masks[key].split(',')
               #(mx, my, mw, mh) = mask_el 
               #mx = mx * hdm_x
               #my = my * hdm_y
               #mw = mw * hdm_x
               #mh = mh * hdm_y
               #masks[key] = str(mx) + "," + str(my) + "," + str(mw) + "," + str(mh)
               #my_masks.append((masks[key]))
            else:
               my_masks.append((masks[key]))


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


def load_video_frames(trim_file, limit=0):

   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(trim_file)
   print("LOAD: ", f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) 
   print("LIMIT:", limit)

   if "HD" in trim_file:
      masks = get_masks(cam, 1)
   else:
      masks = get_masks(cam, 0)

   cap = cv2.VideoCapture(trim_file)
   time.sleep(1)
   frames = []
   frame_count = 0
   go = 1
   while go == 1:
      _ , frame = cap.read()
      if frame is None:
         if frame_count <= 5 :
            cap.release()
            return(frames)
         else:
            go = 0
      else:
         if limit != 0 and frame_count > limit:
            cap.release()
            return(frames)

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

def mask_frame(frame, mp, size=3):
   ih,iw = frame.shape
   px_val = np.mean(frame)
   px_val = 0 
   for x,y in mp:

      if int(y + size) > ih:
         y2 = int(ih - 1)
      else:
         y2 = int(y + size)
      if int(x + size) > iw:
         x2 = int(iw - 1)
      else:
         x2 = int(x + size)

      if y - size < 0:
         y1 = 0
      else:
         y1 = int(y - size)
      if int(x - size) < 0:
         x1 = 0
      else:
         x1 = int(x - size)

      x1 = int(x1)
      x2 = int(x2)
      y1 = int(y1)
      y2 = int(y2)

      frame[y1:y2,x1:x2] = px_val
      #frame[y-3:y+3,x-3:x+3] = px_val

   return(frame)

def median_frames(frames):
   if len(frames) > 200:
      med_stack_all = cv2.convertScaleAbs(np.median(np.array(frames[0:199]), axis=0))
   else:
      med_stack_all = cv2.convertScaleAbs(np.median(np.array(frames), axis=0))
   return(med_stack_all)

def preload_image_acc(frames):
   alpha = .9
   image_acc = np.empty(np.shape(frames[0]))
   for frame in frames:
      frame = cv2.GaussianBlur(frame, (7, 7), 0)
      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), frame,)
      hello = cv2.accumulateWeighted(frame, image_acc, alpha)

   #cv2.imshow('pepe', cv2.convertScaleAbs(image_acc))
   #cv2.waitKey(1)

   return(image_acc)


def spline_fwhm(x, y, k=3):
    """
    Determine full-with-half-maximum of a peaked set of points, x and y.

    Assumes that there is only one peak present in the datasset.  The function
    uses a spline interpolation of order k.
    """

    #x = sorted(x) 
    #y = sorted(y)

    half_max = np.amax(y)/2.0
    print("HALF MAX", half_max)
    s = splrep(x, y - half_max, k=k)
    roots = sproot(s)

    if len(roots) > 2:
        raise MultiplePeaks("The dataset appears to have multiple peaks, and "
                "thus the FWHM can't be determined.")
    elif len(roots) < 2:
        raise NoPeaksFound("No proper peaks were found in the data set; likely "
                "the dataset is flat (e.g. all zeros).")
    else:
        return abs(roots[1] - roots[0])

def find_fwhm(mx,my, gray_frame):
   width, height = gray_frame.shape
   if mx - 5 < 0:
      mx = 5
   if mx + 5 > width-1:
      mx = width-6
   if my - 5 < 0:
      my = 5
   if my + 5 > height-1:
      my = height-6
   
   fwhm_img = gray_frame[my-5:my+5,mx-5:mx+5]

   max_px = np.max(fwhm_img)
   avg_px = np.mean(fwhm_img)
   px_diff = max_px - avg_px
   if px_diff < 10:
      return(-1)

   PX = []
   PY = []
   h,w = fwhm_img.shape
   mx = int(w / 2)
   my = int(h / 2)
   print("FWHM W/H:", w,h)

   for x in range(0,w-1):
      px_val = fwhm_img[my,x] 
      PX.append(px_val)
      #fwhm_img[my,x] = 255
   for y in range(0,h-1):
      py_val = fwhm_img[y,mx] 
      PY.append(py_val)
      #fwhm_img[y,mx] = 255
   print("PX:", PX)
   print("PY:", PY)
   #fwhm = FWHM(PX,PY)
   sp_fwhm = spline_fwhm(PX,PY)
   print("FWHM", spline_fwhm)

   #if fwhm <= 5:
   #   cv2.imshow('pepe', fwhm_img)
   #   cv2.waitKey(30)
   return(fwhm)


def eval_cnt(cnt_img):
   cnth,cntw = cnt_img.shape
   max_px = np.max(cnt_img)
   avg_px = np.mean(cnt_img)
   px_diff = max_px - avg_px
   min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)
   mx, my = max_loc
   mx = mx - 5
   my = my - 5
   #cv2.circle(cnt_img, (mx,my), 5, (255), 1)
   #cv2.imshow('pepe', cnt_img)
   #cv2.waitKey(30)
   return(max_px, avg_px,px_diff,(mx,my)) 

def FWHM(X,Y):
   d = Y - (max(Y) / 2)
   indexes = np.where(d>0)[0]
   try: 
      return(abs(X[indexes[-1]] - X[indexes[0]]))
   except:
      return(0)

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
   found = 0
   if hd == 1:
      md = 40
   else:
      md = 20

   # check if this object_hist is stationary already.
   if len(object_hist) > 1:
      moving = meteor_test_moving(object_hist)
      #print("MOVING: ", moving)

   for fc,ox,oy,w,h,mx,my in object_hist:
      cox = ox + mx
      coy = oy + my
      if cox - md <= x <= cox + md and coy -md <= y <= coy + md:
         found = 1
         return(1)

   # if not found double distance and try again
   md = md * 2
   for fc,ox,oy,w,h,mx,my in object_hist:
      cox = ox + mx
      coy = oy + my
      if cox - md <= x <= cox + md and coy -md <= y <= coy + md:
         found = 1
         return(1)

   return(found)

def center_point(x,y,w,h):
   cx = x + (w/2)
   cy = y + (h/2)
   return(cx,cy)

def id_object(cnt, objects, fc,max_loc, is_hd=0):
   mx,my= max_loc
   mx = mx - 1
   my = my - 1
   x,y,w,h = cv2.boundingRect(cnt)
   cx,cy = center_point(x,y,w,h)
   if len(objects) == 0:
      #print("MAKE FIRST OBJECT")
      oid = 1
      object = make_new_object(oid, fc,x,y,w,h,mx,my)
      objects.append(object)
      return(object, objects)

   
   # Find object or make new one
   obj_found = 0
   matches = []
  
 
   for obj in objects:
      oid = obj['oid']
      ox = obj['x']
      oy = obj['y']
      object_hist = obj['history']
      bx = x + mx
      by = y + my
      found = find_in_hist(obj,bx,by,object_hist, is_hd)
      if found == 1:
         matches.append(obj)
      #else:
   
   if len(matches) == 0:
      # NOT FOUND MAKE NEW 
      max_id = max(objects, key=lambda x:x['oid'])
      oid= max_id['oid'] + 1 
      #print("OBJECT NOT FOUND MAKE NEW: ", oid, fc,x,y,w,h)
      object = make_new_object(oid,fc,x,y,w,h,mx,my)
      objects.append(object)
      return(object, objects)
 
   if len(matches) == 1:
      #print("SINGLE MATCH FOUND", obj['oid'])
      object = matches[0]
      object_hist = object['history']
      this_hist = [fc,x,y,w,h,mx,my]
      if len(object_hist) <= 500:
         object_hist.append(this_hist)
      object['history'] = object_hist
      objects = save_object(object,objects)
      obj_found = 1
      return(object, objects)
      
   if len(matches) > 1:
      # we have more than one match, lets pick the best one.
      #print("More than one potential matching object for x,y", bx,by)
      # our pix is bx,by  . find distance of last px hist for each obj and pic lowest/closest one

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


      #print("BEst distance object to match is :", best_dist_obj)
      #print("BEst History object to match is :", best_hist_obj)

      object = best_hist_obj
      object_hist = object['history']
      this_hist = [fc,x,y,w,h,mx,my]
      if len(object_hist) <= 150:
         object_hist.append(this_hist)
      object['history'] = object_hist
      objects = save_object(object,objects)
      return(object, objects)
    


def check_for_motion2(frames, video_file, show = 0):

   objects = []
   if show == 1:
      cv2.namedWindow('pepe')
   med_stack_all = median_frames(frames[0:25])
   masked_pixels, marked_med_stack = find_bright_pixels(med_stack_all)
   frame_height, frame_width = frames[0].shape
   fc = 0
   for frame in frames:
      frame = mask_frame(frame, masked_pixels)
      frames[fc] = frame
      fc = fc + 1

   image_acc = preload_image_acc(frames)
   thresh = 25
   fc = 0
   for frame in frames:
      frame = adjustLevels(frame, 10,1,255)
      frame = cv2.convertScaleAbs(frame)

      #print(fc)
      nice_frame = frame.copy()
      if len(frame.shape) == 3:
         frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      gray_frame = frame.copy()
      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)


      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), frame,)
      alpha = .5
      hello = cv2.accumulateWeighted(frame, image_acc, alpha)
      _, threshold = cv2.threshold(image_diff.copy(), thresh, 255, cv2.THRESH_BINARY)


      #thresh_obj = cv2.convertScaleAbs(threshold)
      thresh_obj = cv2.dilate(threshold.copy(), None , iterations=4)
      (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

      #while len(cnts) >= 50 :
      #   print("LEN:", len(cnts), thresh)
      #   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      #   thresh = thresh + 5
      #   _, threshold = cv2.threshold(image_diff.copy(), thresh, 255, cv2.THRESH_BINARY)
      #   if thresh > 150:
      #      break

      #print("FRAME: ", fc, "Contours:", len(cnts))
      if len(cnts) < 50:
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
 
               if px_diff > 10 and fc > 5 :
                  object, objects = id_object(cnts[i], objects,fc, max_loc)

                  cv2.putText(nice_frame, str(object['oid']),  (x-5,y-5), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
                  cv2.rectangle(nice_frame, (x, y), (x + w, y + h), (255, 0, 0,.02), 2)
                  #print("\t", x, y, w, h, px_diff)
               #else:
               #    print("FAILED PIX DIFF! ", fc, x,y,w,h) 
  
         if show == 1:
            cv2.imshow('pepe', nice_frame) 
            cv2.waitKey(40)
      fc = fc + 1
   return(objects)

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


def check_for_motion(frames, video_file):
   #cv2.namedWindow('pepe')

   image_acc = np.empty(np.shape(frames[0]))

   # find trim number
   el = video_file.split("/")
   fn = el[-1]
   print("FN:", fn)
   hd_on = 0
   if "HD" not in fn:
      st = fn.split("trim")
      hd_on = 1
   else:
      st = fn.split("trim")

   if "HD" in fn:
      stf = st[1].split("-")
      print("SFTMIKEHD:", stf)
   else:
      stf = st[1].split(".")
      print("SFTMIKE:", stf)

   if len(frames) > 200:
      med_stack_all = cv2.convertScaleAbs(np.median(np.array(frames[0:199]), axis=0))
   else:
      med_stack_all = cv2.convertScaleAbs(np.median(np.array(frames), axis=0))

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


   #med_stack_all = cv2.cvtColor(med_stack_all, cv2.COLOR_BGR2GRAY)


   #cv2.imshow('pepe', med_stack_all)
   #cv2.waitKey(1)
   #cv2.imshow('pepe', star_bg)
   #cv2.waitKey(1)
   print("STF:", stf)
   trim_num = int(stf[0])

   tfc = trim_num
   frame_file_base = video_file.replace(".mp4", "")
   frame_data = []
   last_frame = None
   image_acc = None
   image_acc2 = None
   frame_count = 1
   good_cnts = []
   max_cons_motion = 0
   cons_motion = 0
   moving_objects = None
   object = None
   stacked_image = None

   for frame in frames:
      if len(frame.shape) == 3:
         frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      #thresh_obj = cv2.dilate(star_bg, None , iterations=4)
      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)
      #image_diff = cv2.absdiff(star_bg.astype(frame.dtype), blur_frame,)
      frame = mask_frame(frame, masked_pixels)

      #frame = image_diff 
      #frame = image_diff
      data_str = []
      data_str.append(trim_num)
      data_str.append(frame_count)
      nice_frame = frame.copy()


      stacked_image = stack_image_PIL(nice_frame, stacked_image)
      stacked_image_np = np.asarray(stacked_image)

      gray_frame = frame.copy()
      frame_file = frame_file_base + "-fr" + str(frame_count) + ".png"

      frame = cv2.GaussianBlur(frame, (7, 7), 0)

      # setup image accumulation
      if last_frame is None:
         last_frame = frame
        
      if image_acc is None:
         image_acc = np.empty(np.shape(frame))
         #alpha = .1
         #xend = len(frames)
         #xstart = xend - 30
         #for i in range(xstart,xend):
         #   hello = cv2.accumulateWeighted(frames[i], image_acc, alpha)
         #   image_diff = cv2.absdiff(image_acc.astype(frame.dtype), frames[0],)
         #   _, threshold = cv2.threshold(image_diff, 5, 255, cv2.THRESH_BINARY)
         #   thresh_obj = cv2.dilate(threshold, None , iterations=4)
         #   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
         #   for (i,c) in enumerate(cnts):
         #      bad_cnt = 0
         #      x,y,w,h = cv2.boundingRect(cnts[i])
               #masked_pixels.append((x,y))
         #   frame = mask_frame(frame, masked_pixels)


      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), frame,)
      alpha = .1
      hello = cv2.accumulateWeighted(frame, image_acc, alpha)
      _, threshold = cv2.threshold(image_diff.copy(), 5, 255, cv2.THRESH_BINARY)


      thresh_obj = cv2.convertScaleAbs(threshold)
      (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

      if len(cnts) == 0:
         thresh_obj = cv2.dilate(threshold.copy(), None , iterations=4)
         (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         #print("CNT: ", i, x,y)
         cv2.putText(nice_frame, str(i),  (x,y), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         #cv2.putText(image_diff, str(i),  (x,y), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         #cv2.rectangle(image_diff, (x, y), (x + w, y + w), (255, 0, 0), 2)
         cv2.rectangle(nice_frame, (x, y), (x + w, y + w), (255, 0, 0), 2)
      #cv2.imshow('pepe', image_diff)
      #if 0 < frame_count < 1000:
         #print("LEN CNTS:", len(cnts))
         #cv2.imshow('pepe', thresh_obj)
         #cv2.waitKey(30)
         ##cv2.imshow('pepe', nice_frame)
         #cv2.waitKey(1)
      #else:
      #   cv2.waitKey(1)
      #cv2.imshow('pepe', image_diff2)
      #cv2.waitKey(1)

      good_cnts = []
      #if len(cnts2) > len(cnts):
      #   cnts = cnts2
      cnt_cnt = 0
      #if len(cnts) > 0:
      #   print("CNT:", frame_count, len(cnts))
      # START CNT LOOP
      for (i,c) in enumerate(cnts):
         bad_cnt = 0
         x,y,w,h = cv2.boundingRect(cnts[i])

         if w <= 1 and h <= 1:
            bad_cnt = 1
            continue
         if w >= 630 or h >= 400:
            bad_cnt = 1
            continue


         if bad_cnt == 0:
            x2 = x + w
            y2 = y + h
            cnt_img = gray_frame[y:y2,x:x2]
            cnt_x, cnt_y,cnt_w,cnt_h =  find_center(cnt_img) 
            adj_x = x + cnt_x
            adj_y = y + cnt_y 
            #fx = test_cnt_flux(cnt_img, frame_count, cnt_cnt)
            fx = 1
            bf = examine_cnt(cnt_img)
            print(frame_count, i, bf)
            #print("FLUX: ", frame_count, fx,bf)
            if fx == 0 or bf < 1.5:
               bad_cnt = 1 
               #masked_pixels.append((x,y))

         if bad_cnt == 0:


            if frame_count > 5 and fx == 1 and bf >= 1.5:
               object, moving_objects = find_object(tfc,(adj_x,adj_y,cnt_w,cnt_h,fx), moving_objects)
            else:
               object, masked_objects = find_object(tfc,(adj_x,adj_y,cnt_w,cnt_h,fx), moving_objects)
            

            if object != None and bad_cnt == 0:

               x2 = x + w
               y2 = y + h
               if cnt_img.shape[0] > 0 and cnt_img.shape[1] > 0:
                  fx = test_cnt_flux(cnt_img, frame_count, cnt_cnt)
               else:
                  fx = 0
               if fx == 0:
                  bad_cnt = 1

            cv2.imwrite("/mnt/ams2/tests/cnt" + str(frame_count) + "-" + str(fx) + ".png", cnt_img)

            if bad_cnt == 0:


               good_cnts.append((frame_count,adj_x,adj_y,w,h,fx))
               cv2.rectangle(nice_frame, (x, y), (x + w, y + w), (255, 0, 0), 2)
               cv2.putText(nice_frame, str(object),  (x,y), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
               #cv2.imshow('pepe', nice_frame)
               #cv2.waitKey(30)


               #cv2.rectangle(stacked_image_np, (x, y), (x + w, y + w), (255, 0, 0), 2)
               #cv2.putText(stacked_image_np, str(object),  (x,y), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
            
               stacked_image = Image.fromarray(stacked_image_np)
               cnt_cnt = cnt_cnt + 1
      # END CNT LOOP!
      if len(good_cnts) > 10:
         #print ("NOISE!", video_file,frame_count, len(good_cnts))
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
      else:
         cons_motion = 0
      frame_count = frame_count + 1
      tfc = tfc + 1


   #cv2.imshow('pepe', stacked_image_np)
   #cv2.waitKey(3)

   return(max_cons_motion, frame_data, moving_objects, stacked_image)

def clean_hist(hist):
   new_hist = []
   last_fn = 0
   last_hx = 0
   last_hy = 0
   last_h = None

   # remove duplicate points
   points = []
   past_frames = []
   new_hist = []
   for h in hist:
      #fn,hx,hy,hw,hh,hf = h
      fn,hx,hy,hw,hh = h
      passed = 1 
      for pfn in past_frames:
         if pfn == fn:
            passed = 0

      for point in points:
         px, py = point
         if px - 1 <= hx <= px + 1 and py -1 <= hy <= py + 1:
            # dupe
            passed = 0
         
      if len(new_hist) == 0:
         points.append((hx,hy))
      if passed == 1:
         new_hist.append((h))
      points.append((hx,hy))
      past_frames.append(fn)
     

   if len(new_hist) > 2:
      if new_hist[1][0] - 1 <= new_hist[0][0] <= new_hist[1][0] + 1:
         hist = new_hist
      else:
         hist = new_hist[:-1] 

   #hist = new_hist


   return(hist)
      

def object_report (trim_file, frame_data):
   fc =1
   tfc =1
   moving_objects = None
   found_objects = []
   for fd in frame_data:

      fd_temp = sorted(fd[2], key=lambda x: x[3], reverse=True)
      if len(fd_temp) > 0 and len(fd_temp) < 8:
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
      if px_per_frame <= .3:
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
   x = 0
   y = 0
   w = 0
   h = 0
   thresh = max_diff / 2
   _, threshold = cv2.threshold(cnt_img, thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(threshold, None , iterations=4)
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   # START CNT LOOP
   bad_cnt = 0
   for (i,c) in enumerate(cnts):
      bad_cnt = 0
      x,y,w,h = cv2.boundingRect(cnts[i])

      if w <= 1 and h <= 1:
         bad_cnt = 1
      if w >= 630 or h >= 400:
         bad_cnt = 1
   if bad_cnt == 0 and len(cnts) > 0:
      nx = x + (w /2)
      ny = y + (h /2)
   else:
      nx = 0
      ny = 0
   return(int(nx),int(ny),w,h)
   

def find_object(fn, pt, moving_objects):
   x,y,w,h,fx = pt
   prox_match = 0
   if moving_objects is None:
      lenstr = "0"
   else:
      lenstr = str(len(moving_objects))

   if moving_objects is None:
      # there are no objects yet, so just add this one and return.
      oid = 0
      mo = []
      moving_objects = np.array([ [[oid],[x],[y],[[fn,x,y,w,h,fx],[fn,x,y,w,h,fx]] ]])
      return(oid, moving_objects)
   else:
      # match based on proximity to pixel history of each object
      rowc = 0
      match_id = None
      for (oid,ox,oy,hist) in moving_objects:
         found_in_hist = check_hist(x,y,hist)
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
   #print("LAST METEOR CHECK!")
   object_id = obj[0][0]

   flx_check_total = 0
   fx_pass = 0
   avg_tbf = 0
   obj_hist = []
   for object in moving_objects:
      this_object_id = object[0][0]
      if object_id == this_object_id:
         this_hist = object[3]
         for hist in this_hist:
            fn, x,y,w,h,fx = hist
            flx_check_total = flx_check_total + fx
         if len(hist) > 1:
            fx_perc = flx_check_total / len(this_hist)
         if fx_perc > .6:
            fx_pass = 1
            obj_hist = this_hist

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
         if w > 1 and h > 1:
            cnt_img = image[y1:y2,x1:x2]
            brightness_factor = examine_cnt(cnt_img)
            tbf = tbf + brightness_factor
         #cv2.imwrite("/mnt/ams2/tests/cnt" + str(fn) + ".jpg", cnt_img)

      if len(obj_hist) > 0:
         avg_tbf = tbf / len(obj_hist)

   if avg_tbf > 1.7:
      fx_pass = 1
   else:
      fx_pass = 0


   return(fx_pass)


def examine_cnt(cnt_img):
   max_px = np.max(cnt_img)
   avg_px = np.mean(cnt_img)
   if avg_px > 0:
      brightness_factor = max_px / avg_px
   else:
      brightness_factor = 0
   return(brightness_factor)


def ffmpeg_trim (filename, trim_start_sec, dur_sec, outfile):
   if int(trim_start_sec) < 10:
      trim_start_sec = "0" + str(trim_start_sec)
   if int(dur_sec) < 10:
      dur_sec = "0" + str(dur_sec)

   #outfile = filename.replace(".mp4", out_file_suffix + ".mp4")
   cmd = "/usr/bin/ffmpeg -i " + filename + " -y -ss 00:00:" + str(trim_start_sec) + " -t 00:00:" + str(dur_sec) + " -c copy " + outfile + ">/tmp/x 2>&1"
   os.system(cmd)
   return(outfile)

def test_cnt_flux(cnt_img, frame_count,cnt_cnt):

   cnt_show = cnt_img.copy()
   cnt_h, cnt_w = cnt_img.shape
   hull = 0
   brightness_passed = 0
   corner_passed = 0
   img_min = cnt_img.min()
   img_max = cnt_img.max()
   img_avg = cnt_img.mean()
   img_diff = img_max - img_avg
   thresh = int(img_avg + (img_diff / 2))
   thresh = img_avg


   lc = cnt_img[0,0]
   brc = cnt_img[-1,-1]
   rc = cnt_img[0,-1]
   blc = cnt_img[-1,0]
   total = int(lc) + int(brc) + int(rc) + int(blc)
   avg = total / 4
   passed = 0
   if img_min > 0:
      if img_max / img_min > 1.5:
         brightness_passed = 1
      else:
         brightness_passed = 0

   # cnt in cnt test
   #_, threshold = cv2.threshold(cnt_img.copy(), thresh, 255, cv2.THRESH_BINARY)
   if cnt_w % 2 == 0:
      cnt_w = cnt_w + 1
   print("CNT W: ", cnt_w, cnt_h)
   if cnt_w == 1 :
      cnt_w = 3
   thresh_obj = 255 - cv2.adaptiveThreshold(cnt_img.copy(), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, cnt_w, 3)
   thresh_obj = cv2.dilate(thresh_obj, None , iterations=4)

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
   mean_px_all = np.mean(cnt_img)
   mean_px_in = 0
   tmp_cnt = cnt_img.copy()

   if len(cnts) > 0:
      for (i,c) in enumerate(cnts):
            
         x,y,w,h = cv2.boundingRect(cnts[i])
         nx = int(x + (w/2))
         ny = int(y + (h/2))
         cv2.rectangle(cnt_show , (nx - 3, ny - 3), (nx + 3, ny + 3), (255, 255, 255), 1)
         bpt_img = cnt_img[ny-3:ny+3,nx-3:nx+3]
            
         mean_px_in = np.mean(bpt_img)
         tmp_cnt[ny-3:ny+3,nx-3:nx+3] = mean_px_all


   mean_px_all = np.mean(tmp_cnt)

   if mean_px_all > 0 and img_avg > 0:
      #or img_max / img_avg < 1.2:
      if mean_px_in / mean_px_all < 1.01 :
         # Failed brightness check
         brightness_passed = 0
      else:
         brightness_passed = 1
   else:
      brightness_passed = 0

   score = brightness_passed + corner_passed + cnt_found + shull

   #cv2.imshow("pepe", cnt_show)
   #cv2.waitKey(1)

   #if score >= 3:
      #cv2.imwrite("/mnt/ams2/tests/cnt" + str(frame_count) + "_" + str(cnt_cnt) + "-" + str(brightness_passed) + "-" + str(corner_passed) + "-" + str(cnt_found) + "-" + str(hull) + ".png", cnt_img)

   if score >= 3:
      return(1)
   else:
      return(0)


def new_obj_id(pt, moving_objects):
   x,y = pt
   if len(moving_objects) > 0:
      max_id = np.max(moving_objects, axis=0)
      new_id = max_id[0][0] + 1
   else:
      new_id = 1
   return(new_id)


def check_hist(x,y,hist):

   for (fn,hx,hy,hw,hh,hf) in hist:
      if hx - 35 <= x <= hx + 35 and hy - 35 <= y <= hy +35:
         return(1)
   return(0)

def stack_stack(image, stacked_image):
   print("STACK STACK ROUTINE")
   h,w = image.shape
   for x in range(0,w-1):
      for y in range(0,h-1):
         sp = stacked_image[y,x]
         ip = image[y,x]
         if ip > sp:
            stacked_image[y,x] = image[y,x]
   return(stacked_image)

def stack_frames(frames):
   stacked_image = None   
   fc = 1
   if stacked_image is None:
      stacked_image = frames[0]
   for frame in frames:
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
   if oc >= 5:
      colors = 100,100,255
   
   return(colors)

def slope_test(hist, trim_file):
   slopes = []
   cc = 0

   #overall slope and dist for first and last
   first = hist[0][1], hist[0][2]
   last = hist[-2][1], hist[-1][2]

   o_slope = find_slope(first, last)
   o_dist = calc_dist(first, last)
   o_ang = find_angle(first, last)


 
   if len(hist) > 0:
      e_dist = o_dist / len(hist) 
   else:
      e_dist = 0
   spass = 0
   dpass = 0

   for line in hist:
      fn, x,y,w,h,fx = line 
      if cc > 0:
         slope = find_slope((last_x,last_y), (x,y))
         dist = calc_dist((last_x,last_y), (x,y))
         ang = find_angle((last_x,last_y), (x,y))
         if o_ang - 10 < ang < o_ang + 10:
            spass = spass + 1
         if e_dist - 5 < dist < e_dist+ 5:
            dpass = dpass + 1
         #print("SLOPE:", cc, slope,dist,ang,last_x,last_y,x,y)
         #print("SLOPE/DIST:", cc, slope, dist, dpass, spass)
         slopes.append(slope)
      last_x = x
      last_y = y

      cc = cc + 1
   hl = len(hist)
   hl = hl - 1
   if hl > 0:
      d_perc = dpass / hl
      s_perc = spass / hl
   else:
      d_perc = 0
      s_perc = 0

   if s_perc < .5 or d_perc < .5:
      print("FINAL SLOPE DIST TEST FAILED: ", trim_file)
      print("FINAL SLOPE DIST TEST FAILED: ", s_perc, d_perc)
      print("FINAL SLOPE DIST TEST FAILED: ", len(hist) - 1, spass, dpass)
      s_test = 0
   else:
      s_test = 1
      print("FINAL SLOPE DIST TEST PASSED: ", trim_file)
      print("FINAL SLOPE DIST TEST PASSED: ", s_perc, d_perc)
      print("FINAL SLOPE DIST TEST PASSED: ", len(hist) - 1, spass, dpass)

   return(s_test)

def three_point_test(hist):
   # if an object only has 3 points, then all 3 need to :
   # - fall on the same line / share common angles
   # - have equal distance from each other
   p1 = hist[0][1],hist[0][2]
   p2 = hist[1][1],hist[1][2]
   p3 = hist[2][1],hist[2][2]

   dt1 = calc_dist(p1, p2)
   dt2 = calc_dist(p2, p3)
   oa1 = find_angle(p1, p2)
   oa2 = find_angle(p2, p3)
   oa3 = find_angle(p1, p3)
   #print("P1:", p1)
   #print("P2:", p2)
   #print("P3:", p3)

   passed = 0
   if (dt2 -2 < dt1 < dt2 + 2) or (dt2 -2 < (dt1 * 2) < dt2 + 2) :
      print("Distance test passed")
      passed = passed + 1
   else:
      print("Distance test failed.", dt1, dt2)
   if oa2 -20 <= oa1 <= oa2 + 20:
      #print("Angle 1 test passed")
      passed = passed + 1
   else:
      print("Angle 1 test failed.", oa1, oa2)
   if oa3 -20 <= oa1 <= oa3 + 20:
      print("Angle 2 test passed")
      passed = passed + 1
   else:
      print("Angle 2 test failed.", oa1, oa3)
   if oa3 -20 <= oa2 <= oa3 + 20:
      print("Angle 3 test passed")
      passed = passed + 1
   else:
      print("Angle 3 test failed.", oa2, oa3)

   print("DT1/2:", dt1, dt2)
   print("OA1/2/3:", oa1, oa2, oa3)
   if passed >= 3:
      return(1)
   else:
      return(0)

def hist_cm_events(hist):
   max_cm = 0
   last_fc = 0
   motion_on = 0
   cm = 0
   event = []
   events = []
   hc = 0
   for fc, x, y, w, h,mx,my in hist:
      if (last_fc -1 < fc <= last_fc + 1) and last_fc > 0 : 
         cm = cm + 1
         motion_on = 1
         if len(event) == 0:
            event.append(hist[hc-1])

         event.append([fc,x,y,w,h,mx,my])
      else:
         if len(event) > 1:
            events.append(event)
         event = []
         motion_on = 0
         cm = 0
         # event ended
      if cm > max_cm:
         max_cm = cm
      last_fc = fc 
      hc = hc + 1

   if len(event) > 1:
      events.append(event)

   #for ev in events:
   #   print("EV:", ev)

   return(events, max_cm)   

def hist_eq_dist(hist):
   c = 0
   for fn,x,y,w,h in hist:
      if c >= 1:  
         dist = calc_dist((last_x,last_y),(x,y))
         fdist = calc_dist((fx,fy),(x,y))
         #print("FIRST LAST X/Y DIST:", fdist, dist)
         #print("LAST X/Y DIST:", dist)
      else:
        fx = x
        fy = y
         

      last_x = x
      last_y = y
      c = c + 1


def max_xy(x,y,w,h,max_x,max_y,min_x,min_y):

   if x + w > max_x: 
      max_x = x + w
   if y + h > max_y: 
      max_y = y + h
   if x < min_x: 
      min_x = x
   if y < min_y: 
      min_y = y
   return(max_x,max_y,min_x,min_y)

def find_min_max_dist(hist):
   max_x = 0
   max_y = 0
   min_x = 10000
   min_y = 10000
   for fn,x,y,w,h,mx,my in hist:   
      max_x, max_y,min_x,min_y = max_xy(x,y,w,h,max_x,max_y,min_x,min_y)

   return(max_x,max_y,min_x,min_y)

def straight_hist(hist):
   max_frame = max(map(lambda x: x[0], hist))
   min_frame = min(map(lambda x: x[0], hist))

   #print("MAX/MIN FRAME:", max_frame, min_frame)
   if max_frame < 10:
      return(0, "FAILED: max frame is less than 10.")

   points = []
   sizes = []
   for fn,x,y,w,h,mx,my in hist:   
      size  = w * h
      sizes.append(size)
      point = x+mx,y+my
      points.append(point)
  
   #print ("POINTS:", points)




   #point_test = test_points(points)
   #if point_test == 0:
   #   return(0, "FAILED: point test failed.")
   

   max_x = max(map(lambda x: x[0], points))
   max_y = max(map(lambda x: x[1], points))
   min_x = min(map(lambda x: x[0], points))
   min_y = min(map(lambda x: x[1], points))

   dist = calc_dist((min_x,min_y),(max_x,max_y))
   print("MX/MN XY:", min_x, min_y, max_x,max_y)
 
   sci_peaks = signal.find_peaks(sizes)
   peaks = len(sci_peaks[0])
   peaks_per_frame = peaks / len(hist)


   if peaks > 0:
      peaks_per_px = dist / peaks
   else:
      peaks_per_px = 0
   
   print("SCI:", sci_peaks)
   print("PEAKS:", peaks)
   print("HIST LEN :", len(hist))
   print("PEAKS PER FRAME:", peaks_per_frame)
   print("PEAKS PER DISTANCE:", peaks_per_px)
   print("DISTANCE:", dist)

   if dist < 5:
      return(0, "FAILED: too short. " + str(dist))

   if peaks > 25:
      return(0, "FAILED: too many peaks. " + str(peaks))

 
   return(1, "Passed straight hist tests.")

def meteor_three_point_test(object):
   #print("Designed for short objects of 3 points or less.")
   print("Confirm all 3 points fall on .")

def best_fit_slope_and_intercept(xs,ys):
    xs = np.array(xs, dtype=np.float64)
    ys = np.array(ys, dtype=np.float64)
    m = (((mean(xs)*mean(ys)) - mean(xs*ys)) /
         ((mean(xs)*mean(xs)) - mean(xs*xs)))

    b = mean(ys) - m*mean(xs)

    return m, b

def meteor_test_noise(hist):
   
   objs_per_frame = {}
   for fn,x,y,w,h,mx,my in hist:
      if fn not in objs_per_frame.keys():
         objs_per_frame[fn] = 1
      else:
         objs_per_frame[fn] = objs_per_frame[fn] + 1
   total_obf = 0
   for obf in objs_per_frame:
      total_obf = total_obf + objs_per_frame[obf]

   if len(objs_per_frame) > 0:
      perc = total_obf / len(objs_per_frame)
   
   #print("NOISETEST:" + str(perc), objs_per_frame)
   if perc > 2.5 and len(hist) > 7:

      return(0, "NOISE TEST FAILED:" + str(perc))
   else:
      return(1, "NOISE TESTS PASSED:" + str(perc))

def meteor_test_moving(hist):

   (max_x,max_y,min_x,min_y) = find_min_max_dist(hist)
   dist = calc_dist((min_x,min_y),(max_x,max_y))
   if dist < 3:
      return 0
   else:
      return 1


def meteor_test_dupe_px(object):
   status = 1
   reason = "DUPE PIXEL TEST PASSED"
   hist = object['history']
   xs = []
   ys = []
   for fn,x,y,w,h,mx,my in hist:
      cx = int(x+ (w/2))
      cy = int(y+ (h/2))
      xs.append((cx,cy))
   ux = list(set(xs))
   ul = len(ux)
   tl = len(hist)

   if tl > 0:
      uperc = ul / tl
   else:
      uperc = 0

   if uperc < .4:
      status = 0
      reason = "DUPE PIXEL TEST FAILED: Percentage of unique pixels to total pixels is too low. " 

   reason = reason + str(uperc)


   return(status,reason)

def meteor_test_fit_line(object):
   hist = object['history']
   xs = []
   ys = []
   for fn,x,y,w,h,mx,my in hist:
      cx = int(x+ (w/2))
      cy = int(y+ (h/2))
      xs.append(cx)
      ys.append(cy)
   m,b = best_fit_slope_and_intercept(xs,ys)

   max_x = max(xs)
   max_y = max(ys)
   min_x = min(xs)
   min_y = min(ys)
   line_dist = calc_dist((min_x,min_y),(max_x,max_y))
   safe_dist = line_dist / 12 

   if safe_dist < 5:
      safe_dist = 5 
   if safe_dist > 10:
      safe_dist = 10 
   #print("SAFE DISTANCE: ", safe_dist) 
   regression_line = []
   for x in xs: 
      regression_line.append((m*x)+b)


   good = 0
   for i in range(0,len(regression_line)):
      fn,x,y,w,h,mx,my = hist[i]
      cx = int(x+ (w/2))
      cy = int(y+ (h/2))
      ry = regression_line[i]
      dist = calc_dist((cx,cy),(cx,ry))
      #print("REG:", dist)
      if dist < safe_dist:
         good = good + 1

   match_perc = good / len(regression_line)
   #print("LINE FIT total", len(regression_line))
   #print("LINE FIT good", good)
   #print("METEOR TEST: LINE FIT %", match_perc)

   #import matplotlib.pyplot as plt
   #from matplotlib import style
   #style.use('ggplot')

   #plt.scatter(xs,ys,color='#003F72')
   #plt.plot(xs, regression_line)
   #plt.show()

   return(match_perc)

def meteor_test_straight(object):
   t = 1
   #print("Test if/which meteor points fall on straight line")
   #print("Fail if less than 80% of points fall on line.")
   #print("Remove non-matching points from history") 
   #print("Return: 0 or 1 and 'cleaned' history.")

def meteor_test_peaks(object):
   status = 1
   oid = object['oid']
   reason = "PEAK TEST PASSED: " + str(oid) + ": Peak test passed."
   #print("Test how many max pixel peaks exist in history.")
   #print("Try to identify a plane, by noting repeating peaks.")
   #print("Disqualify object if too many peaks exist / repeat.")


   points = []
   sizes = []
   hist = object['history']
   for fn,x,y,w,h,mx,my in hist:
      size  = w * h
      sizes.append(size)
      point = x+mx,y+my
      points.append(point)
 

   sci_peaks = signal.find_peaks(sizes,threshold=3)
   total_peaks = len(sci_peaks[0])
   total_frames = len(points) 
   if total_frames > 0:
      peak_to_frame = total_peaks / total_frames

   print("SCI:", sci_peaks)
   print("PEAKS:", total_peaks)
   print("FRAMES:", total_frames)
   print("PEAK TO FRAME:", peak_to_frame)
   if total_peaks > 30:
      status = 0
      reason = "PEAK TEST FAILED: too many peaks:" + str(total_peaks)
   if peak_to_frame > .50:
      status = 0
      reason = "PEAK TEST FAILED: peaks/to frame is to high:" + str(peak_to_frame)
   
   reason = reason + str(sci_peaks[0])


   return(status, reason)

def meteor_test_distance(object):
   oid = object['oid']
   status = 1
   reason = "DISTANCE TEST PASSED: " + str(oid) + ": Distance test passed. "
   hist = object['history']
   (max_x,max_y,min_x,min_y) = find_min_max_dist(hist)

   dist = calc_dist((min_x,min_y),(max_x,max_y))
   if dist < 5:
      status = 0 
      reason = "DISTANCE TEST FAILED: " + str(oid) + ": Distance test failed. Max distance is < 5 "

   reason = reason + " dist = " + str(dist)

   #print("Determine the max from min and max. ")
   #print("Determine pixel movement per frame.")
   #print("Determine distance between object segments.")
   #print("Fail if distance is too short. < 5px")
   #print("Fail if px per frame is too little (object moving too slow).  ")

   return(status, reason)

def meteor_test_if_star(object):
   t = 1
   #print("Designed to identify stars.")
   #print("Test to see if there is no/small movement over time, indicating a stationary object.")
   #print("Return 1 if the object is a star, else 0 for non-star.")
   #print("Clean history to remove non-moving objects and return cleaned history too.")

def meteor_test_hist_len(object):
   t = 1
   #print("Return 0 if the length is too short or too long.")
   #print("Return 0 if there are multiple gaps in the history. (blinking lights)")
   #print("Return 0 if there are multiple gaps in the history. (blinking lights)")

   oid = object['oid']
   status = 1
   reason = "HISTORY LENGTH TEST PASSED: " + str(oid) 

   hist = object['history']
   hist_len = len(hist)

   if hist_len > 200:
      status = 0
      reason = "HISTORY LENGTH TEST FAILED" + str(oid) + ": Hist length of object is too long > 200."
   if hist_len < 3:
      status = 0
      reason = "HISTORY LENGTH TEST FAILED: " + str(oid) + " Hist length of object is too short < 3."


   first_frame = hist[0][0]
   last_frame = hist[-1][0]
   elp_frames = last_frame - first_frame

   cm = 0
   max_cm = 0
   gaps = 0
   max_gaps = 0
   gap_events = 0
   last_frame = 0
   for fn,x,y,w,h,mx,my in hist:
      #print ("METEOR TEST: ", last_frame, fn, max_cm, cm, max_gaps, gaps)
      if last_frame + 1 == fn and last_frame > 0:
         cm = cm + 1
      else:
         cm = 0
         if last_frame > 5 :
            gaps = gaps + (fn - last_frame)
            if fn - last_frame > 5:
               gap_events = gap_events + 1
      if cm > max_cm:
         max_cm = cm 
      if gaps > max_gaps:
         max_gaps = gaps 
      last_frame = fn

   # max cm per hist len 1 is best score. < .5 is fail.
   if max_cm > 0:
      cm_hist_len_ratio = max_cm / len(hist) 
   else:
      cm_hist_len_ratio = 0

   if max_gaps > 25:
      status = 0
      reason = "GAP TEST FAILED: " + str(oid) + " Gap test failed. Max gapped frames > 25 / " + str(max_gaps)
   if gap_events > 1:
      status = 0
      reason = "GAP TEST FAILED: " + str(oid) + " Gap test failed. Too many gap events > 2 / " + str(gap_events)

   return(status, reason)

def meteor_test_cons_motion(object):
   print("Determine the consectutive motion inside each history block.")
   print("Return 0 if the cons_motion is too slow.") 
   print("Return 0 if the cons_motion exists but is separated by more than 3 blocks of dead space.") 





def test_object2(object):
   obj_data = {}
   #print("TEST OBJECT: ", object['oid'])
   #print(object)

   # NEW TESTS# 

   status, reason = meteor_test_hist_len(object)
   print("METEOR TEST HIST LEN:", status, reason)
   if status == 0:
      return(0, reason, obj_data)

   status, reason = meteor_test_peaks(object)
   print("METEOR TEST PEAKS:", status, reason)
   if status == 0:
      return(0, reason, obj_data)

   status, reason = meteor_test_distance(object)
   print("METEOR TEST HIST LEN:", status, reason)
   if status == 0:
      return(0, reason, obj_data)

   match_perc = meteor_test_fit_line(object)
   if match_perc < .5:
      tests_passed = 0
      return(0, "Line fit test failed:" + str(match_perc), obj_data)



   hist = object['history']
   (max_x,max_y,min_x,min_y) = find_min_max_dist(hist)
   hist_len = len(hist)
   if hist_len > 200:
      return(0, "FAILED: object history is more than 200 frame.", obj_data)
   if hist_len < 3:
      return(0, "FAILED: object history is less than 3 frames." + str(hist_len), obj_data)
   dist = calc_dist((min_x,min_y),(max_x,max_y))
   if dist < 5:
      return(0, "FAILED: object moves less than 5 pixels total.", obj_data)

   #hist_eq_dist(hist)


   first_frame = hist[0][0]
   last_frame = hist[-1][0] 
   elp_frames = last_frame - first_frame
   if elp_frames > 0:
      px_per_frame = dist / elp_frames 
   else :
      px_per_frame = 0
   if px_per_frame < .3:
      return(0, "FAILED: px per frame is too low: " + str(px_per_frame), obj_data)
   
   cme,max_cm = hist_cm_events(hist)
   #print("CME LEN:", len(cme))
   #print("CME:", cme)

   if len(cme) > 10:
      return(0, "FAILED: object has too many distinct CM Events: ", len(cme))
   obj_data['min_max_xy'] = [min_x,min_y,max_x,max_y]
   good_cmes = []
  
   for ev in cme:
      tpt = 1
      if len(ev) > 2:
         ev_max_x = 0
         ev_max_y = 0
         ev_min_x = 10000
         ev_min_y = 10000
         for fn,x,y,w,h,mx,my in ev:   
            ev_max_x, ev_max_y,ev_min_x,ev_min_y = max_xy(x,y,w,h,ev_max_x,ev_max_y,ev_min_x,ev_min_y)

         cme_dist = calc_dist((ev_min_x,ev_min_y), (ev_max_x,ev_max_y))
         print("EV:", ev, ev_min_x, ev_min_y, ev_max_x, ev_max_y, cme_dist)
         if len(ev) <= 5:
            tpt = three_point_test(ev)
         if cme_dist > 5 and tpt == 1:
            good_cmes.append(ev)

   #for gcme in good_cmes:
   #   print("CME:", gcme)

   if len(good_cmes) == 0:
      return(0, "FAILED: No good CMEs longer than 5 px: " + str(px_per_frame), obj_data)

   hist_ok, reason = straight_hist(hist)              
   if hist_ok == 0:
      return(0, "FAILED: Straight Hist Tests: " + reason, obj_data)

   #print("CME LEN:", len(cme))
   if len(cme) > 0:
      good_bad_cme = len(good_cmes) / len(cme)





   print("\tHist Len: ", hist_len)
   print("\tHist : ", hist)
   print("\tMIN/MAX X/Y : ", min_x,min_y,max_x,max_y)
   print("\tMAX/MIN DISTANCE:", dist)
   print("\tPX PER FRAME:", px_per_frame)

   print("\tTotal Possible CMEs: ", len(cme))
   print("\tTotal Good CMEs: ", len(good_cmes))
   print("\t Good/Bad CMEs: ", good_bad_cme)
   print("\t MAX CM: ", max_cm)

   if good_bad_cme < .4:
      return(0, "FAILED: Good Bad CME too high: " + str(good_bad_cme), obj_data)


   #if good_bad_cme < .5:
   #   return(0, "FAILED: Good/BAD CME Ratio too low. " + str(good_bad_cme), obj_data)

   
   


   return(1, "Passed I guess?", obj_data)


def test_object(object, trim_file, stacked_np):
   w,h = stacked_np.shape
   status = []
   # distance of object
   # object speed / pixels per frame
   # linear motion -- does the object move in the same direction
   # straight line -- do 3 or more points fit a line

   oid, start_x, start_y, hist = object
   print("HIST:", hist)
   hist = clean_hist(hist)
   print("CLEANHIST:", hist)
   if 3 <= len(hist) <= 5:
     
      print("Three point object test needed.", hist)
      tpt = three_point_test(hist)
   else:
      tpt = 1
   
   sl_test = 0
   straight_line = 99
   slope = 0
   dist = 0
   last_x = 0
   last_y = 0
   min_x = w
   min_y = h
   max_x = 0  
   max_y = 0
   print ("HIST0:", hist)
   first = hist[0]
   last = hist[-1]
   p1 = first[1], first[2]
   p2 = last[1], last[2]
   #hist_len = len(object[3]) - 1
   hist_len = len(hist)
   elp_frms = last[0] - first[0]
   cns_mo = 0
   max_cns_mo = 0
   peaks = 0
   last_fn = None
   size_frame_test = 0
   max_size = 0

   if elp_frms > 0:
      elp_time = elp_frms / 25
   else:
      elp_time = 0


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

   if hist_len < 5:
      cm_test = 1


   if hist_len > 2:
      slope = find_slope(p1,p2)
      print("DIST: ", p1,p2)
      dist = calc_dist(p1,p2)

   sizes = []
   if hist_len > 2:
      if hist_len > 3:
         ix = int(hist_len/2)
      else:
         ix = 1
      straight_line = compute_straight_line2(hist[0][1],hist[0][2],hist[ix][1],hist[ix][2],hist[-1][1],hist[-1][2])
      peaks = 0
      max_size = 0
      last_size = 0
      bigger = 0
      for line in hist:
         fn, x,y,w,h,fx = line 
         #print("WIDTH,HEIGHT:", w,h)
         if last_x > 0 and last_y > 0:
            seg_dist = calc_dist((last_x,last_y),(x,y))
         size = w * h
         sizes.append(size)
         if w * h > max_size:
            max_size = w * h
         if size > last_size and bigger == 0:
            bigger = 1
         else:
            bigger = 0
         if x > max_x:
            max_x = x 
         if y > max_y:
            max_y = y  
         if x < min_x:
            min_x = x 
         if y < min_y:
            min_y = y
    

            
         if last_fn is not None:
            if fn - 1 == last_fn or fn -2 == last_fn:
               cns_mo = cns_mo + 1
               if cns_mo > max_cns_mo:
                  max_cns_mo = cns_mo
            else:
               if cns_mo > max_cns_mo:
                  max_cns_mo = cns_mo
               cns_mo = 0

         last_x = x
         last_y = y
         print(line)
         last_fn = fn
         last_size = size

   if max_cns_mo > 0:
      max_cns_mo = max_cns_mo + 1

   if max_cns_mo > 5:
      cm_test = 1

  
   if len(sizes) > 1:
      sci_peaks = signal.find_peaks(sizes)
      peaks = len(sci_peaks[0])
      print("SCI:", sci_peaks)
 
   if peaks > 0 and max_cns_mo > 0:
      peaks_to_frame_ratio = peaks / max_cns_mo
   else:
      peaks_to_frame_ratio = 0

   if peaks > 0 and dist > 0:
      peaks_to_dist_ratio = peaks / dist 
   else:
      peaks_to_dist_ratio = 0
   if max_size > 0 and peaks > 0:
      size_to_peak_ratio = max_size/ peaks
   else:
      size_to_peak_ratio = 0
     
 
   if elp_frms < 7 and max_size > 1500:
      print("Too big for too short of frames")
      size_frame_test = 0
   else:
      size_frame_test = 1

   if max_cns_mo > 0:
      px_per_frame = dist / max_cns_mo 
   else:
      px_per_frame = 0
   if max_cns_mo > 10:
      px_per_frame = dist / max_cns_mo

    
   meteor_yn = 0
   if tpt == 1 and cm_test > .5 and max_cns_mo >= 3 and px_per_frame >= .6 and dist >= 4 and straight_line < 5 and elp_time < 7 and peaks_to_frame_ratio <= .7 and peaks_to_dist_ratio < .45 and size_frame_test == 1:
      print("METEOR")
      meteor_yn = 1
      sl_test =slope_test(hist, trim_file)
   else:
      print("METEOR TEST FAILED.")
      print("SLOPE TEST: ", sl_test)
      #if sl_test == 0:
      #   meteor_yn = 0
   meteor_data = {}
   meteor_data['oid'] = oid[0]
   meteor_data['cm_test'] = cm_test
   meteor_data['max_cns_mo'] = max_cns_mo 
   meteor_data['len_test'] = len_test
   meteor_data['len_hist'] = len(hist)
   meteor_data['elp_time'] = elp_time
   meteor_data['elp_frms'] = elp_frms
   meteor_data['box'] = [min_x,min_y,max_x,max_y]

   meteor_data['dist'] = dist
   meteor_data['sl_test'] = sl_test
   meteor_data['peaks'] = peaks
   meteor_data['peaks_to_frame_ratio'] = peaks_to_frame_ratio
   meteor_data['peaks_to_dist_ratio'] = peaks_to_dist_ratio
   meteor_data['size_to_peak'] = size_to_peak_ratio
   meteor_data['first'] = first
   meteor_data['last'] = last
   meteor_data['hist'] = hist
   meteor_data['max_size'] = max_size 
   meteor_data['size_frame_test'] = size_frame_test
   meteor_data['straight_line'] = straight_line
   meteor_data['px_per_frame'] = px_per_frame
   meteor_data['meteor_yn'] = meteor_yn
   meteor_data['tests'] = {} 

   #if first[0] > 20 and cm_test > .5 and max_cns_mo >= 3 and px_per_frame >= .6 and dist >= 4 and straight_line < 5 and elp_time < 7 and peaks_to_frame_ratio <= .4 and peaks_to_dist_ratio <.4 and size_frame_test == 1:

   if first[0] > 20:
      meteor_data['tests']['early_frame'] = 1
   else:
      meteor_data['tests']['early_frame'] = 0
   if cm_test > .5:
      meteor_data['tests']['cm'] = 1
   else:
      meteor_data['tests']['cm'] = 0
   if max_cns_mo >= 3:
      meteor_data['tests']['max_cns_mo'] = 1
   else:
      meteor_data['tests']['max_cns_mo'] = 0
   if px_per_frame >= .6:
      meteor_data['tests']['px_per_frame'] = 1
   else:
      meteor_data['tests']['px_per_frame'] = 0
   if dist >= .6:
      meteor_data['tests']['dist'] = 1
   else:
      meteor_data['tests']['dist'] = 0
   if straight_line <= 5 :
      meteor_data['tests']['straight_line'] = 1
   else:
      meteor_data['tests']['straight_line'] = 0
   if elp_time < 7  :
      meteor_data['tests']['elp_time'] = 1
   else:
      meteor_data['tests']['elp_time'] = 0
   if peaks_to_frame_ratio <= .5 :
      meteor_data['tests']['peaks_to_frame_ratio'] = 1
   else:
      meteor_data['tests']['peaks_to_frame_ratio'] = 0
   if peaks_to_dist_ratio < .4 :
      meteor_data['tests']['peaks_to_dist_ratio'] = 1
   else:
      meteor_data['tests']['peaks_to_dist_ratio'] = 0
   meteor_data['tests']['size_frame_test'] = 1
   meteor_data['tests']['sl_test'] = sl_test
   meteor_data['tests']['tpt'] = tpt


   print("\n-----------------")
   print ("Object ID: ", oid)
   print("-----------------")
   print ("CM Test: ", cm_test)
   print ("Cons Mo: ", max_cns_mo)
   print ("LEN Test: ", len_test, len(hist))
   print ("Elapsed Time: ", elp_time)
   print ("Elapsed Frames: ", elp_frms)
   print ("Dist: ", dist)
   print ("Peaks: ", peaks)
   print ("Peak To Frame Ratio: ", peaks_to_frame_ratio, peaks, "/", max_cns_mo, )
   print ("Peak To Dist Ratio: ", peaks_to_dist_ratio)
   print ("Size To Peak: ", size_to_peak_ratio)
   print ("First: ", first)
   print ("Last: ", last)
   print ("History:")
   for h  in hist:
      print("HIST:", h)
   print ("Slope: ", slope)
   print ("Max Size: ", max_size)
   print ("Size Frame Test: ", size_frame_test)
   print ("Straight: ", straight_line)
   print ("PX Per Frame: ", px_per_frame)
   print ("Three Point Test: ", tpt)
   print ("Meteor Y/N: ", meteor_yn)
   print("")
   for test in meteor_data['tests']:
      print("TEST:", test, meteor_data['tests'][test])
      #print(test, meteor_data[test])
   return(meteor_yn, meteor_data)

def test_points(points):
   max_x = max(map(lambda x: x[0], points))
   max_y = max(map(lambda x: x[1], points))
   min_x = min(map(lambda x: x[0], points))
   min_y = min(map(lambda x: x[1], points))
   max_dist = calc_dist((min_x,min_y),(max_x,max_y))
   first_last_angle = find_angle(points[0], points[-1])
   dist_per_point = max_dist / len(points)

   print("MAX DIST IS:", max_dist)
   print("DIST PER POINT:", dist_per_point)
   print("FIRST LAST ANGLE:", first_last_angle)
   pc = 0
   ap = 0
   for point in points:
      if pc + 1 <= len(points) - 1:
         next_point = points[pc+1]
         seg_dist = calc_dist(point, next_point) 
         dist_from_first = calc_dist(points[0], point) 
         angle = find_angle(point, next_point)
         if first_last_angle -10 <= angle <= first_last_angle + 10:
            ap = ap + 1

      pc = pc + 1
   app = ap / len(points)
   if app < .5:
      print ("Angle Pass FAILED %:", app)
      return(0)
 
   return(1)

def compute_straight_line2(x1,y1,x2,y2,x3,y3):
   if x1 - x2 == 0 :
      x1 = x1 + 1
   if x3 - x2 == 0 :
      x3 = x3 + 1
   print("X", x1,x2,x3)
   print("Y", y1,y2,y3)
   diff = math.atan((y2-y1)/(x2-x1)) - math.atan((y3-y2)/(x3-x2))
   return(diff)

def compute_straight_line(x1,y1,x2,y2,x3,y3):
   print ("COMP STRAIGHT", x1,y1,x2,y2,x3,y3)
   if x1 - x2 != 0:
      a = (y1 - y2) / (x1 - x2)
   else:
      a = (y1 - y2) / 1
   if x1 - x3 != 0:
      b = (y1 - y3) / (x1 - x3)
   else:
      b = (y1 - y3) / 1 
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

def find_angle(p1,p2):
   myrad = math.atan2(p1[1]-p2[1],p1[0]-p2[0]) 
   mydeg = math.degrees(myrad)
   return(mydeg)

def find_slope(p1,p2):
   (x1,y1) = p1
   (x2,y2) = p2
   top = y2 - y1
   bottom = x2 - y2
   if bottom != 0:
      slope = top / bottom
   else:
      slope = 0
   #print("SLOPE: TOP/BOTTOM ", top, bottom)
   #print(x1,y1,x2,y2,slope)
   return(slope)

    
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

def test_objects(moving_objects, trim_file, stacked_np):
   all_objects = []
   passed = 0
   for object in moving_objects:
      meteor_yn,meteor_data = test_object(object, trim_file, stacked_np)
      if meteor_yn == 1:
         passed = 1
      all_objects.append(meteor_data)
   return(passed, all_objects)
   

def complete_scan(trim_file, meteor_found, found_objects):
   setup_dirs(trim_file)
   el = trim_file.split("/")
   fn = el[-1]
   base_dir = trim_file.replace(fn,"")
   confirm_file = base_dir + "/data/" + fn
   confirm_file = confirm_file.replace(".mp4", "-confirm.txt")
   meteor_file = confirm_file.replace("-confirm.txt", "-meteor.txt")
   obj_fail = confirm_file.replace("-confirm.txt", "-objfail.txt")



   if meteor_found >= 1:
      print ("METEOR")
      mt = open(meteor_file, "w")
      mt.write(str(found_objects))
      mt.close()
      trim_meteor(meteor_file)
   else:
      print ("NO METEOR")
      mt = open(obj_fail, "w")
      mt.write(str(found_objects))
      mt.close()

      cmd = "./stack-stack.py stack_vid " + trim_file + " mv"
      os.system(cmd)



def draw_obj_image(stacked_image_np, moving_objects,trim_file, stacked_np):
   colors = None
   stacked_image_np_gray = stacked_image_np
   stacked_image_np = cv2.cvtColor(stacked_image_np, cv2.COLOR_GRAY2RGB)
   oc = 0
   for object in moving_objects:
    
      meteor_yn,meteor_data = test_object(object,trim_file, stacked_np)
      oid, start_x, start_y, hist = object
      if len(hist) - 1 > 1:
         colors = find_color(oc)
         print("HIST:", oid, hist)
         min_x, min_y, max_x, max_y = object_box(object, stacked_image_np_gray) 
         cv2.rectangle(stacked_image_np, (min_x, min_y), (max_x, max_y), (255,255,255), 2)
         for line in hist:
            fn, x,y,w,h,fx = line 
            #print(x,y)
            dd = int(w / 2)
            #cv2.rectangle(stacked_image_np, (x, y), (x + 3, y + 3), (colors), 2)
            cv2.circle(stacked_image_np, (x,y), dd, (255), 1)
            #cv2.putText(stacked_image_np, str(oid),  (x,y), cv2.FONT_HERSHEY_SIMPLEX, .4, (colors), 1)
            if min_y < 100:
               cv2.putText(stacked_image_np, str(oid),  (min_x,min_y+15), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
            else:
               cv2.putText(stacked_image_np, str(oid),  (min_x,min_y- 15), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
         if meteor_yn == 1:
            print ("XYMETEOR:", min_x, min_y)
            if min_y < 100:
               cv2.putText(stacked_image_np, str("Meteor"),  (min_x,min_y+ 15), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
            else:
               cv2.putText(stacked_image_np, str("Meteor"),  (min_x,min_y- 5), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
         oc = oc + 1
 
   return(stacked_image_np)


def trim_meteor(trim_file, start_frame, end_frame):
   meteor_video_file = trim_file.replace(".mp4", "-meteor.mp4")
   # buffer start / end time
   # adjust meteor trim number for exact time computations? Needed to support more than 1 meteor per trim file...
   start_frame = int(start_frame)
   end_frame = int(end_frame)
   elp_frames = end_frame - start_frame 
   if start_frame > 25:
      start_frame = start_frame - 50
      elp_frames = elp_frames + 75
   else:
      start_frame = 0
      elp_frames = elp_frames + 75
   start_sec = start_frame / 25
   elp_sec = elp_frames/25
   print ("START FRAME: ", start_frame)
   print ("END FRAME: ", end_frame)
   print ("DUR FRAMES: ", elp_frames)
   print ("START SEC: ", start_sec)
   print ("DUR SEC: ", elp_sec)
   if start_sec <= 0:
      start_sec = 0
   if elp_sec <= 2:
      elp_sec = 3
   ffmpeg_trim(trim_file, start_sec, elp_sec, meteor_video_file)
   cmd = "./stack-stack.py stack_vid " + meteor_video_file + " mv"
   os.system(cmd)
   print("STACK", cmd)



def trim_meteor_old(meteor_file):
   print ("TRIM METEOR", meteor_file)
   #el = meteor_file.split("/")
   eld = meteor_file.split("-meteor")
   base = eld[0]
   trim_file = base.replace("data/", "")
   trim_file = trim_file + ".mp4"

   #trim_file = meteor_file.replace("-meteor.txt", ".mp4")
   #trim_file = trim_file.replace("data/", "")

   meteor_video_file = meteor_file.replace(".txt", ".mp4")
   meteor_video_file = meteor_video_file.replace("data/", "")
   file_exists = Path(meteor_video_file)
   if file_exists.is_file() == True:
      print ("ALREADY DONE.")
      return()

   #print ("TRIM FILE:", trim_file)
   dur = check_duration(trim_file)
   print ("DUR: ", dur)
   if int(dur) < 5:
      print ("Duration is less than 5.", dur)
      cmd = "cp " + trim_file + " " + meteor_video_file
      print(cmd)
      os.system(cmd)

      cmd = "./stack-stack.py stack_vid " + trim_file + " mv"
      os.system(cmd)
      print("STACK", cmd)
      cmd = "./stack-stack.py stack_vid " + meteor_video_file + " mv"
      os.system(cmd)
      print("STACK", cmd)

      return()
   else:
      print ("Duration is more than 5 sec", dur)
   fdf = open(meteor_file)
   d = {}
   code = "object_data= "
   for line in fdf:
      code = code + line
   exec (code,  d)
   print(d['object_data'])
   for object in d['object_data']:
      #print(object[0], object[1], object[2],object[3],object[8])
      print("OBJ8:", object[8])
      if len(object[8]) == 0:
         # meteor found
         print("meteor found", object[2], object[3])
         start_frame = object[2][0]
         end_frame = object[3][0]
         elp_frames = end_frame - start_frame
         if start_frame > 25:
            start_frame = start_frame - 50
            elp_frames = elp_frames + 75
         else:
            start_frame = 0
            elp_frames = elp_frames + 75
         start_sec = start_frame / 25
         elp_sec = elp_frames/25
         print ("START FRAME: ", start_frame)
         print ("END FRAME: ", end_frame)
         print ("DUR FRAMES: ", elp_frames)
         print ("START SEC: ", start_sec)
         print ("DUR SEC: ", elp_sec)
         if start_sec <= 0:
            start_sec = 0
         if elp_sec <= 2:
            elp_sec = 3
         ffmpeg_trim(trim_file, start_sec, elp_sec, meteor_video_file)
         cmd = "./stack-stack.py stack_vid " + trim_file + " mv"
         os.system(cmd)
         print("STACK", cmd)
         cmd = "./stack-stack.py stack_vid " + meteor_video_file + " mv"
         os.system(cmd)
         print(cmd)


def check_duration(trim_file):
   cmd = "/usr/bin/ffprobe " + trim_file + ">checks.txt 2>&1"
   print (cmd)
   s= 0
   try:
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
      efp = open("checks.txt")
      stream_found = 0
      for line in efp:
         if "Duration" in line:
            el = line.split(" ")
            dur_str = el[3]
            dur, rest = dur_str.split(".")
            h,m,s = dur.split(":")
            print(int(s))
   except:
      print("DUR CHECK FAILED")
      s = 0
   return(s)

def check_if_done(video_file):
   el = video_file.split("/")
   fn = el[-1]
   bd = video_file.replace(fn, "")
   fn = fn.replace(".mp4", "")
   meteor_file = bd + "data/" + fn + "-meteor.txt"
   objfail = bd + "data/" + fn + "-objfail.txt"
   confirm = bd + "data/" + fn + "-confirm.txt"
   reject = bd + "data/" + fn + "-reject.txt"
   file_exists = Path(meteor_file)
   if file_exists.is_file() is True:
      return(1)
   file_exists = Path(objfail)
   if file_exists.is_file() is True:
      return(1)
   file_exists = Path(confirm)
   if file_exists.is_file() is True:
      return(1)
   file_exists = Path(reject)
   if file_exists.is_file() is True:
      return(1)
   print(meteor_file)
   print(objfail)
   print(confirm)
   print(reject)
   return(0)

def check_final_stack(trim_stack, object):
   min_x, min_y, max_x, max_y = object['box']
   print("MIN/MAX:",min_x,min_y,max_x,max_y)
   trim_stack_np = np.asarray(trim_stack)
   crop_img = trim_stack_np[min_y:max_y,min_x:max_x] 

   max_px = np.max(crop_img)
   mean_px = np.mean(crop_img)
   max_diff = max_px - mean_px
   thresh = max_px - (max_diff/2)

   _, thresh_img = cv2.threshold(crop_img, thresh, 255, cv2.THRESH_BINARY)
   #thresh_obj = cv2.dilate(thresh_img.copy(), None , iterations=1)
   #(_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   #print("LEN CNTS:", len(cnts))
   cv2.imshow("pepe", crop_img)
   cv2.waitKey(1)
   cv2.imshow("pepe", thresh_img)
   cv2.waitKey(1)
