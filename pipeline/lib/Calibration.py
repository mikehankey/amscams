import cv2
import time
import scipy.optimize
from lib.cyFuncs import cyjd2LST, cyraDecToXY
from lib.conversions import datetime2JD, JD2HourAngle
import ephem
import numpy as np
from lib.PipeUtil import angularSeparation, load_json_file, save_json_file, convert_filename_to_date_cam
import lib.brightstardata as bsd
import math
import os
import requests
from PIL import ImageFont, ImageDraw, Image, ImageChops
SHOW = 1
tries = 1

def fetch_calib_data(station_id, camera_id):
    
    dir_path = os.path.dirname(os.path.realpath(__file__))
    local_cal_dir = dir_path + "/../Data/CALIB/" + station_id + "/"
    print("LOCAL CAL DIR:", local_cal_dir)
    cal_range_file = local_cal_dir + station_id + "_cal_range.json"
    conf_file = local_cal_dir + station_id + "_conf.json"

    #AMS110_011005_LENS_MODEL.json
    lens_file = local_cal_dir + station_id + "_" + camera_id + "_LENS_MODEL.json"
    if os.path.exists(local_cal_dir) is False:
        os.makedirs(local_cal_dir)
    if os.path.exists(cal_range_file) is False:
        url = "https://archive.allsky.tv/" + station_id + "/CAL/" + station_id + "_cal_range.json"
        resp = requests.get(url=url)
        cal_range = resp.json()
        save_json_file(cal_range_file, cal_range)
    else:
        cal_range = load_json_file(cal_range_file)

    if os.path.exists(conf_file) is False:
        url = "https://archive.allsky.tv/" + station_id + "/CAL/" +"as6.json"
        resp = requests.get(url=url)
        conf = resp.json()
        save_json_file(conf_file, conf)
    else:
        conf = load_json_file(conf_file)
    if os.path.exists(lens_file) is False:
        url = "https://archive.allsky.tv/" + station_id + "/CAL/" + station_id + "_" + camera_id + "_LENS_MODEL.json"
        resp = requests.get(url=url)
        lens_data = resp.json()
        save_json_file(lens_file, lens_data)
    else:
        lens_data = load_json_file(lens_file)

    return(cal_range, conf, lens_data)

def find_stars_with_grid(img):

    bad_points = []
    raw_img = img.copy()
    gsize = 50,50
    ih,iw = img.shape[:2]
    rows = int(int(ih) / gsize[1])
    cols = int(int(iw) / gsize[0])
    stars = []
    bad_stars = []
    bright_points = []
    grids = []
    pos_stars = []
    for col in range(0,cols+1):
       for row in range(0,rows+1):
          x1 = col * gsize[0]
          y1 = row * gsize[1]
          x2 = x1 + gsize[0]
          y2 = y1 + gsize[1]
          grids.append((x1,y1,x2,y2))
          if x2 >= iw:
             x2 = iw
          if y2 >= ih:
             y2 = ih
          gimg = img[y1:y2,x1:x2]
          show_gimg = cv2.resize(gimg, (500,500))
          show_img = img.copy()
          show_gimg = cv2.cvtColor(show_gimg, cv2.COLOR_BGR2GRAY)
          avg_px = np.mean(show_gimg)
          min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(show_gimg)
          px_diff = max_val - avg_px
          desc = " AVG PX" + str(avg_px) + " MAX VAL" + str(max_val) + "PX DIFF: " + str(px_diff) 
          if px_diff > 10:
             _, thresh_img = cv2.threshold(show_gimg, max_val * .8, 255, cv2.THRESH_BINARY)
             cnts = get_contours_in_crop(thresh_img)

             if len(cnts) == 1:
                 for cnt in cnts:
                     x,y,w,h,cx,cy,adj_x,adj_y = cnt
                     cx = x1 + (cx / 10)
                     cy = y1 + (cy / 10)
                     pos_stars.append((cx,cy,0))
             cv2.putText(show_img, str(desc),  (int(10),int(40)), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
         

          cv2.rectangle(show_img, (x1, y1), (x2, y2 ), (255, 255, 255), 1)
          if len(pos_stars) > 0:
             for star in pos_stars:
                cv2.circle(show_img,(int(star[0]),int(star[1])), 20, (128,128,128), 1)
          show_img2 = cv2.resize(show_img,(1280,720))

          cv2.imshow('main', show_img2)
          if px_diff > 30 and len(cnts) == 1:
             cv2.imshow('preview', thresh_img)
             cv2.waitKey(3)
          else:
             cv2.imshow('preview', show_gimg)
             cv2.waitKey(3)

    stars = []
    clean_stars =[]
    for data in pos_stars:
        x,y,i = data
        sx1 = int(x - 5)
        sy1 = int(y - 5)
        sx2 = int(x + 5)
        sy2 = int(y + 5)
        if sx1 < 0:
           sx1 = 0
           sx2 = 10
        if sy1 < 0:
           sy1 = 0
           sy2 = 10
        if sx2 > iw:
           sx1 = iw - 10
           sx2 = iw
        if sy2 > ih:
           sy1 = ih - 10
           sy2 = ih

        star_cnt = img[sy1:sy2,sx1:sx2]
        data = inspect_star(star_cnt, data, None)
        clean_stars.append(data)
    for star in clean_stars:
        show_img = img.copy()
    return(pos_stars)

def get_contours_in_crop(frame ):
   ih, iw = frame.shape[:2]
   canny = cv2.Canny(frame,30,200)
   #cv2.imshow("CANNY", canny)

   cont = []
   if len(frame.shape) > 2:
      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
   cnt_res = cv2.findContours(canny.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      #if SHOW == 1:
      #   show_img = frame.copy()
      #   cv2.rectangle(show_img, (x, y), (x+w, y+h), (255, 0, 0), 1)
      #   cv2.imshow("GET CNT", show_img)

      if w >= 1 or h >= 1:
         cx = x + (w / 2)
         cy = y + (h / 2)
         adjx = cx - (iw/2)
         adjy = cy - (ih/2)
         cont.append((x,y,w,h,cx,cy,adjx,adjy))
   return(cont)

def inspect_star(star_cnt, user_star_data=None, cat_star_data=None, show=0):
   orig_star_cnt = star_cnt.copy()
   if cat_star_data is not None:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = cat_star_data
   if user_star_data is not None:
      six, siy, i = user_star_data
   if len(star_cnt.shape) == 3:
      gray_star = cv2.cvtColor(star_cnt, cv2.COLOR_BGR2GRAY)
   else:
      gray_star = star_cnt
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_star)
   thresh_val = max_val *.9
   _, thresh_img = cv2.threshold(gray_star.copy(), thresh_val, 255, cv2.THRESH_BINARY)

   if len(star_cnt.shape) == 2:
      star_cnt = cv2.cvtColor(star_cnt, cv2.COLOR_GRAY2BGR)

   if SHOW == 1:
      print("CNT", star_cnt.shape)
      star_cnt[int(my),int(mx)] = [0,0,255]
      star_cnt[4,4] = [0,128,0]
      #cv2.imshow('star', star_cnt)
      #cv2.imshow('thresh', thresh_img)
      #cv2.waitKey(30)
   cnts = get_contours_in_crop(thresh_img)
   if len(cnts) == 1:
      x,y,w,h,cx,cy,adjx,adjy = cnts[0]
      six += adjx
      siy += adjy
      star_int = int(np.sum(star_cnt[y:y+h,x:x+w]))
      if cat_star_data is not None and w < 6 and h < 6:
         print("NEW SIX,SIY:", six, siy)
         return(dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int)
      if user_star_data is not None:
         return((six,siy,star_int))
   else:
      return None


def make_default_cal_params(station_id, cam_id):
   cp = {}
   cp['imagew'] = 1920
   cp['imageh'] = 1080 
   cp['ra_center'] = 0 
   cp['dec_center'] = 0 
   cp['center_az'] = 0 
   cp['center_el'] = 25
   cp['position_angle'] = 100
   cp['pixscale'] = 158
   return(cp)

def update_center_radec(archive_file,cal_params,json_conf,time_diff=0):
   rah,dech = AzEltoRADec(cal_params['center_az'],cal_params['center_el'],archive_file,cal_params,json_conf,time_diff)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))
   cal_params['ra_center'] = ra_center
   cal_params['dec_center'] = dec_center
   #for key in cal_params:
   #   print("UPDATE RAC", key, cal_params[key])
   return(cal_params)


