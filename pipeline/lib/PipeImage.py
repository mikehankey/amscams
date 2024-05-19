"""
 
   Pipeline Image Processing Functions

"""
from PIL import ImageFont, ImageDraw, Image, ImageChops
from lib.PipeUtil import load_json_file
import numpy as np
import cv2
import os
from lib.DEFAULTS import *
from lib.PipeUtil import cfe
import glob
import cv2

def rotate_bound(image, angle):
    # grab the dimensions of the image and then determine the
    # center
    (h, w) = image.shape[:2]
    (cX, cY) = (w // 2, h // 2)
    # grab the rotation matrix (applying the negative of the
    # angle to rotate clockwise), then grab the sine and cosine
    # (i.e., the rotation components of the matrix)
    M = cv2.getRotationMatrix2D((cX, cY), -angle, 1.0)
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    # compute the new bounding dimensions of the image
    nW = int((h * sin) + (w * cos))
    nH = int((h * cos) + (w * sin))
    # adjust the rotation matrix to take into account translation
    M[0, 2] += (nW / 2) - cX
    M[1, 2] += (nH / 2) - cY
    # perform the actual rotation and return the image
    return cv2.warpAffine(image, M, (nW, nH))

def restack_meteor(video_file):
   if "mp4" in video_file:
      jsf = video_file.replace(".mp4", ".json")
   elif "json" in video_file: 
      jsf = video_file
      video_file = jsf.replace(".json", ".mp4") 
   
   js = load_json_file(jsf)
   sd_file = js['sd_video_file']
   if "hd_trim" in js:
      hd_file = js['hd_trim']
   else:
      hd_file = None
   #print("SD:", sd_file)
   #print("HD:", hd_file)
   print("stacking")
   stack_frame, stack_file = quick_video_stack(sd_file)
   print("done stacking")
   js['sd_stack'] = stack_file
   if hd_file is not None:
      stack_frame, stack_file = quick_video_stack(hd_file)
      js['hd_stack'] = stack_file
   else:
      js['hd_stack'] = ""


def quick_video_stack(video_file, count = 0, save=1):
   frames = []
   #fps = int(count)/1499
   #fps = int(60 / count)
   fps_text = f"fps=.1"
   img_file = video_file.replace(".mp4","-stacked.jpg")
   temp_dir = "/mnt/ams2/tmp/st/"
   if cfe(temp_dir, 1) == 0:
      os.makedirs(temp_dir)
   if count == 0:
      cmd = f"/usr/bin/ffmpeg -i {video_file} {temp_dir}frames%03d.jpg > /dev/null 2>&1"
   else:
      cmd = f"/usr/bin/ffmpeg -i {video_file} -vf {fps_text} -vframes {count} {temp_dir}frames%03d.jpg > /dev/null 2>&1"
   print(cmd)
   os.system(cmd)
   files = glob.glob(temp_dir + "*.jpg")
   for file in files:
      print("stacked", file)
      frame = cv2.imread(file)
      frames.append(frame)
   stack_frame = stack_frames(frames, 1, None, "day")
   os.system("rm " + temp_dir + "*")
   if save == 1 and stack_frame is not None:
      #print("SAVED NEW STACK:", img_file)
      cv2.imwrite(img_file, stack_frame)
      stack_frame_tn = cv2.resize(stack_frame, (320,180))
      img_file_half = img_file.replace("-stacked.jpg", "-half-stack.jpg")
      img_file_tn = img_file.replace(".jpg", "-tn.jpg")
      img_file_obj_tn = img_file.replace(".jpg", "obj-tn.jpg")
      cv2.imwrite(img_file_tn, stack_frame_tn)
      cv2.imwrite(img_file_obj_tn, stack_frame_tn)
      stack_frame_half = cv2.resize(stack_frame, (960,540))
      cv2.imwrite(img_file_half, stack_frame_half)

   return(stack_frame, img_file)
  


def stack_frames(frames, skip = 1, resize=None, sun_status="day"):

   if len(frames) == 0:
      return(None)

   stacked_image = None
   fc = 0
   #print("FRAMES:", len(frames))
   #print("SUN:", sun_status)
   for frame in frames:
      if frame is None:
         continue
      try:
         avg_px = np.mean(frame)
      except: 
         print("FRAME PROB:", frame)
         avg_px = 255
      #print("AVG PX:", avg_px)
      #print("RES:", resize)
      go = 1
      if sun_status == 'night' and avg_px >= 240:
         print("TOO BRIGHT!", avg_px, sun_status)
         go = 0
      elif avg_px > 220:     
         go = 0

      if avg_px >= 240:
         print("TOO BRIGHT!", avg_px)
         go = 0
      if go == 1:
         if resize is not None:
               frame = cv2.resize(frame, (int(resize[0]),int(resize[1])))
         if fc % skip == 0:
            frame_pil = Image.fromarray(frame)
            if stacked_image is None:
               stacked_image = stack_stack(frame_pil, frame_pil)
            else:
               stacked_image = stack_stack(stacked_image, frame_pil)
      fc = fc + 1
   if stacked_image is None:
      print("NO STACK IMG")
      return(None)
   else:
      return(np.asarray(stacked_image))


def stack_frames_fast(frames, skip = 1, resize=None, sun_status="night", sum_vals=[]):
   if sum_vals is None:
      sum_vals= [1] * len(frames)
   stacked_image = None
   fc = 0
   for frame in frames:
      if (sun_status == 'night' and sum_vals[fc] > 0) or fc < 10:
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

def stack_stack(pic1, pic2):
   stacked_image=ImageChops.lighter(pic1,pic2)
   return(stacked_image)

#def mark_image_obj():

def mask_frame(frame, mp, masks, size=3):
   if masks is None: 
      return(frame)
   hdm_x = 2.7272
   
   hdm_y = 1.875
   """ Mask bright pixels detected in the median
       and also mask areas defined in the config """
   frame.setflags(write=1)
   ih,iw = frame.shape[0], frame.shape[1]
   px_val = np.mean(frame)
   px_val = 0

   for mask in masks:
      mx,my,mw,mh = mask.split(",")
      mx,my,mw,mh = int(mx), int(my), int(mw), int(mh)
      #if ih == 480 and iw == 704:
      #   fact = 480 / 576
      #   my = int(int(my) * fact) + 1
      #   mh = int(int(mh) * fact) + 1
      #print("MX MY:", my,my+mh,":",mx,mx+mw)
      frame[int(my):int(my)+int(mh),int(mx):int(mx)+int(mw)] = 0

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
   return(frame)


def thumbnail(image_file, w, h, thumb_file=None):
   if thumb_file == None:
      if "png" in image_file:
         thumb_file = image_file.replace(".png", "-tn.png")
      if "jpg" in image_file:
         thumb_file = image_file.replace(".jpg", "-tn.jpg")

   img = cv2.imread(image_file)
   thumb = cv2.resize(img, (w, h))
   cv2.imwrite(thumb_file, thumb) 
