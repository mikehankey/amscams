import os
import json
import cv2
import glob
import numpy as np
from PIL import Image, ImageChops
from PIL import ImageDraw
from PIL import ImageFont
import ephem

#from lib.flexLib import day_or_night 

#from lib.FileIO import load_json_file

from lib.UtilLib import bound_cnt
from lib.FileIO import cfe, convert_filename_to_date_cam
#from lib.DetectLib import 
from lib.MeteorTests import find_min_max_dist, max_xy




def day_or_night(capture_date, json_conf):

   device_lat = json_conf['site']['device_lat']
   device_lng = json_conf['site']['device_lng']

   obs = ephem.Observer()

   obs.pressure = 0
   obs.horizon = '-0:34'
   obs.lat = device_lat
   obs.lon = device_lng
   obs.date = capture_date

   sun = ephem.Sun()
   sun.compute(obs)

   (sun_alt, x,y) = str(sun.alt).split(":")

   saz = str(sun.az)
   (sun_az, x,y) = saz.split(":")
   if int(sun_alt) < -1:
      sun_status = "night"
   else:
      sun_status = "day"
   return(sun_status)


def load_json_file(json_file):
   try:
      with open(json_file, 'r' ) as infile:
         json_data = json.load(infile)
   except:
      json_data = False
   return json_data


def upscale_to_hd(image, points):
   sd_stack_img = image
   hd_image = cv2.resize(image, (1920,1080))
   hdm_x = 2.7272
   hdm_y = 1.875
   shp = image.shape
   ih,iw = shp[0],shp[1]
   star_points = []
   plate_img = np.zeros((ih,iw),dtype=np.uint8)
   plate_img_4f = np.zeros((ih,iw),dtype=np.uint8)

   for x,y in points:
      x,y = int(x),int(y)
      y1 = y - 15
      y2 = y + 15
      x1 = x - 15
      x2 = x + 15
      cnt_img = image[y1:y2,x1:x2]
      ch,cw = cnt_img.shape
      max_pnt,max_val,min_val = cnt_max_px(cnt_img)
      mx,my = max_pnt
      mx = mx - 15
      my = my - 15

      cy1 = y + my - 15
      cy2 = y + my +15
      cx1 = x + mx -15
      cx2 = x + mx +15
      cx1,cy1,cx2,cy2= bound_cnt(x+mx,y+my,iw,ih,15)

      if ch > 0 and cw > 0:
         tmp_cnt_img = sd_stack_img[cy1:cy2,cx1:cx2]
         cnt_img =tmp_cnt_img.copy()
         bgavg = np.mean(cnt_img)
         black_cnt_img, cnt_img = clean_star_bg(cnt_img, bgavg + 3 )

         star_points.append([x+mx,y+my])
         if abs(cy1- (ih/2)) <= (ih/2)*.8 and abs(cx1- (iw/2)) <= (iw/2)*.8:
            plate_img_4f[cy1:cy2,cx1:cx2] = black_cnt_img
            plate_img[cy1:cy2,cx1:cx2] = black_cnt_img
         else:
            if cy2 - cy1 == ch and cx2 - cx1 == cw:
               plate_img_4f[cy1:cy2,cx1:cx2] = black_cnt_img
               hd_image[cy1:cy2,cx1:cx2] = cnt_img

   plate_img = cv2.resize(plate_img, (1920,1080))
   plate_img_4f = cv2.resize(plate_img_4f, (1920,1080))

   

   return(hd_image,plate_img,plate_img_4f,star_points)

def make_10_sec_thumbs(sd_video_file, frames, json_conf):

   sc = 0
   fc = 0
   stacked_image = None
   for frame in frames:
      img_pil = Image.fromarray(frame)
      if stacked_image is None:
         stacked_image = stack_stack(img_pil, img_pil)
      else:
         stacked_image = stack_stack(stacked_image, img_pil)
      if fc % 250 == 0:
         
         stacked_image_np = np.asarray(stacked_image)
         out_file = "/mnt/ams2/trash/stack" + str(sc) + ".png"
         cv2.imwrite(out_file, stacked_image_np)
         sc = sc + 1
         stacked_image = None
      fc = fc + 1