def get_catalog_stars(cal_params, force=0):
   if "short_bright_stars" not in cal_params or force == 1:
      mybsd = bsd.brightstardata()
      bright_stars = mybsd.bright_stars
   else:
      bright_stars = cal_params['short_bright_stars']
      #mybsd = bsd.brightstardata()
      #bright_stars = mybsd.bright_stars

   catalog_stars = []
   possible_stars = 0
   img_w = 1920
   img_h = 1080
   cal_params['imagew'] = 1920
   cal_params['imageh'] = 1080
   RA_center = float(cal_params['ra_center'])
   dec_center = float(cal_params['dec_center'])
   F_scale = 3600/float(cal_params['pixscale'])
   if "x_poly" in cal_params:
      x_poly = cal_params['x_poly']
      y_poly = cal_params['y_poly']
   else:
      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      x_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
      y_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
   fov_w = img_w / F_scale
   fov_h = img_h / F_scale
   fov_radius = np.sqrt((fov_w/2)**2 + (fov_h/2)**2)

   pos_angle_ref = cal_params['position_angle']
   x_res = int(cal_params['imagew'])
   y_res = int(cal_params['imageh'])


   if img_w < 1920:
      center_x = int(x_res / 2)
      center_y = int(x_res / 2)

   bright_stars_sorted = sorted(bright_stars, key=lambda x: x[4], reverse=False)

   sbs = []
   for data in bright_stars_sorted:
      if len(data) == 5:
         bname, cname, ra, dec, mag = data
         name = bname
      elif len(data) == 6:
         name, mag, ra, dec, cat_x, cat_y = data
      elif len(data) == 17:
         name,mag,ra,dec,img_ra,img_dec,match_dist,cat_x,cat_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist,star_int  = data
      else:
         exit()

      if isinstance(name, str) is True:
         name = name
      else:
         name = name.decode("utf-8")

      ang_sep = angularSeparation(ra,dec,RA_center,dec_center)
      if ang_sep < fov_radius and float(mag) <= 6:
         sbs.append((name, name, ra, dec, mag))
         new_cat_x, new_cat_y = distort_xy(0,0,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale)

         possible_stars = possible_stars + 1
         catalog_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y))

   if len(catalog_stars) == 0:
      print("NO CATALOG STARS!?")

   return(catalog_stars)

def distort_xy(sx,sy,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale=1):

   ra_star = np.float64(ra)
   dec_star = np.float64(dec)
   RA_center = np.float64(RA_center)
   dec_center = np.float64(dec_center)
   pos_angle_ref = np.float64(pos_angle_ref)
   F_scale = np.float64(F_scale)
   debug = 0
   if debug == 1:
      print("DISTORT XY")
      print("STR RA/DEC:", ra_star, dec_star)
      print("CENTER RA/DEC:", RA_center, dec_center)
      print("XP:", x_poly, type(x_poly))
      print("YP:", y_poly, type(y_poly))
      print("XRES:", x_res)
      print("YRES:", y_res)
      print("POS:", pos_angle_ref)
      print("FSCALE:", F_scale)

   #F_scale = F_scale/10
   w_pix = 50*F_scale/3600
   #F_scale = 158 * 2
   #F_scale = 155
   #F_scale = 3600/16
   #F_scale = 3600/F_scale
   #F_scale = 1

   # Gnomonization of star coordinates to image coordinates
   ra1 = math.radians(float(RA_center))
   dec1 = math.radians(float(dec_center))
   ra2 = math.radians(float(ra_star))
   dec2 = math.radians(float(dec_star))
   ad = math.acos(math.sin(dec1)*math.sin(dec2) + math.cos(dec1)*math.cos(dec2)*math.cos(ra2 - ra1))
   radius = math.degrees(ad)

   try:
      sinA = math.cos(dec2)*math.sin(ra2 - ra1)/math.sin(ad)
      cosA = (math.sin(dec2) - math.sin(dec1)*math.cos(ad))/(math.cos(dec1)*math.sin(ad))
   except:
      sinA = 0
      cosA = 0
   theta = -math.degrees(math.atan2(sinA, cosA))
   theta = theta + pos_angle_ref - 90.0
   #theta = theta + pos_angle_ref - 90 + (1000*x_poly[12]) + (1000*y_poly[12])
   #theta = theta + pos_angle_ref - 90



   dist = np.degrees(math.acos(math.sin(dec1)*math.sin(dec2) + math.cos(dec1)*math.cos(dec2)*math.cos(ra1 - ra2)))

   # Calculate the image coordinates (scale the F_scale from CIF resolution)
   X1 = radius*math.cos(math.radians(theta))*F_scale
   Y1 = radius*math.sin(math.radians(theta))*F_scale
   # Calculate distortion in X direction
   dX = (x_poly[0]
      + x_poly[1]*X1
      + x_poly[2]*Y1
      + x_poly[3]*X1**2
      + x_poly[4]*X1*Y1
      + x_poly[5]*Y1**2
      + x_poly[6]*X1**3
      + x_poly[7]*X1**2*Y1
      + x_poly[8]*X1*Y1**2
      + x_poly[9]*Y1**3
      + x_poly[10]*X1*math.sqrt(X1**2 + Y1**2)
      + x_poly[11]*Y1*math.sqrt(X1**2 + Y1**2))

   # NEW TERMS DONT WORK WELL
   #dX += x_poly[12]*X1*math.sqrt(X1**2 + Y1**2)**3
   #dX += x_poly[13]*X1*math.sqrt(X1**2 + Y1**2)**5
   # Add the distortion correction and calculate X image coordinates
   #x_array[i] = (X1 - dX)*x_res/384.0 + x_res/2.0
   new_x = X1 - dX + x_res/2.0

   # Calculate distortion in Y direction
   dY = (y_poly[0]
      + y_poly[1]*X1
      + y_poly[2]*Y1
      + y_poly[3]*X1**2
      + y_poly[4]*X1*Y1
      + y_poly[5]*Y1**2
      + y_poly[6]*X1**3
      + y_poly[7]*X1**2*Y1
      + y_poly[8]*X1*Y1**2
      + y_poly[9]*Y1**3
      + y_poly[10]*Y1*math.sqrt(X1**2 + Y1**2)
      + y_poly[11]*X1*math.sqrt(X1**2 + Y1**2))

   # NEW TERMS DONT WORK WELL
   #dY += y_poly[12]*Y1*math.sqrt(X1**2 + Y1**2)**3
   #dY += y_poly[13]*Y1*math.sqrt(X1**2 + Y1**2)**5

   # Add the distortion correction and calculate Y image coordinates
   #y_array[i] = (Y1 - dY)*y_res/288.0 + y_res/2.0
   new_y = Y1 - dY + y_res/2.0
   return(new_x,new_y)


