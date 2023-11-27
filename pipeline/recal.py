#!/usr/bin/python3
ASOS = """
   _____  .____    .____       _____________  __._____.___.
  /  _  \ |    |   |    |     /   _____/    |/ _|\__  |   |
 /  /_\  \|    |   |    |     \_____  \|      <   /   |   |
/    |    \    |___|    |___  /        \    |  \  \____   |
\____|__  /_______ \_______ \/_______  /____|__ \ / ______|
        \/        \/       \/        \/        \/ \/
  -- O  B  S  E  R  V  I  N  G   S  O  F  T  W  A  R  E --

ALL SKY INC IS A UNIT OF MIKE HANKEY LLC - ALL RIGHTS RESERVED
Use permitted under community license for registered users only
                     © 2018 - 2023
"""

from lib.PipeVideo import load_frames_simple
import math

import datetime
from PIL import ImageFont, ImageDraw, Image, ImageChops
import imutils
import time
import json
import numpy as np
import glob
import cv2
import os, sys, select
import requests
from photutils import CircularAperture, CircularAnnulus
from photutils.aperture import aperture_photometry
import scipy.optimize
from PIL import ImageFont, ImageDraw, Image, ImageChops
import lib.brightstardata as bsd
from lib.PipeUtil import load_json_file, save_json_file,angularSeparation, calc_dist, convert_filename_to_date_cam , check_running , get_file_info, collinear, mfd_roi, load_mask_imgs
from lib.PipeAutoCal import distort_xy, insert_calib, minimize_poly_multi_star, view_calib, cat_star_report , update_center_radec, XYtoRADec, draw_star_image, make_lens_model, make_az_grid, make_cal_summary, make_cal_plots, find_stars_with_grid, optimize_matchs, eval_cal_res, radec_to_azel, make_plate_image, make_cal_plots, make_cal_summary, custom_fit_meteor, make_plate_image, save_cal_params, test_fix_pa

from FlaskLib.api_funcs import show_cat_stars 
from lib.PipeTrans import slide_left


import sqlite3 
from lib.DEFAULTS import *
from Classes.MovieMaker import MovieMaker 
from Classes.Stations import Stations 
from Classes.RenderFrames import RenderFrames
from Classes.VideoEffects import VideoEffects
from prettytable import PrettyTable as pt
SAVE_MOVIE = False 
MOVIE_LAST_FRAME = None 
MOVIE_FRAME_NUMBER = 0
MOVIE_FRAMES_TEMP_FOLDER = "/home/ams/MOVIE_FRAMES_TEMP_FOLDER/"

def retry_astrometry(cam_id, limit=25):
    source_dir = "/mnt/ams2/cal/extracal"
    # scan source dir for subdirs, then each of those for stacked pngs. Copy those to the
    # autocal dir
    calib_in_dir = "/mnt/ams2/meteor_archive/" + station_id + "/CAL/AUTOCAL/" 
    files = sorted(os.listdir(source_dir), reverse=True)
    l = 0
    #    _, thresh_block = cv2.threshold(block, threshold_value, 255, cv2.THRESH_BINARY)
    show = False
    for f in files:
        subdir = source_dir + "/" + f
        if os.path.isdir(subdir) is True:
            subfiles = os.listdir(subdir)
            for ff in subfiles:
                if "stacked.png" in ff and cam_id in ff:
                    used_img = np.zeros((1080,1920),dtype=np.uint8)
                    el = ff.split("_")
                    year = el[0]
                    cp_cmd = "cp " + subdir + "/" + ff + " " + calib_in_dir + year + "/"
                    print(cp_cmd)

                    image_path = subdir + "/" + ff
                    thresh_image, image, sub,inv = rowwise_adaptive_threshold(image_path, in_image=None, block_ratio=0.01, threshold_factor=1.50)
        
                    show_img = image.copy()

                    thresh_val = 40
                    _, sub_thresh = cv2.threshold(sub, thresh_val, 255, cv2.THRESH_BINARY)
                    contours, _ = cv2.findContours(sub_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                    img_stars = []


                    cnts = []
                    # largest first
                    cnts = sorted(cnts, key=lambda x: (x[2] + x[3]), reverse=True) 
                    for contour in contours:
                        xx, yy, ww, hh= cv2.boundingRect(contour)
                        cnts.append((xx,yy,ww,hh))

                    for cnt in cnts:
                        xx, yy, ww, hh= cnt
                        cx = xx + ww / 2
                        cy = yy + hh / 2
                        if ww > hh:
                            radius = ww + 1
                        else:
                            radius = hh + 1
                        intensity = np.sum(sub[yy:yy+hh,xx:xx+ww])
                        img_stars.append((cx,cy,radius,intensity))
                        uv = used_img[int(cy),int(cx)]
                        if uv == 0 and intensity > 100 : 
                            #print("KEEP STAR:", uv, cx,cy,radius,intensity)
                            cv2.circle(show_img, (int(cx),int(cy)), 10, (255,255,0),2)
                        #else:
                            #print("SKIP STAR:", uv, cx,cy,radius,intensity)
                        y1 = yy - 10 
                        y2 = yy + 10 + hh
                        x1 = xx - 10
                        x2 = xx + 10 + ww
                        used_img[y1:y2,x1:x2] = 255
                    if show == True:
                        cv2.imshow('Image', show_img)
                        cv2.waitKey(100)
                        cv2.imshow('Sub Thresh', sub_thresh)
                        cv2.waitKey(100)
                        cv2.imshow('Thresh', thresh_image)
                        cv2.waitKey(100)
                        # cv2.imshow('pepe4', inv)
                        cv2.waitKey(30)
                    l = l + 1 
                    if l >= limit:
                        print("End limit")
                        exit()


def rowwise_adaptive_threshold(image_path, in_image=None, block_ratio=0.1, threshold_factor=1.15):
    """
    Applies row-wise adaptive thresholding based on the average brightness of each block.

    Args:
    - image_path (str): Path to the input image or image.
    - block_ratio (float): Ratio of image height for each block.
    - threshold_factor (float): Factor to multiply with average brightness to get threshold.

    Returns:
    - numpy.ndarray: Thresholded image.
    - numpy.ndarray: Original image.
    """
    # Read the image
    if type(image_path) == str and in_image is None:
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    elif in_image is not None:
        image = in_image
    else:
        # if the image path is actually an image we can use that too
        image = image_path

    show_img = image.copy()
    bad_areas = []
    blurred = cv2.GaussianBlur(image, (3, 3), 0)
    original_image = image.copy()
    height, width = image.shape

    # Calculate block height
    block_height = int(height * block_ratio)
    # Initialize an empty image for the final thresholded result
    thresholded_image = np.zeros_like(blurred)

    # Loop through the image block by block
    for i in range(0, height, block_height):
        # Extract the block
        block = image[i:i+block_height, :]
        # Calculate the average brightness of the block
        avg_brightness = np.mean(block)
        # Compute the threshold for the block
        threshold_value = avg_brightness * threshold_factor
        # Apply the threshold to the block
        _, thresh_block = cv2.threshold(block, threshold_value, 255, cv2.THRESH_BINARY)
        # Remove large contours from the thresh since these won't be stars!
        dilated_image = cv2.dilate(thresh_block, None, iterations=2)
        contours, _ = cv2.findContours(dilated_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for contour in contours:
            xx, yy, ww, hh= cv2.boundingRect(contour)
            # black out areas taht are too big
            if 25 < ww < 300 or 25 < hh< 300 or yy <= 0 or xx <= 0 or yy>=1075 or xx >= 1915:
                thresh_block[yy:yy+hh,xx:xx+ww] = 0


        # Assign the thresholded block to the final image
        thresholded_image[i:i+block_height, :] = thresh_block

    inverted_image = 255 - thresholded_image
    # the function should end here and a new function for finding stars should be made
    sub = cv2.subtract(image,inverted_image)
    

    return(thresholded_image, image,sub,inverted_image)

def fix_lens_nans():
    files = glob.glob("/mnt/ams2/cal/*poly*")
    poly_checks = ['x_poly', 'y_poly', 'x_poly_fwd', 'y_poly_fwd']
    for f in files:
        el = f.split("/")[-1].split("-")
        cam_id = el[-1].split(".")[0]
        need_to_save = False
        cp = load_json_file(f)
        for p in poly_checks:
            for c in range(0,len(cp['x_poly'])):
                if math.isnan(cp[p][c]) is True:
                    print(" FIXNAN",cam_id, p, cp[p][c])
                    cp[p][c] = 0
                    need_to_save = True
                else:
                    print(" GOOD", cam_id, p, cp[p][c])
        if need_to_save is True:
            save_json_file(f, cp)

def make_intro(folder): 
   global MOVIE_FRAME_NUMBER
   global MOVIE_FRAMES_TEMP_FOLDER
   SAVE_MOVIE = True
   intro_frames = []
   frames = load_frames_simple("intro_video.mp4")
   for fr in frames:
      fr = cv2.resize(fr, (1920,1080))
      if SHOW == 1:
         cv2.imshow('pepe', fr)
         cv2.waitKey(30)

      if SAVE_MOVIE is True:
         save_movie_frame(fr, MOVIE_FRAME_NUMBER, MOVIE_FRAMES_TEMP_FOLDER)
         intro_frames.append(fr)
         MOVIE_FRAME_NUMBER += 1
   return(intro_frames)


def save_movie_frame(frame, frame_number, folder, repeat = None, fade_last=None):
   global MOVIE_FRAME_NUMBER
   global MOVIE_LAST_FRAME 
   file_name = folder + '{0:06d}'.format(frame_number) + ".jpg"

   if fade_last == None:
      cv2.imwrite(file_name, frame  )
   else:
      # fade into the last frame over X frames
      for i in range(0,fade_last):
         perc = i / fade_last
         rperc = 1 - perc
         print("SH", MOVIE_LAST_FRAME.shape)
         print("SH2", MOVIE_LAST_FRAME[0,0])
         blend = cv2.addWeighted(MOVIE_LAST_FRAME, rperc, frame, perc, .3)
         file_name = folder + '{0:06d}'.format(MOVIE_FRAME_NUMBER) + ".jpg"
         cv2.imwrite(file_name, blend )
         print("FADE", MOVIE_FRAME_NUMBER, rperc, perc)
         if SHOW == 1:
            cv2.imshow("pepe", blend)
            cv2.waitKey(30)
         MOVIE_FRAME_NUMBER += 1


   if repeat is not None:
      for i in range(0,repeat):
         file_name = folder + '{0:06d}'.format(MOVIE_FRAME_NUMBER) + ".jpg"
         cv2.imwrite(file_name, frame )
         MOVIE_FRAME_NUMBER += 1
   MOVIE_LAST_FRAME = frame

def rescue_cal(cam_id, con, cur, json_conf):
   # reset and rescue a calibration -- for when things get corrupted or go wrong
   # copy original calib images to the cal dir and restart the astrometry process
   # only do this for 2 images per month max
   cal_file_dict = {}
   station_id = json_conf['site']['ams_id']
   auto_cal_dir = "/mnt/ams2/meteor_archive/" + station_id + "/CAL/AUTOCAL/"
   free_cal_dir = "/mnt/ams2/cal/freecal/"
   dirs = []
   print("AUTO", auto_cal_dir) 
   contents = os.listdir(auto_cal_dir)
   all_extra_cals = os.listdir("/mnt/ams2/cal/extracal/")
   all_free_cals = os.listdir("/mnt/ams2/cal/freecal/")
   extra_cals = []
   free_cals = []
   for x in all_extra_cals:
      if cam_id in x:
         year_mon = x[0:7]
         if year_mon not in cal_file_dict:
            cal_file_dict[year_mon] = {}
            cal_file_dict[year_mon]['extra_cals'] = []
            cal_file_dict[year_mon]['free_cals'] = []
            cal_file_dict[year_mon]['src_cals'] = []
         cal_file_dict[year_mon]['extra_cals'].append(x)

   for x in all_free_cals:
      if cam_id in x and os.path.isdir(free_cal_dir + x) is True:
         free_cals.append(x)
         year_mon = x[0:7]
         if year_mon not in cal_file_dict:
            cal_file_dict[year_mon] = {}
            cal_file_dict[year_mon]['extra_cals'] = []
            cal_file_dict[year_mon]['free_cals'] = []
            cal_file_dict[year_mon]['src_cals'] = []
         cal_file_dict[year_mon]['free_cals'].append(x)




   for d in contents:
      if "20" in d and os.path.isdir(auto_cal_dir + d) is True:
         sdir = auto_cal_dir + d + "/solved" 
         if os.path.isdir(sdir) is True:
            dirs.append(d)
            sfiles = os.listdir(sdir)
            for x in sfiles:
               if cam_id not in x:
                  continue
               if "png" not in x:
                  continue
               if cam_id in x and ".png" in x:
                  year_mon = x[0:7]
                  if year_mon not in cal_file_dict:
                     cal_file_dict[year_mon] = {}
                     cal_file_dict[year_mon]['extra_cals'] = []
                     cal_file_dict[year_mon]['free_cals'] = []
                     cal_file_dict[year_mon]['src_cals'] = []
                  cal_file_dict[year_mon]['src_cals'].append(x)


   tb = pt()
   tb.field_names = ["Year/Month", "Free Cals","Src Cals", "Extra Cals"]

   for year_mon in sorted(cal_file_dict,reverse=True):
      tb.add_row([year_mon, len(cal_file_dict[year_mon]['free_cals']), len(cal_file_dict[year_mon]['src_cals']), len(cal_file_dict[year_mon]['extra_cals'])])
   print(tb)

def remote_menu(con,cur):
   ST = Stations()
   ST.load_station_data()
   stations = []
   cams = []
   local_stations_root = "/mnt/f/EVENTS/STATIONS/"
   cloud_root = "/mnt/archive.allsky.tv/"
   for key in ST.photo_credits:
      stations.append(key)
   options = {}
   data_values = []
   data_headings = ["Date", "Az", "El", "Pos", "Px", "Stars", "Res"]
   c_widths = [12, 6, 6, 6, 6, 6, 6]

   layout = [
         [sg.Text('ALLSKY7 NETWORK CALIBRATION MENU', size =(25, 1))],
         [sg.Text("Select Station: ",size=(15,1)),
                sg.Combo(stations,key="station_id",default_value="Station ID",size=(10,1))],
         [sg.Text("Select Camera: ",size=(15,1)),
                sg.Combo(cams,key="cam_id",default_value="Cam ID",size=(10,1))],
         [sg.Button('Select / Update', key='_station_selected_')],
         [sg.Table(values=data_values, headings=data_headings, col_widths=c_widths, auto_size_columns = False, num_rows=7,key='_filestable_')],
         [sg.Button('Select Cal File', key='_rows_selected_')]
         ]

   window = sg.Window("ALLSKY7 NETWORK CALIBRATION", layout, size=(1280,720))
   refresh_hist = False
   if True:
      # Create an event loop
      last_station = None
      last_cam = None
      while True:
         event, values = window.read()
         if event == "_rows_selected_":
            print(event, values)
         if event == "_station_selected_":
            selected_id = values['station_id']
            if selected_id != last_station:
               last_station = selected_id

               cal_dir = local_stations_root + selected_id + "/CAL/"
               cloud_cal_dir = cloud_root + selected_id + "/CAL/"
               local_cal_dir = local_stations_root + selected_id + "/CAL/"

               cloud_hist_file = cloud_cal_dir + selected_id + "_" + "cal_history.json"
               local_hist_file = local_cal_dir + selected_id + "_" + "cal_history.json"
               # copy cloud hist file to local if needed
               if os.path.exists(cloud_hist_file) is True and os.path.exists(local_hist_file) is False or refresh_hist is True:
                  if os.path.exists(local_cal_dir) is False:
                     os.makedirs(local_cal_dir)
                  os.system("cp " + cloud_hist_file + " " + local_hist_file)
               else:
                  print("REMOTE COPY FAILED", cloud_hist_file, local_hist_file, refresh_hist)

               # open hist file and list all cams for station in the table or select box?
               cal_hist_data = load_json_file(local_hist_file)
               for key in sorted(cal_hist_data.keys()):
                  print(key)
                  cams.append(key)


               window['cam_id'].update(values = cams)
               print(values)
            selected_cam_id = values['cam_id']
            print("STATION/CAM : ", selected_id, selected_cam_id)
            if selected_cam_id in cal_hist_data and last_cam != selected_cam_id:
               for n in range(0,len(cal_hist_data[selected_cam_id]['cal_files'])):
                  i = len(cal_hist_data[selected_cam_id]['cal_files']) - n - 1
                  cfn = cal_hist_data[selected_cam_id]['cal_files'][i].split("/")[-1]
                  date = cal_hist_data[selected_cam_id]['dates'][i]
                  az = round(cal_hist_data[selected_cam_id]['azs'][i],2)
                  el = round(cal_hist_data[selected_cam_id]['els'][i],2)
                  pos = round(cal_hist_data[selected_cam_id]['pos'][i],2)
                  px = round(float(cal_hist_data[selected_cam_id]['pxs'][i]),2)
                  res = round(cal_hist_data[selected_cam_id]['res'][i],2)
                  data_headings = ["Date", "Az", "El", "Pos", "Px", "Stars", "Res"]
                  data_values.append([date,az,el,pos,px,0,res])
                   
               window['_filestable_'].update(data_values )
               #window['_filestable_'].AutoSizeColumns = True
               last_cam = selected_cam_id
         # End program if user closes window or
         # presses the OK button

         if event == "OK" or event == sg.WIN_CLOSED:
            options['station'] = values['station']

            #save_json_file(self.opt_file, self.options)
            break

      window.close()


def remote_cal(cal_file, con, cur):
   # cal file should be a png with the full path?
   from Classes.AllSkyNetwork import AllSkyNetwork
   ASN = AllSkyNetwork()
   ASN.load_stations_file()

   print("cal file", cal_file)
   # determine if this is a remote file or local file
   if "AMS" in cal_file:
      cal_fn = cal_file.split("/")[-1]
      cal_id = cal_fn.replace(".png", "")
      cal_id = cal_id.replace("-stacked", "")
      st_id = cal_fn.split("_")[0]
      station_id = st_id
      cal_fn = cal_fn.replace(st_id + "_", "")
      cal_params = None
      print("\n\nCAL FN:", st_id, cal_fn)
      (meteor_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)
      cam_id = cam
      station_dir = "/mnt/f/EVENTS/STATIONS/" + st_id 
      freecal_dir = station_dir + "/CAL/FREECAL/"
      cal_dir = station_dir + "/CAL/FREECAL/"
      if os.path.exists(freecal_dir) is False:
         os.makedirs(freecal_dir)
      if "-" in cal_fn:
         cal_root = cal_fn.split("-")[0]
      else:
         cal_root = cal_fn.split(".")[0]
     
      local_cal_file = freecal_dir + cal_root + ".png"
      local_json_file = freecal_dir + cal_root + ".json"
      ST = Stations()
      ST.load_station_data()

      if os.path.exists(local_json_file) is False:
         cmd = "cp " + cal_file + " " + local_json_file
         print(cmd)
         os.system(cmd)

      # is remote
      # load station data
      # create handles for the network calibration db

      default_cal_params, remote_json_conf = ASN.get_remote_cal(st_id, cam_id, cal_fn)
      if st_id in ST.rurls:
         remote_png_url = ST.rurls[st_id] + "/cal/freecal/" + cal_root + "/" + cal_fn
         remote_json_url = ST.rurls[st_id] + "/cal/freecal/" + cal_root + "/" + cal_fn.replace(".png", "-calparams.json")
         if os.path.exists(local_cal_file) is False:
            cmd = "wget " + remote_png_url + " -O " + local_cal_file
            print(cmd)
            os.system(cmd)

         if os.path.exists(local_json_file) is False:
            cmd = "wget " + remote_json_url + " -O " + local_json_file
            print(cmd)
            os.system(cmd)
      else:
         remote_url = None
      print("open", local_json_file)
      try:
         cal_params = load_json_file(local_json_file)
      except:
         print("FAILED:", local_json_file)

      #if "station_id" not in cal_params:
      #   cal_params['station_id'] = station_id
      cal_file = local_cal_file
      if os.path.exists(cal_file) is False:
         print(cal_file, "missing")
         exit()
      oimg = cv2.imread(cal_file)
   else:
      # this must be a local cal file from a local AS7 Station
      cal_root = cal_file.split("-")[0]
      cal_dir = "/mnt/ams2/cal/freecal/" + cal_root + "/"
      (meteor_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_file)

      # suppport more than 1 way
      if "stacked.png" in cal_file:
         cal_json_file = cal_file.replace("-stacked.png", "-stacked-calparams.json")
      else:
         cal_json_file = cal_file.replace(".png", ".json")

      # load cal params file if it exists
      if os.path.exists(cal_dir + cal_json_file) :
         cal_params = load_json_file(cal_dir + cal_json_file)
      else:
         cal_params = None



   used_img = np.zeros((1080,1920),dtype=np.uint8)
   cat_star_mask = np.zeros((1080,1920),dtype=np.uint8)
   cat_star_mask[:,:] = 255

   # load cal image file
   oimg = cv2.imread(cal_file)
   show_img = oimg.copy()
   gray_img = cv2.cvtColor(oimg, cv2.COLOR_BGR2GRAY)

   # find bright points (image stars) in the image
   stars = find_stars_with_grid(oimg)
   best_stars = []

   print("FOUND STARS:", len(stars))
   temp_stars = []
   for star in stars:
      x,y,i = star
      # get flux for star points
      flux = do_photo(gray_img, (int(x),int(y)), 8)


      if 100 <= flux <= 5000:
         temp_stars.append((x,y,flux))

   for star in sorted(temp_stars, key=lambda x: (x[2]), reverse=True) :
      x,y,i = star
      rx1 = int(x - 10)
      rx2 = int(x + 10)
      ry1 = int(y - 10)
      ry2 = int(y + 10)
      star_cat_info = None
      star_crop = gray_img[ry1:ry2,rx1:rx2]
      star_obj = eval_star_crop(star_crop, cal_file, rx1, ry1, rx2, ry2, star_cat_info)
      if star_obj['valid_star'] is True:
         print(" VALID STAR:", star_obj)
         cv2.circle(show_img, (int(x),int(y)), 10, (255,255,0),2)
      else:
         print(" BAD STAR:", star_obj)
         cv2.circle(show_img, (int(x),int(y)), 10, (0,0,255),2)
      #if SHOW == 1:
      #   cv2.imshow('pepe', show_img)
      #   cv2.waitKey(30)
      best_stars.append((x,y,i))
   if SHOW == 1:
      cv2.waitKey(30)

   # these are the image stars sorted by brightest first
   stars =  sorted(best_stars, key=lambda x: x[2], reverse=True)

   # if it exists, try to use the existing calibration as a starting point
   if cal_params is not None:
      # get current catalog
      cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params, MAG_LIMIT=5)
      found = 0
      for row in cat_stars[:100]: 
         (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = row
         cv2.line(cat_star_mask, (int(zp_cat_x),int(zp_cat_y)), (int(new_cat_x),int(new_cat_y)), (0,0,0), 10)
         center_dist = calc_dist((960,540),(new_cat_x,new_cat_y))
         if center_dist > 600:
            rad = 32
            if new_cat_x > (1920 / 2):
               # right side
               rx1 = int(new_cat_x - (rad*2))
               rx2 = int(new_cat_x + 0)
               ry1 = int(new_cat_y - rad)
               ry2 = int(new_cat_y + rad)
            else:
               # left side
               rx1 = int(new_cat_x - 0)
               rx2 = int(new_cat_x + (rad * 2))
               ry1 = int(new_cat_y - rad)
               ry2 = int(new_cat_y + rad)
         else:
            rad = 16
            rx1 = int(new_cat_x - rad)
            rx2 = int(new_cat_x + rad)
            ry1 = int(new_cat_y - rad)
            ry2 = int(new_cat_y + rad)

         if rx1 <= 0 or ry1 <= 0 or rx2 >= 1920 or ry2 >= 1080:
            continue
         star_crop = gray_img[ry1:ry2,rx1:rx2]
         star_cat_info = [name,mag,ra,dec,new_cat_x,new_cat_y]
         used_val = used_img[int(new_cat_y),int(new_cat_x)]
         star_obj = eval_star_crop(star_crop, cal_file, rx1, ry1, rx2, ry2, star_cat_info)
         #print(star_obj)
         if star_obj['valid_star'] is True and used_val == 0:
            found += 1
            line_color = [255,255,255]
            cv2.circle(show_img, (int(new_cat_x),int(new_cat_y)), 10, (255,255,0),2)
            cv2.line(show_img, (int(new_cat_x),int(new_cat_y)), (int(star_obj['star_x']),int(star_obj['star_y'])), line_color, 1)
            used_img[ry1:ry2,rx1:rx2] = 255
         else:
            cv2.circle(show_img, (int(new_cat_x),int(new_cat_y)), 10, (0,0,255),2)

            cv2.putText(show_img, str(star_obj['reject_reason']),  (int(rx1),int(ry1)), cv2.FONT_HERSHEY_SIMPLEX, .8, (200,200,200), 1)

   gray_x = cv2.cvtColor(oimg, cv2.COLOR_BGR2GRAY)
   img_sub = cv2.subtract(gray_x,cat_star_mask)
   if SHOW == 1:
      cv2.imshow('pepe', img_sub)
      cv2.waitKey(30)
      cv2.imshow('pepe', show_img)
      cv2.waitKey(30)

   if cal_params is None:
      cal_params = blind_solve(cal_file, oimg, best_stars, remote_json_conf)
   else:
      cal_params['cam_id'] = cam
      cal_params['station_id'] = st_id
      station_id = st_id

   cal_params = man_cal(local_json_file, oimg, station_id, cal_fn, cal_params)
   return(cal_params)

def blind_solve(cal_file, cal_img, best_stars, remote_json_conf):
   print("BLIND SOLVE:", cal_file)
   temp_dir = "/home/ams/astrotemp/"
   if os.path.exists(temp_dir) is False:
      os.makedirs(temp_dir)
   else:
      os.system("rm " + temp_dir + "*")
   plate_img, star_points = make_plate_image(cal_img, best_stars)
   cal_fn = cal_file.split("/")[-1]
   print(plate_img)
   cv2.imshow("pepe", plate_img)
   cv2.waitKey(30)

   if os.path.exists("/usr/local/astrometry/bin/solve-field") is True:
      AST_BIN = "/usr/local/astrometry/bin/"
   elif os.path.exists("/usr/bin/solve-field") is True:
      AST_BIN = "/usr/bin/"
   
   new_plate_file = temp_dir + cal_fn
   cv2.imwrite(new_plate_file, plate_img)
   print("saved plate file:", new_plate_file)

   cmd = AST_BIN + "solve-field " + new_plate_file + " --cpulimit=30 --verbose --overwrite  --scale-units arcsecperpix --scale-low 150 --scale-high 170 > " + temp_dir + "stderr.txt 2>&1" 
   print(cmd)
   os.system(cmd)
   cmd2 = "grep \" at \" " + temp_dir + "stderr.txt |grep -v onstellation > " + temp_dir + "stars.txt"
   print(cmd2)
   os.system(cmd2)

   time.sleep(1)

   fp = open(temp_dir + "stars.txt")
   show_img = cal_img.copy()
   for line in fp:
      
      xxx = line.split(":")
      print("XXX", xxx)
      if len(xxx) != 1:
         continue
      data = xxx[0]
      star, position = data.split(" at ")
      if "," not in position:
         continue
      x,y = position.split(",")
      x = x.replace("(","")
      y = y.replace(")","")
      x = x.replace(" ","")
      y = y.replace(" ","")
      print("NAME=",star, "POS=", x,y)
      cv2.circle(show_img, (int(float(x)),int(float(y))), 5, (255,255,255),1)
      cv2.putText(show_img, str(star),  (int(float(x)),int(float(y))), cv2.FONT_HERSHEY_SIMPLEX, .8, (200,200,200), 1)
      cv2.imshow('pepe', show_img)
      cv2.waitKey(30)
   if "png" in new_plate_file:
      wcs_file = new_plate_file.replace(".png", ".wcs")
   else:
      wcs_file = new_plate_file.replace(".jpg", ".wcs")
   print("WCS", wcs_file)
   wcs_info_file = wcs_file.replace(".wcs", "-wcsinfo.txt")

   cmd = AST_BIN + "wcsinfo " + wcs_file + " > " + wcs_info_file
   print(cmd)
   os.system(cmd)

   default_cal_params = save_cal_params(wcs_file,remote_json_conf)

   #default_cal_params['ra_center'] = new_ra
   #default_cal_params['dec_center'] = new_dec 
   #default_cal_params['center_az'] = new_az
   #default_cal_params['center_el'] = new_el

   #default_cal_params['position_angle'] = new_pos
   #default_cal_params['pixscale'] = new_px 

   # pair cat stars with image stars
   # try all positions first!
   best_res = 9999
   best_pos = 0 
   most_stars = 0 

   # check for the best position angle
   for i in range(0,180):
      star_index = {} 
      rez = []

      default_cal_params['position_angle'] = i * 2 
      cat_stars, short_bright_stars, cat_image = get_catalog_stars(default_cal_params, MAG_LIMIT=4)
      blend = cv2.addWeighted(cat_image, .5, cal_img, .5, .3)
      for x,y,i in best_stars:
         cv2.circle(blend, (int(x),int(y)), 5, (255,0,0),1)
      for cs in cat_stars:
         (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = cs 
         skey = str(ra) + "_" + str(dec)

         for x,y,i in best_stars:
            dist = calc_dist((x,y),(new_cat_x,new_cat_y))
            if dist < 30:
               print("   BS:", name, mag, i, dist)
               if skey not in star_index:
                  cv2.circle(blend, (int(x),int(y)), 8, (0,0,255),1)
                  star_index[skey] = dist
               elif star_index[skey] <= dist:
                  cv2.circle(blend, (int(x),int(y)), 8, (0,0,255),1)
                  star_index[skey] = dist
         for sk in star_index:
            rez.append(star_index[sk])
         tres = np.median(rez)
         tstars = len(star_index.keys())
         if tres < best_res and tstars > most_stars:
            best_res = tres 
            most_stars = tstars 
            best_pos = default_cal_params['position_angle']

      #echo_calparams(cal_fn, default_cal_params)
      if SHOW == 1:
         cv2.imshow('pepe', blend)
         cv2.waitKey(30)

   mcp = None
   con = None
   cur = None
   print(default_cal_params)
   cv2.imshow('pepe', blend)
   cv2.waitKey(30)
   print("MOST STARS:", most_stars)
   print("BEST RES:", best_res)
   print("BEST POS:", best_pos)

   default_cal_params['position_angle'] = best_pos
   #   for row in zp_cat_stars[:MAX_STARS]: 
   #      (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = row

   #if True:
   # check for the best pixscale 
   start_px = float(default_cal_params['pixscale'])
   for i in range(-10,10):
      cat_star_index = {}
      star_index = {} 
      rez = []
      mod = i / 2 
      default_cal_params['pixscale'] = start_px + mod
      print("MOD:", mod, default_cal_params['pixscale'])
      cat_stars, short_bright_stars, cat_image = get_catalog_stars(default_cal_params, MAG_LIMIT=4)
      blend = cv2.addWeighted(cat_image, .5, cal_img, .5, .3)
      for cs in cat_stars:
         (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = cs 
         skey = str(ra) + "_" + str(dec)

         for x,y,i in best_stars:
            dist = calc_dist((x,y),(new_cat_x,new_cat_y))
            if dist < 30:
               if skey not in star_index:
                  cv2.circle(blend, (int(x),int(y)), 8, (0,0,255),1)
                  cv2.circle(blend, (int(new_cat_x),int(new_cat_y)), 8, (0,255,255),1)
                  star_index[skey] = dist
                  print("   BS:", name, mag, i, dist)
                  cat_star_index[skey] =  [name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y,x,y,i,dist]
                  cv2.line(blend, (int(x),int(y)), (int(zp_cat_x),int(zp_cat_y)), (255,255,255), 1)
               elif star_index[skey] <= dist:
                  print("   BS:", name, mag, i, dist)
                  cv2.circle(blend, (int(x),int(y)), 8, (0,0,255),1)
                  cv2.line(blend, (int(x),int(y)), (int(zp_cat_x),int(zp_cat_y)), (255,255,255), 1)
                  cv2.circle(blend, (int(new_cat_x),int(new_cat_y)), 8, (0,255,255),1)
                  star_index[skey] = dist
                  cat_star_index[skey] =  [name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y,x,y,i,dist]
         for sk in star_index:
            rez.append(star_index[sk])
         tres = np.median(rez)
         tstars = len(star_index.keys())
         if tres < best_res and tstars > most_stars:
            best_res = tres 
            most_stars = tstars 
            best_pxs = default_cal_params['position_angle']
                   
         #cv2.imshow('pepe', blend)
         #cv2.waitKey(30)

   cat_image_stars = []
   blend = cv2.addWeighted(cat_image, .5, cal_img, .5, .3)
   for skey in cat_star_index:
      name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y,six,siy,star_int,cat_dist = cat_star_index[skey] 
     
      match_dist = None
      img_ra = None
      img_dec = None
      img_el = None
      img_az = None
      cat_image_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,zp_cat_x,zp_cat_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int)) 
      if SHOW == 1:
         cv2.line(blend, (int(six),int(siy)), (int(zp_cat_x),int(zp_cat_y)), (255,255,255), 1)
         cv2.imshow('pepe', blend)
         cv2.waitKey(30)

   default_cal_params['cat_image_stars'] = cat_image_stars

   default_cal_params['x_poly'] = list(np.zeros(shape=(15,), dtype=np.float64))
   default_cal_params['y_poly'] = list(np.zeros(shape=(15,), dtype=np.float64))
   default_cal_params['x_poly_fwd'] = list(np.zeros(shape=(15,), dtype=np.float64))
   default_cal_params['y_poly_fwd'] = list(np.zeros(shape=(15,), dtype=np.float64))

   print("CAT IMG STARS:", len(cat_image_stars))
   #temp_cal_params = minimize_fov(cal_fn, default_cal_params, cal_fn,cal_img.copy(),remote_json_conf, False,default_cal_params, "", 1)
   extra_text = "Recenter"
   default_cal_params['total_res_px'] = 99
   temp_cal_params, cat_stars = recenter_fov(cal_fn, default_cal_params, cal_img.copy(),  default_cal_params['cat_image_stars'], remote_json_conf, extra_text, None, None)
   extra_text = "FINAL RESULTS OF REMOTE BLIND SOLVE [NO LENS MODEL]"
   star_img = draw_star_image(cal_img, temp_cal_params['cat_image_stars'],temp_cal_params, remote_json_conf, extra_text)   
   

   print("CAT IMG STARS:", len(temp_cal_params['cat_image_stars']))
   if SHOW == 1:
      cv2.imshow('pepe', star_img)
      cv2.waitKey(30)

   return(temp_cal_params)


def echo_calparams(cf, cp):
   print("*** CAL PARAMS ***")   
   print(" FILE:", cf)
   print(" AZ:", cp['center_az'])
   print(" EL:", cp['center_el'])
   print(" RA:", cp['ra_center'])
   print(" DEC:", cp['dec_center'])
   print(" POS:", cp['position_angle'])
   print(" PXS:", cp['pixscale'])
  
def man_cal(local_json_file, oimg, station_id, cal_fn, cal_params):
   if cal_params is not None:
      orig_cal_params = cal_params.copy()
   else:
      orig_cal_params = cal_params
   MAX_STARS = 500
   go = True
   interval = 1
   (meteor_datetime, cam_id, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(local_json_file)

   local_mask_img_dir = "/mnt/f/EVENTS/STATIONS/" + station_id + "/CAL/MASKS/" 
   cloud_mask_img_dir = "/mnt/archive.allsky.tv/" + station_id + "/CAL/MASKS/" 
   if os.path.exists(local_mask_img_dir) is False:
      os.makedirs(local_mask_img_dir)
   mask_img_file = local_mask_img_dir + cam_id + "_mask.png"  
   if os.path.exists(mask_img_file) is False:
      sys = ("cp " + cloud_mask_img_dir + "*" + " " + local_mask_img_dir)
      os.system(sys)
   mask_img = cv2.imread(mask_img_file)
   mask_img = cv2.resize(mask_img, (oimg.shape[1], oimg.shape[0]))


   #rez = np.median([row[-2] for row in cat_image_stars])

   while go is True:
      cat_star_mask = np.zeros((1080,1920),dtype=np.uint8)
      all_res = []
      cat_star_mask[:,:] = 255
      used_img = np.zeros((1080,1920),dtype=np.uint8)
      oimg = cv2.subtract(oimg, mask_img)
      show_img = oimg.copy()
      temp_img = oimg.copy()
      gray_img = cv2.cvtColor(oimg, cv2.COLOR_BGR2GRAY)

      # get catalog with current cal params
      cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params, MAG_LIMIT=6)

      zp_cal_params = cal_params.copy()
      zp_cal_params['x_poly'] = list(np.zeros(shape=(15,), dtype=np.float64))
      zp_cal_params['y_poly'] = list(np.zeros(shape=(15,), dtype=np.float64))
      zp_cal_params['x_poly_fwd'] = list(np.zeros(shape=(15,), dtype=np.float64))
      zp_cal_params['y_poly_fwd'] = list(np.zeros(shape=(15,), dtype=np.float64))
      zp_cat_stars, short_bright_stars, cat_image = get_catalog_stars(zp_cal_params, MAG_LIMIT=5)
      #cal_params = zp_cal_params
      found = 0
      cat_image_stars = []
      # pick stars based on settings
      for row in zp_cat_stars[:MAX_STARS]: 
         (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = row

         if True:
            if True:
               if int(mag) <= 0:
                  msize = 14
               elif 0 < int(mag) <= 1:
                  msize = 12
               elif 1 < int(mag) <= 2:
                  msize = 10
               elif 3 < int(mag) <= 4:
                  msize = 8
               elif 4 < int(mag) <= 5:
                  msize = 6
               else:
                  msize = 4

         cv2.line(cat_star_mask, (int(zp_cat_x),int(zp_cat_y)), (int(new_cat_x),int(new_cat_y)), (0,0,0), 10)
         center_dist = calc_dist((960,540),(new_cat_x,new_cat_y))
         if gray_img[int(new_cat_y), int(new_cat_x)] == 0:
            # star inside mask area
            continue
         if center_dist > 600:
            # outside
            rad = 32
            if new_cat_x > (1920 / 2):
               # right side
               rx1 = int(new_cat_x - (rad*2))
               rx2 = int(new_cat_x + (rad/2))
               if new_cat_y < 1080 / 2:
                  #top
                  ry1 = int(new_cat_y - (rad/2))
                  ry2 = int(new_cat_y + rad)
               else:
                  ry1 = int(new_cat_y - rad)
                  ry2 = int(new_cat_y + (rad/2))
            else:
               # left side
               rx1 = int(new_cat_x - (rad/2))
               rx2 = int(new_cat_x + (rad * 2))
               if new_cat_y < 1080 / 2:
                  #bottom
                  ry1 = int(new_cat_y - (rad/2))
                  ry2 = int(new_cat_y + rad)
               else:
                  ry1 = int(new_cat_y - rad)
                  ry2 = int(new_cat_y + (rad/2))

         else:
            rad = 16
            rx1 = int(new_cat_x - rad)
            rx2 = int(new_cat_x + rad)
            ry1 = int(new_cat_y - rad)
            ry2 = int(new_cat_y + rad)


         if rx1 <= 0 or ry1 <= 0 or rx2 >= 1920 or ry2 >= 1080:
            continue
         star_crop = gray_img[ry1:ry2,rx1:rx2]
         star_cat_info = [name,mag,ra,dec, new_cat_x,new_cat_y]
         used_val = used_img[int(new_cat_y),int(new_cat_x)]
         star_obj = eval_star_crop(star_crop, cal_fn, rx1, ry1, rx2, ry2, star_cat_info)
         #print(star_obj)
         #for key in star_obj:
         #   print(key, star_obj[key])
         if star_obj['valid_star'] is True and used_val == 0:
            line_color = [128,128,128]
         else:
            line_color = [0,0,128]

         cv2.circle(temp_img, (int(new_cat_x),int(new_cat_y)), 2, (255,255,0),1)
         cv2.rectangle(temp_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), line_color, 1)
         cv2.line(temp_img, (int(new_cat_x),int(new_cat_y)), (int(star_obj['star_x']),int(star_obj['star_y'])), line_color, 1)
         cv2.putText(temp_img, str(star_obj['reject_reason']),  (int(rx1),int(ry1)), cv2.FONT_HERSHEY_SIMPLEX, .8, (200,200,200), 1)
         #cv2.imshow('pepe', temp_img)
         #cv2.imshow('crop', star_crop)
         #cv2.waitKey(30)
         if star_obj['valid_star'] is True and used_val == 0:
            found += 1
            line_color = [255,255,255]

            #(dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
            new_cat_x, new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)

            res_px = calc_dist((star_obj['star_x'],star_obj['star_y']),(new_cat_x,new_cat_y))
            all_res.append(res_px)
            med_res = np.median(all_res)
            rjson_conf = {}
            rjson_conf['site'] = {}
            rjson_conf['site']['ams_id'] = station_id
            rjson_conf['site']['device_lat'] = cal_params['device_lat']
            rjson_conf['site']['device_lng'] = cal_params['device_lng']
            rjson_conf['site']['device_alt'] = cal_params['device_alt']
            new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(star_obj['star_x'],star_obj['star_y'],cal_fn,cal_params,rjson_conf)
            six = star_obj['star_x']
            siy = star_obj['star_y']
            match_dist = angularSeparation(ra,dec,img_ra,img_dec)
            real_res_px = res_px
            used_val2 = used_img[int(siy),int(six)]




            #{'cal_fn': '2023_01_03_20_32_03_000_011101-stacked.png', 'star_x': 945.5, 'star_y': 553.0, 'x1': 929, 'y1': 534, 'x2': 961, 'y2': 566, 'cnts': [(16, 18, 1, 2)], 'star_flux': 1671.91, 'pxd': 187, 'brightest_point': [16, 18], 'brightest_val': 231, 'bg_avg': 43, 'star_yn': -1, 'radius': 2, 'valid_star': True, 'reject_reason': '', 'thresh_val': 226.38, 'cx': 16.5, 'cy': 19.0, 'name': 'αUMi', 'mag': 2.0, 'ra': 37.9529, 'dec': 89.2642#}
            star_int = star_obj['star_flux']
            #img_ra = star_obj['ra']
            #img_dec = star_obj['dec']
            org_x = star_obj['dec']

            match_dist = angularSeparation(ra,dec,img_ra,img_dec)
            print("USED VAL:", used_val, used_val2)
            if used_val != 255 and used_val2 != 255 and res_px <= med_res * 2:
               cat_image_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,real_res_px,star_obj['star_flux']))
               cv2.circle(show_img, (int(new_cat_x),int(new_cat_y)), msize, (255,255,0),2)
               cv2.line(show_img, (int(new_cat_x),int(new_cat_y)), (int(star_obj['star_x']),int(star_obj['star_y'])), line_color, 1)
            used_img[ry1:ry2,rx1:rx2] = 255
            used_img[int(siy),int(six)] = 255
            #cat_image_stars.append((star_obj['name'],star_obj['mag'],ra,dec,img_ra,img_dec,match_dist,star_obj['star_x'],star_obj['star_y'],star_obj['img_az'],star_obj['img_el'],star_obj['cat_x'],star_obj['cat_y'],star_obj['star_x'],star_obj['star_y'],star_obj['total_res_px'],star_obj['star_flux']))

            #cat_image_stars.append(name,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int)


         else:
            cv2.circle(show_img, (int(new_cat_x),int(new_cat_y)), msize, (0,0,255),2)
         if mag <= 2:
            cv2.putText(show_img, str(name),  (int(new_cat_x),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .8, (200,200,200), 1)

      cal_params['cat_image_stars'] = cat_image_stars

      rez = np.median([row[-2] for row in cal_params['cat_image_stars']])

      #gray_x = cv2.cvtColor(oimg, cv2.COLOR_BGR2GRAY)
      #img_sub = cv2.subtract(gray_x,cat_star_mask)
      found_perc = found / MAX_STARS 
       
      # STILL NOT READY

      info = "AZ: {} / EL: {} / POS: {} PX: {} / Int: {} / Found: {}% / Res: {}".format(str(round(cal_params['center_az'],2)), \
              str(round(cal_params['center_el'],2)), \
              str(round(cal_params['position_angle'],2)), \
              str(round(cal_params['pixscale'],2)),\
              str(interval) , str(int(found_perc)), str(round(rez,3)))

      cv2.putText(show_img, str(info),  (int(50),int(50)), cv2.FONT_HERSHEY_SIMPLEX, .8, (200,200,200), 1)

      if SHOW == 1:
         cv2.imshow('pepe', show_img)
         print("OPTIONS ARE AZIMUTH A &F zerro out poly")
         cv2.setMouseCallback('pepe', click_event, "testing123")
         key = cv2.waitKey(0)
      print("KEY", key)

      # azimuth a & f
      if key == 119:
          # W - write 
         save_json_file(local_json_file, cal_params)
         print("SAVED:", local_json_file)
      if key == 122:
         # zero out poly
         print("zero poly")
         cal_params['x_poly'] = list(np.zeros(shape=(15,), dtype=np.float64))
         cal_params['y_poly'] = list(np.zeros(shape=(15,), dtype=np.float64))
         cal_params['x_poly_fwd'] = list(np.zeros(shape=(15,), dtype=np.float64))
         cal_params['y_poly_fwd'] = list(np.zeros(shape=(15,), dtype=np.float64))

      if key == 97:
         cal_params['center_az'] -= interval
      if key == 102:
         cal_params['center_az'] += interval
      # elev s & d 
      if key == 115:
         cal_params['center_el'] -= interval
      if key == 100:
         cal_params['center_el'] += interval
      # position angle k/l
      if key == 107:
         cal_params['position_angle'] -= interval
      if key == 108:
         cal_params['position_angle'] += interval
      # pixscale j/; 
      if key == 106:
         cal_params['pixscale'] -= interval
      if key == 59:
         cal_params['pixscale'] += interval
      # interval +/- 
      if key == 61:
         interval = interval * 10
      if key == 45:
         interval = interval / 10
      if key == 45:
         #(W)rite changes
         save_json_file(local_json_file, cal_params)
      if key == 109:

          temp_cal_params = minimize_fov(cal_fn, cal_params, cal_fn,oimg.copy(),rjson_conf, False,cal_params, "", 1) 
          temp_cal_params['cat_image_stars'] = remove_bad_stars(temp_cal_params['cat_image_stars'])
          if temp_cal_params['total_res_px'] < cal_params['total_res_px']:
             print("AFTER MIN BETTER")
             cal_params = temp_cal_params
             cal_params = update_center_radec(cal_fn,cal_params,rjson_conf)
          else:
             print("AFTER MIN WORSE")
      if key == 112:
         # lens model
         merged_stars = []
         for star in cal_params['cat_image_stars']:
            name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,real_res_px,star_flux = star
            merged_stars.append((cal_fn, cal_params['center_az'], cal_params['center_el'], cal_params['ra_center'], cal_params['dec_center'], cal_params['position_angle'], cal_params['pixscale'], name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,res_px,star_flux))

         status, new_cal_params,merged_stars = minimize_poly_multi_star(merged_stars, rjson_conf,0,0,cal_params['cam_id'],None,cal_params,SHOW)
         if new_cal_params != 0:
            print("NEW CAL XP:", cal_params['x_poly'])
            cal_params['x_poly'] = new_cal_params['x_poly']
            cal_params['y_poly'] = new_cal_params['y_poly']
            cal_params['x_poly_fwd'] = new_cal_params['x_poly_fwd']
            cal_params['y_poly_fwd'] = new_cal_params['y_poly_fwd']
         else:
            print("POLY ATTEMPT FAILED!?")
      
      if key == 114:
         #(R)evert
         cal_params = orig_cal_params
      cal_params = update_center_radec(cal_fn,cal_params,rjson_conf)
      print("CP:", cal_params.keys())
      print("KEY", key)
      if key == 27:
         print("end man cal")
         return(cal_params)
         go = False
   return(cal_params)



def get_close_calib_files(cal_file):
   (meteor_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_file)
   close_files = []
   calindex_file = "/mnt/ams2/cal/freecal_index.json"
   #print("get_close_calib_files:", cal_file)
   if os.path.exists(calindex_file) is True:
      try:
         calindex = load_json_file(calindex_file)
      except:
         print("FAILED TO LOAD CAL INDEX:", calindex_file)
         exit()
   else:
      print("NO FILE:", calindex_file)

   after_files = []
   before_files = []
   for cf in sorted(calindex):
      cdata = calindex[cf]
      if "cam_id" not in cdata:
         continue
      if cdata['cam_id'] == cam:
         (cal_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(cf)
         cfs = cf.split("/")[-1].split("-")[0]
         tdiff = meteor_datetime - cal_datetime
         tdays = float(tdiff.total_seconds() / 60 / 60 / 24)
         pack_data = [cfs, f_date_str, tdays, cdata['center_az'], cdata['center_el'], cdata['position_angle'], cdata['pixscale'], cdata['total_res_px']]
         if tdays > 0:
            before_files.append(pack_data)
         else:
            after_files.append(pack_data)

   bfiles =  sorted(before_files, key=lambda x: x[2], reverse=False)[0:3]
   afiles =  sorted(after_files, key=lambda x: x[2], reverse=False)[0:3]

   print("   BEFORE FILES:", len(bfiles))
   print("   AFTER FILES:",  len(afiles))
   return(bfiles, afiles)

def calc_res_from_stars(cal_fn, cal_params, json_conf):
   up_stars = []
   tres = []
   for star in cal_params['cat_image_stars']:
      name,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,cat_dist,star_int = star

      n_new_cat_x,n_new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)

      if new_cat_x is None:
         continue
      if n_new_cat_x is not None:
         n_res_px = calc_dist((img_x,img_y), (n_new_cat_x,n_new_cat_y))
      else:
         n_res_px = 0
      tres.append(n_res_px)

      #print("OLD {} {}".format(new_cat_x, new_cat_y))
      #print("NEW {} {}".format(n_new_cat_x, n_new_cat_y))
      #print("___")

      up_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,cat_dist,star_int))
      #up_stars.append((cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope))
      cal_params['total_res_px'] = np.median(tres)
      cal_params['cat_image_stars'] = up_stars
   return(cal_params)

def cal_health(con, cur, json_conf, cam_num=None):

   fix_lens_nans()

   cam_num = cam_num.upper()
   autocal_dir = "/mnt/ams2/cal/" 
   station_id = json_conf['site']['ams_id']

   cam_stats = {}
   freecal_index = load_json_file("/mnt/ams2/cal/freecal_index.json") 
   for cal_file in freecal_index:
      d = freecal_index[cal_file]
      # check for bad vals
      if "total_res_px" in d:
         nanres = np.isnan(d['total_res_px'])
      else:
         print(cal_file, "missing res!")
         exit()
      cal_fn = cal_file.split("/")[-1]
      if nanres == True or type(d['total_res_px']) == str or d['total_res_px'] == "": 
         print("BAD RES", d)
         if os.path.exists(cal_file): 
            delete_cal_file(cal_fn, con, cur, json_conf)
         continue 

      if d['cam_id'] not in cam_stats:
         cam_stats[d['cam_id']] = {}
         cam_stats[d['cam_id']]['azs'] = []
         cam_stats[d['cam_id']]['els'] = []
         cam_stats[d['cam_id']]['pos'] = []
         cam_stats[d['cam_id']]['pxs'] = []
         cam_stats[d['cam_id']]['stars'] = []
         cam_stats[d['cam_id']]['rezs'] = []
         cam_stats[d['cam_id']]['bad_files'] = []
         cam_stats[d['cam_id']]['avg_files'] = []
         cam_stats[d['cam_id']]['good_files'] = []
      cam_stats[d['cam_id']]['stars'].append(d['total_stars'])
      cam_stats[d['cam_id']]['rezs'].append(d['total_res_px']) 

   for cam_id in cam_stats:
      #print(cam_stats[cam_id])
      cam_stats[cam_id]['med_stars'] = np.median(cam_stats[cam_id]['stars'])
      cam_stats[cam_id]['med_rez'] = np.median(cam_stats[cam_id]['rezs'])
      #print(cam_id, cam_stats[cam_id]['med_stars'], cam_stats[cam_id]['med_rez'])

   for f in freecal_index:
      d = freecal_index[f]
      cam_id = d['cam_id']
      

      if d['total_stars'] < cam_stats[cam_id]['med_stars'] * .8 or d['total_res_px'] < cam_stats[cam_id]['med_rez'] * .8:
         cam_stats[cam_id]['bad_files'].append(f)
      elif d['total_stars'] > cam_stats[cam_id]['med_stars'] * 1.2 and d['total_res_px'] > cam_stats[cam_id]['med_rez'] * 1.2:
         cam_stats[cam_id]['good_files'].append(f)
      else:
         cam_stats[cam_id]['avg_files'].append(f)

   tb = pt()
   tb.field_names = ["#", "Cam ID","Avg Stars", "Avg Res", "Good Files", "Avg Files","Bad Files", "LM Res", "LM Stars", "LM Runs", "LM Date", "Min/Max Star Dist"]
   cc = 0 
   cam_nums = {}
   info = []

   # make jobs
   jobs = []
   for cam_id in sorted(cam_stats):
      #print(cam_id, len(cam_stats[cam_id]['good_files']), "good", len(cam_stats[cam_id]['bad_files']), "bad")
      lf = "/mnt/ams2/cal/multi_poly-{:s}-{:s}.info".format(station_id, cam_id)
      if os.path.exists(lf) is True:
         mp = load_json_file(lf)
         fun = (mp['x_fun'] + mp['y_fun'] ) / 2
         if "cal_version" in mp:
            model_runs = mp['cal_version']
         else:
            model_runs = 0
         if "total_stars_used" in mp:
            lm_stars = mp['total_stars_used']
            lm_date = mp['lens_model_datetime']
         else:
            lm_stars = "na"
            lm_date = "na na"
      if 'min_max_dist_status' in mp:
         min_max_dist_status = mp['min_max_dist_status'] 
      else:
         min_max_dist_status = "unknown"
         #print(mp.keys())
      cam_num = cc + 1
      tb.add_row([cam_num, cam_id, cam_stats[cam_id]['med_stars'], round(cam_stats[cam_id]['med_rez'],3), len(cam_stats[cam_id]['good_files']), len(cam_stats[cam_id]['avg_files']), len(cam_stats[cam_id]['bad_files']), round(fun,3), lm_stars, model_runs, lm_date.split(" ")[0], min_max_dist_status])
      info.append([cam_num, cam_id, cam_stats[cam_id]['med_stars'], round(cam_stats[cam_id]['med_rez'],3), len(cam_stats[cam_id]['good_files']), len(cam_stats[cam_id]['avg_files']), len(cam_stats[cam_id]['bad_files']), round(fun,3), lm_stars, model_runs, lm_date.split(" ")[0], min_max_dist_status])
      cam_nums[cam_num] = cam_id
      # make actions / decisions for auto bots 

      cc += 1
   now = datetime.datetime.now().strftime("%Y_%m_%d")

   # MAIN USER OUTPUT
   os.system("clear")
   print("AllSky Observing Software")
   print("CALIBRATION HEALTH FOR " + station_id + " RUN ON " + now  )
   print(tb)
   cam_status = tb
   # write cam_status to txt file
   cam_status_txt = "/mnt/ams2/cal/" + station_id + "_cal_status.txt"
   fp = open(cam_status_txt, "w")
   fp.write("CALIBRATION HEALTH FOR " + station_id + " Last updated " + now  + "\n")
   fp.write(str(cam_status) + "\n")

   freecal_files = sorted(os.listdir("/mnt/ams2/cal/freecal"), reverse=True)
   for f in freecal_files:
      if "json" in f and ".jpg" in f:
         print("BAD", f)
         os.system("rm /mnt/ams2/cal/freecal/" + f)
   fp.write("Last 10 Calibration Files\n")

   for f in freecal_files[0:10]:
      print(f)
      fp.write("\t" + str(f) + "\n")

   fp.close()
   cloud_dir = "/mnt/archive.allsky.tv/" + station_id + "/"
   print("saved", cam_status_txt)
   cmd = "cp " + cam_status_txt + " " + cloud_dir
   print(cmd)
   os.system(cmd)

   # The code after here is kind of like auto code, 
   # but really we want to save the cal health info and that is it. 

   return()
   #print("To work on a specific camera enter the camera number and press [ENTER]")
   #print("You have 5 seconds to run a custom command before this prompt ends.")

   # | Cam ID | Avg Stars | Avg Res | Good Files | Avg Files | Bad Files | LM Res | LM Stars | LM Runs |  LM Date   | Min/Max Star Dist
   # decide/prioritize refits -- We can stop when:
   #    - the avg res for the cam < 1 
   #    - there are more combined good + avg files than bad files
   #    - the LM res < 1
   #    - there are at least 350 stars in the LM.
   #    - track job runs so we don't run too much / too often -- need to spread the runs out over all types of jobs/cams/files
   #   start with refit jobs

   # auto jobs, needs work. disabled on of 4/8/23

   sys_rez = [row[3] for row in info]
   #print("System rez:", sys_rez)
   #info.append([cam_num, cam_id, cam_stats[cam_id]['med_stars'], round(cam_stats[cam_id]['med_rez'],3), len(cam_stats[cam_id]['good_files']), len(cam_stats[cam_id]['avg_files']), len(cam_stats[cam_id]['bad_files']), round(fun,3), lm_stars, model_runs, lm_date.split(" ")[0], min_max_dist_status])
   info = sorted(info, key=lambda x: (x[3]), reverse=False)
   for row in info:
      if row[3] > 1:
         # jobs = cam_id, job_id/func call/name, runtime or 0
         #jobs.append(("refit_best", row[1], 0))
         jobs.append(("refit_best", row[1], 8, row[3]))
         jobs.append(("refit_avg", row[1], 8, row[3]))
         jobs.append(("refit_bad", row[1], 8, row[3]))
         #print("\trefit job added", row[1], row[3], "is > 1")
      # if the lens model res is > 1 or there are less than 200 stars used in the model, 
      # redo the model
      if row[7] > 1 or row[8] < 200:
         #print("\tfast_lens job added", row[1], "res", row[7], "is > 1", "or stars", row[8] , "< 300" )
         jobs.append(("fast_lens", row[1], 9, row[7]))

   # get menu response from the user. If no response we should auto run the jobs?
   # this way a cron cal to cal_health will run the 'next' jobs without running too long

   # priority jobs
   jobs = sorted(jobs, key=lambda x: (x[2], x[3]), reverse=True)
   pjobs = []
   for job in jobs:
      pjobs.append(job)
   #   print("PJOBs", job)

   i, o, e = select.select( [sys.stdin], [], [], 10 )
   if (i) :
      scam_num = int(sys.stdin.readline().strip())
      selected_cam = cam_nums[scam_num]
      print("SELECTED CAMERA:", selected_cam)
      cam_menu(selected_cam, con, cur, json_conf,cam_status, cam_stats)
   elif cam_num is None:
      max_cams = len(cam_nums)
      scam_num = input("Select cam number (1-" + str(max_cams) + ")")
      selected_cam = cam_nums[int(scam_num)]
      print("SELECTED CAMERA:", selected_cam)
      cam_menu(selected_cam, con, cur, json_conf,cam_status, cam_stats)
   else:
      print("ALL CAMERAS SELECTED.")

   # below here is auto jobs stuff disabled on 4/8/23 for rework
  
   if False:
      selected_cam = None
      print("No custom command selected in time.")
      print("Auto running job list:")
      for job in jobs:
         print("JOB", job)
      #print("waiting for 3 seconds before starting autojobs... [cntl-x] to quit else auto jobs will run")
      #time.sleep(3)
      if False:
      #for job in pjobs:
         cam_id = job[1]
         if job[0] == "fast_lens":
            limit = 20 
            fast_lens(cam_id, con, cur, json_conf,limit, None)
            # only do this if the result from fast lens is really bad
            #lens_model(cam_id, con, cur, json_conf )

         if job[0] == "refit_avg":
            batch_apply(cam_id, con, cur, json_conf, None, False, cam_stats, "AVG", 50)
         if job[0] == "refit_best":
            batch_apply(cam_id, con, cur, json_conf, None, False, cam_stats, "BEST",50)
         if job[0] == "refit_bad":
            batch_apply(cam_id, con, cur, json_conf, None, False, cam_stats, "BAD",50)
      #print("Done auto cal health jobs")
   exit()



   # refit best files for each cam
   for cam_id in sorted(cam_stats):
      calfiles_data = load_cal_files(cam_id, con, cur)
      mcp = None
      if mcp is None:
         mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
         if os.path.exists(mcp_file) == 1:
            mcp = load_json_file(mcp_file)
      for f in cam_stats[cam_id]['good_files']:
         d = freecal_index[f]
         oimg = cv2.imread(d['cal_image_file'])
         if os.path.exists(f) is False:
            print("NO FILE:", f)
            continue
         cp = load_json_file(f)
         star_img = draw_star_image(oimg.copy(), cp['cat_image_stars'],cp, json_conf, "")
         if SHOW == 1:
            cv2.imshow('pepe', star_img)
            cv2.waitKey(30)
         cal_fn = f.split("/")[-1]
         extra_text = cal_fn
         #result = apply_calib (cal_fn, calfiles_data, json_conf, mcp, None, "", False, None)
         stars,cat_stars = get_paired_stars(cal_fn, cp, con, cur)

         cp['cat_image_stars'] = remove_bad_stars(cp['cat_image_stars'])
         cal_params, cat_stars = recenter_fov(cal_fn, cp, oimg.copy(),  stars, json_conf, extra_text, con, cur)

         cal_params['cat_image_stars'] = cat_star_match(cal_fn, cal_params, oimg, cat_stars)
         cal_params['cat_image_stars'] = remove_bad_stars(cp['cat_image_stars'])
         cal_params, cat_stars = recenter_fov(cal_fn, cal_params, oimg.copy(),  stars, json_conf, extra_text)
         save_json_file(f, cal_params)

def click_event(event, x,y,flags,params): 
   if event == cv2.EVENT_LBUTTONDOWN:
      print("YO:", event, x,y,flags,params)

def cam_menu(cam_id, con,cur, json_conf, cam_status="", cam_stats=None):

   tb = pt()
   tb.field_names = ["#", "Action"]
   tb.add_row(["1", "Calibration Status"])
   tb.add_row(["2", "Refit All Calfiles"])
   tb.add_row(["3", "Refit Best Calfiles"])
   tb.add_row(["4", "Refit Avg Calfiles"])
   tb.add_row(["5", "Refit Bad Calfiles"])
   tb.add_row(["6", "Remake Lens Model "])
   tb.add_row(["7", "Prune Excess Files"])
   tb.add_row(["8", "Reset Lens Model"])
   tb.add_row(["9", "Rebuild Cal Index"])
   tb.add_row(["10", "Main Menu"])
   go = True

   while go is True:
      os.system("clear")
      print(ASOS)
      print(cam_status)
      print("CALIBRATION MENU OPTIONS FOR CAMERA " + cam_id)
      print(tb)


      cmd = input("Select action # and press [ENTER]") 
      if True:
      #try:
         print("CMD", cmd)
         if int(cmd) == 1:
            print("Calibration status for camera:", cam_id)
            cal_status_report(cam_id, con, cur, json_conf)
         elif int(cmd) == 2:
            batch_apply(cam_id, con, cur, json_conf)
         elif int(cmd) == 3:
            batch_apply(cam_id, con, cur, json_conf, None, False, cam_stats, "BEST")
         elif int(cmd) == 4:
            batch_apply(cam_id, con, cur, json_conf, None, False, cam_stats, "AVG")
         elif int(cmd) == 5:
            print("APPLY BAD", cmd)
            batch_apply(cam_id, con, cur, json_conf, None, False, cam_stats, "BAD")
         elif int(cmd) == 6:
            samples = int(input("Enter the number of calibration files you want to use?"))
            fast_lens(cam_id, con, cur, json_conf, samples, None)
            if len(cam_stats[cam_id]['good_files']) >= samples:
               cal_fns = cam_stats[cam_id]['good_files'][0:samples]
            elif len(cam_stats[cam_id]['good_files']) + len(cam_stats[cam_id]['avg_files']) >= samples :
               cal_fns = cam_stats[cam_id]['good_files']
               cal_fns.extend(cam_stats[cam_id]['avg_files'])
               cal_fns = cal_fns[0:samples]        
            else:
               cal_fns = cam_stats[cam_id]['good_files']
               cal_fns.extend(cam_stats[cam_id]['avg_files'])
               cal_fns.extend(cam_stats[cam_id]['bad_files'])
               cal_fns = cal_fns[0:samples]        
            lens_model(cam_id, con, cur, json_conf, cal_fns, True)
         elif int(cmd) == 7:
            prune(cam_id, con, cur, json_conf)
         elif int(cmd) == 8:
            reset_lens_model(cam_id, con, cur, json_conf)
         elif int(cmd) == 9:
            os.system("cd ../pythonv2/; ./autoCal.py cal_index")
         elif int(cmd) == 10:
            cal_health(con, cur, json_conf )
         else:
            print("BAD INPUT!", cmd)
            cam_menu(cam_id, con,cur, json_conf, cam_status)
      #except:
      else:
         print("TRY FAILED# ")
         cam_menu(cam_id, con,cur, json_conf, cam_status="")

def reset_lens_model(cam_id, con, cur,json_conf):
   print("RESET LENS MODEL FOR ", cam_id)

def reset_bad_cals(this_cam_id, con, cur,json_conf):
   # this will scan all of the cals and anything that has 8px res will be sent back to the 
   # autocal dir for re-plate solving. 
   # then move the folder/contents to the badcal dir and make sure it no longer exists
   # inside the freecal dir. Keep a log of resets. If a file has already been reset more than 2x just delete it. 

   autocal_dir = "/mnt/ams2/cal/" 
   station_id = json_conf['site']['ams_id']

   mcp = None
   if mcp is None:
      mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + this_cam_id + ".info"
      if os.path.exists(mcp_file) == 1:
         mcp = load_json_file(mcp_file)

   freecal_index = load_json_file("/mnt/ams2/cal/freecal_index.json") 
   temp , temp_imgs = load_mask_imgs(json_conf)
   mask_imgs = {}
   for cam in temp:
      if temp[cam].shape[0] == 1080:
         mask_imgs[cam] = temp[cam]

   stats = {}
   cc = 0

   # build the stats if they don't exist or have been updated in a while
   go = False
   if mcp is None :
       mcp = {}
   if "cal_file_stats" not in mcp:
      go = True
   else:
      stats = mcp['cal_file_stats']
      if time.time() - mcp['cal_file_stats']['last_run'] > 86400 * 7:
         go = True
      else:
         print((time.time() - mcp['cal_file_stats']['last_run']) / 60 , "minutes ago")
         print("LAST RUN:", mcp['cal_file_stats']['last_run'] )

   go = True
   if go is True:
      stats = freecal_stats(this_cam_id, freecal_index, json_conf, stats, mask_imgs) 
   else:
      stats = mcp['cal_file_stats']

   if True:
      if mcp is not None:
         mcp['cal_file_stats'] = stats
         mcp['cal_file_stats']['last_run'] = time.time()
         save_json_file(mcp_file, mcp)

   for cam_id in stats: 
      if type(stats[cam_id]) is not dict:
         continue
      print(cam_id, stats[cam_id])

      for key in stats[cam_id]: 
         if "med" in key:
            print(cam_id, stats[cam_id], key, stats[cam_id][key])

   # now what?
   for cf in freecal_index:
      total_res_px = freecal_index[cf]['total_res_px']
      total_stars = freecal_index[cf]['total_stars']
      cal_id = cf.split("/")[-1].split("-")[0]
      cam_id = cal_id.split("_")[-1]
      if cam_id == this_cam_id:
         if total_res_px > 12 or total_stars < 5:
            reset_cal_file(station_id, cal_id)
            print("RESET", cam_id, cal_id, total_stars, total_res_px)
         else:
            print("GOOD", cam_id, cal_id, total_stars, total_res_px)


def freecal_stats(cam_id, freecal_index, json_conf, stats, mask_imgs) :
   cc = 0
   station_id = json_conf['site']['ams_id']
   for cal_file in freecal_index:
      print("CAL FILE:", cal_file)
      cal_id = cal_file.split("/")[-1].split("-")[0]
      cal_data = freecal_index[cal_file]
      t_cam_id = cal_data['cam_id']
      if cam_id != t_cam_id:
         continue


      if os.path.exists(cal_data['base_dir']) is False:
         continue

      cal_img = cv2.imread(cal_data['cal_image_file'])
      if cal_img is None:
         cmd = "rm " + cal_data['base_dir']
         print(cmd)
         exit()
      gray_cal_img = cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)

      if cam_id not in stats:
         stats[cam_id] = {}
         stats[cam_id]['total_stars'] = []
         stats[cam_id]['total_res_px'] = []
         stats[cam_id]['stars_found'] = []
      if cam_id in mask_imgs:
         #print(cal_img.shape, mask_imgs[cam_id].shape)
         gray_cal_img = cv2.subtract(gray_cal_img, mask_imgs[cam_id])
      else:
         print("NO MASK", cam_id)
         exit()
      cal_img = cv2.cvtColor(gray_cal_img, cv2.COLOR_GRAY2BGR)
      cal_json_file = cal_data['cal_image_file'].replace(".png", "-calparams.json")
      try:
         cal_params = load_json_file(cal_json_file)
      except:
         print(cal_json_file, "FILE IS BAD")
         reset_cal_file(station_id, cal_id)
         exit()

      if "star_points" not in cal_params :
         star_points, show_img = get_star_points(cal_data['cal_image_file'], cal_img, cal_params, station_id, cam_id, json_conf)
         cal_params['star_points'] = star_points
         save_json_file(cal_json_file, cal_params)
      else:
         star_points = cal_params['star_points']

     # for star in cal_params['cat_image_stars']:
     #    dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
     #    print(six, siy)
         #cv2.circle(show_img, (int(six),int(siy)), 25, (0,0,250),2)

      if cal_data['total_stars'] > 0 and len(star_points) > 0:
         stars_found = round((cal_data['total_stars'] / len(star_points)) * 100, 2)
      else:
         stars_found = 0
      cal_fn = cal_data['cal_image_file'].split("/")[-1]
      cal_fn = cal_fn.replace("-stacked.png", "")
      if math.isnan(stars_found) is True :
         stars_found = 0
      if math.isnan(cal_data['total_res_px']) is True :
         cal_data['total_res_px'] = 999


      print(cal_fn, len(star_points), cal_data['total_stars'], str(stars_found) + "%" , round(cal_data['total_res_px'],3) )
      freecal_index[cal_file]['star_points'] = len(star_points)
      freecal_index[cal_file]['star_found'] = stars_found 

      stats[cam_id]['total_stars'].append(cal_data['total_stars'])
      stats[cam_id]['stars_found'].append(stars_found)
      stats[cam_id]['total_res_px'].append(cal_data['total_res_px'])
      if cc > 100:
         continue
      cc += 1

      #cv2.imshow('pepe', show_img)
   for cam_id in stats:
      if type(stats[cam_id]) is not dict:
         continue
      print(cam_id, stats[cam_id])
      print(cam_id, stats[cam_id]['total_stars'])
      if len(stats[cam_id]['total_stars']) > 0:
         print("c1", cam_id, 
              np.median(stats[cam_id]['total_stars']),
              np.median(stats[cam_id]['stars_found']),
              np.median(stats[cam_id]['total_res_px']),
          )
      else:
         print(cam_id, "missing stats")
      stats[cam_id]['med_stars'] = np.median(stats[cam_id]['total_stars'])
      stats[cam_id]['med_stars_found'] = np.median(stats[cam_id]['stars_found'])
      stats[cam_id]['med_res'] = np.median(stats[cam_id]['total_res_px'])
   return(stats)

def reset_cal_file(station_id, cal_id):
   # cal_id should be the freecal dir. all other files are dervived from it. 
   today = datetime.date.today()
   year = today.strftime("%Y")
   reset = 1
   cal_dir = "/mnt/ams2/cal/freecal/" + cal_id + "/"
   bad_cal_dir = "/mnt/ams2/cal/bad_cals/" + cal_id + "/"
   stack_file = cal_dir + cal_id + "-stacked.png"
   
   # copy the source png back to the cal-in dir and hope it gets processed correctly the 'next' time.
   cal_in_dir = "/mnt/ams2/meteor_archive/" + station_id + "/CAL/AUTOCAL/" + year + "/" 
   cmd1 = "cp " + stack_file + " " + cal_in_dir + cal_id + ".png"
   print(cmd1)
   if os.path.exists(bad_cal_dir) is False:
      print("mkdirs " + bad_cal_dir)
      os.makedirs(bad_cal_dir) 
 
   # move the freecal dir to the badcals (as backup in case we later need to recover it)
   cmd2 = "mv " + cal_dir + "* " + bad_cal_dir
   print(cmd2)
   os.system(cmd2)

   # remove the free cal dir
   cmd3 = "rm " + cal_dir 
   print(cmd3)
   os.system(cmd2)

   os.system(cmd3)

   #

def anchor_cal(cam_id, con, cur, json_conf):
   freecal_index = load_json_file("/mnt/ams2/cal/freecal_index.json") 
   fns = []
   azs = []
   els = []
   pos = []
   pxs = []
   stars = []
   res= []
   groups = {}
   for cal_file in sorted(freecal_index.keys(), reverse=True):
      cal_data = freecal_index[cal_file]
      if cal_data['cam_id'] != cam_id:
         continue
      gkey = str(int(cal_data['center_az'])) + "_" + str(int(cal_data['center_el'])) + "_" + str(int(cal_data['position_angle'])) + "_" + str(int(cal_data['pixscale'])) 
      cal_fn = cal_file.split("/")[-1]
      cal_date = cal_fn[0:10]
      if gkey not in groups:
         groups[gkey] = {}
         groups[gkey]['cal_dates'] = []
      groups[gkey]['cal_dates'].append(cal_date)
      fns.append(cal_fn)
      azs.append(cal_data['center_az'])
      els.append(cal_data['center_el'])
      pos.append(cal_data['position_angle'])
      pxs.append(cal_data['pixscale'])
      res.append(cal_data['total_res_px'])
      stars.append(cal_data['total_stars'])

   min_az = min(azs)
   max_az = max(azs)
   med_az = np.median(azs)

   min_el = min(els)
   max_el = max(els)
   med_el = np.median(els)

   min_pos = min(pos)
   max_pos = max(pos)
   med_pos = np.median(pos)

   min_pxs = min(pxs)
   max_pxs = max(pxs)
   med_pxs = np.median(pxs)

   min_res = min(res)
   max_res = max(res)
   med_res = np.median(res)

   min_stars = min(stars)
   max_stars = max(stars)
   med_stars = np.median(stars)




   print("AZS", min_az, max_az, med_az)
   print("ELS", min_el, max_el, med_el)
   print("POS", min_pos, max_pos, med_pos)
   print("PXS", min_pxs, max_pxs, med_pxs)
   print("STARS", min_stars, max_stars, med_stars)
   print("RES", min_res, max_res, med_res)
   for gkey in groups:
      print(gkey, groups[gkey])
   all_data = {}
   all_data['azs'] = azs
   all_data['els'] = els 
   all_data['pos'] = pos 
   all_data['pxs'] = pxs 
   all_data['groups'] = groups 
   anchor_file = "/mnt/ams2/cal/{:s}_{:s}_ANCHOR.json".format(json_conf['site']['ams_id'], cam_id)


   save_json_file(anchor_file, all_data)
   print("saved", anchor_file)
   return(all_data) 


def perfect_cal(cam_id, con, cur, json_conf):
   # this function will perfect the calibration 
   # by running the wizard, apply functions, prune and purge functions
   # over and over until the optimal calib is reached
   print("Perfect cal")
   log = {}
   log['start_time'] = time.time()

   # prune if needed
   cal_status_report(cam_id, con, cur, json_conf)

   # prune if needed
   prune(cam_id, con, cur, json_conf)

   # get quality report
   quality_report = quality_check_all_cal_files(cam_id, con, cur)

   # run the wizard 
   wizard(station_id, cam_id, con, cur, json_conf, 25)

   # run the batch_apply
   batch_apply_bad(cam_id, con, cur, json_conf, None, True)

   # run the wizard again
   #wizard(station_id, cam_id, con, cur, json_conf, 25)

   # apply results to bad
   #batch_apply_bad(cam_id, con, cur, json_conf)

   cal_status_report(cam_id, con, cur, json_conf)



def optimize_var_new(var_name, cal_fn, cp,json_conf,rval,percision, cal_img,mcp=None):
   print("OPTIMIZE :", var_name)
   current_value = cp[var_name]
   start_val = cp[var_name]

   cp['cat_image_stars'] = pair_star_points(cal_fn, cal_img, cp.copy(), json_conf, con, cur, mcp, save_img = False)
   cp['cat_image_stars'] = remove_bad_stars(cp['cat_image_stars'])
   cp, bad_stars, marked_img = eval_cal_res(cal_fn, json_conf, cp.copy(), cal_img,None,None,cp['cat_image_stars'])

   star_img = draw_star_image(cal_img.copy(), cp['cat_image_stars'],cp, json_conf, "") 
   if SHOW == 1:
      cv2.imshow('pepe', star_img)
      cv2.waitKey(30)



   start_res = cp['total_res_px']
   best_res = start_res 
   best_val = current_value 
   best_score = len(cp['cat_image_stars']) / (best_res * .5)

   if "x_poly" not in cp: 
      print("NO XPOLY")
      exit()
      cp['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cp['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cp['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cp['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   orig_cp = cp.copy()
  
   tcal = cp.copy()
   go = 0 
   inc = .01
   count = 1
   last_res = 0
   while go < 5:
      #val = tcal[var_name] + (inc)
      val = best_val + (inc)
      if var_name == "position_angle" and val > 360:
         val = val - 360
      tcal[var_name] = val
      tcal = update_center_radec(cal_fn,tcal,json_conf)
      #tcal['ra_center'] = float( tcal['ra_center'])
      #tcal['dec_center'] = float( tcal['dec_center'])
      tcal['cat_image_stars'] = pair_star_points(cal_fn, cal_img, tcal.copy(), json_conf, con, cur, mcp, save_img = False)
      tcal['cat_image_stars'] = remove_bad_stars(tcal['cat_image_stars'])
      tcal, bad_stars, marked_img = eval_cal_res(cal_fn, json_conf, tcal.copy(), cal_img,None,None,tcal['cat_image_stars'])
      tres = tcal['total_res_px']
      score = len(tcal['cat_image_stars']) / tres
      #if tres < best_res:
      if score > best_score:
         print("\tBETTER SCORE START/THIS", go, count, inc, var_name, val, start_res, tres, score)
         best_res = tres 
         best_val = val
         if go % 2 == 0:
            inc = inc * 1.5  
         go = go + 1
      else:
         print("\tWORSE SCORE START/THIS", go, count, inc, var_name, val, start_res, tres , score)
         inc = inc * -1
         #inc = inc * .5 
         if go % 2 == 0:
            inc = inc * 1.5 
         go = go + 1
         count = 0
      count += 1
      last_res = tres
      star_img = draw_star_image(cal_img.copy(), tcal['cat_image_stars'],tcal, json_conf, "") 
      if SHOW == 1:
         cv2.imshow('pepe', star_img)
         cv2.waitKey(30)

   cp[var_name] = best_val

   return(cp)

def optimize_var(var_name, cal_fn, cp,json_conf,rval,percision, cal_img,mcp=None):
   
   current_value = cp[var_name]
   start_res = cp['total_res_px']
   best_val = 9999
   if "x_poly" not in cp: 
      cp['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cp['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cp['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cp['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   orig_cp = cp.copy()
  
   tcal = cp.copy()

   low = int(-1 * rval )
   high = int(rval)
   best_cp = cp 
   best_var_val = None
   for i in range (low,high):
      val = i / percision 
      if var_name == "position_angle" and val > 360:
         val = val - 360
      tcal[var_name] = float(orig_cp[var_name]) + val
      #data = [cp_file, tcal['center_az'], tcal['center_el'], tcal['position_angle'], tcal['pixscale'], len(tcal['user_stars']), len(tcal['cat_image_stars']), tcal['total_res_px'],0]
      tcal = update_center_radec(cal_fn,tcal,json_conf)
      tcal['ra_center'] = float( tcal['ra_center'])
      tcal['dec_center'] = float( tcal['dec_center'])
      tcal['cat_image_stars'] = pair_star_points(cal_fn, cal_img, tcal.copy(), json_conf, con, cur, mcp, save_img = False)
      temp_cp, bad_stars, marked_img = eval_cal_res(cal_fn, json_conf, tcal.copy(), cal_img,None,None,tcal['cat_image_stars'])
      best_val = temp_cp['total_res_px'] 
      print("OPTIMIZE", var_name, val, temp_cp[var_name], len(temp_cp['cat_image_stars']), "STARS", temp_cp['total_res_px'], "RES PX")

      
      if temp_cp['total_res_px'] < best_val:
     
         print("\tBETTER", var_name, best_cp[var_name], temp_cp['total_res_px'])
         best_cp = temp_cp.copy()
         best_val = best_cp['total_res_px']
         best_var_val = temp_cp[var_name]
      #else:
      #   print("NOT BETTER THAN BEST VAL:", best_val , tcal[var_name], cp[var_name], len(temp_cp['cat_image_stars']), len(tcal['cat_image_stars']))

   if best_cp is None:
      best_cp = cp
      #print("NO BEST OPT USING ORG", var_name, best_cp[var_name], best_cp['total_res_px'])
   #else:
   #   print("BEST OPT", var_name, best_var_val, best_cp[var_name], best_cp['total_res_px'])
   return(best_cp)

def refit_summary(log):

   #([cam_id, ff, last_cp['center_az'], last_cp['center_el'], last_cp['ra_center'], last_cp['dec_center'], last_cp['position_angle'], last_cp['pixscale'], len(last_cp['cat_image_stars']), last_cp['total_res_px']])
   cam_stats = {}
   used = {}
   for row in log:
      cam_id, ff, az, el, ra, dec, pos, pxs, star_count, res_px = row
      if ff in used:
         continue
      if cam_id not in cam_stats:
         cam_stats[cam_id] = {}
         cam_stats[cam_id]['files'] = []
         cam_stats[cam_id]['azs'] = []
         cam_stats[cam_id]['els'] = []
         cam_stats[cam_id]['poss'] = []
         cam_stats[cam_id]['pixs'] = []
         cam_stats[cam_id]['stars'] = []
         cam_stats[cam_id]['res'] = []
      cam_stats[cam_id]['files'].append(ff)
      cam_stats[cam_id]['azs'].append(az)
      cam_stats[cam_id]['els'].append(el)
      cam_stats[cam_id]['poss'].append(pos)
      cam_stats[cam_id]['pixs'].append(pxs)
      cam_stats[cam_id]['stars'].append(star_count)
      cam_stats[cam_id]['res'].append(res_px)
      used[ff] = 1

   for cam_id in cam_stats:
      print()
      med_az = np.median(cam_stats[cam_id]['azs'])
      med_el = np.median(cam_stats[cam_id]['els'])
      med_pos = np.median(cam_stats[cam_id]['poss'])
      med_px = np.median(cam_stats[cam_id]['pixs'])
      med_stars = np.median(cam_stats[cam_id]['stars'])
      med_res = np.median(cam_stats[cam_id]['res'])
      print(cam_id, "FILES", "", cam_stats[cam_id]['files'])
      print(cam_id, "AZS", med_az, cam_stats[cam_id]['azs'])
      print(cam_id, "ELS", med_el, cam_stats[cam_id]['els'])
      print(cam_id, "POS", med_pos, cam_stats[cam_id]['poss'])
      print(cam_id, "PX", med_px, cam_stats[cam_id]['pixs'])
      print(cam_id, "STARS", med_stars, cam_stats[cam_id]['stars'])
      print(cam_id, "RES", med_res, cam_stats[cam_id]['res'])
      print()
   return(cam_stats)

def star_track(cam_id, date, con, cur, json_conf ):
   y,m,d = date.split("_")
   st_dir = "/mnt/ams2/cal/startrack/" + y + "/"
   st_file = st_dir + cam_id + "_" + date  + ".json"
   if os.path.exists(st_dir) is False:
      os.makedirs(st_dir)
   if os.path.exists(st_file):
      stdata = load_json_file(st_file)
   else:
      stdata = {}

   MM = MovieMaker()
   station_id = json_conf['site']['ams_id']
   wild = "/mnt/ams2/HD/" + date + "*" + cam_id + "*.mp4"
   hd_files = glob.glob(wild)

   autocal_dir = "/mnt/ams2/cal/" 
   mcp = None
   if mcp is None:
      mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
      if os.path.exists(mcp_file) == 1:
         mcp = load_json_file(mcp_file)
         # reset mcp if it is bad

   #mcp = None
   cal_params = None
   extra_text = ""
   lc = 0
   last_az = None
   for hdf in sorted(hd_files, reverse=False):
      print(lc, lc % 5)
      if lc % 5 != 1:
         lc += 1
         continue 
      snap_file, snap_img = MM.make_snap(hdf, 1920,1080)
      brightness = np.mean(snap_img)
      snap_fn = snap_file.split("/")[-1]
      extra_text = snap_fn 
      #if cal_params is None:
      #if snap_fn in stdata:
      #   [cal_params['ra_center'], cal_params['dec_center'], cal_params['center_az'], cal_params['center_az'], cal_params['position_angle'], cal_params['pixscale'], total_stars, cal_params['total_res_px']]= stdata[snap_fn] 
         #cal_params = update_center_radec(snap_file,cal_params,json_conf)

      #if cal_params is None:
      cal_params = get_default_cal_for_file(cam_id, snap_file, None, con, cur, json_conf)

      if cal_params is None:
         # the cal params don't exist yet!
         cal_params = {}
         cal_params['center_az'] = 1
         cal_params['center_el'] = 25
         cal_params['position_angle'] = 180
         cal_params['pixscale'] = 156 
         cal_params['user_stars'] = []
         cal_params['cat_image_stars'] = []
         cal_params['total_res_px'] = 999
         cal_params['total_res_deg'] = 999

      if False: #last_az is not None:
         cal_params['center_az'] = last_az
         cal_params['center_el'] = last_el
         cal_params['position_angle'] = last_pos
         cal_params['pixscale'] = last_pxs
      
      cal_params = update_center_radec(snap_file,cal_params,json_conf)
      print(hdf, snap_file, cal_params['center_az'], cal_params['center_el'], cal_params['ra_center'], cal_params['dec_center'])



      star_points, show_img = get_star_points(snap_file, snap_img, cal_params, station_id, cam_id, json_conf)

      cal_params['user_stars'] = star_points

      cal_params['cat_image_stars'] = pair_star_points(snap_file, snap_img, cal_params, json_conf, con, cur, mcp, True)
      cal_params, bad_stars, marked_img = eval_cal_res(snap_file, json_conf, cal_params.copy(), snap_img,None,None,cal_params['cat_image_stars'])

      stars,cat_stars = get_paired_stars(snap_file, cal_params, con, cur)
      cal_params, bad_stars, marked_img = eval_cal_res(snap_file, json_conf, cal_params.copy(), snap_img,None,None,cal_params['cat_image_stars'])


      star_img = draw_star_image(snap_img.copy(), cal_params['cat_image_stars'],cal_params, json_conf, extra_text) 
      cv2.putText(star_img, str(brightness),  (int(50),int(50)), cv2.FONT_HERSHEY_SIMPLEX, .8, (200,200,200), 1)
      if SHOW == 1:
         cv2.imshow('pepe', star_img)
         cv2.waitKey(30)


      cal_params['cat_image_stars'] = remove_bad_stars(cal_params['cat_image_stars'])

      #star_points, show_img = get_star_points(snap_file, snap_img, cal_params, station_id, cam_id, json_conf)
      extra_text = snap_fn + " " + str(int(brightness))
      if len(cal_params['cat_image_stars']) > 5:
         cal_params, cat_stars = recenter_fov(snap_file, cal_params, snap_img.copy(),  stars, json_conf, extra_text, con, cur)
         cal_params = update_center_radec(snap_file,cal_params,json_conf)
         cal_params['cat_image_stars'] = pair_star_points(snap_file, snap_img, cal_params, json_conf, con, cur, mcp, True)

      #cal_params['cat_image_stars'] = cat_star_match(snap_fn, cal_params, snap_img, cat_stars)
      #cal_params['cat_image_stars'] = remove_bad_stars(cal_params['cat_image_stars'])

      if len(cal_params['cat_image_stars']) > 5:
         cal_params, cat_stars = recenter_fov(snap_file, cal_params, snap_img.copy(),  stars, json_conf, extra_text, con, cur)
         cal_params['cat_image_stars'] = cat_star_match(snap_fn, cal_params, snap_img, cat_stars)
      #stars,cat_stars = get_paired_stars(snap_file, cal_params, con, cur)
      #print(cat_stars)

      cal_params['cat_image_stars'] = remove_bad_stars(cal_params['cat_image_stars'])
      cal_params, bad_stars, marked_img = eval_cal_res(snap_file, json_conf, cal_params.copy(), snap_img,None,None,cal_params['cat_image_stars'])
      #cal_params, cat_stars = recenter_fov(snap_file, cal_params, snap_img.copy(),  stars, json_conf, "")
      #cal_params['cat_image_stars'] = pair_star_points(snap_file, snap_img, cal_params, json_conf, con, cur, mcp, True)
      
      #cal_params['cat_image_stars'] = remove_bad_stars(cal_params['cat_image_stars'])
      last_az = cal_params['center_az']
      last_el = cal_params['center_el']
      last_pos = cal_params['position_angle']
      last_pxs= cal_params['pixscale']
      star_img = draw_star_image(snap_img.copy(), cal_params['cat_image_stars'],cal_params, json_conf, extra_text) 
      cv2.putText(star_img, str(brightness),  (int(50),int(50)), cv2.FONT_HERSHEY_SIMPLEX, .8, (200,200,200), 1)
      if SHOW == 1:
         cv2.imshow('pepe', snap_img)
         cv2.waitKey(30)

      stdata[snap_fn] = [cal_params['ra_center'], cal_params['dec_center'], cal_params['center_az'], cal_params['center_az'], cal_params['position_angle'], cal_params['pixscale'], len(cal_params['cat_image_stars']), cal_params['total_res_px']]
      if lc % 20 == 0:
         save_json_file(st_file, stdata)
      lc += 1
   save_json_file(st_file, stdata)



def remove_mask_stars(cat_image_stars, mask_img):
   good = []
   bad = []
   if len(mask_img.shape) == 3:
      mask_img = cv2.cvtColor(mask_img, cv2.COLOR_BGR2GRAY)
   for star in cat_image_stars:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      y = int(siy)
      x = int(six)
 
      if mask_img[y,x] == 0:
         bad.append(star)
      else:
         good.append(star)
   return(good, bad)


def remove_bad_stars(cat_image_stars):
   # 
   good = []
   bad = []
   left_side = []
   right_side = []
   close = []
   far = []
   rez = np.median([row[-2] for row in cat_image_stars])

   # group each star to left or right and near or far from center
   for star in cat_image_stars:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      center_dist = calc_dist((960,540),(six,siy))

      if six < 1920 / 2:
         left_side.append(cat_dist)
      else:
         right_side.append(cat_dist)
      if center_dist < 600:
         close.append(cat_dist)
      else:
         far.append(cat_dist)
   if len(left_side) > 3:
      left_res = np.median(left_side) 
   else:
      left_res = 10 
   if len(right_side) > 3:
      right_res = np.median(right_side) 
   else:
      right_res = 10

   if len(far) > 3:
      far_res = np.median(far)
   else:
      far_res = 25

   if len(close) > 3:
      close_res = np.median(close)
   else:
      close_res = 5


   for star in cat_image_stars:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      center_dist = calc_dist((960,540),(six,siy))
      x_res = abs(six - new_cat_x)
      y_res = abs(siy - new_cat_y)
      if center_dist < 600:
         dist = "close"
      else:
         dist = "far"
      if six < 1920/2:
         side = "left"
      else:
         side = "right"
      if side == "left":
         res_limit = left_res
      else:
         res_limit = right_res
      if dist == "close" and res_limit < close_res:
         res_limit = close_res
      if dist == "far" and res_limit < far_res:
         res_limit = far_res


      if center_dist < 600:
         factor = 2
      else:
         factor = 5

      if center_dist > 600 and cat_dist > 15:
         if y_res > x_res :
            bad.append(star)
            continue
         # reject bad side matches
         if side == "left":
            if new_cat_x > six:
               print("\t\tCAT X on wrong side of star for being on the left!", new_cat_x, six)
               bad.append(star)
               continue
         else:
            if new_cat_x < six:
               print("\t\tCAT X on wrong side of star for being on the right!", new_cat_x, six)
               bad.append(star)
               continue
      if star_int == None:
         bad.append(star)
         continue
      if mag >= 4 and star_int > 1400 or star_int < 50:
         #print("\t\tBad mag/star int!", mag, star_int)
         bad.append(star)
         continue

      if cat_dist < (res_limit * factor):
         good.append(star)
      else:
         bad.append(star)

   try:
      avg_res = (left_res + right_res + close_res + far_res) / 4
   except:
      print("AVG RES CALC FAILED")
      avg_res = 99
   #print("   RES LEFT      :", left_res)
   #print("   RES RIGHT     :", right_res)
   #print("   RES CENTER    :", close_res)
   #print("   RES EDGES     :", far_res)
   #print("   RES AVG       :", avg_res)
   #print("   GOOD/BAD STARS:", len(good)," / ", len(bad))
   return(good)

def plot_cal_history(con, cur, json_conf):
   import matplotlib
   matplotlib.use('Agg')
   import matplotlib.pyplot as plt 
   from matplotlib.pyplot import figure 

   calindex_file = "/mnt/ams2/cal/freecal_index.json"
   cal_dir = "/mnt/ams2/cal/"
   if os.path.exists(calindex_file) is True:
      try:
         calindex = load_json_file(calindex_file)
      except:
         print("FAILED TO LOAD:", calindex_file)
   data = {}
   for key in calindex:
      row = calindex[key]
      fn = key.split("/")[-1]
      print("ROW", type(row), row )
      if "cam_id" not in row:
         continue
      if row['cam_id'] not in data:
         data[row['cam_id']] = {}
         data[row['cam_id']]['fns'] = []
         data[row['cam_id']]['dates'] = []
         data[row['cam_id']]['azs'] = []
         data[row['cam_id']]['els'] = []
         data[row['cam_id']]['pos'] = []
         data[row['cam_id']]['pxs'] = []
         data[row['cam_id']]['stars'] = []
         data[row['cam_id']]['res'] = []
      data[row['cam_id']]['fns'].append(fn)
      data[row['cam_id']]['dates'].append(row['cal_date'])
      data[row['cam_id']]['azs'].append(float(row['center_az']))
      data[row['cam_id']]['els'].append(float(row['center_el']))
      data[row['cam_id']]['pos'].append(float(row['position_angle']))
      data[row['cam_id']]['pxs'].append(float(row['pixscale']))
      data[row['cam_id']]['stars'].append(float(row['total_stars']))
      data[row['cam_id']]['res'].append(float(row['total_res_px']))


   for cam_id in data:
      #print(cam_id, data[cam_id])
      fig, (ax1, ax2, ax3) = plt.subplots(1,3)
      fig.set_size_inches(12,4)
      fig.tight_layout(pad=5.0)
      ax1.scatter(data[cam_id]['azs'],data[cam_id]['els'])
      ax1.set_xlabel("Azimuth")
      ax1.set_ylabel("Elevation")
      fig.suptitle("Calibration History for " + station_id + "-" + cam_id  , fontsize=16)

      ax2.scatter(data[cam_id]['pos'],data[cam_id]['pxs'])
      ax2.set_xlabel("Position Angle")
      ax2.set_ylabel("Pixel Scale")

      ax3.scatter(data[cam_id]['stars'],data[cam_id]['res'])
      ax3.set_xlabel("Total Stars")
      ax3.set_ylabel("Residual Error (PXs)")
      plot_file = cal_dir + "plots/" + station_id + "_" + cam_id + "_CAL_PLOTS.png"
      print("\tSAVED PLOT", plot_file)
      fig.savefig(plot_file, dpi=72)
      # convert to jpg
      plt_img = cv2.imread(plot_file)
      plot_file_jpg = plot_file.replace(".png", ".jpg")
      cv2.imwrite(plot_file_jpg , plt_img)
      if os.path.exists(plot_file):
         os.system("rm " + plot_file)
      #plt.show()
      cloud_file = "/mnt/archive.allsky.tv/" + station_id + "/CAL/plots/" + station_id + "_" + cam_id + "_CAL_PLOTS.jpg"
      cloud_png_file = "/mnt/archive.allsky.tv/" + station_id + "/CAL/plots/" + station_id + "_" + cam_id + "_CAL_PLOTS.png"
      cloud_plot_dir = "/mnt/archive.allsky.tv/" + station_id + "/CAL/plots/" 
      if os.path.exists(cloud_plot_dir) is False:
         os.makedirs(cloud_plot_dir)
      if os.path.exists(cloud_png_file):
         os.system("rm " + cloud_png_file)
      os.system("cp " + plot_file_jpg + " " + cloud_file)
      #print("cp " + plot_file_jpg + " " + cloud_file)

   all_imgs = []
   for cam_id in sorted(data):
      plot_file = cal_dir + "plots/" + station_id + "_" + cam_id + "_CAL_PLOTS.png"
      if os.path.exists(plot_file) is True:
         img = cv2.imread(plot_file)
         ih,iw = img.shape[:2]
         all_imgs.append(img)
      else:
         iw = 1920
         ih = 1080 
   mh = ih * len(all_imgs) + ih
   c = 0
   all_img = np.zeros((mh,iw,3),dtype=np.uint8)
   for img in all_imgs:
      img = cv2.resize(img,(iw,ih))
      y1 = ih * c
      y2 = y1 + ih
      x1 = 0
      x2 = x1 + iw
      all_img[y1:y2,x1:x2] = img
      c += 1
   #cv2.imshow('pepe', all_img)


def plot_refit_meteor_day(meteor_day, con, cur, json_conf):
   print("plot_refit_meteor_day:", meteor_day)
   import matplotlib.pyplot as plt 
   from matplotlib.pyplot import figure 
   meteor_dir = "/mnt/ams2/meteors/" + meteor_day + "/" 
   refit_log_file = "/mnt/ams2/meteors/" + meteor_day + "/refit.log"
   if os.path.exists(refit_log_file):
      mets = load_json_file(refit_log_file)
   else:
      mets = []
   for cam_num in json_conf['cameras']:
      cam_id = json_conf['cameras'][cam_num]['cams_id']
      azs = []
      els = []
      pos = []
      pxs = []
      stars = []
      res = []
      for met in mets:
         cd, ff, center_az, center_el, ra_center, dec_center, position_angle, pixscale, total_stars, total_res_px = met
         if cam_id == met[0]:
            azs.append(center_az)
            els.append(center_el)
            pos.append(position_angle)
            pxs.append(pixscale)
            stars.append(total_stars)
            res.append(total_res_px)

      print("\nCAM:", cam_id)
      print("AZs:", azs)
      print("ELs:", els)
      print("POSs:", pos)
      print("PXSs:", pxs)
      print("STARs:", stars)
      print("RESs:", res)
      fig, (ax1, ax2, ax3) = plt.subplots(1,3)
      fig.set_size_inches(12,4)
      fig.tight_layout(pad=5.0)
      ax1.scatter(azs,els)
      ax1.set_xlabel("Azimuth")
      ax1.set_ylabel("Elevation")
      fig.suptitle("Meteor Calibrations for " + station_id + "-" + cam_id + " on " + meteor_day, fontsize=16)

      ax2.scatter(pos,pxs)
      ax2.set_xlabel("Position Angle")
      ax2.set_ylabel("Pixel Scale")

      ax3.scatter(stars,res)
      ax3.set_xlabel("Total Stars")
      ax3.set_ylabel("Residual Error (PXs)")
      plot_file = meteor_dir + station_id + "_" + cam_id + "_CAL_" + meteor_day + ".png"
      print("\tSAVED PLOT", plot_file)
      fig.savefig(plot_file, dpi=72)
      plt.show()

def timelapse_day_fast(meteor_day, con, cur, json_conf):
   global MOVIE_FRAME_NUMBER
   global MOVIE_FRAMES_TEMP_FOLDER 
   wdir = "/mnt/ams2/latest/" + meteor_day + "/"
   cams = []
   files = os.listdir(wdir)
   station_id = json_conf['site']['ams_id']
   cam_files = {}

   for cam_num in json_conf['cameras']:
      cams_id = json_conf['cameras'][cam_num]['cams_id']
      cam_files[cams_id] = []
      cams.append(cams_id)

      for f in sorted(files):
         if cams_id in f:
            print("LOADING:", f)
            cam_files[cams_id].append(f)

   #for cam_id in json_conf[

   for cam in sorted(cams):
      first_frame_file = wdir + cam_files[cam][0]
      first_frame = cv2.resize(cv2.imread(first_frame_file), (1920,1080))
      mcp_file = "/mnt/ams2/cal//multi_poly-{:s}-{:s}.info".format(station_id, cam)
      mcp = load_json_file(mcp_file)
      print(MOVIE_LAST_FRAME.shape)
      print(first_frame.shape)
      print(wdir + first_frame_file )
      if MOVIE_LAST_FRAME is not None:
         pref = "FF"
         start_count = 0
         extra = slide_left(MOVIE_LAST_FRAME, first_frame, pref, start_count)
         try:
            extra = slide_left(MOVIE_LAST_FRAME, first_frame, pref, start_count)
            print(len(extra))
         except:
            extra = []

         # Last sequence / transition slide left frames
         for eframe in extra:
            eframe = RF.watermark_image(eframe, RF.logo_320, logo_x,logo_y, .33, make_int=True)
            extra_text = meteor_day
            eframe = draw_star_image(eframe.copy(), [],mcp, json_conf, extra_text) 

            save_movie_frame(eframe, MOVIE_FRAME_NUMBER, MOVIE_FRAMES_TEMP_FOLDER)
            MOVIE_FRAME_NUMBER += 1
            if SHOW == 1:
               cv2.imshow('pepe', eframe)
               cv2.waitKey(30)


      for f in sorted(files):
         if cam in f:
            img_file = wdir + f
            eframe = cv2.imread(img_file)
            eframe = cv2.resize(eframe,(1920,1080))
            #eframe = RF.watermark_image(eframe, RF.logo_320, logo_x,logo_y, .33, make_int=True)

            eframe = draw_star_image(eframe.copy(), [],mcp, json_conf, extra_text) 

            save_movie_frame(eframe, MOVIE_FRAME_NUMBER, MOVIE_FRAMES_TEMP_FOLDER)
            MOVIE_FRAME_NUMBER += 1 
            if SHOW == 1:
               cv2.imshow('pepe', eframe)
               cv2.waitKey(30)



def refit_meteor_day(meteor_day, con, cur, json_conf):

   global MOVIE_FRAMES_TEMP_FOLDER
   global SAVE_MOVIE
   global MOVIE_FRAME_NUMBER

   if SHOW == 1:
      # set the windows
      cv2.namedWindow("pepe")
      cv2.resizeWindow("pepe", 1920, 1080)
      cv2.moveWindow("pepe", 1400,100)


   if os.path.exists(MOVIE_FRAMES_TEMP_FOLDER) is False:
      os.makedirs(MOVIE_FRAMES_TEMP_FOLDER)
   else:
      os.system("rm " + MOVIE_FRAMES_TEMP_FOLDER + "*.jpg")
   files = os.listdir(MOVIE_FRAMES_TEMP_FOLDER)
   print(len(files), "in the temp dir")

   make_intro(MOVIE_FRAMES_TEMP_FOLDER) 

   timelapse_day_fast(meteor_day, con, cur, json_conf)

   files = os.listdir("/mnt/ams2/meteors/" + meteor_day + "/")
   cc = 1
   for ff in files:
      if "json" not in ff:
         continue
      if "reduced" in ff:
         continue
      mjf = "/mnt/ams2/meteors/" + meteor_day + "/" + ff
      if os.path.exists(mjf) :
         mjrf = mjf.replace(".json", "-reduced.json")
         if os.path.exists(mjf) is True:
            try:
               mj = load_json_file(mjf)
            except:
               print("Problem! with", mjf )
               continue
         if os.path.exists(mjrf) is True:
            try:
               mjr = load_json_file(mjrf)
               mfd = mjr['meteor_frame_data']
            except:
               cmd = "rm " + mjrf
               print(cmd)
               os.system(cmd)
             
               mfd = []
         else:
            mfd = []
         if (os.path.exists(mjrf) is False or len(mfd) == 0) and "fireball_fail" not in mj:
            cmd = "./Process.py fireball " + ff.replace(".json", ".mp4")
            print(cmd)
            os.system(cmd)
         #if "refit" not in mj and "fireball_fail" not in mj : 
         if True:
            print(cc, "REFIT", mj.keys())
            refit_meteor(ff, con, cur, json_conf)
         else:
            print(cc, "SKIP REFIT DONE", ff)
         print("MFD", len(mfd)) 
      cc += 1

   print("Done day", meteor_day)
   mdir = "/mnt/ams2/meteors/" + meteor_day + "/"

   refit_log_file = mdir + "refit.log"
   refit_sum_file = mdir + "refit_summary.log"

   if os.path.exists(refit_log_file) is True:
      refit_log = load_json_file(refit_log_file)
      report = refit_summary(refit_log)
      save_json_file(refit_sum_file, report)
   vid_dir = "/mnt/ams2/day_summary/"
   if os.path.exists(vid_dir) is False:
      os.makedirs(vid_dir)
   cmd = "./FFF.py imgs_to_vid ~/REFIT_METEOR_FRAMES_TEMP/ 00 /mnt/ams2/day_summary/" + meteor_day + ".mp4 25 28"
   os.system(cmd)

def refit_meteor(meteor_file, con, cur, json_conf, mcp = None, last_best_dict = None):
   global RF
   global MOVIE_FRAME_NUMBER
   global MOVIE_FRAMES_TEMP_FOLDER
   global SAVE_MOVIE 
   '''
       Refit meteor -- this function should optimize the calibration, selected stars, and perfect the meteors x,y points
       When complete all frames should have the latest / greatest calib applied to them. 
       In the cases where there are not enough stars (< 3) to safely confirm the calibration residuals, 
       the default or last best calibration will be used as a fall back. 

       So we should : 
          1) Get the user stars
          2) Get the current calib
             Use default calib if not enough stars else
          4) Recenter
          5) Appy Calib to frames

   '''
   print("Refit Meteor File", meteor_file, MOVIE_FRAME_NUMBER)
   frames = []
   # meteor_file should end with .json and have no path info
   if "/" in meteor_file:
      meteor_file = meteor_file.split("/")[-1]
   if ".mp4" in meteor_file:
      meteor_file = meteor_file.replace(".mp4", ".json")
   
   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(meteor_file)
   station_id = json_conf['site']['ams_id']

   

   # MRH - Possible bug / this should be checked or convert to 'last_best'? 3/16/23 
   default_cp = get_default_cal_for_file(cam_id, meteor_file, None, con, cur, json_conf)
   if default_cp is None:
      # cant refit if there is no default cp!
      return()

   extra_text = "Refit " +  meteor_file.split("-")[0]
   if last_best_dict is None:
      last_best_dict = {}

   autocal_dir = "/mnt/ams2/cal/" 

   # load the MCP if it exists
   if mcp is None:
      mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
      if os.path.exists(mcp_file) == 1:
         mcp = load_json_file(mcp_file)
         # reset mcp if it is bad
         if "x_fun" not in mcp :
            mcp = None
         elif mcp['x_fun'] > 5:
            mcp = None

   # setup dirs and filenames 
   day = meteor_file[0:10]
   mdir = "/mnt/ams2/meteors/" + day + "/" 
   fit_img_file = mdir + meteor_file.replace(".json", "-rfit.jpg")
   sd_vid = "/mnt/ams2/meteors/" + day + "/" + meteor_file.replace(".json", ".mp4")
   json_file = "/mnt/ams2/meteors/" + day + "/" + meteor_file #.replace(".mp4", ".json")
   red_json_file = "/mnt/ams2/meteors/" + day + "/" + meteor_file.replace(".json", "-reduced.json")
   stack_file = json_file.replace(".json", "-stacked.jpg")


   # load reduced json.
   orig_res = 999
   start_datetime = None
   if os.path.exists(red_json_file):
      mjr = load_json_file(red_json_file)
      meteor_roi = mfd_roi(mjr['meteor_frame_data'])
      if "meteor_frame_data" in mjr:
         print("MJR", mjr['meteor_frame_data'][0][0])
         start_datetime = mjr['meteor_frame_data'][0][0]
   else:
      # if reduced file doesn't exist try to make it
      meteor_roi = None
      mjr = None

      cmd = "./Process.py fireball " + meteor_file
      os.system(cmd)
      if os.path.exists(red_json_file):
         mjr = load_json_file(red_json_file)
         meteor_roi = mfd_roi(mjr['meteor_frame_data'])

   # load meteor json file
   hd_frames = []
   if os.path.exists(json_file):
      try:
         mj = load_json_file(json_file)
      except:
         # corrupt mj remake!
         os.system("rm " + json_file)
         os.system("./Process.py fireball " + meteor_file) 
      try:
         mj = check_for_nan(json_file, mj)
      except:
         # meteor file is corrupt or empty re-run the reduce process on it
         os.system("rm " + json_file)
         os.system("./Process.py fireball " + meteor_file) 
         mj = load_json_file(json_file)

      if "hd_trim" in mj:
         if os.path.exists(mj['hd_trim']) is True:
            sd_frames = load_frames_simple(sd_vid)
            hd_frames = load_frames_simple(mj['hd_trim'])
         elif os.path.exists(sd_vid) is True:
            sd_frames = load_frames_simple(sd_vid)
            hd_frames = sd_frames
         else:
            sd_frames = load_frames_simple(sd_vid)
            hd_frames = sd_frames
            print("ERROR NO VIDEO FRAMES!", sd_vid)
            input("ABORT")
            return()
      elif os.path.exists(sd_vid) is True:
         sd_frames = load_frames_simple(sd_vid)
         hd_frames = sd_frames
      else:
         sd_frames = load_frames_simple(sd_vid)
         hd_frames = sd_frames
         print("ERROR NO VIDEO FRAMES!", sd_vid)
         return()

   # check mj against mcp
   if mcp is not None:
      if "cp" not in mj:
         mj['cp'] = mcp 
         mj['cp'] = update_center_radec(meteor_file,mcp,json_conf)
      if mj['cp']['x_poly'][0] != mcp['x_poly'][0]:
         mj['cp']['x_poly'] = mcp['x_poly']
         mj['cp']['y_poly'] = mcp['y_poly']
         mj['cp']['x_poly_fwd'] = mcp['x_poly_fwd']
         mj['cp']['y_poly_fwd'] = mcp['y_poly_fwd']

   if len(hd_frames) > 0:
      frames = hd_frames
   if "refit" in mj:
      # refit is already done, just return 
      print("DONE REFIT ALREADY!")
      #return(mj['cp'])

   # by here all frames SD and HD and json data should be loaded

   # make the median frame for star astrometry and photemetry 
   median_frame = cv2.convertScaleAbs(np.median(np.array(hd_frames[0:10]), axis=0))
   median_frame = cv2.resize(median_frame, (1920,1080))

   # subtract mask from med frame
   median_frame = subtract_mask(median_frame, station_id, cam_id)
   extra_text = "Median Frame"
   print("E:", extra_text, median_frame.shape, median_frame[0,0] )
   median_frame   = draw_star_image(median_frame.copy(), [],mj['cp'], json_conf, extra_text) 
   # load meteor image
   if os.path.exists(stack_file) is True:
      meteor_stack_img = cv2.imread(stack_file)
      meteor_stack_img = cv2.resize(meteor_stack_img,(1920, 1080))
   else:
      meteor_stack_img = None
   if start_datetime is None:
      start_datetime = f_date_str
   extra_text = "Meteor Stack " + start_datetime 
   meteor_stack_img = draw_star_image(meteor_stack_img.copy(), [],mj['cp'], json_conf, extra_text) 

   #if SHOW == 1: 
   #   cv2.imshow('pepe', median_frame)
   #   cv2.waitKey(30)
   logo_x = 1550 
   logo_y = 950 
   if MOVIE_LAST_FRAME is not None:
      pref = "FF" 
      start_count = 0
      try:
         extra = slide_left(MOVIE_LAST_FRAME, median_frame, pref, start_count)
         print(len(extra))
      except:
         extra = []
      
      # Last sequence / transition slide left frames
      for eframe in extra:
         eframe = RF.watermark_image(eframe, RF.logo_320, logo_x,logo_y, .33, make_int=True)
         save_movie_frame(eframe, MOVIE_FRAME_NUMBER, MOVIE_FRAMES_TEMP_FOLDER)
         MOVIE_FRAME_NUMBER += 1 
         if SHOW == 1:
            cv2.imshow('pepe', eframe)
            cv2.waitKey(30)



   if SAVE_MOVIE is True:
      print("MOVIE_FRAME_NUMBER:", MOVIE_FRAME_NUMBER)
      MOVIE_FRAME_NUMBER += 1
      meteor_stack_img = RF.watermark_image(meteor_stack_img, RF.logo_320, logo_x,logo_y, .33, make_int=True)
      save_movie_frame(meteor_stack_img, MOVIE_FRAME_NUMBER, MOVIE_FRAMES_TEMP_FOLDER, 10)


   stack_img = median_frame

   # highlight the ROI if it exists 
   if meteor_roi is not None:
      x1,y1,x2,y2 = meteor_roi
      color = (255,255,255)
      cv2.rectangle(meteor_stack_img, (int(x1), int(y1)), (int(x2) , int(y2) ), color, 2)

   if True:
      # if the CP has not been assigned to the meteor give it the default cal
      if "cp" not in mj:
         cp = default_cp #get_default_cal_for_file(cam_id, meteor_file, None, con, cur, json_conf)
         if cp is None:
            print("CAN'T REFIT!")
            return(None) 
         mj['cp'] = cp

      # get cals before/after this file
      before_files, after_files = get_close_calib_files(meteor_file)
      star_points, show_img = get_star_points(meteor_file, stack_img, mj['cp'], station_id, cam_id, json_conf)
      mj['cp']['user_stars'] = star_points
      mj['cp']['star_points'] = star_points

      # try to find a better cal if the res is high 
      # but only if there are enough stars
      if "total_res_px" not in mj['cp']:
         mj['cp']['total_res_px'] = 999
      if mj['cp']['total_res_px'] > 4 and len(star_points) > 3:
         mj['cp'] = test_cals (meteor_file, mj['cp'], json_conf, mcp, meteor_stack_img, before_files, after_files, con, cur)

        

      if "total_res_px" not in mj['cp']:
         # There are no stars so there is no res??
         mj['cp']['total_res_px'] = 999
         mj['cp']['total_res_deg'] = 999

      if mj['cp']['total_res_px'] > 15:
         # res is too high, use the default
         if default_cp is None:
            return()
         mj['cp'] = default_cp #get_default_cal_for_file(cam_id, meteor_file, None, con, cur, json_conf)
         if "total_res_px" in mj['cp']: 
            print("USING DEFAULT CP! RES HIGH", mj['cp']['total_res_px'])
         print("OK")

   try:
      orig_res = mj['cp']['total_res_px']
   except:
      print("CP IS WACKED", meteor_file, mj['cp'])
      return()


   best_cal = find_best_calibration(meteor_file, mj['cp'], json_conf)
   if best_cal is not None:
      print("BEST CAL", len(mj['cp']['cat_image_stars']),  best_cal['total_res_px'])

   if best_cal is not None:
      if orig_res > best_cal['total_res_px']:
         mj['cp'] = best_cal 


   stars,cat_stars = get_paired_stars(meteor_file, mj['cp'], con, cur)

   show_frame = median_frame.copy()


   if SAVE_MOVIE is True:
      print("MOVIE_FRAME_NUMBER:", MOVIE_FRAME_NUMBER)
      MOVIE_FRAME_NUMBER += 1

      show_frame = RF.watermark_image(show_frame, RF.logo_320, logo_x,logo_y, .33, make_int=True)
      save_movie_frame(show_frame, MOVIE_FRAME_NUMBER, MOVIE_FRAMES_TEMP_FOLDER, 5)
      for star in mj['cp']['user_stars']:
         x,y,i = star
         cv2.circle(show_frame, (int(x),int(y)), 15, (128,255,128),1)
         save_movie_frame(show_frame, MOVIE_FRAME_NUMBER, MOVIE_FRAMES_TEMP_FOLDER)
         MOVIE_FRAME_NUMBER += 1
      save_movie_frame(show_frame, MOVIE_FRAME_NUMBER, MOVIE_FRAMES_TEMP_FOLDER, 5)

   if SHOW == 1:
      # frame with no markings just stars 
      show_frame = median_frame.copy()
      show_frame = RF.watermark_image(show_frame, RF.logo_320, logo_x,logo_y, .33, make_int=True)
      cv2.imshow('pepe', show_frame)
      cv2.waitKey(30)
      for star in mj['cp']['user_stars']:
         x,y,i = star
         cv2.circle(show_frame, (int(x),int(y)), 15, (128,255,128),1)
         cv2.imshow('pepe', show_frame)
         cv2.waitKey(30)
      # frame with white circles

   print("CAT STARS", len(mj['cp']['cat_image_stars']))
   if len(mj['cp']['cat_image_stars']) > 1:
      mj['cp'], cat_stars = recenter_fov(meteor_file, mj['cp'].copy(), stack_img.copy(),  stars, json_conf, meteor_file , None, None, con, cur)

      stars,cat_stars = get_paired_stars(meteor_file, mj['cp'], con, cur)
      print("CAT STARS", len(mj['cp']['cat_image_stars']))
      mj['cp']['cat_image_stars'] = pair_star_points(meteor_file, stack_img, mj['cp'], json_conf, con, cur, mcp, True)
      print("CAT STARS", len(mj['cp']['cat_image_stars']))
      #mj['cp'], bad_stars, marked_img = eval_cal_res(meteor_file, json_conf, mj['cp'].copy(), stack_img,None,None,mj['cp']['cat_image_stars'])


   else:
      print("There are not enough stars to recenter! We should use the last_best_calib / default calib for this file!")
      print("***********************************")
      print("******************************")
      print("*************************")
      print("********************")
      mj['cp'] = best_cal
      save_json_file(json_file, mj)      
      print("Using best cal")
      #return(mj['cp'])
      extra_text = "Not enough stars to refit"
      star_img = draw_star_image(median_frame.copy(), [],mj['cp'], json_conf, extra_text) 

   # ADD MORE STARS
   if meteor_stack_img is not None and mj['cp'] is not None:
      star_img = draw_star_image(meteor_stack_img.copy(), mj['cp']['cat_image_stars'],mj['cp'], json_conf, extra_text) 
   if meteor_stack_img is not None and mj['cp'] is not None:
      mj['cp'] = add_more_stars(fit_img_file, mj['cp'], median_frame, median_frame, json_conf)



   if meteor_stack_img is not None and mj['cp'] is not None:
      star_img = draw_star_image(meteor_stack_img.copy(), mj['cp']['cat_image_stars'],mj['cp'], json_conf, extra_text) 
      cv2.imwrite(fit_img_file, star_img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])

   if SAVE_MOVIE is True:
      print("MOVIE_FRAME_NUMBER:", MOVIE_FRAME_NUMBER)
      MOVIE_FRAME_NUMBER += 1
      show_frame = RF.watermark_image(meteor_stack_img, RF.logo_320, logo_x,logo_y, .33, make_int=True)
      save_movie_frame(meteor_stack_img, MOVIE_FRAME_NUMBER, MOVIE_FRAMES_TEMP_FOLDER, 15, 10)
   if SHOW == 1:
      if meteor_stack_img is not None:
         cv2.imshow('pepe', meteor_stack_img)
         cv2.waitKey(30)

   #mj['cp'], cat_stars = recenter_fov(meteor_file, mj['cp'].copy(), median_frame.copy(),  stars, json_conf, meteor_file , None, None, con, cur)
   if meteor_stack_img is not None and mj['cp'] is not None:
      star_img = draw_star_image(meteor_stack_img.copy(), mj['cp']['cat_image_stars'],mj['cp'], json_conf, extra_text) 
      print("CAT STARS AFTER RECENTER", len(mj['cp']['cat_image_stars']))

      cv2.imwrite(fit_img_file, star_img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])

   if SAVE_MOVIE is True:
      print("MOVIE_FRAME_NUMBER:", MOVIE_FRAME_NUMBER)
      MOVIE_FRAME_NUMBER += 1
      star_img = RF.watermark_image(star_img, RF.logo_320, logo_x,logo_y, .33, make_int=True)
      save_movie_frame(star_img, MOVIE_FRAME_NUMBER, MOVIE_FRAMES_TEMP_FOLDER, 10)

   if SHOW == 1 and meteor_stack_img is not None:
      cv2.imshow('pepe', star_img)
      cv2.waitKey(30)

   #cp = custom_fit_meteor(meteor_file,json_conf,show=SHOW)
   #mj['cp'] = cp
   #extra_text = "AFTER CUSTOM"
   #star_img = draw_star_image(stack_img.copy(), cp['cat_image_stars'],cp, json_conf, extra_text) 
   #if SHOW == 1:
   #   cv2.imshow('pepe', star_img)

   #if SHOW == 1 :
   #   cv2.imshow('pepe', star_img)
   #   cv2.waitKey(30)


   # BY HERE ALL CALIB IS GOOD BUT WE SHOULD CONFIRM THE POINTS ARE PERFECT AND THE ROI ID IS CORRECT WITH AI.
   if len(frames) > 0:
      print("mj", mj['cp'])
      if mj['cp'] is not None:
         star_img = draw_star_image(frames[0].copy(), mj['cp']['cat_image_stars'],mj['cp'], json_conf, extra_text) 
      else:
         star_img = None
         star_img = frames[0]
   else:
      star_img = None
      if len(frames) > 0:
         star_img = frames[0]
      else:
         star_img = meteor_stack_img

   
   # save the first frame of the movie?
   star_img = cv2.resize(star_img, (1920,1080))
   if SAVE_MOVIE is True:
      if len(frames) > 0:
         ff = cv2.resize(frames[0], (1920,1080))
      else:
         ff = star_img 
      blend_img = cv2.addWeighted(ff, .5, star_img, .5,0)
      print("MOVIE_FRAME_NUMBER:", MOVIE_FRAME_NUMBER)
      MOVIE_FRAME_NUMBER += 1
      blend_img = RF.watermark_image(blend_img, RF.logo_320, logo_x,logo_y, .33, make_int=True)
      save_movie_frame(blend_img, MOVIE_FRAME_NUMBER, MOVIE_FRAMES_TEMP_FOLDER, 10)
   if SAVE_MOVIE is True:
      for frame in frames:
         frame = cv2.resize(frame, (1920,1080))
         blend_img = cv2.addWeighted(frame, .5, star_img, .5,0)
         blend_img = RF.watermark_image(blend_img, RF.logo_320, logo_x,logo_y, .33, make_int=True)

         if meteor_roi is not None:
            x1,y1,x2,y2 = meteor_roi
            color = (255,255,255)
            blend_img[y1:y2,x1:x2] = frame[y1:y2,x1:x2]
            cv2.rectangle(blend_img, (int(x1), int(y1)), (int(x2) , int(y2) ), color, 2)

         if SAVE_MOVIE is True:
            print("MOVIE_FRAME_NUMBER:", MOVIE_FRAME_NUMBER)
            MOVIE_FRAME_NUMBER += 1
            save_movie_frame(blend_img, MOVIE_FRAME_NUMBER, MOVIE_FRAMES_TEMP_FOLDER)
         if SHOW == 1:
            cv2.imshow('pepe', blend_img)
            cv2.waitKey(30)

      blend_img = cv2.addWeighted(meteor_stack_img, .5, star_img, .5,0)
      if SAVE_MOVIE is True:
         blend_img = RF.watermark_image(blend_img, RF.logo_320, logo_x,logo_y, .33, make_int=True)
         save_movie_frame(blend_img, MOVIE_FRAME_NUMBER, MOVIE_FRAMES_TEMP_FOLDER, 15, 10)
      if SHOW == 1:
         cv2.imshow('pepe', blend_img)
         cv2.waitKey(30)
   #if mjr is not None:
   #   if "meteor_frame_data" in mjr:
   #      mfd = perfect_meteor(json_file, sd_frames, mjr['meteor_frame_data'], meteor_roi)

   # bug we should update the poly fields all the time.? Else how will meteors get the newest lens model?
   # but what about custom fits? 

   if mjr is not None:
      if "meteor_frame_data" in mjr:
         mjr = update_mfd(meteor_file, mjr, mj['cp'])
         print("UPDATED RED DATA")
         cp = mj['cp']
         if cp is None:
            cp = mcp
            cp = update_center_radec(meteor_file,cp,json_conf)

         if "x_poly" in cp:
            cp['x_poly'] = mcp['x_poly']
            cp['y_poly'] = mcp['y_poly']
            cp['x_poly_fwd'] = mcp['x_poly_fwd']
            cp['y_poly_fwd'] = mcp['y_poly_fwd']
            if isinstance(cp['x_poly'], list) is not True:
               cp['x_poly'] = cp['x_poly'].tolist()
               cp['y_poly'] = cp['y_poly'].tolist()
               cp['x_poly_fwd'] = cp['x_poly_fwd'].tolist()
               cp['y_poly_fwd'] = cp['y_poly_fwd'].tolist()
         mjr['cal_params']  = cp
         save_json_file(red_json_file, mjr)

   if "refit" in mj:
      mj['refit'] += 1
   else:
      mj['refit'] = 1

   save_json_file(json_file, mj)      

   # run the star api to finalize
   if "sd_video_file" in mj:
      video_file = mj['sd_video_file'].split("/")[-1]
   else:
      video_file = None
   if "hd_stack" in mj:
      hd_stack_file = mj['hd_stack'].split("/")[-1]
   else:
      hd_stack_file = None
   point_str = ""
   if "cp" in mj:
      if mj['cp'] is not None:
         if "user_stars" in mj['cp']:
            for row in mj['cp']['user_stars']:
               if len(row) == 3:
                  x,y,i = row
               if len(row) == 2:
                  x,y = row
               point_str += str(x) + "," + str(y) + "|"


   # cp = get_default_cal_for_file(meteor_file, median_frame.copy(), con, cur, json_conf)

   # update json / web api so page is up to date
   if video_file is None:
      print("VIDEO FILE IS NONE!", meteor_file)
      video_file = meteor_file.replace(".json", ".mp4")
      mdir = "/mnt/ams2/meteors/" + video_file[0:10] + "/"
      mj['sd_video_file'] = mdir + video_file 
      video_file = mdir + video_file 
      mjf = video_file.replace(".mp4", ".json")
      save_json_file(mjf, mj)
      print(video_file)
      #return(mj)

   print(video_file, mj.keys())
   show_cat_stars (video_file, hd_stack_file, point_str)
   
   #show_cat_url = "http://AMS1:xrp23q@localhost/API/show_cat_stars?video_file={:s}&hd_stack_file={:s}&cmd=show_cat_stars&points={:}".format(video_file, hd_stack_file, point_str)
   #response = requests.get(show_cat_url)
   #content = response.content.decode()
   #print("REQ", content)

   cmd = "./pushAWS.py push_obs " + meteor_file + " > /dev/null 2>&1 &"
   os.system(cmd)


   return(mj['cp'])

def subtract_mask(cal_img, station_id, cam_id):

   mask_file = "/mnt/ams2/meteor_archive/{}/CAL/MASKS/{}_mask.png".format(station_id, cam_id)
   if os.path.exists(mask_file) is True:
      mask = cv2.imread(mask_file)
      mask = cv2.resize(mask, (1920,1080))
   else:
      size = len(clean_cal_img.shape)
      mask = np.zeros((1080,1920,size),dtype=np.uint8)

   #print(clean_cal_img.shape, mask.shape)
   print(cal_img)
   if len(cal_img.shape) == mask.shape:
      clean_cal_img = cv2.subtract(cal_img, mask)
   else:
      clean_cal_img = cal_img
   return(clean_cal_img)

def add_more_stars(cal_file, cp, star_img, median_frame, json_conf) :
   logo_x = 1550 
   logo_y = 950 

   global MOVIE_FRAME_NUMBER
   cat_stars, short_bright_stars, cat_image = get_catalog_stars(cp)
   med_frame_copy = median_frame.copy()
   star_objs = []
   cat_image_stars = []
   star_points = []
   #dcname,mag,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist = star
   all_img = median_frame.copy() 

   for row in short_bright_stars[0:100]:
      (name, name2, ra, dec, mag,new_cat_x, new_cat_y,zp_cat_x, zp_cat_y, rx1,ry1,rx2,ry2) = row 
      simg = median_frame.copy() 
      star_crop = med_frame_copy[ry1:ry2,rx1:rx2].copy()
      star_cat_info = [name, mag, ra,dec,new_cat_x,new_cat_y]  
      cv2.rectangle(simg, (rx1,ry1), (rx2,ry2) , [255,175,212], 1)

      if rx1 < 0 or ry1 < 0 or rx2 >= 1920 or ry2 >=1080:
         continue
      #if SHOW == 1:
      #   cv2.imshow("pepe", simg)
      #   cv2.waitKey(30)

      star_obj = eval_star_crop(star_crop, cal_file, rx1, ry1, rx2, ry2, star_cat_info)
      #if SHOW == 1:
      #   cv2.rectangle(simg, (rx1,ry1), (rx2,ry2) , [255,175,212], 1)
      #   cv2.imshow("pepe", simg)
      #   cv2.waitKey(30)
      res_px = cp['total_res_px']
      if res_px < 3:
         res_px = 3 

      if star_obj['valid_star'] is True and star_obj['res_px'] < (res_px * 5):
         if "res_px" in star_obj:
            desc = str(round(star_obj['res_px'],2)) + " res px" 
         else:
            desc = ""
         if SHOW == 1:
            cv2.rectangle(simg, (rx1,ry1), (rx2,ry2) , [55,175,212], 1)
            cv2.circle(simg, (int(star_obj['star_x']), int(star_obj['star_y'])), 5, (128,128,128),1)
            cv2.rectangle(simg, (int(new_cat_x)-5,int(new_cat_y)-5), (int(new_cat_x)+5,int(new_cat_y)+5) , [128,128,128], 1)
            cv2.putText(simg, desc,  (int(rx2+5),int(ry1-5)), cv2.FONT_HERSHEY_SIMPLEX, .4, (200,200,200), 1)

            cv2.rectangle(all_img, (rx1,ry1), (rx2,ry2) , [55,175,212], 1)
            cv2.circle(all_img, (int(star_obj['star_x']), int(star_obj['star_y'])), 5, (128,128,128),1)
            cv2.rectangle(all_img, (int(new_cat_x)-5,int(new_cat_y)-5), (int(new_cat_x)+5,int(new_cat_y)+5) , [128,128,128], 1)
            cv2.putText(all_img, desc,  (int(rx2+5),int(ry1-5)), cv2.FONT_HERSHEY_SIMPLEX, .4, (200,200,200), 1)


            #cv2.imshow("pepe", simg)
            #cv2.waitKey(30)
         simg[ry1:ry2,rx1:rx2] = [0,0,0]
         med_frame_copy[ry1:ry2,rx1:rx2] = [0,0,0]
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(star_obj['star_x'],star_obj['star_y'],cal_file,cp,json_conf)
         match_dist = angularSeparation(ra,dec,img_ra,img_dec)

         cat_image_stars.append((star_obj['name'],star_obj['mag'],star_obj['ra'],star_obj['dec'],img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,star_obj['cat_x'],star_obj['cat_y'],star_obj['star_x'],star_obj['star_y'],star_obj['res_px'],star_obj['star_flux']))
         star_points.append((star_obj['star_x'],star_obj['star_y'],star_obj['star_flux']))
      else:
         if SHOW == 1:
      #         print("INVALID:", res_px * 5, star_obj['valid_star'], star_obj['res_px'] , "PX" , star_obj['reject_reason'])
               cv2.rectangle(simg, (rx1,ry1), (rx2,ry2) , [0,0,255], 1)
               #cv2.imshow("pepe", simg)
               #cv2.waitKey(30)


   if SAVE_MOVIE is True:
      print("MOVIE_FRAME_NUMBER:", MOVIE_FRAME_NUMBER)
      MOVIE_FRAME_NUMBER += 1

      all_img = RF.watermark_image(all_img, RF.logo_320, logo_x,logo_y, .33, make_int=True)
      save_movie_frame(all_img, MOVIE_FRAME_NUMBER, MOVIE_FRAMES_TEMP_FOLDER, 10, 10)

   #if SHOW == 1:
   #   cv2.imshow("pepe", all_img)
   #   cv2.waitKey(30)
   cp['cat_image_stars'] = cat_image_stars
   cp['star_points'] = star_points

   return(cp)

def perfect_meteor(meteor_file, frames, mfd, meteor_roi):
   meteor_fn = meteor_file.split("/")[-1].replace(".json", "")
   crops = []
   print(len(frames), "FRAMES")
   mf = {}
   for row in mfd:

      (dt, fn, x, y, w, h, oint, ra, dec, az, el) = row
      print("MFD", row)
      mf[fn] = row

   for frame in frames:

      frame = cv2.resize(frame, (1920,1080))

      if meteor_roi is not None:
         x1,y1,x2,y2 = meteor_roi
         color = (255,255,255)
         crop_frame = frame[y1:y2,x1:x2]
         crops.append(crop_frame)

   fc = 0 
   last_x = 0
   last_y = 0
   last_max_x = 0
   last_max_y = 0
   bad_mfd = {}
   fluxes = []
   fns= []
   xs = []
   ys = []
   end = 0
   for frame in crops:
      if fc in mf:
         (dt, fn, x, y, w, h, oint, ra, dec, az, el) = mf[fc]
         img_x = x - x1
         img_y = y - y1
         cx = int(img_x + (w/2))
         cy = int(img_y + (h/2))
         if w > h:
            radius = w
         else:
            radius = h
         if last_max_x == 0:
            last_max_x = img_x
            last_max_y = img_y

         gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         frame_flux = do_photo(gray_frame, (cx,cy), radius)
         fluxes.append(frame_flux)
         fns.append(fn)

         xs.append(cx)
         ys.append(cy)

         cv2.circle(frame, (int(img_x), int(img_y)), 5, (128,128,128),1)


         last_x_dist = abs(img_x - last_max_x)
         last_y_dist = abs(img_y - last_max_y)
         last_x = img_x
         last_y = img_y
         if last_x > last_max_x:
            last_max_x = last_x
         if last_y > last_max_y:
            last_max_y = last_y
         if last_x_dist <= 0 and last_y_dist < 0:
            end += 1
            if fc not in bad_mfd:
               bad_mfd[fc] = []
            bad_mfd[fc].append("negative distance")
         print(end, fc, img_x, img_y, last_x_dist, last_y_dist, frame_flux)

      else:
         print(fc, "NO MFD")
         fluxes.append(0)
         fns.append(fc)

      frame = cv2.resize(frame, (500,500))
      if SHOW == 1:
         cv2.imshow('crop', frame)
         cv2.waitKey(30)
      fc += 1 

   import matplotlib.pyplot as plt 
   fig, (ax1, ax2) = plt.subplots(1,2)
   fig.set_size_inches(12,4)
   fig.tight_layout(pad=5.0)
   fig.suptitle("Reduction for " + meteor_fn)
   ax1.scatter(fns, fluxes, marker="+", color="r")
   ax2.scatter(xs, ys, marker="+", color="r")
   ax1.set_xlabel("fns")
   ax1.set_ylabel("fluxes")
   ax2.set_xlabel("xs")
   ax2.set_ylabel("ys")
   #plt.show()


def update_mfd(meteor_file, mjr, cp):

   mjr['meteor_frame_data'] = sorted(mjr['meteor_frame_data'], key=lambda x: (x[1]), reverse=False)
   # make sure we are using the manual points if defined. 
   mday = meteor_file[0:10]
   mdir = "/mnt/ams2/meteors/" + mday + "/"
   mj = load_json_file(mdir + meteor_file)
   man = None
   if "user_mods" in mj:
      if "frames" in mj['user_mods']:
         man = mj['user_mods']['frames']
   updated_frame_data = []
   for row in mjr['meteor_frame_data']:
      (dt, fn, x, y, w, h, oint, ra, dec, az, el) = row
      if man is not None:
         if str(fn) in man:
            print("USING MAN DATA FOR FRAME:", fn, man[str(fn)])
            x,y = man[str(fn)]
         elif fn in man:
            print("USING MAN DATA FOR FRAME:", fn, man[fn])
            x,y = man[str(fn)]
      tx, ty, ra ,dec , az, el = XYtoRADec(x,y,meteor_file,mjr['cal_params'],json_conf)
      updated_frame_data.append((dt, int(fn), x, y, w, h, oint, ra, dec, az, el))
   mjr['meteor_frame_data'] = updated_frame_data
   return(mjr)

def check_for_nan(mjf, mj):
   mjrf = mjf.replace(".json", "-reduced.json")
   nan_found = False
   if os.path.exists(mjrf) is True:
      try:
         mjr = load_json_file(mjrf)
      except:
         nan_found = True
         mjr = {}
      if "meteor_frame_data" in mjr:
         for row in mjr['meteor_frame_data']:
            for val in row:
               if type(val) != str:
                  res = np.isnan(val)
                  if res == True:
                     nan_found = True

   if "cp" in mj:
      if mj['cp'] is None:
         del(mj['cp'] )

   if "cp" in mj:
      for field in mj['cp']:
         val = mj['cp'][field]
         if type(val) == float: 
            res = np.isnan(val)
         else:
            res = False
         if res == True:
            nan_found = True

   if nan_found == True:
      os.system("rm " + mjrf)
      del mj['cp']
      save_json_file(mjf, mj)
   return(mj)

def make_photo_credit(json_conf, cam_id=None):
   if json_conf is not None:
      station_id = json_conf['site']['ams_id'] 
      if cam_id is not None:
         station_id += "-" + cam_id
      if "operator_name" in json_conf['site']:
         name = json_conf['site']['operator_name']

      if "operator_country" in json_conf['site']:
         city = json_conf['site']['operator_city']
      if "operator_state" in json_conf['site']:
         state = json_conf['site']['operator_state']
      if "operator_country" in json_conf['site']:
         country = json_conf['site']['operator_country']
      if "USA" in country or "United States" in country:
         country = "US"
         photo_credit = station_id + " - " + name + ", " + city + ", " + state + " " + country
      else:
         photo_credit = station_id + " - " + name + ", " + city + ", " + country
   return(photo_credit)

def draw_text_on_image(img, text_data) :
   image = Image.fromarray(img)
   draw = ImageDraw.Draw(image)
   font = ImageFont.truetype("/usr/share/fonts/truetype/DejaVuSans.ttf", 20, encoding="unic" )
   for tx,ty,text in text_data:
      draw.text((tx, ty), str(text), font = font, fill="white")

   return_img = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
   return(return_img)

def draw_stars_on_image(img, cat_image_stars,cp=None,json_conf=None,extra_text=None,img_w=1920,img_h=1080) :
   photo_credit = ""
   station_id = ""
   name = ""
   city = ""
   state = ""
   country = ""
   hdm_x = img_w / 1920
   hdm_y = img_h / 1080
   #print(cp.keys())
   #print(json_conf.keys())
   if json_conf is not None:
      station_id = json_conf['site']['ams_id']
      if "operator_name" in json_conf['site']:
         name = json_conf['site']['operator_name']

      if "operator_country" in json_conf['site']:
         city = json_conf['site']['operator_city']
      if "operator_state" in json_conf['site']:
         state = json_conf['site']['operator_state']
      if "operator_country" in json_conf['site']:
         country = json_conf['site']['operator_country']
      if "US" in country or "United States" in country:
         country = "US"
         photo_credit = station_id + " - " + name + ", " + city + ", " + state + " " + country
      else:
         photo_credit = station_id + " - " + name + ", " + city + ", " + country
   for star in cat_image_stars:
      if len(star) == 9:
         dcname,mag,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist = star
      else:
         dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      if 0 <= six <= 1920 and 0 <= siy <= 1080:
         img[int(siy*hdm_y),int(six*hdm_x)] = [0,0,255]

   image = Image.fromarray(img)
   draw = ImageDraw.Draw(image)
   #font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 20, encoding="unic" )
   font = ImageFont.truetype("/usr/share/fonts/truetype/DejaVuSans.ttf", 20, encoding="unic" )
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

      dist = calc_dist((six,siy), (new_cat_x,new_cat_y))
     
      six = int(six * hdm_x)
      siy = int(siy * hdm_y)
      org_x = int(org_x * hdm_x)
      org_y = int(org_y * hdm_y)
      new_cat_x = int(new_cat_x * hdm_x)
      new_cat_y = int(new_cat_y * hdm_y)

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
         ltext0 = "Images / Res Px:"
         text0 =  str(len(cp['cat_image_stars'])) + " / " + str(cp['total_res_px'])[0:7]
         ltext1 = "Center RA/DEC:"
         text1 =  str(cp['ra_center'])[0:7] + " / " + str(cp['dec_center'])[0:7]
         ltext2 = "Center AZ/EL:"
         text2 =  str(cp['center_az'])[0:7] + " / " + str(cp['center_el'])[0:7]
         ltext3 = "Position Angle:"
         text3 =  str(cp['position_angle'])[0:7]
         ltext4 = "Pixel Scale:"
         text4 =  str(cp['pixscale'])[0:7]
         draw.text((800, 20), str(extra_text), font = font, fill="white")


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

         draw.text((1520, 1050), str(photo_credit), font = font, fill="white")
   return_img = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)

   return(return_img)


def make_grid_stars(merged_stars, mcp = None, factor = 2, gsize=50, limit=3):
   merged_stars = sorted(merged_stars, key=lambda x: x[-2], reverse=False)
   if mcp is None:
      print("NO MCP? FIRST TIME CAL?")
      gsize = 80
      factor = 2
      max_dist = 35
   else:
      if mcp['cal_version'] < 3:
         gsize= 100
         factor = 2
         max_dist = 5
      else:
         gsize= 100
         factor = 1
         max_dist = 5

   all_res = [row[-2] for row in merged_stars]
   res1 = []
   res2 = []
   for star in merged_stars:
      (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star
      center_dist = calc_dist((six,siy), (1920/2, 1080/2))
      cat_dist = calc_dist((six,siy), (new_cat_x,new_cat_y))
      if center_dist < 800:
         res1.append(cat_dist)
      else:
         res2.append(cat_dist)

   med_res = np.mean(all_res) ** 2
   med_res1 = np.mean(res1) ** factor
   med_res2 = np.mean(res2) ** factor
   if med_res1 > max_dist:
      med_res1 = max_dist
   if med_res2 > max_dist:
      med_res2 = max_dist

   qual_stars = []
   grid = {}
   for w in range(0,1920):
      for h in range(0,1080):
         if (w == 0 and h == 0) or (w % gsize == 0 and h % gsize == 0):
            x1 = w
            x2 = w + gsize
            y1 = h
            y2 = h + gsize
            if x2 > 1920:
               x2 = 1920
            if y2 > 1080:
               y2 = 1080
            grid_key = str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2)

            if grid_key not in grid:
               grid[grid_key] = [] 

            for star in merged_stars:
               (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star
               cat_dist = calc_dist((six,siy), (new_cat_x,new_cat_y))

               res_limit = med_res
               if x1 <= six <= x2 and y1 <= siy <= y2 : #and cat_dist < res_limit:
                  grid[grid_key].append(star)
                  #break
   


   return(grid)


def minimize_fov(cal_file, cal_params, image_file,img,json_conf,zero_poly=False, mcp=None, extra_text=None,show=0):
   orig_cal = dict(cal_params)

   cal_params = update_center_radec(cal_file,cal_params,json_conf)

   #all_res, inner_res, middle_res, outer_res = recalc_res(cal_params)
   all_res, inner_res, middle_res, outer_res,cal_params = recalc_res(cal_file, cal_params, json_conf)
   cal_params['total_res_px'] = all_res

   az = np.float64(orig_cal['center_az'])
   el = np.float64(orig_cal['center_el'])
   pos = np.float64(orig_cal['position_angle'])
   pixscale = np.float64(orig_cal['pixscale'])
   if mcp is not None:
      x_poly = np.float64(mcp['x_poly'])
      y_poly = np.float64(mcp['y_poly'])
   else:
      x_poly = np.float64(orig_cal['x_poly'])
      y_poly = np.float64(orig_cal['y_poly'])


   this_poly = np.zeros(shape=(4,), dtype=np.float64)
   if all_res < 10:
      this_poly = [.0001,.0001,.0001,.0001]
   elif 10 <= all_res <= 20:
      this_poly = [.001,.001,.001,.001]
   else:
      this_poly = [.005,.005,.005,.005]


   if zero_poly is True:
      cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)

      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      x_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
      y_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
   elif mcp is None:
      cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      x_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
      y_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)

   else:
      x_poly = mcp['x_poly']
      y_poly = mcp['y_poly']
      x_poly_fwd = mcp['x_poly_fwd']
      y_poly_fwd = mcp['y_poly_fwd']

      cal_params['x_poly'] = mcp['x_poly']
      cal_params['y_poly'] = mcp['y_poly']
      cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      cal_params['y_poly_fwd'] = mcp['y_poly_fwd']




   # MINIMIZE!
   tries = 0

   orig_res = []
   orig_cat_image_stars = []

   #
   all_stars = cal_params['cat_image_stars']
   best_stars = []
   #XXX
   # CALC RES
   for star in cal_params['cat_image_stars']:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      center_dist = calc_dist((960,540),(six,siy))
      #
      if center_dist < 600:
         best_stars.append(star)
      new_cat_x, new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)
      res_px = calc_dist((six,siy),(new_cat_x,new_cat_y))

      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_file,cal_params,json_conf)
      match_dist = angularSeparation(ra,dec,img_ra,img_dec)

      orig_res.append(res_px)
      orig_cat_image_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,res_px,bp)) 
   old_res = np.mean(orig_res)
   orig_info = [cal_params['center_az'], cal_params['center_el'], cal_params['ra_center'], cal_params['dec_center'], cal_params['position_angle'], cal_params['pixscale'], old_res ]

   check_cal_params, check_report_txt, check_show_img = cal_params_report(image_file, cal_params, json_conf, img.copy(), 30, mcp)

   if len(best_stars) > 5:
      cal_params['cat_image_stars'] = best_stars
   ores = check_cal_params['total_res_px']

   res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=( az,el,pos,pixscale,x_poly, y_poly, x_poly_fwd, y_poly_fwd, image_file,img,json_conf, cal_params['cat_image_stars'],extra_text,0), method='Nelder-Mead')

   if isinstance(cal_params['x_poly'], list) is not True:
      cal_params['x_poly'] = x_poly.tolist()
      cal_params['y_poly'] = y_poly.tolist()
      cal_params['x_poly_fwd'] = x_poly_fwd.tolist()
      cal_params['y_poly_fwd'] = y_poly_fwd.tolist()

   adj_az, adj_el, adj_pos, adj_px = res['x']

   new_az = az + (adj_az*az)
   new_el = el + (adj_el*el)
   new_position_angle = pos + (adj_pos*pos)
   new_pixscale = pixscale + (adj_px*pixscale)


   cal_params['center_az'] =  new_az
   cal_params['center_el'] =  new_el
   cal_params['position_angle'] =  new_position_angle
   cal_params['pixscale'] =  new_pixscale
   cal_params['total_res_px'] = res['fun']
   cal_params = update_center_radec(cal_file,cal_params,json_conf)

   # update the stars with best / new results
   new_cat_image_stars = []
   for star in cal_params['cat_image_stars']:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      center_dist = calc_dist((960,540),(six,siy))
      #
      #if center_dist < 600:
      #   best_stars.append(star)
      new_cat_x, new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)
      res_px = calc_dist((six,siy),(new_cat_x,new_cat_y))

      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_file,cal_params,json_conf)
      match_dist = angularSeparation(ra,dec,img_ra,img_dec)

      orig_res.append(res_px)
      new_cat_image_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,res_px,bp)) 
   old_res = np.mean(orig_res)
   orig_info = [cal_params['center_az'], cal_params['center_el'], cal_params['ra_center'], cal_params['dec_center'], cal_params['position_angle'], cal_params['pixscale'], old_res ]

   check_cal_params, check_report_txt, check_show_img = cal_params_report(image_file, cal_params, json_conf, img.copy(), 30, mcp)

   #if len(best_stars) > 5:
   cal_params['cat_image_stars'] = new_cat_image_stars
   ores = check_cal_params['total_res_px']



   return(cal_params)


def reduce_fov_pos(this_poly,az,el,pos,pixscale, x_poly, y_poly, x_poly_fwd, y_poly_fwd, cal_params_file, oimage, json_conf, cat_image_stars, extra_text="", show=0):
   cal_fn = cal_params_file
   #extra_text = cal_fn[0:20]
   global tries
   tries = tries + 1
   image = oimage.copy()
   image = cv2.resize(image, (1920,1080))

   only_center = False 

   extra_text += " x" + str(tries)

   new_az = az + (this_poly[0]*az)
   new_el = el + (this_poly[1]*el)
   new_position_angle = pos + (this_poly[2]*pos)
   new_pixscale = pixscale + (this_poly[3]*pixscale)


   lat,lng,alt = json_conf['site']['device_lat'], json_conf['site']['device_lng'], json_conf['site']['device_alt']

   temp_cal_params = {}
   #temp_cal_params['ra_center'] = ra_center
   #temp_cal_params['dec_center'] = dec_center
   temp_cal_params['center_az'] = new_az
   temp_cal_params['center_el'] = new_el
   temp_cal_params['pixscale'] = new_pixscale
   temp_cal_params['position_angle'] = new_position_angle
   temp_cal_params['device_lat'] = json_conf['site']['device_lat']
   temp_cal_params['device_lng'] = json_conf['site']['device_lng']
   temp_cal_params['device_alt'] = json_conf['site']['device_alt']
   temp_cal_params['imagew'] = 1920
   temp_cal_params['imageh'] = 1080
   temp_cal_params['x_poly'] = x_poly
   temp_cal_params['y_poly'] = y_poly
   temp_cal_params['x_poly_fwd'] = x_poly_fwd 
   temp_cal_params['y_poly_fwd'] = y_poly_fwd
   temp_cal_params['cat_image_stars'] = cat_image_stars 
   temp_cal_params = update_center_radec(cal_fn,temp_cal_params,json_conf)

   #for key in temp_cal_params:
   #   print(key, temp_cal_params[key])
   #show_calparams(temp_cal_params)

   all_res = []
   new_cat_image_stars = []
   for star in cat_image_stars:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      new_cat_x, new_cat_y = get_xy_for_ra_dec(temp_cal_params, ra, dec)
      res_px = calc_dist((six,siy),(new_cat_x,new_cat_y))

      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_fn,temp_cal_params,json_conf)
      match_dist = angularSeparation(ra,dec,img_ra,img_dec)
      real_res_px = res_px
      if only_center is True:
         center_dist = calc_dist((960,540),(six,siy))
         if center_dist > 800:
            real_res_px = res_px
            res_px = 0

      all_res.append(res_px)
      new_cat_image_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,real_res_px,bp)) 
   mean_res = np.median(all_res)
   temp_cal_params['cat_image_stars'] = new_cat_image_stars 
   temp_cal_params['total_res_px'] = mean_res
   if SHOW == 1 or show == 1:
      if tries % 50 == 0:
         star_img = draw_star_image(image, new_cat_image_stars,temp_cal_params, json_conf, extra_text) 
         if SHOW == 1:
            cv2.imshow('pepe', star_img)
            cv2.waitKey(30)
   #print("\r", "REDUCE STARS / RES:", len(new_cat_image_stars), mean_res, extra_text, end = "") #, extra_text, x_poly[0], y_poly[0], end="")

   #print("AZ", temp_cal_params['center_az']) 
   #print("EL", temp_cal_params['center_el']) 
   #print("PA", temp_cal_params['position_angle']) 
   #print("PX", temp_cal_params['pixscale']) 
   return(mean_res)


def delete_cal_file(cal_fn, con, cur, json_conf):

   # this should only delete the cal file from the database!
   # you must also move the caldir to the bad location if you want to do that but don't do it here
   # this function is used during updates and should not edit the filesystem! 

   if False:
      # don't do this here!
      cal_dir = "/mnt/ams2/cal/freecal/" + cal_fn.replace("-stacked-calparams.json", "")
      base = cal_dir.split("/")[-1] 
      bad_dir = "/mnt/ams2/cal/bad_cals/" + cal_fn.replace("-stacked-calparams.json", "")
      if os.path.exists(bad_dir) is False:
         os.makedirs(bad_dir)
      if os.path.exists(bad_dir + base) is True:
         os.system("rm -rf " + bad_dir + base)
      #os.system("mv  " + cal_dir + "/" + cal_fn + " " + bad_dir )
   
   if True:
      sql = "DELETE FROM calibration_files where cal_fn = ?"
      dvals = [cal_fn]
      cur.execute(sql, dvals)
      #print(sql, dvals)
      sql = "DELETE FROM calfile_paired_stars where cal_fn = ?"
      dvals = [cal_fn]
      cur.execute(sql, dvals)
      con.commit()
      #print(sql, dvals)

def start_calib(cal_fn, json_conf, calfiles_data, mcp=None):

   #print("Start calib for : ", cal_fn)
   autocal_dir = "/mnt/ams2/cal/"
   station_id = json_conf['site']['ams_id']
   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)

   if cal_fn in calfiles_data:
      cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, None, mcp)
   else:
      print("CAL FN", cal_fn, "is no longer valid? Maybe you should re-run the recal.py status all")
      #print("OK")
      cal_img = False

   if cal_img is False:
      print("FAILED")
      return(False)

   cal_img_fn = cal_fn.replace("-calparams.json", ".png")
   cal_image_file = cal_fn.replace("-calparams.json", ".png")
   cal_dir = cal_dir_from_file(cal_image_file)
   cal_json_file = get_cal_json_file(cal_dir)
   if cal_json_file is None:
      print("CAL_JSON IS NONE.", cal_json_file, cal_dir, "None json file")
      return(None)
   cal_json_fn = cal_json_file.split("/")[-1]
   if os.path.exists(cal_dir + cal_img_fn):
      clean_cal_img = cv2.imread(cal_dir + cal_img_fn)
   else:
      clean_cal_img = None

   mask_file = "/mnt/ams2/meteor_archive/{}/CAL/MASKS/{}_mask.png".format(station_id, cam_id)
   if os.path.exists(mask_file) is True:
      mask = cv2.imread(mask_file)
      mask = cv2.resize(mask, (1920,1080))
   else:
      size = len(clean_cal_img.shape)
      mask = np.zeros((1080,1920,size),dtype=np.uint8)

   if clean_cal_img is not None:
      clean_cal_img = cv2.subtract(clean_cal_img, mask)

   if mcp is None:
      mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
      if os.path.exists(mcp_file) == 1:
         mcp = load_json_file(mcp_file)
         # reset mcp if it is bad
         if mcp['x_fun'] > 5:
            mcp = None



   if mcp is not None:
      cal_params['x_poly'] = mcp['x_poly']
      cal_params['y_poly'] = mcp['y_poly']
      cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      cal_params['y_poly_fwd'] = mcp['y_poly_fwd']

      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
      mcp['cal_version'] += 1

      # reset mcp if it is bad
      if "x_fun" in mcp:
         if mcp['x_fun'] > 5:
            mcp = None
            cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
            cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
            cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
            cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)

   else:
      mcp = None
      cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   

   
   return(station_id, cal_dir, cal_json_file, cal_image_file, cal_params, cal_img, clean_cal_img, mask_file, mcp)

def cal_status_report(cam_id, con, cur, json_conf): 

   reconcile_calfiles(cam_id, con, cur, json_conf)

   station_id = json_conf['site']['ams_id']


   autocal_dir = "/mnt/ams2/cal/"
   # get all call files for this cam
   print("LOAD CAL FILES :", cam_id)
   calfiles_data = load_cal_files(cam_id, con, cur)

   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
   else:
      mcp = None

   if mcp is None:
      print("Can't update until the MCP is made!", cam_id)
      cmd = "python3 Process.py deep_init " + cam_id
      print(cmd)
      os.system(cmd)
      return()

   # get all paired stars by file 
   cal_files = []
   sql = """
      SELECT cal_fn, count(*) as ss, avg(res_px) as arp,  count(*) / avg(res_px) as score
        FROM calfile_paired_stars
       WHERE cal_fn like ?
         AND res_px is not NULL
       GROUP bY cal_fn
    ORDER BY score DESC
   """

   dvals = ["%" + cam_id + "%"]
   cur.execute(sql, dvals)
   rows = cur.fetchall()
   cal_fns = []

   calfile_paired_star_stats = {}
   stats_res = []
   stats_stars = []
   for row in rows:
      cal_fn, total_stars, avg_res , score = row
      cal_files.append((cal_fn, total_stars, avg_res , score))
      calfile_paired_star_stats[cal_fn] = [cal_fn,total_stars,avg_res] 
      stats_res.append(avg_res)
      stats_stars.append(total_stars)

   avg_res = np.mean(stats_res)
   avg_stars = np.mean(stats_stars)
   # get all files from the cal-index / filesystem
   freecal_index = load_json_file("/mnt/ams2/cal/freecal_index.json") 
  
   need_to_load = {}
   cal_files_count = 0
   for key in freecal_index:
      data = freecal_index[key]
      print("DATA:", data)
      if "cam_id" not in data:
         (f_datetime, m_cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(key)
         data['cam_id'] = m_cam_id
      
      if data['cam_id'] == cam_id:
        cal_fn = key.split("/")[-1]
        if cal_fn not in calfiles_data:
           need_to_load[cal_fn] = {}
           need_to_load[cal_fn]['cal_dir'] = data['base_dir']
           need_to_load[cal_fn]['cal_fn'] = cal_fn
        if cal_fn not in calfile_paired_star_stats:
           need_to_load[cal_fn] = {}
           need_to_load[cal_fn]['cal_dir'] = data['base_dir']
           need_to_load[cal_fn]['cal_fn'] = cal_fn
        cal_files_count += 1

   #print("FILES TO LOAD", len(need_to_load.keys()))

   lc = 1 
   for cal_fn in sorted(need_to_load, reverse=True):
      #print(lc, need_to_load[cal_fn]['cal_dir'] + cal_fn)
      cal_dir = need_to_load[cal_fn]['cal_dir'] + "/"
      print("import", cal_dir, cal_fn)
      import_cal_file(cal_fn, cal_dir, mcp)
      lc += 1

   print("FILES LOADED", cal_files_count)
   #print("All files loaded...")
   #os.system("clear")


   sql = """
      SELECT avg(res_px) as avg_res from calfile_paired_stars where cal_fn like ?
   """

   dvals = ["%" + cam_id + "%"]
   cur.execute(sql, dvals)
   rows = cur.fetchall()
   avg_res_2 = rows[0][0]


  
   tb = pt()
   tb.field_names = ["Field", "Value"]

   tb.add_row(["Station ID", station_id])
   tb.add_row(["Camera ID", cam_id])
   tb.add_row(["Calfiles loaded in DB", len(calfiles_data.keys())])
   tb.add_row(["Calfiles with star data", len(calfile_paired_star_stats.keys())])
   tb.add_row(["Freecal source files", len(freecal_index.keys())])
   rr = str(round(avg_res,2)) + "/" + str(round(avg_res,2) )
   tb.add_row(["Average Res", rr])

   tb2 = pt()
   tb2.field_names = ["File", "Stars", "Res Px", "AZ", "EL", "Angle", "Scale", "Version", "Last Updated (Days)"]
   print("CAL FILES:", len(cal_files))
   cal_files = sorted(cal_files, key=lambda x: x[0], reverse=True)
   for row in cal_files:
      cal_fn, total_stars, avg_res , score = row
      if cal_fn not in calfiles_data:
         print("MISSING FROM CALFILES DATA???", cal_fn)
         continue
      (station_id, camera_id, cal_fn, cal_ts, az, el, ra, dec, position_angle,\
         pixel_scale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
         y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) = calfiles_data[cal_fn]

      tdiff = str((time.time() - last_update ) / 60 / 60 / 24)[0:5]

      tb2.add_row([cal_fn, str(total_stars), str(avg_res), az, el, position_angle, pixel_scale, cal_version, tdiff])


   #print("IN DB:", len(calfiles_data.keys()) )
   #print("WITH STAR DATA:", len(calfile_paired_star_stats.keys()))
   #print("IN FOLDER :", len(freecal_index.keys()) )
   

   print(tb)
   print(tb2)

   #os.system("./Process.py move_exta_cals")
   #os.system("cd /home/ams/amscams/pythonv2/; ./autoCal.py cal_index")

def import_cal_file(cal_fn, cal_dir, mcp):
   #print("import cal file:", cal_fn)
   # load json, insert into main table, insert stars into pairs table
   delete_cal_file(cal_fn, con, cur, json_conf)
   cal_img_file = cal_dir + cal_fn.replace("-calparams.json", ".png")
   if os.path.exists(cal_img_file) is True:
      cal_img = cv2.imread(cal_img_file)
   else:
      print("\tfailed to import:", cal_img_file, "not found")
      cmd = "mv " + cal_dir + " /mnt/ams2/cal/extracal/"
      print("\t import move:", cmd)
      os.system(cmd)
      return()
   if os.path.exists(cal_dir + cal_fn) is True:
      insert_calib(cal_dir + cal_fn , con, cur, json_conf)
      con.commit()
      try:
         cal_params = load_json_file(cal_dir + cal_fn)
      except:
         return()
      cal_params_nlm = cal_params.copy()
      cal_params_nlm['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      sc = 0
      for star in cal_params['cat_image_stars']:
         (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,res_px,bp) = star
         img_x = six
         img_y = siy
         ra_key = str(ra) + "_" + str(dec)
         rx1 = int(new_cat_x - 16)
         rx2 = int(new_cat_x + 16)
         ry1 = int(new_cat_y - 16)
         ry2 = int(new_cat_y + 16)

         if rx1 <= 0 or ry1 <= 0 or rx2 >= 1920 or ry2 >= 1080:
            continue
         star_crop = cal_img[ry1:ry2,rx1:rx2]
         star_cat_info = [dcname,mag,ra,dec,new_cat_x,new_cat_y]
         star_obj = eval_star_crop(star_crop, cal_fn, rx1, ry1, rx2, ry2, star_cat_info)

         try:
            zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params_nlm,json_conf)
         except:
            continue
         zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, ra, dec)

         zp_res_px = calc_dist((img_x,img_y), (zp_cat_x,zp_cat_y))
         try:
            res_deg = angularSeparation(ra,dec,img_ra,img_dec)
         except:
            print("\tRES DEG FAILED TO COMPUTE!")
            continue
         star_obj["cal_fn"] = cal_fn
         star_obj["name"]  = dcname
         star_obj["mag"] = mag
         star_obj["ra"]  = ra
         star_obj["dec"] = dec
         star_obj["new_cat_x"] = new_cat_x
         star_obj["new_cat_y"] = new_cat_y
         star_obj["zp_cat_x"]  = zp_cat_x
         star_obj["zp_cat_y"] = zp_cat_y
         star_obj["img_x"] = img_x
         star_obj["img_y"] = img_y
         star_obj["star_flux"] = star_obj['star_flux']
         star_obj["star_yn"]  = star_obj['star_yn']
         star_obj["star_pd"] = star_obj['pxd']
         star_obj["star_found"] = 1
         if mcp is None:
            star_obj["lens_model_version"] = 1
         else:
            if "cal_version" not in mcp:
               mcp['cal_version'] = 1
            star_obj["lens_model_version"] = mcp['cal_version']
         if new_cat_x == 0 or zp_cat_x == 0:
            continue
       
         try:
            slope = (img_y - new_cat_y) / (img_x - new_cat_x)
         except:
            continue
         try:
            zp_slope = (img_y - zp_cat_y) / (img_x - zp_cat_x)
         except:
            continue

         star_obj["slope"] = slope
         star_obj["zp_slope"] = zp_slope
         star_obj["res_px"] = res_px
         star_obj["zp_res_px"] = zp_res_px
         star_obj["res_deg"] = res_deg
         insert_paired_star(cal_fn, star_obj, con, cur, json_conf)
         sc += 1
         
   else:
      print("\tfailed to import :", cal_dir + cal_fn)
      return()

def batch_review(station_id, cam_id, con, cur, json_conf, limit=25, work_type="top"):

   # load the mask
   mask_file = "/mnt/ams2/meteor_archive/{}/CAL/MASKS/{}_mask.png".format(station_id, cam_id)
   if os.path.exists(mask_file) is True:
      mask = cv2.imread(mask_file)
      #mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
      mask = cv2.resize(mask, (1920,1080))
   else:
      mask = np.zeros((1080,1920),dtype=np.uint8)

   # set some vars
   my_limit = limit
   last_cal = None
   autocal_dir = "/mnt/ams2/cal/"

   # load cal files from Database into an array
   calfiles_data = load_cal_files(cam_id, con, cur)

   # load the multi cal params file
   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
   else:
      mcp = None


   # Build dynamic query to determine res? can replace with function call?
   all_stars = []
   all_res = []
   sql = """
      SELECT a.cal_fn, b.last_update, count(*) as ss, avg(a.res_px) as arp
        FROM calfile_paired_stars a, calibration_files b
       WHERE a.cal_fn like ?
         AND a.res_px is not NULL
         AND a.cal_fn = b.cal_fn
   """

   sql += """
       GROUP bY a.cal_fn
   """

   if work_type == "last_done":
      sql += """
         ORDER BY b.last_update DESC 
         LIMIT {}
      """.format(limit)

   elif work_type == "most_recent":
      sql += """
         ORDER BY a.cal_fn DESC 
         LIMIT {}
      """.format(limit)
   elif work_type == "top":
      sql += """
         ORDER BY ss DESC 
         LIMIT {}
      """.format(limit)
   elif work_type == "worst":
      sql += """
         ORDER BY arp DESC 
         LIMIT {}
      """.format(limit)
   else: 
      sql += """
         ORDER BY ss DESC 
      """ #.format(limit)

         #LIMIT {}
   dvals = ["%" + cam_id + "%"]
   cur.execute(sql, dvals)
   rows = cur.fetchall()
   cal_fns = []

   print("BATCH REVEIW", len(rows), "ROWS")
   new_rows = []
   for row in rows:
      cal_fn, timestmp, t_stars, avg_res = row
      score = t_stars / avg_res
      new_rows.append((cal_fn, timestmp, t_stars, avg_res, score))
   new_rows = sorted(new_rows, key=lambda x: x[4], reverse=True)


   for row in new_rows[0:limit]:
     
      cal_fn, timestmp, t_stars, avg_res,score = row
      print("SCORE:", score)
      all_stars.append(t_stars)
      all_res.append(avg_res)

   med_all_stars = np.median(all_stars)
   med_all_res = np.median(all_res)
   
   # big block above all just to get the med stars and med res for this cam!? rework. 

   # fetch files for this review based on input params / search options
   sql = """
      SELECT cal_fn, count(*) as ss, avg(res_px) as arp,  (count(*) / avg(res_px)) as score
        FROM calfile_paired_stars
       WHERE cal_fn like ?
         AND res_px is not NULL
   """

   sql += """
       GROUP bY cal_fn
       """
   if work_type == "most_recent":
      sql += """
         ORDER BY cal_fn DESC 
         LIMIT {}
      """.format(limit)
   elif work_type == "top":
      sql += """
         ORDER BY score DESC 
         LIMIT {}
      """.format(limit)
   elif work_type == "worst":
      sql += """
         ORDER BY arp desc 
         LIMIT {}
      """.format(limit)
   else: 
      sql += """
         ORDER BY ss DESC 
         LIMIT {}
      """.format(limit)

   dvals = ["%" + cam_id + "%"]
   cur.execute(sql, dvals)
   rows = cur.fetchall()
   cal_fns = []
   cc = 0
   bad_cal_files = []
   
   probs = []

   # make sure all files are valid
   for row in rows:
      more_stars = False
      cal_fn, total_stars, avg_res,score = row
      root = cal_fn.split("-")[0]
      cal_dir = "/mnt/ams2/cal/freecal/" + root 
      if os.path.exists(cal_dir) is False:
         probs.append(root)

   # delete any prob files!
   for prob in probs:
      sql = "DELETE FROM calfile_paired_stars where cal_fn like '%" + prob + "%'" 
      cur.execute(sql)
      sql = "DELETE FROM calibration_files where cal_fn like '%" + prob + "%'" 
      cur.execute(sql)
   con.commit()

   # for each cal_file selected
   for row in rows:
      more_stars = False
      cal_fn, total_stars, avg_res,score = row

      # skip if these things are true
      if total_stars < med_all_stars or total_stars < 20:
         more_stars = True 
         #continue
      if cal_fn not in calfiles_data:
         bad_cal_files.append(cal_fn)
         continue
      if avg_res is None:
         bad_cal_files.append(cal_fn)
         continue
      extra_text = cal_fn + " ( " + str(cc) + " / " + str(len(rows)) + ")"

      # -- RECENTER -- #
      cal_image_file = cal_fn.replace("-calparams.json", ".png")
      cal_dir = cal_dir_from_file(cal_image_file)
      cal_json_file = get_cal_json_file(cal_dir)
      if cal_json_file is None:
         print("no cal_json file")
         continue
      cal_json_fn = cal_json_file.split("/")[-1]
      oimg = cv2.imread(cal_dir + cal_image_file)
      orig_img = oimg.copy()

      # load mask
      mask_file = "/mnt/ams2/meteor_archive/{}/CAL/MASKS/{}_mask.png".format(station_id, cam_id)
      if os.path.exists(mask_file) is True:
         mask = cv2.imread(mask_file)
         mask = cv2.resize(mask, (1920,1080))
      else:
         mask = np.zeros((1080,1920,3),dtype=np.uint8)
      oimg = cv2.subtract(oimg, mask)
      orig_img = cv2.subtract(orig_img, mask)

      try:
         cal_params = load_json_file(cal_json_file)
         ores = cal_params['total_res_px']
      except:
         print("BAD FILE:", cal_json_file)
         print("BAD DIR :", cal_dir)
         continue
      if mcp is not None:
         cal_params['x_poly'] = mcp['x_poly']
         cal_params['y_poly'] = mcp['y_poly']
         cal_params['y_poly_fwd'] = mcp['y_poly_fwd']
         cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      else:
         cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)



      cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
      cal_params['short_bright_stars'] = short_bright_stars


      #cat_stars = pair_star_points(cal_fn, oimg, new_cp, json_conf, con, cur, mcp, True)

      stars,cat_stars = get_paired_stars(cal_fn, cal_params, con, cur)
      cal_params['cat_image_stars'] = cat_stars
      # Need to modes here?
      

      if cal_params['total_res_px'] > med_all_res and last_cal is not None:
         # use last best
         if False: # More work is needed to test vals after! 
            cal_params['center_az'] = last_cal['center_az']
            cal_params['center_el'] = last_cal['center_el']
            cal_params['position_angle'] = last_cal['position_angle']
            cal_params['pixscale'] = last_cal['pixscale']
            cal_params = update_center_radec(cal_fn,cal_params,json_conf)


      star_img = draw_star_image(oimg, cal_params['cat_image_stars'],cal_params, json_conf, extra_text) 
      if SHOW == 1:
         print("JUST DREW STAR IMAGED")
         cv2.imshow('pepe', star_img)
         cv2.waitKey(0)


      if "cal_fn" not in cal_params:
         cal_params['cal_fn'] = cal_fn
      



      # check / remove dupes
      used = {}
      dupes = {}
      new_stars = []
      for star in cal_params['cat_image_stars'] :
         (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
         key = str(ra) + "_" + str(dec)
         if key not in used:
            new_stars.append(star)
            used[key] = 1
         else:
            if key not in dupes:
               dupes[key] = 1
            else:
               dupes[key] += 1
            print("DUPE:", star)

      cal_params['cat_image_stars'] = new_stars
      print("NEW STARS:", len(new_stars))

      new_cal_params, del_stars = delete_bad_stars(cal_fn, cal_params, con,cur,json_conf, orig_img) 

      new_cal_params = minimize_fov(cal_fn, cal_params, cal_image_file,oimg,json_conf, False,mcp, extra_text)

      new_cal_params = calc_res_from_stars(cal_fn, new_cal_params, json_conf)

            # if the results from apply are still bad try to make better
      last_cal_params = new_cal_params
      if True:
         if True:
            if last_cal_params['total_res_px'] > 5:
               #print(cal_fn, " is FAILING. We will try to fix" )
               #cal_params = fix_cal(cal_fn, con, cur, json_conf)
               cal_params = calc_res_from_stars(cal_fn, cal_params, json_conf)
               print("AFTER FIXED RES:", cal_params['total_res_px'])
               if cal_params['total_res_px'] < last_cal_params['total_res_px'] and cal_params['total_res_px'] < 5:
                  save_json_file(cal_dir + cal_fn, cal_params)
               else:
                  # all else has failed resolve the file!
                  # if we already did it just update the calparams with astr info

                  cal_file_temp = cal_dir + "tmp/" + cal_fn
                  cal_file = cal_dir + "" + cal_fn
                  wcs_file = cal_file_temp.replace("-stacked-calparams.json", "-plate.wcs")
                  wcs_info_file = cal_file.replace("-stacked-calparams.json", "-plate.wcs_info")
                  #print(cal_file, wcs_info_file)
                  if os.path.exists(wcs_info_file):
                     new_cal_params = wcs_to_cal_params(wcs_file,json_conf)
                     cal_params = load_json_file(cal_file)
                     cal_params['ra_center'] = new_cal_params['ra_center']
                     cal_params['dec_center'] = new_cal_params['dec_center']
                     cal_params['center_az'] = new_cal_params['center_az']
                     cal_params['center_el'] = new_cal_params['center_el']
                     cal_params['position_angle'] = new_cal_params['position_angle']
                     cal_params['pixscale'] = new_cal_params['pixscale']
                     save_json_file(cal_params_file, cal_params)
                  else:
                     plate_file, plate_img = make_plate(cal_fn, json_conf, con, cur)
                     result = solve_field(plate_file, json_conf, con, cur)

                     if result is True:
                        print("Resolve worked!")
                     else:
                        print("Resolve failed! Just delete this calfile!!! It can't be saved.")

      #if mcp is not None:
      #   new_cal_params = minimize_fov(cal_fn, new_cal_params, cal_image_file,oimg,json_conf, mcp)


      print("NEW:", new_cal_params['total_res_px'], "OLD:", cal_params['total_res_px'])
      # ALWAYS SAVE!

      if os.path.exists(cal_json_file):
         up_stars, cat_image_stars = update_paired_stars(cal_fn, new_cal_params, stars, con, cur, json_conf)
         new_cal_params['cat_image_stars'] = cat_image_stars
         update_calibration_file(cal_fn, new_cal_params, con,cur,json_conf,mcp)
         save_json_file(cal_json_file, new_cal_params)
      last_cal = dict(new_cal_params)


      # -- END RECENTER -- #
      if cal_fn in calfiles_data:
         cal_fns.append(cal_fn)
      cc += 1
      if len(cal_params['cat_image_stars']) * 2 < med_all_stars:
         cmd = "mv " + cal_dir + " /mnt/ams2/cal/extracal/"
         os.system(cmd)

   print("\tBAD CAL FILES:", bad_cal_files)
   print("\tCAL FILES:", len(calfiles_data))

   for fn in cal_fns:
      root = fn.split("-")[0]
      cal_dir = "/mnt/ams2/cal/freecal/" + root + "/"
      if os.path.exists(cal_dir) is False:
         print("BAD:", cal_dir)
      else:
         print("GOOD :", cal_dir)
      if fn in calfiles_data:
         print("GOOD:", fn)
      else:
         print("BAD:", fn)

   return(cal_fns, calfiles_data)

def revert_to_wcs(cal_fn,mcp=None):


   cal_dir = "/mnt/ams2/cal/freecal/" + cal_fn.replace("-stacked-calparams.json", "") + "/"
   cal_file = cal_dir + cal_fn
   cal_img_file = cal_dir + "tmp/" + cal_fn.replace("-stacked-calparams.json", "-plate.jpg")
   cal_img = cv2.imread(cal_img_file)
   wcs_file = cal_dir + "tmp/" + cal_fn.replace("-stacked-calparams.json", "-plate.wcs")
   wcs_info_file = cal_dir + "tmp/" + cal_fn.replace("-stacked-calparams.json", "-plate.wcs_info")
   #print(cal_file, wcs_info_file)
   cal_params = load_json_file(cal_file)
   if os.path.exists(wcs_info_file):
      new_cal_params = wcs_to_cal_params(wcs_file,json_conf)
      cal_params['imagew'] = 1920
      cal_params['imageh'] = 1080
      cal_params['ra_center'] = new_cal_params['ra_center']
      cal_params['dec_center'] = new_cal_params['dec_center']
      cal_params['center_az'] = new_cal_params['center_az']
      cal_params['center_el'] = new_cal_params['center_el']
      cal_params['position_angle'] = new_cal_params['position_angle']
      cal_params['pixscale'] = new_cal_params['pixscale']
      cal_params['wcs'] = {}
      cal_params['wcs']['ra_center'] = new_cal_params['ra_center']
      cal_params['wcs']['dec_center'] = new_cal_params['dec_center']
      cal_params['wcs']['center_az'] = new_cal_params['center_az']
      cal_params['wcs']['center_el'] = new_cal_params['center_el']
      cal_params['wcs']['position_angle'] = new_cal_params['position_angle']
      cal_params['wcs']['pixscale'] = new_cal_params['pixscale']
   else:
      print("NO WCS FILE", cal_file, wcs_info_file)
      plate_file, plate_img = make_plate(cal_fn, json_conf, con, cur)
      result = solve_field(plate_file, json_conf, con, cur)
      time.sleep(10)

      return(None)

   if mcp is not None:
      cal_params['x_poly'] = mcp['x_poly']
      cal_params['y_poly'] = mcp['y_poly']
      cal_params['y_poly_fwd'] = mcp['y_poly_fwd']
      cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
   else:
      cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params['cat_image_stars'] = pair_star_points(cal_fn, cal_img, cal_params.copy(), json_conf, con, cur, mcp, save_img = False)
   stars,cat_stars = get_paired_stars(cal_fn, cal_params, con, cur)
   temp_cal_params, cat_stars = recenter_fov(cal_fn, cal_params, cal_img.copy(),  stars, json_conf, "", None, cal_img, con, cur)
   if temp_cal_params['total_res_px'] < cal_params['total_res_px']:
      cal_params = temp_cal_params.copy()
   save_json_file(cal_file, cal_params)
   return(cal_params)

def pair_star_points(cal_fn, oimg, cal_params, json_conf, con, cur, mcp, save_img=False):
   used_img = np.zeros((1080,1920),dtype=np.uint8)
   (f_datetime, cam_id, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(cal_fn)
   show_img = oimg.copy()
   sql = "DELETE FROM calfile_catalog_stars where cal_fn = '{:s}'".format(cal_fn)
   cur.execute(sql)
   con.commit()


   cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
   for star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
      if new_cat_x < 10 or new_cat_y < 10 or new_cat_x > 1910 or new_cat_y > 1070:
         continue

      desc = name + " " + str(mag)
      sql = """
               INSERT OR REPLACE INTO calfile_catalog_stars (
                      cal_fn,
                      name,
                      mag,
                      ra,
                      dec,
                      new_cat_x,
                      new_cat_y,
                      zp_cat_x,
                      zp_cat_y 
               ) 
               VALUES (?,?,?,?,?,?,?,?,?)
      """
      ivals = [cal_fn, name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y]
      cur.execute(sql, ivals)
      #try:
      #   cur.execute(sql, ivals)
      #except:
      #   print("Must be done already")

   con.commit()

   # loop over each star point in the image and find a pair
   up_cat_image_stars = []
   if "star_points" not in cal_params:
      cal_dir = "/mnt/ams2/cal/freecal/" + cal_fn.replace("-stacked-calparams.json", "") + "/tmp/" 
      if os.path.exists(cal_dir + cal_fn.replace("-stacked-calparams.json", "-plate.jpg")):
         cal_img = cv2.imread(cal_dir + cal_fn.replace("-stacked-calparams.json", "-plate.jpg"))
      else:
         cal_img = None
         cal_img = oimg
      resp = get_star_points(cal_fn, cal_img, cal_params, station_id, cam_id, json_conf)
      if resp is not None:
         star_points, star_img = resp
      else:
         star_points = []
      cal_params['star_points'] = star_points
   for img_x,img_y,star_flux in cal_params['star_points']:
      # this is not really flux here, but the brightest pixel!
      star_obj = {}
      star_obj['cal_fn'] = cal_fn
      star_obj['x'] = img_x
      star_obj['y'] = img_y
      star_obj['star_flux'] = star_flux


      cv2.circle(show_img, (int(img_x), int(img_y)), 5, (128,128,128),1)
      close_stars = find_close_stars(star_obj)
      if len(close_stars) >= 1:
         for star in close_stars[0:1]:

            cal_fn, name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, \
            x_img_x, x_img_y, star_flux, star_yn, star_pd, star_found, lens_model_version, \
            slope, zp_slope, dist, zp_dist = star
            img_x = star_obj['x'] 
            img_y = star_obj['y'] 



            if new_cat_x is not None and img_x is not None:
      
               new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params,json_conf)

               res_px = calc_dist((img_x,img_y),(new_cat_x,new_cat_y))
               match_dist = angularSeparation(ra,dec,img_ra,img_dec)
               if res_px < 40 and used_img[int(img_y),int(img_x)] != 200 :
                  color = [0,255,0]
                  up_cat_image_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) )
                  used_img[int(img_y),int(img_x)] = 200
                  if 0 <= new_cat_x < 1920 and 0 <= new_cat_y < 1080:
                     used_img[int(new_cat_y),int(new_cat_x)] = 200
               else:
                  color = [0,0,255]
               cv2.line(show_img, (int(zp_cat_x),int(zp_cat_y)), (int(img_x),int(img_y)), color, 1)
               cv2.putText(show_img, str(dist)[0:4],  (int(new_cat_x),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (200,200,200), 1)
            #else:
            #if SHOW == 1:
            #   cv2.imshow('pepe', show_img)

   cal_dir = "/mnt/ams2/cal/freecal/" + cal_fn.replace("-stacked-calparams.json", "/")

   return(up_cat_image_stars)
      

def re_pair_stars(cal_fn, cp, json_conf, show_img, con, cur,mcp):
   # NOT WORKING!
   star_cat_dict = {}
   star_img_dict = {}
   new_cat_stars = []
   # if already there we can skip!
   for star in cp['cat_image_stars']:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      ra_key = str(ra) + "_" + str(dec)
      img_key = str(int(six)) + "_" + str(int(siy))
      if ra_key not in star_cat_dict:
         star_cat_dict[ra_key] = star
      if img_key not in star_img_dict:
         star_img_dict[img_key] = star
      new_cat_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp))

   for star in cp['star_points']:
      x, y, bp = star
      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(x,y,cal_fn,cp,json_conf)
      img_key = str(int(x)) + "_" + str(int(y))
      if img_key in star_img_dict:
         cv2.circle(show_img, (int(x),int(y)), 15, (128,255,128),1)
         continue 
      
      matches = []
      for cat_star in cp['short_bright_stars']:
         (name, name2, ra, dec, mag,new_cat_x,new_cat_y,zp_cat_x, zp_cat_y, rx1,ry1,rx2,ry2) = cat_star
         ra_key = str(ra) + "_" + str(dec)
         if ra_key in star_cat_dict:
            continue 

         new_cat_x, new_cat_y = get_xy_for_ra_dec(cp, ra, dec)
         res_px = calc_dist((x,y),(new_cat_x,new_cat_y))
         match_dist = angularSeparation(ra,dec,img_ra,img_dec)
         if match_dist < .5 or res_px <= 10:
            #print("--- NEW ---", name, match_dist, res_px)
            matches.append((cat_star, match_dist))
            cv2.circle(show_img, (int(x),int(y)), 15, (255,255,0),2)
            cv2.line(show_img, (int(new_cat_x),int(new_cat_y)), (int(x),int(y)), (128,128,128), 1)
            cv2.circle(show_img, (int(x),int(y)), 5, (255,255,255),1)
            cv2.circle(show_img, (int(new_cat_x),int(new_cat_y)), 5, (128,128,255),1)
            if SHOW == 1:
               cv2.imshow('pepe', show_img)
               cv2.waitKey(30)
            star_cat_dict[ra_key] = star
            star_img_dict[img_key] = star
      matches = sorted(matches, key=lambda x: x[1], reverse=False)
      if len(matches) > 0:
         #print("CLOSESEST:", matches[0])
         new_cat_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp))
         new_star = (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp)
         insert_paired_star_full(new_star, cal_fn, cp, mcp, json_conf)

   cp['cat_image_stars'] = new_cat_stars

   #print("REPAIR DONE")
   #print("NEW CAT IMG STARS!", len(cp['cat_image_stars']))

   return(cp)

def wcs_to_cal_params(wcs_file,json_conf):
   wcs_info_file = wcs_file.replace(".wcs", ".wcs_info")
   cal_params_file = wcs_file.replace("-plate.wcs", "-calparams.json")
   fp =open(wcs_info_file, "r")
   cal_params_json = {}
   cal_root = wcs_file.split("/")[-1].replace("-plate.wcs", "")
   cam_id = cal_root.split("_")[-1]
   cal_params_json['cal_root'] = cal_root
   cal_params_json['cam_id'] = cam_id 
   for line in fp:
      line = line.replace("\n", "")
      field, value = line.split(" ")
      if field == "imagew":
         cal_params_json['imagew'] = value
      if field == "imageh":
         cal_params_json['imageh'] = value
      if field == "pixscale":
         cal_params_json['pixscale'] = value
      if field == "orientation_center":
         if float(value) < 0:
            cal_params_json['position_angle'] = float(value) + 360 
         else:
            cal_params_json['position_angle']  = float(value)
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

   ra = cal_params_json['ra_center']
   dec = cal_params_json['dec_center']
   lat = json_conf['site']['device_lat']
   lon = json_conf['site']['device_lng']
   alt = json_conf['site']['device_alt']

   (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(wcs_file)
   new_date = y + "/" + m + "/" + d + " " + h + ":" + mm + ":" + s
   az, el = radec_to_azel(ra,dec, new_date,json_conf)

   cal_params_json['center_az'] = az
   cal_params_json['center_el'] = el
   #cal_params = default_cal_params(cal_params, json_conf)
   cal_params_json = update_center_radec(wcs_file,cal_params_json,json_conf)


   #save_json_file(cal_params_file, cal_params_json)
   return(cal_params_json)

def solve_field(plate_file, json_conf, con, cur):
   if plate_file is None:
      print("PLATE FILE IS NONE")
      return(plate_file)
   station_id = json_conf['site']['ams_id']
   if os.path.exists("/usr/local/astrometry/bin/solve-field") is True:
      AST_BIN = "/usr/local/astrometry/bin/"
   elif os.path.exists("/usr/bin/solve-field") is True:
      AST_BIN = "/usr/bin/"
   plate_fn = plate_file.split("/")[-1]
   cal_dir = plate_file.replace( plate_fn, "")


   plate_fn = plate_file.split("/")[-1]
   plate_dir = plate_file.replace(plate_fn, "")
   if os.path.exists(plate_dir + "tmp") is False:
      os.makedirs(plate_dir + "tmp/")
   new_plate_file = plate_dir + "tmp/" + plate_fn 
   cmd = "cp " + plate_file + " " + new_plate_file
   print(cmd)
   os.system(cmd)
   cal_params_file = plate_file.replace("-plate.jpg", "-stacked-calparams.json")

   plate_file = new_plate_file
   solved_file = plate_file.replace(".jpg", ".solved")
   astrout = plate_file.replace(".jpg", ".astrometry_log")
   wcs_file = plate_file.replace(".jpg", ".wcs")
   wcs_info_file = plate_file.replace(".jpg", ".wcs_info")

   cmd = AST_BIN + "solve-field " + new_plate_file + " --cpulimit=30 --verbose --overwrite --crpix-center -d 1-40 --scale-units dw --scale-low 60 --scale-high 120 "
   #-S " + solved_file + " >" + astrout
   #cmd = AST_BIN + "solve-field " + new_plate_file + " --cpulimit=30 --verbose --overwrite --scale-units dw --scale-low 60 --scale-high 120 " #| grep at >"  + astrout
   cmd = AST_BIN + "solve-field " + new_plate_file + " --cpulimit=30 --verbose --overwrite  --scale-units arcsecperpix --scale-low 150 --scale-high 170" #| grep at >"  + astrout
   print(cmd)
   os.system(cmd)
   print(cmd)
   if os.path.exists(wcs_file) is True:
      cmd = AST_BIN + "wcsinfo " + wcs_file + " > " + wcs_info_file
      os.system(cmd)
      new_cal_params = wcs_to_cal_params(wcs_file,json_conf)
      # save new cal params to file and then apply calib 
      #print(cal_params_file)
      cal_params = load_json_file(cal_params_file)
      cal_params['ra_center'] = new_cal_params['ra_center']
      cal_params['dec_center'] = new_cal_params['dec_center']
      cal_params['center_az'] = new_cal_params['center_az']
      cal_params['center_el'] = new_cal_params['center_el']
      cal_params['position_angle'] = new_cal_params['position_angle']
      cal_params['pixscale'] = new_cal_params['pixscale']
      save_json_file(cal_params_file, cal_params)
      cal_fn = cal_params_file.split("/")[-1]

      (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)
      autocal_dir = "/mnt/ams2/cal/"
      mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
      if os.path.exists(mcp_file) == 1:
         mcp = load_json_file(mcp_file)
      else:
         mcp = None

      calfiles_data = load_cal_files(cam_id, con, cur)
      result = apply_calib (cal_fn, calfiles_data, json_conf, mcp, None, "", False, None)
      return(True)


   else:
      print("Astrometry.net failed")
      if os.path.exists("/mnt/ams2/cal/bad_cals/") is False:
         os.makedirs("/mnt/ams2/cal/bad_cals/")
      cmd = "mv " + cal_dir + " /mnt/ams2/cal/bad_cals/" 
      print(cmd)
      os.system(cmd)
      return(False)

def best_wcs(cal_fn, cal_params, oimg, con, cur, mcp):

   all_wcs_file = "/mnt/ams2/cal/wcs_index.json"
   if os.path.exists(all_wcs_file) is True:
      all_wcs = load_json_file(all_wcs_file)
      print(all_wcs)
   else:
      print("NO WCS")
      return(cal_params)
   best_cp = cal_params.copy()

   for row in all_wcs:
      new_cp = cal_params.copy()
      #print(cam_id, row)
      if row['cam_id'] == cam_id:
         #print(row['center_az'], row['center_el'], row['position_angle'], row['pixscale'] )
         new_cp['center_az'] = row['center_az']
         new_cp['center_el'] = row['center_el']
         new_cp['position_angle'] = row['position_angle']
         new_cp['pixscale'] = row['pixscale']
         new_cp = update_center_radec(row['cal_root'],new_cp,json_conf)
         new_cp['cat_image_stars'] = pair_star_points(cal_fn, oimg, new_cp, json_conf, con, cur, mcp,  False)
         new_cp , bad_stars, marked_img = eval_cal_res(cal_fn, json_conf, new_cp.copy(), oimg,None,None,new_cp['cat_image_stars'])

         oscore =  len(best_cp['cat_image_stars']) / best_cp['total_res_px']
         score =  len(new_cp['cat_image_stars']) / new_cp['total_res_px']
         print("RA/DEC", new_cp['ra_center'], new_cp['dec_center'])
         print("AZ/EL", new_cp['center_az'], new_cp['center_el'])
         print("POS/PX", new_cp['position_angle'], new_cp['pixscale'])
         print("STARS/RES", len(new_cp['cat_image_stars']), new_cp['total_res_px'])
         print("OSCORE/SCORE", oscore, score)
         #if score < oscore:
         print("WCS TRY", row['cal_root'], score, "SCORE", len(new_cp['cat_image_stars']),  "STARS", new_cp['total_res_px'], "RES PX")
    
         #if new_cp['total_res_px'] <  best_cp['total_res_px'] : #or score < oscore:
         if score >  oscore:
            best_cp = new_cp
            print("WCS BEST ", row['cal_root'], score, "SCORE", len(new_cp['cat_image_stars']),  "STARS", new_cp['total_res_px'], "RES PX")
         #else:
         #   print("WCS ", row['cal_root'], score, "SCORE", len(new_cp['cat_image_stars']),  "STARS", new_cp['total_res_px'], "RES PX", best_cp['total_res_px'])
         #print(new_cp['total_res_px'])
   return(best_cp)


def run_astr(cam_id, json_conf, con, cur):
   # check and run if needed astronomy on all calfiles matching the cam_id
   cal_index = load_json_file("/mnt/ams2/cal/freecal_index.json")
   all_wcs_file = "/mnt/ams2/cal/wcs_index.json"
   all_wcs = []
   for cal_file in cal_index:
      data = cal_index[cal_file]
      cal_fn = cal_file.split("/")[-1]
      cal_dir = cal_file.replace(cal_fn, "")
      wcs_info_file = cal_dir + "tmp/" + cal_fn.replace("-stacked-calparams.json", "-plate.wcs_info")
      wcs_file = cal_dir + "tmp/" + cal_fn.replace("-stacked-calparams.json", "-plate.wcs")
      if os.path.exists(cal_dir) is False:
         print("No exists")
         continue
      if cam_id == data['cam_id']:

         print("Matched cam")
         if os.path.exists(wcs_file) is True:
            print("FOUND", wcs_file)
         else:
            print("NOT FOUND", wcs_info_file)
            print("CAL FN", cal_fn)
            plate_file, plate_img = make_plate(cal_fn, json_conf, con, cur)
            result = solve_field(plate_file, json_conf, con, cur)
            print("RESULT:", result)
   # assemble the WCS INFO across all files

   #wcs_info = load_json_file(wcs_info_file)
      if os.path.exists(wcs_file):
         wcs_cal_params = wcs_to_cal_params(wcs_file,json_conf)
         all_wcs.append(wcs_cal_params)
   save_json_file(all_wcs_file, all_wcs)

   groups = {}

   for row in all_wcs:
      groups = {}
      if row['cam_id'] == cam_id:
         print(row['center_az'], row['center_el'], row['position_angle'], row['pixscale'] )
         groups = find_make_group(row, groups)
   print(all_wcs_file )
   for gid in groups:
      print(gid, groups[gid])
  
def find_make_group(row, groups):
   if len(groups) == 0: 
      groups[0] = {}
      groups[0]['az'] = []
      groups[0]['el'] = []
      groups[0]['pos'] = []
      groups[0]['pxs'] = []
      groups[0]['az'].append(row['center_az'])
      groups[0]['el'].append(row['center_el'])
      groups[0]['pos'].append(row['position_angle']) 
      groups[0]['pxs'].append(row['pixscale'])
      return(groups)
   else:
      for gid in groups:
         mean_az = np.mean(groups[gid]['az'])
         mean_el = np.mean(groups[gid]['el'])
         mean_pos = np.mean(groups[gid]['pos'])
         mean_pxs = np.mean(groups[gid]['pxs'])

         az_diff = abs(row['center_az'] - mean_az)
         el_diff = abs(row['center_el'] - mean_el)
         pos_diff = abs(row['position_angle'] - mean_pos)
         pxs_diff = abs(row['pixscale'] - mean_pxs)

         if az_diff < 1 and el_diff < 1 and pos_diff > 1 and pxs_diff > 1:
            groups[gid]['az'].append(row['center_az'])
            groups[gid]['el'].append(row['center_el'])
            groups[gid]['pos'].append(row['position_angle']) 
            groups[gid]['pxs'].append(row['pixscale'])
            return(groups)
   # no group found and not first group so make new group
   gid = max(groups.keys()) + 1
   groups[gid]['az'].append(row['center_az'])
   groups[gid]['el'].append(row['center_el'])
   groups[gid]['pos'].append(row['position_angle']) 
   groups[gid]['pxs'].append(row['pixscale'])
   return(groups)


def make_plate(cal_fn, json_conf, con, cur):

   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)
   mcp = get_mcp(cam_id) 

   calfiles_data = load_cal_files(cam_id, con, cur)

   plate_img = np.zeros((1080,1920),dtype=np.uint8)

   resp = start_calib(cal_fn, json_conf, calfiles_data, mcp)
   if resp is None:
      print(resp)
      print("start Calib failed!", cal_fn)
      return(None, None)
   else:
      print("RESP to start calib:", resp)
      try:
         (station_id, cal_dir, cal_json_file, cal_img_file, cal_params, cal_img, clean_cal_img, mask_file,mcp) = resp
      except:
         return(None,None)

   plate_file = cal_dir + cal_fn.replace("-stacked-calparams.json", "-plate.jpg")
   gray_img = cv2.cvtColor(clean_cal_img, cv2.COLOR_BGR2GRAY)

   stack_jpg_file = plate_file.replace("-plate.jpg", "-stacked.jpg")
   if os.path.exists(stack_jpg_file) is True:
      os.system("cp " + stack_jpg_file + " " + plate_file)
      stack_jpg = cv2.imread(stack_jpg_file)
      print("USING ORIGINAL PLATE")
      return(plate_file, stack_jpg)
   else:
      resp = get_star_points(cal_fn, clean_cal_img, cal_params, station_id, cam_id, json_conf)
      if resp is not None:
         star_points, star_img = resp
      else:
         print("GET STAR POINTS RESP:", resp)
         star_points = []


      plate_image, star_points = make_plate_image(gray_img.copy(), star_points)
      #plate_file = image_file.replace(".png", ".jpg")
      cv2.imwrite(plate_file, plate_image)
      print("MADE NEW PLATE IMAGE!" + plate_file)


   resp = get_star_points(cal_fn, clean_cal_img, cal_params, station_id, cam_id, json_conf)

   if resp is not None:
      star_points, star_img = resp
   else:
      print("GET STAR POINTS RESP:", resp)
      star_points = []
      

   for x,y,bp in star_points:
      x1 = x - 5 
      y1 = y - 5
      x2 = x + 5
      y2 = y + 5
      plate_img[y1:y2,x1:x2] = gray_img[y1:y2,x1:x2]
      if x1 <= 0 or x2 >= 1920 or y1 < 0 or y2 >= 1080:
         continue
   if SHOW == 1:
      cv2.imshow('pepe', plate_img)
      cv2.waitKey(30)
   print(plate_file)
   cv2.imwrite(plate_file, plate_img)
   return(plate_file, plate_img)

def ui_frame():
   logo = cv2.imread("ALLSKY_LOGO.png")
   logo = imutils.resize(logo, width=1280)
   ui = np.zeros((1080,1920,3),dtype=np.uint8)
   # main
   cv2.rectangle(ui, (0,0), (1280,720) , [255,255,255], 1)
   # logo right top
   #cv2.rectangle(ui, (1280,0), (1920,158) , [255,255,255], 1)
   # 2nd frame (with logo right top)
   #cv2.rectangle(ui, (1280,158), (1920,360+158) , [255,255,255], 1)

   cv2.rectangle(ui, (1280,0), (1920,360) , [255,255,255], 1)
   cv2.rectangle(ui, (1280,360), (1920,720) , [255,255,255], 1)
   cv2.rectangle(ui, (0,720), (1280,317+720) , [255,255,255], 1)
   ui[740:317+740,2:1282] = logo
   cv2.rectangle(ui, (1280,720), (1920,1080) , [255,255,255], 1)
   
   #make empty ui frame
   return(ui)

def star_points_report(cam_id, json_conf, con, cur):
   mcp = get_mcp(cam_id)
   ui_img = ui_frame()
   if SHOW == 1:
      cv2.namedWindow("pepe")
      cv2.resizeWindow("pepe", 1920, 1080)
      cv2.moveWindow("pepe", 1400,100)


   hdmx_360 = 640 / 1920
   hdmy_360 = 360 / 1080
   photo_credit = make_photo_credit(json_conf, cam_id)

   calfiles_data = load_cal_files(cam_id, con, cur)
   mcp = get_mcp(cam_id) 
   station_id = json_conf['site']['ams_id']
   # make / verify star points and associated files for all cal_files in the system!

   all_merged_stars = []
   all_merged_stars_file = "/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json"

   console_image = np.zeros((360,640,3),dtype=np.uint8)


   zp_image = np.zeros((1080,1920,3),dtype=np.uint8)
   zp_image_small = np.zeros((360,640,3),dtype=np.uint8)
   for cal_fn in calfiles_data:
      cal_dir = "/mnt/ams2/cal/freecal/" + cal_fn.replace("-stacked-calparams.json", "/")
      cal_img_file = cal_dir + cal_fn.replace("-calparams.json", ".png")
      cal_json_file = cal_dir + cal_fn
      star_points_file = cal_dir + cal_fn.replace("-calparams.json", "-star-points.json")
      star_pairs_file = cal_dir + cal_fn.replace("-calparams.json", "-star-pairs.json")
      star_points_image_file = cal_dir + cal_fn.replace("-calparams.json", "-star-points.jpg")
      star_pairs_image_file = cal_dir + cal_fn.replace("-calparams.json", "-star-pairs.jpg")



      if os.path.exists(cal_img_file):
         cal_img = cv2.imread(cal_img_file)

      if os.path.exists(star_points_image_file):
         star_points_img = cv2.imread(star_points_image_file)
      if os.path.exists(star_pairs_image_file):
         star_pairs_img = cv2.imread(star_pairs_image_file)
      if os.path.exists(star_points_file):
         cp = load_json_file(cal_json_file)

         before_ra = cp['ra_center']
         before_dec = cp['dec_center']
         before_pos = cp['position_angle']
         before_pxs = cp['pixscale']
         before_res = cp['total_res_px']

         if mcp is not None:
            cp['x_poly'] = mcp['x_poly']
            cp['y_poly'] = mcp['y_poly']
            cp['y_poly_fwd'] = mcp['y_poly_fwd']
            cp['x_poly_fwd'] = mcp['x_poly_fwd']
         else:
            cp['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
            cp['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
            cp['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
            cp['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)



         try:
            star_pairs= load_json_file(star_pairs_file)
            star_points = load_json_file(star_points_file)
         except:
            print("FAILED:", star_pairs_file)
            continue

         cat_image_stars = []

         # HERE WE SHOULD DO SOMETHING..
         # TO UPDATE WITH THE LATEST PARAMS
         # AND RESAVE THE PAIRS!
         new_star_pairs = []
         for star in star_pairs:
            (hip_id, name_ascii, cons, mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,x,y,zp_cat_x,zp_cat_y,slope,zp_slope,res_px,flux) = star

            new_cat_x, new_cat_y = get_xy_for_ra_dec(cp, ra, dec)
            new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(x,y,cal_fn,cp,json_conf)
            img_new_cat_x, img_new_cat_y = get_xy_for_ra_dec(cp, img_ra, img_dec)
            new_star_pairs.append((hip_id, name_ascii, cons, mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,x,y,zp_cat_x,zp_cat_y,slope,zp_slope,res_px,flux)) 

            cat_image_stars.append((name_ascii,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,x,y,res_px,flux))

          
            all_merged_stars.append((cal_fn, cp['center_az'], cp['center_el'], cp['ra_center'], cp['dec_center'], cp['position_angle'], cp['pixscale'], name_ascii, mag,ra,dec,ra,dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,x,y,res_px,flux))

            if res_px <= 5:
               color = [20,255,57]
               bad = False 
            elif 5 < res_px <= 10:
               color = [152,251,152]
               bad = False 
            else:
               bad = True
               color = [0,0,255]
            cv2.line(zp_image, (int(zp_cat_x),int(zp_cat_y)), (int(x),int(y)), color, 1)
           
            zp_cat_x_sm = int(zp_cat_x * hdmx_360)
            zp_cat_y_sm = int(zp_cat_y * hdmy_360)
            x_sm = int(x * hdmx_360)
            y_sm = int(y * hdmy_360)

            cv2.line(zp_image_small, (int(zp_cat_x_sm),int(zp_cat_y_sm)), (int(x_sm),int(y_sm)), color, 1)

         desc = str(len(star_pairs)) + " / " + str(len(star_points))
         perc_good = int((len(star_pairs) / len(star_points)) * 100)
         desc += " = " + str(perc_good) + "%"
         if perc_good < 50:
            color = [0,0,255]
         else:
            color = [0,255,0]

         cp['cat_image_stars'] = cat_image_stars

         # all_res, inner_res, middle_res, outer_res = recalc_res(cp)
         all_res, inner_res, middle_res, outer_res,cp = recalc_res(cal_fn, cp , json_conf)

         cal_img_720 = cv2.resize(cal_img, (1280,720))
         stars_image = draw_stars_on_image(cal_img_720, cat_image_stars,cp,json_conf,extra_text=None,img_w=1280,img_h=720) 

         final_img = ui_img.copy()
         main_frame_img = cv2.resize(star_pairs_img,(1280,720))
         sub_frame_img_2 = cv2.resize(cal_img, (640,360))
         sub_frame_img_1 = zp_image_small 


         text_data = []
         text_data.append((20,10,photo_credit))

         az = round(cp['center_az'],1)
         el = round(cp['center_el'],1)
         ra = round(float(cp['ra_center']),1)
         dec = round(float(cp['dec_center']),1)
         pos = round(float(cp['position_angle']),1)
         pixscale = round(float(cp['pixscale']),1)
         all_res = round(all_res,1)

         text_data.append((20,50,"Total Stars"))
         text_data.append((250,50,str(len(cp['cat_image_stars']))))
         text_data.append((20,75,"Residuals"))
         text_data.append((250,75,str(all_res)))
         text_data.append((20,100,"Azimuth"))
         text_data.append((250,100,str(az)))
         text_data.append((20,125,"Elevation"))
         text_data.append((250,125,str(el)))
         text_data.append((20,150,"Ra"))
         text_data.append((250,150,str(ra)))
         text_data.append((20,175,"Dec"))
         text_data.append((250,175,str(dec)))
         text_data.append((20,200,"Position Angle"))
         text_data.append((250,200,str(pos)))
         text_data.append((20,225,"Pixel Scale"))
         text_data.append((250,225,str(pixscale)))


         console_frame = draw_text_on_image(console_image.copy(), text_data)

         final_img[0:720,0:1280] = stars_image #main_frame_img
         final_img[0:360,1280:1920] = sub_frame_img_1 
         final_img[360:720,1280:1920] = sub_frame_img_2
         final_img[720:1080,1280:1920] = console_frame 
       
         if SHOW == 1:
            cv2.imshow('pepe', final_img)
            cv2.waitKey(30)

         center_stars = cp['cat_image_stars']

         extra_text = "minimize cal params"

         new_cp = minimize_fov(cal_fn, cp, cal_fn,cal_img,json_conf, False,mcp, extra_text, show=0)

         stars_image = draw_stars_on_image(cal_img_720, new_cp['cat_image_stars'],new_cp,json_conf,extra_text=None,img_w=1280,img_h=720) 
         final_img[0:720,0:1280] = stars_image #main_frame_img
         if SHOW == 1:
            cv2.imshow('pepe', final_img)
            cv2.waitKey(30)
         #SHOW = 1

         # save new / updated json file 
         # and also update the DB
         save_json_file(cal_json_file, new_cp)
         update_calibration_file(cal_fn, new_cp, con,cur,json_conf,mcp)


         print("SAVING NEW JSON FILE!", cal_json_file)
         save_json_file(star_pairs_file, new_star_pairs)


   save_json_file(all_merged_stars_file, all_merged_stars)
   print("saved", len(all_merged_stars), "stars", all_merged_stars_file)


def star_points_all(cam_id, json_conf, con, cur):
   calfiles_data = load_cal_files(cam_id, con, cur)
   mcp = get_mcp(cam_id) 
   station_id = json_conf['site']['ams_id']
   # make / verify star points and associated files for all cal_files in the system!

   zp_image_file = "/mnt/ams2/cal/plots/" + station_id + "_" + cam_id + "_ZP_STARS.jpg"
   zp_image = np.zeros((1080,1920,3),dtype=np.uint8)
   for cal_fn in calfiles_data:
      cal_dir = "/mnt/ams2/cal/freecal/" + cal_fn.replace("-stacked-calparams.json", "/")
      cal_img_file = cal_dir + cal_fn.replace("-calparams.json", ".png")
      cal_json_file = cal_dir + cal_fn
      star_points_file = cal_dir + cal_fn.replace("-calparams.json", "-star-points.json")
      star_pairs_file = cal_dir + cal_fn.replace("-calparams.json", "-star-pairs.json")
      star_points_image_file = cal_dir + cal_fn.replace("-calparams.json", "-star-points.jpg")
      star_pairs_image_file = cal_dir + cal_fn.replace("-calparams.json", "-star-pairs.jpg")

      cal_params = cal_data_to_cal_params(cal_fn, calfiles_data[cal_fn],json_conf, mcp)


      if mcp is not None:
         cal_params['x_poly'] = mcp['x_poly']
         cal_params['y_poly'] = mcp['y_poly']
         cal_params['y_poly_fwd'] = mcp['y_poly_fwd']
         cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      else:
         cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)

      if os.path.exists(star_points_file) is False:
         if os.path.exists(cal_img_file):
            cal_img = cv2.imread(cal_img_file)
         if os.path.exists(cal_json_file):
            try:
               cp = load_json_file(cal_json_file)
            except:
               return

         star_points, star_image = get_star_points(cal_fn,  cal_img, cp, station_id, cam_id, json_conf)
         cv2.imwrite(star_points_image_file, star_image)
         save_json_file(star_points_file, star_points)
         print("saved", star_points_file)
      else:
         star_points = load_json_file(star_points_file)
         star_image = cv2.imread(star_points_image_file)

      if SHOW == 1:
         cv2.imshow('pepe', star_image)
         cv2.waitKey(30)

      if True:
      #if os.path.exists(star_pairs_file) is False:
         star_pairs = []
      else:
         try:
            star_pairs = load_json_file(star_pairs_file)
            #continue 
         except:
             
            star_pairs = []
            print("DONE", star_pairs_file)

      # pair stars
      if len(star_pairs) == 0:
         resp = pair_points(cal_fn, star_points, star_pairs_file, star_pairs_image_file, cal_params, star_image, zp_image)
         if resp is not None:
            star_pairs,show_image,zp_image = resp
         else:
            print(resp)

      else:
         print("WE did everything for this file already")
         img = cv2.imread(star_pairs_image_file)
         if SHOW == 1:
            cv2.imshow('pepe', img)
            cv2.waitKey(30)
   cv2.imwrite(zp_image_file, zp_image)

def pair_points(cal_fn, star_points, star_pairs_file, star_pairs_image_file, cal_params,star_image, zp_image):
      show_img = star_image.copy()
      star_pairs = []
      cal_params_nlm = cal_params.copy()
      cal_params_nlm['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)


      sql = "DELETE FROM calfile_catalog_stars where calfile = '{:s}'".format(cal_fn)
      print(sql)
      #cur.execute(sql)
      #con.commit()
 
      cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
      for star in cat_stars:
         (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star

         #zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(x,y,cal_fn,cal_params_nlm,json_conf)
         zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, ra, dec)

         sql = """
               INSERT INTO calfile_catalog_stars (
                      cal_fn,
                      name,
                      mag,
                      ra,
                      dec,
                      new_cat_x,
                      new_cat_y,
                      zp_cat_x,
                      zp_cat_y
               )
               VALUES (?,?,?,?,?,?,?,?,?)
         """
         ivals = [cal_fn, name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y]
         try:
            cur.execute(sql, ivals)
         except:
            print("Must be done already")
      con.commit()

      cc = 0
      for x,y,flux in star_points:
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(x,y,cal_fn,cal_params,json_conf)
         img_new_cat_x, img_new_cat_y = get_xy_for_ra_dec(cal_params, img_ra, img_dec)


         # try to find it from the reverse ra/dec of the bright point
         sql = """
            SELECT hip_id, mag, iau_ra, iau_decl, name_ascii, constellation 
              FROM catalog_stars 
             WHERE iau_ra > ?
               AND iau_ra < ?
               AND iau_decl > ?
               AND iau_decl < ?
          ORDER BY mag ASC
         """
         svals = [img_ra-5, img_ra+5, img_dec-5, img_dec+5]
         cur.execute(sql, svals)
         rows = cur.fetchall()

         # try to find it from the reverse ra/dec of the bright point
         sql = """
            SELECT name, mag, ra, dec, name, name  
              FROM calfile_catalog_stars 
             WHERE new_cat_x > ?
               AND new_cat_x < ?
               AND new_cat_y > ?
               AND new_cat_y < ?
               AND cal_fn = ?
          ORDER BY mag ASC
         """
         res = 25
         svals = [x-res, x+res, y-res, y+res, cal_fn]
         cur.execute(sql, svals)
         rows2 = cur.fetchall()
         print(sql)
         print(svals)
         print("ROWS1", len(rows))
         print("ROWS2", len(rows2))
         if len(rows) == 0 and len(rows2) > 0:
            print("ROWS2 OVERRIDE!", rows2)
            rows = rows2


         #(116727, 3.21, 354.836655, 77.632313, 'Errai', 'Cep')
         for row in rows:
            hip_id, mag, ra, dec, name_ascii, cons = row 
            new_cat_x, new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)
            x1 = new_cat_x - 16 
            x2 = new_cat_x + 16 
            y1 = new_cat_y - 16 
            y2 = new_cat_y + 16 
            if name_ascii == "":
               name_ascii = hip_id
            zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(x,y,cal_fn,cal_params_nlm,json_conf)
            zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, img_ra, img_dec)


            res_px = calc_dist((new_cat_x,new_cat_y),(x,y))
            if res_px <= 5:
               color = [20,255,57]
               bad = False 
            elif 5 < res_px <= 10:
               color = [152,251,152]
               bad = False 
            else:
               bad = True
               color = [0,0,255]

            print("RES", res_px, color)
            # NEED TO HANDLE MULTI'S BETTER HERE!
            cv2.rectangle(show_img, (int(x1), int(y1)), (int(x2) , int(y2) ), color, 1)
            if bad is False:
               cv2.rectangle(show_img, (int(new_cat_x-2), int(new_cat_y-2)), (int(new_cat_x+2) , int(new_cat_y+2) ), color, 1)
               cv2.line(show_img, (int(new_cat_x),int(new_cat_y)), (int(x),int(y)), color, 1)

               cv2.rectangle(show_img, (int(zp_cat_x-2), int(zp_cat_y-2)), (int(zp_cat_x+2) , int(zp_cat_y+2) ), [192,240,208], 1)

               cv2.line(show_img, (int(zp_cat_x),int(zp_cat_y)), (int(x),int(y)), color, 1)
               cv2.line(zp_image, (int(zp_cat_x),int(zp_cat_y)), (int(x),int(y)), color, 1)

               desc = name_ascii + " (" + str(int(mag)) + ") " + str(int(ra)) + " / " + str(int(dec))
               cv2.putText(show_img, desc,  (int(x1-10),int(y2+10)), cv2.FONT_HERSHEY_SIMPLEX, .4, color, 1)

               match_dist = angularSeparation(ra,dec,img_ra,img_dec)
               res_px = calc_dist((x,y),(new_cat_x,new_cat_y))

               slope = (y - new_cat_y) / (x - new_cat_x)
               zp_slope = (y - zp_cat_y) / (x - zp_cat_x)


               star_pairs.append((hip_id, name_ascii, cons, mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,x,y,zp_cat_x,zp_cat_y,slope,zp_slope,res_px,flux)) 

            #else:
            #   cv2.putText(show_img, "X: " + str(int(res_px)),  (int(x+5),int(y+5)), cv2.FONT_HERSHEY_SIMPLEX, .4, color, 1)
               #cv2.line(show_img, (int(new_cat_x),int(new_cat_y)), (int(x),int(y)), color, 1)
            #cv2.circle(show_img, (int(x1 + mx),int(y1 + my)), 5, (128,128,128),1)
            #desc2 = "IMG: " + str(img_ra)[0:5] + " " + str(img_dec)[0:5]
            #cv2.putText(show_img, desc2,  (int(x1),int(y2+20)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)


         if len(rows) > 0 or len(rows2) > 0 :
             foo = 1
         #   print("CLOSE:", rows)
         else:
            desc = "X - No close stars" 
            cv2.putText(show_img, desc,  (int(x),int(y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
         if SHOW == 1:
            if cc % 50 == 0:
               cv2.imshow('pepe', show_img)
               cv2.imshow('pepe2', zp_image)
               cv2.waitKey(30)


         cc += 1
      cv2.waitKey(90)

      save_json_file(star_pairs_file, star_pairs)
      cv2.imwrite(star_pairs_image_file, show_img)
      print("\tSAVED STAR PAIRS FILE:", star_pairs_file, len(star_pairs))
      print("\tSAVED star_pairs_image_file:", star_pairs_image_file)


def get_star_points(cal_fn, oimg, cp, station_id, cam_id, json_conf):
   SHOW = 0
   gsize = 50
   mask_file = "/mnt/ams2/meteor_archive/{}/CAL/MASKS/{}_mask.png".format(station_id, cam_id)
   if os.path.exists(mask_file) is True:
      mask = cv2.imread(mask_file)
      #mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
      mask = cv2.resize(mask, (1920,1080))
   else:
      print("MASK NOT FOUND!", mask_file)
      mask = np.zeros((1080,1920),dtype=np.uint8)

   # fastest possible way to get STAR POINTS (Possible stars) from the image
   if len(oimg.shape) == 3:
      gray_orig = cv2.cvtColor(oimg, cv2.COLOR_BGR2GRAY)
      gray_img = cv2.cvtColor(oimg, cv2.COLOR_BGR2GRAY)
   else:
      gray_orig = oimg
      gray_img = oimg
   if len(mask.shape) == 3:
      mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
      mask = cv2.resize(mask, (gray_img.shape[1], gray_img.shape[0]))
   gray_img = cv2.subtract(gray_img, mask)
   gray_img = cv2.resize(gray_img,(1920,1080))

   star_points = []
   c = 0
   show_img = oimg.copy()
   for w in range(0,1920):
      for h in range(0,1080):
         found = False
         if (w == 0 and h == 0) or (w % gsize == 0 and h % gsize == 0):
            x1 = w
            x2 = w + gsize
            y1 = h
            y2 = h + gsize
            if x2 > 1920:
               x2 = 1920
            if y2 > 1080:
               y2 = 1080
            grid_key = str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2)
            crop = gray_img[y1:y2,x1:x2]
            low_row = np.mean(crop[-1,:])
            if low_row == 0 or crop[-1,0] == 0 or crop[-1,-1] == 0:
               continue
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(crop)
            avg_val = np.mean(crop)
            pxd = max_val - avg_val
            cv2.rectangle(show_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1)
            # MAIN FILTER STAR
            if pxd > 15 : #and avg_val < 80:
               found = True 
               cv2.circle(show_img, (int(x1 + mx),int(y1 + my)), 5, (128,128,128),1)
               # Should add flux here and not max_VAL!?
               star_points.append((x1+mx,y1+my,max_val))
            if c % 25 == 0:
               if SHOW == 1: 
                  cv2.imshow('pepe', show_img)
                  if avg_val < 10 or found is False:
                     cv2.waitKey(1)
                  else:
                     cv2.waitKey(1)
            c += 1

   if SHOW == 1:
      cv2.waitKey(30)
   #show_img = oimg.copy()
   #return(star_points, show_img )
   new_star_points = []

   for star in star_points:
      x,y,bp = star
      cv2.circle(show_img, (int(x),int(y)), 15, (88,88,88),1)

      x1 = w
      x2 = w + gsize
      y1 = h
      y2 = h + gsize
      if x2 > 1920:
         x2 = 1920
      if y2 > 1080:
         y2 = 1080
      grid_key = str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2)
      crop = gray_img[y1:y2,x1:x2]

      rx1 = int(x - 16)
      rx2 = int(x + 16)
      ry1 = int(y - 16)
      ry2 = int(y + 16)
      if rx1 < 0 or ry1 < 0:
         continue
      if rx2 >= 1920 or ry2 >= 1080 :
         continue
      star_crop = gray_img[ry1:ry2,rx1:rx2]

      star_obj = eval_star_crop(star_crop, cal_fn, rx1, ry1, rx2, ry2)
      if star_obj['valid_star'] is True:
         if star_obj['star_flux'] > 50:
            new_star_points.append((x,y,star_obj['star_flux']))
         if star_obj['star_yn'] > 50:
            cv2.rectangle(show_img, (int(star_obj['x1']), int(star_obj['y1'])), (int(star_obj['x2']) , int(star_obj['y2']) ), (0, 255, 0), 1)
         else:
            cv2.rectangle(show_img, (int(star_obj['x1']), int(star_obj['y1'])), (int(star_obj['x2']) , int(star_obj['y2']) ), (0, 128, 0), 1)
      else:
         cv2.rectangle(show_img, (int(star_obj['x1']), int(star_obj['y1'])), (int(star_obj['x2']) , int(star_obj['y2']) ), (0, 0, 255), 1)

      # ROUNDED POINT! (for flux!)
      sx = int(star_obj['star_x'])
      sy = int(star_obj['star_y'])
      #show_img[sy, sx] = [0,0,255]
      cv2.circle(show_img, (int(sx),int(sy)), int(star_obj['radius']), (0,0,255),1)

      # ANNULUS
      cv2.circle(show_img, (int(sx),int(sy)), int(star_obj['radius'])+2, (128,128,128),1)
      cv2.circle(show_img, (int(sx),int(sy)), int(star_obj['radius'])+4, (128,128,128),1)



      desc = str(int(star_obj['star_yn'])) + "%"
      if np.isnan(star_obj['star_flux']) :
         star_obj['star_flux'] = 0
      desc2 = str(int(star_obj['star_flux']))  #+ " / " + str(len(star_obj['cnts'])) + " / " + str(star_obj['radius'])
      cv2.putText(show_img, desc,  (star_obj['x1'],star_obj['y2']+10), cv2.FONT_HERSHEY_SIMPLEX, .4, (200,200,200), 1)
      cv2.putText(show_img, desc2,  (star_obj['x1'],star_obj['y1']-10), cv2.FONT_HERSHEY_SIMPLEX, .4, (200,200,200), 1)


   #for row in new_star_points:

   if SHOW == 1:
      cv2.imshow('pepe', show_img)
      cv2.waitKey(30)
   return(new_star_points, show_img)


def get_stars_from_image(oimg, cp):
   cat_image_stars = cp['cat_image_stars']
   cal_fn = cp['cal_fn']
   image_stars = []
   star_objs = []
   # make list of star points from cat stars and whatever else we can find
   gray_orig = cv2.cvtColor(oimg, cv2.COLOR_BGR2GRAY)
   gray_img = cv2.cvtColor(oimg, cv2.COLOR_BGR2GRAY)
   for star in cat_image_stars:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      x1 = int(six - 25)
      x2 = int(six + 25)
      y1 = int(siy - 25)
      y2 = int(siy + 25)
      if x1 < 0:
         x1 = 0
      if y1 < 0:
         y1 = 0
      if x2 >= 1920:
         x2 = 1920 
      if y2 >= 1080:
         y2 = 1080
      gray_img[y1:y2,x1:x2] = 0
      image_stars.append((six,siy,bp))
      if SHOW == 1:
         cv2.imshow("pepe", gray_img)
         cv2.waitKey(30)

   show_img = oimg.copy()
   # check top 100 brightest points in the image
   for i in range(0,200):
      if SHOW == 1:
         cv2.imshow("gray", gray_img)
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_img)
      resp = make_star_roi(mx,my,32)
      sbx = mx
      sby = my
      status,x1,y1,x2,y2 = resp
      valid = False
      if status is True:
         crop_img = gray_orig[y1:y2,x1:x2]
         avg_val = np.mean(crop_img)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(crop_img)
         pxd = max_val - avg_val

         _, crop_thresh = cv2.threshold(crop_img, max_val * .90, 255, cv2.THRESH_BINARY)
         cnts = get_contours_in_image(crop_thresh)

         if pxd > 20 and len(cnts) == 1:
            valid = True

         if len(cnts) == 1:
            x,y,w,h = cnts[0]
            cx = x + (w/2)
            cy = y + (h/2)
            if w > h:
               radius = w
            else:
               radius = h
            try:
               star_flux = do_photo(crop_img, (cx,cy), radius)
            except:
               star_flux = 0
            if star_flux > 0:
               #star_yn = ai_check_star(crop_img, cal_fn)
               star_yn = -1 
            else:
               star_yn = -1 
               valid = False
         else:
            valid = False

         if valid is True:


            star_obj = {}
            star_obj['cal_fn'] = cp['cal_fn'] 
            star_obj['x'] = x1 + (x) + (w/2)
            star_obj['y'] = y1 + (y) + (h/2)
            star_obj['star_flux'] = star_flux
            star_obj['star_yn'] = star_yn
            star_obj['star_radius'] = radius
            image_stars.append((star_obj['x'], star_obj['y'], star_obj['star_flux']))
            star_objs.append(star_obj)
            desc = str(int(star_flux)) + " " + str(int(star_yn))
            if SHOW == 1:
               if star_yn > 90:
                  cv2.putText(show_img, desc,  (x1,y1), cv2.FONT_HERSHEY_SIMPLEX, .4, (128,128,128), 1)
                  cv2.rectangle(show_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1)
               else:
                  cv2.putText(show_img, desc,  (x1,y1), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,0), 1)
                  cv2.rectangle(show_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 0, 0), 1)
               if SHOW == 1:
                  cv2.imshow("pepe", show_img)
                  cv2.waitKey(30)

      gray_img[y1:y2,x1:x2] = 0
   if SHOW == 1:
      cv2.imshow("pepe", show_img)
      cv2.waitKey(30)
   return(image_stars, star_objs)

def catalog_image(cal_fn, con, cur, json_conf,mcp=None, add_more=False,del_more=False ):
   fine_tune = False
   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)

   if SHOW == 1:
      cv2.namedWindow("pepe")
      cv2.resizeWindow("pepe", 1920, 1080)

   calfiles_data = load_cal_files(cam_id , con, cur )

   resp = start_calib(cal_fn, json_conf, calfiles_data, mcp)
   if resp is False:
      return(False)
   else:
      (station_id, cal_dir, cal_json_file, cal_img_file, cal_params, cal_img, clean_cal_img, mask_file,mcp) = resp


   if fine_tune is True:
      if cal_params['total_res_px'] > 20:
         tuner = 10
      elif 10 < cal_params['total_res_px'] <= 20:
         tuner = 100
      else:
         tuner = 1000
      if len(cal_params['cat_image_stars']) is None:
         print("BAD CAL: NO CAT IMAGE STARS!")
         #print(cal_dir + cal_fn)
      if len(cal_params['cat_image_stars']) >80:
         add_more = False

      print("TUNE:", len(cal_params['cat_image_stars']), cal_params['total_res_px'], tuner)
      new_cal_params, report_txt, show_img = cal_params_report(cal_fn, cal_params, json_conf, clean_cal_img.copy(), 30, mcp)

      # AUTO TWEEK THE CAL!

      best_res_px = new_cal_params['total_res_px']
      best_res_deg = new_cal_params['total_res_deg']
      best_az = 9999
      best_el = 9999
      best_ra = 9999
      best_dec = 9999
      best_pos = 9999
      best_pxs = 9999

      if len(cal_params['cat_image_stars']) > 60 and cal_params['total_res_px'] > 10:
         cal_params, del_stars = delete_bad_stars(cal_fn, cal_params, con,cur,json_conf, cal_img)
   
      if cal_params['cat_image_stars'] == 0:
         #print(cal_params)
         print("NO STARS FAIL")

      for i in range(-10,10):
         v = i / tuner
         nc = cal_params.copy()
         nc['center_az'] = nc['center_az'] + v
         nc = update_center_radec(cal_fn,nc,json_conf)
         nc, report_txt, show_img = cal_params_report(cal_fn, nc, json_conf, clean_cal_img.copy(), 30, mcp)
         if nc['total_res_px'] < best_res_px:
            best_res_px = nc['total_res_px']
            best_res_deg = nc['total_res_deg']
            best_az = nc['center_az']
            best_ra = nc['ra_center']
            best_dec = nc['dec_center']
            print("BEST!", best_az, best_ra)
         print("CAT IMAGE RES PX/RES DEG", nc['total_res_px'], nc['total_res_deg'])

      if best_az != 9999:
         print("UPDATE BETTER CAL")
         cal_params = nc.copy()
         cal_params['center_az'] = best_az
         cal_params['ra_center'] = best_ra
         cal_params['dec_center'] = best_dec
         cal_params['total_res_px'] = best_res_px 
         cal_params['total_res_deg'] = best_res_deg 

      cal_params, report_txt, show_img = cal_params_report(cal_fn, cal_params, json_conf, clean_cal_img.copy(), 30, mcp)
      best_res_px = cal_params['total_res_px']


      for i in range(-10,10):
         v = i / tuner
         nc = cal_params.copy()
         nc['center_el'] = nc['center_el'] + v
         nc = update_center_radec(cal_fn,nc,json_conf)
         nc, report_txt, show_img = cal_params_report(cal_fn, nc, json_conf, clean_cal_img.copy(), 30, mcp)
         if nc['total_res_px'] < best_res_px:
            best_res_px = nc['total_res_px']
            best_el = nc['center_el']
            best_ra = nc['ra_center']
            best_dec = nc['dec_center']
            print("BEST!", best_el, best_ra)
         #print("RES", nc['total_res_px'], nc['total_res_deg'])

      if best_el != 9999:
         print("UPDATE BETTER CAL")
         cal_params = nc.copy()
         cal_params['center_el'] = best_el
         cal_params['ra_center'] = best_ra
         cal_params['dec_center'] = best_dec
         cal_params['total_res_px'] = best_res_px 
         cal_params['total_res_deg'] = best_res_deg 


      cal_params, report_txt, show_img = cal_params_report(cal_fn, cal_params, json_conf, clean_cal_img.copy(), 30, mcp)
      best_res_px = cal_params['total_res_px']

      for i in range(-10,10):
         v = i / tuner
         nc = cal_params.copy()
      
         nc['position_angle'] = nc['position_angle'] + v
         nc = update_center_radec(cal_fn,nc,json_conf)
         nc, report_txt, show_img = cal_params_report(cal_fn, nc, json_conf, clean_cal_img.copy(), 30, mcp)
         if nc['total_res_px'] < best_res_px:
            best_res_px = nc['total_res_px']
            best_pos = nc['position_angle']
            best_ra = nc['ra_center']
            best_dec = nc['dec_center']
            print("BEST!", best_pos, best_ra, best_dec)
         #print("RES", nc['total_res_px'], nc['total_res_deg'])

      if best_pos != 9999:
         print("UPDATE BETTER CAL")
         cal_params = nc.copy()
         cal_params['position_angle'] = best_pos
         cal_params['ra_center'] = best_ra
         cal_params['dec_center'] = best_dec
         cal_params['total_res_px'] = best_res_px 
         cal_params['total_res_deg'] = best_res_deg 

      cal_params, report_txt, show_img = cal_params_report(cal_fn, cal_params, json_conf, clean_cal_img.copy(), 30, mcp)
      best_res_px = cal_params['total_res_px']
      print("LAST BEST:", best_res_px)

      for i in range(-10,10):
         v = i / tuner
         nc = cal_params.copy()
         nc['pixscale'] = nc['pixscale'] + v
         nc = update_center_radec(cal_fn,nc,json_conf)
         nc, report_txt, show_img = cal_params_report(cal_fn, nc, json_conf, clean_cal_img.copy(),30,mcp)
         if nc['total_res_px'] < best_res_px:
            best_res_px = nc['total_res_px']
            best_pxs = nc['pixscale']
            best_ra = nc['ra_center']
            best_dec = nc['dec_center']
            print("BEST!", best_pxs, best_ra, best_dec)
         #print("RES", nc['total_res_px'], nc['total_res_deg'])

      if best_pxs != 9999:
         print("UPDATE BETTER CAL")
         cal_params['pixscale'] = best_pxs
         cal_params['total_res_px'] = best_res_px 
         cal_params['total_res_deg'] = best_res_deg 

      print("DONE")
      cal_params = update_center_radec(cal_fn,cal_params,json_conf)
      # final before delete
      cal_params, report_txt, show_img = cal_params_report(cal_fn, cal_params, json_conf, clean_cal_img.copy(), 30, mcp)
      best_res_px = cal_params['total_res_px']

   # DELETE BAD STARS
   if del_more is True:
      cal_params, del_stars = delete_bad_stars (cal_fn, cal_params, con,cur,json_conf)

   # final after delete
   cal_params, report_txt, show_img = cal_params_report(cal_fn, cal_params, json_conf, clean_cal_img.copy(), 30, mcp)
   if SHOW == 1:
      cv2.imshow('pepe', show_img)
      cv2.waitKey(30)

   print("BEFORE UPDATE RES:", cal_fn, cal_params['total_res_px'], cal_params['total_res_deg'])
   cal_params = update_center_radec(cal_fn,cal_params,json_conf)
   update_calibration_file(cal_fn, cal_params, con,cur,json_conf,mcp)

   save_json_file(cal_dir + cal_fn, cal_params)


   print("AFTER UPDATE RES:", cal_dir + cal_fn, cal_params['total_res_px'], cal_params['total_res_deg'])
   #add_more = False 

   if add_more is False:
      print("WE HAVE ENOUGH STARS!")
      return()
   ### ADD MORE STARS IF WE CAN ###
   ### GET MORE STARS IF WE CAN ###
   cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
   blend_img = cv2.addWeighted(show_img, .5, cat_image, .5,0)
   cat_show_img = show_img.copy()

   last_best_res = cal_params['total_res_px'] + 2

   cal_params_nlm = cal_params.copy()
   cal_params_nlm['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   #all_res, inner_res, middle_res, outer_res = recalc_res(cal_params)
   all_res, inner_res, middle_res, outer_res,cal_params= recalc_res(cal_fn, cal_params, json_conf)


   used = {}
   new_stars = []
   for star in cal_params['cat_image_stars']: 
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      # ONLY TRY TO ADD EDGE STARS! 
      


      ra_key = str(ra) + "_" + str(dec)
      used[ra_key] = {}


   print("LAST BEST RES:", inner_res, middle_res, outer_res)
   rejected = 0
   for star in cat_stars[0:30]:
      if rejected > 20:
         print("NO MORE STARS CAN BE ADDED!")
         continue
      (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star 
      ra_key = str(ra) + "_" + str(dec)
      rx1 = int(new_cat_x - 16)
      rx2 = int(new_cat_x + 16)
      ry1 = int(new_cat_y - 16)
      ry2 = int(new_cat_y + 16)

      if (new_cat_x < 300 or new_cat_x > 1620) and (new_cat_y < 200 or new_cat_y > 880):
         print("EDGE")
      else:
         print("NOT EDGE")
         #continue

      if rx1 <= 0 or ry1 <= 0 or rx2 >= 1920 or ry2 >= 1080:
         continue
      if ra_key in used:
         cv2.rectangle(cat_show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (0, 255, 0), 2)
      else:
         star_crop = clean_cal_img[ry1:ry2,rx1:rx2]
         star_obj = eval_star_crop(star_crop, cal_fn, rx1, ry1, rx2, ry2)
         if star_obj['valid_star'] is True:
            star_obj['cx'] = star_obj['cx'] + rx1
            star_obj['cy'] = star_obj['cy'] + ry1
            cv2.rectangle(cat_show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (128, 200, 128), 1)
            star_yn = star_obj['star_yn'] 
            img_x= star_obj['cx'] 
            img_y = star_obj['cy'] 
            bp = star_obj['star_flux']
            star_flux = star_obj['star_flux']

            res_px = calc_dist((star_obj['cx'],star_obj['cy']),(new_cat_x,new_cat_y))
            print("RE PXS/ LAST BEST RES:", res_px, last_best_res)

            center_dist = calc_dist((960,540),(img_x,img_y))
            if center_dist < 400: 
               act_res = inner_res ** 2
            elif 400 <= center_dist < 600: 
               act_res = middle_res  ** 2
            else:

               act_res = (outer_res ** 2) + outer_res

            if res_px <= act_res :
               print("ADD NEW INCLUDE:", act_res, res_px)

               new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params,json_conf)
               match_dist = angularSeparation(ra,dec,img_ra,img_dec)
               res_deg = match_dist
               cal_params['cat_image_stars'].append((name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,bp)) 
               print("ADD NEW STAR!", name, res_px)

               zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params_nlm,json_conf)
               zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, ra, dec)

               zp_res_px = res_px
               slope = (img_y - new_cat_y) / (img_x - new_cat_x)
               zp_slope = (img_y - zp_cat_y) / (img_x - zp_cat_x)


               new_stars.append((cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, res_deg, slope, zp_slope, star_obj['pxd']))

               cv2.rectangle(cat_show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (0,255, 0), 1)
               cv2.line(cat_show_img, (int(new_cat_x),int(new_cat_y)), (int(star_obj['cx']),int(star_obj['cy'])), (255,255,255), 2)
               cv2.putText(cat_show_img, str(round(res_px,1)) + "px",  (int(new_cat_x + 5),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,255,0), 1)
            else:
               # NOT VALID PER EVAL
               print("FAILED EVAL!", star_obj)
               print("REJECT:", act_res, res_px)
               cv2.putText(cat_show_img, str(round(res_px,1)) + "px",  (int(new_cat_x + 5),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,128), 1)
               cv2.rectangle(cat_show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (0,0, 255), 1)
         else:

            print("REJECT: not valid" )
            for key in star_obj:
               print(key, star_obj[key])

            cv2.putText(cat_show_img, "X",  (int(rx1),int(ry1)), cv2.FONT_HERSHEY_SIMPLEX, .5, (0,0,255), 2)
            rejected += 1
            continue
            #cv2.putText(cat_show_img, str(round(res_px,1)) + "px",  (int(new_cat_x + 5),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
            cv2.rectangle(cat_show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (64,64, 128), 1)
         #if SHOW == 1:
         #   cv2.imshow('pepe', cat_show_img)
         #   cv2.waitKey(10)


   update_calibration_file(cal_fn, cal_params, con,cur,json_conf,mcp)


   save_json_file(cal_dir + cal_fn, cal_params)

   if SHOW == 1:      
      cv2.imshow('pepe', blend_img)
      cv2.waitKey(100)

      cv2.imshow('pepe', cat_show_img)
      cv2.waitKey(30)



   # INSERT NEW STARS!
   for star in new_stars:
      (cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, res_deg, slope, zp_slope,star_pd) = star

      zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params_nlm,json_conf)
      zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, ra, dec)

      zp_res_px = calc_dist((img_x,img_y), (zp_cat_x,zp_cat_y))
      star_obj["cal_fn"] = cal_fn
      star_obj["name"]  = name
      star_obj["mag"] = mag
      star_obj["ra"]  = ra 
      star_obj["dec"] = dec
      star_obj["new_cat_x"] = new_cat_x 
      star_obj["new_cat_y"] = new_cat_y 
      star_obj["zp_cat_x"]  = zp_cat_x 
      star_obj["zp_cat_y"] = zp_cat_y 
      star_obj["img_x"] = img_x 
      star_obj["img_y"] = img_y 
      star_obj["star_flux"] = star_flux 
      star_obj["star_yn"]  = star_yn 
      star_obj["star_pd"] = star_pd 
      star_obj["star_found"] = 1 
      if mcp is None:
         star_obj["lens_model_version"] = 1
      else:
         star_obj["lens_model_version"] = mcp['cal_version']
      star_obj["slope"] = slope
      star_obj["zp_slope"] = zp_slope
      star_obj["res_px"] = res_px
      star_obj["zp_res_px"] = zp_res_px
      star_obj["res_deg"] = res_deg
      #print("INSERT NEW STAR!", star_obj)
      insert_paired_star(cal_fn, star_obj, con, cur, json_conf )
   return(cal_params)

def recalc_res(cal_fn, cal_params, json_conf):
   all_deg = []
   all_res = []
   inner_res = []
   middle_res = []
   outer_res = []
   updated_stars = []

   cal_params = update_center_radec(cal_fn,cal_params,json_conf)

   for star in cal_params['cat_image_stars']:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,res_px,bp) = star
      center_dist = calc_dist((960,540),(six,siy))
      
      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_fn,cal_params,json_conf)
      new_cat_x,new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)

      res_px = calc_dist((six,siy), (new_cat_x,new_cat_y))
      match_dist = angularSeparation(ra,dec,img_ra,img_dec)

      updated_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,res_px,bp))

      all_res.append(res_px)
      all_deg.append(match_dist)
      if center_dist < 400:
         inner_res.append(res_px)
      elif 400 <= center_dist < 800:
         middle_res.append(res_px)
      else:
         outer_res.append(res_px)
   if len(all_res) > 3:
      all_res_mean = np.mean(all_res)
   else:
      all_res_mean = 5

   if len(inner_res) > 3:
      inner_res_mean = np.mean(inner_res)
   else:
      inner_res_mean = 5

   if len(middle_res) > 3:
      middle_res_mean = np.mean(middle_res)
   else:
      middle_res_mean = 15

   if len(outer_res) > 3:
      outer_res_mean = np.mean(outer_res)
   else:
      outer_res_mean = 36 

   if inner_res_mean < 5:
      inner_res_mean = 5 

   cal_params['cat_image_stars'] = updated_stars
   cal_params['total_res_px'] = np.mean(all_res)
   cal_params['total_res_deg'] = np.mean(all_deg)
   return(all_res_mean, inner_res_mean, middle_res_mean, outer_res_mean, cal_params)

def delete_bad_stars (cal_fn, cal_params, con,cur,json_conf, oimg):

   new_stars = []
   del_stars = []
   if cal_params['x_poly'][0] == 0:
      return(cal_params, del_stars)


   all_res, inner_res, middle_res, outer_res,cal_params = recalc_res(cal_fn, cal_params, json_conf)
   mean_all_res = all_res
   if np.isnan(outer_res) :
      outer_res = 35

   if sum(cal_params['x_poly'] ) == 0:
      first_time_cal = True
   else:
      first_time_cal = False 

   if all_res > 10:
      factor = 2 
   else:
      factor = 2 

   if first_time_cal is True:
      factor = 4 

   tb = pt()
   tb.field_names = ["Action", "Star", "Mag", "Intensity", "x/y", "Center Dist", "Res Limit", "Res Pixels"]

   res_table = {}
   res_table[0] = []
   res_table[500] = []
   res_table[600] = []
   res_table[800] = []
   mres = {}
   for star in cal_params['cat_image_stars']:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      center_dist = calc_dist((960,540),(six,siy))
      if center_dist < 500:
         res_table[0].append(res_px)
      if 500 <= center_dist < 600:
         res_table[500].append(res_px)
      if 600 <= center_dist < 800:
         res_table[600].append(res_px)
      if 800 <= center_dist < 1200:
         res_table[800].append(res_px)

   for key in res_table:
      if len(res_table[key]) > 3:
         mres[key] = np.median(res_table[key])
      else:
         mres[key] = 5 

   for star in cal_params['cat_image_stars']:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      center_dist = calc_dist((960,540),(six,siy))
      # check mask area
      cx = int(six)
      cy = int(siy)
      crop = oimg[cy-10:cy+10,cx-10:cx+10]
      try:
         if sum(crop[-1,0]) == 0:
            print("THIS STAR IS TOO CLOSE TO THE MASK IGNORE!")
            continue
      except:
         continue

      if center_dist < 500:
         dist_limit = mres[0] * 2 
      if 500 <= center_dist < 600:
         dist_limit = mres[500] * 2 
      if 600 <= center_dist < 800:
         dist_limit = mres[600] * 2.2 
      if 800 <= center_dist < 1200:
         dist_limit = mres[800] * 2.5 
      #if dist_limit > 15:
      #   dist_limit = 15

      if res_px < dist_limit :
         new_stars.append(star)
         act = "KEEP"
      else:
         act = "DELETE"
         del_stars.append(star)
         sql = """DELETE FROM calfile_paired_stars 
                   WHERE ra = ?
                     AND dec = ?
                  AND cal_fn = ?
         """
         dvals = [ra, dec, cal_fn]
         cur.execute(sql, dvals)
      xy = str(six) + " / " + str(siy)
      row = [act, dcname, mag, bp, xy, int(center_dist), str(dist_limit)[0:4], res_px]
      tb.add_row(row)
   print(tb)
   con.commit()
   cal_params['cat_image_stars'] = new_stars
   return(cal_params, del_stars)
 

def create_star_catalog_table(con, cur):
   #   (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
   sql = """
         DROP TABLE IF EXISTS "calfile_catalog_stars";
         CREATE TABLE IF NOT EXISTS "calfile_catalog_stars" (
            cal_fn text,
            name text,
            mag real,
            ra real,
            dec real,
            new_cat_x real,
            new_cat_y real,
            zp_cat_x real,
            zp_cat_y real,
            img_x real,
            img_y real,
            star_flux real,
            star_yn real,
            star_pd integer,
            star_found integer DEFAULT 0,
            lens_model_version integer,
            PRIMARY KEY(cal_fn,ra,dec)
         )

   """

def get_xy_for_ra_dec(cal_params, ra, dec):
   # pass in cal_params and ra, dec 
   # get back x,y!

   MAG_LIMIT = 8
   img_w = 1920
   img_h = 1080
   # setup astrometry and lens model variables
   catalog_stars = []
   cal_params['imagew'] = img_w
   cal_params['imageh'] = img_h 
   RA_center = float(cal_params['ra_center'])
   dec_center = float(cal_params['dec_center'])
   F_scale = 3600/float(cal_params['pixscale'])
   if "x_poly" in cal_params:
      x_poly = cal_params['x_poly']
      y_poly = cal_params['y_poly']
      x_poly_fwd = cal_params['x_poly_fwd']
      y_poly_fwd = cal_params['y_poly_fwd']
   else:
      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      x_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
      y_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)

   zp_x_poly = np.zeros(shape=(15,), dtype=np.float64)
   zp_y_poly = np.zeros(shape=(15,), dtype=np.float64)

   fov_w = img_w / F_scale
   fov_h = img_h / F_scale
   fov_radius = np.sqrt((fov_w/2)**2 + (fov_h/2)**2)

   pos_angle_ref = cal_params['position_angle']
   x_res = int(cal_params['imagew'])
   y_res = int(cal_params['imageh'])

   center_x = int(x_res / 2)
   center_y = int(y_res / 2)
   new_cat_x, new_cat_y = distort_xy(0,0,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale)

   return(new_cat_x, new_cat_y)

def get_catalog_stars(cal_params, MAG_LIMIT=5):
   mybsd = bsd.brightstardata()
   bright_stars = mybsd.bright_stars

   cat_image = np.zeros((1080,1920,3),dtype=np.uint8)

   img_w = 1920
   img_h = 1080
   # setup astrometry and lens model variables
   catalog_stars = []
   cal_params['imagew'] = img_w
   cal_params['imageh'] = img_h 
   RA_center = float(cal_params['ra_center'])
   dec_center = float(cal_params['dec_center'])
   F_scale = 3600/float(cal_params['pixscale'])
   if "x_poly" in cal_params:
      x_poly = cal_params['x_poly']
      y_poly = cal_params['y_poly']
      x_poly_fwd = cal_params['x_poly_fwd']
      y_poly_fwd = cal_params['y_poly_fwd']
   else:
      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      x_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
      y_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)

   zp_x_poly = np.zeros(shape=(15,), dtype=np.float64)
   zp_y_poly = np.zeros(shape=(15,), dtype=np.float64)

   fov_w = img_w / F_scale
   fov_h = img_h / F_scale
   fov_radius = np.sqrt((fov_w/2)**2 + (fov_h/2)**2)

   fov_radius = fov_radius * 2 

   pos_angle_ref = cal_params['position_angle']
   x_res = int(cal_params['imagew'])
   y_res = int(cal_params['imageh'])

   center_x = int(x_res / 2)
   center_y = int(y_res / 2)

   bright_stars_sorted = sorted(bright_stars, key=lambda x: x[4], reverse=False)

   sbs = []
   for data in bright_stars_sorted:
      bname, cname, ra, dec, mag = data
      name = bname
      mag = float(mag)
      if mag > MAG_LIMIT:
         continue

      # decode name when needed
      if isinstance(name, str) is True:
         name = name
      else:
         name = name.decode("utf-8")

      # calc ang_sep of star's ra/dec from fov center ra/dec
      ang_sep = angularSeparation(ra,dec,RA_center,dec_center)
      #print("ANG:", bname, mag, ang_sep)
      #if ang_sep < fov_radius and float(mag) <= MAG_LIMIT:
      #if float(mag) <= MAG_LIMIT:
      if True:
         # get the star position with no distortion
         zp_cat_x, zp_cat_y = distort_xy(0,0,ra,dec,RA_center, dec_center, zp_x_poly, zp_y_poly, x_res, y_res, pos_angle_ref,F_scale)
         new_cat_x, new_cat_y = distort_xy(0,0,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale)
         if zp_cat_x > 0 and zp_cat_y > 0 and zp_cat_x < 1920 and zp_cat_y < 1080:
            good = 1 
         else:
            continue

         catalog_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y))
         if mag <= 6:
            cv2.line(cat_image, (int(new_cat_x),int(new_cat_y)), (int(zp_cat_x),int(zp_cat_y)), (255,255,255), 2)
            center_dist = calc_dist((new_cat_x, new_cat_y), (1920/2,  1080/2))
            bxd = 40
            lxd = 10
            if center_dist > 800:
               bxd = 60
            if new_cat_x < 300:
               # left side
               rx1 = new_cat_x - bxd 
               rx2 = new_cat_x + 10
               if new_cat_y < 400:
                  # top
                  ry1 = new_cat_y - bxd
                  ry2 = new_cat_y + 10
               elif new_cat_y > 600:
                  # bottom 
                  ry1 = new_cat_y - 10
                  ry2 = new_cat_y + bxd 
               else:
                  # center 
                  ry1 = new_cat_y - int(bxd/2)
                  ry2 = new_cat_y + int(bxd/2)
            elif new_cat_x > 1620:
               #right side
               rx1 = new_cat_x - 10 
               rx2 = new_cat_x + bxd 
               if new_cat_y < 400:
                  # top
                  ry1 = new_cat_y - bxd 
                  ry2 = new_cat_y + 10
               elif new_cat_y > 600:
                  # bottom 
                  ry1 = new_cat_y - 10 
                  ry2 = new_cat_y + bxd
               else:
                  # center 
                  ry1 = new_cat_y - int(bxd / 2)
                  ry2 = new_cat_y + int(bxd / 2)
            else:
               # middle
               rx1 = new_cat_x - 25
               rx2 = new_cat_x + 25
               ry1 = new_cat_y - 25
               ry2 = new_cat_y + 25
            # add star search region
            sbs.append((name, name, ra, dec, mag, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, int(rx1),int(ry1),int(rx2),int(ry2)))
            if True:
               cv2.rectangle(cat_image, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (255, 255, 255), 2)
               cv2.putText(cat_image, name, (int(rx1),int(ry1)), cv2.FONT_HERSHEY_SIMPLEX, .8, (200,200,200), 1)
               #if SHOW == 1:
               #   cv2.imshow('pepe', cat_image)
               #   cv2.waitKey(30)
   if len(catalog_stars) == 0:
      print("NO CATALOG STARS!?")

   catalog_stars = sorted(catalog_stars, key=lambda x: x[1], reverse=False)
   return(catalog_stars, sbs, cat_image)

def ai_check_star(img, img_file):

   # SHOULD CHACHE THESE!! 
   # AND LEARN FROM THEM 
   if os.path.exists(img_file) is False:
      temp_file = "/mnt/ams2/tempstar.jpg"
      cv2.imwrite(temp_file, img)
   else:
      temp_file = img_file

   url = "http://localhost:5000/AI/STAR_YN/?file={}".format(temp_file)
   if True:
      response = requests.get(url)
      content = response.content.decode()
      resp = json.loads(content)
   return(resp['star_yn'])

def do_photo(image, position, radius,r_in=10, r_out=12):

   if radius < 2:
      radius = 2

   if False:
      # debug display
      xx,yy = position
      xx = int(xx * 10)
      yy = int(yy * 10)

      disp_img = cv2.resize(image, (320,320))
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(disp_img)
      avg_val = np.mean(disp_img)
      pxd = max_val - avg_val 
      thresh_val = int(avg_val + (max_val/2))
      if thresh_val > max_val:
         thresh_val = max_val * .8

      _, thresh_image = cv2.threshold(disp_img, thresh_val, 255, cv2.THRESH_BINARY)
   
   r_in = radius + 2
   r_out = radius + 4

   aperture_area = np.pi * radius**2
   annulus_area = np.pi * (r_out**2 - r_in**2)

   # pass in BW crop image centered around the star
   
   aperture = CircularAperture(position,r=radius)
   bkg_aperture = CircularAnnulus(position,r_in=r_in,r_out=r_out)



   phot = aperture_photometry(image, aperture)
   bkg = aperture_photometry(image, bkg_aperture)

   bkg_mean = bkg['aperture_sum'][0] / annulus_area
   bkg_sum = bkg_mean * aperture_area


   flux_bkgsub = phot['aperture_sum'][0] - bkg_sum

   if SHOW == 1:
      xx,yy = position

   return(flux_bkgsub)

def get_contours_in_image(frame ):
   ih, iw = frame.shape[:2]

   cont = []
   if len(frame.shape) > 2:
      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
   cnt_res = cv2.findContours(frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      if (w >= 1 or h >= 1) : # and (w < 10 and h < 10):
         cont.append((x,y,w,h))


   return(cont)

def cal_dir_from_file(cal_file):
   freecal_dir = "/mnt/ams2/cal/freecal/" 
   #2022_05_18_06_32_03_000_010001-stacked-fit.jpg
   if "trim" not in cal_file:
      cal_root_fn = cal_file.split("-")[0]
   else:
      print("CAL FILE:", cal_file)
      cal_root_fn = cal_file 
   
   cal_dir = freecal_dir + cal_root_fn + "/"
   if os.path.isdir(cal_dir):
      return(cal_dir)
   else:
      #print(cal_dir)
      return(False)

def get_cal_json_file(cal_dir):
   if cal_dir is False:
      return(None)
   files = glob.glob(cal_dir + "*calparams.json")
   if len(files) == 1:
      return(files[0])
   else:
      return(None)

def make_star_roi(x,y,size):
   x1 = int(x - (size/2))
   x2 = int(x + (size/2))
   y1 = int(y - (size/2))
   y2 = int(y + (size/2))
   status = True
   if True:
      if x1 <= 0:
         x1 = 0
         x2 = size
         status = False 
      if x2 >= 1920:
         x1 = 1920 - size 
         x2 = 1920
         status = False 
      if y1 <= 0:
         y1 = 0
         y2 = size
         status = False 
      if y2 >= 1080:
         y1 = 1080 - size 
         y2 = 1080 
         status = False 
      return(status, x1,y1,x2,y2)

def get_mcp(cam_id) :

   autocal_dir = "/mnt/ams2/cal/"
   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
   else:
      mcp = None
   if mcp is None:
      print("Can't update until the MCP is made!")
   else:
      if type(mcp['cal_version']) != int:
         mcp['cal_version'] = 1
      
   return(mcp)



def get_avg_res(cam_id, con, cur):

   sql = """
      SELECT avg(res_px) as arp
        FROM calibration_files 
       WHERE cal_fn like ?
         AND res_px is not NULL
   """

   dvals = ["%" + cam_id + "%"]
   cur.execute(sql, dvals)
   rows = cur.fetchall()
   for row in rows:
      avg_res = row[0]

   sql2 = """
      SELECT cal_fn, count(*) 
        FROM calfile_paired_stars 
       WHERE cal_fn like ?
         AND res_px is not NULL
    GROUP BY cal_fn
   """

   dvals = ["%" + cam_id + "%"]
   #print(sql2, dvals)
   cur.execute(sql2, dvals)
   rows = cur.fetchall()
   tt = []
   for row in rows:
      #print(row)
      tt.append(row[1])
   if len(tt) > 1:
      total_stars = int(np.mean(tt))
   else:
      total_stars = 0
   return(total_stars, avg_res)


def batch_apply_bad(cam_id, con, cur, json_conf, blimit=25):
   
   prune(cam_id, con, cur, json_conf)


   calfiles_data = load_cal_files(cam_id, con, cur)
   mcp_file = "/mnt/ams2/cal/multi_poly-" + station_id + "-" + cam_id + ".info"

   tsize,tdiff = get_file_info(mcp_file )

   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
   else:
      mcp = {}
      mcp['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      mcp['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      mcp['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      mcp['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)

   # get avg res and avg stars
   cal_files = []
   sql = """
      SELECT cal_fn, count(*) as ss, avg(res_px) as arp,  count(*) / avg(res_px) as score
        FROM calfile_paired_stars
       WHERE cal_fn like ?
         AND res_px is not NULL
       GROUP bY cal_fn
    ORDER BY res_px DESC
   """
    #ORDER BY score DESC

   dvals = ["%" + cam_id + "%"]
   cur.execute(sql, dvals)
   rows = cur.fetchall()
   cal_fns = []

   calfile_paired_star_stats = {}
   stats_res = []
   stats_stars = []
   for row in rows:

      cal_fn, total_stars, avg_res , score = row
      cal_files.append((cal_fn, total_stars, avg_res , score))
      calfile_paired_star_stats[cal_fn] = [cal_fn,total_stars,avg_res]
      stats_res.append(avg_res)
      stats_stars.append(total_stars)

   avg_res = np.mean(stats_res)
   avg_stars = np.mean(stats_stars)

   cal_files = sorted(cal_files, key=lambda x: x[2], reverse=True)
   x = 0
   best_cal_fns= []
   bad_cal_files = []
   good_cal_files = []
   best_cal_files = []
   # good, bad, best
   for row in cal_files:
      (cal_fn, total_stars, res , score) = row
      if res > avg_res * 1.2 or total_stars < avg_stars * .8:
         bad_cal_files.append(row)
      else:
         if res < avg_res * .8 and total_stars > avg_stars * 1.2:
            best_cal_files.append(row)
            best_cal_fns.append(cal_fn)
         else:
            good_cal_files.append(row)
            best_cal_fns.append(cal_fn)
      x+=1 
   # Work on worst 10 files!
   print("GOOD FILES: ", len(good_cal_files))
   print(" BAD FILES: ", len(bad_cal_files))
   print("BEST FILES: ", len(best_cal_files))
   mcp['best_files'] = best_cal_files
   mcp['good_files'] = good_cal_files
   mcp['bad_files'] = bad_cal_files


   save_json_file(mcp_file, mcp)

   blimit = int(blimit)
   for row in bad_cal_files[0:blimit]:
      
      #print(cal_fn)
      (cal_fn, total_stars, res , score) = row
      if True:
         cdir = cal_fn.split("-")[0]
         cal_dir = "/mnt/ams2/cal/freecal/" + cdir + "/"
         if os.path.exists(cal_dir):
            last_cal_params,flux_table = apply_calib (cal_fn, calfiles_data, json_conf, mcp )
            if last_cal_params is None:
               continue
            # if the results from apply are still bad try to make better
            if last_cal_params['total_res_px'] > 5:
               print(cal_fn, " is FAILING. We will try to fix" )
               cal_params = last_cal_params
               #cal_params = fix_cal(cal_fn, con, cur, json_conf)
               print("AFTER FIXED RES:", last_cal_params['total_res_px'])
               if cal_params['total_res_px'] < last_cal_params['total_res_px'] and cal_params['total_res_px'] < 5:
                  save_json_file(cal_dir + cal_fn, cal_params)
               else:
                  # all else has failed resolve the file!
                  resp = make_plate(cal_fn, json_conf, con, cur)
                  print(resp)
                  if resp is not None:
                     plate_file, plate_img = resp
                  
                     result = solve_field(plate_file, json_conf, con, cur)
                     if result is True:
                        print("Resolve worked!")
                     else:
                        print("Resolve failed! Just delete this calfile!!! It can't be saved.")
                  else:
                     print("MAKE PLATE FAILED!", plate_file)
                     print("WE SHOULD DELETE THIS?")

      print(cal_fn, total_stars, res, score)


   # run lens model 1x per 24 hours max

   make_cal_plots(cam_id, json_conf)
   make_cal_summary(cam_id, json_conf)
   #os.system("./Process.py cal_sum_html")
   tdiff, tsize = get_file_info(mcp_file )
   tdays = tdiff / 60 / 24 
   if tdays > 1:
      # at most make the lens model 1x per day
      # stop doing it if the mcp res is < 1 and total merged stars > 300
      if "x_fun" not in mcp:
         mcp['x_fun'] = 99
      if "total_stars_used" not in mcp:
         mcp['total_stars_used'] = 0
      if mcp['x_fun'] > 1 and mcp['total_stars_used'] < 300:
         print("We should make the lens model again!")
         limit = 10
         fast_lens(cam_id, con, cur, json_conf,limit, None)
         lens_model(cam_id, con, cur, json_conf )
      #
   characterize_best(cam_id, con, cur, json_conf, 50 )

def copy_best_cal_images(con, cur, json_conf):
   # copy 5-10 best cal images to the cloud so we can use these for lens models
   station_id = json_conf['site']['ams_id']
   for cam_num in json_conf['cameras']:
      cam_id = json_conf['cameras'][cam_num]['cams_id']
      cams_list.append(cam_id)
      best_local_dir = "/mnt/ams2/CAL/IMAGES/" + cam_id + "/"
      best_cloud_dir = "/mnt/archive.allsky.tv/" + station_id + "/CAL/IMAGES/" + cam_id + "/"
      if os.path.exists(best_local_dir) is False:
         os.makedirs(best_local_dir)
      if os.path.exists(best_cloud_dir) is False:
         os.makedirs(best_cloud_dir)


      calfiles_data = load_cal_files(cam_id, con, cur)
      for row in calfiles_data[0:10]:
         print(row)

def batch_apply(cam_id, con,cur, json_conf, last=None, do_bad=False, cam_stats=None, apply_type="ALL", limit=None):

   # apply the latest MCP Poly to each cal file and then recenter them
   print("BATCH APPLY:", apply_type)
   autocal_dir = "/mnt/ams2/cal/"
   station_id = json_conf['site']['ams_id']
   if SHOW == 1:
      cv2.namedWindow("pepe")
      cv2.resizeWindow("pepe", 1920, 1080)

   if cam_id == "all":
      cams_list = []
      for cam_num in json_conf['cameras']:
         cam_id = json_conf['cameras'][cam_num]['cams_id']
         cams_list.append(cam_id)
   else:
      cams_list = [cam_id]
   if True:
      # Main apply loop one for each camera in the camera list
      for cam_id in cams_list:

         if last is None:
            calfiles_data = load_cal_files(cam_id, con, cur)
         else:
            calfiles_data = load_cal_files(cam_id, con, cur, False, last)

         mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
         if os.path.exists(mcp_file) == 1:
            mcp = load_json_file(mcp_file)
            if "cal_version" not in mcp:
               mcp['cal_version'] = 0
         else:
            mcp = None
         if mcp is None:
            print("Can't update until the MCP is made!")

         cff = 0
         last_cal_params = None
         rc = 0
         flux_table = {}
         # sorted most recent to least recent
         if limit is None:
            limit = len(calfiles_data) 
         for cf in sorted(calfiles_data, reverse=True)[0:limit]:
            cal_dir = "/mnt/ams2/cal/freecal/" + cf.split("-")[0] + "/"

            if cf in calfiles_data:
               (station_id, camera_id, cal_fn, cal_ts, az, el, ra, dec, position_angle,\
               pixel_scale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
               y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) = calfiles_data[cf]
               cal_timestamp = cal_ts
               try:
                  cal_params = load_json_file(cal_dir + cf)
               except:
                  continue
               total_stars = len(cal_params['cat_image_stars']) 

            elif os.path.exists(cal_dir + cf) is True:
               print("\tLoading:", cf)
               cal_params = load_json_file(cal_dir + cf)
               res_px = total_res_px
               total_stars = len(cal_params['cat_image_stars']) 

            else:
               print("\tSkipping/Failed:", cf)
               continue
            extra_text = cf + " " + str(rc) + " of " + str(len(calfiles_data))
            if cam_stats is not None:
               if apply_type == "BEST":
                  if res_px < cam_stats[cam_id]['med_rez'] * .8 and total_stars > cam_stats[cam_id]['med_stars'] * 1.2:
                     last_cal_params, flux_table = apply_calib (cf, calfiles_data, json_conf, mcp, last_cal_params, extra_text, do_bad, flux_table)
               elif apply_type == "AVG":
                  if res_px < cam_stats[cam_id]['med_rez'] * 1.2 and total_stars > cam_stats[cam_id]['med_stars'] * .8:
                     last_cal_params, flux_table = apply_calib (cf, calfiles_data, json_conf, mcp, last_cal_params, extra_text, do_bad, flux_table)
               elif apply_type == "BAD":
                  if res_px > cam_stats[cam_id]['med_rez'] * 1.2 or total_stars < cam_stats[cam_id]['med_stars'] * .8:
                     last_cal_params, flux_table = apply_calib (cf, calfiles_data, json_conf, mcp, last_cal_params, extra_text, do_bad, flux_table)
               else:
                  last_cal_params, flux_table = apply_calib (cf, calfiles_data, json_conf, mcp, last_cal_params, extra_text, do_bad, flux_table)
            else:
               last_cal_params, flux_table = apply_calib (cf, calfiles_data, json_conf, mcp, last_cal_params, extra_text, do_bad, flux_table)
            rc += 1

def get_image_stars_with_catalog(obs_id, cal_params, show_img, flux_table=None):
   if flux_table is None:
      flux_table = {}
   clean_img = show_img.copy() 





   cal_fn = obs_id
   #star_obj = eval_star_crop(crop_img, cal_fn, mcx1, mcy1, mcx2, mcy2)

   star_points = cal_params['user_stars']
   user_stars = star_points
   ic = 0
 
   #print(len(star_points), "star_points")
   #print(len(user_stars), "user_stars")
   #star_points, show_img = get_star_points(cal_file, oimg, cal_params, station_id, camera_id, json_conf)

   if True:
      if True:
         cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
         used = {}
         if True:
            for ix,iy,ii in star_points[0:50]:
               cv2.circle(show_img, (int(ix),int(iy)), int(5), (0,255,0),1)

         all_res = []
         cat_image_stars = []
         for star in cat_stars[0:100]:
            (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
            fm = int(mag)
            if fm not in flux_table:
               flux_table[fm] = []
            cv2.putText(show_img, str(name),  (int(new_cat_x-25),int(new_cat_y-25)), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
            cv2.rectangle(show_img, (int(new_cat_x-25), int(new_cat_y-25)), (int(new_cat_x+25) , int(new_cat_y+25) ), (255, 255, 255), 1)

            # find closest image star!
            dist_arr = []
            # sort by brightest points
            star_points = sorted(star_points, key=lambda x: x[2], reverse=True)
            for ix,iy,ii in star_points[0:200]:
               this_dist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
               if this_dist < 150:
                  dist_arr.append((this_dist, star, ii))
            dist_arr = sorted(dist_arr, key=lambda x: x[0], reverse=False)
            if len(dist_arr) > 0:
               closest_star = dist_arr[0][1]
               star_x = closest_star[4]
               star_y = closest_star[5]
               flux = dist_arr[0][2]
               res = dist_arr[0][0]

               if len(flux_table[fm]) > 1:
                  mflux = int(np.mean(flux_table[fm]))
               else:
                  mflux = 0

               flux_table[fm].append(flux)

               if mflux > 0:
                  perc_diff = flux / mflux
               else:
                  perc_diff = 0

               #print("NAME, FM, MAG, FLUX, AVG FLUX:", fm, name, mag, flux, mflux, perc_diff)
               # skip dim stars with bright flux
               if perc_diff > 0:
                  if .5 <= perc_diff <= 1.50:
                     foo = 1
                  else:
                     continue

               

               all_res.append(res)



               x1 = int(star_x - 16)
               x2 = int(star_x + 16)
               y1 = int(star_y - 16)
               y2 = int(star_y + 16)
               if x1 < 0:
                  x1 = 0
                  x2 = 32
               if y1 < 0:
                  y1 = 0
                  y2 = 32
               if x2 > 1920:
                  x2 = 1920 
                  x1 = 1920 - 32
               if y2 > 1080:
                  y2 = 1080
                  y1 = 1080 - 32
               crop_img = clean_img[y1:y2,x1:x2]
               star_obj = eval_star_crop(crop_img, cal_fn, x1, y1, x2, y2)

               new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(new_cat_x,new_cat_y,obs_id,cal_params,json_conf)
               img_new_cat_x, img_new_cat_y = get_xy_for_ra_dec(cal_params, img_ra, img_dec)
               try:
                  match_dist = angularSeparation(ra,dec,img_ra,img_dec)
               except:
                  match_dist = 9999
               #cat_image_stars.append((name_ascii,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,x,y,res_px,flux))
               cv2.circle(show_img, (int(star_x),int(star_y)), 20, (255,0,0),2)
               star_obj['name'] = name
               star_obj['mag'] = mag
               star_obj['ra'] = ra
               star_obj['dec'] = dec
               star_obj['new_cat_x'] = new_cat_x
               star_obj['new_cat_y'] = new_cat_y
               star_obj['img_x'] = star_obj['star_x']
               star_obj['img_y'] = star_obj['star_y']

               star_obj['img_ra'] = img_ra 
               star_obj['img_dec'] = img_dec 
               star_obj['img_az'] = img_az
               star_obj['img_el'] = img_el
               star_obj['zp_cat_x'] = zp_cat_x 
               star_obj['zp_cat_y'] = zp_cat_y 
               star_obj['star_pd'] = 999 
               star_obj['lens_model_version'] = 999 
               res_px = calc_dist((star_obj['star_x'],star_obj['star_y']), (new_cat_x,new_cat_y))
               # HERE WE CAN DO BETTER!? OR IS THIS WIDE AN DFILTER?

               if res_px < 40: 
                  cat_image_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,star_obj['star_x'],star_obj['star_y'],res_px,star_obj['star_flux']))
                  user_stars.append((star_obj['star_x'], star_obj['star_y'], star_obj['star_flux']))

               #insert_paired_star(cal_fn, star_obj, con, cur, json_conf)

               ic += 1
   #con.commit()
   if SHOW == 1:
      cv2.imshow('pepe', show_img)
      cv2.waitKey(30)
   
   temp = []

   # final filter to remove really bad things. 
   if True:
      rez = np.median([row[-2] for row in cal_params['cat_image_stars']])
      if rez < 1:
         rez = 1
      fact = 2
      for row in cal_params['cat_image_stars']:
         name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,res_px,star_flux = row
         center_dist = calc_dist((six,siy), (1920/2,1080/2))
         if center_dist < 500 and rez < 1:
            rez = 1
            fact = 1 
         if center_dist > 600 and rez < 2:
            rez = 2 
            fact = 1 
         if center_dist > 600 :
            fact = 2 
         if center_dist > 800 :
            fact = 3 

         # geometry filters
         # Top right corner
         if six > 1920 * .7 and siy < 1080 * .6:
            if new_cat_x < six:
               continue
            if new_cat_y < siy:
               continue

         # Top left corner
         if six < 1920 * .7 and siy < 1080 * .6:
            if new_cat_x > six:
               continue
            if new_cat_y < siy:
               continue

         # bottom left corner
         if six < 1920 * .6 and siy > 1080 * .6:
            if new_cat_x > six:
               continue
            if new_cat_y > siy:
               continue
         # bottom right corner
         if six > 1920 * .6 and siy > 1080 * .6:
            if new_cat_x < six:
               continue
            if new_cat_y > siy:
               continue



         if row[-2] < rez * fact:
            temp.append(row)

      cal_params['cat_image_stars'] = temp

   return(cat_image_stars, user_stars, flux_table)

def test_cals (cal_fn, cal_params, json_conf, mcp, oimg, before_files, after_files, con, cur):
   if True:
      if mcp is not None:
         cal_params['x_poly'] = mcp['x_poly']
         cal_params['y_poly'] = mcp['y_poly']
         cal_params['y_poly_fwd'] = mcp['y_poly_fwd']
         cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      else:
         cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   extra_text = cal_fn
   cal_params['cat_image_stars'] = pair_star_points(cal_fn, oimg, cal_params, json_conf, con, cur, mcp, False)
   cal_params['cat_image_stars'] = remove_bad_stars(cal_params['cat_image_stars'])
   cal_params, bad_stars, marked_img = eval_cal_res(cal_fn, json_conf, cal_params.copy(), oimg,None,None,cal_params['cat_image_stars'])
   star_img = draw_star_image(oimg.copy(), cal_params['cat_image_stars'],cal_params, json_conf, extra_text) 
   if SHOW == 1:
      cv2.imshow('pepe', star_img)
      cv2.waitKey(30)
   start_score = len(cal_params['cat_image_stars']) / cal_params['total_res_px']
   best_score = start_score
   best_cal = cal_params.copy() 
   for cfd in before_files:
      tcp = cal_params.copy()
      cfs, f_date_str, tdays, center_az, center_el, position_angle, pixscale, total_res_px = cfd
      tcp['center_az'] = center_az
      tcp['center_el'] = center_el
      tcp['position_angle'] = position_angle 
      tcp['pixscale'] = pixscale
      tcp = update_center_radec(cal_fn,tcp,json_conf )
      tcp['cat_image_stars'] = pair_star_points(cal_fn, oimg, tcp, json_conf, con, cur, mcp, False)
      tcp['cat_image_stars'] = remove_bad_stars(tcp['cat_image_stars'])
      tcp, bad_stars, marked_img = eval_cal_res(cal_fn, json_conf, tcp.copy(), oimg,None,None,tcp['cat_image_stars'])


      star_img = draw_star_image(oimg.copy(), tcp['cat_image_stars'],tcp, json_conf, extra_text) 
      score = len(tcp['cat_image_stars']) / tcp['total_res_px']
      print("   TEST STARS/RES:", cal_fn, len(tcp['cat_image_stars']), tcp['total_res_px'], score)
      if score > best_score:
         best_cal = tcp.copy()
      if SHOW == 1:
         cv2.imshow('pepe', star_img)
         cv2.waitKey(30)

   if SHOW == 1:
      star_img = draw_star_image(oimg.copy(), best_cal['cat_image_stars'],best_cal, json_conf, "***** BEST" + extra_text + " BEST *****") 
      cv2.imshow('pepe', star_img)
      cv2.waitKey(30)
   return(best_cal)

def apply_calib (cal_file, calfiles_data, json_conf, mcp, last_cal_params=None, extra_text= "", do_bad=False, flux_table=None):
      #os.system("clear")
      #print("apply_calib:", cal_file)
      station_id = json_conf['site']['ams_id']

      now = datetime.datetime.now()
      cur_year = now.strftime("%Y")
      (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_file)

      cal_fn = cal_file.split("/")[-1]
      cal_dir = cal_dir_from_file(cal_file)

      try:
         cal_params = load_json_file(cal_dir + cal_file)
      except:
         print("\tERROR: Failed to load cal file!", cal_dir , cal_file)
         return(None,None)
      cal_params['cat_image_stars'] = remove_bad_stars(cal_params['cat_image_stars'])

      cal_image_file = cal_file.replace("-calparams.json", ".png")
      if os.path.exists(cal_dir + cal_image_file) is True:
         oimg = cv2.imread(cal_dir + cal_image_file)
      else:
         print("\tERROR: Failed to load cal image file!", cal_dir , cal_image_file)
         return(None,None)


      # get mask
      mask_file = "/mnt/ams2/meteor_archive/{}/CAL/MASKS/{}_mask.png".format(station_id, cam_id)
      if os.path.exists(mask_file) is True:
         if len(oimg.shape) == 3:
            mask = cv2.imread(mask_file)
         else:
            mask = cv2.imread(mask_file, 0)
         #mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
         mask = cv2.resize(mask, (1920,1080))
      else:
         if len(oimg.shape) == 3:
            mask = np.zeros((1080,1920,3),dtype=np.uint8)
         else:
            mask = np.zeros((1080,1920),dtype=np.uint8)

      # add more stars
      oimg = cv2.subtract(oimg, mask)
      #cv2.imshow('mask', oimg)


      cal_params = add_more_stars(cal_fn, cal_params, oimg, oimg, json_conf)
      #try:
         #print("   AZ  :", round(int(cal_params['center_az'])),2)
         #print("   EL  :", round(cal_params['center_el']),2)
         #print("   PA  :", round(cal_params['position_angle']),2)
         #print("   PX  :", round(cal_params['pixscale']),2)
         #print("   STARS:" +  str(len(cal_params['cat_image_stars'])) )
      #except:
         #print("   STRINGS IN CAL PARAMS!")


      # if 0 stars we have to abort
      if "cat_image_stars" not in cal_params:
         print("\tERROR: No stars found in cal image file!", cal_dir , cal_image_file)
         return(None,None)
      elif len(cal_params['cat_image_stars']) == 0:
         # last ditch effort adj 180 on pos?
         pos = 180 - cal_params['position_angle']
         print("TRY 180 - pos way!", pos)
         cal_params['position_angle'] = pos
         cal_params = add_more_stars(cal_fn, cal_params, oimg, oimg, json_conf)
         if len(cal_params['cat_image_stars']) == 0:
            print("\tERROR: No stars found in cal image file!", cal_dir , cal_image_file)
            return(None,None)

      # first check if the file is corrupt. If so reset 1 time, else move to bad.
      if len(cal_params['cat_image_stars']) < 10 or cal_params['total_res_px'] > 10 :
         if "reapply" in cal_params:
            if cal_params['reapply'] >= 2:
               # reset this file! 
               auto_dir = "/mnt/ams2/meteor_archive/" + station_id + "/CAL/AUTOCAL/" + cur_year + "/"
               # add code to track the # of times this has been done. Only allow it 1-2 times then perma delete the calib file
               print("BAD CAL REMOVE:", len(cal_params['cat_image_stars']), cal_params['total_res_px'])
               cmd = "cp " + cal_dir + cal_image_file + " " + auto_dir + cal_image_file.replace("-stacked.png", ".png")
               print("\tCMD:", cmd)
               os.system(cmd)
               cmd = "rm -rf " + cal_dir 
               print("\t", cmd)
               os.system(cmd)
               print("\t***")
               print("\t****")
               print("\t*****")
               print("Reapply already at ", cal_params['reapply'])


               return(None,None)
   
      best_cal = find_best_calibration(cal_file, cal_params, json_conf)
      if best_cal is not None:
         if best_cal['total_res_px'] < cal_params['total_res_px']:
            cal_params = best_cal
            cal_params = add_more_stars(cal_image_file, cal_params, oimg, oimg, json_conf)

      if cal_params['total_res_px'] > 10 or len(cal_params['cat_image_stars']) < 5:

         cal_params = test_fix_pa(cal_image_file, cal_params, oimg.copy(), json_conf)

      #print("BEST:", best_cal['total_res_px'])
      #exit()
      
      if cal_params['total_res_px'] > 10:
         before_files, after_files = get_close_calib_files(cal_file)
      if cal_params['total_res_px'] > 10:
         cal_params = test_cals (cal_fn, cal_params, json_conf, mcp, oimg, before_files, after_files, con, cur)

      if cal_dir is False:
         print("\tCal dir doesn't exist:", cal_dir)
         return(None,None)
      
      if mcp is not None:
         cal_params['x_poly'] = mcp['x_poly']
         cal_params['y_poly'] = mcp['y_poly']
         cal_params['y_poly_fwd'] = mcp['y_poly_fwd']
         cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      else:
         cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)

      mask_file = "/mnt/ams2/meteor_archive/{}/CAL/MASKS/{}_mask.png".format(station_id, cam_id)
      if os.path.exists(mask_file) is True:
         if len(oimg.shape) == 3:
            mask = cv2.imread(mask_file)
         else:
            mask = cv2.imread(mask_file, 0)
         #mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
         mask = cv2.resize(mask, (1920,1080))
      else:
         if len(oimg.shape) == 3:
            mask = np.zeros((1080,1920,3),dtype=np.uint8)
         else:
            mask = np.zeros((1080,1920),dtype=np.uint8)
       
      oimg = cv2.subtract(oimg, mask)

      cal_img = cv2.subtract(oimg, mask)

      star_points, show_img = get_star_points(cal_file, oimg, cal_params, station_id, cam_id, json_conf)
      #print("STAR POINTSS:", len(star_points))
      if SHOW == 1:
         cv2.imshow('pepe', show_img)
         cv2.waitKey(30)

      star_points_img = show_img.copy()
      cal_params['user_stars'] = star_points
      cal_params['star_points'] = star_points
      print("\tRES:", cal_params['total_res_px']) 
      # revert to WCS
      if cal_params['total_res_px'] > 8:
         cal_id = cal_file.split("/")[-1].split("-")[0]
         reset_cal_file(station_id, cal_id)
         #rev_cal_params = revert_to_wcs(cal_fn)
         rev_cal_params = None

      else:
         rev_cal_params = None

      if rev_cal_params is not None:
         rev_cal_params['cat_image_stars'] = pair_star_points(cal_fn, oimg, rev_cal_params, json_conf, con, cur, mcp, False)
         rev_cal_params, bad_stars, marked_img = eval_cal_res(cal_fn, json_conf, rev_cal_params.copy(), oimg,None,None,rev_cal_params['cat_image_stars'])
         print("\tREV RES:", rev_cal_params['total_res_px'])
         rev_cal_params['cat_image_stars'] = pair_star_points(cal_fn, oimg, rev_cal_params, json_conf, con, cur, mcp, False)
         rev_cal_params, bad_stars, marked_img = eval_cal_res(cal_fn, json_conf, rev_cal_params.copy(), oimg,None,None,rev_cal_params['cat_image_stars'])
         new_cp = rev_cal_params
         print("\nREVERT")
         print("\tRA/DEC", new_cp['ra_center'], new_cp['dec_center'])
         print("\tAZ/EL", new_cp['center_az'], new_cp['center_el'])
         print("\tPOS/PX", new_cp['position_angle'], new_cp['pixscale'])
         print("\tSTARS/RES", len(new_cp['cat_image_stars']), new_cp['total_res_px'])
         oscore =  len(cal_params['cat_image_stars']) / cal_params['total_res_px']
         score =  len(new_cp['cat_image_stars']) / new_cp['total_res_px']
         score =  len(new_cp['cat_image_stars']) / new_cp['total_res_px']
         print("\nORIGINAL")

         new_cp = cal_params
         print("\tRA/DEC", new_cp['ra_center'], new_cp['dec_center'])
         print("\tAZ/EL", new_cp['center_az'], new_cp['center_el'])
         print("\tPOS/PX", new_cp['position_angle'], new_cp['pixscale'])
         print("\tSTARS/RES", len(new_cp['cat_image_stars']), new_cp['total_res_px'])
         oscore =  len(cal_params['cat_image_stars']) / cal_params['total_res_px']

         if score > oscore and len(new_cp['cat_image_stars']) > 10:
            cal_params = new_cp.copy()
         print("\tOSCORE/SCORE", oscore, score)
      
      # try wcs 
      if cal_params['total_res_px'] > 16:
         # NOT SURE THIS WORKS!?
         print("RUN BEST WCS")
         temp_cp = best_wcs(cal_fn, cal_params, oimg, con, cur, mcp)
         new_cp = temp_cp.copy()
         print("RA/DEC", new_cp['ra_center'], new_cp['dec_center'])
         print("AZ/EL", new_cp['center_az'], new_cp['center_el'])
         print("POS/PX", new_cp['position_angle'], new_cp['pixscale'])
         print("STARS/RES", len(new_cp['cat_image_stars']), new_cp['total_res_px'])
         oscore =  len(cal_params['cat_image_stars']) / cal_params['total_res_px']
         score =  len(new_cp['cat_image_stars']) / new_cp['total_res_px']
         print("OSCORE/SCORE", oscore, score)


         print("new/old stars", len(temp_cp['cat_image_stars']) , len(cal_params['cat_image_stars']))
         print("new/old res", temp_cp['total_res_px'] , cal_params['total_res_px'])
         if score > oscore:
            cal_params = temp_cp.copy()

      cal_params['cat_image_stars'] = pair_star_points(cal_fn, oimg, cal_params, json_conf, con, cur, mcp, False)
      temp_cp, bad_stars, marked_img = eval_cal_res(cal_fn, json_conf, cal_params.copy(), oimg,None,None,cal_params['cat_image_stars'])

      if len(cal_params['user_stars']) > 0:
         cat_star_ratio = len(cal_params['cat_image_stars']) / len(cal_params['star_points'])
         #print("\tCAT STAR RATIO", cat_star_ratio)

      if SHOW == 1:
         cv2.imshow('pepe', show_img)
         cv2.waitKey(30)

      before =  len(cal_params['cat_image_stars'])

      cal_params['user_stars'] = sorted(cal_params['user_stars'], key=lambda x: x[2], reverse=True)

      if mcp is not None:
         cal_params['x_poly'] = mcp['x_poly']
         cal_params['y_poly'] = mcp['y_poly']
         cal_params['y_poly_fwd'] = mcp['y_poly_fwd']
         cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      else:
         cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)

      # ADD MORE STARS ?
      if True:
         cal_params['cat_image_stars'] = pair_star_points(cal_fn, oimg, cal_params, json_conf, con, cur, mcp, False)
         last_res = cal_params['total_res_px']
         temp_stars = []
         for star in cal_params['cat_image_stars']:
            dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
            center_dist = calc_dist((960,540),(six,siy))

            if center_dist > 600:
               bonus = 4
            else:
               bonus = 3

            if star_int > 30 and cat_dist < last_res * bonus:
               temp_stars.append(star)

         cal_params['cat_image_stars'] = temp_stars


      if len(cal_params['cat_image_stars']) < 10:
           
         if os.path.exists("/mnt/ams2/cal/bad_cals/") is False:
            os.makedirs("/mnt/ams2/cal/bad_cals/")
         cmd = "mv " + cal_dir + " /mnt/ams2/cal/bad_cals/" 
         print(cmd)
         os.system(cmd)

      temp = []
      rez = np.median([row[-2] for row in cal_params['cat_image_stars']])
      reject_stars = []

      # THIS HERE NEEDS TO BE FIXED TO WORK ON AN AVG OF KNOWN VALUES NOT RANDOM GUESSES
      for row in cal_params['cat_image_stars']:
         dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = row 
         center_dist = calc_dist((960,540),(six,siy))

         if 0 <= center_dist < 500:
            fact = 5
         if 500 <= center_dist < 600:
            fact = 6 
         if 600 <= center_dist < 800:
            fact = 7 
         if center_dist >= 800:
            fact = 8 
         else:
            fact = 3

         if cat_dist < rez * fact:
            temp.append(row)
         else:
            reject_stars.append(row)

      # save these to the cal
      temp_rez = []
      for star in temp:
         dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
         temp_rez.append(cat_dist)
      rez = np.median(temp_rez)
      good_temp = []
      for star in  temp:
         dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
         # FIX EDGE STARS HERE?
         
         if cat_dist <= rez * 2.5 and cat_dist < 15:
            good_temp.append(star) 
      if len(good_temp) > 5:
         temp = good_temp
      for star in reject_stars:
         dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star

         cv2.line(cal_img, (int(new_cat_x),int(new_cat_y)), (int(six),int(siy)), (0,0,255), 1)
         cv2.putText(cal_img, "X - " + str(cat_dist) + " " + row[0],  (int(six+4),int(siy)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
      cal_params['reject_stars'] = reject_stars

      if SHOW == 1:
         # Show cal_img with no markings
         cv2.imshow('pepe', cal_img)
         cv2.waitKey(30)
      cal_params['cat_image_stars'] = temp
      cal_params['total_res_px'] = rez 
      cal_params['total_res_deg'] = (rez * (float(cal_params['pixscale']) / 3600) )

      try:
         save_json_file(cal_dir + cal_file, cal_params)
      except:
         print("cal file no longer exists")
         return(cal_params, flux_table)

      import_cal_file(cal_fn, cal_dir, mcp)

      # set the calib lens model poly to the best saved lens model
      if mcp is not None:
         cal_params['x_poly'] = mcp['x_poly']
         cal_params['y_poly'] = mcp['y_poly']
         cal_params['y_poly_fwd'] = mcp['y_poly_fwd']
         cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      else:
         cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)


      cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)

      # show catalog image
      if SHOW == 1:
         # showing the cat image (star names white box and line between the cat star and zp star projection)
         cv2.imshow('pepe', cat_image)
         cv2.waitKey(30)
    

      cal_params['short_bright_stars'] = short_bright_stars
      cal_params['no_match_stars'] = [] 
      cal_image_file = cal_fn.replace("-calparams.json", ".png")
      cal_dir = cal_dir_from_file(cal_image_file)
      cal_json_file = get_cal_json_file(cal_dir)
      if cal_json_file is None:
         return(cal_params, flux_table)


      cal_json_fn = cal_json_file.split("/")[-1]
      oimg = cv2.imread(cal_dir + cal_image_file)
      if oimg is None:
         return(cal_params, flux_table)
      cal_img = oimg.copy()
      cal_params_json = load_json_file(cal_json_file)

      # Need to modes here?
      stars,cat_stars = get_paired_stars(cal_fn, cal_params, con, cur)

      cal_params['cat_image_stars'] = cat_stars

      #print("PXSCALE:", cal_params['pixscale'])

      new_cat = []
      rez = []
      for star in cal_params['cat_image_stars']:
         rez.append(star[-2])
      new_rez = []
      med_res = np.median(rez)
      for star in cal_params['cat_image_stars']:
         dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
         if star[-2] <= med_res * 3:
            new_cat.append(star)
            new_rez.append(star[-2])
      med_res = np.median(new_rez)
      cal_params['cat_image_stars'] = new_cat
      # BUG FOUND HERE!?
      #cal_params= update_center_radec(cal_fn,cal_params,json_conf)

      #print("PXSCALE:", cal_params['pixscale'])

      show_calparams(cal_params)


      # how is this different than get paired stars?
      cal_params['cat_image_stars'] = pair_star_points(cal_fn, cal_img, cal_params.copy(), json_conf, con, cur, mcp, save_img = False)
      temp_cal_params , bad_stars, marked_img = eval_cal_res(cal_fn, json_conf, cal_params.copy(), cal_img,None,None,cal_params['cat_image_stars'])
      extra_text = cal_fn

      star_img = draw_star_image(cal_img.copy(), cal_params['cat_image_stars'],cal_params, json_conf, extra_text) 
      blend_star_cat = cv2.addWeighted(star_points_img, .5, cat_image, .5, .3)
      blend_star_cat_final = cv2.addWeighted(blend_star_cat, .5, star_img, .5, .3)

      temp_cal_params, cat_stars = recenter_fov(cal_fn, temp_cal_params, oimg.copy(),  stars, json_conf, extra_text, None, cal_img, con, cur)

      if temp_cal_params['total_res_px'] > 4 and len(cal_params['cat_image_stars']) > 20:
         new_stars = []
         rez = [row[-2] for row in cal_params['cat_image_stars']] 
         # center dist
         med_rez = np.median(rez) 
         for row in temp_cal_params['cat_image_stars']:
            center_dist = calc_dist((960,540),(new_cat_x,new_cat_y))
            if center_dist < 600:
               factor = 2
            elif 600 <= center_dist < 800:
               factor = 4
            else:
               factor = 5
            if row[-2] <= med_rez * factor:
               new_stars.append(row)
            else:
               print("REJECT:", row)
         if len(new_stars) > 10:
            temp_cal_params['cat_image_stars'] = new_stars
            #temp_cal_params, cat_stars = recenter_fov(cal_fn, temp_cal_params, oimg.copy(),  stars, json_conf, None, oimg, extra_text, con,cur)
            temp_cal_params = minimize_fov(cal_fn, temp_cal_params, cal_fn,oimg,json_conf, False,temp_cal_params, "")
         print("\tSTARS:", len(new_stars))
      
     
      if temp_cal_params['total_res_px'] <= cal_params['total_res_px'] or True:
         cal_params = temp_cal_params
      #else:
      #   print("\tCAL PARAMS OPTIMIZER FAILED!")

      up_stars, cat_image_stars = update_paired_stars(cal_fn, cal_params, stars, con, cur, json_conf)
      cal_params['cat_image_stars'] = cat_image_stars
      update_calibration_file(cal_fn, cal_params, con,cur,json_conf,mcp)
      if "reapply" not in cal_params:
         cal_params['reapply'] = 1
      else:
         cal_params['reapply'] += 1
      save_json_file(cal_json_file, cal_params)
      update_calibration_file(cal_fn, cal_params, con,cur,json_conf,mcp)


      show_calparams(cal_params)      



      #if SHOW == 1:
      #   cv2.imshow("pepe", cal_img)
      #   cv2.waitKey(30)
      #print("STAR POINTS / CAT STARS / CAL RES:", len(cal_params['star_points']), len(cal_params['cat_image_stars']), cal_params['total_res_px'])
      if (cal_params['total_res_px'] > 5 or len(cal_params['cat_image_stars']) < 8) and cal_params['reapply'] > 5:
         #delete_cal_file(cal_fn, con, cur, json_conf)
         print("\n\n (*** DELETE BAD CAL FILE? ***)" + cal_fn)

         bad_cal_dir = "/mnt/ams2/cal/bad_cals/"
         if os.path.exists(bad_cal_dir) is False:
            os.makedirs(bad_cal_dir)
         cmd = "mv " + cal_dir + " " + bad_cal_dir
         cal_root = cal_dir.split("/")[-1]

         print("\tPURGE CAL\n", (cmd))
         if os.path.exists(bad_cal_dir + cal_root) is True:
            os.system("rm -rf " + bad_cal_dir + cal_root)
         os.system(cmd)

      # remove cal if res too high or stars too low and refit is too high
      print("FINAL APPLY RES", len(cal_params['cat_image_stars']), "STARS, ", cal_params['total_res_px'], "RES PX")


      return(cal_params, flux_table)

def cat_star_match(cal_fn, cal_params, cal_img, cat_stars):
   print("cat_star_match:")
   cat_image = cal_img.copy()
   new_cat_image_stars = []
   print("CAT STAR MATCH")
   if SHOW == 1:
      cv2.imshow('pepe', cal_img)
      cv2.waitKey(30)
   if len(cal_img.shape) == 3:
      gray_img = cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)
   else:
      gray_img = cal_img
   if True:
      for row in cat_stars:
         name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y = row
         if mag <= 5.5:
            if new_cat_x < 300:
               cv2.circle(cat_image, (int(zp_cat_x),int(zp_cat_y)), 3, (0,0,255),1)
               # left side
               if new_cat_y < 540:
                  # top left
                  rx1 = zp_cat_x - 10
                  rx2 = zp_cat_x + 60
                  ry1 = zp_cat_y - 10
                  ry2 = zp_cat_y + 60
               else:
                  # bottom left
                  rx1 = zp_cat_x - 10
                  ry1 = zp_cat_y - 60
                  rx2 = zp_cat_x + 60
                  ry2 = zp_cat_y + 10

            elif new_cat_x > 1620:
               cv2.circle(cat_image, (int(zp_cat_x),int(zp_cat_y)), 3, (0,0,255),1)
               # right side
               if new_cat_y < 540:
                  # top right 
                  cv2.circle(cat_image, (int(zp_cat_x),int(zp_cat_y)), 5, (0,0,255),1)
                  rx1 = zp_cat_x - 60
                  ry1 = zp_cat_y - 10
                  rx2 = zp_cat_x + 10
                  ry2 = zp_cat_y + 60
               else:
                  # bottom right 
                  cv2.circle(cat_image, (int(zp_cat_x),int(zp_cat_y)), 5, (0,0,255),1)
                  rx1 = zp_cat_x - 60
                  ry1 = zp_cat_y - 60
                  rx2 = zp_cat_x + 10
                  ry2 = zp_cat_y + 10
            # center
            else:
               cv2.circle(cat_image, (int(zp_cat_x),int(zp_cat_y)), 3, (0,0,255),1)
               rx1 = zp_cat_x - 20
               rx2 = zp_cat_x + 20
               ry1 = zp_cat_y - 20
               ry2 = zp_cat_y + 20

            crop_img = gray_img[int(ry1):int(ry2),int(rx1):int(rx2)]


            if rx1 < 0 or ry1 < 0 or rx2 >= 1920 or ry2 >= 1080:
               continue

            try:
               min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(crop_img)
               avg = int(np.mean(crop_img))
            except:
               continue

            pxd = max_val - avg 

            _, crop_thresh = cv2.threshold(crop_img, max_val * .95, 255, cv2.THRESH_BINARY)
            cnts = get_contours_in_image(crop_thresh)
            if len(cnts) >= 1:
               radius = max(cnts[0][2],cnts[0][3] )
               imx = cnts[0][0] + (cnts[0][2]/2) + rx1
               imy = cnts[0][1] + (cnts[0][3]/2) + ry1
               cx = cnts[0][0] + (cnts[0][2]/2)
               cy = cnts[0][1] + (cnts[0][3]/2)
               star_flux = do_photo(crop_img, (cx,cy), radius+1)
               res = calc_dist((imx,imy), (new_cat_x,new_cat_y))
               zp_res = calc_dist((imx,imy), (zp_cat_x,zp_cat_y))
            else:
               zp_res = 999
               res = 999


            if pxd > 20 and len(cnts) >= 1:

               new_cat_x, new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)
               res_px = calc_dist((imx,imy),(new_cat_x,new_cat_y))
               new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(imx,imy,cal_fn,cal_params,json_conf)
               match_dist = angularSeparation(ra,dec,img_ra,img_dec)
               real_res_px = res_px


               new_cat_image_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,imx,imy,real_res_px,star_flux))


               # good 
               color = (0,255,0)
               act = "keep"
               #up_cat_image_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) )
            elif pxd <= 20 and len(cnts) == 1:
               color = (0,128,0)
               act = "keep"
            elif pxd <= 20:
               color = (0,0,255)
               act = "skip"
            elif len(cnts) == 0:
               color = (0,0,255)
               act = "skip"
            elif len(cnts) > 1:
               color = (0,0,255)
               act = "skip"
            else:
               color = (128,128,128)
               act = "skip"
            gray_img[int(ry1):int(ry2),int(rx1):int(rx2)] = 0

            center_dist = int(calc_dist((960,540),(new_cat_x,new_cat_y)))
            if act == "keep":
               cv2.line(cat_image, (int(new_cat_x),int(new_cat_y)), (int(zp_cat_x),int(zp_cat_y)), (255,255,255), 2)

            cv2.rectangle(cat_image, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), color, 2)
   
         #if SHOW == 1:
         #   cv2.imshow('pepe', cat_image)
         #   cv2.waitKey(30)

   if SHOW == 1:
      cv2.imshow('pepe', cat_image)
      cv2.waitKey(30)

   #if SHOW == 1: 
   #    cv2.imshow('pepe', cat_image) 
   for row in new_cat_image_stars:
      (name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,imx,imy,real_res_px,star_flux) = row
      print("GOOD", name,int(imx),int(imy),round(real_res_px,2))
   return(new_cat_image_stars)
#   exit()

def debug_image(cal_params, cal_img):
   for star in cal_params['user_stars']:
      x,y,b = star
      #print("POINT:", x,y,b)

   tres = []  
   for star in cal_params['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      tres.append(cat_dist)
   mres = np.median(tres)
   print("Median res for stars", mres)
   #for star in cal_params['cat_image_stars']:
   #   dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star

   #print("DEBUG IMAGE", cal_params)
#   exit()

def show_calparams(cal_params):
   if False:
      for key in cal_params:
         if "star" in key:
            print("CP", key, len(cal_params[key]))
         elif "poly" in cal_params:
            print("CP", key, cal_params[key][0])
         else:
            print("CP", key, cal_params[key])

def update_calfiles(cam_id, con,cur, json_conf):
   autocal_dir = "/mnt/ams2/cal/"
   station_id = json_conf['site']['ams_id']

   calfiles_data = load_cal_files(cam_id, con, cur)

   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
   else:
      mcp = None

   #if mcp is None:
   #   print("Can't update until the MCP is made!")

   cff = 0
   for cf in calfiles_data:
      (station_id, camera_id, cal_fn, cal_ts, az, el, ra, dec, position_angle,\
         pixel_scale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
         y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) = calfiles_data[cf]
      if cal_version < mcp['cal_version']:
         print(cal_fn, "needs update!", cal_version, mcp['cal_version'])
         manual_tweek_calib(cal_fn, con, cur, json_conf, mcp, calfiles_data)

         #redo_calfile(cal_fn, con, cur, json_conf)
         #cv2.waitKey(30)
         print("ENDED HERE")
         #repair_calfile_stars(cal_fn, con, cur, json_conf, mcp)
      else:
         print(cal_fn, "is ok!", cal_version, mcp['cal_version'])
      cff += 1
      #if cff > 10:
      #   print("EXIT", cff)
         #exit()


def recenter_fov(cal_fn, cal_params, cal_img, stars, json_conf, extra_text="", this_poly_in=None, meteor_stack_img=None, con=None, cur=None):
   nc = cal_params
   if "station_id" in cal_params:
      station_id = cal_params['station_id']
   else:
      station_id = json_conf['site']['ams_id']
   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)
   # make sure we are using the latest MCP!
   autocal_dir = "/mnt/ams2/cal/"
   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   if "x_poly" in cal_params:
      mcp = None

   elif os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      cal_params['x_poly'] = mcp['x_poly']
      cal_params['y_poly'] = mcp['y_poly']
      cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      cal_params['y_poly_fwd'] = mcp['y_poly_fwd']
 
   else:
      mcp = None
      cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)


   if False: 
      cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)


   this_poly = np.zeros(shape=(4,), dtype=np.float64)
   #if 0 < cal_params['total_res_px'] < .75:
   #   this_poly = [.000005,.000005,.000005,.000005]
   #elif .75 <= cal_params['total_res_px'] < 1:
   #   this_poly = [.00001,.00001,.00001,.00001]
   #elif 1 <= cal_params['total_res_px'] < 5:
   #   this_poly = [.0001,.0001,.0001,.0001]
   #elif 5 <= cal_params['total_res_px'] < 10:
   #   this_poly = [.001,.001,.001,.001] 
   #else:
      # greater than 10
   #   this_poly = [.005,.005,.005,.005] 

   all_res = cal_params['total_res_px']
   if all_res < 10:
      this_poly = [.0001,.0001,.0001,.0001]
   elif 10 <= all_res <= 20:
      this_poly = [.001,.001,.001,.001]
   else:
      this_poly = [.005,.005,.005,.005]


   if this_poly_in is not None:
      this_poly = this_poly_in

   start_cp = dict(cal_params)
   start_res = cal_params['total_res_px']

   center_stars = []
   center_user_stars = []
   for star in cal_params['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
      if 50 <= six <= 1870 and 50 <= siy <= 1030:
         center_stars.append(star)
         center_user_stars.append((six,siy,bp))

   if len(center_stars) < 5:
      center_stars = cal_params['cat_image_stars']

   #extra_text = cal_fn + " "
   nc = dict(cal_params)

   show_calparams(cal_params)

   if len(center_stars) < 10:
      center_stars = cal_params['cat_image_stars']
   extra_text = ""
   #print("DEBUG:", this_poly, cal_params['center_az'], cal_params['center_el'],cal_params['position_angle'],cal_params['pixscale'],cal_params['x_poly'], cal_params['y_poly'], cal_params['x_poly_fwd'], cal_params['y_poly_fwd'],cal_fn, extra_text)
   center_stars = cal_params['cat_image_stars']

   if len(nc['cat_image_stars']) <= 10:
      cal_params = add_more_stars(cal_fn, nc, cal_img, cal_img, json_conf)
#ZZZ

   res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=( np.float64(cal_params['center_az']),np.float64(cal_params['center_el']),np.float64(cal_params['position_angle']),np.float64(cal_params['pixscale']),cal_params['x_poly'], cal_params['y_poly'], cal_params['x_poly_fwd'], cal_params['y_poly_fwd'],cal_fn,cal_img,json_conf, cal_params['cat_image_stars'], extra_text,0), method='Nelder-Mead')
   #res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=( np.float64(cal_params['center_az']),np.float64(cal_params['center_el']),np.float64(cal_params['position_angle']),np.float64(cal_params['pixscale']),cal_params['x_poly'], cal_params['y_poly'], cal_params['x_poly_fwd'], cal_params['y_poly_fwd'],cal_fn,cal_img,json_conf, center_stars, extra_text,0), method='Nelder-Mead')

   #adj_az, adj_el, adj_pos, adj_px = res['x']
   this_poly = res['x']


   if type(nc['x_poly']) is not list:
      nc['x_poly'] = nc['x_poly'].tolist()
      nc['y_poly'] = nc['y_poly'].tolist()
      nc['x_poly_fwd'] = nc['x_poly_fwd'].tolist()
      nc['y_poly_fwd'] = nc['y_poly_fwd'].tolist()
   az = np.float64(cal_params['center_az'])
   el = np.float64(cal_params['center_el'])
   pos = np.float64(cal_params['position_angle'])
   pixscale = np.float64(cal_params['pixscale'])

   new_az = az + (this_poly[0]*az)
   new_el = el + (this_poly[1]*el)
   new_position_angle = pos + (this_poly[2]*pos)
   new_pixscale = pixscale + (this_poly[3]*pixscale)

   nc['center_az'] = new_az
   nc['center_el'] = new_el
   nc['position_angle'] = new_position_angle
   nc['pixscale'] = new_pixscale

   nc['total_res_px'] = res['fun']
   nc['pixscale'] = new_pixscale


   nc = update_center_radec(cal_fn,nc,json_conf)
 
   cat_stars, short_bright_stars, cat_image = get_catalog_stars(nc)

   end_res = nc['total_res_px']
   if end_res > start_res:
      # IGNORE THE RUN!
      nc = start_cp 

   #cat_stars, short_bright_stars, cat_image = get_catalog_stars(nc)
   if False:
      # not sure about this / causing a bug. 
      if "cal_params" in cal_fn:
         # for meteor files
         up_stars, cat_image_stars = update_paired_stars(cal_fn, nc, stars, con, cur, json_conf)
      else:
         # for non meteor files this is a bug / no need to do this. 
         print("CUR:", cur)
         nc['cat_image_stars'] = pair_star_points(cal_fn, cal_img, nc, json_conf, con, cur, mcp, False)
         cat_image_stars = nc['cat_image_stars']

      if len(cat_image_stars) > 0:
         nc['cat_image_stars'] = cat_image_stars
   nc['total_res_px'] = end_res 
   return(nc, cat_stars)


def recenter_cal_file(cal_fn, con, cur, json_conf, mcp):

      cal_image_file = cal_fn.replace("-calparams.json", ".png")
      cal_dir = cal_dir_from_file(cal_image_file)
      cal_json_file = get_cal_json_file(cal_dir)
      cal_json_fn = cal_json_file.split("/")[-1]
      oimg = cv2.imread(cal_dir + cal_image_file)

      # APPLY LATEST MODEL AND RECENTER THE FOV
      # THEN SAVE THE CALP FILE AND UPDATE THE DB

      if os.path.exists(cal_json_file) is True:

         cal_params = load_json_file(cal_json_file)
         cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
         cal_params['short_bright_stars'] = short_bright_stars

         #view_calib(cal_fn,json_conf, cal_params,oimg, show = 0)
         this_poly = np.zeros(shape=(4,), dtype=np.float64)
         this_poly = [0,0,0,0]



         res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=( cal_params['center_az'],cal_params['center_el'],cal_params['position_angle'],cal_params['pixscale'],cal_params['x_poly'], cal_params['y_poly'], cal_image_file,oimg,json_conf, cal_params['cat_image_stars'],cal_params['user_stars'],1,SHOW,None,cal_params['short_bright_stars']), method='Nelder-Mead')

         adj_az, adj_el, adj_pos, adj_px = res['x']

         #nc = minimize_fov(cal_fn, cal_params, cal_fn,oimg,json_conf )
         nc = cal_params.copy()

         nc['center_az'] = cal_params['center_az'] + (adj_az*cal_params['center_az'] )
         nc['center_el'] = cal_params['center_el'] + (adj_az*cal_params['center_el'] )
         nc['position_angle'] = cal_params['position_angle'] + (adj_az*cal_params['position_angle'] )
         nc['pixscale'] = cal_params['pixscale'] + (adj_az*cal_params['pixscale'] )
         nc = update_center_radec(cal_file,nc,json_conf)
         cat_stars, short_bright_stars, cat_image = get_catalog_stars(nc)
         nc['short_bright_stars'] = short_bright_stars

         #print("CAZ", cal_params['center_az'])
         #print("CEL", cal_params['center_el'])
         #print("POS", cal_params['position_angle'])
         #print("PIX", cal_params['pixscale'])
         #print("RES", cal_params['total_res_px'])

         #print("AFTER:")

         nc['total_res_px'] = res_px
         nc['total_res_deg'] = res_deg

         #print("CAZ", nc['center_az'])
         #print("CEL", nc['center_el'])
         #print("POS", nc['position_angle'])
         #print("PIX", nc['pixscale'])
         #print("RES", nc['total_res_px'])
         up_cat_image_stars = []
         for star in cal_params['cat_image_stars']:
            dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
            sql = """
                   SELECT new_cat_x, new_cat_y 
                     FROM calfile_catalog_stars 
                    WHERE cal_fn = ? 
                      AND ra = ? 
                      AND dec = ?
            """
            svals = [cal_fn, ra, dec]
            cur.execute(sql, svals)
            rows = cur.fetchall()
            #print("NEW:", rows[0])
            up_cat_x, up_cat_y = rows[0]
            res_px = calc_dist((six,siy), (up_cat_x,up_cat_y))

            if res_px < 20:
               up_cat_image_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) )

         nc['cat_image_stars'] = up_cat_image_stars
         temp_stars, total_res_px,total_res_deg = cat_star_report(nc['cat_image_stars'], 4)
         nc['total_res_px'] = total_res_px
         nc['total_res_deg'] = total_res_deg

         # only save if new is better than old
         if cal_params['total_res_px'] > total_res_px:
            cal_params = nc
            save_json_file(cal_json_file, cal_params)
            update_calfile(cal_fn, con, cur, json_conf, mcp)
         else:
            print("\tOLD BETTER")

         #view_calib(cal_fn,json_conf, nc,oimg, show = 1)

def redo_calfile(cal_fn, con, cur, json_conf):
   cal_image_file = cal_fn.replace("-calparams.json", ".png")
   cal_dir = cal_dir_from_file(cal_image_file)
   cal_img = cv2.imread(cal_dir + cal_image_file)
   cal_json_file = get_cal_json_file(cal_dir)
   cal_json_fn = cal_json_file.split("/")[-1]

   sql = """
      DELETE FROM calfile_catalog_stars 
            WHERE cal_fn = ?
   """
   ivals = [cal_fn]
   cur.execute(sql, ivals)
   con.commit()

   sql = """
      DELETE FROM calibration_files 
            WHERE cal_fn = ?
   """
   ivals = [cal_fn]
   cur.execute(sql, ivals)
   con.commit()

   sql = """
      DELETE FROM calfile_paired_stars 
            WHERE cal_fn = ?
   """
   ivals = [cal_fn]
   cur.execute(sql, ivals)
   con.commit()

   if os.path.exists(cal_dir + cal_image_file):
      get_image_stars(cal_dir + cal_image_file, con, cur, json_conf)
   else:
      print("NO IMAGE", cal_dir + cal_image_file)






def repair_calfile_stars(cal_fn, con, cur, json_conf, mcp):
   # RE-PAIR STARS WITH LATESTS VALUES FROM DB OR JSON
   # AND MAKE SURE BOTH MATCH BY THE END!
   # COULD ALSO CALL THIS APPLY CAL 

   # LOAD THE FILES
   cal_image_file = cal_fn.replace("-calparams.json", ".png")
   cal_dir = cal_dir_from_file(cal_image_file)
   cal_img = cv2.imread(cal_dir + cal_image_file)
   cal_json_file = get_cal_json_file(cal_dir)
   cal_json_fn = cal_json_file.split("/")[-1]

   cal_params = load_json_file(cal_json_file)
   # RELOAD THE CATALOG STARS BASED ON JSON CAL PARAMS FILE (REFITS OR REMODEL UPDATES SHOULD HAVE ALREADY HAPPENED BEFORE THIS!")
   cat_stars, short_bright_stars = reload_calfile_catalog_stars(cal_fn, cal_params)


   
   # GET PAIRED STARS FROM THE DB
   # THIS IS WHAT WE HAVE CURRENTLY
   # LETS RE-PAIR EACH ONE TO GET THE BEST MATCH / VALUES
   stars,cat_stars = get_paired_stars(cal_fn, cal_params, con, cur)
   for star in stars:
      (cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope) = star
      key = str(ra)[0:5] + "_" + str(dec)[0:5]
      print("ORIG:", cal_fn, name, mag, star_yn, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px)
      #cv2.line(cal_img, (int(new_cat_x),int(new_cat_y)), (int(zp_cat_x),int(zp_cat_y)), (255,255,255), 2)

      if res_px is not None:
         res_px = calc_dist((img_x,img_y), (new_cat_x,new_cat_y))
         if 0 < res_px <= 1:
            color = [0,255,0]
         elif 1 < res_px <= 3:
            color = [255,0,0]
         elif res_px > 3:
            color = [0,0,255]
         else:
            color = [255,255,255]

      if img_x is not None:
         cv2.circle(cal_img, (int(img_x),int(img_y)), 3, (0,69,255),1)
      if new_cat_x is not None:
         cv2.circle(cal_img, (int(new_cat_x),int(new_cat_y)), 5, color,1)
      if zp_cat_x is not None:
         cv2.circle(cal_img, (int(zp_cat_x),int(zp_cat_y)), 3, (128,128,128),1)
      if zp_cat_x is not None:
         cv2.line(cal_img, (int(zp_cat_x),int(zp_cat_y)), (int(img_x),int(img_y)), (128,128,128), 2)
      if new_cat_x is not None:
         cv2.line(cal_img, (int(new_cat_x),int(new_cat_y)), (int(img_x),int(img_y)), color, 1)

      # get close stars from the latest refreshed catalog db 
      star_obj = {}
      star_obj['cal_fn'] = cal_fn
      star_obj['x'] = img_x
      star_obj['y'] = img_y
      star_obj['star_flux'] = star_flux
      close_stars = find_close_stars(star_obj)

      if len(close_stars) > 0:
         for cs in close_stars:
            (cs_cal_fn, cs_name, cs_mag, cs_ra, cs_dec, cs_new_cat_x, cs_new_cat_y, cs_zp_cat_x, cs_zp_cat_y, \
               cs_ximg_x, cs_ximg_y, cs_star_flux, cs_star_yn, cs_star_pd, cs_star_found, cs_lens_model_version, \
               cs_slope, cs_zp_slope, cs_dist, cs_zp_dist) = cs
            cv2.line(cal_img, (int(cs_new_cat_x),int(cs_new_cat_y)), (int(img_x),int(img_y)), [255,255,255], 3)
      else:
         cv2.putText(cal_img, "X",  (int(img_x),int(img_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)

   if SHOW == 1:
      cv2.imshow('pepe', cal_img)
      cv2.waitKey(30)
   #get_image_stars(cal_dir + cal_image_file, con, cur, json_conf, True)
   #view_calfile(cal_fn, con,cur,json_conf)
   #exit()

def cal_data_to_cal_params(cal_fn, cal_data,json_conf, mcp):
   (station_id, camera_id, cal_fn, cal_ts, az, el, ra, dec, position_angle,\
      pixel_scale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
      y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) = cal_data

   x_poly = json.loads(x_poly)
   y_poly = json.loads(y_poly)
   x_poly_fwd = json.loads(x_poly_fwd)
   y_poly_fwd = json.loads(y_poly_fwd)
   cal_params = {}
      
   if True:
      if mcp is not None:
         cal_params['x_poly'] = mcp['x_poly']
         cal_params['y_poly'] = mcp['y_poly']
         cal_params['y_poly_fwd'] = mcp['y_poly_fwd']
         cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      else:
         cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)

   
   cal_params['station_id'] = station_id
   cal_params['camera_id'] = camera_id
   cal_params['cal_fn'] = cal_fn
   cal_params['img_w'] = 1920
   cal_params['img_h'] = 1080 
   cal_params['cal_ts'] = cal_ts
   cal_params['center_az'] = az
   cal_params['center_el'] = el
   cal_params['ra_center'] = ra
   cal_params['dec_center'] = dec
   cal_params['position_angle'] = position_angle
   cal_params['pixscale'] = pixel_scale
   cal_params['total_res_px'] = res_px
   cal_params['total_res_deg'] = res_deg 
   cal_params['x_poly'] = x_poly 
   cal_params['y_poly'] = y_poly 
   cal_params['x_poly_fwd'] = x_poly_fwd 
   cal_params['y_poly_fwd'] = y_poly_fwd 
   cal_params['cal_version'] = y_poly_fwd 
   cal_params['last_update'] = last_update


   cal_params['user_stars'] = []
   cal_params['cat_image_stars'] = []

   stars,cat_stars = get_paired_stars(cal_fn, cal_params, con, cur)
   for star in stars:
      (x_cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope) = star
      if ra is not None:
         cal_params['cat_image_stars'].append((name,mag,ra,dec,ra,dec,res_px,zp_cat_x,zp_cat_y,az,el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux))
      cal_params['user_stars'].append((img_x,img_y,star_flux))

   #print("AZ EL :", cal_fn, cal_params['center_az'], cal_params['center_el'])
   #cal_params = update_center_radec(cal_fn,cal_params,json_conf)
   return(cal_params)

def make_help_img(cal_img):
   print("CI", cal_img.shape)
   x1 = int((1920 / 2) - 400)
   x2 = int((1920 / 2) + 400)
   y1 = int((1080/ 2) - 400)
   y2 = int((1080/ 2) + 400)
   if cal_img is not None:
      temp_img = cal_img.copy()
   else:
      temp_img = np.zeros((1080,1920,3),dtype=np.uint8) 


   bgimg = temp_img[y1:y2, x1:x2]
   help_image = np.zeros((800,800,3),dtype=np.uint8) 
   try:
      blend_img = cv2.addWeighted(bgimg, .5, help_image, .5,0)
   except:
      blend_img = np.zeros((800,800,3),dtype=np.uint8) 
   cv2.putText(blend_img, "ALLSKYOS - CALIBRATION TOOL",  (100,30), cv2.FONT_HERSHEY_SIMPLEX, .9, (128,128,128), 2)
   cv2.putText(blend_img, "[ESC] = Quit",  (120,100), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[F1]  = Display/Hide this help message",  (120,140), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[A]   = -Azimuth ",  (120,180), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[S]   = -Elevation",  (120,220), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[D]   = +Elevation",  (120,260), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[F]   = +Azimuth ",  (120,300), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[Q]   = -Pixel Scale",  (120,340), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[W]   = -Position Angle",  (120,380), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[E]   = +Position Angle",  (120,420), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[R]   = +Pixel Scale",  (120,460), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[C]   = Center FOV",  (120,500), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[P]   = Re-Fit",  (120,540), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[0]   = Set Interval to 1.0",  (120,580), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[1]   = Set Interval to 0.1",  (120,620), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[2]   = Set Interval to 0.01",  (120,660), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[3]   = Set Interval to 0.001",  (120,700), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)

   print(x1,y1,x2,y2)
   print("T", temp_img.shape)
   print("B", blend_img.shape)
   temp_img[y1:y2,x1:x2] = blend_img

   cv2.rectangle(temp_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 2)
   return(temp_img)

def show_message(cal_img, message, px, py):
   val = 255
   for i in range(0, 10):
      val = val - (i * 10)
      temp_img = cal_img.copy()
      color = [val,val,val]
      cv2.putText(temp_img, message,  (px,py), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
      if SHOW == 1:
         cv2.resizeWindow("TWEEK CAL", 1920, 1080)
         cv2.imshow("TWEEK CAL", temp_img)
         cv2.waitKey(30)



def cat_view(cal_fn, con, cur, json_conf, mcp=None):
   print("CAT VIEW")
   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)
   cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, None, None, mcp)

   cal_img_fn = cal_fn.replace("-calparams.json", ".png")
   cal_image_file = cal_fn.replace("-calparams.json", ".png")
   cal_dir = cal_dir_from_file(cal_image_file)
   cal_json_file = get_cal_json_file(cal_dir)
   cal_json_fn = cal_json_file.split("/")[-1]

   if os.path.exists(cal_dir + cal_img_fn):
      clean_cal_img = cv2.imread(cal_dir + cal_img_fn)

   cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
   if SHOW == 1:
      cv2.imshow('pepe', cat_image)
      cv2.waitKey(30)
   for star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
      #print(name,mag,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y)

   

def manual_tweek_calib(cal_fn, con, cur, json_conf,mcp, calfiles_data):
   help_on = False
   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)

   cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, None, mcp)


   if cal_img is not None:
      help_img = make_help_img(cal_img) 
   else:
      help_img = np.zeros((800,800,3),dtype=np.uint8)

   interval = .1

   cal_img_fn = cal_fn.replace("-calparams.json", ".png")
   cal_image_file = cal_fn.replace("-calparams.json", ".png")
   cal_dir = cal_dir_from_file(cal_image_file)
   cal_json_file = get_cal_json_file(cal_dir)
   cal_json_fn = cal_json_file.split("/")[-1]
   if os.path.exists(cal_dir + cal_img_fn):
      clean_cal_img = cv2.imread(cal_dir + cal_img_fn)

   cv2.namedWindow("TWEEK CAL")
   cv2.resizeWindow("TWEEK CAL", 1920, 1080)

   cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
   cal_params['short_bright_stars'] = short_bright_stars
   stars,cat_image_stars = get_paired_stars(cal_fn, cal_params, con, cur)
   cal_params['cat_image_stars'] = cat_image_stars

   cat_on = False

   while True:
      if help_on is True and SHOW == 1:
         cv2.imshow("TWEEK CAL", help_img)
      elif SHOW == 1:
         cv2.imshow("TWEEK CAL", cal_img)

      key = cv2.waitKey(0)
      if key == 27:
         return()
      if key == 104 or key == 190:
         if help_on is False:
            help_on = True
            help_img = make_help_img(cal_img) 
            cv2.imshow('TWEEK CAL', help_img) 
         else:
            cv2.imshow('TWEEK CAL', cal_img) 
            help_on = False
      if key == 102:
         cal_params['center_az'] += interval

        # cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, None, mcp)

         cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, cal_params,mcp)
         show_message(cal_img, "AZ + " + str(interval),900,500 )
      if key == 97:
         cal_params['center_az'] -= interval
         cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, cal_params,mcp)
         show_message(cal_img, "AZ - " + str(interval),900,500 )
      if key == 115:
         cal_params['center_el'] -= interval
         cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, cal_params,mcp)
         show_message(cal_img, "EL - " + str(interval),900,500 )
      if key == 100:
         cal_params['center_el'] += interval

         print("CAL FN :", cal_fn, len(cal_params['cat_image_stars']),cal_params['total_res_px'] )
         cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, cal_params,mcp)
         show_message(cal_img, "EL + " + str(interval),900,500 )
      if key == 119:
         cal_params['position_angle'] -= interval
         cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, cal_params,mcp)
         show_message(cal_img, "PA - " + str(interval),900,500 )
      if key == 101:
         cal_params['position_angle'] += interval
         cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, cal_params,mcp)
         show_message(cal_img, "PA + " + str(interval),900,500 )
      if key == 113:
         cal_params['pixscale'] -= interval
         cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, cal_params,mcp)
         show_message(cal_img, "PX - " + str(interval),900,500 )
      if key == 114:
         cal_params['pixscale'] += interval
         show_message(cal_img, "PX + " + str(interval),900,500 )

      if key == 99 or key == 191:
         show_message(cal_img, "Recenter FOV Fit" + str(interval),900,500 )
         cal_params, cat_stars = recenter_fov(cal_fn, cal_params, clean_cal_img.copy(), stars, json_conf)
         cal_params['short_bright_stars'] = short_bright_stars
         cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, cal_params, mcp)


      if key == 112 or key == 192:
         show_message(cal_img, "Recenter Poly Vars" + str(interval),900,500 )
      if key == 193:
         if cat_on is True:
            cv2.imshow('TWEEK CAL', cal_img) 
            cat_on = False
         else:
            cv2.imshow('TWEEK CAL', catalog_image) 
            cat_on = True 





      if key == 48 :
         interval = 1
         show_message(cal_img, "Set interval to " + str(interval),900,500 )
      if key == 49 :
         interval = .1
         show_message(cal_img, "Set interval to " + str(interval),900,500 )
      if key == 50 :
         interval = .01
         show_message(cal_img, "Set interval to " + str(interval),900,500 )
      if key == 51 :
         interval = .001
         show_message(cal_img, "Set interval to " + str(interval),900,500 )

      cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
      up_stars, cat_image_stars = update_paired_stars(cal_fn, cal_params, stars, con, cur, json_conf)
      cal_params['cat_image_stars'] = cat_image_stars

      cal_params['short_bright_stars'] = short_bright_stars
      cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, cal_params, mcp)


      blend_img = cv2.addWeighted(cal_img, .9, cat_image, .1,0)
      cal_img= blend_img

      #cv2.imshow("TWEEK CAL", blend_img)
      help_img = make_help_img(cal_img) 


def view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data= None, cp = None,mcp=None):
   calfiles_data = load_cal_files(cam_id, con, cur)
   #print("start view calfiles ", cal_fn, len(calfiles_data))
   if calfiles_data is not None:
      # we are dealing with a cal-file not a meteor-file
      if cal_fn in calfiles_data:
         cal_data = calfiles_data[cal_fn]
      else:
         print("PROBLEM cal_fn is not in the cal data!?", cal_fn, calfiles_data.keys())
         print("was it moved to the extra cal folder?")
         # try to load it?
         cal_data = load_cal_files(cam_id, con, cur, cal_fn)

         #print(len(calfiles_data.keys()), "calfiles data")
         #exit()
         return(False, False)
   else:
      print("CAL files data is none!", calfiles_data)
      exit()

   if cp is None:
      cal_params = cal_data_to_cal_params(cal_fn, cal_data,json_conf, mcp)
   else:
      cal_params = cp.copy()

   cal_img_fn = cal_fn.replace("-calparams.json", ".png")
   cal_image_file = cal_fn.replace("-calparams.json", ".png")
   cal_dir = cal_dir_from_file(cal_image_file)
   cal_json_file = get_cal_json_file(cal_dir)
   if cal_json_file is None:
      return (None,None)
   print("CAL JSON FILE IS : ", cal_json_file)

   
   cal_json_fn = cal_json_file.split("/")[-1]

   if os.path.exists(cal_dir + cal_img_fn):
      cal_img = cv2.imread(cal_dir + cal_img_fn)
   else:
      return(None,None)

   
   cal_params = update_center_radec(cal_fn,cal_params,json_conf)

   print("Get paired stars")
   stars, cat_image_stars = get_paired_stars(cal_fn, cal_params, con, cur)

   cal_params['cat_image_stars'] = cat_image_stars

   rez = []

   for star in stars:
      (cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope) = star
      if ra is not None:
         res_px = calc_dist((img_x,img_y), (new_cat_x,new_cat_y))
         zp_res_px = calc_dist((img_x,img_y), (zp_cat_x,zp_cat_y))
         rez.append(res_px)
      else:
         res_px = None
      if res_px is not None:
         if 0 < res_px <= 1:
            color = [0,255,0]
         elif 1 < res_px <= 3:
            color = [255,0,0]
         elif res_px > 3:
            color = [0,0,255]
         else:
            color = [255,255,255]
      else:
         # There is no match for this star
         cv2.putText(cal_img, "X",  (int(img_x + 5),int(img_y )), cv2.FONT_HERSHEY_SIMPLEX, .5, (0,0,128), 2)

      if img_x is not None:
         cv2.circle(cal_img, (int(img_x),int(img_y)), 3, (0,69,255),1)
      if new_cat_x is not None:
         cv2.circle(cal_img, (int(new_cat_x),int(new_cat_y)), 5, color,1)
      if zp_cat_x is not None:
         cv2.circle(cal_img, (int(zp_cat_x),int(zp_cat_y)), 3, (128,128,128),1)
      if zp_cat_x is not None:
         cv2.line(cal_img, (int(zp_cat_x),int(zp_cat_y)), (int(img_x),int(img_y)), (128,128,128), 2)
      if new_cat_x is not None:
         cv2.line(cal_img, (int(new_cat_x),int(new_cat_y)), (int(img_x),int(img_y)), color, 1)

   mean_res = np.mean(rez)
   cal_params['total_res_px'] = mean_res 
   desc = json_conf['site']['ams_id'] + " " + cal_fn.replace("-calparams.json", "")
   desc = desc.replace("-stacked", "")
   desc += " | "

   desc += "AZ {:.4f} | ".format(cal_params['center_az'])
   desc += "EL {:.4f} | ".format(cal_params['center_el'])
   desc += "RA {:.4f} | ".format(float(cal_params['ra_center']))
   desc += "DEC {:.4f} | ".format(float(cal_params['dec_center']))
   desc += "POS {:.4f} | ".format(cal_params['position_angle'])
   desc += "PIX {:.4f} | ".format(cal_params['pixscale'])
   desc += "RES {:.3f} | ".format(mean_res)
   cv2.putText(cal_img, desc,  (250,15), cv2.FONT_HERSHEY_SIMPLEX, .6, (128,128,128), 1)

   # todo add total_res_deg...
   return(cal_img, cal_params)

def update_paired_stars(cal_fn, cal_params, stars, con, cur, json_conf):
   # this will update existing paired stars with latest cat x,y based on provided cal_params


      # get stars from the cal_params

   up_stars = []
   up_cat_image_stars = []
   #print("CALP", cal_params['center_az'], cal_params['center_el'], cal_params['ra_center'], cal_params['dec_center'] )
   for star in stars:
      #print("STAR IS:", star)
      (cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope) = star

      n_new_cat_x,n_new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)

      if new_cat_x is None:
         continue
      if n_new_cat_x is not None:
         n_res_px = calc_dist((img_x,img_y), (n_new_cat_x,n_new_cat_y))
      else:
         n_res_px = 0

      #print("OLD {} {}".format(new_cat_x, new_cat_y))
      #print("NEW {} {}".format(n_new_cat_x, n_new_cat_y))
      #print("___")

      up_stars.append((cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope))
      sql = """
         UPDATE calfile_paired_stars
            SET new_cat_x = ?,
                new_cat_y = ?,
                res_px = ?
          WHERE cal_fn = ?
            AND img_x = ?
            AND img_y = ?
      """
      uvals = [n_new_cat_x, n_new_cat_y, n_res_px, cal_fn, img_x, img_y]
      cur.execute(sql, uvals)
      #print(sql)
      #print(uvals)
      # temp holder / fix later

      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params,json_conf)

      img_ra = img_ra
      img_dec = img_dec
      img_az = img_az
      img_el = img_el
      match_dist = zp_res_px
      cat_dist = res_px
      if ra is not None:
         up_cat_image_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux))
   con.commit()
   return(up_stars, up_cat_image_stars)


def get_image_stars(cal_image_file, con, cur, json_conf,force=False):

   print("get image stars 1")
   time.sleep(5)
   # 1
   # run this the first time the image is processed to extract stars and pairs?

   #print("CAL IMAGE_FILE", cal_image_file)

   if "/" in cal_image_file:
      cal_image_file = cal_image_file.split("/")[-1]

   """
      in: image file to extract stars from
     output : x,y,intensity of each point that 'passes' the star tests
   """

   cal_fn = cal_image_file.split("-")[0]


   zp_star_chart_img = np.zeros((1080,1920,3),dtype=np.uint8)


   # this will update existing paired stars with latest cat x,y based on provided cal_params


      # get stars from the cal_params 

   up_stars = []
   up_cat_image_stars = []
   #print("CALP", cal_params['center_az'], cal_params['center_el'], cal_params['ra_center'], cal_params['dec_center'] )
   for star in stars:
      print("UPDATE:", star)
      (cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope) = star

      n_new_cat_x,n_new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)


      if new_cat_x is None:
         continue
      if n_new_cat_x is not None:
         n_res_px = calc_dist((img_x,img_y), (n_new_cat_x,n_new_cat_y))
      else:
         n_res_px = 0

      #print("OLD {} {}".format(new_cat_x, new_cat_y))
      #print("NEW {} {}".format(n_new_cat_x, n_new_cat_y))
      #print("___")

      up_stars.append((cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope)) 
      sql = """
         UPDATE calfile_paired_stars 
            SET new_cat_x = ?, 
                new_cat_y = ?, 
                res_px = ? 
          WHERE cal_fn = ? 
            AND img_x = ? 
            AND img_y = ?
      """
      uvals = [n_new_cat_x, n_new_cat_y, n_res_px, cal_fn, img_x, img_y]
      cur.execute(sql, uvals)
      #print(sql)
      #print(uvals)
      # temp holder / fix later

      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params,json_conf)

      img_ra = img_ra 
      img_dec = img_dec 
      img_az = img_az 
      img_el = img_el 
      match_dist = zp_res_px
      cat_dist = res_px 
      if ra is not None:
         up_cat_image_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux)) 
   con.commit()

   return(up_stars, up_cat_image_stars)

def update_calibration_file(cal_fn, cal_params, con,cur,json_conf,mcp):
   ts = time.time()

   if type(cal_params['x_poly']) is not list:
      cal_params['x_poly'] = cal_params['x_poly'].tolist()
      cal_params['y_poly'] = cal_params['y_poly'].tolist()
      cal_params['x_poly_fwd'] = cal_params['x_poly_fwd'].tolist()
      cal_params['y_poly_fwd'] = cal_params['y_poly_fwd'].tolist()

   if mcp is None:
      cv = 1
   else:
      cv = mcp['cal_version']

   uvals = [ts, cal_params['center_az'], cal_params['center_el'], cal_params['ra_center'], cal_params['dec_center'], \
            cal_params['position_angle'], cal_params['pixscale'], json.dumps(cal_params['x_poly']), json.dumps(cal_params['y_poly']), \
            json.dumps(cal_params['x_poly_fwd']), json.dumps(cal_params['y_poly_fwd']), cal_params['total_res_px'], cal_params['total_res_deg'], \
            cv, ts, cal_fn]
   sql = """
      UPDATE calibration_files 
         SET 
                 cal_ts = ?,
                     az = ?,
                     el = ?,
                     ra = ?,
                    dec = ?,
         position_angle = ?,
            pixel_scale = ?,
                 x_poly = ?,
                 y_poly = ?,
             x_poly_fwd = ?,
             y_poly_fwd = ?,
                 res_px = ?,
                res_deg = ?,
            cal_version = ?,
            last_update = ?
       WHERE cal_fn = ? 
   """

   #print(sql)
   #print(uvals)
   cur.execute(sql, uvals)
   con.commit()

def update_calfile(cal_fn, con, cur, json_conf, mcp):

   cal_root = cal_fn.split("-")[0]
   cal_dir = "/mnt/ams2/cal/freecal/" + cal_root + "/"  
   cal_img_fn = cal_fn.replace("-calparams.json", ".png")
   if os.path.exists(cal_dir + cal_img_fn):
      cal_img = cv2.imread(cal_dir + cal_img_fn)
   if os.path.exists(cal_dir + cal_fn) is True:
      cal_params = load_json_file(cal_dir + cal_fn)
   else:   
      print(cal_dir + cal_fn + " NOT FOUND.")
      exit()

   cal_params['x_poly'] = mcp['x_poly']
   cal_params['y_poly'] = mcp['y_poly']
   cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
   cal_params['y_poly_fwd'] = mcp['y_poly_fwd']

   save_json_file(cal_dir + cal_fn, cal_params)

   sql = """UPDATE calibration_files SET az = ?, el = ?, ra = ?, dec = ?, position_angle = ?, pixel_scale = ?, x_poly = ?, y_poly = ?, x_poly_fwd = ?, y_poly_fwd = ?
            WHERE cal_fn = ?
   """

   uvals = [cal_params['center_az'], cal_params['center_el'], cal_params['ra_center'], cal_params['dec_center'], cal_params['position_angle'], cal_params['pixscale'], json.dumps(mcp['x_poly']), json.dumps(mcp['y_poly']), json.dumps(mcp['x_poly_fwd']), json.dumps(mcp['y_poly_fwd']), cal_fn ]
   #print(sql)
   #print(uvals)
   cur.execute(sql, uvals)

   sql = """
      SELECT station_id, camera_id, cal_fn, cal_ts, az, el, ra, dec, position_angle, pixel_scale, 
             zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, y_poly, x_poly_fwd, y_poly_fwd, 
             res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update
        FROM calibration_files WHERE cal_fn = ?
   """
   svals = [cal_fn]
   cur.execute(sql, svals)
   rows = cur.fetchall()


   # UPDATE THE CATALOG
   cat_stars, short_bright_stars,calibration_image = get_catalog_stars(cal_params)
   for star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
      desc = name + " " + str(mag)
      #cv2.putText(zp_star_chart_img, desc,  (zp_cat_x,zp_cat_y), cv2.FONT_HERSHEY_SIMPLEX, .4, (128,128,128), 1)
      cv2.line(cal_img, (int(new_cat_x),int(new_cat_y)), (int(zp_cat_x),int(zp_cat_y)), (255,255,255), 2)
      sql = """
               INSERT OR REPLACE INTO calfile_catalog_stars (
                      cal_fn,
                      name,
                      mag,
                      ra,
                      dec,
                      new_cat_x,
                      new_cat_y,
                      zp_cat_x,
                      zp_cat_y
               )
               VALUES (?,?,?,?,?,?,?,?,?)
      """
      ivals = [cal_fn, name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y]
      try:
         cur.execute(sql, ivals)
      except:
         print("Must be done already")
   con.commit()
   if SHOW == 1:
      cv2.imshow("calview", cal_img)
      cv2.waitKey(60)

   # GET THE CURRENT STARS, UPDATE THE PAIRS BASED ON NEWLY LOADED CAT STAR POSITIONS
   sql = """
      SELECT cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope
        FROM calfile_paired_stars
       WHERE cal_fn = ?
   """
   svals = [cal_fn]
   #print(sql)
   #print(svals)
   cur.execute(sql, svals )

   # PAIR STARS AREA HERE..
   rows = cur.fetchall()
   all_good_stars = []
   for row in rows:
      cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope = row

      if new_cat_x is not None and new_cat_y is not None and img_x is not None and img_y is not None:
         res_px = calc_dist((img_x,img_y), (new_cat_x,new_cat_y))
      else:
         res_px = None

      #print(name, new_cat_x, new_cat_y, img_x, img_y, res_px)
      star_obj = {}
      star_obj['x'] = img_x
      star_obj['y'] = img_y
      star_obj['star_flux'] = star_flux
      star_obj['cal_fn'] = cal_fn 
      close_stars = find_close_stars(star_obj)

      pp = 1
      for cs in close_stars:
         (cal_fn, name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, \
            ximg_x, ximg_y, star_flux, star_yn, star_pd, star_found, lens_model_version, \
            slope, zp_slope, dist, zp_dist) = cs
         #if new_cat_x is None or new_cat_y is None or img_x is None or img_y is None:
         #   continue
         res_px = calc_dist((img_x,img_y), (new_cat_x,new_cat_y))
         zp_dist = calc_dist((img_x,img_y), (zp_cat_x,zp_cat_y))
         slope = (img_y - new_cat_y) / (img_x - new_cat_x)
         zp_slope = (img_y - zp_cat_y) / (img_x - zp_cat_x)

         #print("   CLOSE:", name, mag, new_cat_x, new_cat_y, img_x, img_y, res_px)

         if pp == 1:
            # UPDATE THE calfile_paired_stars table
            sql = """
               UPDATE calfile_paired_stars SET name = ?, 
                                               mag = ?,
                                               ra = ?,
                                               dec = ?,
                                               new_cat_x = ?,
                                               new_cat_y = ?,
                                               zp_cat_x = ?,
                                               zp_cat_y = ?,
                                               slope = ?,
                                               zp_slope = ?,
                                               res_px = ?,
                                               zp_res_px = ?
                                         WHERE cal_fn = ?
                                           AND img_x = ?
                                           AND img_y = ?
            """
            uvals = [name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, slope, zp_slope, res_px, zp_dist, cal_fn, img_x, img_y]
            cur.execute(sql, uvals)
            #print(sql)
            #print(uvals)
         pp += 1


def reload_calfile_catalog_stars(cal_fn, cal_params):

   sql = """
      DELETE FROM calfile_catalog_stars 
            WHERE cal_fn = ?
   """
   ivals = [cal_fn]
   cur.execute(sql, ivals)
   con.commit()

   cat_stars, short_bright_stars = get_catalog_stars(cal_params)
   for star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
      sql = """
               INSERT OR REPLACE INTO calfile_catalog_stars (
                      cal_fn,
                      name,
                      mag,
                      ra,
                      dec,
                      new_cat_x,
                      new_cat_y,
                      zp_cat_x,
                      zp_cat_y
               )
               VALUES (?,?,?,?,?,?,?,?,?)
      """
      ivals = [cal_fn, name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y]
      try:
         cur.execute(sql, ivals)
      except:
         print("Must be done already")
   con.commit()
   return(cat_stars, short_bright_stars)


def get_paired_stars(cal_fn, cal_params, con, cur):
   sql = """
      SELECT cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope
        FROM calfile_paired_stars
       WHERE cal_fn = ?
   """
   svals = [cal_fn]
   cur.execute(sql, svals )
   up_cat_image_stars = []
   # PAIR STARS AREA HERE..
   rows = cur.fetchall()
   stars = []
   used = {}
   dupes = {}
   counter = 0
   for row in rows:
      cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope = row
      key = str(ra) + "_" + str(dec)
      if key not in used:

         stars.append((cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope))
         used[key] = 1
      else:
         dupes[key] = 1

      # temp holder / fix later
      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params,json_conf)

      img_ra = img_ra
      img_dec = img_dec
      img_az = img_az
      img_el = img_el 
      if ra is not None and img_ra is not None:
         match_dist = angularSeparation(ra,dec,img_ra,img_dec)
      else:
         match_dist = 999


      cat_dist = res_px 
      if ra is not None:
         up_cat_image_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,zp_cat_x,zp_cat_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux)) 
      counter += 1

   return(stars, up_cat_image_stars)


def get_image_stars(cal_image_file, con, cur, json_conf,force=False):
   print("get image stars 2")
   time.sleep(5)
   # 2
   # run this the first time the image is processed to extract stars and pairs?

   print("CAL IMAGE_FILE", cal_image_file)

   if "/" in cal_image_file:
      cal_image_file = cal_image_file.split("/")[-1]

   """
      in: image file to extract stars from
     output : x,y,intensity of each point that 'passes' the star tests
   """

   cal_fn = cal_image_file.split("-")[0]

   sql = "DELETE FROM calfile_paired_stars where cal_fn = ?"
   if cur is not None:
      cur.execute(sql, [cal_image_file] )
      con.commit()

   zp_star_chart_img = np.zeros((1080,1920,3),dtype=np.uint8)
   star_chart_img = np.zeros((1080,1920,3),dtype=np.uint8)

   image_stars = []
   cv2.namedWindow("calview")
   cv2.resizeWindow("calview", 1920, 1080)
   # setup values
   cal_dir = cal_dir_from_file(cal_image_file)
   if cal_dir is False:
      cf = cal_image_file.split("/")[-1]
      cal_dir = cal_image_file.replace(cf, "")

   if cal_dir is False:
      print("Corrupted files or not named right.")
      return()


   cal_json_file = get_cal_json_file(cal_dir)
   cal_json_fn = cal_json_file.split("/")[-1]


   resp = check_calibration_file(cal_json_fn, con, cur)
   if resp is True and force is False:
      print("SKIP DONE!")
      print("Response from insert", resp)
      #return() 
   if resp is False and cur is not None:
      insert_calib(cal_json_file, con, cur, json_conf)
      con.commit()
      print(cal_json_file)


   # load the image
   if os.path.exists(cal_dir + cal_image_file) is True:
      cal_img = cv2.imread(cal_dir + cal_image_file)
      cal_img_orig = cal_img.copy()
   else:
      print("No image_file!")
      return(False) 


   if os.path.exists(cal_json_file) is True:
      cal_params = load_json_file(cal_json_file)
   else:
      return(False) 

   cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
   for star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
      desc = name + " " + str(mag)
      #cv2.putText(zp_star_chart_img, desc,  (zp_cat_x,zp_cat_y), cv2.FONT_HERSHEY_SIMPLEX, .4, (128,128,128), 1)
      cv2.line(zp_star_chart_img, (int(new_cat_x),int(new_cat_y)), (int(zp_cat_x),int(zp_cat_y)), (255,255,255), 2)
      sql = """
               INSERT INTO calfile_catalog_stars (
                      cal_fn,
                      name,
                      mag,
                      ra,
                      dec,
                      new_cat_x,
                      new_cat_y,
                      zp_cat_x,
                      zp_cat_y 
               ) 
               VALUES (?,?,?,?,?,?,?,?,?)
      """
      ivals = [cal_json_fn, name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y]
      try:
         cur.execute(sql, ivals)
      except:
         print("Must be done already")
   con.commit()
   if SHOW == 1:
      cv2.imshow("calview", zp_star_chart_img)
      cv2.waitKey(30)

   gray_orig = cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)
   gray_img  = cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)
   show_img = cal_img.copy()
   if SHOW == 1:
      cv2.imshow("calview", show_img)
      cv2.waitKey(30)

   # check top 100 brightest points in the image
   for i in range(0,200):
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_img)
      resp = make_star_roi(mx,my,32)
      sbx = mx
      sby = my
      status,x1,y1,x2,y2 = resp
      valid = False
      if status is True:
         crop_img = gray_orig[y1:y2,x1:x2]
         avg_val = np.mean(crop_img)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_img)
         pxd = max_val - avg_val 

         _, crop_thresh = cv2.threshold(crop_img, max_val * .85, 255, cv2.THRESH_BINARY)
         #cv2.imshow('crop_thresh', crop_thresh)
         cnts = get_contours_in_image(crop_thresh)

         if pxd > 20 and len(cnts) == 1:
            valid = True

         star_yn = ai_check_star(crop_img, cal_fn)

         if len(cnts) == 1:
            x,y,w,h = cnts[0]
            cx = x + (w/2)
            cy = y + (h/2)
            if w > h:
               radius = w
            else:
               radius = h
            if True:
               star_flux = do_photo(crop_img, (cx,cy), radius+1)
            #try:
            #except:
            #   star_flux = 0

         else:
            valid = False

         if valid is True:

            #print("FLUX / YN:", star_flux, star_yn)

            star_obj = {}
            star_obj['cal_fn'] = cal_json_fn 
            star_obj['x'] = x1 + (x) + (w/2)
            star_obj['y'] = y1 + (y) + (h/2)
            star_obj['star_flux'] = star_flux
            star_obj['star_yn'] = star_yn
            star_obj['star_radius'] = radius
            image_stars.append(star_obj)
            desc = str(int(star_flux)) + " " + str(int(star_yn)) 
            if star_yn > 90:
               cv2.putText(show_img, desc,  (x1,y1), cv2.FONT_HERSHEY_SIMPLEX, .4, (128,128,128), 1)
               cv2.rectangle(show_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1)
            else:
               cv2.putText(show_img, desc,  (x1,y1), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,0), 1)
               cv2.rectangle(show_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 0, 0), 1)


            # Do an insert here into calfile_paired_stars table
            sql = """
               INSERT INTO calfile_paired_stars (
                           cal_fn, 
                           img_x, 
                           img_y, 
                           star_flux, 
                           star_yn, 
                           star_pd)
                    VALUES (?,?,?,?,?,?)
            """
            ivals = [cal_json_fn, star_obj['x'], star_obj['y'], star_flux, star_yn, pxd]
            print(sql)
            print(ivals)
            try:
               cur.execute(sql, ivals)
            except:
               print("Must be done already")


      gray_img[y1:y2,x1:x2] = 0
      if SHOW == 1:
         cv2.imshow("calview", show_img)
         cv2.waitKey(10)

   if SHOW == 1:
      cv2.waitKey(30)

   print("NOW LETS PAIR THE STARS!")
   for star_obj in image_stars:
      
      cal_fn = star_obj['cal_fn']
      x = star_obj['x']
      y = star_obj['y']
      star_flux = star_obj['star_flux']
      close_stars = find_close_stars(star_obj)

      pp = 1
      if len(close_stars) == 0:
         cv2.putText(show_img, "X",  (int(x + 5),int(y + 5)), cv2.FONT_HERSHEY_SIMPLEX, .5, (0,0,128), 2)
         continue

      for pstar in close_stars:
         (cal_fn, name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, \
         img_x, img_y, cat_star_flux, star_yn, star_pd, star_found, lens_model_version, \
         slope, zp_slope, dist, zp_dist) = pstar

        
         desc = str(int(mag))
         cv2.putText(show_img, desc,  (int(zp_cat_x+20),int(zp_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .5, (128,128,128), 2)
         cv2.line(show_img, (int(zp_cat_x),int(zp_cat_y)), (int(x),int(y)), (128,128,128), 2)
         if pp == 1:
            # UPDATE THE calfile_paired_stars table
            res_px = calc_dist((x,y), (new_cat_x,new_cat_y))
            sql = """
               UPDATE calfile_paired_stars SET name = ?, 
                                               mag = ?,
                                               ra = ?,
                                               dec = ?,
                                               new_cat_x = ?,
                                               new_cat_y = ?,
                                               zp_cat_x = ?,
                                               zp_cat_y = ?,
                                               slope = ?,
                                               zp_slope = ?,
                                               res_px = ?,
                                               zp_res_px = ?
                                         WHERE cal_fn = ?
                                           AND img_x = ?
                                           AND img_y = ?
            """
            uvals = [name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, slope, zp_slope, res_px, zp_dist, cal_json_fn, x, y]
            cur.execute(sql, uvals)
            #print(sql)
            #print(uvals)
            #cv2.line(cal_img_orig, (int(new_cat_x),int(new_cat_y)), (int(zp_cat_x),int(zp_cat_y)), (255,255,255), 2)



            #cv2.line(show_img, (int(new_cat_x),int(new_cat_y)), (int(x),int(y)), (0,128,0), 1)
            cv2.line(show_img, (int(new_cat_x),int(new_cat_y)), (int(x),int(y)), (203,192,255), 1)

         # extra close stars that are not choosen
         #else:
         #   if img_x is not None:
         #      cv2.putText(show_img, "X",  (int(img_x),int(img_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
         #   cv2.line(show_img, (int(new_cat_x),int(new_cat_y)), (int(x),int(y)), (203,192,255), 1)
         cv2.imshow("calview", show_img)
         cv2.waitKey(30)
         pp += 1



   if SHOW == 1:
      cv2.waitKey(30)
   con.commit()


#   calib_info = get_calibration_file()

def insert_paired_star_full(cat_image_star, cal_fn, cal_params, mcp, json_conf):
   cal_params_nlm = cal_params.copy()
   cal_params_nlm['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   star_yn = -1
   star_pd = -1
   slope = -1
   zp_slope = -1
   res_deg = -1
   if True:
      star_obj = {}
      (name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = cat_image_star

      zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params_nlm,json_conf)
      zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, ra, dec)

      zp_res_px = calc_dist((img_x,img_y), (zp_cat_x,zp_cat_y))
      star_obj["cal_fn"] = cal_fn
      star_obj["name"]  = name
      star_obj["mag"] = mag
      star_obj["ra"]  = ra
      star_obj["dec"] = dec
      star_obj["new_cat_x"] = new_cat_x
      star_obj["new_cat_y"] = new_cat_y
      star_obj["zp_cat_x"]  = zp_cat_x
      star_obj["zp_cat_y"] = zp_cat_y
      star_obj["img_x"] = img_x
      star_obj["img_y"] = img_y
      star_obj["star_flux"] = star_flux
      star_obj["star_yn"]  = star_yn
      star_obj["star_pd"] = star_pd
      star_obj["star_found"] = 1
      if mcp is None:
         star_obj["lens_model_version"] = 1
      else:
         star_obj["lens_model_version"] = mcp['cal_version']
      star_obj["slope"] = slope
      star_obj["zp_slope"] = zp_slope
      star_obj["res_px"] = res_px
      star_obj["zp_res_px"] = zp_res_px
      star_obj["res_deg"] = res_deg
      insert_paired_star(cal_fn, star_obj, con, cur, json_conf )
   con.commit()

def insert_paired_star(cal_fn, star_obj, con, cur, json_conf):
   # Do an insert here into calfile_paired_stars table
   sql = """
               INSERT OR REPLACE INTO calfile_paired_stars (
                           cal_fn,
                           name,
                           mag,
                           ra,
                           dec,
                           new_cat_x,
                           new_cat_y,
                           zp_cat_x,
                           zp_cat_y,
                           img_x,
                           img_y,
                           star_flux,
                           star_yn,
                           star_pd,
                           star_found,
                           lens_model_version,
                           slope,
                           zp_slope,
                           res_px,
                           zp_res_px,
                           res_deg
                           )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
   """

   ivals = [star_obj["cal_fn"], star_obj["name"], star_obj["mag"], star_obj["ra"], star_obj["dec"], star_obj["new_cat_x"], star_obj["new_cat_y"], star_obj["zp_cat_x"], star_obj["zp_cat_y"], star_obj["img_x"], star_obj["img_y"], star_obj["star_flux"], star_obj["star_yn"], star_obj["star_pd"], 1, star_obj["lens_model_version"], star_obj["slope"], star_obj["zp_slope"], star_obj["res_px"], star_obj["zp_res_px"], star_obj["res_deg"]]

   if True:
      cur.execute(sql, ivals)
      #con.commit()
   #try:
   #except:
   #   print("record already exists.")

def check_calibration_file(cal_fn, con, cur):
   sql = "SELECT cal_fn FROM calibration_files where cal_fn = ?"
   uvals = [cal_fn]
   if cur is not None:
      cur.execute(sql, uvals)
      #print(sql, cal_fn)
      rows = cur.fetchall()
   else:
      rows = []
   if len(rows) > 0:
      return(True)
   else:
      return(False)

def quality_check_all_cal_files(cam_id, con, cur, cal_index=None):
   total_stars, avg_res = get_avg_res(cam_id, con, cur)
   print("AVG RES:", avg_res)
   calfiles_data  = load_cal_files(cam_id, con,cur)

   autocal_dir = "/mnt/ams2/cal/"
   mcp_file = autocal_dir + "multi_poly-" + json_conf['site']['ams_id'] + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)


   if cal_index is None:
      cal_index = load_json_file("/mnt/ams2/cal/freecal_index.json")

   last_cal_params = None
   above_avg_res = 0
   below_avg_res = 0
   above_avg_stars = 0
   below_avg_stars = 0
   trez = []
   
   for cal_file in cal_index:
      cdata = cal_index[cal_file]
      cfile = cal_file.split("/")[-1]
      trez.append(cdata['total_res_px']) 
      if cdata['cam_id'] == cam_id:
         print(cdata['total_stars'], cdata['total_res_px'], cfile)
         if cdata['total_res_px'] == 2:
            result = apply_calib (cfile, calfiles_data, json_conf, mcp, None, "", False, None)
         if cdata['total_res_px'] < avg_res:
            below_avg_res += 1 
         else:
            above_avg_res += 1 
         if cdata['total_stars'] < total_stars:
            below_avg_stars += 1 
         else:
            above_avg_stars += 1 

   print("DB Res: ",  avg_res)
   print("IDX Res: ", np.median(trez))
   print("Average Stars: ",  total_stars)
   print("Cal files above avg res: ", above_avg_res)
   print("Cal files below avg res: ", below_avg_res)
   print("Cal files above avg stars: ", above_avg_stars)
   print("Cal files below avg stars: ", below_avg_stars)
   print(total_stars, avg_res)


def find_stars_with_catalog(cal_fn, con, cur, json_conf,mcp=None, cp=None, cal_img=None):
   # for each star in the catalog check a crop around that location for an image star
   # if found add to user_stars and cat_image_stars
   # calc final res
   tb = pt()


   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)
   font = ImageFont.truetype("/usr/share/fonts/truetype/DejaVuSans.ttf", 20, encoding="unic" )
   if cp is None:
      cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf,None, None, mcp )
   else:
      cal_params = dict(cp)

   if cal_img is False:
      print("FAILED FIND")
      return()
   #help_img = make_help_img(cal_img)
   interval = .1
   cal_img = cv2.GaussianBlur(cal_img, (7, 7), 0)

   if "calparams" in cal_fn:
      cal_img_fn = cal_fn.replace("-calparams.json", ".png")
      cal_image_file = cal_fn.replace("-calparams.json", ".png")
   else:
      cal_img_fn = cal_fn.replace(".json", "-stacked.jpg")
      cal_image_file = cal_fn.replace(".json", "-stacked.jpg")

   # is this a meteor file or not!
   if "cal_params" in cal_fn:
      cal_dir = cal_dir_from_file(cal_image_file)
      cal_json_file = get_cal_json_file(cal_dir)
   else:
      date = cal_fn[0:10]
      cal_dir = "/mnt/ams2/meteors/" + date + "/"
      cal_json_file = cal_dir + cal_fn

   cal_json_fn = cal_json_file.split("/")[-1]
   if cal_img is not None:
      clean_cal_img = cal_img.copy()
   elif os.path.exists(cal_dir + cal_img_fn):
      clean_cal_img = cv2.imread(cal_dir + cal_img_fn)
   clean_cal_img = cv2.resize(clean_cal_img, (1920,1080))

   mask_file = "/mnt/ams2/meteor_archive/{}/CAL/MASKS/{}_mask.png".format(station_id, cam_id)
   if os.path.exists(mask_file) is True:
      mask = cv2.imread(mask_file)
      #mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
      mask = cv2.resize(mask, (1920,1080))
   else:
      mask = np.zeros((1080,1920),dtype=np.uint8)
   if len(mask.shape) == 3:
      mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
   if len(clean_cal_img.shape) == 3:
      clean_cal_img = cv2.cvtColor(clean_cal_img, cv2.COLOR_BGR2GRAY)


   clean_cal_img = cv2.subtract(clean_cal_img, mask)
   

   cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)

   good_stars = []
   star_objs = []
   bad_star_objs = []
   bad_count = 0
   for star in cat_stars[0:100]:
      name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y = star
      #if bad_count > 25:
      #   continue 

      mcx1 = int(new_cat_x - 25)
      mcx2 = int(new_cat_x + 25)
      mcy1 = int(new_cat_y - 25)
      mcy2 = int(new_cat_y + 25)
      if mcx1 < 0 or mcx2 > 1920 or mcy1 < 0 or mcy2 > 1080:
         continue
      crop_img = clean_cal_img[mcy1:mcy2,mcx1:mcx2]
      # 10x bigger
      show_img = clean_cal_img.copy()
      cv2.rectangle(show_img, (int(mcx1), int(mcy1)), (int(mcx2) , int(mcy2) ), (255, 255, 255), 1)

      ow = mcx2 - mcx1
      oh = mcy2 - mcy1
      crop_img_big = cv2.resize(crop_img, (ow * 10,oh * 10))


      star_obj = eval_star_crop(crop_img, cal_fn, mcx1, mcy1, mcx2, mcy2)


      show_image_pil = Image.fromarray(show_img)
      show_image_draw = ImageDraw.Draw(show_image_pil)

      crop_image_pil = Image.fromarray(crop_img_big)
      crop_image_draw = ImageDraw.Draw(crop_image_pil)
    
      crop_text = "Star: {} Mag: {} X/Y {}/{}".format(name, mag , str(int(new_cat_x)), str(int(new_cat_y)))
      crop_text2 = "YN: {} Flux: {}".format(str(int(star_obj['star_yn'])) + "%", str(int(star_obj['star_flux'])))
    
      crop_image_draw.text((20, 10), str(crop_text), font = font, fill="white")
      crop_image_draw.text((20, 475), str(crop_text2), font = font, fill="white")

      crop_img_big = np.asarray(crop_image_pil) 
      if len(crop_img_big.shape) == 3:
         crop_img_big = cv2.cvtColor(crop_image_pil, cv2.COLOR_RGB2BGR)


      if len(star_obj['cnts']) >= 1:


         cx1 = star_obj['cnts'][0][0] * 10
         cy1 = star_obj['cnts'][0][1] * 10
         cx2 = cx1 + (star_obj['cnts'][0][2] * 10)
         cy2 = cy1 + (star_obj['cnts'][0][3] * 10)

         ccx = int((cx1 + cx2) / 2)
         ccy = int((cy1 + cy2) / 2)

         six = mcx1 + (ccx/10)
         siy = mcy1 + (ccy/10)

         cv2.rectangle(crop_img_big, (int(cx1), int(cy1)), (int(cx2) , int(cy2) ), (0, 0, 255), 2)


         cv2.circle(show_img, (int(star_obj['star_x']),int(star_obj['star_y'])), 10, (255,255,255),1)

         cv2.circle(crop_img_big, (int(ccx),int(ccy )), star_obj['radius']* 10, (0,69,255),1)

         cv2.line(crop_img_big, (int(250),int(0)), (int(250),int(500)), (255,255,255), 1)
         cv2.line(crop_img_big, (int(0),int(250)), (int(500),int(250)), (255,255,255), 1)

         cv2.line(crop_img_big, (int(250),int(250)), (ccx,ccy), (255,255,255), 1)

      #if star_obj['valid_star'] is True:
      #   print("GOOD STAR", mag, star_obj)
      if star_obj['valid_star'] is False:
         
         cv2.circle(show_img, (int(star_obj['star_x']),int(star_obj['star_y'])), 10, (0,0,255),1)
         cv2.rectangle(crop_img_big, (int(0), int(0)), (int(499) , int(499) ), (0, 0, 255), 2)
         #print("BAD STAR", mag, star_obj)
         bad_count += 1


         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(star_obj['star_x'],star_obj['star_y'],cal_fn,cal_params,json_conf)
         match_dist = angularSeparation(ra,dec,img_ra,img_dec)
         cat_dist = calc_dist((star_obj['star_x'],star_obj['star_y']),(new_cat_x,new_cat_y))
         center_dist = calc_dist((960,540),(new_cat_x,new_cat_y))
         star_obj['star_name'] = name
         star_obj['mag'] = mag 
         star_obj['ra'] = ra
         star_obj['dec'] = dec
         star_obj['img_ra'] = img_ra
         star_obj['img_dec'] = img_dec
         star_obj['img_az'] = img_az
         star_obj['img_el'] = img_el
         star_obj['proj_x'] = new_x
         star_obj['proj_y'] = new_y
         star_obj['cat_x'] = new_cat_x
         star_obj['cat_y'] = new_cat_y
         
         star_obj['img_x'] = star_obj['star_x'] 
         star_obj['img_y'] = star_obj['star_y']
         star_obj['center_dist'] = int(center_dist)
         star_obj['total_res_deg'] = match_dist
         star_obj['total_res_px'] = cat_dist 

         bad_star_objs.append(star_obj)
      else:
         cv2.circle(show_img, (int(star_obj['star_x']),int(star_obj['star_y'])), 10, (0,255,0),1)
         cv2.rectangle(crop_img_big, (int(0), int(0)), (int(499) , int(499) ), (0, 255, 0), 2)
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_fn,cal_params,json_conf)

         match_dist = angularSeparation(ra,dec,img_ra,img_dec)
         cat_dist = calc_dist((six,siy),(new_cat_x,new_cat_y))
         center_dist = calc_dist((960,540),(new_cat_x,new_cat_y))
         good_stars.append(( name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_obj['star_flux'] ))
         star_obj['star_name'] = name
         star_obj['mag'] = mag 
         star_obj['ra'] = ra
         star_obj['dec'] = dec
         star_obj['img_ra'] = img_ra
         star_obj['img_dec'] = img_dec
         star_obj['img_az'] = img_az
         star_obj['img_el'] = img_el
         star_obj['proj_x'] = new_x
         star_obj['proj_y'] = new_y
         star_obj['cat_x'] = new_cat_x
         star_obj['cat_y'] = new_cat_y
         star_obj['img_x'] = six 
         star_obj['img_y'] = siy 
         star_obj['center_dist'] = int(center_dist)
         star_obj['total_res_deg'] = match_dist
         star_obj['total_res_px'] = cat_dist 
         star_objs.append(star_obj)


      if SHOW == 1:
         cv2.imshow('pepe_crop', crop_img_big)
         cv2.imshow('pepe', show_img)
         cv2.resizeWindow("pepe", 1920, 1080)
         cv2.waitKey(30)

   show_img = clean_cal_img.copy()

   print("MAG TABLE!")
   star_objs = sorted(star_objs, key=lambda x: x['mag'], reverse=False)
   new_star_objs = []
   all_res = []
   for so in  star_objs:
      all_res.append(so["total_res_px"]) 
      if so['star_name'] == "":
         name = "---"
      else:
         name = so['star_name']
   final_res = np.mean(all_res) 
   if final_res < 2:
      final_res = 2

   if final_res > 15:
      final_res = 15 
   if final_res < 2:
      final_res = 2 

   tb.field_names = ["Action", "Star", "Mag", "Intensity", "Res Limit", "Res Pixels", ]
   #tb.add(act, name, mag, star_flux, final_res, res_pixels)


   for so in  star_objs:
      #name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_flux = so
      if "star_flux" in so:
         star_flux = so['star_flux']
      if "res_pixels" in so:
         res_pixels = so['res_pixels']
      if "total_res_px" in so:
         res_pixels = so['total_res_px']

      if so["total_res_px"] <= final_res * 1.5:
         new_star_objs.append(so)
         act = "KEEP"
      else:
         act = "REJECT"
      tb.add_row([act, name, mag, star_flux, final_res, res_pixels])
   star_objs = new_star_objs  

   star_obj_report(star_objs)
   #for star in good_stars:
   #   name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_flux = star
   #   center_dist = int(calc_dist((960,540),(new_cat_x,new_cat_y)))

   if SHOW == 1:
      cv2.imshow('pepe', show_img)
      cv2.waitKey(30)



   return(star_objs, bad_star_objs)

def cal_params_report(cal_fn, cal_params,json_conf, show_img, waitVal=30, mcp=None):

   cal_params_nlm = cal_params.copy()
   cal_params_nlm['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   
   tb = pt()
   tb.field_names = ["Star","Magnitude", "Flux", "RA", "Dec", "Cat X", "Cat Y", "Img X", "Img Y", "Res PX", "Res Deg"]
   res_pxs = []
   res_degs = []
   zp_res_pxs = []
   zp_res_degs = []
   new_cat_image_stars = []
   center_res_pxs = []

   for star in cal_params['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
      new_cat_x, new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)

      # with the best lens model 
      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_fn,cal_params,json_conf)

      # with NO lens model 
      zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(six,siy,cal_fn,cal_params_nlm,json_conf)
      zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, ra, dec)

      cat_dist = calc_dist((six,siy),(new_cat_x,new_cat_y))
      match_dist = angularSeparation(ra,dec,img_ra,img_dec)

      zp_cat_dist = calc_dist((six,siy),(zp_x,zp_y))
      zp_match_dist = angularSeparation(ra,dec,zp_img_ra,zp_img_dec)


      res_pxs.append(cat_dist)
      res_degs.append(match_dist)

      zp_res_pxs.append(zp_cat_dist)
      zp_res_degs.append(zp_match_dist)
      center_dist = calc_dist((six,siy),(1920/2,1080/2))

      if center_dist < 600:
         center_res_pxs.append(cat_dist)


      # image star point (yellow)
      cv2.circle(show_img, (int(six),int(siy)), 3, ( 0, 234, 255),1)

      # Projected image star point 
      cv2.putText(show_img, "+",  (int(new_x-5),int(new_y+4)), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
      cv2.circle(show_img, (int(new_x),int(new_y)), 3, (255,69,255),1)

      # corrected catalog star point using lens model
      cv2.rectangle(show_img, (int(new_cat_x - 7), int(new_cat_y-7)), (int(new_cat_x+7) , int(new_cat_y+7) ), (255, 255, 255), 1)

      # zero poly catalog star point ( no lens model)

      cv2.rectangle(show_img, (int(zp_cat_x - 5), int(zp_cat_y-5)), (int(zp_cat_x+5) , int(zp_cat_y+5) ), (0, 0, 255), 1)

      tb.add_row([dcname, round(mag,2), int(bp), round(ra,2), round(dec,2), round(new_cat_x,2), round(new_cat_y,2), round(six,2), round(siy,2), round(cat_dist,2), round(match_dist,2)])
      new_cat_image_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp ))

   cv2.circle(show_img, (int(1920/2),int(1080/2)), 400, (128,128,128),1)
   cv2.circle(show_img, (int(1920/2),int(1080/2)), 800, (128,128,128),1)

   mean_center_res = np.mean(center_res_pxs)
   cal_params['mean_center_res'] = mean_center_res
   report_txt = str(tb)
   tb = pt()
   tb.field_names = ["Cal Paramater","Value"]
   # CENTER ??
   cal_params['total_res_px'] = mean_center_res
   #cal_params['total_res_px'] = np.mean(res_pxs)
   cal_params['total_res_deg'] = np.mean(res_degs)
   tb.add_row(["Center RA", cal_params['ra_center']] )
   tb.add_row(["Center Dec", cal_params['dec_center']])
   tb.add_row(["Center Az", cal_params['center_az']])
   tb.add_row(["Center El", cal_params['center_el']])
   tb.add_row(["Pixel Scale", cal_params['pixscale']])
   tb.add_row(["Residuals (Px)", cal_params['total_res_px']])
   tb.add_row(["Residuals (Deg)", cal_params['total_res_deg']])
   tb.add_row(["Residuals (Cnt PX)", cal_params['mean_center_res']])
   report_txt += str(tb)
   desc = "Stars: {} Res PX: {} Res Deg: {}".format(len(cal_params['cat_image_stars']), round(cal_params['total_res_px'],3), round(cal_params['total_res_deg'],3))
   cv2.putText(show_img, desc,  (int(10),int(1060)), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)

   cal_params['cat_image_stars'] = new_cat_image_stars
   #if SHOW == 1:
   #   cv2.imshow('pepe', show_img)
   #   cv2.waitKey(waitVal)

   return(cal_params, report_txt, show_img)


def star_obj_report(star_objs):
   #pip install prettytable
   tb = pt()
   tb.field_names = ["Star","Magnitude","Flux","Cen Dist", "Res Deg", "Res PX", "AI YN", "CRR"]

   star_objs = sorted(star_objs, key=lambda x: x['mag'], reverse=False)
   for so in  star_objs:
      if so['star_name'] == "":
         so['star_name'] = "---"
      center_res_ratio = round(so['total_res_px'] / so['center_dist'] , 2)
      tb.add_row([so['star_name'], so['mag'], round(so['star_flux'],2), so['center_dist'], round(so['total_res_deg'],3), round(so['total_res_px'],3), so['star_yn'], center_res_ratio])


def eval_star_crop(crop_img, cal_fn, x1, y1,x2,y2, star_cat_info=None ):

   star_obj = {}
   if crop_img.shape[0] == 0 or crop_img.shape[1] == 0:
      star_obj['valid_star'] = False
      return(star_obj)
   reject_reason = ""
   learn_dir = "/mnt/ams2/datasets/cal_stars/"
   if os.path.exists(learn_dir) is False:
      os.makedirs(learn_dir)
   roi_end = "_" + str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2)
   star_key= cal_fn.replace("-stacked-calparams.json", roi_end)

   star_img_file = learn_dir + star_key + ".jpg"
   star_data_file = learn_dir + star_key + ".json"

   if False:
      try:
         if os.path.exists(star_data_file) is True:
            data = load_json_file(star_data_file) 
            return(data)
      except:
         os.system("rm " + star_data_file)


   radius = 2
   star_flux = 0
   valid_star = True 
   if len(crop_img.shape) == 3:
      gray_img  = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
      gray_orig = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
   else:
      gray_img  = crop_img 
      gray_orig = crop_img 
   show_img = crop_img.copy()
   cx = 0
   cy = 0

   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_img)
   avg_val = np.mean(crop_img)
   if avg_val > 130:
      reject_reason = "AVG VAL TOO HIGH: " +  str(avg_val)
      valid_star = False
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_img)
   pxd = max_val - avg_val

   if pxd < 5:
      reject_reason = "PXD TOO LOW: " +  str(pxd)
      valid_star = False

   cch, ccw = crop_img.shape[:2]
   blval = gray_img[cch-1,0]
   brval = gray_img[cch-1,ccw-1]

   if blval == 0 or brval == 0:
      reject_reason += "too close to mask: " +  str(blval) + " " + str(brval)
      valid_star = False

   # check for cnt
   #thresh_val = max_val * .8

   thresh_val = find_best_thresh(gray_img)
   #if thresh_val < 80:
   #   thresh_val = 80
   if thresh_val < 20:
      reject_reason += "thresh_val_too_low: " +  str(thresh_val)
      valid_star = False 

   if thresh_val is None:
      thresh_val = 100
   _, crop_thresh = cv2.threshold(gray_img, thresh_val, 255, cv2.THRESH_BINARY)
   cnts = get_contours_in_image(crop_thresh)

   # lower sens if not found
   if len(cnts) == 0:
      thresh_val = max_val * .8

      _, crop_thresh = cv2.threshold(crop_img, thresh_val, 255, cv2.THRESH_BINARY)
      cnts = get_contours_in_image(crop_thresh)

   if pxd > 15:
      if len(cnts) == 0:
         cnts = [[mx,my,1,1]]

   if len(cnts) == 1:
      x,y,w,h = cnts[0]


      cx = x + (w/2)
      cy = y + (h/2)
      if w > h:
         radius = w 
      else:
         radius = h 

      # remove if not center # depends on crop size!!!
      #if x < 7 or x > 13:
      #   reject_reason += "x not center: " +  str(x) + " " + str(y)
      #   valid_star = False 
      #if y < 7 or y > 13:
      #   reject_reason += "y not center: " +  str(x) + " " + str(y)
      #   valid_star = False 

      if w > 3 or h > 3:
         reject_reason += "cnt w/h too big: " +  str(w) + " " + str(h)
         valid_star = False 
      star_flux = do_photo(gray_img, (cx,cy), radius)
      #try:
      #except:
      #   star_flux = 0
   #else:

   if star_flux > 0 and valid_star is True:
      # if you want AI write the file and call this
      #cv2.imwrite(star_img_file,crop_img)
      #star_yn = ai_check_star(crop_img, star_img_file)
      star_yn = -1
   else:
      star_yn = -1

   if pxd < 8 and (len(cnts) == 0):
      valid_star = False 
      reject_reason += "LOW PXD AND NO CNT"
   if pxd < 1 :
      valid_star = False 
      reject_reason += "LOW PXD "
   if star_flux <=  20:
      valid_star = False 
      reject_reason += "LOW FLUX " + str(star_flux)

   if radius < 1:
      radius = 1

   # return : cnts, star_flux, pxd, star_yn, radius
   star_obj = {}
   star_obj['cal_fn'] = cal_fn
   star_obj['star_x'] = x1 + cx
   star_obj['star_y'] = y1 + cy
   star_obj['x1'] = x1
   star_obj['y1'] = y1
   star_obj['x2'] = x2
   star_obj['y2'] = y2
   star_obj['cnts'] = cnts
   star_obj['star_flux'] = round(star_flux,2)
   star_obj['pxd'] = int(pxd)
   star_obj['brightest_point'] = [mx,my]
   star_obj['brightest_val'] = int(max_val)
   star_obj['bg_avg'] = int(avg_val)
   star_obj['star_yn'] = int(star_yn)
   star_obj['radius'] = radius
   star_obj['valid_star'] = valid_star
   star_obj['reject_reason'] = reject_reason
   star_obj['thresh_val'] = thresh_val
   star_obj['cx'] = cx 
   star_obj['cy'] = cy
   if star_cat_info is not None:
      name, mag, ra,dec,new_cat_x,new_cat_y = star_cat_info
      star_obj['name'] = name
      star_obj['mag'] = mag 
      star_obj['ra'] = ra
      star_obj['dec'] = dec
      star_obj['cat_x'] = new_cat_x
      star_obj['cat_y'] = new_cat_y
      star_obj['res_px'] = calc_dist((new_cat_x, new_cat_y), (star_obj['star_x'], star_obj['star_y']))

   else:
      star_obj['x'] = star_obj['star_x']
      star_obj['y'] = star_obj['star_y']

   #print(star_obj)
   #if SHOW == 1:
   #   cv2.imshow("CROP", crop_thresh)
   #   cv2.waitKey(30)

   return ( star_obj)

def find_best_thresh(gray_img):

   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_img)
   avg_val = np.mean(gray_img)
   pxd = max_val - avg_val

   for i in range(0,5):
      fact = (i + 1 * 2) / 100
      thresh_val = max_val * (1-fact) 
      if pxd < 5:
         return(thresh_val)

      _, crop_thresh = cv2.threshold(gray_img, thresh_val, 255, cv2.THRESH_BINARY)
      cnts = get_contours_in_image(crop_thresh)
      if len(cnts) == 1:
         x,y,w,h = cnts[0]
         if w != gray_img.shape[1] and h != gray_img.shape[0]:
            return(thresh_val)

   thresh_val = max_val * .8
   return(thresh_val)

def find_close_stars(star_obj):
   cal_fn = star_obj['cal_fn']
   x = star_obj['x']
   y = star_obj['y']
   star_flux = star_obj['star_flux']
   sql = """
      SELECT cal_fn, name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, 
             img_x, img_y, star_flux, star_yn, star_pd, star_found, lens_model_version 
        FROM calfile_catalog_stars
       WHERE cal_fn = ?
         AND (new_cat_x > ? and new_cat_x < ?)
         AND (new_cat_y > ? and new_cat_y < ?)
   """
   center_dist = calc_dist((x,y),(1920/2,1080/2))
   if center_dist < 800:
      x1 = x - 50
      x2 = x + 50
      y1 = y - 50
      y2 = y + 50
   else:
      x1 = x - 75 
      x2 = x + 75
      y1 = y - 75
      y2 = y + 75

   # Adjust search box based on where the img star is
   # right side image, cat must be greater than source!
   if x > 1620:
      x1 = x 
      x2 = x1 + 70 
   # left side image, cat must be greater than source!
   if x < 300:
      x2 = x 
      x1 = x2 - 70 

   ivals = [cal_fn, x1, x2, y1, y2]
   cur.execute(sql, ivals)
   rows = cur.fetchall()
   stars = []

   for row in rows:
      cal_fn, name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, \
         img_x, img_y, cat_star_flux, star_yn, star_pd, star_found, lens_model_version  = row
      img_x = star_obj['x']
      img_y = star_obj['y']
      y = img_y
      x = img_x
      cat_star_flux = star_obj['star_flux']
      slope = (y - new_cat_y) / (x - new_cat_x)
      zp_slope = (y - zp_cat_y) / (x - zp_cat_x)
      dist = calc_dist((x,y),(new_cat_x,new_cat_y))
      zp_dist = calc_dist((x,y),(zp_cat_x,zp_cat_y))


      valid = True

      if center_dist > 700:
         if x < 600 and y < 400: # top left corner
            if new_cat_x > x:
               valid = False
            if new_cat_y > y:
               valid = False
         if x < 600 and y > 1080 - 400: # bottom left corner
            if new_cat_x > x:
               valid = False
            if new_cat_y < y:
               valid = False
         if x > 1920 - 600 and y < 400: # top right corner
            if new_cat_x < x:
               valid = False
            if new_cat_y > y:
               valid = False
         if x > 1920 - 600 and y > 1080- 400: # bottom right corner
            if new_cat_x < x:
               valid = False
            if new_cat_y < y:
               valid = False
         
         # y_dist should not be more than x_dist on edge
         y_dist = abs(new_cat_y - y)
         x_dist = abs(new_cat_x - x)
         if y_dist > x_dist:
            valid = False

      if star_flux is None:
         valid = False
      elif star_flux > 1000 and mag >= 4:
         valid = False
      if center_dist < 600:
         if zp_dist > 25:
            valid = False 
      valid = True
      if valid is True:
         stars.append(( cal_fn, name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, \
            img_x, img_y, star_flux, star_yn, star_pd, star_found, lens_model_version, \
            slope, zp_slope, dist, zp_dist))

   stars = sorted(stars, key=lambda x: x[-2], reverse=False)
   for star in stars:
      cal_fn, name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, img_x, img_y, star_flux, star_yn, star_pd, star_found, lens_model_version, slope, zp_slope, dist, zp_dist = star
   return(stars)

#def cal_main(cal_file):
#   print("Menu")

   # GET IMAGE STARS IS DONE. 

   # GET CATALOG STARS
def get_default_cal_for_file(cam_id, obs_file, img, con, cur, json_conf):

   sql = """
       SELECT substr(cal_fn, 0,11), az, el, position_angle,pixel_scale, res_px 
        FROM calibration_files
       WHERE cal_fn like ?
         AND cal_fn like ?
   """

   year_month = obs_file[0:7] 
   ivals = [year_month + "%", "%" + cam_id + "%"]

   #print(sql, ivals)
   cur.execute(sql, ivals)
   rows = cur.fetchall()

   if len(rows) == 0:
      print("this method will not work. need to revert back to the range file", obs_file)
      try:
         default_cp = get_default_cal_for_file_with_range (cam_id, obs_file, None, con, cur, json_conf)
      except:
         print("DEFAULT CAL FAILED! -- there is no default cal for this camera!")
         return()

      return(default_cp)
   else:
      print("ROWS:", len(rows))

   #exit()

   best = []
   best_dict = {}
   dates = []
   azs = []
   els = []
   poss = []
   pxs = []
   ress = []

   best_dates = []
   best_azs = []
   best_els = []
   best_poss = []
   best_pxs = []
   best_ress = []

   for row in rows:
      print("ROW:", row)
      date, az, el, pos, px, res = row 
      if az != None:
         dates.append(date)
         azs.append(az)
         els.append(el)
         poss.append(pos)
         pxs.append(px)
      if res is not None:
         ress.append(res)

   if len(azs) == 0:
      return()
   print(azs)
   med_az = np.median(azs)
   med_el = np.median(els)
   med_pos = np.median(poss)
   med_pxs = np.median(pxs)

   print(ress)
   med_res = np.median(ress)


   for row in rows:
     
      date, az, el, pos, px, res = row 
      if res is None:
         continue
      print(med_res * 1.2, row)

      if res <= med_res * 1.2:
         best_dates.append(date)
         best_azs.append(az)
         best_els.append(el)
         best_poss.append(pos)
         best_pxs.append(pxs)
         best_ress.append(res)

   best_med_az = np.median(best_azs)
   best_med_el = np.median(best_els)
   best_med_pos = np.median(best_poss)
   best_med_pxs = np.median(best_pxs)
   best_med_res = np.median(best_ress)

   print("MED/BEST")
   print(med_az, best_med_az)
   print(med_el, best_med_el)
   print(med_pos, best_med_pos)
   print(med_pxs, best_med_pxs)
   print(med_res, best_med_res)

   autocal_dir = "/mnt/ams2/cal/"
   mcp_file = autocal_dir + "multi_poly-" + json_conf['site']['ams_id'] + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
   else:
      mcp = {} 
      mcp['x_poly'] = np.zeros(shape=(15,), dtype=np.float64).tolist()
      mcp['y_poly'] = np.zeros(shape=(15,), dtype=np.float64).tolist()
      mcp['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64).tolist()
      mcp['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64).tolist()


   mcp['center_az'] = best_med_az
   mcp['center_el'] = best_med_el
   mcp['position_angle'] = best_med_pos
   mcp['pixscale'] = best_med_pxs
   mcp['cat_image_stars'] = []
   mcp['user_stars'] = []
   mcp = update_center_radec(obs_file,mcp,json_conf)
   mcp['total_res_px'] = 0 
   mcp['total_res_deg'] = 0


   #exit()
   return(mcp)

def get_default_cal_for_file_with_range(cam_id, obs_file, img, con, cur, json_conf):
   # use this function to get a default cal when no stars or info 
   # is present

   autocal_dir = "/mnt/ams2/cal/"
   mcp_file = autocal_dir + "multi_poly-" + json_conf['site']['ams_id'] + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
   else:
      mcp = {} 
      mcp['x_poly'] = np.zeros(shape=(15,), dtype=np.float64).tolist()
      mcp['y_poly'] = np.zeros(shape=(15,), dtype=np.float64).tolist()
      mcp['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64).tolist()
      mcp['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64).tolist()

   try:
      range_data = get_cal_range(obs_file, img, con, cur, json_conf)
   except:
      print("No range data! for camera.")
      return(None)

   ( rcam_id, rend_dt, rstart_dt, elp, az, el, pos, pxs, res) = range_data[0]

   if mcp is None:
      mcp = {}
   if mcp is not None:
      mcp['center_az'] = az
      mcp['center_el'] = el
      mcp['position_angle'] = pos
      mcp['pixscale'] = pxs 
      mcp['user_stars'] = []
      mcp['cat_image_stars'] = []
      mcp = update_center_radec(obs_file,mcp,json_conf)
      mcp['total_res_px'] = 999
      mcp['total_res_deg'] = 999

   return(mcp)

def get_cal_range(obs_file, img, con, cur, json_conf):

   #show_img = img.copy()

   (cal_date, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(obs_file)
   station_id = json_conf['site']['ams_id']
   lens_model_file = "/mnt/ams2/cal/multi_poly-" + json_conf['site']['ams_id'] + "-" + cam_id + ".info"
   if os.path.exists(lens_model_file) is True:
      lens_model = load_json_file(lens_model_file)
   else:
       lens_model = {}
   cal_range = load_json_file("/mnt/ams2/cal/" + json_conf['site']['ams_id'] + "_cal_range.json")
 
   #print("OBS FILE:", obs_file)
   #img = cv2.imread(obs_file.replace(".mp4", "-stacked.jpg"))

   #star_points,stars_image = get_star_points(obs_file, img, {}, station_id, cam_id, {})


   match_range_data = []
   for row in cal_range:
      rcam_id, rend_date, rstart_date, az, el, pos, pxs, res = row
      if np.isnan(az) is True:
         print("NAN SKIP")
         continue

      rcam_id = row[0]
      rend_date = row[1]
      rstart_date = row[2]

      rend_dt = datetime.datetime.strptime(rend_date, "%Y_%m_%d")
      rstart_dt = datetime.datetime.strptime(rstart_date, "%Y_%m_%d")

      if rcam_id == cam_id and np.isnan(az) == False:
         elp = abs((cal_date - rend_dt).total_seconds()) / 86400
         match_range_data.append(( rcam_id, rend_dt, rstart_dt, elp, az, el, pos, pxs, res))

   return(match_range_data)



def get_best_cal_files(cam_id, con, cur, json_conf, limit=500):
   avg_stars, avg_res = get_avg_res(cam_id, con, cur)

   sql = """
        SELECT 
            cal_fn, 
            count(*) AS ss, 
            avg(res_px) as rs, 
            count(*) / avg(res_px) as score
        FROM 
            calfile_paired_stars
        WHERE 
            cal_fn LIKE ? AND 
            res_px IS NOT NULL AND 
            res_px < ?
        GROUP BY 
            cal_fn
        HAVING 
            count(*) > 20
        ORDER BY 
            score
            LIMIT ? 
   """
   dvals = ["%" + cam_id + "%", avg_res, limit]
   cur.execute(sql, dvals)
   rows = cur.fetchall()
   best = []
   best_dict = {}
   for row in rows:
      x_cal_fn, total_stars, avg_res,score = row
      best.append((x_cal_fn, total_stars, avg_res,score ))
      best_dict[x_cal_fn] = [x_cal_fn,total_stars,avg_res,score]
   return(best, best_dict)

def fast_lens(cam_id, con, cur, json_conf,limit=5, cal_fns=None):
   fast_img = np.zeros((1080,1920,3),dtype=np.uint8)
   station_id = json_conf['site']['ams_id']
   mcp_file = "/mnt/ams2/cal/multi_poly-" + json_conf['site']['ams_id'] + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
      mcp['cal_version'] += 1
      if "x_fun" in mcp:
         if mcp["x_fun"] > 5:
            mcp = None
            print("Current lens model is bad and should be reset!")
            #exit()
   else:
      mcp = None

   # get mask
   mask_file = "/mnt/ams2/meteor_archive/{}/CAL/MASKS/{}_mask.png".format(station_id, cam_id)
   if os.path.exists(mask_file) is True:
      mask_img = cv2.imread(mask_file)
      mask_img = cv2.resize(mask_img, (1920,1080))
   else:
      mask_img = np.zeros((1080,1920,3),dtype=np.uint8)

      # add more stars


   calfiles_data = load_cal_files(cam_id, con, cur)
   best, best_dict =  get_best_cal_files(cam_id, con, cur, json_conf, limit=500)
   merged_stars = []
   best_index = {}
   best_cals = {}


   # apply latest calib to our best files
   for row in best[0:limit]:
      cal_fn = row[0]
      print(cal_fn)
      result = apply_calib (cal_fn, calfiles_data, json_conf, mcp, None, "", False, None)

   # main loop of files
   for bc in best[0:limit]:
      cal_fn = bc[0]
      resp = start_calib(cal_fn, json_conf, calfiles_data, mcp)
      if resp is not False and resp is not None:
         (station_id, cal_dir, cal_json_file, cal_img_file, cal_params, cal_img, clean_cal_img, mask_file,mcp) = resp
         cal_img = cv2.subtract(cal_img, mask_img)
      else:
         continue 

      cal_params = update_center_radec(cal_img_file,cal_params,json_conf)
      cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)


      cat_image_stars = cat_star_match(cal_fn, cal_params, cal_img, cat_stars)
      stars,xxx_cat_stars = get_paired_stars(cal_fn, cal_params, con, cur)

      cal_params['cat_image_stars'] = cat_image_stars
      print("CAT STARS 1:", len(cal_params['cat_image_stars']))
      cal_params['cat_image_stars'] = remove_bad_stars(cal_params['cat_image_stars'])
      print("CAT STARS 2:", len(cal_params['cat_image_stars']))

      cal_params['cat_image_stars'], bad_stars = remove_mask_stars(cal_params['cat_image_stars'], cal_img)
      print("CAT STARS 3:", len(cal_params['cat_image_stars']))


      cal_params = add_more_stars(cal_fn, cal_params, cal_img, cal_img, json_conf)
      print("XP", cal_params['x_poly'])

      print("CAT STARS 4:", len(cal_params['cat_image_stars']))

      #cal_params, xxx_cat_image_stars = recenter_fov(cal_fn, cal_params, cal_img.copy(),  stars, json_conf, "", None, cal_img, con, cur)

      extra_text = "Fast lens : after re-center fov"
      star_img = draw_star_image(cal_img, cal_params['cat_image_stars'],cal_params, json_conf, extra_text)
      cv2.imwrite("/mnt/ams2/last.jpg", star_img)

      ocps = cal_params['cat_image_stars'] 
     
      if cal_params['total_res_px'] >= 5:
         cal_params['cat_image_stars'] = remove_bad_stars(cal_params['cat_image_stars'])
         if len(cal_params['cat_image_stars']) < 5:
            cal_params['cat_image_stars'] = ocps
         if len(cal_params['cat_image_stars']) > 10:
            print("\tRECENTER AGAIN.", len(cal_params['cat_image_stars']), cal_params['total_res_px'] )
            cal_params, xxx_cat_image_stars = recenter_fov(cal_fn, cal_params, cal_img.copy(),  stars, json_conf, "", None, cal_img, con, cur)
            #cat_image_stars = cat_star_match(cal_fn, cal_params, cal_img, cat_stars)
            #cal_params['cat_image_stars'] = cat_image_stars 
         else:
            continue

      rez = [row[-2] for row in merged_stars] 
      best_index[cal_fn] = rez
      best_cals[cal_fn] = cal_params 
      update_calibration_file(cal_fn, cal_params, con,cur,json_conf,mcp)
      save_json_file(cal_json_file, cal_params)


   rez = []
   for cal_fn in best_index:
      rez.append(best_index[cal_fn])
   med_rez = np.median(rez)

   long_stars = []
   for cal_fn in best_index:
      if best_index[cal_fn]  > med_rez:
         #print("skip ", cal_fn, med_rez, best_index[cal_fn])
         continue
      cat_image_stars = best_cals[cal_fn]['cat_image_stars']
      cal_params = best_cals[cal_fn]
      for star in cat_image_stars:
         (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = star
         center_dist = calc_dist((img_x,img_y),(1920/2,1080/2))
         if center_dist > 600:
            long_stars.append(star)
         merged_stars.append((cal_fn, cal_params['center_az'], cal_params['center_el'], cal_params['ra_center'], cal_params['dec_center'], cal_params['position_angle'], cal_params['pixscale'], dcname,mag,ra,dec,ra,dec,match_dist,new_x,new_y,cal_params['center_az'],cal_params['center_el'],new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux))

   rez = [row[-2] for row in merged_stars] 
   long_rez = [row[-2] for row in long_stars] 
   if len(long_rez) > 1:
      long_rez = [row[-2] for row in long_stars] 
   else:
      long_rez = 50

   norm_med_rez_limit = np.median(rez) * 3
   long_med_rez_limit = np.median(long_rez) * 2
   for star in merged_stars:
      cal_fn, center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,ra,dec,match_dist,new_x,new_y,center_az,center_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux = star
      res_px2 = calc_dist((new_x,new_y),(new_cat_x,new_cat_y))
      col1,col2 = collinear(img_x,img_y,new_x,new_y,new_cat_x,new_cat_y)
      if res_px2 < res_px:
         res_px = res_px2
      
      center_dist = calc_dist((img_x,img_y),(1920/2,1080/2))
      if center_dist > 600:
         med_rez_limit = norm_med_rez_limit
      else:
         med_rez_limit = long_med_rez_limit
     

      res_col = abs(col1 - col2)
      desc = str(int(res_col))
      if res_px < med_rez_limit * 2:
         good = True
         print("KEEP", med_rez_limit, dcname, mag, star_flux, res_px)
         color = [0,255,0]
      else:
         good = False 
         color = [128,128,255]
         print("REJECT", med_rez_limit, dcname, mag, star_flux, res_px)
      # turn rejects off
      good = True
 

      if res_col < 300 and good is True:
         cv2.putText(fast_img, desc ,  (int(new_x),int(new_y)), cv2.FONT_HERSHEY_SIMPLEX, .6, color, 1)
         cv2.line(fast_img, (int(new_x),int(new_y)), (int(img_x),int(img_y)), [255,255,255], 1)
         cv2.line(fast_img, (int(new_cat_x),int(new_cat_y)), (int(img_x),int(img_y)), color, 1)
         cv2.rectangle(fast_img, (int(new_cat_x-5), int(new_cat_y-5)), (int(new_cat_x+5) , int(new_cat_y+5) ), color, 1)
         cv2.rectangle(fast_img, (int(new_x-5), int(new_y-5)), (int(new_x+5) , int(new_y+5) ), (128,128,128), 1)
         cv2.circle(fast_img, (int(img_x),int(img_y)), 5, (255,255,255),1)
      #if SHOW == 1:
         #cv2.imshow('pepe', fast_img)
         #print("FAST IMAGE")
         #cv2.waitKey(30)

   save_json_file("/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json", merged_stars)
   cv2.imwrite('/mnt/ams2/fast_img.jpg', fast_img)
   print('saved /mnt/ams2/fast_img.jpg' )

   if SHOW == 1:
      print("DONE Showing fast_img")
      cv2.imshow('pepe', fast_img)
      cv2.waitKey(30)


def characterize_best(cam_id, con, cur, json_conf,limit=50, cal_fns=None):
   # choose best star pairs to use in the lens model

   my_limit = limit
   limit = 50 
   calfiles_data  = load_cal_files(cam_id, con,cur)
   if cal_fns is None:
      cal_fns = list(calfiles_data.keys())[0:limit]

   autocal_dir = "/mnt/ams2/cal/"
   all_stars_image_file = autocal_dir + "plots/" + json_conf['site']['ams_id'] + "_" + cam_id + "_ALL_STARS.jpg"
   mcp_file = autocal_dir + "multi_poly-" + json_conf['site']['ams_id'] + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
      mcp['cal_version'] += 1
   else:
      mcp = None


   station_id = json_conf['site']['ams_id']
   all_cal_files, best_dict = get_best_cal_files(cam_id, con, cur, json_conf)

   # determine current avg res

   sql = """
      SELECT cal_fn, count(*) AS ss, avg(res_px) as rs 
        FROM calfile_paired_stars 
       WHERE cal_fn like ?
         AND res_px IS NOT NULL
    GROUP BY cal_fn 
    ORDER BY rs
    LIMIT {}
   """.format(limit)
   dvals = ["%" + cam_id + "%"]
   cur.execute(sql, dvals)
   rows = cur.fetchall()

   if len(rows) == 0:
      print("FAILED no rows")
      exit()

   updated_stars = []
   updated_stars_zp = []

   res_0 = []
   res_200 = []
   res_400 = []
   res_600 = []
   res_800 = []
   res_900 = []
   res_1000 = []

   nres_0 = []
   nres_200 = []
   nres_400 = []
   nres_600 = []
   nres_800 = []
   nres_900 = []
   nres_1000 = []

   
   #for cal_fn in best_dict:
   #if cal_fns is not None:
   #   rows = cal_fns
   good = 0
   bad = 0

   # determine res at different differences
   # this is hot db way
   #for row in rows:
   #   if row[2] is None:
   #      continue
   #   cal_fn = row[0]

   # this is the 'review way'
   for cal_fn in cal_fns:
      # need this block for the review way!
      if True:
         # OLD / SLOW / NOT NEEDED
         resp = start_calib(cal_fn, json_conf, calfiles_data, mcp)
         if resp is not False and resp is not None:
            (station_id, cal_dir, cal_json_file, cal_img_file, cal_params, cal_img, clean_cal_img, mask_file,mcp) = resp
         else:
            continue 
      # better way to do this
      if cal_fn in calfiles_data:
         cal_data = calfiles_data[cal_fn]
         #cal_params = cal_data_to_cal_params(cal_fn, cal_data,json_conf, mcp)
         try:
            cal_params = load_json_file(cal_dir + cal_fn)
         except:
            print("bad cal file!", cal_dir + cal_fn)
            if os.path.exists("/mnt/ams2/cal/bad_cals/") is False:
               os.makedirs("/mnt/ams2/cal/bad_cals/")
            cmd = "mv " + cal_dir + " /mnt/ams2/cal/bad_cals/" 
            #print(cmd)
            os.system(cmd)
            # bad cal file!



      stars,cat_stars = get_paired_stars(cal_fn, cal_params, con, cur)

      # no lens model cal
      cal_params_nlm = cal_params.copy()
      cal_params_nlm['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)


      for star in cat_stars:
         (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = star
         new_cat_x, new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params,json_conf)

         zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, ra, dec)
         zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params_nlm,json_conf)

         match_dist = angularSeparation(ra,dec,img_ra,img_dec)
         res_px = calc_dist((img_x,img_y),(new_cat_x,new_cat_y))

         zp_match_dist = angularSeparation(ra,dec,img_ra,img_dec)
         zp_res_px = calc_dist((img_x,img_y),(zp_cat_x,zp_cat_y))

         zp_center_dist = calc_dist((1920/2,1080/2),(zp_cat_x,zp_cat_y))
         #print(dcname, mag, zp_center_dist, res_px)
         # determine the zp / no lens model dist median avg for characterization
         if zp_center_dist < 200:
            res_0.append(zp_res_px)
         if 200 <= zp_center_dist < 400:
            res_200.append(zp_res_px)
         if 400 <= zp_center_dist < 600:
            res_400.append(zp_res_px)
         if 600 <= zp_center_dist < 800:
            res_600.append(zp_res_px)
         if 800 <= zp_center_dist < 900:
            res_800.append(zp_res_px)
         if 900 <= zp_center_dist < 1000:
            res_900.append(zp_res_px)
         if zp_center_dist >= 1000:
            res_1000.append(zp_res_px)

         updated_stars.append((cal_fn,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux))
         updated_stars_zp.append((cal_fn,dcname,mag,ra,dec,zp_img_ra,zp_img_dec,zp_match_dist,zp_x,zp_y,zp_img_az,zp_img_el,zp_cat_x,zp_cat_y,img_x,img_y,zp_res_px,star_flux))

   tb = pt()

   print("AllSkyOS: ", station_id + "-" + cam_id)
   print("NON CORRECTED CATALOG TO IMAGE STAR DISTANCE BY FOV ZONE")

   tb.field_names = ["Dist from Center", "Catalog / Image Pixel Distance"]

   tb.add_row(["0-200", np.median(res_0)])
   tb.add_row(["200-400", np.median(res_200)])
   tb.add_row(["400-600", np.median(res_400)])
   tb.add_row(["600-800", np.median(res_600)])
   tb.add_row(["800-900", np.median(res_800)])
   tb.add_row(["900-1000", np.median(res_900)])
   tb.add_row(["1000+", np.median(res_1000)])

   print(tb)
   try:
      base_image = clean_cal_img.copy()
   except:
      base_image = np.zeros((1080,1920,3),dtype=np.uint8)

   if False:
      cv2.circle(base_image, (int(1920/2),int(1080/2)), 200, (128,128,128),1)
      cv2.circle(base_image, (int(1920/2),int(1080/2)), 400, (128,128,128),1)
      cv2.circle(base_image, (int(1920/2),int(1080/2)), 600, (128,128,128),1)
      cv2.circle(base_image, (int(1920/2),int(1080/2)), 800, (128,128,128),1)
      cv2.circle(base_image, (int(1920/2),int(1080/2)), 900, (128,128,128),1)
      cv2.circle(base_image, (int(1920/2),int(1080/2)), 1000, (128,128,128),1)

      cv2.putText(base_image, str(int(np.median(res_0))),  (960,540), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
      cv2.putText(base_image, str(int(np.median(res_200))),  (720,400), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
      cv2.putText(base_image, str(int(np.median(res_400))),  (550,300), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
      cv2.putText(base_image, str(int(np.median(res_600))),  (350,195), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
      cv2.putText(base_image, str(int(np.median(res_800))),  (200,115), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
      cv2.putText(base_image, str(int(np.median(res_900))),  (125,60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
      cv2.putText(base_image, str(int(np.median(res_1000))),  (55,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)

      cv2.line(base_image, (int(0),int(0)), (int(1920/2),int(1080/2)), [255,255,255], 1)

   # select the best stars based on the dist/res
   best_stars = []
   not_best_stars = []

   ic = 0
   for star in updated_stars_zp:
      (cal_fn,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,zp_cat_x,zp_cat_y,img_x,img_y,res_px,star_flux) = star
      if True:
         zp_center_dist = calc_dist((1920/2,1080/2),(zp_cat_x,zp_cat_y))
         if zp_center_dist < 200:
            limit = np.median(res_0)
         if 200 <= zp_center_dist < 400:
            limit = np.median(res_200)
         if 400 <= zp_center_dist < 600:
            limit = np.median(res_400)
         if 600 <= zp_center_dist < 800:
            limit = np.median(res_600)
         if 800 <= zp_center_dist < 900:
            limit = np.median(res_800)
         if 900 <= zp_center_dist < 1000:
            limit = np.median(res_900)
         if zp_center_dist >= 1000 :
            limit = np.median(res_1000)

      
      fact = abs(res_px / limit)
      if .7 <= fact <= 1.3:
         good += 1
      else:
         bad += 1
      if star_flux is None:
         star_flux = 0
      if mag > 4 and star_flux > 500:
      #   print("MAG FAIL!", mag, star_flux)
         fact += 10
      #print("FACT", fact , res_px, mag, star_flux)
      if .25 <= fact <= 1.8 :
         #cv2.line(base_image, (int(zp_cat_x),int(zp_cat_y)), (int(img_x),int(img_y)), (0,255,0), 2)
         (cal_fn,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = updated_stars[ic]

         res_px = calc_dist((img_x,img_y),(new_cat_x,new_cat_y))


         best_stars.append((cal_fn,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,zp_cat_x,zp_cat_y,img_x,img_y,res_px,star_flux)) 

         cv2.line(base_image, (int(new_cat_x),int(new_cat_y)), (int(img_x),int(img_y)), (0,255,0), 2)
      else:
         (cal_fn,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = updated_stars[ic]
         cv2.line(base_image, (int(new_cat_x),int(new_cat_y)), (int(img_x),int(img_y)), (0,0,255), 2)
         not_best_stars.append((cal_fn,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,zp_cat_x,zp_cat_y,img_x,img_y,res_px,star_flux)) 

      ic += 1

   if SHOW == 1 :
      cv2.imshow('pepe', base_image)
      cv2.waitKey(30)
   cv2.imwrite(all_stars_image_file, base_image)


   merged_stars = []
   rez = [row[-2] for row in best_stars] 
   med_rez = np.median(rez) * 1.2

   if med_rez < 2:
      med_rez = 2
   # only keep the best stars

   for star in best_stars:

      (cal_fn, name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = star

      if cal_fn in calfiles_data:
         #(cal_fn_ex, center_az,center_el, ra_center,dec_center, position_angle, pixscale) = calfiles_data[cal_fn]
         (station_id, camera_id, cal_fn, cal_ts, center_az, center_el, ra_center, dec_center, position_angle,\
            pixscale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
            y_poly, x_poly_fwd, y_poly_fwd, a_res_px, a_res_deg, ai_weather, ai_weather_conf, cal_version, last_update) = calfiles_data[cal_fn]


      match_dist = 9999
      center_dist = calc_dist((img_x, img_y),(1920/2,1080/2))   
      factor = 2 
      if center_dist > 600:
         factor = 2 
      if center_dist > 700:
         factor = 3 
      if center_dist > 800:
         factor = 4 
      if center_dist > 900:
         factor = 5 
      if res_px < med_rez * factor: 
         merged_stars.append((cal_fn, center_az, center_el, ra_center, dec_center, position_angle, pixscale, name,mag,ra,dec,ra,dec,match_dist,new_x,new_y,center_az,center_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux))

   # select grid stars when we have more than 400
   # this distributes out the stars across the fov 

   if len(merged_stars) > 400:
      grid = make_grid_stars(merged_stars, mcp , factor = 2, gsize=50, limit=10)
      best_stars = []
      for grid_key in grid:
         just_data = sorted(grid[grid_key], key=lambda x: x[-2], reverse=False)
         rc = 0
         if len(just_data ) > 0:
            for row in just_data:
               if rc < 5:
                  best_stars.append(row)
               else:
                  break 
               rc += 1
   else:
      best_stars = merged_stars

   # now we have our best stars to use for the model!
   base_image_good_stars = np.zeros((1080,1920,3),dtype=np.uint8)
   print("BEST STARS:", len(best_stars))
   for star in best_stars:

      (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, name,mag,ra,dec,ra,dec,match_dist,new_x,new_y,center_az,center_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = star
      #(cal_fn, name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = star
      cv2.line(base_image, (int(new_x),int(new_y)), (int(img_x),int(img_y)), (255,255,255), 2)
      cv2.line(base_image_good_stars, (int(new_x),int(new_y)), (int(img_x),int(img_y)), (255,255,255), 2)

   if SHOW == 1 :
      cv2.imshow('pepe', base_image)
      cv2.waitKey(30)

      cv2.imshow('pepe', base_image_good_stars)
      cv2.waitKey(30)


   save_json_file("/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json", merged_stars)
   save_json_file("/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json", best_stars)
   #print("\tSAVED STARS FOR MODEL! /mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json", len(best_stars), "stars")
   if len(best_stars) < 10:
      print("LESS THAN 10 stars IN MODEL ABORT!", len(not_best_stars))
      best_stars = not_best_stars
      return()
      #exit()


def plot_star_chart(base_image, cat_stars, zp_cat_stars):
   for star in zp_cat_stars:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = star

      cv2.circle(base_image, (int(img_x),int(img_y)), 4, (135,247,252),1) # yellow

      cv2.circle(base_image, (int(new_x),int(new_y)), 4, (0,0,200),1)
      #cv2.circle(base_image, (int(new_cat_x),int(new_cat_y)), 4, (0,255,255),1)

      x1 = new_cat_x - 4 
      x2 = new_cat_x + 4 
      y1 = new_cat_y - 4 
      y2 = new_cat_y + 4 
      cv2.rectangle(base_image, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 0, 200), 1)


   for star in cat_stars:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = star
      cv2.circle(base_image, (int(new_x),int(new_y)), 3, (0,68,255),1)
      #cv2.circle(base_image, (int(new_cat_x),int(new_cat_y)), 3, (0,0,255),1)

      x1 = new_cat_x - 5
      x2 = new_cat_x + 5
      y1 = new_cat_y - 5
      y2 = new_cat_y + 5
      cv2.rectangle(base_image, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1)


   cv2.circle(base_image, (int(1920/2),int(1080/2)), 200, (128,128,128),1)
   cv2.circle(base_image, (int(1920/2),int(1080/2)), 400, (128,128,128),1)
   cv2.circle(base_image, (int(1920/2),int(1080/2)), 600, (128,128,128),1)
   cv2.circle(base_image, (int(1920/2),int(1080/2)), 800, (128,128,128),1)
   cv2.circle(base_image, (int(1920/2),int(1080/2)), 1000, (128,128,128),1)

   if SHOW == 1:
      cv2.imshow('pepe', base_image)
      cv2.waitKey(30)



def characterize_fov(cam_id, con, cur, json_conf):
   station_id = json_conf['site']['ams_id']
   autocal_dir = "/mnt/ams2/cal/"
   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
      mcp['cal_version'] += 1
   else:
      mcp = None
   print("YO1-1")
   photo_file = "/mnt/ams2/cal/plots/" + json_conf['site']['ams_id'] + "_" + cam_id + "_MAG_FLUX.png"
   best_cal_files, best_dict = get_best_cal_files(cam_id, con, cur, json_conf, 400)
   title = json_conf['site']['ams_id'] + " " + cam_id + " CALIBRATION FLUX MAGNITUDE PLOT"

   station_id = json_conf['site']['ams_id']
   print("YO1-1")
   import matplotlib.pyplot as plt
   print("YO1-1a")
   grid_img = np.zeros((1080,1920,3),dtype=np.uint8)
   # flux / mag
         #AND star_yn >= 99
   sql = """
      SELECT cal_fn, star_flux, mag 
        FROM calfile_paired_stars
       WHERE star_flux is not NULL
         and cal_fn like ?
   """
   mag_db = {}
   med_flux_db = {}

   cur.execute(sql, [ "%" + cam_id + "%"])
   rows = cur.fetchall()
   xs = []
   ys = []
   for row in rows:
      cal_fn, flx, mag = row
      if mag is None:
         continue
      if mag not in mag_db:
         mag_db[mag] = []
      mag_db[mag].append(flx)

   for mag in sorted(mag_db):
      med_flux = np.median(mag_db[mag])
      mean_flux = np.mean(mag_db[mag])
      med_flux_db[mag] = med_flux
      num_samples = len(mag_db[mag])
      #print(mag, num_samples, mean_flux, med_flux)
      xs.append(mag)
      ys.append(mean_flux)

   print("YO1-2")
   try:
      plt.plot(xs,ys)
      plt.title(title)
      plt.ylabel("Flux")
      plt.xlabel("Magnitude")
      plt.savefig(photo_file)
   except: 
      print("*** FAILED TO MAKE NEW PLOTS MAYBE A QT PYTHON PROBLEM WITH MATPLOTLIB")
   #plt.show()
   print("Saved", photo_file)

   print("YO1-3")
   # determine the avg, min, max zp_dist and zp_slope for each grid in the image!
   grid_size = 100
   grid_data = {}
   for y in range(0,1080) :
      if y == 0 or y % 100 == 0:
         for x in range(0,1920):
            if x == 0 or x % 100 == 0:
               x1 = x
               y1 = y
               x2 = x + grid_size
               y2 = y + grid_size


               sql = """
                  SELECT cal_fn, zp_res_px, zp_slope 
                    FROM calfile_paired_stars 
                   WHERE img_x > ? and img_x < ? 
                     AND img_y > ? and img_y < ?
                     AND zp_res_px is NOT NULL
                     AND cal_fn like ?
               """
               uvals = [x1,x2,y1,y2, "%" + cam_id + "%" ]
               cur.execute(sql, uvals)
               rows = cur.fetchall()
               dist_vals = []
               slope_vals = []

               for row in rows:
                  cal_fn = row[0] 
                  if cal_fn not in best_dict:
                     print(cal_fn, "NOT IN BEST DICT!")
                     continue

                  dist_val = row[1] 
                  slope_val = row[2] 
                  dist_vals.append(dist_val)
                  slope_vals.append(slope_val)

               if len(dist_vals) > 2:
                  med_d_val = np.median(dist_vals)
                  mean_d_val = np.mean(dist_vals)
               else:
                  med_d_val = None
                  mean_d_val = None
               if len(slope_vals) > 2:
                  med_s_val = np.median(slope_vals)
                  mean_s_val = np.mean(slope_vals)
               else:
                  med_s_val = None
                  mean_s_val = None

               med_dist = med_d_val
               if mean_s_val is None:
                  cv2.rectangle(grid_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1)
               elif mean_s_val < 0: 
                  cv2.rectangle(grid_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 255, 0), 1)
               else:
                  cv2.rectangle(grid_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 0, 255), 1)

               if med_dist is not None:
                  desc = str(int(med_dist)) + " " + str(med_s_val)[0:4]
               else:
                  desc = str(len(rows))
               cv2.putText(grid_img, desc,  (x1+15,y1+15), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
               #cv2.imshow("pepper", grid_img)
               #cv2.waitKey(30)

               grid_key = str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2)
               grid_data[grid_key] = [x1,y1,x2,y2,med_d_val, med_s_val]
               #print(x1,y1,x2,y2,med_d_val, med_s_val)


   sql = """
      SELECT cal_fn, name, mag, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, zp_res_px, zp_slope
        FROM calfile_paired_stars
       WHERE 
         new_cat_x is not NULL
         AND cal_fn like ?
   """

       #star_flux is not NULL
         #AND star_yn >= 99
   cur.execute(sql, ["%" + cam_id + "%"])
   rows = cur.fetchall()
   all_good_stars = []

   for row in rows:
      cal_fn, name, mag, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, zp_res_px, zp_slope = row
      med_flux = med_flux_db[mag]
      if cal_fn not in best_dict:
         continue

      if star_flux is not None and med_flux is not None:
         flux_diff = star_flux / med_flux
      else :
         flux_diff = 0

      grid_key = get_grid_key(grid_data, img_x, img_y, zp_res_px, zp_slope)
      try:
         [x1,y1,x2,y2,med_d_val, med_s_val] = grid_data[grid_key] 
      except:
         continue
      if med_d_val is None or zp_res_px is None:
         continue
      dist_diff = zp_res_px /  med_d_val
      scope_diff = zp_slope /  med_s_val
      dist = str(dist_diff)[0:4] + " " + str(scope_diff)[0:4]
      cv2.putText(grid_img, desc,  (x1+15,y1+25), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)

      cval = 128
      if .75 <= dist_diff <= 1.75:
         cval = cval + (cval/2)
      else:
         cval = cval - (cval /2)
      if .75 <= scope_diff <= 1.75:
         cval = cval + (cval/2)
      else:
         cval = cval - (cval /2)
      if .75 <= flux_diff <= 1.75:
         cval = cval + (cval/2)
      else:
         cval = cval - (cval /2)
      if cval > 245:
         cval = 250
         all_good_stars.append((cal_fn, name, mag, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, zp_res_px, zp_slope)) 

      if cval < 0:
         cval = 64 

      if cval > 128:
         color = [0,cval, 0]
      else:
         color = [cval,cval, cval]


      cv2.line(grid_img, (int(zp_cat_x),int(zp_cat_y)), (int(img_x),int(img_y)), color, 2)

      #cv2.imshow("pepper", grid_img)
      #cv2.waitKey(30)
      sql = """UPDATE calfile_paired_stars set star_found = 1 where cal_fn = ? and img_x = ? and img_y = ?"""
      uvals = [cal_fn, img_x, img_y]
      cur.execute(sql, uvals )
      
   if SHOW == 1:
      cv2.imshow("pepe", grid_img)
      cv2.waitKey(90)
   cv2.imwrite("/mnt/ams2/cal/plots/" + station_id + "_" + cam_id + "_ALL_GOOD_STARS.jpg", grid_img)

   print("saved all stars image /mnt/ams2/cal/plots/" + station_id + "_" + cam_id + "_ALL_GOOD_STARS.jpg")
   save_json_file("/mnt/ams2/cal/" + station_id + "_" + cam_id + "_ALL_GOOD_STARS.json", all_good_stars)
   print("saved", "/mnt/ams2/cal/" + station_id + "_" + cam_id + "_ALL_GOOD_STARS.json")
   con.commit()
   # plot all stars?

   #(cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star

   calfiles_data  = load_cal_files(cam_id, con,cur)
   merged_stars = []
   for star in all_good_stars:

      (cal_fn, name, mag, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, zp_res_px, zp_slope) = star
      if cal_fn not in best_dict:
         continue

      if cal_fn in calfiles_data:
         #(cal_fn_ex, center_az,center_el, ra_center,dec_center, position_angle, pixscale) = calfiles_data[cal_fn]
         (station_id, camera_id, cal_fn, cal_ts, center_az, center_el, ra_center, dec_center, position_angle,\
            pixscale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
            y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) = calfiles_data[cal_fn] 


      #match_dist = zp_res_px

      match_dist = 9999
      merged_stars.append((cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,center_az,center_el,new_cat_x,new_cat_y,img_x,img_y,zp_res_px,star_flux)) 
   save_json_file("/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json", merged_stars)
   print("YO3")
   if mcp is not None:
      make_cal_summary(cam_id, json_conf)
      make_cal_plots(cam_id, json_conf)

   #if mcp is not None:
   #   make_lens_model(cam_id, json_conf, merged_stars)


def reconcile_calfiles(cam_id, con, cur, json_conf):
   all_files = {}
   sql = """
      SELECT cal_fn
        FROM calibration_files 
   """
   cur.execute(sql )

   rows = cur.fetchall()
   for row in rows:
      cal_fn = row[0]
      all_files[cal_fn] = {}
      print(cal_fn)


   sql = """
      SELECT cal_fn
        FROM calfile_paired_stars 
   """
   cur.execute(sql )

   rows = cur.fetchall()
   for row in rows:

      cal_fn = row[0]
      all_files[cal_fn] = {}
      print(cal_fn)


   bad_cals = []
   for cal_fn in all_files:
      root = cal_fn.split("-")[0]
      free_cal_dir = "/mnt/ams2/cal/freecal/"
      extra_cal_dir = "/mnt/ams2/cal/extracal/"
      cal_dir = free_cal_dir + root
      if os.path.exists(cal_dir) is False:
         print("bad calfile:", cal_fn)
         bad_cals.append(cal_fn)
      #else:
         #print("good calfile:", cal_fn)

   for bad_fn in bad_cals:
      sql = "DELETE FROM calibration_files where cal_fn = ?"
      cur.execute(sql, [bad_fn] )

      sql = "DELETE FROM calfile_paired_stars where cal_fn = ?"
      cur.execute(sql, [bad_fn] )
   con.commit()

def load_cal_files(cam_id, con, cur, single=False,last=None):
   sql = """
      SELECT station_id,
             camera_id,
             cal_fn,
             cal_ts,
             az,
             el,
             ra,
             dec,
             position_angle,
             pixel_scale,
             zp_az,
             zp_el,
             zp_ra,
             zp_dec,
             zp_position_angle,
             zp_pixel_scale,
             x_poly,
             y_poly,
             x_poly_fwd,
             y_poly_fwd,
             res_px,
             res_deg,
             ai_weather,
             ai_weather_conf,
             cal_version,
             last_update
        FROM calibration_files
   """
   if single is False:
      sql += """
         WHERE cal_fn like ?
      """
      uvals = ["%" + cam_id + "%"]
   else:
      sql += """
         WHERE cal_fn = ?
      """
      uvals = [ cam_id  ]

   # ORDER CALS BY!?

   sql += """
    ORDER BY res_px ASC 
   """



   cur.execute(sql, uvals )

   rows = cur.fetchall()
   calfiles_data = {}

   for row in rows:
      failed = False
      (station_id, camera_id, cal_fn, cal_ts, az, el, ra, dec, position_angle,\
         pixel_scale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
         y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) = row

      cal_dir = cal_dir_from_file(cal_fn)
      if False:
         if cal_dir is False:
            failed = True 
            continue
         elif os.path.exists(cal_dir + cal_fn) is False: 
            failed = True 
            continue

         if failed is True:
            delete_cal_file(cal_fn, con, cur, json_conf)
            continue

      calfiles_data[cal_fn] = (station_id, camera_id, cal_fn, cal_ts, az, el, ra, dec, position_angle,\
         pixel_scale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
         y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) 

   return(calfiles_data)       
   



def get_grid_key(grid_data, img_x, img_y, zp_res_px, zp_slope):
   for gkey in grid_data:
      [x1,y1,x2,y2,med_d_val, med_s_val] = grid_data[gkey] 
      if x1 <= img_x <= x2 and y1 <= img_y <= y2:
         return(gkey)
      
def batch_calib(cam_id, con, cur, json_conf):
   free_cal_dir = "/mnt/ams2/cal/freecal/"
   cal_dirs = glob.glob(free_cal_dir + "*" + cam_id + "*")
   for ccd in sorted(cal_dirs, reverse=True):
      cal_fn = ccd.split("/")[-1]
      cal_img_file = ccd + "/" + cal_fn + "-stacked.png"
      cal_json_file = cal_img_file.replace(".png", "-calparams.json")
      cal_json_fn = cal_json_file.split("/")[-1]
      if os.path.exists(cal_img_file):
         #print("JSON:", cal_json_fn)
         loaded = check_calibration_file(cal_json_fn, con, cur)
         if loaded is False:
            get_image_stars(cal_img_file, con, cur, json_conf)
         else:
            print("Already loaded. ") 



def best_stars(merged_stars, mcp, factor = 2, gsize=50):
   #best = []

   rez = [row[-2] for row in merged_stars]
   med_rez = np.median([row[-2] for row in merged_stars])


   if True:
      grid = make_grid_stars(merged_stars, mcp = None, factor = 2, gsize=50, limit=10)
      best_stars = []
      for grid_key in grid:
         just_data = sorted(grid[grid_key], key=lambda x: x[-2], reverse=False)
         rc = 0
         if len(just_data) > 0:
            for row in just_data:
               if rc < 3:
                  best_stars.append(row)
               else:
                  break 
               rc += 1

   best = []

   med_rez = np.median([row[-2] for row in best_stars])

   res_limit = med_rez ** 2
   if res_limit < 3:
      res_limit = 3
   

   for star in best_stars:
      (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,center_az,center_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = star

      if res_px >  res_limit * 2:
         print("SKIP:", res_px, res_limit)
         foo = 1
      else:
         best.append(star)


   return(best)

def lens_model(cam_id, con, cur, json_conf, cal_fns= None, force=False): 
   lens_img = np.zeros((1080,1920,3),dtype=np.uint8)
   station_id = json_conf['site']['ams_id']
   limit = 1000
   lens_img_file = "/mnt/ams2/cal/" + station_id + "_" + cam_id + "_LENS_IMG_STARS.jpg"
   #cal_fns = batch_review(station_id, cam_id, con, cur, json_conf, limit)

   #save_json_file(cal_sum_file, cal_sum)

   avg_stars, avg_res = get_avg_res(cam_id, con, cur)

   if cal_fns is None:
      sql = """
         SELECT cal_fn, res_px
           FROM calibration_files 
          WHERE cal_fn like ?
            AND res_px < ?
       ORDER BY res_px ASC 
      """

      dvals = ["%" + cam_id + "%", avg_res]
      cur.execute(sql, dvals)
      rows = cur.fetchall()
      cal_fns = []
      for row in rows:
         print("\r", row[0], row[1], end="")
         cal_fns.append(row[0])


   mask_file = "/mnt/ams2/meteor_archive/{}/CAL/MASKS/{}_mask.png".format(station_id, cam_id)

   if os.path.exists(mask_file) is True:
      mask = cv2.imread(mask_file)
      mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
      mask = cv2.resize(mask, (1920,1080))
   else:
      mask = np.zeros((1080,1920),dtype=np.uint8)

   autocal_dir = "/mnt/ams2/cal/"
   station_id = json_conf['site']['ams_id']

   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"

   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
      mcp['cal_version'] += 1
   else:
      mcp = None

   if mcp is not None:
      if "x_fun" in mcp:
         mcp['last_model_x_fun'] = mcp['x_fun']
         mcp['last_model_y_fun'] = mcp['y_fun']

      if "total_stars_used" in mcp:
         tsu = mcp['total_stars_used']
      else:
         tsu = 0

      if "fun_diff_x" in mcp:
         print("FUN DIFF X FROM LAST RUN WAS:", mcp['fun_diff_x'] )
         print("FUN DIFF Y FROM LAST RUN WAS", mcp['fun_diff_y'] )
         if mcp['fun_diff_x'] < .1 and mcp['x_fun'] < 1 and tsu > 300:
            print("xfun is < 1 and the last run only improved by .1.")
            if force is False:
               print("New lens model run aborted because this lens model is already good enough.")
               print("Set force true if you want to force a run")
               return()



   merged_stars = load_json_file("/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json")

   if len(merged_stars) < 25:
      print("NOT ENOUGH MERGED STARS. NEED >= 25 you have:", len(merged_stars))
      return()

   rez = [row[-2] for row in merged_stars]
   print("BEFORE BEST STARS RES:", len(merged_stars), np.median(rez))
   inner_rezs = []
   outer_rezs = []
   xs = []
   ys = []
   for star in merged_stars:
      cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, name,mag,ra,dec,ra,dec,match_dist,orig_cat_x,orig_cat_y,center_az,center_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux = star
      center_dist = calc_dist((img_x,img_y), (1920/2, 1080/2))
      xs.append(img_x)
      ys.append(img_y)
      if center_dist > 600:
         outer_rezs.append(res_px)
      else:
         inner_rezs.append(res_px)
   inner_res = np.median(inner_rezs) * 2
   outer_res = np.median(outer_rezs) * 4

   # best stars only
   #merged_stars = best_stars(merged_stars, mcp, factor = 2, gsize=50)
   rez = [row[-2] for row in merged_stars]
   

   rez = [row[-2] for row in merged_stars] 
   if len(merged_stars) > 5:
      med_rez = np.median(rez) * 2
   else:
      med_rez = 10 
   nms = []

   print("MED REZ IS (med, inner, outer):",  med_rez, inner_res, outer_res)
   print("MERGED STARS IS:", len(merged_stars))

   # final quality check
   xx = 0
   for star in merged_stars:
      cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, name,mag,ra,dec,ra,dec,match_dist,orig_cat_x,orig_cat_y,center_az,center_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux = star
      center_dist = calc_dist((img_x,img_y), (1920/2, 1080/2))
      if center_dist > 600:
         factor = 4
         trez = outer_res * factor
      else:
         factor = 2
         trez = inner_res * factor
      # reject if the x-y in the mask 
      mask_val = mask[int(img_y),int(img_x)]
      if mask_val > 0: 
         continue
      cv2.circle(lens_img, (int(img_x),int(img_y)), 15, (128,255,128),1)
      color = (255,255,255)
      cv2.line(lens_img, (int(orig_cat_x),int(orig_cat_y)), (int(img_x),int(img_y)), color, 1)
      if star[-2] < trez  :
         nms.append(star)
         if SHOW == 1:
            if xx % 10 == 0:
               cv2.imshow('pepe', lens_img)
               cv2.waitKey(30)
         xx += 1

         print("LM KEEP STAR", med_rez, star[0], star[-2])
      else:
         print("LM IGNORE STAR", med_rez, star[0], star[-2])
   #merged_stars = nms
   cv2.imwrite(lens_img_file, lens_img)
   #print("\tSAVED lens_img_file:", lens_img_file)
   status, cal_params,merged_stars = minimize_poly_multi_star(merged_stars, json_conf,0,0,cam_id,None,mcp,SHOW)
   if cal_params == 0:
      print("LENS MODEL MAKE FAILED")
      return() 



   if "cal_version" not in cal_params and mcp is None:
      cal_params['cal_version'] = 1 
   else:
      cal_params['cal_version'] =  mcp['cal_version']

   new_x_fun = cal_params['x_fun']
   new_y_fun = cal_params['y_fun']

   cal_params['lens_model_x_fun'] = new_x_fun
   cal_params['lens_model_y_fun'] = new_y_fun

   print("The new lens model has completed NEW XY FUN", cal_params['x_fun'], cal_params['y_fun'])
   time.sleep(2)
   if mcp is not None:
      #print("LAST XY FUN", mcp['last_model_x_fun'] , mcp['last_model_y_fun'] )
      if "last_model_x_fun" in mcp:
         fun_diff_x = mcp['last_model_x_fun'] - cal_params['x_fun']
         fun_diff_y = mcp['last_model_y_fun'] - cal_params['y_fun']
      else:
         fun_diff_x = 99
         fun_diff_y = 99

   else:
      fun_diff_x = 99
      fun_diff_y = 99
   cal_params['fun_diff_x'] = fun_diff_x 
   cal_params['fun_diff_y'] = fun_diff_y 

   if fun_diff_x > 0:
      print("X FUN IMPROVED BY:", fun_diff_x)
   else:
      print("X FUN GOT WORSE BY:", fun_diff_x)

   if fun_diff_y > 0:
      print("Y FUN IMPROVED BY:", fun_diff_y)
   else:
      print("Y FUN GOT WORSE BY:", fun_diff_y)


   now = datetime.datetime.now()
   now_str = now.strftime("%Y_%m_%d %H:%M:%S")
   time_stamp = time.time()
   cal_params['lens_model_datetime'] = now_str
   cal_params['lens_model_timestamp'] = time_stamp 
   cal_params['total_stars_used'] = len(merged_stars)
   cal_params['min_max_x_dist'] = max(xs) - min(xs)
   cal_params['min_max_y_dist'] = max(ys) - min(ys)

   if  cal_params['min_max_x_dist'] > 1500 and  cal_params['min_max_y_dist'] > 800:
      cal_params['min_max_dist_status'] = "GOOD"
   elif cal_params['min_max_x_dist'] > 1500 and cal_params['min_max_y_dist'] > 600:
      cal_params['min_max_dist_status'] = "OK"
   else:
      cal_params['min_max_dist_status'] = "BAD"
    
   save_json_file(mcp_file, cal_params)
   print("\tSAVED MCP:", mcp_file)

   # save the new merged stars!
   new_merged_stars = []

   rez = [row[-2] for row in merged_stars] 
   med_rez = np.median(rez) 

   tb = pt()
   tb.field_names = ["Action", "Star", "Mag", "Intensity", "Res Limit", "Res Pixels", ]
   # med_rez 
   for star in merged_stars:
      (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,center_az,center_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = star
      cal_params['center_az'] = center_az
      cal_params['center_el'] = center_el
      cal_params['ra_center'] = ra_center
      cal_params['dec_center'] = dec_center
      cal_params['position_angle'] = position_angle 
      cal_params['pixscale'] = pixscale 
      #nc = update_center_radec(cal_fn,cal_params,json_conf)
      new_cat_x,new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)
      res_px = calc_dist((img_x,img_y),(new_cat_x,new_cat_y))
      center_dist = calc_dist((img_x,img_y), (1920/2, 1080/2))
      if center_dist > 600:
         factor = 3  
      else:
         factor = 2
         
      if res_px <= med_rez * factor:
         new_merged_stars.append((cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,center_az,center_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux))
         act = "KEEP"
      else:
         act = "REJECT"
      tb.add_row([act, name, mag, star_flux, med_rez, res_px])


   if len(new_merged_stars) > 500:
      save_json_file("/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json", new_merged_stars)

   rez = [row[-2] for row in new_merged_stars] 
   mean_rez = np.median(rez) 
   print("NEW STARS:", len(new_merged_stars))
   print("NEW REZ:", mean_rez)
   print(tb)
   lens_model_report(cam_id, con, cur, json_conf)
   # write data to the cal_summary file

   #if os.path.exists(cal_sum_file) is True:
   #   cal_sum = load_json_file(cal_sum_file)
   #else: 
   #   cal_sum = {}

   #cal_sum['lens_model_datetime'] = now_str
   #cal_sum['lens_model_timestamp'] = time_stamp 
   #save_json_file(cal_sum_file, cal_sum)


def wizard(station_id, cam_id, con, cur, json_conf, file_limit=25):

   if SHOW == 1:
      cv2.namedWindow("pepe")
      cv2.resizeWindow("pepe", 1920, 1080)
      cv2.moveWindow("pepe", 1400,100)


   os.system("clear")
   print("ALLSKY7 LENS MODEL CALIBRATION WIZARD")
   print("Limit:", file_limit)   
   # review / apply the current lens model 
   # and calibration on the best 10 files

   best_cal_fns = []
   res_test = []
   if True:
      cal_fns, calfiles_data = batch_review(station_id, cam_id, con, cur, json_conf, file_limit)
      print("CAL FINS RETURNED FROM BATCH REVIEW:", len(cal_fns))
      for cal_fn in cal_fns:
         print(calfiles_data[cal_fn][-6])
         res_test.append(calfiles_data[cal_fn][-6])
      mres = np.median(res_test)
      for cal_fn in cal_fns:
         res = calfiles_data[cal_fn][-6]
         if res < mres * 1.5:
            print("USE:", cal_fn, res)
            best_cal_fns.append(cal_fn) 
         else:
            print("SKIP2:", cal_fn, res)

      cal_fns = best_cal_fns


   else:
      avg_stars, avg_res = get_avg_res(cam_id, con, cur)
      cal_fns = []
      sql = """
             SELECT cal_fn, avg(res_px) as rp, count(*) stars
               FROM calfile_paired_stars
              WHERE cal_fn = ?
                AND res_px < ?
                AND stars >= ?
           GROUP BY cal_fn
           ORDER BY rp, stars desc 
           limit ?
      """
      dvals = ["%" + cam_id + "%", (avg_res *.9), avg_stars, file_limit]
      cur.execute(sql, dvals)
      rows = cur.fetchall()
      for row in rows:
         cal_fn, res, stars = row
         #print("USING:", cal_fn, res, stars)

         cal_fns.append(cal_fn)

   print("Running lens wizard with : ", len(cal_fns))
   # characterize the current lens model 
   # and define best merge star values
   print("CAL FNS :", cal_fns)
   characterize_best(cam_id, con, cur, json_conf, file_limit, cal_fns)
   # run lens model with current stars
   lens_model(cam_id, con, cur, json_conf, cal_fns)
   #exit()

   file_limit = int(file_limit) * 2
   print("FILE LIMIT:", file_limit)
   cal_fns, calfiles_data = batch_review(station_id, cam_id, con, cur, json_conf, file_limit)
   characterize_best(cam_id, con, cur, json_conf, file_limit, cal_fns)
   # run lens model a second time
   lens_model(cam_id, con, cur, json_conf, cal_fns)

   # now the lens model should be made within around to less than 1PX res. 
   # if it is less than 2px that is fine as each indiviual capture will
   # be specifically fined tuned. Remember the goal here is to make a generic model
   # that can be applied to any file at any time. Not to neccessarily get the minimize possible res

   # lens_model_final_report()
   lens_model_report(cam_id, con, cur, json_conf)
   merged_star_file = "/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json"
   merged_stars = load_json_file(merged_star_file)
   make_lens_model(cam_id, json_conf, merged_stars)
   #try:
   #except:
   #   print("Make lens model failed?")

   #characterize_fov(cam_id, con, cur, json_conf)

def lens_model_report(cam_id, con, cur, json_conf):
   #characterize_fov(cam_id, con, cur, json_conf)
   characterize_best(cam_id, con, cur, json_conf)
   import matplotlib.pyplot as plt

   station_id = json_conf['site']['ams_id']
   msfile = "/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json"
   if os.path.exists(msfile) is True:
      merged_stars = load_json_file(msfile)
   make_cal_plots(cam_id, json_conf)

   try:
      make_lens_model(cam_id, json_conf, merged_stars)
   except:
      print("Failed making some files.")

   #exit()
   #print("ENDED AFTER SUM")
   grid_bg = np.zeros((1080,1920,3),dtype=np.uint8)
   autocal_dir = "/mnt/ams2/cal/"
   station_id = json_conf['site']['ams_id']
   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   merged_star_file = "/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json"

   if os.path.exists(merged_star_file) is False:
      print("No star file :", cam_id)
      return()
   mstars = load_json_file(merged_star_file)
   if os.path.exists(mcp_file):
      mcp = load_json_file(mcp_file)
      print(mcp.keys())
   else:
      return()



   print("LENS MODEL REPORT FOR ", cam_id)
   print("--------------------- ")

   print("Stars used in final lens model:", len(mstars))
   print("Final Multi-Poly Res X (px):", mcp['x_fun'])
   print("Final Multi-Poly Res Y (px):", mcp['y_fun'])
   print("Final Multi-Poly Fwd Res X (deg):", mcp['x_fun_fwd'])
   print("Final Multi-Poly Fwd Res Y (deg):", mcp['y_fun_fwd'])
   print("Images")
   print("------")
   print("All Stars / Distortion Image")
   print("Final Multi-Image ")
   print("Final Multi-Image FWD")
   print("Grid Image")
   print("Graphs")
   print("Photometry")

   # Photometry report
   mags = []
   fluxs = []
   xs = []
   ys = []
   med_flux_db = {}
   mag_db = {}
   for star in mstars:
      (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,flx) = star
      mags.append(mag)
      fluxs.append(flx)
      if mag is None:
         continue
      if mag not in mag_db:
         mag_db[mag] = []
      if flx is not None:
         mag_db[mag].append(flx)
   
   for mag in sorted(mag_db):
      if "mag" in mag_db:
         med_flux = np.median(mag_db[mag])
         mean_flux = np.mean(mag_db[mag])
         med_flux_db[mag] = med_flux
         num_samples = len(mag_db[mag])
         #print(mag, num_samples, mean_flux, med_flux)
         xs.append(mag)
         ys.append(mean_flux)

   mj = {}
   mj['cp'] = mcp 
   #mj['sd_trim'] = cal_file 


   plt.scatter(mags,fluxs)
   #plt.show()
   plt.plot(xs,ys)
   #plt.show()



def fix_cal(cal_fn, con, cur,json_conf ):
   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)
   if True:
      mcp_file = "/mnt/ams2/cal/" + "multi_poly-" + station_id + "-" + cam_id + ".info"
      anc_file = "/mnt/ams2/cal/" + station_id + "_" + cam_id + "_ANCHOR.json"
      print(anc_file)
      if os.path.exists(mcp_file) == 1:
         mcp = load_json_file(mcp_file)
         # reset mcp if it is bad
         if mcp['x_fun'] > 5:
            mcp = None
      else:
         mcp = None
      if os.path.exists(anc_file) is True:
         anc_data = load_json_file(anc_file)
      else:
         anchor_cal(cam_id, con, cur, json_conf)
         anc_data = load_json_file(anc_file)

   if "json" in cal_fn:
      cal_dir = "/mnt/ams2/cal/freecal/" + cal_fn.replace("-stacked-calparams.json", "/")
   cal_params = load_json_file(cal_dir + cal_fn)
   cal_img = cv2.imread(cal_dir + cal_fn.replace("-calparams.json", ".png"))
   range_data = get_cal_range(cal_fn, cal_img, con, cur, json_conf)

   #for row_data in range_data:
   best_score = 0
   best_cp = None
   for row_data in anc_data['groups']:
      show_img = cal_img.copy()
      cp = dict(cal_params)

      #rcam_id, rend_dt, rstart_dt, elp, az, el, pos, pxs, res = row_data
      az, el, pos, pxs = row_data.split("_")
      cp['center_az'] = int(az)
      cp['center_el'] = int(el)
      cp['position_angle'] = int(pos)
      cp['pixscale'] = int(pxs)

      cp = update_center_radec(cal_fn,cp,json_conf)

      #cp['cat_image_stars'], cp['user_stars'], flux_table = get_image_stars_with_catalog(cal_fn, cp, show_img)
      cp['cat_image_stars'] = pair_star_points(cal_fn, cal_img, cp.copy(), json_conf, con, cur, mcp, save_img = False)
      cp, bad_stars, marked_img = eval_cal_res(cal_fn, json_conf, cp.copy(), cal_img,None,None,cp['cat_image_stars'])

      new_cat_image_stars = []
      for star in cp['cat_image_stars']:
         (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
         new_cat_x, new_cat_y = get_xy_for_ra_dec(cp, ra, dec)
         res_px = calc_dist((six,siy),(new_cat_x,new_cat_y))
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_fn,cp,json_conf)
         match_dist = angularSeparation(ra,dec,img_ra,img_dec)
         real_res_px = res_px
         new_cat_image_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,real_res_px,bp))
      cp['cat_image_stars'] = new_cat_image_stars

      rez = [row[-2] for row in cp['cat_image_stars'] ]
      med_rez = np.median(rez) 
      extra_text = str(med_rez) + " pixel median residual distance"
      score = len(cp['cat_image_stars']) / float(med_rez)
      print("STARS, SCORE, REZ FIX CAL FILE IS:", len(cp['cat_image_stars']), score, med_rez)
      if score > best_score:
         best_cp = cp.copy()
         best_score = score 


      star_img = draw_star_image(show_img, cp['cat_image_stars'],cp, json_conf, extra_text) 
      if SHOW == 1:
         cv2.imshow('pepe', star_img)
         cv2.waitKey(30)
   print("FINAL")
   show_img = cal_img.copy()
   star_img = draw_star_image(show_img, best_cp['cat_image_stars'],best_cp, json_conf, extra_text) 
   if SHOW == 1:
      cv2.imshow('pepe', star_img)
      cv2.waitKey(30)

   stars,cat_stars = get_paired_stars(cal_fn, best_cp, con, cur)
   best_cp, cat_stars = recenter_fov(cal_fn, best_cp, cal_img.copy(),  stars, json_conf, "")
   best_cp = update_center_radec(cal_fn,best_cp,json_conf)

   stars,cat_stars = get_paired_stars(cal_fn, best_cp, con, cur)
   best_cp, cat_stars = recenter_fov(cal_fn, best_cp, cal_img.copy(),  stars, json_conf, "")


   print("FINAL FINAL")
   show_img = cal_img.copy()
   star_img = draw_star_image(show_img, best_cp['cat_image_stars'],best_cp, json_conf, extra_text) 
   print("STARS/RES", len(best_cp['cat_image_stars']), best_cp['total_res_px'])
   if SHOW == 1:
      cv2.imshow('pepe', star_img)
      cv2.waitKey(30)
   return(best_cp)
   


def find_best_calibration(cal_fn, orig_cal, json_conf):
   station_id = json_conf['site']['ams_id']
   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)
   # Not used...
   cal_range_file = "/mnt/ams2/cal/" + "cal_day_hist.json"
   list_of_cals = load_json_file(cal_range_file)
   last_best_res = 9999
   last_best_cal = None 

   for row in list_of_cals:
      [t_cam_id, cal_date, az,el,pos,pxs,ores] = row
      if t_cam_id != cam_id:
         continue

      cp = dict(orig_cal)
      cp['center_az'] = az
      cp['center_el'] = el
      cp['position_angle'] = pos
      cp['pixscale'] = pxs
      cp = update_center_radec(cal_fn,cp,json_conf)
      new_cat_image_stars = []
      for star in cp['cat_image_stars']:
         (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,res_px,bp) = star
         new_cat_x, new_cat_y = get_xy_for_ra_dec(cp, ra, dec)
         res_px = calc_dist((six,siy),(new_cat_x,new_cat_y))
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_fn,cp,json_conf)
         match_dist = angularSeparation(ra,dec,img_ra,img_dec)
         real_res_px = res_px
         new_cat_image_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,real_res_px,bp))
      cp['cat_image_stars'] = new_cat_image_stars

      rez = [row[-2] for row in cp['cat_image_stars'] ]
      rez_deg = [row[-11] for row in cp['cat_image_stars'] ]
      med_rez = np.median(rez) #** 2
      med_rez_deg = np.median(rez_deg) #** 2
      if med_rez < last_best_res: 
         last_best_res = med_rez
         cp['total_res_px'] = med_rez
         cp['total_res_deg'] = med_rez_deg
         last_best_cal = cp
   #print("   NEW BEST RES (px/deg):", cp['total_res_px'], cp['total_res_deg'])

   return(last_best_cal)

def prune(cam_id, con, cur, json_conf):
   #print("Prune calfiles for cam_id")
   freecal_dir = "/mnt/ams2/cal/freecal/"
   extracal_dir = "/mnt/ams2/cal/extracal/"
   if os.path.exists(extracal_dir) is False:
      os.path.exists(extracal_dir)
   temp = os.listdir(freecal_dir)
   cal_files = []
   for xx in temp:
      if cam_id in xx:
         cal_files.append(xx)

   freecal_index = load_json_file("/mnt/ams2/cal/freecal_index.json") 
   month_dict = {}
   pruned = 0
   for cal_file in freecal_index:
      if cam_id not in cal_file:
         continue
      cal_fn = cal_file.split("/")[-1]
      day = cal_fn[0:10]
      month = cal_fn[0:7]
      if month not in month_dict:
         month_dict[month] = {}
         month_dict[month]['files'] = []
      data = freecal_index[cal_file]
      month_dict[month]['files'].append([cal_file, data])

   mc = 0
   bad_data = []
   for month in sorted(month_dict, reverse=True):
      if mc < 1:
         print("Skip most recent month!")
         mc += 1
         continue
      over_files = len(month_dict[month]['files']) - 15
      print(month, len(month_dict[month]['files']), "over", over_files )
      just_data = []
      for cal_file, data in month_dict[month]['files'] :
         just_data.append(data)
      if over_files <= 1:
         print("THIS MONTH IS GOOD", month)
         continue
      try:
         just_data = sorted(just_data, key=lambda x: x['total_stars'] / x['total_res_px'], reverse=True)
      except:
         print("PROBLEM")

      for data in just_data[0:over_files]:
         if os.path.isdir(data['base_dir']) is True:
            cmd = "mv " + data['base_dir'] + " " + extracal_dir
            print(cmd)
            os.system(cmd)
            #print(data['base_dir'], data['total_stars'], data['total_res_px'])
            pruned += 1
         else:
            if "total_stars" in data:
               print("DONE ALREADY!", data['base_dir'], data['total_stars'], data['total_res_px'])
            else:
               bad_data.append(data)

      mc += 1
      
   print("Before prune total files:", len(cal_files))
   print("Suggest pruning:", pruned)
   print("After prune total files:", len(cal_files) - pruned)


if __name__ == "__main__":

   try:
      import PySimpleGUI as sg
   except:
      print("Missing lib:")
      print("sudo python3 -m pip install PySimpleGUI")



   tries = 0
   logo_x = 1550 
   logo_y = 950 

   RF = RenderFrames()
   VE = VideoEffects()

   MOVIE_FRAMES_TEMP_FOLDER = "/home/ams/REFIT_METEOR_FRAMES_TEMP/"
   if sys.argv[1] == "refit_meteor_day" : 
      SAVE_MOVIE = True
   else:
      SAVE_MOVIE = False 

   py_running = check_running("python")
   print("Python processes running now:", py_running)
   if py_running > 15:
      print("Too many processes to run, try again later")
      #exit()
   else:
      print("Ok to run!")

   running = check_running("recal.py ")
   if running > 2 and sys.argv[1] != "refit_meteor":
      print("ALREADY RUNNING:", running)
      cmd = "echo " + str(running) + " >x"
      os.system(cmd)
      print("Press enter to re-start processes.") 
      i, o, e = select.select( [sys.stdin], [], [], 10 )
      if (i) :
         cmd = "kill -9 $(ps aux | grep 'recal.py' | awk '{print $2}')"
         print(cmd)
         os.system(cmd)
      else:
         print("AUTO KILLED")
         exit()


   json_conf = load_json_file("../conf/as6.json")
   station_id = json_conf['site']['ams_id']
   db_file = station_id + "_CALIB.db" 
   #con = sqlite3.connect(":memory:")

   if os.path.exists(db_file) is False:
      cmd = "cat CALDB.sql |sqlite3 " + db_file
      print("Making calibration database...")
      
      print(cmd)
      os.system(cmd)
   #else:
   #   print("CAL DB EXISTS ALREADY")

   con = sqlite3.connect(db_file)
   cur = con.cursor()

   cmd = sys.argv[1]
   if len(sys.argv) > 2:
      cal_file = sys.argv[2]

   # batch = batch load cal files in DB / v2 structure
   # gis = process 1 file for first time
   # cal_main = main menu
   # char = recharacterize camera -- pre-req for lens_model 
   # lens_model = make multi-file lens model from best stars
   # update_calfiles = update all files with latest poly vals, re-center and re-pick/calc stars and res
   # view = view a file
   # man_tweek = tweek a file

   # cron process/es shoudl be: {
   #   batch
   #   char
   #   lens_model
   #   update
   # }
   # do this 3-5x and it should be good?!
   # 
   print("CMD:", cmd)
   if cmd == "fix_lens_nans":
      fix_lens_nans()

   if sys.argv[1] == "remote"  or sys.argv[1] == "remote_cal":
      if len(sys.argv) == 2:
         remote_menu(con, cur)
      else:
         cal_file = sys.argv[2]
         remote_cal(cal_file, con, cur)

   if sys.argv[1] == "rescue" :
      cam_id = sys.argv[2]
      rescue_cal(cam_id, con, cur, json_conf)


   if cmd == "anchor_cal" :
      cam_id = sys.argv[2]
      anchor_cal(cam_id, con, cur, json_conf)

   if cmd == "best" :
      cam_id = sys.argv[2]
      characterize_best(cam_id, con, cur, json_conf)

   if cmd == "batch" :
      # WORKS BUT OLD AND SLOW
      # USE status to get started and wiz to perfect!

      cam_id = sys.argv[2]
      batch_calib(cam_id, con, cur, json_conf)
   if cmd == "get_image_stars" or cmd == "gis":
      get_image_stars(cal_file, con, cur, json_conf)
   if cmd == "cal_main" :
      cal_main(cal_file)
   if cmd == "char" :
      cam_id = sys.argv[2]
      characterize_fov(cam_id, con, cur, json_conf)
      characterize_best(cam_id, con, cur, json_conf)

   if cmd == "fast_lens":
      force = 1
      cam_id = sys.argv[2]
      limit = 10 
      if len(sys.argv) > 3:
         limit = int(sys.argv[3])

      if cam_id == "all":
         for cam_num in json_conf['cameras']:
            cam_id = json_conf['cameras'][cam_num]['cams_id']
            fast_lens(cam_id, con, cur, json_conf,limit, None)
            lens_model(cam_id, con, cur, json_conf, None,force)
      else:
         fast_lens(cam_id, con, cur, json_conf,limit, None)
         lens_model(cam_id, con, cur, json_conf, None,force)


   if cmd == "lens_model" :

      cam_id = sys.argv[2]
      if len(sys.argv) > 3:
         force = True
      else:
         force = False 

      if cam_id == "all":
         for cam_num in json_conf['cameras']:
            cam_id = json_conf['cameras'][cam_num]['cams_id']
            lens_model(cam_id, con, cur, json_conf, None,force)
      else:
         lens_model(cam_id, con, cur, json_conf, None, force)



   if cmd == "update" :
      cam_id = sys.argv[2]
      update_calfiles(cam_id, con, cur, json_conf)
   if cmd == "view" :
      view_calfile(cal_file, con, cur, json_conf)
   if cmd == "man_tweek" :
      manual_tweek_calib(cal_file, con, cur, json_conf)
   if cmd == "reset_bad_cals" :

      cam_id = sys.argv[2]
      reset_bad_cals(cam_id, con, cur, json_conf)

   if cmd == "apply_calib" :
      cf = sys.argv[2]
      (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cf)
      autocal_dir = "/mnt/ams2/cal/"
      mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
      if os.path.exists(mcp_file) == 1:
         mcp = load_json_file(mcp_file)
         # reset mcp if it is bad
         if mcp['x_fun'] > 5:
            mcp = None
      else:
         mcp = None

      calfiles_data = load_cal_files(cam_id, con, cur)

      last_cal_params = apply_calib(cf, calfiles_data, json_conf, mcp, None, "")

   if cmd == "batch_apply_bad" :
      cam_id = sys.argv[2]
      if len(sys.argv) > 3:
         blimit = sys.argv[3] 
      else:
         blimit = 25

      if cam_id != "ALL" and cam_id != "all":
         batch_apply_bad(cam_id, con, cur, json_conf, blimit)
      else:
         for cam_num in json_conf['cameras']:
            cam_id = json_conf['cameras'][cam_num]['cams_id']
            batch_apply_bad(cam_id, con, cur, json_conf, blimit)

      os.system("cd ../pythonv2; ./autoCal.py cal_index")

   if cmd == "batch_apply" :
      cam_id = sys.argv[2]
      if cam_id == "ALL" or cam_id == "all":
         for cam_num in json_conf['cameras']:
            cam_id = json_conf['cameras'][cam_num]['cams_id']
            #cmd = "python3 recal.py batch_apply {}".format(cam_id)
            #os.system(cmd)
            batch_apply(cam_id, con, cur, json_conf, None, True)

      else:
         if len(sys.argv) > 3:
            # do bad
            batch_apply(cam_id, con, cur, json_conf, None, True)
         else:
            batch_apply(cam_id, con, cur, json_conf)

   if cmd == "cat_view" :
      cal_fn = sys.argv[2]
      cat_view(cal_fn, con, cur, json_conf)
   if cmd == "find_stars_cat" :
      cal_fn = sys.argv[2]
      find_stars_with_catalog(cal_fn, con, cur, json_conf)
   if cmd == "cat_image" :
      cal_fn = sys.argv[2]
      catalog_image(cal_fn, con, cur, json_conf)

   if cmd == "batch_review" :
      cam_id = sys.argv[2]
      batch_review(station_id, cam_id, con, cur, json_conf)
   if cmd == "wiz" :
      cam_id = sys.argv[2]
      if len(sys.argv) > 3:
         limit = int(sys.argv[3])
      else:
         limit = 25

      if cam_id == "all":
         for cam_num in json_conf['cameras']:
            cam_id = json_conf['cameras'][cam_num]['cams_id']
            cmd = "python3 recal.py wiz {} {}".format(cam_id, limit)
            os.system(cmd)
            #wizard(cam_id, con, cur, json_conf, limit)
      else:
         wizard(station_id, cam_id, con, cur, json_conf, limit)

   if cmd == "status" :
      cam_id = sys.argv[2]
      print("CAM:", cam_id)
      if cam_id == "all":
         for cam_num in json_conf['cameras']:
            cn = int(cam_num.replace("cam", ""))
            if cn > 7:
               continue
            cam_id = json_conf['cameras'][cam_num]['cams_id']
            cal_status_report(cam_id, con, cur, json_conf)
      else:
         print("CAM:", cam_id)
         cal_status_report(cam_id, con, cur, json_conf)
      os.system("cd /home/ams/amscams/pythonv2/; ./autoCal.py cal_index")
      plot_cal_history(con, cur, json_conf)



   if cmd == "prune" :
      cam_id = sys.argv[2]

      if cam_id == "all":
         for cam_num in json_conf['cameras']:
            cam_id = json_conf['cameras'][cam_num]['cams_id']
            prune(cam_id, con, cur, json_conf)
      else:
         prune(cam_id, con, cur, json_conf)
   if cmd == "lens_model_report" :
      cam_id = sys.argv[2]
      if cam_id == "all":
         for cam_num in json_conf['cameras']:
            cam_id = json_conf['cameras'][cam_num]['cams_id']
            lens_model_report(cam_id, con, cur, json_conf)
      else:
         lens_model_report(cam_id, con, cur, json_conf)
   if cmd == "run_astr":
      cam_id = sys.argv[2]
      run_astr(cam_id, json_conf, con, cur)

   if cmd == "make_plate":
      cal_fn = sys.argv[2]
      plate_file, plate_img = make_plate(cal_fn, json_conf, con, cur)
      solve_field(plate_file, json_conf, con, cur)
   if cmd == "star_points":
      cam_id = sys.argv[2]
      if cam_id == "all":
         for cam_num in json_conf['cameras']:
            cam_id = json_conf['cameras'][cam_num]['cams_id']
            star_points_all(cam_id, json_conf, con, cur)
      else:
         star_points_all(cam_id, json_conf, con, cur)
   if cmd == "star_points_report":
      cam_id = sys.argv[2]
      if cam_id == "all":
         for cam_num in json_conf['cameras']:
            cam_id = json_conf['cameras'][cam_num]['cams_id']
            star_points_report(cam_id, json_conf, con, cur)
      else:
         star_points_report(cam_id, json_conf, con, cur)


   if cmd == "star_track" :
      cam_id = sys.argv[2]
      date = sys.argv[3]
      star_track(cam_id, date, con, cur, json_conf)
  

   if cmd == "fix_cal" :
      cal_file = sys.argv[2]
      fix_cal(cal_file, con, cur, json_conf)


   if cmd == "refit_meteor" :
      meteor_file = sys.argv[2]
      refit_meteor(meteor_file, con, cur, json_conf)

   if cmd == "refit_meteor_year":
      year = sys.argv[2]
      files = os.listdir("/mnt/ams2/meteors/")
      for ff in sorted(files, reverse=True):
         if year not in ff:
            continue
         if os.path.isdir("/mnt/ams2/meteors/" + ff + "/") is True :
            print(ff)
            print("/mnt/ams2/meteors/" + ff + "/refit_summary.log") 
            if os.path.exists("/mnt/ams2/meteors/" + ff + "/refit_summary.log") is False:
               refit_meteor_day(ff, con, cur , json_conf)
               #print(cmd)
               #os.system(cmd)
            else:
               print("Did already.")
   if cmd == "refit_summary" :
      date = sys.argv[2]
      mdir = "/mnt/ams2/meteors/" + date + "/"
      refit_log_file = mdir + "refit.log"
      refit_sum_file = mdir + "refit_summary.log"
      if os.path.exists(refit_log_file) is True:
         refit_log = load_json_file(refit_log_file)
         report = refit_summary(refit_log)
         save_json_file(refit_sum_file, report)

   if cmd == "recal" :
      # main recal routine 
      recal_history_file = "/mnt/ams2/cal/recal.json" 
      if os.path.exists(recal_history_file) is True:
         recal_hist = load_json_file(recal_history_file)
      else:
         recal_hist = {}

      os.system("touch pause-jobs.json")
      cam_id = sys.argv[2]
      force = 1
      if cam_id != "ALL" and cam_id != "all":
         limit = 25
         fast_lens(cam_id, con, cur, json_conf,limit, None)
         lens_model(cam_id, con, cur, json_conf, None,force)
         batch_apply(cam_id, con, cur, json_conf, None, True)
      else:
         # for now only continue if the cam is not in the hist file yet
         for cam_num in json_conf['cameras']:
            limit = 25
            cam_id = json_conf['cameras'][cam_num]['cams_id']
            if cam_id in recal_hist:
               elp =  (time.time() - recal_hist[cam_id]['last_run']) / 60 / 60 / 24
               print("Did already", cam_id, elp , "days ago")
               # do max of 1x per 5 days 
               if elp < 5:
                  print("Skip -- we recalled this cam within the last 5 days")
                  time.sleep(5)
                  continue
            else:
               cal_status_report(cam_id, con, cur, json_conf)
               recal_hist[cam_id] = {}
               recal_hist[cam_id]['last_run'] = time.time()
            fast_lens(cam_id, con, cur, json_conf,limit, None)
            lens_model(cam_id, con, cur, json_conf, None,force)
            batch_apply(cam_id, con, cur, json_conf, None, True)
            save_json_file(recal_history_file, recal_hist)
      save_json_file(recal_history_file, recal_hist)
      os.system("rm pause-jobs.json")

   if cmd == "perfect_cal" or cmd == "perfect":
      cam_id = sys.argv[2]

      if cam_id != "ALL" and cam_id != "all":
         perfect_cal(cam_id, con, cur, json_conf)
      else:
         for cam_num in json_conf['cameras']:
            cam_id = json_conf['cameras'][cam_num]['cams_id']
            perfect_cal(cam_id, con, cur, json_conf)

   if cmd == "revert" :
      cal_fn = sys.argv[2]
      revert_to_wcs(cal_fn)

   if cmd == "cal_index" :
         os.system("cd ../pythonv2; ./autoCal.py cal_index")

   if cmd == "plot_cal_history" :
      plot_cal_history(con, cur, json_conf)

   if cmd == "cal_plots" :
      cam_id = sys.argv[2]
      make_cal_plots(cam_id, json_conf)
      make_cal_summary(cam_id, json_conf)

   if cmd == "quality_check" :
      cam_id = sys.argv[2]
      quality_check_all_cal_files(cam_id, con, cur) 

   if cmd == "plot_refit_meteor_day":
      meteor_day = sys.argv[2]
      plot_refit_meteor_day(meteor_day, con, cur, json_conf)

   if cmd == "cal_health" :
      cal_health(con, cur, json_conf, sys.argv[2])
   if cmd == "copy_best_cal_images" :
      copy_best_cal_images(con, cur, json_conf)
   if cmd == "retry_astrometry" :
      cam_id = sys.argv[2]
      retry_astrometry( cam_id)

   
   if cmd == "refit_meteor_day" :
      date = sys.argv[2]

      refit_meteor_day(date, con, cur , json_conf)
      exit()
      mdir = "/mnt/ams2/meteors/" + date + "/"
      files = os.listdir("/mnt/ams2/meteors/" + date + "/")
      refit_log_file = mdir + "refit.log"
      if os.path.exists(refit_log_file) is True:
         refit_log = load_json_file(refit_log_file)
         refit_summary(refit_log)
      else:
         refit_log = []
      last_best = {}

      print(refit_log_file)

      by_cam = {}
      for ff in files:
         (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(ff)
         if "json" not in ff:
            continue
         if "reduced" in ff:
            continue

         if cam_id not in by_cam:
            by_cam[cam_id] = {}
         by_cam[cam_id][ff] = {}

      all_files = []
      for cam in by_cam:
         for ff in by_cam[cam]:
            all_files.append(ff) 

      last_cp = {}
      last_best = {}
      for ff in all_files:
         (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(ff)
         last_cp = refit_meteor(ff, con, cur, json_conf, None, last_best)
         if last_cp is None:
            continue
         last_cp = refit_meteor(ff, con, cur, json_conf, None, last_best)

         if cam_id not in last_best:
            last_best[cam_id] = last_cp
         if "center_az" in last_cp:
            refit_log.append([cam_id, ff, last_cp['center_az'], last_cp['center_el'], last_cp['ra_center'], last_cp['dec_center'], last_cp['position_angle'], last_cp['pixscale'], len(last_cp['cat_image_stars']), last_cp['total_res_px']])
         else:
            print("Refit failed no calibration for ", ff)

            continue

         if last_best[cam_id]['total_res_px'] > last_cp['total_res_px'] : 
            print("LAST/BEST:", last_cp['total_res_px'], last_best[cam_id]['total_res_px'] )
            last_best[cam_id] = last_cp
            print(" *(**** BETTER RES found!")
         print("LAST BEST:", last_best.keys())
      save_json_file(refit_log_file, refit_log)
      print(refit_log_file)
      refit_summary(refit_log)
      #os.system("./recal.py refit_summary " + date )

   def rowwise_adaptive_threshold(self, image_path, in_image=None, block_ratio=0.1, threshold_factor=1.15):
        """
        Applies row-wise adaptive thresholding based on the average brightness of each block.

        Args:
        - image_path (str): Path to the input image or image.
        - block_ratio (float): Ratio of image height for each block.
        - threshold_factor (float): Factor to multiply with average brightness to get threshold.

        Returns:
        - numpy.ndarray: Thresholded image.
        - numpy.ndarray: Original image.
        """
        # Read the image
        if type(image_path) == str and in_image is None:
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        elif in_image is not None:
            image = in_image 
        else:
            # if the image path is actually an image we can use that too
            image = image_path

        show_img = image.copy()
        bad_areas = []

        blurred = cv2.GaussianBlur(image, (3, 3), 0)
        original_image = image.copy()
        height, width = image.shape

        # Calculate block height
        block_height = int(height * block_ratio)

        # Initialize an empty image for the final thresholded result
        thresholded_image = np.zeros_like(blurred)

        # Loop through the image block by block
        for i in range(0, height, block_height):
            # Extract the block
            block = image[i:i+block_height, :]

            # Calculate the average brightness of the block
            avg_brightness = np.mean(block)

            # Compute the threshold for the block
            threshold_value = avg_brightness * threshold_factor

            # Apply the threshold to the block
            _, thresh_block = cv2.threshold(block, threshold_value, 255, cv2.THRESH_BINARY)

            # Remove large contours from the thresh since these won't be stars!
            dilated_image = cv2.dilate(thresh_block, None, iterations=4)
            contours, _ = cv2.findContours(dilated_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            for contour in contours:
                xx, yy, ww, hh= cv2.boundingRect(contour)
                if 15 < ww < 300 or 15 < hh< 300 or yy <= 0 or xx <= 0 or yy>=1075 or xx >= 1915:
                    thresh_block[yy:yy+hh,xx:xx+ww] = 0

            # Assign the thresholded block to the final image
            thresholded_image[i:i+block_height, :] = thresh_block

        # the function should end here and a new function for finding stars should be made

        return(thresholded_image, image)
