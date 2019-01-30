import cv2
import glob
import numpy as np
from PIL import Image, ImageChops
from lib.FileIO import cfe
#from lib.DetectLib import 
from lib.MeteorTests import find_min_max_dist, max_xy


def thumb(image_file = "", image = ""):
   print("THUMB!", image_file)
   if image_file != "":
      thumb_file = image_file.replace(".png", "-tn.png")
      image = cv2.imread(image_file)
   try:
      print(image.shape)
   except:
      return()
   thumb_img = cv2.resize(image, (0,0),fx=.4, fy=.4)
   if image_file != "":
      cv2.imwrite(thumb_file,thumb_img)
   
   return(image)


def bigger_box(min_x,min_y,max_x,max_y,iw,ih,fac=5):
   if min_x - fac < 0:
      min_x = 0 
   if min_y - fac < 0:
      min_y = 0 
   if max_x + fac > iw-1:
      max_x = iw-1
   if max_y + fac > ih-1:
      max_y = ih-1
   return(min_x-fac,min_y-fac,max_x+fac,max_y+fac)


def draw_stack(objects,stack_img,stack_file):
   ih,iw=stack_img.shape
   for obj in objects:
      hist = obj['history'] 
      (max_x,max_y,min_x,min_y) = find_min_max_dist(hist)
      (min_x,min_y,max_x,max_y) = bigger_box(min_x,min_y,max_x,max_y,iw,ih,25) 
      cv2.rectangle(stack_img, (min_x, min_y), (max_x , max_y), (255, 0, 0,.02), 1)
      if obj['meteor'] == 1:
         cv2.putText(stack_img, str(obj['oid']) + " Meteor",  (min_x,min_y-3), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      else:
         cv2.putText(stack_img, str(obj['oid']) ,  (min_x-5,min_y-12), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   stack_file=stack_file.replace("-stacked.png", "-stacked-obj.png")
   print("WROTE:", stack_file)
   cv2.imwrite(stack_file,stack_img)

def stack_stack(pic1, pic2):
   stacked_image=ImageChops.lighter(pic1,pic2)
   return(stacked_image)

def stack_glob(glob_dir, out_file):
   stacked_image = None
   img_files = glob.glob(glob_dir)
   for file in img_files:
      print(file)
      img = cv2.imread(file, 0)
      img_pil = Image.fromarray(img)
      if stacked_image is None:
         stacked_image = stack_stack(img_pil, img_pil)
      else:
         stacked_image = stack_stack(stacked_image, img_pil)
   if stacked_image is not None:
      stacked_image_np = np.asarray(stacked_image)
      print(out_file)
      cv2.imwrite(out_file, stacked_image_np)



def stack_frames(frames,video_file):
   stacked_image = None
   stacked_file= video_file.replace(".mp4", "-stacked.png")
   if cfe(stacked_file) == 1:
      print("SKIP - Stack already done.") 
      return()
   for frame in frames:
      frame_pil = Image.fromarray(frame)
      if stacked_image is None:
         stacked_image = stack_stack(frame_pil, frame_pil)
      else:
         stacked_image = stack_stack(stacked_image, frame_pil)
   if stacked_image is not None:
      stacked_image.save(stacked_file)
      print ("Saved: ", stacked_file)
   else:
      print("bad file:", video_file)
   return(stacked_file,np.asarray(stacked_image))


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


def preload_image_acc(frames):
   alpha = .9
   image_acc = np.empty(np.shape(frames[0]))
   for frame in frames:
      frame = cv2.GaussianBlur(frame, (7, 7), 0)
      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), frame,)
      hello = cv2.accumulateWeighted(frame, image_acc, alpha)
   return(image_acc)


def mask_frame(frame, mp, masks, size=3):
   """ Mask bright pixels detected in the median 
       and also mask areas defined in the config """

   ih,iw = frame.shape
   px_val = np.mean(frame)
   px_val = 0


   for mask in masks:
      mx,my,mw,mh = mask.split(",")
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


def median_frames(frames):
   if len(frames) > 200:
      med_stack_all = cv2.convertScaleAbs(np.median(np.array(frames[0:199]), axis=0))
   else:
      med_stack_all = cv2.convertScaleAbs(np.median(np.array(frames), axis=0))
   return(med_stack_all)