def AzEltoRADec(az,el,cal_file,cal_params,json_conf,time_diff=0):
   azr = np.radians(az)
   elr = np.radians(el)
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cal_file)

   if "trim" in cal_file:
      # add extra sec from trim num
      try:
         trim_num = get_trim_num(cal_file)
         extra_sec = int(trim_num) / 25
         trim_time = hd_datetime + dt.timedelta(0,extra_sec)
         hd_datetime = trim_time
      except:
         trim_num = 0
         extra_sec = 0
         trim_time = hd_datetime

   if time_diff != 0:
      hd_datetime = hd_datetime + dt.timedelta(0,time_diff)

   #hd_datetime = hd_y + "/" + hd_m + "/" + hd_d + " " + hd_h + ":" + hd_M + ":" + hd_s
   if "device_lat" in cal_params:
      device_lat = cal_params['device_lat']
      device_lng = cal_params['device_lng']
      device_alt = cal_params['device_alt']
   else:
      device_lat = json_conf['site']['device_lat']
      device_lng = json_conf['site']['device_lng']
      device_alt = json_conf['site']['device_alt']

   obs = ephem.Observer()


   obs.lat = str(device_lat)
   obs.lon = str(device_lng)
   obs.elevation = float(device_alt)
   obs.date = hd_datetime


   ra,dec = obs.radec_of(azr,elr)


   return(ra,dec)