def thumb(image_file = "", image = "", perc_size = None):
   print("THUMB!", image_file)
   if image_file != "":
      thumb_file = image_file.replace(".jpg", "-tn.jpg")
      image = cv2.imread(image_file)
      print("THUMB FILE OPENED")

   try:
      h,w = image.shape
      print("IMAGE SHAPE:", image.shape)
   except:
      print("IMAGE THUMB FAILED FOR ", image_file)
      return()

   if perc_size is None:
      if w < 1000:
         #thumb_img = cv2.resize(image, (0,0),fx=.4, fy=.4)
         thumb_img = cv2.resize(image, (320,180))
      else:
         #thumb_img = cv2.resize(image, (0,0),fx=.15, fy=.15)
         thumb_img = cv2.resize(image, (320,180))
   else:
      #thumb_img = cv2.resize(image, (0,0),fx=perc_size, fy=perc_size)
      thumb_img = cv2.resize(image, (320,180))

   if image_file != "":
      print("SAVING:", thumb_file)
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

def obj_to_hist(obj):
   # hist = fn,x,y,w,h,i
   hist = []
   for i in range(0, len(obj['oxs'])):
      x = obj['oxs'][i]
      y = obj['oys'][i]
      fn = obj['ofns'][i]
      w = obj['ows'][i]
      h = obj['ohs'][i]
      i = obj['oint'][i]
      hist.append([fn,x,y,w,h,x,y,i,i])
   return(hist)

