#!/usr/bin/python3

import time
import datetime
import cv2
import os
import sys
from lib.FileIO import load_json_file, save_json_file, cfe
from lib.UtilLib import check_running
from lib.CalibLib import save_cal_params



def plate_solve(cal_file,json_conf):

   el = cal_file.split("/")
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
# --crpix-center
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

   save_cal_params(wcs_file)

   if cfe(grid_file) == 1:
      tmp_img = cv2.imread(grid_file)
      tmp_img_tn = cv2.resize(tmp_img, (0,0),fx=.5, fy=.5)
      grid_file_half = grid_file.replace(".png", "-half.png")
      cv2.imwrite(grid_file_half, tmp_img_tn)



json_conf = load_json_file("../conf/as6.json")

cal_img_file = sys.argv[1]

plate_solve(cal_img_file, json_conf)