def get_image_stars(file=None,img=None,json_conf=None,show=0):
   (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(file)

   if True:
      mask_file = MASK_DIR + cam + "_mask.png"

      if cfe(mask_file) == 1:
         mask_img = cv2.imread(mask_file)
         mask_img = cv2.resize(mask_img, (1920,1080))

      else:
         mask_img = None


   if img is None:
      img = cv2.imread(file)
   if len(img.shape) == 3:
      img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
   if len(mask_img.shape) == 3:
      mask_img = cv2.cvtColor(mask_img, cv2.COLOR_BGR2GRAY)
   if mask_img is not None:
      mask_img = cv2.resize(mask_img, (img.shape[1],img.shape[0]))
      img = cv2.subtract(img, mask_img)

   stars = []
   huge_stars = []
   if img is None:
      img = cv2.imread(file, 0)
   if img.shape[0] != '1080':
      img = cv2.resize(img, (1920,1080))

   if len(img.shape) > 2:
      img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
   show_pic = img.copy()



   raw_img = img.copy()
   cam = cam.replace(".png", "")
   #masks = get_masks(cam, json_conf,1)
   #img = mask_frame(img, [], masks, 5)

   mask_file = MASK_DIR + cam + "_mask.png"
   if cfe(mask_file) == 1:
      mask_img = cv2.imread(mask_file, 0)
      mask_img = cv2.resize(mask_img, (1920,1080))
   else:
      mask_img = None
   if mask_img is not None:
      mask_img = cv2.resize(mask_img, (img.shape[1],img.shape[0]))
      img = cv2.subtract(img, mask_img)

   cv2.imwrite("/mnt/ams2/masked.jpg", img)
   best_stars = find_stars_with_grid(img)
   for star in best_stars:
      #print("BEST STAR:", star)
      if star is None:
         continue
      x,y,z = star
      cv2.circle(img, (int(x),int(y)), 5, (128,128,128), 1)
   cv2.imwrite("/mnt/ams2/temp.jpg", img)
   return(best_stars)

def pair_stars(cal_params, cal_params_file, json_conf, cal_img=None, show = 0):
   dist_type = "radial"
   if cal_img is None:
      cal_img_file = cal_params_file.replace("-calparams.json", ".png")
      cal_img = cv2.imread(cal_img_file)

   (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(cal_params_file)
   jd = datetime2JD(f_datetime, 0.0)
   hour_angle = JD2HourAngle(jd)

   if cal_img is None:
      img_file = cal_params_file.replace("-calparams.json", ".jpg")
      cal_img = cv2.imread(img_file)
   #print("CAL IMG IS:", cal_img)
   if cal_img is not None:
      if len(cal_img.shape) > 2:
         cal_img = cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)
   if "x_poly" not in cal_params:
      cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)

   if cal_img is not None:
      temp_img = cal_img.copy()

      ih, iw= cal_img.shape[:2]
   else:
      iw = 1920
      ih = 1080
   ra_center = cal_params['ra_center']
   dec_center = cal_params['dec_center']
   center_az = cal_params['center_az']
   center_el = cal_params['center_el']
   star_matches = []
   my_close_stars = []
   total_match_dist = 0
   total_cat_dist = 0
   total_matches = 0
   cat_stars = get_catalog_stars(cal_params)


   #new_user_stars = []
   #new_stars = []
   #cal_params['user_stars'] = new_user_stars

   used = {}
   no_match = []

   degrees_per_pix = float(cal_params['pixscale'])*0.000277778
   px_per_degree = 1 / degrees_per_pix
   cc = 0

   for data in cal_params['user_stars']:
      if data is None:
         continue
      if len(data) == 3:
         ix,iy,bp = data
      else:
         ix,iy = data
         bp = 0

      # INTENSITY OF IMAGE STAR
      sx1 = ix - 5
      sx2 = ix + 5
      sy1 = iy - 5
      sy2 = iy + 5
      if sx1 < 0:
         sx1 = 0
      if sy1 < 0:
         sy1 = 0
      close_stars = find_close_stars((ix,iy), cat_stars)
      found = 0
      #if len(close_stars) == 0:
      for name,mag,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist in close_stars:
         #dcname = str(name.decode("utf-8"))
         #dbname = dcname.encode("utf-8")
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(ix,iy,cal_params_file,cal_params,json_conf)

         ra_data = np.zeros(shape=(1,), dtype=np.float64)
         dec_data = np.zeros(shape=(1,), dtype=np.float64)
         ra_data[0] = ra
         dec_data[0] = dec

         #ra_data = [cal_params['ra_center']]
         #dec_data = [cal_params['dec_center']]
         x_data, y_data = cyraDecToXY(ra_data, \
               dec_data,
               jd, json_conf['site']['device_lat'], json_conf['site']['device_lng'], iw, \
               ih, hour_angle, float(cal_params['ra_center']),  float(cal_params['dec_center']), \
               float(cal_params['position_angle']), \
               px_per_degree, \
               cal_params['x_poly'], cal_params['y_poly'], \
               dist_type, True, False, False)

         new_x = x_data[0]
         new_y = y_data[0]



         match_dist = abs(angularSeparation(ra,dec,img_ra,img_dec))
         # are all 3 sets of point on the same line
         points = [[ix,iy],[new_x,new_y], [1920/2, 1080/2]]
         xs = [ix,new_x,new_cat_x,1920/2]
         ys = [iy,new_y,new_cat_y,1080/2]
         #line_test = arecolinear(points)

         lxs = [ix,1920/2]
         lys = [iy,1080/2]
         #dist_to_line = poly_fit_check(lxs,lys, new_cat_x,new_cat_y)
         #dist_to_line2 = poly_fit_check(lxs,lys, new_x,new_y)
         #cv2.circle(temp_img,(six,siy), 7, (128,128,128), 1)
         #cv2.circle(temp_img,(int(new_cat_x),int(new_cat_y)), 7, (255,128,128), 1)
         #cv2.circle(temp_img,(int(new_x),int(new_y)), 7, (128,128,255), 1)
         used_key = str(ra) + "-" + str(dec)
         if match_dist >= 20 or used_key in used:
            bad = 1
            if used_key in used:
               dd = "used already"
            else:
               dd = "too far"
            #plt.plot(xs, ys)
            #plt.show()
         else:
            my_close_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp))
            total_match_dist = total_match_dist + match_dist
            total_cat_dist = total_cat_dist + cat_dist
            total_matches = total_matches + 1
            used[used_key] = 1
            found = 1
      if found == 0:
         if len(close_stars) >= 1:

            no_match.append(close_stars[0])
      cc += 1

   #my_close_stars,bad_stars = qc_stars(my_close_stars)
   bad_stars = []
   cal_params['bad_stars'] = bad_stars
   cal_params['no_match_stars'] = no_match
   if SHOW == 1:
      for star in my_close_stars:
         dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
         cv2.rectangle(temp_img, (int(new_cat_x)-2, int(new_cat_y)-2), (int(new_cat_x) + 2, int(new_cat_y) + 2), (128, 128, 128), 1)
         cv2.rectangle(temp_img, (int(six-2), int(siy-2)), (int(six+ 2), int(siy+ 2)), (255, 255, 255), 1)
         cv2.circle(temp_img,(int(six),int(siy)), 7, (128,128,128), 1)
         cv2.putText(temp_img, str(dcname),  (int(new_cat_x),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
         debug_txt = "RA/DEC: " + str(cal_params['ra_center'])  + " / " + str(cal_params['dec_center'])
         debug_txt = "POS: " + str(cal_params['position_angle'])
         debug_txt = "PX SCALE: " + str(cal_params['pixscale'])
         cv2.putText(temp_img, str(dcname),  (int(new_cat_x),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)


      #show_image(temp_img,'pepe', 0)

   if total_matches > 1:
      total_res_px = total_cat_dist / total_matches
   else:
      total_res_px = 999
   good_stars = []
   if total_res_px < 4:
      total_res_px = 4
   for star in my_close_stars:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
      if cat_dist < total_res_px * 3:
         good_stars.append(star)

   my_close_stars = good_stars

   cal_params['cat_image_stars'] = my_close_stars
   if total_matches > 0:
      cal_params['total_res_deg'] = total_match_dist / total_matches
      cal_params['total_res_px'] = total_cat_dist / total_matches
   else:
      cal_params['total_res_deg'] = 9999
      cal_params['total_res_px'] = 9999
   cal_params['cal_params_file'] = cal_params_file

   fit_on = 0
   if fit_on == 1:
      os.system("./fitPairs.py " + cal_params_file)
   #cal_params['cat_image_stars'], bad = qc_stars(cal_params['cat_image_stars'])
   cal_params['cat_image_stars'], res_px,res_deg = cat_star_report(cal_params['cat_image_stars'], 4)
   cal_params['total_res_px'] = res_px
   cal_params['total_res_deg'] = res_deg

   return(cal_params)



def HMS2deg(ra='', dec=''):
  RA, DEC, rs, ds = '', '', 1, 1
  if dec:
    D, M, S = [float(i) for i in dec.split()]
    if str(D)[0] == '-':
      ds, D = -1, abs(D)
    deg = D + (M/60) + (S/3600)
    DEC = '{0}'.format(deg*ds)

  if ra:
    H, M, S = [float(i) for i in ra.split()]
    if str(H)[0] == '-':
      rs, H = -1, abs(H)
    deg = (H*15) + (M/4) + (S/240)
    RA = '{0}'.format(deg*rs)

  if ra and dec:
    return (RA, DEC)
  else:
    return RA or DEC

def RAdeg2HMS( RAin ):
   RAin = float(RAin)
   if(RAin<0):
      sign = -1
      ra   = -RAin
   else:
      sign = 1
      ra   = RAin

   h = int( ra/15. )
   ra -= h*15.
   m = int( ra*4.)
   ra -= m/4.
   s = ra*240.

   if(sign == -1):
      out = '-%02d:%02d:%06.3f'%(h,m,s)
   else: out = '+%02d:%02d:%06.3f'%(h,m,s)

   return out



def minimize_fov(cal_file, cal_params, image_file,img,json_conf ):
   #print("CAT STARS:", len(cal_params['cat_image_stars']))
   orig_cal = dict(cal_params)
   #this_poly = [.25,.25,.25,.25]

   cal_params = update_center_radec(cal_file,cal_params,json_conf)
   std_dist, avg_dist = calc_starlist_res(cal_params['cat_image_stars'])
   az = np.float64(orig_cal['center_az'])
   el = np.float64(orig_cal['center_el'])
   pos = np.float64(orig_cal['position_angle'])
   pixscale = np.float64(orig_cal['pixscale'])
   x_poly = np.float64(orig_cal['x_poly'])
   y_poly = np.float64(orig_cal['y_poly'])

   #if "short_bright_stars" not in cal_params:
   #short_bright_stars = get_catalog_stars(cal_params)
   #cal_params['short_bright_stars'] = short_bright_stars
   #print(len(cal_params['short_bright_stars']))

   short_bright_stars = []
   if "cat_image_stars" in cal_params:
      for star in cal_params['cat_image_stars']:

         dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
         short_bright_stars.append((dcname,dcname,ra,dec,mag))
      cal_params['short_bright_stars'] = short_bright_stars
   else:
      cp['short_bright_stars'] = None


   this_poly = np.zeros(shape=(4,), dtype=np.float64)
   #this_poly = [.1,.1,.1,.1]
   #print("CAT STARS:", len(cal_params['cat_image_stars']))
   res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=( az,el,pos,pixscale,x_poly, y_poly, image_file,img,json_conf, cal_params['cat_image_stars'],cal_params['user_stars'],1,SHOW,None,cal_params['short_bright_stars']), method='Nelder-Mead')



   #print("RESULT:", res)
   adj_az, adj_el, adj_pos, adj_px = res['x']

   new_az = az + (adj_az*az)
   new_el = el + (adj_el*el)
   new_position_angle = pos + (adj_pos*pos)
   new_pixscale = pixscale + (adj_px*pixscale)


   cal_params['center_az'] =  new_az
   cal_params['center_el'] =  new_el
   cal_params['position_angle'] =  new_position_angle
   cal_params['pixscale'] =  new_pixscale
   cal_params = update_center_radec(cal_file,cal_params,json_conf)

   if "fov_fit" not in cal_params:
      cal_params['fov_fit'] = 1
   else:
      cal_params['fov_fit'] += 1
   if len(img.shape) > 2:
      gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
   else:
      gray_img = img

   cp = pair_stars(cal_params, image_file, json_conf, gray_img)
   trash_stars, res_px,res_deg = cat_star_report(cp['cat_image_stars'], 4)

   if math.isnan(res_px) is True:
      print("TOTAL RES IS NAN:", res_px )
      exit()
   cp['total_res_px'] = res_px
   cp['total_res_deg'] = res_deg

   return(cal_params)

def XYtoRADec(img_x,img_y,cal_file,cal_params,json_conf):
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cal_file)
   F_scale = 3600/float(cal_params['pixscale'])
   #F_scale = 24

   total_min = (int(hd_h) * 60) + int(hd_M)
   day_frac = total_min / 1440
   hd_d = int(hd_d) + day_frac
   #jd = date_to_jd(int(hd_y),int(hd_m),float(hd_d))

   (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(cal_file)
   jd = datetime2JD(f_datetime, 0.0)
   #hour_angle = JD2HourAngle(jd)

   lat = float(json_conf['site']['device_lat'])
   lon = float(json_conf['site']['device_lng'])

   # Calculate the reference hour angle
   T = (jd - 2451545.0)/36525.0
   Ho = (280.46061837 + 360.98564736629*(jd - 2451545.0) + 0.000387933*T**2 \
      - (T**3)/38710000.0)%360
   if "x_poly_fwd" in cal_params:
      x_poly_fwd = cal_params['x_poly_fwd']
      y_poly_fwd = cal_params['y_poly_fwd']
   else:
      x_poly_fwd = np.zeros(shape=(15,),dtype=np.float64)
      y_poly_fwd = np.zeros(shape=(15,),dtype=np.float64)

   dec_d = float(cal_params['dec_center'])
   RA_d = float(cal_params['ra_center'])

   dec_d = dec_d + (x_poly_fwd[13] * 100)
   dec_d = dec_d + (y_poly_fwd[13] * 100)

   RA_d = RA_d + (x_poly_fwd[14] * 100)
   RA_d = RA_d + (y_poly_fwd[14] * 100)

   pos_angle_ref = float(cal_params['position_angle']) + (1000*x_poly_fwd[12]) + (1000*y_poly_fwd[12])

   # Convert declination to radians
   dec_rad = math.radians(dec_d)

   # Precalculate some parameters
   sl = math.sin(math.radians(lat))
   cl = math.cos(math.radians(lat))

   if "imagew" not in cal_params:
      cal_params['imagew'] = 1920
      cal_params['imageh'] = 1080

   x_det = img_x - int(cal_params['imagew'])/2
   y_det = img_y - int(cal_params['imageh'])/2

   #x = img_x
   #y = img_y
   #x0 = x_poly[0]
   #y0 = y_poly[0]

   #r = math.sqrt((x - x0)**2 + (y - y0)**2)

   dx = (x_poly_fwd[0]
      + x_poly_fwd[1]*x_det
      + x_poly_fwd[2]*y_det
      + x_poly_fwd[3]*x_det**2
      + x_poly_fwd[4]*x_det*y_det
      + x_poly_fwd[5]*y_det**2
      + x_poly_fwd[6]*x_det**3
      + x_poly_fwd[7]*x_det**2*y_det
      + x_poly_fwd[8]*x_det*y_det**2
      + x_poly_fwd[9]*y_det**3
      + x_poly_fwd[10]*x_det*math.sqrt(x_det**2 + y_det**2)
      + x_poly_fwd[11]*y_det*math.sqrt(x_det**2 + y_det**2))

   #dx += x_poly_fwd[12]*x_det*math.sqrt(x_det**2 + y_det**2)**3
   #dx += x_poly_fwd[13]*x_det*math.sqrt(x_det**2 + y_det**2)**5
   # Add the distortion correction
   x_pix = x_det + dx

   dy = (y_poly_fwd[0]
      + y_poly_fwd[1]*x_det
      + y_poly_fwd[2]*y_det
      + y_poly_fwd[3]*x_det**2
      + y_poly_fwd[4]*x_det*y_det
      + y_poly_fwd[5]*y_det**2
      + y_poly_fwd[6]*x_det**3
      + y_poly_fwd[7]*x_det**2*y_det
      + y_poly_fwd[8]*x_det*y_det**2
      + y_poly_fwd[9]*y_det**3
      + y_poly_fwd[10]*y_det*math.sqrt(x_det**2 + y_det**2)
      + y_poly_fwd[11]*x_det*math.sqrt(x_det**2 + y_det**2))

   #dy += y_poly_fwd[12]*y_det*math.sqrt(x_det**2 + y_det**2)**3
   #dy += y_poly_fwd[13]*y_det*math.sqrt(x_det**2 + y_det**2)**5


   # Add the distortion correction
   y_pix = y_det + dy

   x_pix = x_pix / F_scale
   y_pix = y_pix / F_scale

   ### Convert gnomonic X, Y to alt, az ###

   # Caulucate the needed parameters
   radius = math.radians(math.sqrt(x_pix**2 + y_pix**2))
   theta = math.radians((90 - pos_angle_ref + math.degrees(math.atan2(y_pix, x_pix)))%360)

   sin_t = math.sin(dec_rad)*math.cos(radius) + math.cos(dec_rad)*math.sin(radius)*math.cos(theta)
   Dec0det = math.atan2(sin_t, math.sqrt(1 - sin_t**2))

   sin_t = math.sin(theta)*math.sin(radius)/math.cos(Dec0det)
   cos_t = (math.cos(radius) - math.sin(Dec0det)*math.sin(dec_rad))/(math.cos(Dec0det)*math.cos(dec_rad))
   RA0det = (RA_d - math.degrees(math.atan2(sin_t, cos_t)))%360

   h = math.radians(Ho + lon - RA0det)
   sh = math.sin(h)
   sd = math.sin(Dec0det)
   ch = math.cos(h)
   cd = math.cos(Dec0det)

   x = -ch*cd*sl + sd*cl
   y = -sh*cd
   z = ch*cd*cl + sd*sl

   r = math.sqrt(x**2 + y**2)

   # Calculate azimuth and altitude
   azimuth = math.degrees(math.atan2(y, x))%360
   altitude = math.degrees(math.atan2(z, r))

   ### Convert alt, az to RA, Dec ###

   # Never allow the altitude to be exactly 90 deg due to numerical issues
   if altitude == 90:
      altitude = 89.9999

   # Convert altitude and azimuth to radians
   az_rad = math.radians(azimuth)
   alt_rad = math.radians(altitude)

   saz = math.sin(az_rad)
   salt = math.sin(alt_rad)
   caz = math.cos(az_rad)
   calt = math.cos(alt_rad)

   x = -saz*calt
   y = -caz*sl*calt + salt*cl
   HA = math.degrees(math.atan2(x, y))

   # Calculate the hour angle
   T = (jd - 2451545.0)/36525.0
   hour_angle = (280.46061837 + 360.98564736629*(jd - 2451545.0) + 0.000387933*T**2 - T**3/38710000.0)%360

   RA = (hour_angle + lon - HA)%360
   dec = math.degrees(math.asin(sl*salt + cl*calt*caz))

   ### ###




   return(x_pix+img_x,y_pix+img_y,RA,dec,azimuth,altitude)



def find_close_stars(star_point, catalog_stars,dt=100):
   scx,scy = star_point
   #scx,scy = scx, scy

   center_dist = calc_dist((scx,scy),(960,540))
   if center_dist > 500:
      dt = 120
   if center_dist > 700:
      dt = 140
   if center_dist > 800:
      dt = 160
   if center_dist > 900:
      dt = 180


   matches = []
   nomatches = []
   for name,mag,ra,dec,cat_x,cat_y in catalog_stars:
      try:
         dcname = str(name.decode("utf-8"))
         dbname = dcname.encode("utf-8")
      except:
         dcname = name
         dbname = name
      cat_x, cat_y = cat_x, cat_y
      cat_center_dist = calc_dist((cat_x,cat_y),(960,540))

      if cat_x - dt < scx < cat_x + dt and cat_y -dt < scy < cat_y + dt:
         cat_star_dist= calc_dist((cat_x,cat_y),(scx,scy))
         matches.append((dcname,mag,ra,dec,cat_x,cat_y,scx,scy,cat_star_dist))
      else:
         cat_star_dist= calc_dist((cat_x,cat_y),(scx,scy))
         nomatches.append((dcname,mag,ra,dec,cat_x,cat_y,scx,scy,cat_star_dist))



   if len(matches) > 1:
      matches_sorted = sorted(matches, key=lambda x: x[8], reverse=False)
      # check angle back to center from cat star and then angle from cat star to img star and pick the one with the closest match for the star...
      #for match in matches_sorted:

      matches = matches_sorted
   else:
      no_matches_sorted = sorted(nomatches, key=lambda x: x[8], reverse=False)
   return(matches[0:1])


def calc_dist(p1,p2):
   x1,y1 = p1
   x2,y2 = p2
   dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
   return dist


def cat_star_report(cat_image_stars, multi=2.5):
   #multi = 100
   c_dist = []
   m_dist = []
   for star in cat_image_stars:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      c_dist.append(abs(cat_dist))
      m_dist.append(abs(match_dist))
   med_c_dist = np.median(c_dist)
   med_m_dist = np.median(m_dist)
   if med_c_dist < 1:
      med_c_dist = 1

   clean_stars = []
   c_dist = []
   m_dist = []
   for star in cat_image_stars:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      center_dist = calc_dist((six,siy),(960,540))
      cat_center_dist = calc_dist((new_cat_x,new_cat_y),(960,540))
      if 800 < center_dist < 1000:
         multi = 12
         if med_c_dist <= 3:
            med_c_dist = 3
      elif 400 < center_dist <= 800:
         multi = 7
         if med_c_dist <= 2.5:
            med_c_dist = 2.5
      else:
         multi = 2.5

      if cat_dist > med_c_dist * multi:
      #if False:
         foo = 1
      else:
         c_dist.append(abs(cat_dist))
         m_dist.append(abs(match_dist))
         clean_stars.append(star)
   return(clean_stars, np.mean(c_dist), np.mean(m_dist))


def draw_star_image(img, cat_image_stars,cp=None) :

   from matplotlib import font_manager
   font = font_manager.FontProperties(family='sans-serif', weight='bold')
   file = font_manager.findfont(font)

   for star in cat_image_stars:
      if len(star) == 9:
         dcname,mag,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist = star
      else:
         dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      if siy < 1080 and six < 1920:
         img[int(siy),int(six)] = [0,0,255]

   image = Image.fromarray(img)
   draw = ImageDraw.Draw(image)
   #font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 20, encoding="unic" )
   font = ImageFont.truetype(file, 20, encoding="unic")
   #font = ImageFont.truetype("/usr/share/fonts/truetype/DejaVuSans.ttf", 20, encoding="unic" )
   org_x = None
   org_y = None
   for star in cat_image_stars:
      if len(star) == 9:
         dcname,mag,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist = star
      else:
         dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star

      match_dist = calc_dist((new_cat_x,new_cat_y), (six,siy))
      cat_dist = match_dist
      if cat_dist <= .5:
         color = "#add900"
      if .5 < cat_dist <= 1:
         color = "#708c00"
      if 1 < cat_dist <= 2:
         color = "#0000FF"
      if 2 < cat_dist <= 3:
         color = "#FF00FF"
      if 3 < cat_dist <= 4:
         color = "#FF0000"
      if cat_dist > 4:
         color = "#ff0000"

      #print("DRAW:", dcname, match_dist)

      res_line = [(six,siy),(new_cat_x,new_cat_y)]
      draw.rectangle((six-7, siy-7, six+7, siy+7), outline='white')
      draw.rectangle((new_cat_x-7, new_cat_y-7, new_cat_x + 7, new_cat_y + 7), outline=color)
      #draw.ellipse((six-5, siy-5, six+7, siy+7),  outline ="white")
      draw.line(res_line, fill=color, width = 0)
      draw.text((new_cat_x, new_cat_y), str(dcname), font = font, fill="white")
      if org_x is not None:
         org_res_line = [(six,siy),(org_x,org_y)]
         draw.rectangle((org_x-5, org_y-5, org_x + 5, org_y + 5), outline="gray")
         draw.line(org_res_line, fill="gray", width = 0)
      if cp is not None:
         ltext0 = "Res Px:"
         text0 =  str(cp['total_res_px'])[0:7]
         ltext1 = "Center RA/DEC:"
         text1 =  str(cp['ra_center'])[0:6] + "/" + str(cp['dec_center'])[0:6]
         ltext2 = "Center AZ/EL:"
         text2 =  str(cp['center_az'])[0:6] + "/" + str(cp['center_el'])[0:6]
         ltext3 = "Position Angle:"
         text3 =  str(cp['position_angle'])[0:6]
         ltext4 = "Pixel Scale:"
         text4 =  str(cp['pixscale'])[0:6]
         draw.text((20, 950), str(ltext0), font = font, fill="white")
         draw.text((20, 975), str(ltext1), font = font, fill="white")
         draw.text((20, 1000), str(ltext2), font = font, fill="white")
         draw.text((20, 1025), str(ltext3), font = font, fill="white")
         draw.text((20, 1050), str(ltext4), font = font, fill="white")
         draw.text((200, 950), str(text0), font = font, fill="white")
         draw.text((200, 975), str(text1), font = font, fill="white")
         draw.text((200, 1000), str(text2), font = font, fill="white")
         draw.text((200, 1025), str(text3), font = font, fill="white")
         draw.text((200, 1050), str(text4), font = font, fill="white")
   return_img = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)

   return(return_img)



def minimize_fov(cal_file, cal_params, image_file,img,json_conf ):
   #print("CAT STARS:", len(cal_params['cat_image_stars']))
   orig_cal = dict(cal_params)
   #this_poly = [.25,.25,.25,.25]

   cal_params = update_center_radec(cal_file,cal_params,json_conf)
   std_dist, avg_dist = calc_starlist_res(cal_params['cat_image_stars'])
   az = np.float64(orig_cal['center_az'])
   el = np.float64(orig_cal['center_el'])
   pos = np.float64(orig_cal['position_angle'])
   pixscale = np.float64(orig_cal['pixscale'])
   x_poly = np.float64(orig_cal['x_poly'])
   y_poly = np.float64(orig_cal['y_poly'])

   #if "short_bright_stars" not in cal_params:
   #short_bright_stars = get_catalog_stars(cal_params)
   #cal_params['short_bright_stars'] = short_bright_stars
   #print(len(cal_params['short_bright_stars']))

   short_bright_stars = []
   if "cat_image_stars" in cal_params:
      for star in cal_params['cat_image_stars']:

         dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
         short_bright_stars.append((dcname,dcname,ra,dec,mag))
      cal_params['short_bright_stars'] = short_bright_stars
   else:
      cp['short_bright_stars'] = None


   this_poly = np.zeros(shape=(4,), dtype=np.float64)
   #this_poly = [.1,.1,.1,.1]
   #print("CAT STARS:", len(cal_params['cat_image_stars']))
   res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=( az,el,pos,pixscale,x_poly, y_poly, image_file,img,json_conf, cal_params['cat_image_stars'],cal_params['user_stars'],1,SHOW,None,cal_params['short_bright_stars']), method='Nelder-Mead')



   #print("RESULT:", res)
   adj_az, adj_el, adj_pos, adj_px = res['x']

   new_az = az + (adj_az*az)
   new_el = el + (adj_el*el)
   new_position_angle = pos + (adj_pos*pos)
   new_pixscale = pixscale + (adj_px*pixscale)


   cal_params['center_az'] =  new_az
   cal_params['center_el'] =  new_el
   cal_params['position_angle'] =  new_position_angle
   cal_params['pixscale'] =  new_pixscale
   cal_params = update_center_radec(cal_file,cal_params,json_conf)

   if "fov_fit" not in cal_params:
      cal_params['fov_fit'] = 1
   else:
      cal_params['fov_fit'] += 1
   if len(img.shape) > 2:
      gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
   else:
      gray_img = img

   cp = pair_stars(cal_params, image_file, json_conf, gray_img)
   trash_stars, res_px,res_deg = cat_star_report(cp['cat_image_stars'], 4)

   if math.isnan(res_px) is True:
      print("TOTAL RES IS NAN:", res_px )
      exit()
   cp['total_res_px'] = res_px
   cp['total_res_deg'] = res_deg

   return(cal_params)

