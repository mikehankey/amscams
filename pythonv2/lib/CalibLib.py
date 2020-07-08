import time
import subprocess
import math
from pathlib import Path
import datetime
import cv2
import numpy as np
import ephem
import glob
import os

from lib.VideoLib import load_video_frames, get_masks

from lib.ImageLib import stack_frames, median_frames, adjustLevels, mask_frame
from lib.UtilLib import convert_filename_to_date_cam, bound_cnt, check_running,date_to_jd, angularSeparation , calc_dist, better_parse_file_date
from lib.FileIO import cfe, save_json_file, load_json_file
#from lib.DetectLib import eval_cnt
from scipy import signal
import lib.brightstardata as bsd

mybsd = bsd.brightstardata()
bright_stars = mybsd.bright_stars


# XY To RADEC 
# distort_xy_new (should be called RADEC to corrected xy)
#AZ TO RA DEC (and then to XY)

def AzEltoRADec(az,el,cal_file,cal_params,json_conf):
   azr = np.radians(az)
   elr = np.radians(el)
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cal_file)
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
   #print("AZ/RA DEBUG: ", device_lat, device_lng, device_alt, hd_datetime, az, el)
   #print("AZ2RA DATETIME:", hd_datetime)
   #print("AZ2RA LAT:", obs.lat)
   #print("AZ2RA LON:", obs.lon)
   #print("AZ2RA ELV:", obs.elevation)
   #print("AZ2RA DATE:", obs.date)
   #print("AZ2RA AZ,EL:", az,el)
   #print("AZ2RA RAD AZ,EL:", azr,elr)

   ra,dec = obs.radec_of(azr,elr)
   
   #print("AZ2RA RA,DEC:", ra,dec)

   return(ra,dec)


def XYtoRADec(img_x,img_y,cal_file,cal_params,json_conf):
   #print("CAL FILE IS : ", cal_file)
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cal_file)
   F_scale = 3600/float(cal_params['pixscale'])
   #F_scale = 24

   total_min = (int(hd_h) * 60) + int(hd_M)
   day_frac = total_min / 1440 
   hd_d = int(hd_d) + day_frac
   jd = date_to_jd(int(hd_y),int(hd_m),float(hd_d))

   lat = float(json_conf['site']['device_lat'])
   lon = float(json_conf['site']['device_lng'])

   # Calculate the reference hour angle
   T = (jd - 2451545.0)/36525.0
   Ho = (280.46061837 + 360.98564736629*(jd - 2451545.0) + 0.000387933*T**2 \
      - (T**3)/38710000.0)%360

   x_poly_fwd = cal_params['x_poly_fwd']
   y_poly_fwd = cal_params['y_poly_fwd']
   
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


   x_det = img_x - int(cal_params['imagew'])/2
   y_det = img_y - int(cal_params['imageh'])/2

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

   # Add the distortion correction
   x_pix = x_det + dx 

   #print("ORIG X:", img_x)
   #print("X DET:", x_det)
   #print("DX :", dx)
   #print("NEWX :", x_pix)

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



def Decdeg2DMS( Decin ):
   Decin = float(Decin)
   if(Decin<0):
      sign = -1
      dec  = -Decin
   else:
      sign = 1
      dec  = Decin

   d = int( dec )
   dec -= d
   dec *= 100.
   m = int( dec*3./5. )
   dec -= m*5./3.
   s = dec*180./5.

   if(sign == -1):
      out = '-%02d:%02d:%06.3f'%(d,m,s)
   else: out = '+%02d:%02d:%06.3f'%(d,m,s)

   return out

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


def radec_to_azel(ra,dec, caldate,json_conf, lat=None,lon=None,alt=None):
   if lat is None:
      lat = json_conf['site']['device_lat']
      lon = json_conf['site']['device_lng']
      alt = json_conf['site']['device_alt']

   body = ephem.FixedBody()
   #print ("BODY: ", ra, dec)
   body._epoch=ephem.J2000

   rah = RAdeg2HMS(ra)
   dech= Decdeg2DMS(dec)

   body._ra = rah
   body._dec = dech

   

   obs = ephem.Observer()
   obs.lat = ephem.degrees(lat)
   obs.lon = ephem.degrees(lon)
   obs.date = caldate
   obs.elevation=float(alt)
   body.compute(obs)
   az = str(body.az)
   el = str(body.alt)

   #print("RADEC_2_AZEL BODY RA:", body._ra)
   #print("RADEC_2_AZEL BODY DEC:", body._dec)
   #print("RADEC_2_AZEL OBS DATE:", obs.date)
   #print("RADEC_2_AZEL OBS LAT:", obs.lat)
   #print("RADEC_2_AZEL OBS LON:", obs.lon)
   #print("RADEC_2_AZEL OBS EL:", obs.elevation)
   #print("RADEC_2_AZEL AZH AZH:", az)
   #print("RADEC_2_AZEL ELH ELH:", el)
   
   (d,m,s) = az.split(":")
   dd = float(d) + float(m)/60 + float(s)/(60*60)
   az = dd

   (d,m,s) = el.split(":")
   dd = float(d) + float(m)/60 + float(s)/(60*60)
   el = dd
   #az = ephem.degrees(body.az)

   #print("RADEC_2_AZEL DATE:", caldate)
   #print("RADEC_2_AZEL lat:", lat)
   #print("RADEC_2_AZEL lon:", lon)
   #print("RADEC_2_AZEL alt:", alt)
   #print("RADEC_2_AZEL RA IN:", ra)
   #print("RADEC_2_AZEL DEC IN:", dec)
   #print("RADEC_2_AZEL RAH IN:", rah)
   #print("RADEC_2_AZEL DECH IN:", dech)
   #print("RADEC_2_AZEL AZ OUT:", az)
   #print("RADEC_2_AZEL EL OUT:", el)

   return(az,el)