def draw_stack(objects,stack_img,stack_file):
   if stack_img is None:
      return() 
   ih,iw=stack_img.shape[:2]
   for obj in objects:
      print("OBJ:", obj)
      if "history" in obj:
         hist = obj['history'] 
      else:
         hist = obj_to_hist(obj)
         print("HIST:", hist)
         #exit()        
      (max_x,max_y,min_x,min_y) = find_min_max_dist(hist)
      (min_x,min_y,max_x,max_y) = bigger_box(min_x,min_y,max_x,max_y,iw,ih,25) 
      cv2.rectangle(stack_img, (min_x, min_y), (max_x , max_y), (255, 0, 0,.02), 1)
      if "meteor" not in obj :
         print(obj)
         obj['meteor'] = 1

      if obj['meteor'] == 1:
         if 'oid' in obj:
            oid = obj['oid']
         else:
            oid = obj['obj_id']
         cv2.putText(stack_img, str(oid) + " Meteor",  (min_x,min_y-3), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      else:
         cv2.putText(stack_img, str(obj['oid']) ,  (min_x-5,min_y-12), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   stack_file=stack_file.replace("-stacked.jpg", "-stacked-obj.jpg")
   print("WROTE:", stack_file)
   cv2.imwrite(stack_file,stack_img)

def stack_stack(pic1, pic2):
   stacked_image=ImageChops.lighter(pic1,pic2)
   return(stacked_image)

def stack_glob(glob_dir, out_file):
   stacked_image = None
   json_conf = load_json_file("../conf/as6.json")
   print("GLOBDIR: ", glob_dir)
   img_files = glob.glob(glob_dir)
   for file in img_files:
      print(file)
      img = cv2.imread(file, 0)
      (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
      sun_status = day_or_night(f_date_str, json_conf)
      if sun_status == 'day':
         continue

      try:
         h,w = img.shape
      except:
         os.system("rm " + file)
         continue 
      avg_px = np.mean(img)
      print("AG:", avg_px)
      if avg_px > 80 or avg_px == 0:
      #   os.system("rm " + file)
         continue
      img_pil = Image.fromarray(img)
      if stacked_image is None:
         stacked_image = stack_stack(img_pil, img_pil)
      else:
         stacked_image = stack_stack(stacked_image, img_pil)
   if stacked_image is not None:
      stacked_image_np = np.asarray(stacked_image)
      print("SAVED STACK:",out_file)
      cv2.imwrite(out_file, stacked_image_np)



def stack_frames(frames,video_file,nowrite=0, resize=None):
   if resize is not None:
      resize_w = resize[0]
      resize_h = resize[1]
   stacked_image = None
   stacked_file= video_file.replace(".mp4", "-stacked.jpg")
   print("STACKED FILE IS:", stacked_file)
   if cfe(stacked_file) == 1 and nowrite == 0:
      #print("SKIP - Stack already done.") 
      stacked_image = cv2.imread(stacked_file)
      return(stacked_file,stacked_image)
   for frame in frames:
      frame_pil = Image.fromarray(frame)
      if stacked_image is None:
         stacked_image = stack_stack(frame_pil, frame_pil)
      else:
         stacked_image = stack_stack(stacked_image, frame_pil)
   if nowrite == 0:
      if stacked_image is not None:
         #stacked_image.save(stacked_file)
         image = np.array(stacked_image)
         #bgr_image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
         #cv2.imshow('pepe', bgr_image)
         #cv2.waitKey(0)
         #cv2.imshow('pepe', image)
         #cv2.waitKey(0)
         cv2.imwrite(stacked_file, image)
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
   alpha = .5
   image_acc = np.empty(np.shape(frames[0]))
   for frame in frames:
      frame = cv2.GaussianBlur(frame, (7, 7), 0)
      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), frame,)
      hello = cv2.accumulateWeighted(frame, image_acc, alpha)
      #show_frame = cv2.convertScaleAbs(image_acc)

      #cv2.imshow('pepe', show_frame)
      #cv2.waitKey(0)
   return(image_acc)


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


def median_frames(frames):
   if len(frames) > 200:
      med_stack_all = cv2.convertScaleAbs(np.median(np.array(frames[0:199]), axis=0))
   else:
      med_stack_all = cv2.convertScaleAbs(np.median(np.array(frames), axis=0))
   return(med_stack_all)


def draw_stars_on_img(image_np, star_list, color="white", track_type="box")  :
   image = Image.fromarray(image_np)
   draw = ImageDraw.Draw(image)
   font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 14, encoding="unic" )
   for data in star_list:
      print("LEN:", len(data))
      if len(data) == 12:
         star_name, common_name, ra, dec, mag, cx, cy, mx, my, az, el,ofn = data
      if len(data) == 11:
         star_name, common_name, ra, dec, mag, cx, cy, mx, my, az, el = data
      if len(data) == 6:
         star_name, ra, dec, mag, cx, cy = data
      if len(data) == 8:
         star_name, ra, dec, mag, cx, cy, az, el = data
      
      #az_txt = str(star_name) + " " + str(int(az)) + "/" + str(int(el))
      az_txt = star_name
      if track_type == "box":
         #draw.rectangle((cx-20, cy-20, cx + 20, cy + 20), outline=color)
         draw.text((cx+15, cy), str(az_txt), font = font, fill=color)
      if track_type == "trail":
         draw.ellipse((cx-1, cy-1, cx+1, cy+1),  outline ="white")
      if track_type == "anchor":
         draw.ellipse((cx-3, cy-3, cx+3, cy+3),  outline ="white")

   image_np = np.asarray(image)
   #cv2.imshow('pepe', image_np)
   #cv2.waitKey(10)
   return(image_np)


def clean_star_bg(this_cnt_img, bg_avg):
   cnt_img = this_cnt_img.copy()
   
   max_px = np.max(cnt_img)
   min_px = np.min(cnt_img)
   avg_px = np.mean(cnt_img)
   halfway = int((max_px - min_px) / 3)
   cnt_img.setflags(write=1)
   black_cnt_img = cnt_img.copy()
   for x in range(0,cnt_img.shape[1]):
      for y in range(0,cnt_img.shape[0]):
         px_val = cnt_img[y,x]
         if px_val < bg_avg + halfway:
            #cnt_img[y,x] = random.randint(int(bg_avg - 3),int(avg_px))
            pxval = cnt_img[y,x]
            pxval = int(pxval) / 2
            black_cnt_img[y,x] = 0
         else:
            pxval = cnt_img[y,x]
            pxval = int(pxval) * 2
            if pxval > 255:
               pxval = 255
            cnt_img[y,x] = pxval
            black_cnt_img[y,x] = pxval
   return(black_cnt_img, cnt_img)

def cnt_max_px(cnt_img):
   cnt_img = cv2.GaussianBlur(cnt_img, (7, 7), 0)
   min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)

   return(max_loc, min_val, max_val)