def reduce_fov_pos(this_poly, az,el,pos,pixscale, x_poly, y_poly, cal_params_file, oimage, json_conf, paired_stars, user_stars, min_run = 1, show=0, field = None, short_bright_stars = None):
   #print("SHORT", len(short_bright_stars))

   global tries
   tries = tries + 1
   image = oimage.copy()
   image = cv2.resize(image, (1920,1080))


   start_stars = len(paired_stars)

   if field is None:
      new_az = az + (this_poly[0]*az)
      new_el = el + (this_poly[1]*el)
      new_position_angle = pos + (this_poly[2]*pos)
      new_pixscale = pixscale + (this_poly[3]*pixscale)


   lat,lng,alt = get_device_lat_lon(json_conf)
   cal_temp = {
      'center_az' : new_az,
      'center_el' : new_el,
      'position_angle' : new_position_angle,
      'pxscale' : new_pixscale,
      'site_lat' : lat,
      'site_lng' : lng,
      'site_alt' : alt,
      'user_stars' : user_stars,
   }

   rah,dech = AzEltoRADec(new_az,new_el,cal_params_file,cal_temp,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))

   temp_cal_params = {}
   temp_cal_params['position_angle'] = new_position_angle
   temp_cal_params['ra_center'] = ra_center
   temp_cal_params['dec_center'] = dec_center
   temp_cal_params['center_az'] = new_az
   temp_cal_params['center_el'] = new_el
   temp_cal_params['pixscale'] = new_pixscale
   temp_cal_params['device_lat'] = json_conf['site']['device_lat']
   temp_cal_params['device_lng'] = json_conf['site']['device_lng']
   temp_cal_params['device_alt'] = json_conf['site']['device_alt']
   temp_cal_params['imagew'] = 1920
   temp_cal_params['imageh'] = 1080
   temp_cal_params['x_poly'] = x_poly
   temp_cal_params['y_poly'] = y_poly
   temp_cal_params['user_stars'] = user_stars
   temp_cal_params['cat_image_stars'] = paired_stars
   #if short_bright_stars is not None:
   #   temp_cal_params['short_bright_stars'] = short_bright_stars

   fov_poly = 0
   pos_poly = 0
   if short_bright_stars is not None:
      cat_stars = short_bright_stars
   else:
      cat_stars = get_catalog_stars(temp_cal_params)
   # MIKE!
   before = time.time()
   temp_cal_params, bad_stars, marked_img = eval_cal_res(cal_params_file, json_conf, temp_cal_params, oimage,None,None,cat_stars)
   elp = time.time() - before
   #print("EVAL RUN TIME:", elp)
   #temp_cal_params, bad_stars, marked_img = eval_cal(cal_params_file, json_conf, temp_cal_params, oimage,None,None,cat_stars)
   tstars = len(temp_cal_params['cat_image_stars'])
   sd = start_stars - tstars
   if sd <= 0:
      sd = 0
   match_val = 1 - temp_cal_params['match_perc']
   print("STARS/RES:", sd, temp_cal_params['total_res_px'])
   return(temp_cal_params['total_res_px'] +sd)




