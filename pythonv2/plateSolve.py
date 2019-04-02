#!/usr/bin/python3

import numpy as np
import time
import datetime
import cv2
import os
import sys
from lib.FileIO import load_json_file, save_json_file, cfe
from lib.UtilLib import check_running, angularSeparation, convert_filename_to_date_cam
from lib.CalibLib import save_cal_params, radec_to_azel, get_catalog_stars, find_close_stars, XYtoRADec
from lib.DetectLib import eval_cnt



def plate_solve(cal_file,json_conf):
   el = cal_file.split("/")
   fn = el[-1]
   cal_date = fn[0:19]

   running = check_running("solve-field")
   if running > 0:
      exit()

   h_cal_file = cal_file.replace("-stacked.jpg", "-half-stack.png")
   print(cal_file)
   cal_img = cv2.imread(cal_file)
   sh = cal_img.shape
   cih,ciw = sh[0], sh[1]
   print("SIZE:", cih, ciw)
   if ciw == 1408 and cih == 1152:
      cal_img = cv2.resize(cal_img, (704,396))
      cal_file = cal_file.replace(".png", "p.png")
      cv2.imwrite(cal_file, cal_img)
      


   wcs_file = cal_file.replace(".jpg", ".wcs")
   solved_file = cal_file.replace(".jpg", ".solved")
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

   if cfe(solved_file) == 0:
      cmd = "/usr/local/astrometry/bin/solve-field " + cal_file + " --crpix-center --cpulimit=30 --verbose --no-delete-temp --overwrite --width=" + str(width) + " --height=" + str(height) + " -d 1-40 --scale-units dw --scale-low 50 --scale-high 90 -S " + solved_file + " > " + astr_out + " 2>&1 &"
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
      print(cmd)
      os.system(cmd)

      cmd = "/usr/local/astrometry/bin/wcsinfo " + wcs_file + " > " + wcs_info_file 
      print(cmd)
      os.system(cmd)

   base_file = solved_file.replace(".solved", "")

   if cfe(grid_file) == 1:
      tmp_img = cv2.imread(grid_file)
      tmp_img_tn = cv2.resize(tmp_img, (0,0),fx=.5, fy=.5)
      grid_file_half = grid_file.replace(".png", "-half.png")
      cv2.imwrite(grid_file_half, tmp_img_tn)
      save_cal_params(wcs_file)
      cal_params_file = wcs_file.replace(".wcs", "-calparams.json")
      cal_params = load_json_file(cal_params_file)

      ra = cal_params['ra_center']
      dec = cal_params['dec_center']
      lat = json_conf['site']['device_lat'] 
      lon = json_conf['site']['device_lng'] 
      alt = json_conf['site']['device_alt'] 

      print("CAL DATE:", cal_date)
      (y,m,d,h,mm,s) = cal_date.split("_")
      new_date = y + "/" + m + "/" + d + " " + h + ":" + mm + ":" + s
      az, el = radec_to_azel(ra,dec, new_date,json_conf)

      cal_params['center_az'] = az
      cal_params['center_el'] = el
      cal_params = default_cal_params(cal_params, json_conf)
      save_json_file(cal_params_file, cal_params)

      star_matches = pair_stars(cal_params, cal_params_file, json_conf)
      print(cal_params_file)



      wild = base_file + ".txt"
      os.system("rm " + wild)
      wild = base_file + ".axy"
      os.system("rm " + wild)
      wild = base_file + ".corr"
      os.system("rm " + wild)
      wild = base_file + ".match"
      os.system("rm " + wild)
      wild = base_file + ".new"
      os.system("rm " + wild)
      wild = base_file + ".rdls"
      os.system("rm " + wild)
      wild = base_file + ".xyls"
      os.system("rm " + wild)
      wild = base_file + "-astrometry-output.txt"
      os.system("rm " + wild)

      os.system("rm " + wild)
      wild = base_file + "-stars.txt"
      os.system("rm " + wild)
      wild = base_file + "-wcsinfo.txt"
   else:
      #cal failed
      wild = base_file + ".txt"
      os.system("rm " + wild)
      wild = base_file + ".axy"
      os.system("rm " + wild)
      wild = base_file + ".corr"
      os.system("rm " + wild)
      wild = base_file + ".match"
      os.system("rm " + wild)
      wild = base_file + ".new"
      os.system("rm " + wild)
      wild = base_file + ".rdls"
      os.system("rm " + wild)
      wild = base_file + ".xyls"
      os.system("rm " + wild)
      wild = base_file + "-astrometry-output.txt"
      os.system("rm " + wild)
      wild = base_file + "-objs.png"
      os.system("rm " + wild)
      wild = base_file + "-stars.txt"
      os.system("rm " + wild)
      wild = base_file + "-wcsinfo.txt"
      os.system("rm " + wild)
      wild = base_file + ".failed"
      os.system("touch " + wild)

