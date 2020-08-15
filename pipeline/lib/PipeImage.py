"""
 
   Pipeline Image Processing Functions

"""
from PIL import ImageFont, ImageDraw, Image, ImageChops

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

def quick_video_stack(video_file, count = 10):
   frames = []
   temp_dir = "/mnt/ams2/tmp/st/"
   if cfe(temp_dir, 1) == 0:
      os.makedirs(temp_dir)
   cmd = "/usr/bin/ffmpeg -i " + video_file + " -vframes " + str(count) +  " " + temp_dir + "frames%03d.jpg > /dev/null 2>&1"
   os.system(cmd)
   files = glob.glob(temp_dir + "*.jpg")
   for file in files:
      frame = cv2.imread(file)
      frames.append(frame)
   stack_frame = stack_frames(frames)
   os.system("rm " + temp_dir + "*")
   return(stack_frame)
  


def stack_frames(frames, skip = 1, resize=None, sun_status="night"):


   stacked_image = None
   fc = 0
   for frame in frames:
      if True:
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