def eval_cal_res(cp_file,json_conf,nc=None,oimg=None, mask_img=None,batch_mode=None,short_bright_stars=None):
   dist_type = "radial"
   cal_params = nc

   degrees_per_pix = float(cal_params['pixscale'])*0.000277778
   px_per_degree = 1 / degrees_per_pix

   (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(cp_file)
   jd = datetime2JD(f_datetime, 0.0)
   hour_angle = JD2HourAngle(jd)

   rez = []
   new_cat_stars = []

   #print(float(cal_params['ra_center']))
   #print(float(cal_params['dec_center']))
   #print(float(cal_params['position_angle']))
   #print(px_per_degree)
   nc['no_match_stars'] = []

   for star in nc['cat_image_stars']:
      #print(star)
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cp_file,nc,json_conf)


      new_cat_x, new_cat_y = distort_xy(0,0,ra,dec,float(cal_params['ra_center']), float(cal_params['dec_center']), cal_params['x_poly'], cal_params['y_poly'], float(cal_params['imagew']), float(cal_params['imageh']), float(cal_params['position_angle']),3600/float(cal_params['pixscale']))
      cat_dist = calc_dist((six,siy),(new_cat_x,new_cat_y))
      rez.append(cat_dist)

      new_cat_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int))

   nc['cat_image_stars'] = new_cat_stars
   bad_stars = []
   marked_img = None
   nc['match_perc'] = 1
   nc['total_res_px'] = float(np.mean(rez))
   #marked_img = view_calib(cp_file,json_conf,nc,oimg)

   #print("SUM REZ:", sum(rez))
   #print("MEAN REZ:", np.mean(rez))
   print("EVAL", len(nc['cat_image_stars']), nc['total_res_px'])
   return(nc, bad_stars, marked_img)