def xyfits(cal_file, stars):
   xyfile = cal_file.replace(".jpg", "-xy.txt")
   xyf = open(xyfile, "w")
   xyf.write("x,y\n")
   for x,y,mg in stars:
      xyf.write(str(x) + "," + str(y) + "\n")
   xyf.close()

   xyfits = xyfile.replace(".txt", ".fits")

   cmd = "/usr/local/astrometry/bin/text2fits -f \"ff\" -s \",\" " + xyfile + " " + xyfits
   print (cmd)
   os.system(cmd)

   cmd = "/usr/local/astrometry/bin/solve-field " + xyfits + " --overwrite --width=1920 --height=1080 --scale-low 50 --scale-high 95 --no-remove-lines --x-column x --y-column y"
   os.system(cmd)
   print(cmd)


def check_if_solved(cal_file):
   cal_wild = cal_file.replace(".jpg", "*")
   astr_files = []
   solved = 0
   for astr_file in sorted((glob.glob(cal_wild))):
      if 'wcs' in  astr_file:
         print("This image has been solved.")
         solved = 1
      astr_files.append(astr_file)
   return(solved, astr_files)


def save_cal_params(wcs_file):
   wcs_info_file = wcs_file.replace(".wcs", "-wcsinfo.txt")
   cal_params_file = wcs_file.replace(".wcs", "-calparams.json")
   fp =open(wcs_info_file, "r")
   cal_params_json = {}
   for line in fp:
      line = line.replace("\n", "")
      field, value = line.split(" ")
      if field == "imagew":
         cal_params_json['imagew'] = value
      if field == "imageh":
         cal_params_json['imageh'] = value
      if field == "pixscale":
         cal_params_json['pixscale'] = value
      if field == "orientation":
         cal_params_json['position_angle'] = float(value) + 180
      if field == "ra_center":
         cal_params_json['ra_center'] = value
      if field == "dec_center":
         cal_params_json['dec_center'] = value
      if field == "fieldw":
         cal_params_json['fieldw'] = value
      if field == "fieldh":
         cal_params_json['fieldh'] = value
      if field == "ramin":
         cal_params_json['ramin'] = value
      if field == "ramax":
         cal_params_json['ramax'] = value
      if field == "decmin":
         cal_params_json['decmin'] = value
      if field == "decmax":
         cal_params_json['decmax'] = value

   save_json_file(cal_params_file, cal_params_json)


