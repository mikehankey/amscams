import glob
import time
import math
import os
import scipy.optimize
import numpy as np
import datetime, calendar
import cv2
from sklearn import linear_model, datasets
from skimage.measure import ransac, LineModelND, CircleModel

from sklearn.linear_model import RANSACRegressor
from sklearn.datasets import make_regression

from PIL import ImageFont, ImageDraw, Image, ImageChops

from Classes.DisplayFrame import DisplayFrame
from Classes.Detector import Detector
from Classes.Camera import Camera
from Classes.Calibration import Calibration
from lib.PipeAutoCal import gen_cal_hist,update_center_radec, get_catalog_stars, pair_stars, scan_for_stars, calc_dist, minimize_fov, AzEltoRADec , HMS2deg, distort_xy, XYtoRADec, angularSeparation
from lib.PipeUtil import load_json_file, save_json_file, cfe, check_running
from lib.FFFuncs import best_crop_size, ffprobe

import seaborn as sns

class Plotter():
   def __init__(self, cmd=None, extra_args=[]):
      self.cmd = cmd
      self.DATA_DIR = "/mnt/f/"
      print("ARGS:", cmd, extra_args)
      if "ALL" not in extra_args[0] and "SPO" not in extra_args[0] and "SHW" not in extra_args[0] :
         print("Extra Args:", extra_args)
         y,m,d = extra_args[0].split("_")
         self.day = y + "_" + m + "_" + d
         self.date_desc = m + "/" + d + "/" + y
         self.event_dir = self.DATA_DIR + "EVENTS/" + y + "/" + m + "/" + d + "/" 
         #self.all_radiants_png_file = self.event_dir + self.day.replace("_", "") + "_RADIANTS.png" 
         self.all_radiants_png_file = self.DATA_DIR + "EVENTS/DAYS/" + self.day.replace("_", "") + "_PLOTS_ALL_RADIANTS.png" 
         self.all_radiants_json_file = self.event_dir + "ALL_RADIANTS.json"
         self.all_radiants = load_json_file(self.all_radiants_json_file)
         self.alpha = .9
         print("FILE", self.all_radiants_json_file)
      else:
         self.day = extra_args[0]
         self.event_dir = self.DATA_DIR + "EVENTS/"
         self.all_radiants_png_file = self.DATA_DIR + "EVENTS/DAYS/" + extra_args[0] + "_RADIANTS.png"
         self.all_radiants_json_file = self.DATA_DIR + "EVENTS/DAYS/" + extra_args[0] + "_RADIANTS.json"
         self.all_radiants = load_json_file(self.all_radiants_json_file)
         self.extra_args = extra_args
         self.date_desc = ""
         if "SPO" in extra_args[0]: 
            self.alpha = .025
         else:
            self.alpha = .75

   def make_shower_colors(self):
      shower_color_file = "shower_colors.json"
      if os.path.exists(shower_color_file) is True:
         self.shower_colors = load_json_file(shower_color_file)
         return()
      sp = open("streamfulldata.csv")
      self.shower_names = []
      self.shower_colors = {}
      for line in sp:
         line = line.replace("\n", "")
         data = line.split("|")
         print(data)
         self.shower_names.append(data[3].upper())
      self.shower_names.append("...")

      palette = sns.color_palette("pastel", len(self.shower_names))
      cx = 0
      for i in palette:
         shower_name = self.shower_names[cx]
         self.shower_colors[shower_name] = i
         cx += 1

      for shower_name in self.shower_colors:
         print(shower_name, self.shower_colors[shower_name])
      save_json_file(shower_color_file, self.shower_colors)


   def plot_all_rad(self):
      self.make_shower_colors()
      import matplotlib
      matplotlib.use('TkAgg')
      import matplotlib.ticker as plticker
      from matplotlib import pyplot as plt
      showers = {}
      #shower_colors = {}
      #shower_names = []
      #for rad in self.all_radiants:
      #   sh = rad['IAU']
         #if sh == "...":
         #   sh = "SPO"


         #if sh not in showers:
         #   showers[sh] = 1
         #   shower_names.append(sh)
         #else:
         #   showers[sh] += 1 

      #palette = sns.color_palette("pastel", len(showers.keys()))
      #cx = 0
      #for i in palette:
      #   shower_name = shower_names[cx]
      #   shower_colors[shower_name] = i
      #   cx += 1
      #for shower_name in shower_colors:
      #   print(shower_name, shower_colors[shower_name])


      fig = plt.figure(figsize=(12,9))
      ax = fig.add_subplot(111, projection="mollweide" )
      geo_ras = []
      geo_decs = []
      ap_ras = []
      ap_decs = []
      hl_ras = []
      hl_decs = []

      plot_data = {
         "t": "Sun Centered geocentric ecliptic coordinates <br> " + self.date_desc ,
         "x": [],
         "y": [],
         "c": [],
         "n": [],
         "p": [],
         "ids": []
      }
      rads_by_day = {}
      mp_colors = []
      labels = []


      for rad in self.all_radiants:

         if rad is None:
            continue
         if rad['geocentric']['ra_g'] is None or rad['geocentric']['dec_g'] is None :
            continue

         event_id = rad['event_id']
         day = event_id[0:8]
         mon = event_id[0:6]
         if "ALL" in self.day or "SHW" in self.day or "SPO" in self.day:
            day = self.day 

         if day not in rads_by_day:
            rads_by_day[day] = {
               "t": "Sun Centered geocentric ecliptic coordinates <br> " + self.date_desc ,
               "x": [],
               "y": [],
               "c": [],
               "n": [],
               "p": [],
               "ids": []
            }

         #if "202103" not in rad['event_id'] :
         #   continue
         #if "..." in rad['IAU'] :
         #   continue

         ra = np.radians(np.degrees(rad['geocentric']['ra_g'])-180)
         geo_ras.append(ra)
         geo_decs.append(rad['geocentric']['dec_g']) 
         if "apparent_ECI" in rad:
            ap_ra = np.radians(np.degrees(rad['apparent_ECI']['ra'])-180)
            ap_ras.append(ap_ra)
            ap_decs.append(rad['apparent_ECI']['dec']) 

         # STRANGE BUG NEEDS TO BE FIXED BY GPT
         if "ecliptic_helio" in rad:
            #hl_ra = np.radians(np.degrees(rad['ecliptic_helio']['L_h'])-180)
            hl_ra = np.radians(np.degrees(rad['ecliptic_helio']['L_h']))
            #hl_ra = rad['ecliptic_helio']['L_h']
            # reverse the Y?
            #hl_ra_rev = hl_ra
            hl_ra_rev = -hl_ra
            hl_ras.append(hl_ra_rev)
            hl_decs.append(rad['ecliptic_helio']['B_h'])

            hl_ra_n = np.degrees(rad['ecliptic_helio']['L_h']) 

            # Not sure if this is needed? Some strange things happen 
            # When converting radians to degrees that don't match the RMS
            # SEEMS to only happen to radiants < 180?
            #if hl_ra_n < 180:
            hl_ra_n = 360 - hl_ra_n


            rads_by_day[day]['x'].append((hl_ra_n))
            rads_by_day[day]['y'].append(np.degrees(rad['ecliptic_helio']['B_h']) *-1)

            if rad['IAU'] in self.shower_colors:
               r, g, b = self.shower_colors[rad['IAU']]
               alph = .7
            else:
               r, g, b, = .5,.5,.5
               alph = .2
            rgb_val = (r , g, b)
            mp_colors.append(rgb_val)
            labels.append(rad['IAU'])
            color_str = str(int(255*r)) + "," + str(int(255*g)) + "," + str(int(255*b)) + "," + str(alph)
            rads_by_day[day]['c'].append("rgba(" + color_str + ")")
            #rads_by_day[day]['c'].append("rgba(255,255,255,1)")

            rads_by_day[day]['n'].append(rad['IAU'] + " " + rad['event_id'])
            rads_by_day[day]['p'].append("top center")
            rads_by_day[day]['ids'].append(rad['event_id'])

            print("RAD:", rad['IAU'], rad['ecliptic_helio']['L_h'], rad['ecliptic_helio']['B_h'], np.degrees(rad['ecliptic_helio']['L_h']), np.degrees(rad['ecliptic_helio']['B_h']), hl_ra_n)


      mp_colors = tuple(mp_colors)
      ax.scatter(geo_ras, geo_decs, marker='.' , c=mp_colors, alpha=self.alpha )
      ax.set_xticklabels(['14h','16h','18h','20h','22h','0h','2h','4h','6h','8h','10h'])
      ax.grid(True)
      #plt.savefig(self.DATA_DIR  + "EVENTS/DAYS/" + self.day.replace("_", "") + "_PLOTS_ALL_RADIANTS.png" )
      plt.title("Radiants on " + self.day)
      plt.savefig(self.all_radiants_png_file )

      print("SAVED:", self.all_radiants_png_file)
      print("SAVED:", self.all_radiants_json_file)
      fig.clear()
      #save_json_file("/mnt/ams2/EVENTS/PLOTS_ALL_RADIANTS.json", plot_data)
      #cmd = "cp /mnt/ams2/EVENTS/PLOTS_ALL_RADIANTS.json /mnt/archive.allsky.tv/EVENTS/PLOTS_ALL_RADIANTS.json"
      #os.system(cmd)

      print("RADS BY DAY DAYS:", len(rads_by_day))
      #if len(rads_by_day) > 1:
      #   exit()

      for day in rads_by_day:
         if "ALL" in self.day or "SHW" in self.day or "SPO" in self.day:
            save_file = self.DATA_DIR + "EVENTS/DAYS/" + day + "_PLOTS_ALL_RADIANTS.json"
         else:
            save_file = self.DATA_DIR + "EVENTS/DAYS/" + day + "_PLOTS_ALL_RADIANTS.json"
         cloud_file = save_file.replace(self.DATA_DIR, "/mnt/archive.allsky.tv/")
         save_json_file(save_file, rads_by_day[day])
         save_file2 = save_file.replace(".json", ".png" )
         cloud_file2 = cloud_file.replace(".json", ".png" )
         print("cp " + save_file + " " + cloud_file)
         print("cp " + save_file2 + " " + cloud_file2)
         os.system("cp " + save_file + " " + cloud_file)
         os.system("cp " + save_file2 + " " + cloud_file2)

      print("DONE")
      #fig = plt.figure(figsize=(12,9))
      #ax = fig.add_subplot(111, projection="mollweide")
      #ax.scatter(ap_ras, ap_decs, marker='+', color='red')
      #plt.savefig("/mnt/ams2/test3.png")
      #fig.clear()

      #fig = plt.figure(figsize=(12,9))
      #ax = fig.add_subplot(111, projection="mollweide" )
      #tick_labels = np.array([60, 30, 0, 330, 300, 270, 240, 210,180,150,120,90])

      #ax.set_xticklabels(tick_labels)
      #ax.scatter(hl_ras, hl_decs, marker='+', color='red')
      #ax.grid(True)
      #title = "Sun-centererd geocentric ecliptic coordinates"
      #suptitle = "Jan 1, 2021 - Apr 9, 2021 \n" + str(len(hl_ras)) + " meteors"
      #plt.title(title)
      #plt.suptitle(suptitle, y=.2)
      #plt.savefig("/mnt/ams2/test4.png")
      #$fig.clear()


   def controller(self):
      if self.cmd == "" or self.cmd == "help":
         print("Need help?")
         print("python3 PLT.py all_rad")
      if self.cmd == "all_rad":
         self.plot_all_rad() 


   def get_catalog_stars(self, cal_params=None):
      import lib.brightstardata as bsd
      mybsd = bsd.brightstardata()
      bright_stars = mybsd.bright_stars

      if cal_params is None:
         cal_params = {}
         cal_params['imagew'] = 1920
         cal_params['imageh'] = 1080
         cal_params['ra_center'] = 0
         cal_params['dec_center'] = 0
         cal_params['pixscale'] = 1000 
         cal_params['position_angle'] = 0


      catalog_stars = []

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
      fov_w = cal_params['imagew'] / F_scale
      fov_h = cal_params['imageh'] / F_scale
      fov_radius = np.sqrt((fov_w/2)**2 + (fov_h/2)**2)

      pos_angle_ref = cal_params['position_angle']
      x_res = int(cal_params['imagew'])
      y_res = int(cal_params['imageh'])


      if cal_params['imagew'] < 1920:
         center_x = int(x_res / 2)
         center_y = int(y_res / 2)

      bright_stars_sorted = sorted(bright_stars, key=lambda x: x[4], reverse=False)

      sbs = []
      for data in bright_stars_sorted:
         if len(data) == 5:
            bname, cname, ra, dec, mag = data
         elif len(data) == 6:
            bname, mag, ra, dec, cat_x, cat_y = data
            cname = bname
         elif len(data) == 17:
            iname,mag,ra,dec,img_ra,img_dec,match_dist,cat_x,cat_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist,star_int  = data
            bname = iname
            cname = iname
         else:
            print("BAD DATA:", len(data))
            print("BAD DATA:", data)
            exit()

         try:
            dcname = cname.decode("utf-8")
            dbname = bname.decode("utf-8")
         except:
            dcname = cname
            dbname = bname

         if dcname == "":
            name = bname
         else:
            name = cname

         ang_sep = angularSeparation(ra,dec,RA_center,dec_center)
         if ang_sep < fov_radius and float(mag) < 7:
            sbs.append((bname, cname, ra, dec, mag))
            new_cat_x, new_cat_y = distort_xy(0,0,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale)

            catalog_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y))

      if len(catalog_stars) == 0:
         print("NO CATALOG STARS!?")

      return(catalog_stars)

if __name__ == "__main__":
   import sys
   extra_args = []
   if len(sys.argv[1]) > 2:
      for arg in sys.argv[1:]:
         extra_args.append(arg)

   PLT = Plotter(cmd=sys.argv[1], extra_args=extra_args)
   PLT.controller()