def view_calib(cp_file,json_conf,nc,oimg, show = 0):
   (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(cp_file)
   img = oimg.copy()
   tres = 0
   for star in nc['user_stars']:
      if star is None:
         continue
      if len(star) == 3:
         x,y,flux = star
      else:
         x,y = star
         flux = 0
      #cv2.circle(img,(x,y), 5, (128,128,128), 1)
   for star in nc['no_match_stars']:
      name,mag,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist = star
      #cv2.circle(img,(int(new_cat_x),int(new_cat_y)), 5, (128,255,128), 1)

   for star in nc['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      #cv2.circle(img,(six,siy), 10, (128,128,128), 1)
      #cv2.circle(img,(int(new_x),int(new_y)), 10, (128,128,255), 1)
      #cv2.circle(img,(int(new_cat_x),int(new_cat_y)), 10, (128,255,128), 1)
      #cv2.line(img, (int(new_cat_x),int(new_cat_y)), (int(new_x),int(new_y)), (255), 2)
      #cv2.line(img, (int(six),int(siy)), (int(new_cat_x),int(new_cat_y)), (255), 2)
      #cv2.putText(img, str(dcname),  (int(new_cat_x),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
      #cv2.line(marked_img, (six,siy), (new_x,new_y), (255), 2)
      tres += cat_dist

   fn, dir = fn_dir(cp_file)
   #cv2.putText(img, "Res:" + str(nc['total_res_px'])[0:5],  (25,25), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   #cv2.putText(img, "AZ/EL:" + str(nc['center_az'])[0:6] + "/" + str(nc['center_el'])[0:6],  (25,50), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   #cv2.putText(img, "RA/DEC:" + str(nc['ra_center'])[0:6] + "/" + str(nc['dec_center'])[0:6],  (25,75), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   #cv2.putText(img, "POS:" + str(nc['position_angle'])[0:6] ,  (25,100), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   #cv2.putText(img, "PIX:" + str(nc['pixscale'])[0:6] ,  (25,125), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   #cv2.putText(img, "File:" + str(fn),  (25,150), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   #cv2.putText(img, "Match %:" + str(nc['match_perc']),  (25,175), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   #cv2.putText(img, "POLY" +  str(nc['x_poly'][0]),  (25,200), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)


   img = draw_star_image(img, nc['cat_image_stars'], nc)
   global MOVIE_FN
   if SHOW == 1:
      #dimg = cv2.resize(img, (1280,720))
      cv2.imshow('pepe9', img)
      cv2.waitKey(30)
      if MOVIE_FN % 50 == 0:
         cal_fn = cp_file.split("/")[-1]
         if MOVIE == 1:
            cv2.imwrite(MOVIE_DIR + cam + "_fov_fit" + cal_fn.replace(".json", "") + "_" + str(MOVIE_FN) + ".jpg", img)
            #print(MOVIE_DIR + cam + "_fov_fit" + cal_fn.replace(".json", "") + "_" + str(MOVIE_FN) + ".jpg")
      MOVIE_FN += 1
   return(img)

def calc_starlist_res(ms):

   # compute std dev distance
   tot_res = 0
   close_stars = []
   dist_list = []
   for star in ms:
      if len(star) == 16:
         iname,mag,o_ra,o_dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist  =star
      if len(star) == 17:
         iname,mag,o_ra,o_dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist,star_int  =star
      if len(star) == 24:
         (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star
      dist_list.append(cat_dist)
   std_dev_dist = np.std(dist_list)
   avg_dev_dist = np.mean(dist_list)
   return(std_dev_dist, avg_dev_dist)


def get_device_lat_lon(json_conf):
   if "device_lat" in json_conf['site']:
      lat = json_conf['site']['device_lat']
      lng = json_conf['site']['device_lng']
      alt = json_conf['site']['device_alt']
   else:
      lat = json_conf['site']['site_lat']
      lng = json_conf['site']['site_lng']
      alt = json_conf['site']['site_alt']
   return(lat,lng,alt)
