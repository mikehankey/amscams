"""
 
   Pipeline Image Processing Functions

"""
from PIL import ImageFont, ImageDraw, Image, ImageChops
import numpy as np
import cv2

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