def default_cal_params(cal_params,json_conf):
   if 'fov_poly' not in cal_params:
      fov_poly = [0,0]
      cal_params['fov_poly'] = fov_poly
   if 'pos_poly' not in cal_params:
      pos_poly = [0]
      cal_params['pos_poly'] = pos_poly
   if 'x_poly' not in cal_params:
      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly'] = x_poly.tolist()
   if 'y_poly' not in cal_params:
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly'] = x_poly.tolist()
   if 'x_poly_fwd' not in cal_params:
      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly_fwd'] = x_poly.tolist()
   if 'y_poly_fwd' not in cal_params:
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly_fwd'] = x_poly.tolist()

   return(cal_params)

def pair_stars(cal_params, cal_params_file, json_conf):

   img_file = cal_params_file.replace("-calparams.json", ".png")
   print("IMG:", img_file)
   cal_img = cv2.imread(img_file, 0)
   ih, iw= cal_img.shape
   ra_center = cal_params['ra_center']
   dec_center = cal_params['dec_center']
   center_az = cal_params['center_az']
   center_el = cal_params['center_el']
   star_matches = []
   my_close_stars = []
   total_match_dist = 0
   total_cat_dist = 0
   total_matches = 0

   cat_stars = get_catalog_stars(cal_params['fov_poly'], cal_params['pos_poly'], cal_params,"x",cal_params['x_poly'],cal_params['y_poly'],min=0)
   user_star_file = cal_params_file.replace("-calparams.json", "-user-stars.json")
   user_stars = load_json_file(user_star_file)
   new_user_stars = []
   for x,y in user_stars['user_stars']:
      #cv2.rectangle(cal_img, (x-4, y-4), (x+ 4, y+ 4), (128, 128, 128), 1)
      y1 = y - 15
      y2 = y + 15
      x1 = x - 15
      x2 = x + 15
      if (x-10 > 0 and y-10 > 0) and (x+10 < iw-1 and y+10 < ih-1):
         print("STAR:", y1,y2,x1,x2)
         cnt_img = cal_img[y1:y2,x1:x2]
         max_px, avg_px, px_diff,max_loc = eval_cnt(cnt_img)
         mx,my = max_loc
         # maybe bug here?
         pp_x = (x + int(max_loc[0]) -10)
         pp_y = (y + int(max_loc[1]) -10)
         print("PP:", x, pp_x, y, pp_y)
         #pp_x = (x + int(max_loc[0]) )
         #pp_y = (y + int(max_loc[1]) )
         cv2.circle(cal_img,(pp_x,pp_y), 7, (128,128,128), 1)
      new_user_stars.append((pp_x,pp_y))

   user_stars['user_stars'] = new_user_stars   


   for ix,iy in user_stars['user_stars']:
      close_stars = find_close_stars((ix,iy), cat_stars)
      for name,mag,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist in close_stars:
         dcname = str(name.decode("utf-8"))
         dbname = dcname.encode("utf-8")
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(ix,iy,cal_params_file,cal_params,json_conf)
         match_dist = abs(angularSeparation(ra,dec,img_ra,img_dec))
         my_close_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist))
         total_match_dist = total_match_dist + match_dist
         total_cat_dist = total_cat_dist + cat_dist
         total_matches = total_matches + 1
         #cv2.rectangle(cal_img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
         #cv2.rectangle(cal_img, (six-2, siy-2), (six+ 2, siy+ 2), (255, 255, 255), 1)
         #cv2.circle(cal_img,(six,siy), 7, (128,128,128), 1)



   cal_params['close_stars'] = my_close_stars
   cal_params['total_res_deg'] = total_match_dist / total_matches
   cal_params['total_res_px'] = total_cat_dist / total_matches
   cal_params['cal_params_file'] = cal_params_file
   save_json_file(cal_params_file, cal_params)

   #cv2.imshow('pepe', cal_img)
   #cv2.waitKey(0)
   fit_on = 0
   if fit_on == 1:
      os.system("./fitPairs.py " + cal_params_file)

   return(star_matches)

json_conf = load_json_file("../conf/as6.json")

cal_img_file = sys.argv[1]

#cv2.namedWindow('pepe')
plate_solve(cal_img_file, json_conf)