def find_image_stars(cal_img):
   bgavg = np.mean(cal_img)
   thresh = bgavg * 1.5
   if thresh < 1:
      thresh =  10

   print("THREHS:", thresh)
   if cal_img.shape == 3:
      cal_img= cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)
   cal_img = cv2.GaussianBlur(cal_img, (7, 7), 0)
   _, threshold = cv2.threshold(cal_img.copy(), thresh, 255, cv2.THRESH_BINARY)
   #cal_img = cv2.dilate(threshold, None , iterations=4)
   cal_img= cv2.convertScaleAbs(threshold)
   (_, cnts, xx) = cv2.findContours(cal_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   star_pixels = []
   non_star_pixels = []
   cloudy_areas = []
   for (i,c) in enumerate(cnts):
      x,y,w,h= cv2.boundingRect(cnts[i])
      if w > 1 and h > 1:
         star_pixels.append((x,y,w,h))
         #cv2.rectangle(cal_img, (x, y), (x + w, y + h), (128, 128, 128), 1)
   return(star_pixels,cal_img)

def last_sunrise_set(json_conf, cal_date = None):
   if cal_date == None:
      cal_date =  datetime.date.today().strftime("%Y-%m-%d %H:%M:%S")
   print("CAL DATE:", cal_date)
   device_lat = json_conf['site']['device_lat']
   device_lng = json_conf['site']['device_lng']

   obs = ephem.Observer()

   obs.pressure = 0
   obs.horizon = '-0:34'
   obs.lat = device_lat
   obs.lon = device_lng
   obs.date = cal_date

   sun = ephem.Sun()
   sun.compute(obs)
   last_sunrise = obs.previous_rising(ephem.Sun())
   last_sunset = obs.previous_setting(ephem.Sun())
   # if the sun is currently set, use the next sunset as the end time not prev
   timediff = last_sunrise - last_sunset
   print(last_sunrise, last_sunset)
   print(timediff)
   sr_datetime = last_sunrise.datetime().strftime('%Y-%m-%d %H:%M:%S')
   ss_datetime = last_sunset.datetime().strftime('%Y-%m-%d %H:%M:%S')
   print(sr_datetime)
   print(ss_datetime)
   sr_datetime_t = datetime.datetime.strptime(sr_datetime, "%Y-%m-%d %H:%M:%S")
   ss_datetime_t = datetime.datetime.strptime(ss_datetime, "%Y-%m-%d %H:%M:%S")

   time_diff = sr_datetime_t - ss_datetime_t
   hr = time_diff.seconds / (3600)   
   print(sr_datetime,ss_datetime,hr)
   return(sr_datetime_t, ss_datetime_t,hr)

def find_hd_file(cal_glob):
   print(cal_glob)
   files = glob.glob(cal_glob)
   return(files)

def calibrate_pic(cal_image_file, json_conf, show = 1):
   cal_file = cal_image_file
   new_cal_file = cal_file
   orig_cal_file = cal_image_file.replace(".jpg", "-orig.jpg")
   plate_cal_file = cal_image_file.replace(".jpg", "-plate.jpg")
   dark_cal_file = cal_image_file.replace(".jpg", "-dark.jpg")

   cal_image_np = cv2.imread(cal_image_file, 0)
   orig_image = cal_image_np
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cal_image_file)


   cams_id = hd_cam

   print("cal pic")
   cams_id = cams_id.replace(".jpg", "")
   print("CAMS ID:", cams_id)
   masks = get_masks(cams_id, json_conf, hd = 1)
   print("MASKS:", masks)
   cal_image_np = mask_frame(cal_image_np, [], masks)
   avg_px = np.mean(cal_image_np)
   print("AVG PX",avg_px)
   temp = adjustLevels(cal_image_np, avg_px+10,1,255)
   cal_image_adj  = cv2.convertScaleAbs(temp)

   cv2.imwrite(new_cal_file, cal_image_np)
   cv2.imwrite(dark_cal_file, cal_image_adj)
   cv2.imwrite(orig_cal_file, orig_image)

   cal_star_file = cal_file.replace(".jpg", "-median.jpg")

   show_img = cv2.resize(cal_image_np, (0,0),fx=.4, fy=.4)
   cv2.putText(show_img, "Cal Image NP",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(10)
   (stars, nonstars, plate_image,plate_image_4f) = make_plate_image(cal_image_adj, cal_star_file, cams_id, json_conf)
   cv2.imwrite(plate_cal_file, plate_image)
   plate_cal_file_4f = plate_cal_file.replace(".jpg", "-4f.jpg")
   cv2.imwrite(plate_cal_file_4f, plate_image_4f)

   if show == 1:
      show_img = cv2.resize(plate_image, (0,0),fx=.4, fy=.4)
      cv2.namedWindow('pepe')
      cv2.putText(show_img, "Plate Image",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      cv2.imshow('pepe', show_img)
      cv2.waitKey(10)
   print("STARS:", len(stars))

   rect_file = orig_cal_file.replace("-orig", "-rect")
   for x,y,mg in sorted(stars, key=lambda x: x[2], reverse=True) :
      print(x,y,mg)
      cv2.rectangle(orig_image, (x-5, y-5), (x + 5, y + 5), (255, 0, 0), 1)
   for x,y,mg in sorted(nonstars, key=lambda x: x[2], reverse=True) :
      print(x,y,mg)
      cv2.rectangle(orig_image, (x-7, y-7), (x + 7, y + 7), (120, 0, 0), 1)
   cv2.imwrite(rect_file, orig_image)

   solved = plate_solve(new_cal_file,json_conf)



def calibrate_camera(cams_id, json_conf, cal_date = None, show=1):
   # unless passed in use the last night as the calibration date
   # check 1 frame per hour and if there are enough stars then 
   # attempt to plate solve with astrometry
   # if that succeeds fit the plate and save the calibration file

   # first find the time of the last sun rise and sun set...
   last_sunrise, last_sunset,hr = last_sunrise_set(json_conf, cal_date)
   print("Hours of Dark:", hr)
   for i in range (2,int(hr)-1):
      cal_date = last_sunset + datetime.timedelta(hours=i)
      cal_video = find_hd_file(cal_date.strftime('/mnt/ams2/HD/%Y_%m_%d_%H_%M*' + cams_id + '*.mp4') )
      if len(cal_video) == 0:
         continue 
      cal_file = cal_video[0].replace('.mp4', '.jpg')

      frames = load_video_frames(cal_video[0],json_conf,100)
      if len(frames) < 50: 
         return()

      el = cal_file.split("/")
      cal_file = "/mnt/ams2/cal/tmp/" + el[-1]
      print(cal_file)
      cal_image, cal_image_np = stack_frames(frames,cal_file) 
      #cal_image_np =  median_frames(frames) 

      orig_img = cal_image_np

      masks = get_masks(cams_id, json_conf, hd = 1)
      cal_image_np = mask_frame(cal_image_np, [], masks)
      cal_star_file = cal_file.replace(".jpg", "-median.jpg")
      cal_orig_file = cal_file.replace(".jpg", "-orig.jpg")

      #MIKE!

      avg_px = np.mean(cal_image_np)
      print("AVG PX",avg_px)
      temp = adjustLevels(cal_image_np, avg_px+10,1,255)
      cal_image_np = cv2.convertScaleAbs(temp)

      show_img = cv2.resize(cal_image_np, (0,0),fx=.4, fy=.4)
      cv2.putText(show_img, "Cal Image NP",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      cv2.imshow('pepe', show_img)
      cv2.waitKey(10)
      (stars, nonstars, plate_image, plate_image_4f) = make_plate_image(cal_image_np, cal_star_file, cams_id, json_conf)
      if show == 1:
         show_img = cv2.resize(plate_image, (0,0),fx=.4, fy=.4)
         cv2.namedWindow('pepe')
         cv2.putText(show_img, "Plate Image",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         cv2.imshow('pepe', show_img)
         cv2.waitKey(10)
     # cv2.imwrite(cal_file, cal_image_np)
      cal_file_4f = cal_file.replace(".jpg", "-4f.jpg")
      cv2.imwrite(cal_file, plate_image)
      cv2.imwrite(cal_star_file, plate_image)
      cv2.imwrite(cal_file_4f, plate_image_4f)
      cv2.imwrite(cal_orig_file, orig_img)

      print("STARS:", len(stars))
      rect_file = cal_orig_file.replace("-orig", "-rect")
      for x,y,mg in sorted(stars, key=lambda x: x[2], reverse=True) :
         print(x,y,mg)
         cv2.rectangle(orig_img, (x-5, y-5), (x + 5, y + 5), (255, 0, 0), 1)
      for x,y,mg in sorted(nonstars, key=lambda x: x[2], reverse=True) :
         print(x,y,mg)
         cv2.rectangle(orig_img, (x-7, y-7), (x + 7, y + 7), (120, 0, 0), 1)
      cv2.imwrite(rect_file, orig_img)

      print("STARS:", len(stars))
      print("NONSTARS:", len(nonstars))

      if len(stars) >= 12 and len(stars) < 200:

         #xyfits(cal_file, stars)
         #exit()
         solved = plate_solve(cal_file,json_conf)
         print("SOLVED:", solved)
         if solved == 1:
            star_file = cal_file.replace(".jpg", "-mapped-stars.json")
            cmd = "./calFit.py " + star_file
            print(cmd)
            os.system(cmd)

def find_best_cal_file(hd_datetime, hd_cam):
   cal_file = None
   return(cal_file)

def reduce_object(object, sd_video_file, hd_file, hd_trim, hd_crop_file, hd_crop_box, json_conf, trim_time_offset, cal_file = None):
   cal_param_file = None
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(hd_file)
   #cal_param_file = "/mnt/ams2/cal/solved/2019_02_17_09_54_53_000_010004-calparams.json"
   #cal_params = load_json_file(cal_param_file)
   #if cal_param_file is None:
   #   cal_param_file = find_best_cal_file(hd_datetime, hd_cam)

   print("HD TRIM REDUCE OBJECT: ", hd_trim)
   if "-trim-" in hd_trim:
      el = hd_trim.split("-trim-")
   else:
      el = hd_trim.split("-trim")
   min_file = el[0] + ".mp4"

   print(el[1])
   ttt = el[1].split("-")
   trim_num = ttt[0]

   print("REDUCE OBJECT", trim_num)

   meteor_frames = []
   #extra_sec = int(trim_num) / 25
   extra_sec = trim_time_offset
   print("DATE:", hd_datetime)
   print("EXTRA:", extra_sec)
   start_frame_time = hd_datetime + datetime.timedelta(0,int(extra_sec))
   start_frame_str = start_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
   start_frame_num = object['history'][0][0]

   print("HISTORY:", object['history'])

   for hist in object['history']:
      fc,x,y,w,h,mx,my = hist
      hd_x = x + hd_crop_box[0] 
      hd_y = y + hd_crop_box[1] 

      extra_sec = (fc) /  25
      frame_time = start_frame_time + datetime.timedelta(0,extra_sec)
      frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
      if cal_param_file is None:
         ra, dec, rad, decd, az, el = 0,0,0,0,0,0
      else:
         nx = hd_x + (w/2)
         ny = hd_y + (h/2)
         xp,yp,ra,dec,az,el= XYtoRADec(nx,ny,cal_param_file,cal_params,json_conf)
         rad = ra
         decd = dec
         print("AZ")
      meteor_frames.append((fc,frame_time_str,x,y,w,h,hd_x,hd_y,ra,dec,rad,decd,az,el))


   print("METEORFRMAES:", meteor_frames)
   return(meteor_frames) 

def plate_solve(cal_file,json_conf):

   el = cal_file.split("/")

   wcs_file = cal_file.replace(".jpg", ".wcs")
   grid_file = cal_file.replace(".jpg", "-grid.png")
   star_file = cal_file.replace(".jpg", "-stars-out.jpg")
   star_data_file = cal_file.replace(".jpg", "-stars.txt")
   astr_out = cal_file.replace(".jpg", "-astrometry-output.txt")
   wcs_info_file = cal_file.replace(".jpg", "-wcsinfo.txt")
   quarter_file = cal_file.replace(".jpg", "-1.jpg")
   image = cv2.imread(cal_file)

   if len(image.shape) > 2:
      gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
   else:
      gray = image
   height = gray.shape[0]
   width = gray.shape[1]
# --crpix-center
   cmd = "/usr/local/astrometry/bin/solve-field " + cal_file + " --crpix-center --cpulimit=30 --verbose --no-delete-temp --overwrite --width=" + str(width) + " --height=" + str(height) + " -d 1-40 --scale-units dw --scale-low 50 --scale-high 90 > " + astr_out + " 2>&1 &"
   print(cmd) 
   os.system(cmd)

   running = check_running("solve-field") 
   start_time = datetime.datetime.now()
   while running > 0:
      running = check_running("solve-field") 
      cur_time = datetime.datetime.now()
      tdiff = cur_time - start_time
      print("running plate solve.", tdiff)
      time.sleep(10)
   
   time.sleep(3)

   os.system("grep Mike " + astr_out + " >" +star_data_file + " 2>&1" )

   cmd = "/usr/bin/jpegtopnm " + cal_file + "|/usr/local/astrometry/bin/plot-constellations -w " + wcs_file + " -o " + grid_file + " -i - -N -C -G 600 > /dev/null 2>&1 "
   os.system(cmd)

   cmd = "/usr/local/astrometry/bin/wcsinfo " + wcs_file + " > " + wcs_info_file 
   os.system(cmd)

   #bright_star_data = parse_astr_star_file(star_data_file)
   #plot_bright_stars(cal_file, image, bright_star_data)
   print("GRID FILE: ", grid_file)
   solved = cfe(grid_file)
   if solved == 1:
      save_cal_params(wcs_file)
   return(solved)

def distort_xy_new(sx,sy,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale=1):

   ra_star = ra
   dec_star = dec

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

   # Add the distortion correction and calculate Y image coordinates
   #y_array[i] = (Y1 - dY)*y_res/288.0 + y_res/2.0
   new_y = Y1 - dY + y_res/2.0
   #print("DENIS RA:", X1, Y1, sx, sy, F_scale, w_pix, dist)
   #print("DENIS:", X1, Y1, dX, dY, sx, sy, F_scale, w_pix, dist)
   #print("THETA:",theta)
   #print("DENIS:", sx,sy,new_x,new_y, sx-new_x, sy-new_y)
   return(new_x,new_y)

def make_plate_image(med_stack_all, cam_num, json_conf, show = 1):
   
   nonstars = []
   stars = []
   center_stars = 0
   med_cpy = med_stack_all.copy()
   plate_image = med_stack_all
   if show == 1:
      show_img = cv2.resize(med_stack_all, (0,0),fx=.4, fy=.4)
      cv2.putText(show_img, "Make Plate Image",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      cv2.imshow('pepe', show_img)
      cv2.waitKey(10)
   img_height,img_width = med_stack_all.shape
   max_px = np.max(med_stack_all)
   avg_px = np.mean(med_stack_all)
   print("AVG PX:", avg_px)
   best_thresh = find_best_thresh(med_stack_all, avg_px)
   print("BEST THRESH:", best_thresh)
   if best_thresh < 0:
      best_thresh = 1
   print("BEST THRESH:", best_thresh)

   _, star_thresh = cv2.threshold(med_stack_all, best_thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(star_thresh, None , iterations=4)
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

   plate_image= np.zeros((img_height,img_width),dtype=np.uint8)
   plate_image_4f = np.zeros((img_height,img_width),dtype=np.uint8)
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      cnt_img = med_cpy[y:y+h,x:x+h]
      if True and w < 30 and h < 30:
         (max_px, avg_px,px_diff,max_loc) = eval_cnt(cnt_img)
 
         mx,my = max_loc
         cx = x + mx
         cy = y + my
         mnx,mny,mxx,mxy = bound_cnt(cx,cy,img_width,img_height)

         is_star = star_test(cnt_img)
         #is_star = 1
         cnt_h, cnt_w = cnt_img.shape
         #cv2.putText(cnt_img, str(is_star),  (0,cnt_h-1), cv2.FONT_HERSHEY_SIMPLEX, .2, (255, 255, 255), 1)
         cv2.imshow('pepe', cnt_img)
         cv2.waitKey(1)

         if is_star == 1:
            cx = int(mnx + mxx / 2)
            cy = int(mny + mxy / 2)
            print(cx,cy)

            mnx,mny,mxx,mxy = bound_cnt(cx,cy,img_width,img_height)
            cnt_img = med_cpy[mny:mxy,mnx:mxx]
            cnt_h,cnt_w = cnt_img.shape
            (max_px, avg_px,px_diff,max_loc) = eval_cnt(cnt_img)

            cx = int(x + (w/2))
            cy = int(y + (h/2))

            stars.append((cx,cy,max_px))
            bp_x,bp_y = max_loc
            #cv2.putText(cnt_img, str(is_star),  (0,cnt_h-1), cv2.FONT_HERSHEY_SIMPLEX, .2, (255, 255, 255), 1)
            #cv2.circle(cnt_img, (int(bp_x),int(bp_y)), 5, (255,255,255), 1)
            star_cnt = cnt_img
            ul = cnt_img[0,0] 
            ur = cnt_img[0,cnt_w-1] 
            ll =  cnt_img[cnt_h-1,0] 
            lr = cnt_img[cnt_h-1,cnt_w-1] 
             
            cavg = int((ul + ur + ll + lr) / 4)
            star_cnt = clean_star_bg(cnt_img, cavg+5)
            # limit to center stars only...
            if abs(mny - (img_height/2)) <= (img_height/2)*.5 and abs(mnx - (img_width/2)) <= (img_width/2)*.5:
               print(abs(mny-(img_height/2)))
               print(abs(mnx-(img_width/2)))
               plate_image[mny:mxy,mnx:mxx] = star_cnt  
               plate_image_4f[mny:mxy,mnx:mxx] = star_cnt  
               center_stars = center_stars + 1
            else:
               plate_image_4f[mny:mxy,mnx:mxx] = star_cnt  
         else:
            nonstars.append((cx,cy,0))

   temp = sorted(stars, key=lambda x: x[2], reverse=True) 
   if len(temp) > 30:
      stars = temp[0:29]
          
   cv2.imshow('pepe', plate_image)
   cv2.waitKey(10)

   return(stars,nonstars,plate_image,plate_image_4f)


def find_bright_pixels(med_stack_all, solved_file, cam_num, json_conf):

   show_img = cv2.resize(med_stack_all, (0,0),fx=.4, fy=.4)
   cv2.putText(show_img, "Find Bright Pixels",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(10)
   cams_id = cam_num
   img_height,img_width = med_stack_all.shape
   med_cpy = med_stack_all.copy()
   star_pixels = []
   max_px = np.max(med_stack_all)
   avg_px = np.mean(med_stack_all)
   pdif = max_px - avg_px
   pdif = int(pdif / 20) + avg_px

   best_thresh = find_best_thresh(med_stack_all, pdif)
   _, star_bg = cv2.threshold(med_stack_all, best_thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(star_bg, None , iterations=4)
   #thresh_obj = star_bg
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   show_img = cv2.resize(thresh_obj, (0,0),fx=.4, fy=.4)
   cv2.putText(show_img, "Thresh OBJ",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(10)
   masked_pixels = []
   bg_avg = 0

   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      if True and w < 20 and h < 20:
         cnt_img = med_stack_all[y:y+h,x:x+w]
         cv2.imshow('pepe', cnt_img)
         cv2.waitKey(10)
         (max_px, avg_px,px_diff,max_loc) = eval_cnt(cnt_img)
         mx,my = max_loc
         cx = x + mx
         cy = y + my
         mnx,mny,mxx,mxy = bound_cnt(cx,cy,img_width,img_height)

         cnt_img = med_stack_all[mny:mxy,mnx:mxx]
         cv2.imshow('pepe', cnt_img)
         cv2.waitKey(10)

         cnt_w,cnt_h = cnt_img.shape
         if cnt_w > 0 and cnt_h > 0:
            is_star = star_test(cnt_img)
            is_star = 1
            if is_star >= 0:
               bg_avg = bg_avg + np.mean(cnt_img)
               star_pixels.append((cx,cy))
               cv2.circle(med_cpy, (int(cx),int(cy)), 5, (255,255,255), 1)
            else:
               cv2.rectangle(med_cpy, (cx-5, cy-5), (cx + 5, cy + 5), (255, 0, 0), 1)
         else:
               cv2.rectangle(med_cpy, (cx-15, cy-15), (cx + 15, cy + 15), (255, 0, 0), 1)


   show_img = cv2.resize(med_cpy, (0,0),fx=.4, fy=.4)
   cv2.putText(show_img, "Initial Stars Found",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(10)


   if len(star_pixels) > 0:
      bg_avg = bg_avg / len(star_pixels)
   else:
      bg_avg = 35

   file_exists = Path(solved_file)
   if True:
   #if file_exists.is_file() is False:
      plate_image= med_stack_all 
      plate_image= np.zeros((img_height,img_width),dtype=np.uint8)
      star_sz = 10
      for star in star_pixels:
         sx,sy = star
         mnx,mny,mxx,mxy = bound_cnt(sx,sy,img_width,img_height)
         star_cnt = med_stack_all[mny:mxy,mnx:mxx]
         #star_cnt = clean_star_bg(star_cnt, bg_avg+7)
         plate_image[mny:mxy,mnx:mxx] = star_cnt
         cv2.imshow('pepe', star_cnt)
         cv2.waitKey(10)

   else:
      print("PLATE ALREADY SOLVED HERE! FIX", solved_file)
      plate_file = solved_file.replace("-grind.png", ".jpg")
      plate_image = cv2.imread(plate_file, 0)


   masks = get_masks(cams_id, json_conf, hd = 1)
   print("MASKS:",  masks)
   for mask in masks:
      msx,msy,msw,msh = mask.split(",")
      plate_image[int(msy):int(msy)+int(msh),int(msx):int(msx)+int(msw)] = 0

   plate_image[0:1080,0:200] = 0
   plate_image[0:1080,1720:1920] = 0

   #cv2.imshow('pepe', plate_image)
   #cv2.waitKey(10)

   return(star_pixels, plate_image)


def find_best_thresh(image, start_thresh):
   if len(image.shape) > 2:
      image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
   show_img = cv2.resize(image, (0,0),fx=.4, fy=.4)
   cv2.putText(show_img, "Find Best Thresh",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
#   cv2.imshow('pepe', show_img)
#   cv2.waitKey(10)

   go = 1
   tries = 0
   while go == 1:
      _, star_bg = cv2.threshold(image, start_thresh, 255, cv2.THRESH_BINARY)

      #thresh_obj = cv2.dilate(star_bg, None , iterations=4)
      #star_bg = cv2.convertScaleAbs(star_bg)
      (_, cnts, xx) = cv2.findContours(star_bg.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      if len(cnts) > 70:
         start_thresh = start_thresh + 1
      elif len(cnts) < 3:
         start_thresh = start_thresh - 1
      else:
         go = 0
      if tries > 10:
         go = 0
      tries = tries + 1
      print("THRESH:", start_thresh)
   return(start_thresh)


def star_test(cnt_img):
   PX = []
   PY = []
   ch,cw = cnt_img.shape
   my = int(ch / 2)
   mx = int(cw / 2)
   max_px = np.max(cnt_img)
   avg_px = np.mean(cnt_img[0:])
   px_diff = max_px - avg_px

   for x in range(0,cw-1):
      px_val = cnt_img[my,x]
      PX.append(px_val)
      #cnt_img[my,x] = 255
   for y in range(0,ch-1):
      py_val = cnt_img[y,mx]
      PY.append(py_val)
      #cnt_img[y,mx] = 255

   ys_peaks = signal.find_peaks(PY)
   y_peaks = len(ys_peaks[0])
   xs_peaks = signal.find_peaks(PX)
   x_peaks = len(xs_peaks[0])


   if px_diff > 8 or max_px > 80:
      is_star = 1
      print("STAR PASSED:", px_diff, max_px)
   else:
      print("STAR FAIL:", px_diff, max_px)
      is_star = 0

   return(is_star)


def clean_star_bg(cnt_img, bg_avg):
   max_px = np.max(cnt_img)
   min_px = np.min(cnt_img)
   avg_px = np.mean(cnt_img)
   halfway = int((max_px - min_px) / 2)
   cnt_img.setflags(write=1)
   for x in range(0,cnt_img.shape[1]):
      for y in range(0,cnt_img.shape[0]):
         px_val = cnt_img[y,x]
         if px_val < bg_avg + halfway:
            #cnt_img[y,x] = random.randint(int(bg_avg - 3),int(avg_px))
            pxval = cnt_img[y,x]
            pxval = int(pxval) / 2
            cnt_img[y,x] = 0
   return(cnt_img)

def get_catalog_stars(fov_poly, pos_poly, cal_params,dimension,x_poly,y_poly,min=0):
 
   
   catalog_stars = []
   possible_stars = 0
   img_w = int(cal_params['imagew'])
   img_h = int(cal_params['imageh'])
   RA_center = float(cal_params['ra_center']) 
   dec_center = float(cal_params['dec_center']) 
   F_scale = 3600/float(cal_params['pixscale'])
   fov_w = img_w / F_scale
   fov_h = img_h / F_scale
   fov_radius = np.sqrt((fov_w/2)**2 + (fov_h/2)**2)

   pos_angle_ref = cal_params['position_angle'] 
   x_res = int(cal_params['imagew'])
   y_res = int(cal_params['imageh'])

   #print("USING CALP:", RA_center, dec_center, pos_angle_ref, cal_params['pixscale'], x_res, y_res)

   if img_w < 1920:
      center_x = int(x_res / 2)
      center_y = int(x_res / 2)

   bright_stars_sorted = sorted(bright_stars, key=lambda x: x[4], reverse=False)

   for bname, cname, ra, dec, mag in bright_stars_sorted:
      dcname = cname.decode("utf-8")
      dbname = bname.decode("utf-8")
      if dcname == "":
         name = bname
      else:
         name = cname

      ang_sep = angularSeparation(ra,dec,RA_center,dec_center)
      if ang_sep < fov_radius and float(mag) < 5.5:
         new_cat_x, new_cat_y = distort_xy_new (0,0,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale)

         possible_stars = possible_stars + 1
         catalog_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y))

   return(catalog_stars)

def find_close_stars_fwd(star_point, catalog_stars,match_thresh=5):
   star_ra, star_dec = star_point
   dt = 20
   temp= []
   matches = []
   print("\tFIND CLOSE STARS FWD:", star_ra, star_dec)
   for name,mag,ra,dec,cat_x,cat_y in catalog_stars:
      #print(star_ra,star_dec,name,ra,dec)
      ra, dec= float(ra), float(dec)
      match_dist = abs(angularSeparation(star_ra,star_dec,ra,dec))
      if match_dist < match_thresh:
         #star_dist = abs(ra - star_ra) + abs(dec - star_dec)
         #star_dist = angularSeparation(ra,dec,star_ra,star_dec)
         print("MATCH FOR ", star_ra, star_dec, name, ra, dec,match_dist)
         temp.append((name,mag,ra,dec,cat_x,cat_y,match_dist))

   matches = sorted(temp, key=lambda x: x[6], reverse=False)
   #if len(matches) > 0:

   return(matches[0:1])

def find_close_stars(star_point, catalog_stars,dt=25):

   scx,scy = star_point
   scx,scy = int(scx), int(scy)

   center_dist = calc_dist((scx,scy),(960,540))
   if center_dist > 500:
      dt = 55
   if center_dist > 700:
      dt = 65
   if center_dist > 800:
      dt = 75
   if center_dist > 900:
      dt = 150


   matches = []
   #print("IMAGE STAR:", scx,scy)
   for name,mag,ra,dec,cat_x,cat_y in catalog_stars:
      cat_x, cat_y = int(cat_x), int(cat_y)
      if cat_x - dt < scx < cat_x + dt and cat_y -dt < scy < cat_y + dt:
         #print("\t{:s} at {:d},{:d} is CLOSE to image star {:d},{:d} ".format(name,cat_x,cat_y,scx,scy))
         cat_star_dist= calc_dist((cat_x,cat_y),(scx,scy))
         matches.append((name,mag,ra,dec,cat_x,cat_y,scx,scy,cat_star_dist))


   if len(matches) > 1:
      matches_sorted = sorted(matches, key=lambda x: x[8], reverse=False)
      # check angle back to center from cat star and then angle from cat star to img star and pick the one with the closest match for the star...
      #for match in matches_sorted:
      #print("MULTI MATCH:", scx,scy, matches)
     
      matches = matches_sorted
   #print("<HR>")

   return(matches[0:1])

def radec_to_azel2(ra,dec,lat,lon,alt, caldate):
   y = caldate[0:4]
   m = caldate[4:6]
   d = caldate[6:8]

   #t = caldate[8:14]
   h = caldate[8:10]
   mm = caldate[10:12]
   s = caldate[12:14]
   caldate = y + "/" + m + "/" + d + " " + h + ":" + mm + ":" + s
   print("CAL DATE:", caldate)

   body = ephem.FixedBody()
   print ("BODY: ", ra, dec)
   body._ra = ra
   body._dec = dec
   #body._epoch=ephem.J2000

   obs = ephem.Observer()
   obs.lat = ephem.degrees(lat)
   obs.lon = ephem.degrees(lon)
   obs.date = caldate
   print ("CALDATE:", caldate)
   obs.elevation=float(alt)
   body.compute(obs)
   az = str(body.az)
   el = str(body.alt)
   (d,m,s) = az.split(":")
   dd = float(d) + float(m)/60 + float(s)/(60*60)
   az = dd

   (d,m,s) = el.split(":")
   dd = float(d) + float(m)/60 + float(s)/(60*60)
   el = dd
   #az = ephem.degrees(body.az)
   return(az,el)

def get_active_cal_file(input_file):
   if "png" in input_file:
      input_file = input_file.replace(".png", ".mp4")
   if "json" in input_file:
      input_file = input_file.replace(".json", ".mp4")
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(input_file)

   # find all cal files from his cam for the same night
   matches = find_matching_cal_files(cam_id, f_datetime)
   if len(matches) > 0:
      return(matches)
   else:
      return(None)

def find_matching_cal_files(cam_id, capture_date, cal_dir = None):
   matches = []
   if cal_dir is None:
      all_files = glob.glob("/mnt/ams2/cal/freecal/*")
   else:
      all_files = glob.glob(cal_dir + "/*")

   for file in all_files:
      if cam_id in file :
         el = file.split("/")
         fn = el[-1]
         cal_p_file = file  + "/" + fn + "-stacked-calparams.json"
         if cfe(cal_p_file) == 1:
            matches.append(cal_p_file)
         else:
            cal_p_file = file  + "/" + fn + "-calparams.json"
         if cfe(cal_p_file) == 1:
            matches.append(cal_p_file)


   td_sorted_matches = []

   for match in matches:
      (t_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(match)
      tdiff = abs((capture_date-t_datetime).total_seconds())
      td_sorted_matches.append((match,f_date_str,tdiff))

   temp = sorted(td_sorted_matches, key=lambda x: x[2], reverse=False)

   return(temp)
def define_crop_box(mfd):
   temp = sorted(mfd, key=lambda x: x[2], reverse=False)
   min_x = temp[0][2]
   temp = sorted(mfd, key=lambda x: x[2], reverse=True)
   max_x = temp[0][2]
   temp = sorted(mfd, key=lambda x: x[3], reverse=False)
   min_y = temp[0][3]
   temp = sorted(mfd, key=lambda x: x[3], reverse=True)
   max_y = temp[0][3]
   w = max_x - min_x
   h = max_y - min_y
#   if w > h:
#      h = w
#   else:
#      w = h
#   if w < 100 and h < 100:
#      w = 100
#      h = 100

   if w % 2 != 0:
      w = w + 1
   #sz = int(w/2) + 50

   cx = int(min_x + ((max_x - min_x) / 2))
   cy = int(min_y + ((max_y - min_y) / 2))
   box_min_x = min_x - 50 
   box_min_y = min_y - 50
   box_max_x = max_x + 50
   box_max_y = max_y + 50 
   if box_min_x < 0:
      mox_max_x = box_max_x + abs(box_min_x)
      box_min_x = 0
   if box_min_y < 0:
      mox_max_y = box_max_y + abs(box_min_y)
      box_min_y = 0


   return(box_min_x,box_min_y,box_max_x,box_max_y)

