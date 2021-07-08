import colorsys
from decimal import Decimal
#import pickle5 as pickle
import glob
import json
import math
import os
import scipy.optimize
import numpy as np
import datetime
import cv2
from sklearn import linear_model, datasets
from skimage.measure import ransac, LineModelND, CircleModel

from sklearn.linear_model import RANSACRegressor
from sklearn.datasets import make_regression

from PIL import ImageFont, ImageDraw, Image, ImageChops

from Classes.DisplayFrame import DisplayFrame
from Classes.Detector import Detector
from Classes.Camera import Camera
from Classes.Event import Event
from Classes.Calibration import Calibration
from lib.PipeAutoCal import XYtoRADec
from lib.PipeVideo import load_frames_simple
from lib.PipeAutoCal import gen_cal_hist,update_center_radec, get_catalog_stars, pair_stars, scan_for_stars, calc_dist, minimize_fov, AzEltoRADec , HMS2deg, distort_xy, XYtoRADec, angularSeparation
from lib.PipeUtil import load_json_file, save_json_file, cfe, convert_filename_to_date_cam,get_trim_num
from lib.FFFuncs import best_crop_size, ffprobe, crop_video, splice_video, lower_bitrate
import boto3
import socket




class Meteor():

   def __init__(self, meteor_file=None, min_file=None,detect_obj=None):

      try:
         import redis
         self.r = redis.Redis(decode_responses=True)
         self.redis_ok = 1
      except:
         print("NO LOCAL REDIS AVAILABLE??")
         os.system("touch /mnt/ams2/noredis.txt")
         self.redis = 0

      self.months = {
        "01": "January",
        "02": "Febuary",
        "03": "March",
        "04": "April",
        "05": "May",
        "06": "June",
        "07": "July",
        "08": "August",
        "09": "September",
        "10": "October",
        "11": "November",
        "12": "December"
      }


      self.show = 0
      self.DF = DisplayFrame()
      self.SCAN_DIR = "/mnt/ams2/METEOR_SCAN/"
      self.SCAN_REPORT_DIR = "/mnt/ams2/METEOR_SCAN/REPORTS/"
      self.sd_frames = None
      self.sd_sub_frames = None


      if cfe(self.SCAN_DIR,1) == 0:
         os.makedirs(self.SCAN_DIR)
      if cfe(self.SCAN_REPORT_DIR,1) == 0:
         os.makedirs(self.SCAN_REPORT_DIR)

      self.scan_period = {}
      self.scan_period['days']= []
      self.scan_period['months']= []
      self.scan_period['years']= []
      temp_months = {}
      temp_years = {}
      # regenerate 1x per day if the current day is not in there or the file time is old
      if cfe(self.SCAN_DIR + "scan_days.json") == 1:
         self.scan_days = load_json_file(self.SCAN_DIR + "scan_days.json")
      else:
         self.scan_days = {}

      if cfe(self.SCAN_DIR + "scan_period.json") == 1:
         self.scan_period = load_json_file(self.SCAN_DIR + "scan_period.json")
      else:
         print("REBUILDING SCAN PERIOD...")
         temp = glob.glob(self.SCAN_DIR + "*") 
         self.scan_days = {}
         for ttt in temp:
            msdir = ttt
            ttt = ttt.split("/")[-1]
            if cfe(msdir,1) == 1 and ttt[0:2] == "20" :
               print(ttt)
               self.scan_period['days'].append(ttt.split("/")[-1]) 
               year = ttt[0:4]
               year_month = ttt[0:7]
               temp_months[year_month] = 1 
               temp_years[year] = 1 
         for year in sorted(temp_years, reverse=True):
            self.scan_period['years'].append(year)
         for month in sorted(temp_months, reverse=True):
            self.scan_period['months'].append(month)
         save_json_file(self.SCAN_DIR + "scan_period.json", self.scan_period)
         print("SCAN PERIOD", self.scan_period)

      self.mfiles = []
      self.all_media_files = None
      self.sync_status = None
      self.meteor_file = meteor_file
      self.json_conf = load_json_file("../conf/as6.json")
      self.station_id = self.json_conf['site']['ams_id']
      self.meteor_training_dir = "/mnt/ams2/datasets/images/training/meteors/"
      self.non_meteor_training_dir = "/mnt/ams2/datasets/images/training/nonmeteors/"
      if self.meteor_file is not None:
         self.red_file = meteor_file.replace(".json", "-reduced.json")
      else:
         self.red_file = None

      if self.meteor_file is not None:
         mfn = self.meteor_file.split("/")[-1]
         self.meteor_dir = "/mnt/ams2/meteors/" + mfn[0:10] + "/" 
         self.vid_fn = mfn.replace(".json", ".mp4")
         self.mj = load_json_file(self.meteor_file)
      if self.red_file is not None:
         if cfe(self.red_file) == 1:
            self.red_data = load_json_file(self.red_file)
         else:
            self.red_data = None
      else:
         self.red_data = None

   def sd_to_hd_roi(self, sd_roi, iw,ih):
      hdm_x = 1920 / iw
      hdm_y = 1080/ ih
      x1,y1,x2,y2 = sd_roi
      hx1 = x1 * hdm_x 
      hy1 = y1 * hdm_y
      hx2 = x2 * hdm_x
      hy2 = y2 * hdm_y

      hw = hx2 - hx1
      hh = hy2 - hy1
      if hw > hh :
         hh = hw
      else:
         hw = hh

      cx = (hx1 + hx2) / 2
      cy = (hy1 + hy2) / 2

      hx1 = int(cx - (hw/2))
      hx2 = int(cx + (hw/2))
      hy1 = int(cy - (hh/2))
      hy2 = int(cy + (hh/2))
      hx1,hy1,hx2,hy2 = self.bound_crop(hx1,hy1,hx2,hy2,1920,1080)
      return(hx1,hy1,hx2,hy2)

   def make_meteor_image_html(self, data):

      sd_vid = data['sd']
      meteor_dir = "/mnt/ams2/meteors/" + sd_vid[0:10] + "/" 
      meteor_scan_dir = "/mnt/ams2/METEOR_SCAN/" + sd_vid[0:10] + "/" 
      root_file = sd_vid.replace(".mp4", "")
      felm = root_file.split("_")
      year = felm[0]
      mon = felm[1]
      dom = felm[2]

      prev_img = sd_vid.replace(".mp4", "-PREV.jpg")
      prev_img = self.station_id + "_" + prev_img
      stack_thumb = sd_vid.replace(".mp4", "-stacked-tn.jpg")

      if "hp" in data:
         edit_color = "green"
      else:
         edit_color = "white"

      if "hc" in data:
         thumb_color = "green"
      else:
         thumb_color = "white"
      if "ev" in data:
         ev = data['ev']
      else:
         ev = None

      icon_html = self.make_icons(self.station_id, sd_vid, thumb_color, edit_color, ev)
   
      meteor_link = "/meteor/" + self.station_id + "/" + sd_vid[0:10] + "/" + sd_vid
      if "meteor_scan_crop_scan" in data:
         if len(data['meteor_scan_crop_scan']) > 0:
            #print(data['meteor_scan_crop_scan'])
            ms_result = 1
      if "roi" not in data:
         ms_result = 0
      else:
         ms_result = 1

      if "hc" in data:
         ms_result = 1

      if ms_result == "good" or str(ms_result) == "1" :
         # use the ROI image
         #print("DATA:", data)
         for key in data:
            print(key)
         for key in data:
            print(key)
         roi = data['roi']
         roi_file = meteor_scan_dir+ self.station_id + "_" + root_file + "-ROI.jpg"
         prev_file = meteor_scan_dir+ self.station_id + "_" + root_file + "-PREV.jpg"
         if cfe(roi_file) == 1:
            img_file = meteor_scan_dir+ self.station_id + "_" + root_file + "-ROI.jpg"
            print("USE ROI:", roi_file)
         else:
            img_file = prev_file
            print("USE PREV:", prev_file)
         iw = 150
         ih = 150
         if cfe(img_file) == 0:
            print("PROBLEM LEARNING THUMB NOT PRESENT!")
            print(img_file)
      else:
         #use the stack thumb
         img_file = meteor_dir + stack_thumb 
         iw = 320
         ih = 180
      rand = datetime.datetime.now().strftime("?%H%M%S")   
      img_url = img_file.replace("/mnt/ams2", "")
      img_url += rand
      # 2020_12_13_07_02_00_000_010005-trim-0314_obj5.jpg
      show_date = mon + "/" + dom
      img_html = """
         
         <div class="meteor_gallery" id="gl_{:s}_{:s}" style="background-color: #000000; background-image: url({:s}); background-repeat: no-repeat; background-size: 100%; width: {:s}px; height: {:s}px; border: 1px #000000 solid; float: left; color: #fcfcfc; margin:5px ">
         <div data-id="{:s}:{:s}" style='width: 100%; height:80%'>{:s}</div><div>{:s}</div></div>
      """.format(str(self.station_id), str(root_file), str(img_url), str(iw), str(ih),self.station_id, root_file, show_date, icon_html )

      print("IMG HTML DONE:", img_html)

      return(img_html)

   def delete_local_meteor(self, sd_video_file, reclass): 
      month = sd_video_file[0:7]
      hd_vid = None
      mfn = sd_video_file.replace(".mp4", ".json")
      mdir = "/mnt/ams2/meteors/" + sd_video_file[0:10] + "/"  
      nonmdir = "/mnt/ams2/nonmeteors/" + sd_video_file[0:10] + "/"  
      lc_dir = "/mnt/ams2/meteors/" + sd_video_file[0:10] + "/cloud_files/"  
      lc_stage_dir = "/mnt/ams2/meteors/" + sd_video_file[0:10] + "/cloud_stage/"  
      if cfe(nonmdir,1) == 0:
         os.makedirs(nonmdir)

      sd_wild = sd_video_file.replace(".mp4",  "*")
      mjf = mdir + sd_video_file.replace(".mp4", ".json")
      if cfe(mjf) == 1:
         try:
            mj = load_json_file(mjf)
            if "hd_trim" in mj:
               hd_vid = mj['hd_trim'].split("/")[-1]
               hd_wild = hd_vid.replace(".mp4", "*")
            mj['meteor_deleted'] = reclass
            save_json_file(mjf, mj)
         except:
            print("JSON FILE IS CORRUPT", mjf)

      # remove the file from redis
      rkey = "M:" + sd_video_file.replace(".mp4", "")
      self.r.delete(rkey)



      # remove the files
      if hd_vid is not None:
         cmd = "rm " + lc_dir + hd_wild
         print(cmd)
         os.system(cmd)
         cmd = "rm " + lc_stage_dir + hd_wild
         print(cmd)
         os.system(cmd)
         cmd = "mv " + mdir + hd_wild + " " + nonmdir
         print(cmd)
         os.system(cmd)



      cmd = "rm " + lc_dir + sd_wild
      print(cmd)
      os.system(cmd)
      cmd = "rm " + lc_stage_dir + sd_wild
      print(cmd)
      os.system(cmd)
      cmd = "mv " + mdir + sd_wild + " " + nonmdir
      print(cmd)
      os.system(cmd)
   
   def get_meteor_media(self, meteor_file):
      root = meteor_file.replace(".json", "")
      ms_dir = "/mnt/ams2/METEOR_SCAN/" + meteor_file[0:10] + "/" + self.station_id + "_" + meteor_file.replace(".json", "*")
      print(ms_dir)
      all_media = []
      med_files = glob.glob(ms_dir)
      for med in med_files:
         fn = med.split("/")[-1]
         ext = fn.replace(self.station_id + "_" + root + "-", "")
         all_media.append(ext)
      return(all_media)

   def mfd_frames_img(self, station_id, sd_video_file, frames, mfd):
      frames_file = "/mnt/ams2/METEOR_SCAN/" + sd_video_file[0:10] + "/" + station_id + "_" + sd_video_file
      frames_img_file = frames_file.replace(".mp4", "-FRMS.jpg")
      print("FF:", frames_img_file)
      total_cells = len(mfd)
      total_cols_per_row = 800 / 20
      total_rows = total_cells / total_cols_per_row
      crop_frames = []
      if total_rows < 1:
         total_rows = 1
      else:
         total_rows = int(total_rows)
      if total_rows == 1:
         frm_h = 20
         frm_w = total_cells * 20 
         frames_img = np.zeros((frm_h,frm_w,3),dtype=np.uint8)

      col = 0
      row = 0
      hdm_x = 1920 / frames[0].shape[1] 
      hdm_y = 1080 / frames[0].shape[0] 
      debug = frames[0]
      for i in range(0, len(mfd)):

         (dt, fn, hd_x, hd_y, w, h, oint, ra, dec, az, el) = mfd[i] 
         frame = frames[fn]
         sd_x = int(hd_x / hdm_x)
         sd_y = int(hd_y / hdm_y)
         x1 = sd_x - 10
         x2 = sd_x + 10
         y1 = sd_y - 10
         y2 = sd_y + 10
         if x1 < 0:
            x1 = 0
            x2 = 20
         if x2 > frame.shape[1]:
            x2 = frame.shape[1]
            x1 = frame.shape[1] - 20
         if y1 < 0:
            y1 = 0
            y2 = 20
         if y2 > frame.shape[0]:
            y2 = frame.shape[0]
            y1 = frame.shape[0] - 20
         x1,y1,x2,y2 = int(x1),int(y1),int(x2),int(y2)
         print("HD/SD:", fn, hd_x, hd_y, sd_x, sd_y)
         #print("X1:", x1, y1, x2, y2)
         crop_frame = frame[y1:y2,x1:x2]
         crop_frame[0:20,10:11] = [128,128,128]
         crop_frame[10:11,0:20] = [128,128,128]
         crop_frame[0:20,0:1] = [255,255,255]
         crop_frame[0:20,19:20] = [255,255,255]
         crop_frame[0:1,0:20] = [255,255,255]
         crop_frame[19:20,0:20] = [255,255,255]
         crop_frames.append(crop_frame)
         cx1 = col * 20
         cy1 = row * 20
         cx2 = cx1 + 20
         cy2 = cy1 + 20
         cv2.rectangle(debug, (int(x1), int(y1)), (int(x2) , int(y2)), (255, 255, 255), 1)
         #print("CX:", cx1,cy1,cx2,cy2)
         #print("CROP:", crop_frame.shape)

         frames_img[cy1:cy2,cx1:cx2] = crop_frame
         col += 1

      print("saving", frames_img_file)
      print("size", frames_img.shape)
      cv2.imwrite(frames_img_file, frames_img) 
      cv2.imwrite("/mnt/ams2/debug.jpg", debug) 



   def make_frames_img(self,final_sd_vid, mj):
      frames_img_file = final_sd_vid.replace("-SD.mp4", "-FRMS.jpg")
      crop_frames = []
      if "meteor_scan_meteors" in mj:
         if len(mj["meteor_scan_meteors"]) > 0:
            fns = mj['meteor_scan_meteors'][0]['ofns']
            xs = mj['meteor_scan_meteors'][0]['oxs']
            ys = mj['meteor_scan_meteors'][0]['oys']
            self.load_frames(mj['sd_video_file']) 
            total_cells = len(fns)
            total_cols_per_row = 800 / 20
            total_rows = total_cells / total_cols_per_row
            if total_rows < 1:
               total_rows = 1
            else:
               total_rows = int(total_rows)
            if total_rows == 1:
               frm_h = 20
               frm_w = total_cells * 20 
               frames_img = np.zeros((frm_h,frm_w,3),dtype=np.uint8)
            else:
               frm_h = 20 * total_rows
               frm_w = 800
               frames_img = np.zeros((frm_h,frm_w,3),dtype=np.uint8)
 
            col = 0
            row = 0
            for i in range(0, len(fns)):
               fn = fns[i]
               frame = self.sd_frames[fn]
               x1 = xs[i] - 10
               x2 = xs[i] + 10
               y1 = ys[i] - 10
               y2 = ys[i] + 10
               if x1 < 0:
                  x1 = 0
                  x2 = 20
               if x2 > frame.shape[1]:
                  x2 = frame.shape[1]
                  x1 = frame.shape[1] - 20
               if y1 < 0:
                  y1 = 0
                  y2 = 20
               if y2 > frame.shape[0]:
                  y2 = frame.shape[0]
                  y1 = frame.shape[0] - 20
               x1,y1,x2,y2 = int(x1),int(y1),int(x2),int(y2)
               crop_frame = frame[y1:y2,x1:x2]
               crop_frame[0:20,10:11] = [128,128,128]
               crop_frame[10:11,0:20] = [128,128,128]
               crop_frame[0:20,0:1] = [255,255,255]
               crop_frame[0:20,19:20] = [255,255,255]
               crop_frame[0:1,0:20] = [255,255,255]
               crop_frame[19:20,0:20] = [255,255,255]
               crop_frames.append(crop_frame)
               print("ROW/COL", row, col)
               cx1 = col * 20
               cy1 = row * 20
               cx2 = cx1 + 20
               cy2 = cy1 + 20
               print("CX:", cx1,cy1,cx2,cy2)
               print("CROP:", crop_frame.shape)

               frames_img[cy1:cy2,cx1:cx2] = crop_frame
               col += 1
               if col >= 800 / 20:
                  col = 0
                  row = 0
            cv2.imwrite(frames_img_file, frames_img)
            print(frames_img_file)
            for cf in crop_frames:
               print(cf.shape)



   def make_final_meteor_vids_pics(self,final_sd_vid, mj):

      meteor_file = final_sd_vid.replace("-SD.mp4", ".json")
      print("Making final meteor vids and pics for", final_sd_vid)
      # this will make the images and SD final splice and then 
      # make the SD ROI so both have the same # of frames
      # before we can run this, we MUST have successfully completed meteor_scan
      # we also must have the ffp info for the original sd video

      if "all_media" not in mj:
         mj['all_media'] = []
      # IMAGE PROCESSING
      # WE NEED: PREV.jpg, ROI.jpg, SD.jpg
      # ROIHD.jpg HD.jpg
      base_file = final_sd_vid.replace("-SD.mp4", "")
      # SAVE SD ROI 
      if "roi" in mj:
         if sum(mj['roi']) > 0:
            x1,y1,x2,y2 = mj['roi']
            x1,y1,x2,y2 = int(x1),int(y1),int(x2),int(y2)  
            mj['roi'] = [x1,y1,x2,y2]
            print(x1,y1,x2,y2)
            roi_img = self.sd_stack[y1:y2,x1:x2]
            cv2.imwrite(base_file + "-ROI.jpg", roi_img, [cv2.IMWRITE_JPEG_QUALITY, 90])
      else:
         print("We can't make an ROI crop.")

      # SAVE SD STACK
      cv2.imwrite(base_file + "-SD.jpg", self.sd_stack,[cv2.IMWRITE_JPEG_QUALITY, 60])

      # MAKE AND SAVE PREV IMG
      prev_img = cv2.resize(self.sd_stack, (320,180))
      cv2.imwrite(base_file + "-PREV.jpg", prev_img,[cv2.IMWRITE_JPEG_QUALITY, 90])

      #frames_img = final_sd_vid.replace(".mp4", "-FRMS.jpg")
      #if cfe(frames_img) == 0 or True:
      #   self.make_frames_img(final_sd_vid, mj)
    
      # SAVE HD STACK AND HD ROI IF POSSIBLE
      if self.hd_stack is not None: 
         cv2.imwrite(base_file + "-HD.jpg", self.hd_stack,[cv2.IMWRITE_JPEG_QUALITY, 60])
         if "roi" in mj:
            if sum(mj['roi']) > 0:
               hx1,hy1,hx2,hy2 = self.sd_to_hd_roi(mj['roi'], self.sd_stack.shape[1], self.sd_stack.shape[0])
               if self.hd_stack.shape[0] != 1080:
                  self.hd_stack = cv2.resize(self.hd_stack, (1920,1080))
               #cv2.imshow('pepe', self.hd_stack)
               #cv2.waitKey(0)
               mj['roi_hd'] = [hx1,hy1,hx2,hy2]
               hd_roi_img = self.hd_stack[hy1:hy2,hx1:hx2]
               print("ROI:", hx1,hy1,hx2,hy2)
               print("SHAPE:", hd_roi_img.shape)
               cv2.imwrite(base_file + "-ROIHD.jpg", hd_roi_img,[cv2.IMWRITE_JPEG_QUALITY, 90])

      # SD VIDEO SPLICE AND CROP
      # we can only do this if meteor scan has run!
      if "meteor_scan_meteors" in mj:
         if type(mj['meteor_scan_meteors']) == dict: 
            mj['meteor_scan_meteors'] = self.dict_to_array(mj['meteor_scan_meteors'])
         if len(mj['meteor_scan_meteors']) > 0:
          
            print("LEN:", len(mj['meteor_scan_meteors']))
            if len( mj['meteor_scan_meteors'][0]['ofns']) > 0:
               start = mj['meteor_scan_meteors'][0]['ofns'][0] - 10
               end = mj['meteor_scan_meteors'][0]['ofns'][-1] + 10
            else:
               if "msc_meteors" in mj:
                  if len(mj['msc_meteors']) > 0:
                     if len( mj['meteor_scan_meteors'][0]['ofns']) > 0:
                        start = mj['msc_meteors'][0]['ofns'][0] - 10
                        end = mj['msc_meteors'][0]['ofns'][-1] + 10

            if "ffp" in mj:
               if 'sd' in mj['ffp']:
                  sd_w,sd_h,sd_bitrate,sd_frames = mj['ffp']['sd']
               else:
                  mj['ffp'] = ffprobe(mj['sd_video_file'])
            else:
               mj['ffp'] = ffprobe(mj['sd_video_file'])
            if start < 0:
               start = 0

            if "final_trim" not in mj:
               mj['final_trim'] = {}
               mj['final_trim']['ffp'] = {}

            if start < 0:
               start = 0
            media_file_name_temp = final_sd_vid.replace(".mp4", "-temp.mp4")
            splice_video(mj['sd_video_file'], start,  end,  media_file_name_temp, "frame")
            os.system("mv " + media_file_name_temp + " " + final_sd_vid)
            lower_bitrate(final_sd_vid, 30)
            if "SD.mp4" not in mj['all_media']:
               mj['all_media'].append("SD.mp4")
            mj['final_trim']['sd'] = [start,end]
            if "ffp" not in mj['final_trim']:
               mj['final_trim']['ffp'] = {}

            mj['final_trim']['ffp']['sd'] = ffprobe(final_sd_vid)
            # The final SD.mp4 should be made now. Next made the ROI.mp4 from this video.
            x1,y1,x2,y2 = mj['roi']
            cw = x2 - x1
            ch = y2 - y1
            crop_box = [x1,y1,cw,ch]
            final_sd_crop_vid = final_sd_vid.replace("-SD.mp4", "-ROI.mp4")
            crop_video(final_sd_vid, final_sd_crop_vid, crop_box) 
            if "ROI.mp4" not in mj['all_media']:
               mj['all_media'].append("ROI.mp4")

      # NOW LETS DO THE SAME THING FOR THE HD FILES BUT ONLY IF THE 
      # HD SCAN HAS ALREADY RUN SUCCESSFULLY
      # RUN THE HD CROP SCAN / HD ROI
      if "meteor_scan_hd_crop_scan" in mj:
         if (type(mj['meteor_scan_hd_crop_scan']) == dict): 
            mj['meteor_scan_hd_crop_scan'] = self.dict_to_array(mj['meteor_scan_hd_crop_scan'])

         if len(mj['meteor_scan_hd_crop_scan']) > 0: 
            if "ofns" in mj['meteor_scan_hd_crop_scan']:
               print("HDCS", mj['meteor_scan_hd_crop_scan'])
               print(type(mj['meteor_scan_hd_crop_scan']))
               start = mj['meteor_scan_hd_crop_scan'][0]['ofns'][0] - 10
               end = mj['meteor_scan_hd_crop_scan'][0]['ofns'][-1] + 10
               if start < 0:
                  start = 0    
               final_hd_vid = final_sd_vid.replace("-SD.mp4", "-HD.mp4")
               media_file_name_temp = final_hd_vid.replace(".mp4", "-temp.mp4")
               splice_video(mj['hd_trim'], start,  end,  media_file_name_temp, "frame")
               os.system("mv " + media_file_name_temp + " " + final_hd_vid)
               lower_bitrate(final_hd_vid, 30)
               mj['final_trim']['hd'] = [start,end]
               mj['final_trim']['ffp']['hd'] = ffprobe(final_hd_vid)
            else:
                #MIKE
                final_hd_vid = None
                if "hd_trim" in mj:
                   if mj['hd_trim'] != 0:
                      if cfe(mj['hd_trim']) == 1:
                         meteors, non_meteors, frame_data = self.meteor_scan_hd_crop(mj['hd_trim'], mj)
                         mj['meteor_scan_hd_crop_scan'] = meteors
                         mj['meteor_scan_hd_crop_scan'] = self.dict_to_array(meteors)
                         if len(mj['meteor_scan_hd_crop_scan']) > 0:
                            start = mj['meteor_scan_hd_crop_scan'][0]['ofns'][0] - 10
                            end = mj['meteor_scan_hd_crop_scan'][0]['ofns'][-1] + 10
                            if start < 5:
                               start = 0
                            final_hd_vid = final_sd_vid.replace("-SD.mp4", "-HD.mp4")
                            media_file_name_temp = final_hd_vid.replace(".mp4", "-temp.mp4")

                            print(meteors)
                            splice_video(mj['hd_trim'], start,  end,  media_file_name_temp, "frame")
                            os.system("mv " + media_file_name_temp + " " + final_hd_vid)
                            lower_bitrate(final_hd_vid, 30)
                            if "final_trim" not in mj:
                               mj['final_trim'] = {}
                               mj['final_trim']['ffp'] = {}
                            mj['final_trim']['hd'] = [start,end]
                            mj['final_trim']['ffp']['hd'] = ffprobe(final_hd_vid)



         if "HD.mp4" not in mj['all_media']:
            mj['all_media'].append("HD.mp4")

         if "roi" in mj:
            hx1,hy1,hx2,hy2 = self.sd_to_hd_roi(mj['roi'], self.sd_stack.shape[1], self.sd_stack.shape[0])
            mj['roi_hd'] = [hx1,hy1,hx2,hy2]
            final_hd_crop_vid = final_sd_vid.replace("-SD.mp4", "-ROIHD.mp4")
            final_hd_vid = final_sd_vid.replace("-SD.mp4", "-HD.mp4")
            if final_hd_vid is not None:
               crop_video(final_hd_vid, final_hd_crop_vid, [hx1,hy1,hx2-hx1,hy2-hy1] )
            else:
               crop_video(mj['hd_trim'], final_hd_crop_vid, [hx1,hy1,hx2-hx1,hy2-hy1] )
            if "ROIHD.mp4" not in mj['all_media']:
               mj['all_media'].append("ROIHD.mp4")

      frames_img = final_sd_vid.replace(".mp4", "-FRMS.jpg")

      if cfe(frames_img) == 0 or True:
         self.make_frames_img(final_sd_vid, mj)
      
      mfn = meteor_file.split("/")[-1]
      print("METEOR FILE IS:", mfn)
      mfn = mfn.replace(self.station_id + "_", "")
      mj['all_media'] = self.get_meteor_media(mfn)
      print(mj['all_media'])
      return(mj)

   def dict_to_array(self,dict_data):
      adata = []
      for key in dict_data:
         print("DICT:", key, dict_data[key])
         if "obj_id" in dict_data[key]:
            adata.append(dict_data[key])
         else:
            for obj_id in dict_data[key]:
               adata.append(dict_data[key][obj_id])

      return(adata)

   def check_fix_cloud_media_for_day(self,day):
      cloud_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + day[0:4] + "/" + day + "/"
      local_dir = "/mnt/ams2/METEOR_SCAN/" + day + "/"
      met_dir = "/mnt/ams2/meteors/" + day + "/cloud_files/"
      self.get_mfiles("/mnt/ams2/meteors/" + day + "/")
      cloud_files = {}
      local_files = {}
      root_files = {}
      good_files = {}
      bad_files = {}

      for mfile in self.mfiles:
         root_file = mfile.replace(".mp4", "")
         root_files[root_file] = {}
      if cfe(local_dir,1) == 0:
         print("No METEOR_SCAN dir for this day.", day)
         return()
 
      cmd = "ls -l " + cloud_dir + "* >" + local_dir + "cloudfiles.txt"
      os.system(cmd)

      cmd = "ls -l " + local_dir + "* >" + local_dir + "localfiles.txt"
      os.system(cmd)
      cmd = "ls -l " + met_dir + "* >>" + local_dir + "localfiles.txt"
      os.system(cmd)

      if cfe(local_dir + "cloudfiles.txt") == 1:
         fp = open(local_dir + "cloudfiles.txt", "r")
      else:
         print("no cloudfiles.txt in " + local_dir)
         return()

      for line in fp:
         if ".meteors" in line or "info" in line or "txt" in line or ".json" in line or ".html" in line:
            continue
         line=line.replace("\n", "")
         elms = line.split()
         cloud_file = elms[8].split("/")[-1]
         cloud_size = elms[4]
         
         ext = cloud_file.split("-")[-1] 
         ext2 = cloud_file.split("-")[-2] 
         if ext2 == 'prev':
            ext = ext2 + "-" + ext
         croot = cloud_file.replace("-" + ext, "")
         croot = croot.replace(self.station_id + "_", "")
         if croot in root_files:
            cloud_files[cloud_file] = int(cloud_size)
         else:
            print(line)
            bad_files[cloud_file] = "No meteor.json for this resource"


      fp = open(local_dir + "localfiles.txt", "r")
      for line in fp:
         if ".meteors" in line or "info" in line or "txt" in line or ".json" in line or ".html" in line:
            continue
         line=line.replace("\n", "")
         elms = line.split()
         local_file = elms[8].split("/")[-1]
         local_size = elms[4]
         
         local_files[local_file] = local_size
      # check that all cloud files exist in the local dir and are the same sizeA
      for cf in cloud_files:
         if cf not in local_files:
            bad_files[cf] = "local file missing" 
         else:
            if int(cloud_files[cf]) != int(local_files[cf]):
               bad_files[cf] = "size mismatch " + str(local_files[cf]) + " != " + str(cloud_files[cf])

            else:
               good_files[cf] = cloud_files[cf]

      # First fix any size mis-matches
      for cf in bad_files:
         print("BAD:", cf, bad_files[cf])
         if "size" in bad_files[cf]:
            local_file = local_dir + cf
            cmd = "cp " + local_file + " " + cloud_dir
            print(cmd)
            os.system(cmd)

      # Next make sure all of the local files exist in the cloud
      # Follow sync level rules! -- 
      # No meteor_scan_detection = LEVEL 1 -- thumb only
      # Meteor Scan Detect = LEVEL 2 -- SD FILES ONLY
      # Human confirm or MS confirm = LEVEL 3 -- ALL FILES
      bad_local_files = {}
      for lf in local_files:
         # ignore types we don't want to upload (anymore)
         root_file, ext = self.get_root_file(lf)
         if root_file not in root_files:
            bad_local_files[lf] = "No meteor.json for this resource"

         if "prev-vid.mp4" in lf or "PREV.jpg" in lf or "txt" in lf or "info" in lf:
            continue


         if lf not in cloud_files:
            if "HD" not in lf and root_file in root_files:
               cmd = "cp " + local_dir + lf + " " + cloud_dir
               print(cmd)
               os.system(cmd)
      # Then make sure there are no 0k files in the local dir. If there are these should
      # be reported in an error report so they can be manually corrected or ignored

   def get_root_file(self, fn):
      print("FN:", fn)
      ext = fn.split("-")[-1] 
      ext2 = fn.split("-")[-2] 
      if ext2 == 'prev':
         ext = ext2 + "-" + ext
      croot = fn.replace("-" + ext, "")
      croot = croot.replace(self.station_id + "_", "")
      return(croot, ext)

   def meteor_status_report(self, meteor_file, force=0):
      mj_changed = 0
      meteor_file = meteor_file.replace(".mp4", ".json")
      root = meteor_file.replace(".json", "")
      root_file = root 
      print("Status report for {:s}".format(meteor_file))
      mdir = "/mnt/ams2/meteors/" + meteor_file[0:10] + "/"
      ms_dir = "/mnt/ams2/METEOR_SCAN/" + meteor_file[0:10] + "/"
      if cfe(ms_dir,1) == 0:
         os.makedirs(ms_dir)
      missing = []
      rkey = "M:" + meteor_file.replace(".json", "")
      if "mp4" in rkey:
         rkey = rkey.replace(".mp4", "")
      root = meteor_file.replace(".json", "")
      rval = self.r.get(rkey)
      if rval is not None and rval != 0 and rval != "0":
         rval = json.loads(rval)
         if "hp" in rval:
            if rval['hp'] == 1:
               print("this meteor has human points and has been review and is good. no more scanning or processing is needed for it. ")
               # but first make sure all the redis data, ffprobe etc is good too.  And that AWS has the latest version of data.
               #return()
      if rval == 0 or rval == "0":
         print("DELETED BAD REDIS KEY!")
         self.r.delete(rkey)
         rval = self.mj_to_redis(root) 
         self.r.set(rkey, json.dumps(rval))

         
      final_media = {}
      print("RKEY:", rkey)
      # needed media files
      # preview image / cropped thumbs
      final_media['prev_img'] = ms_dir + self.station_id + "_" + root + "-PREV.jpg"
      final_media['roi_img'] = ms_dir + self.station_id + "_" + root + "-ROI.jpg"
      final_media['roi_hd_img'] = ms_dir + self.station_id + "_" + root + "-ROIHD.jpg"
      # preview / cropped videos
      final_media['roi_vid'] = ms_dir + self.station_id + "_" + root + "-ROI.mp4"
      final_media['roi_hd_vid'] = ms_dir + self.station_id + "_" + root + "-ROIHD.mp4"
      # SD/HD stack images
      final_media['sd_img'] = ms_dir + self.station_id + "_" + root + "-SD.jpg"
      final_media['hd_img'] = ms_dir + self.station_id + "_" + root + "-HD.jpg"

      # trimmed videod clips
      final_media['sd_vid'] = ms_dir + self.station_id + "_" + root + "-SD.mp4"
      final_media['hd_vid'] = ms_dir + self.station_id + "_" + root + "-HD.mp4"

      mfile = mdir + meteor_file
      mjf = mfile.replace(".mp4", ".json") 
      if cfe(mjf) == 1:
         print("Meteor file good", mjf)
         try:
            mj = load_json_file(mjf)
         except:
            mj = self.remake_mj(root_file)
            print("Loading MJ FAILED!", mfile)
            
            #return(0)
         if cfe(mj['sd_stack']) == 1:
            self.sd_stack = cv2.imread(mj['sd_stack'])
         else:
            self.sd_stack = None
         if cfe(mj['hd_stack']) == 1:
            self.hd_stack = cv2.imread(mj['hd_stack'])
         else:
            self.hd_stack = None



         if cfe(mj['hd_stack']) == 1:
            self.hd_stack = cv2.imread(mj['hd_stack'])
         else:
            self.hd_stack = None
      else:
         print("meteor file not found.", mfile)


      print("ready?")
      rval = self.mj_to_redis(root) 
      print("RVAL:", rkey, rval)
      if rval is not None:
         self.r.set(rkey, json.dumps(rval))
         print("RVAL:", rkey, rval)
         if rval == 0:
            exit() 
         
         print("REDIS SAVING:", rkey)
         for field in rval:
            print("   " + field, rval[field])

      print("RVAL:", rkey, rval)


      # vars we want to see in the json
      # roi, meteor_scan_meteors (ms_meteors), msc_meteors (hd_crop_scan_meteors?)
      # final_trim, ffp
      # all_media
      if "roi" not in mj or sum(mj['roi']) == 0:
         print("THERE IS NO ROI DEFINED!")
         if "meteor_scan_meteors" in mj:
            if len(mj['meteor_scan_meteors']) > 0:
               if "roi" in mj['meteor_scan_meteors'][0]:
                  mj['roi'] = mj['meteor_scan_meteors'][0]['roi']
                  roi = mj['roi']
                  save_json_file(mfile, mj)
       
      if "meteor_scan_meteors" in mj:
         if len(mj["meteor_scan_meteors"]) == 0:
            del mj['meteor_scan_meteors']
      if "msc_meteors" in mj:
         if len(mj["msc_meteors"]) == 0:
            del mj['msc_meteors']
      if "meteor_scan_hd_crop_scan" in mj:
         if len(mj["meteor_scan_hd_crop_scan"]) == 0:
            del mj['meteor_scan_hd_crop_scan']
      if "meteor_scan_meteors" not in mj and "msc_meteors" not in mj or force == 1:
         self.meteor_file = meteor_file
         self.mj = mj
         self.meteor_scan()
         mj['meteor_scan_meteors'] = self.meteor_scan_meteors
         print("METEOR SCAN METEORS", mj['meteor_scan_meteors'])
         missing.append("msc_meteors")
      elif "meteor_scan_meteors" not in mj and "msc_meteors" in mj:
         mj['meteor_scan_meteors'] = mj['msc_meteors']

      print(mj.keys())
      if "run_crop_scan" in mj:
         missing.append("rerun crop scan")

      if "msc_meteors" not in mj or "run_crop_scan" in mj:
         print("CROP SCAN!")
         if "human_roi" in mj:
            x1,y1,x2,y2 = mj['human_roi']
         elif "roi" in mj:
            x1,y1,x2,y2 = mj['roi']
         else:
            mj['roi'] = [0,0,0,0]
            print("ROI IS ZERO!")
         if sum(mj['roi']) > 0:
            x1,y1,x2,y2 = self.bound_crop(x1,y1,x2,y2, self.sd_stack.shape[0],self.sd_stack.shape[1])
            crop_video(mj['sd_video_file'], final_media['roi_vid'], [x1,y1,x2-x1,y2-y1] )
            print("                ************************************ ")
            print("                ************************************ ")
            print("                ************************************ ")
            print("                ************************************ ")
            print("                RECROP METEOR final_media['roi_vid'] ")
            mj['msc_meteors'] = self.meteor_scan_crop(meteor_file)
            print("CROP DONE:", mj['msc_meteors'])
            mj_changed = 1
            for key in mj['msc_meteors']:
   
               print(key, mj['msc_meteors'][key])

         if "msc_meteors" in mj:
            if (type(mj['msc_meteors']) == dict): 
               mj['msc_meteors'] = self.dict_to_array(mj['msc_meteors'])
               if len(mj['msc_meteors']) > 0:
                  start = mj['msc_meteors'][0]['ofns'][0] - 10
                  end = mj['msc_meteors'][0]['ofns'][-1] + 10
                  if start < 0:
                     start = 0
                  media_file_name_temp = final_media['roi_vid'].replace(".mp4", "-temp.mp4")
                  splice_video(final_media['roi_vid'], start,  end,  media_file_name_temp, "frame")
                  os.system("mv " + media_file_name_temp + " " + final_media['roi_vid'])
                  print("RESPLICED", start, end, final_media['roi_vid'])
                  mj_changed = 1
               else:
                  print("NO MSC METEORS!", mj['msc_meteors']) 

           
         # BEFORE WE ARE DONE WE NEED TO TRIM IT TOO
         if "run_crop_scan" in mj:
            

            del (mj['run_crop_scan'])

         
      if "meteor_scan_hd_crop_scan" not in mj or "run_hd_crop_scan" in mj:

         if "roi" in mj:
            hx1,hy1,hx2,hy2 = self.sd_to_hd_roi(mj['roi'], self.sd_stack.shape[1], self.sd_stack.shape[0])
            mj['roi_hd'] = [hx1,hy1,hx2,hy2]
            final_sd_vid = final_media['sd_vid']
            final_hd_crop_vid = final_sd_vid.replace("-SD.mp4", "-ROIHD.mp4")
            if "hd_trim" in mj:
               if mj['hd_trim'] is not None and mj['hd_trim'] != 0:
                  crop_video(mj['hd_trim'], final_hd_crop_vid, [hx1,hy1,hx2-hx1,hy2-hy1] )

            if self.sd_frames is None:
               self.load_frames(mj['sd_video_file'])
            meteors, non_meteors, frame_data = self.meteor_scan_hd_crop(final_hd_crop_vid, mj)

            if "run_hd_crop_scan" in mj:
               del (mj['run_hd_crop_scan'])
            mj['meteor_scan_hd_crop_scan'] = meteors

      else:
         if (type(mj['meteor_scan_hd_crop_scan']) == dict): 
            mj['meteor_scan_hd_crop_scan'] = self.dict_to_array(mj['meteor_scan_hd_crop_scan'])

      if "msc_meteors" not in mj:
         missing.append("msc_meteors")
      else:
         if (type(mj['msc_meteors']) == dict): 
            mj['msc_meteors'] = self.dict_to_array(mj['msc_meteors'])
      if "final_trim" not in mj:
         missing.append("final_trim")
      if "ffp" not in mj:
         missing.append("ffp")
      if "all_media" not in mj:
         missing.append("all_media")
      if len(missing) > 0:
         print("   *** Missing variables in mj:", missing)
      if "all_media" in missing:
         meteor_media = self.get_meteor_media(meteor_file)
         mj['all_media'] = meteor_media
         mj_changed = 1
      else:
         meteor_media = mj['all_media']
      for media in final_media:
         media_file = final_media[media]   #ms_dir + self.station_id + "_" + root + "-" + media
         print("CHECK:", media_file)
         if cfe(media_file) == 0:
            print("MISSING", media_file)
            missing.append("MEDIA:" + media_file)

      # CHECK FOR FINAL TRIM IN MJ
      # IF IT IS NOT THERE OR IF THE SD IS MISSING 
      # RE-TRIM THE SD VID AND CROP THE ROI FROM THE NEW TRIM FILE
      # THIS IS TO ELIMINATE EXCESSIVE FRAMES AT THE START AND END

      print("MISSING:", missing)
      if "final_trim" not in mj or len(missing) > 0:
         print("REMAKE VIDEOS SOMETHING IS MISSING!", missing)
         mj = self.make_final_meteor_vids_pics(final_media['sd_vid'], mj)
         mj_changed = 1

      # RUN THE HD CROP SCAN / HD ROI

      if mj_changed == 1:
         print("saving updated json", mfile)
         save_json_file(mfile, mj)
      if mj_changed == 1 or len(missing) > 0 :
         print("MISSING:", missing)
         print("CHANGED:", mj_changed)
         cmd = "./pushAWS.py push_obs " + meteor_file
         print(cmd)
         os.system(cmd)
         rval = self.mj_to_redis(root) 
         if rval is not None:
            print("REDIS SAVING:", rkey)
            self.r.set(rkey, json.dumps(rval))
      




   def scan_report(self, scan_date, page_num=1,per_page=500):
      print("Scan report for " + scan_date, page_num, per_page)
      row_data = {}
      idx_data = {}
      if scan_date == "today":
         scan_date = datetime.datetime.now().strftime("%Y_%m_%d")   
      good_html = "<div class='container-fluid'>"
      bad_html = "<div class='container-fluid'>"
      conf_html = "<div class='container-fluid'>"
      month = scan_date[0:7]
      deleted_keys = []

      cc_conf = 0
      cc_good = 0
      cc_bad = 0
      print("SCAN DATE IS:", scan_date)
      if len(scan_date) == 7:
         all_redis_keys = self.r.keys("M:" + scan_date[0:8] + "*")
         print("REDIS:", "M:" + scan_date[0:8] + "*")
      else:
         all_redis_keys = self.r.keys("M:" + scan_date + "*")
         print("REDIS:", "M:" + scan_date[0:8] + "*")
      debug_html = ""
      for rkey in sorted(all_redis_keys, reverse=True):
         key = rkey.replace("M:", "") 
         debug_html += key + "<br>"
         mjf = "/mnt/ams2/meteors/" + key[0:10] + "/" + key + ".json" #key.replace(".mp4", ".json")
         if cfe(mjf) == 1:
            print("MJF GOOD:", mjf)
         else:
            print("MJF BAD:", mjf)
            deleted_keys.append(mjf)
            continue
         data = self.r.get(rkey)
         if data is not None:
            if 'sd' not in data:
               self.r.delete(rkey)
               continue
         else:
            continue

         if data is not None:
            data = json.loads(data)
         print("DATA:", data)
         if "ms_meteor" in data: 
            ms_result = data['ms_meteors']
         else:
            ms_result = 0
         if ms_result == 1 or ms_result == "1":
            ms_result = "good"
         ms_meteors = ms_result 
         idx_data[key] = {} 
         idx_data[key]['msm'] = [] 
         i = 0


         if "ms_meteors" in data:
            debug_html += "&nbsp; meteor_scan_meteors yes" + "<br>"
         if "roi" in data:
            idx_data[key]['roi'] = data['roi']
         if "hc" in data:
            data['hc'] = 1 
         if "hd" in data:
            print("DATA:", data['hd'])
            idx_data[key]['hdv'] = data['hd']
         if "calib" in data:
            idx_data[key]['calib'] = data['calib']
         if "hc" in data:
            hc = 1
         else:
            hc = 0
         if "event_id" in data:
            event_id = data['event_id']
         if "event_status" in data:
            if event_id != 0 and event_id != "0":
               event_id += ":" + str(row_data[key]['mj_info']['event_status'])
               idx_data['e'] = event_id

         #print ("{:s}    {:s}    {:s}    {:s}".format(key, str(ms_result),str(ms_meteors),str(ms_non_meteors)))
         img_html = self.make_meteor_image_html(data)
         print("MS RSULT!", ms_result)
         print("HC!", hc)
         if hc == 1:
            conf_html += img_html
            cc_conf += 1

         elif 'roi' in data :
            good_html += img_html
            cc_good += 1
         else:
            bad_html += img_html
            cc_bad += 1

      #for dk in deleted_keys:
      #   del scan_data[dk]
      print("GETTING FOR SCAN DATE:", scan_date)
      month_select = self.make_month_select(scan_date)

     

      date_parts = month.split("_")

      print("IN MONTH:", month)
      print("IN MONTH LEN:", len(month))
      if len(scan_date) == 7:
         month_long = self.months[date_parts[1]]
         year  = date_parts[0]
         date_desc = "the month of " + month_long + ", " + year
         date_val = ""
         print("DATE VAL IS:", date_val)
      else:
         date_desc = " " + scan_date
         date_val = month.replace("_", "-")
         print("DATE VAL IS:", date_val)
      show_scan_date = scan_date.replace("_", "-")
      date_nav_result = "Showing meteor detections for " + date_desc  + "<br>"
      date_nav_result += "<table><tr><td>Select another month </td><td>" + month_select + " </td><td>or a specific day " 
      date_nav_result += "<input id='ms_change_date' class='ms_change_date' type=date value='" + show_scan_date + "'></td></tr></table>"

     
      conf_html += "</div><div style='clear:both'></div>"
      conf_msg = "<table ><tr><td ><h3>Human Confirmed Meteor detections </h2></td></tr></table>"
      good_html += "</div><div style='clear:both'></div>"
      bad_html += "</div><div style='clear:both'></div>"
      #good_msg = "<table ><tr><td ><h3>Detections Classified as Meteors for " + month + "</h2></td><td>" + month_select + "</td></tr></table>"
      good_msg = "<table ><tr><td ><h3>Auto Detections Classified as Meteors for " + month + "</h2></td><td></td></tr></table>"
      good_msg += "<p>if you do not see a meteor in the thumbnail it is either a bad capture or the meteor crop area is missing or wrong.<br>"
      good_msg += "In both cases click the thumbnail to fix the problem </p>"

      bad_msg = "<h3>Uncertain Auto Detections for " + month + "</h3>"
      bad_msg += "<p>Confirm these are bad meteors and they will be removed from the queue. <br>If you see good meteors in this section, human confirm them as meteors and they will move to the meteor confirmed list.</p>"
      if cc_conf == 0:
         conf_msg = "There are no human confirmed meteors. Thumbs up to confirm."
         conf_html = ""
      if cc_good == 0:
         good_msg = ""
         good_html = ""
      if cc_bad == 0:
         bad_msg = ""
         bad_html = ""

      bad_html += debug_html
      all_html = date_nav_result + "<br>" + conf_msg + conf_html + good_msg + good_html + bad_msg + bad_html

      report_file = self.SCAN_REPORT_DIR + self.station_id + "_" + month + "_METEOR_SCAN.html"
      fp = open(report_file, "w")
      fp.write(all_html)
      print("saved ", report_file)
      stats = {}
      return(all_html, idx_data, stats)

   def make_icons(self, station_id, sd_vid, thumb_color="white", edit_color="white", ev=None):
      video_url = "/meteors/" + sd_vid[0:10] + "/" + sd_vid
      ev_icon = ""
      if ev is not None:
         event_id, solve_status = ev.split(":")
         if event_id != "0" and event_id != 0:
            if "SUCCESS" in solve_status:
               ev_color = "green"
            elif "FAIL" in solve_status:
               ev_color = "red"
            else  :
               ev_color = "white"

               #<a class="event_preview" data-id="event_preview:{:s}:" href="javascript:void(0)"><i class="bi bi-diagram-2" style="color: {:s}" data-toggle="popover" title="{:s} {:s}" data-content="Event"></i></a></td><td>""".format(ev, ev_color, event_id, solve_status)
            ev_icon = """
               <a class="event_preview" data-id="event_preview:{:s}" href="javascript:void(0)"><i class="bi bi-diagram-2" style="color: {:s}" data-toggle="popover" title="" data-content="" id="ev_{:s}"></i></a></td><td>
            """.format(event_id, ev_color, event_id)
            

      icon_html = """
         <table ><tr>
         <td><a class="video_link" data-id="video_link:{:s}:{:s}:{:s}" href="javascript:void(0)"><i class="bi bi-caret-right-square" style="color: white" data-toggle="popover" title="Play Video" data-content="SD Video"></i></a></td><td>
         <td><a class="confirm_meteor" data-id="confirm_meteor:{:s}:{:s}" href="javascript:void(0)"><i class="bi bi-hand-thumbs-up" style="color: {:s}" data-toggle="popover" title="Confirm Meteor Detection" data-content="Confirm Meteor Detection" id="cm_{:s}_{:s}"></i></a></td><td>
         <td><a class="meteor_astrometry" data-id="meteor_astrometry:{:s}_{:s}" href="javascript:void(0)">
         <i class="bi bi-stars" style="color: white" title="Review astrometry" data-content="Edit observation data."></i></a></td>
         <td>
         <a class="reduce_meteor" data-id="reduce_meteor:{:s}:{:s}" href="javascript:void(0)"><i class="bi bi-pencil" style="color: {:s}" data-toggle="popover" title="Edit observation data" data-content="Edit observation data."></i></td>
         <td>


      """.format(station_id, sd_vid, video_url,station_id,sd_vid,thumb_color, station_id, sd_vid.replace(".mp4", ""), station_id, sd_vid.replace(".mp4", ""),station_id, sd_vid.replace(".mp4", ""), edit_color)
      icon_html += ev_icon

      icon_trash_html = self.make_trash_icon(station_id, sd_vid)
      icon_html += icon_trash_html + "</td>"
      icon_html += "</tr></table>"
      return(icon_html)

   def update_meteor_scan_record(self, sd_video_file, updates):
      month = sd_video_file[0:7]
      SCAN_FILE = self.SCAN_DIR + self.station_id + "_" + month + "_scan.pickle"
      print ("UPDATE SCAN FILE!", SCAN_FILE)
      if True:
         if cfe(SCAN_FILE) == 1:
            with open(SCAN_FILE, 'rb') as handle:
               scan_data = pickle.load(handle)
            data = scan_data[sd_video_file]
            for key in updates:
               data[key] = updates[key]
            scan_data[key] = data
            with open(SCAN_FILE, 'wb') as handle:
               pickle.dump(scan_data, handle, protocol=pickle.HIGHEST_PROTOCOL)

 
   def human_confirm_meteor(self, sd_video_file):
      mjf = "/mnt/ams2/meteors/" + sd_video_file[0:10] + "/" + sd_video_file.replace(".mp4", ".json")
      if cfe(mjf) == 1:
         mj = load_json_file(mjf)
         mj['hc'] = 1
         save_json_file(mjf, mj)
      rkey = "M:" + sd_video_file.replace(".mp4", "")
      rval = self.r.get(rkey)
      if rval != None:
         rval = json.loads(rval)
         rval['hc'] = 1
         self.r.set(rkey, json.dumps(rval))

   def debug(self, station_id, sd_video_file):
      print("SD V:", sd_video_file)
      mjf = "/mnt/ams2/meteors/" + sd_video_file[0:10] + "/" + sd_video_file.replace(".mp4", ".json")
      mjrf = "/mnt/ams2/meteors/" + sd_video_file[0:10] + "/" + sd_video_file.replace(".mp4", "-reduced.json")
      ms_root = "/mnt/ams2/METEOR_SCAN/" + sd_video_file[0:10] + "/" + station_id + "_" + sd_video_file.replace(".mp4", "")
      roi_file = ms_root + "-ROI.mp4"
      sd_file = ms_root + "-SD.mp4"
      if cfe(mjf) == 1:
         mj = load_json_file(mjf)
      if cfe(mjrf) == 1:
         mjr = load_json_file(mjrf)
      print(mjrf)
      rx1, ry1, rx2, ry2 = mj['roi']
      #sd_frames = load_frames_simple(mj['sd_video_file'])
      print(roi_file)
      sd_frames = load_frames_simple(sd_file)
      roi_frames = load_frames_simple(roi_file)

      if "ffp" in mj:
         sd_w = int(mj['ffp']['sd'][0])
         sd_h = int(mj['ffp']['sd'][1])
         hdm_x = 1920 / sd_w 
         hdm_y = 1080 / sd_h 


      for row in mjr['meteor_frame_data']:
         (dt, ofn, hd_x, hd_y, w, h, oint, ra, dec, az, el) = row
         afn = ofn - mj['final_trim']['sd'][0] - 1
         frame = roi_frames[afn]
         sd_frame = sd_frames[afn]
         sd_x = int(hd_x / hdm_x) 
         sd_y = int(hd_y / hdm_y) 
         sd_rx = sd_x - rx1
         sd_ry = sd_y - ry1
         print("OFN/AFN", rx1, ry1, ofn, afn, sd_rx, sd_ry, sd_x, sd_y)
         cv2.circle(frame,(sd_rx,sd_ry), 1, (0,0,255), 1)
         cv2.circle(sd_frame,(sd_x,sd_y), 1, (0,0,255), 1)
         cv2.putText(frame, str(afn),  (10, 10), cv2.FONT_HERSHEY_SIMPLEX, .4, (200, 200, 200), 1)
         cv2.putText(sd_frame, str(afn),  (10, 10), cv2.FONT_HERSHEY_SIMPLEX, .4, (200, 200, 200), 1)
         cv2.imshow('pepe', frame)
         cv2.imshow('pepe_sd', sd_frame)
         cv2.waitKey(0)
         
      
   

   def save_human_data(self, station_id, sd_video_file, human_data):
      mjf = "/mnt/ams2/meteors/" + sd_video_file[0:10] + "/" + sd_video_file.replace(".mp4", ".json")
      mjrf = "/mnt/ams2/meteors/" + sd_video_file[0:10] + "/" + sd_video_file.replace(".mp4", "-reduced.json")
      (f_datetime, this_cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(sd_video_file)
      event_start_datetime = self.starttime_from_file(sd_video_file)


      mfd = []
      human_points = []
      if cfe(mjf) == 1:
         mj = load_json_file(mjf)
      else:
         return()
      if cfe(mjrf) == 1:
         mjr = load_json_file(mjrf)
      else:
         return()

      sd_frames = load_frames_simple(mj['sd_video_file'])
      trim_start = int(mj['final_trim']['sd'][0])
      img_h, img_w = sd_frames[0].shape[:2]
      mcp_dir = "/mnt/ams2/cal/"
      mcp_file = mcp_dir + "multi_poly-" + station_id + "-" + this_cam + ".info"
      crops = []
      if cfe(mcp_file) == 1:
         mcp = load_json_file(mcp_file)
         mj['cp']['x_poly'] = mcp['x_poly']
         mj['cp']['y_poly'] = mcp['y_poly']
         mj['cp']['x_poly_fwd'] = mcp['x_poly_fwd']
         mj['cp']['y_poly_fwd'] = mcp['y_poly_fwd']


      if "human_roi" in mj:
         roi = mj['human_roi']
      elif "roi" in mj:
         roi = mj['roi']
      rx1,ry1,rx2,ry2 = roi
      if "ffp" in mj:
         if type(mj['ffp']) == list:
            mj['ffp'] = {}
            mj['ffp']['sd'] = ffprobe(mj['sd_video_file'])
            mj['ffp']['hd'] = ffprobe(mj['hd_trim'])
            sd_w = int(mj['ffp']['sd'][0])
            sd_h = int(mj['ffp']['sd'][1])
            hdm_x = 1920 / sd_w 
            hdm_y = 1080 / sd_h 

         elif "sd" in mj['ffp']:

            print("MJ:", mj['ffp'])
            if mj['ffp']['sd'][0] == 0:
               mj['ffp']['sd'] = ffprobe(mj['sd_video_file'])
               mj['ffp']['hd'] = ffprobe(mj['hd_trim'])
            sd_w = int(mj['ffp']['sd'][0])
            sd_h = int(mj['ffp']['sd'][1])

            hdm_x = 1920 / sd_w 
            hdm_y = 1080 / sd_h 
         else:
            mj['ffp'] = {}
            mj['ffp']['sd'] = ffprobe(mj['sd_video_file'])
            mj['ffp']['hd'] = ffprobe(mj['hd_trim'])
            sd_w = int(mj['ffp']['sd'][0])
            sd_h = int(mj['ffp']['sd'][1])
            hdm_x = 1920 / sd_w 
            hdm_y = 1080 / sd_h 
      else:
         hdm_x = 1920 / 704
         hdm_y = 1080 / 576 
      for fn in human_data:
         row = human_data[fn]
         if "hx" in row:
            print("HUMAN:", row['hx'], row['hy'])
            hx = row['hx'] + rx1
            hy = row['hy'] + ry1
            act = row['act']
            print("HUMAN + ROI:", hx, hy)
         elif "px" in row:
            hx = row['px']
            hy = row['py']
            act = "existing"
         ofn = int(fn) + int(trim_start) 
       
         x1 = hx - 12
         x2 = hx + 12
         y1 = hy - 12
         y2 = hy + 12
         x1,y1,x2,y2 = self.bound_crop(x1,y1,x2,y2, img_w,img_h)
         int_crop_bg = sd_frames[0][y1:y2,x1:x2]
         int_crop = sd_frames[ofn][y1:y2,x1:x2]
         int_sub = cv2.subtract(int_crop, int_crop_bg)
         oint = int(np.sum(int_sub))
         w = int_crop.shape[1] 
         h = int_crop.shape[0] 
         hd_x = hx * hdm_x
         hd_y = hy * hdm_y
         extra_sec = int(ofn) / 25
         frame_time = event_start_datetime + datetime.timedelta(0,extra_sec)
         dt = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S.%f")

         tx, ty, ra ,dec , az, el = XYtoRADec(hd_x,hd_y,sd_video_file,mj['cp'],self.json_conf)
         if act != "del":
            print(fn, ofn, hd_x, hd_y, w, h, oint, ra, dec, az, el)
            mfd.append((dt, ofn, hd_x, hd_y, w, h, oint, ra, dec, az, el))
            human_points.append((fn,act,hd_x,hd_y))
      mjr['meteor_frame_data'] = mfd
      mj['human_points'] = human_points
      save_json_file(mjrf, mjr)
      save_json_file(mjf, mj)

      rkey = "M:" + sd_video_file.replace(".mp4", "")
      rval = self.r.get(rkey)
      if rval is not None:
         rval = json.loads(rval)
         rval['hp'] = 1
         self.r.set(rkey, json.dumps(rval))

      cmd = "./pushAWS.py push_obs " + sd_video_file.replace(".mp4", ".json")
      print(cmd)
      os.system(cmd)

      self.mfd_frames_img(station_id, sd_video_file, sd_frames, mfd)
      #for row in mfd:
      #   print(row)

   def update_roi_crop(self, sd_video_file, new_roi):
      # save in the original json file

      # save in pickle db
      # push to aws
      resp = {}
      resp['msg'] = str(sd_video_file) + str(new_roi)
      mjf = "/mnt/ams2/meteors/" + sd_video_file[0:10] + "/" + sd_video_file.replace(".mp4", ".json")
      if cfe(mjf) == 1:


         mj = load_json_file(mjf)
         mfn = mjf.split("/")[-1]
         rkey = "M:" + mfn.replace(".json", "")
         print(rkey)
         rval = self.r.get(rkey)
         if rval is not None:
            rval = json.loads(rval)
         rval['roi'] = new_roi
         rval['human_roi'] = new_roi
         rval['hc'] = 1 
         self.r.set(rkey, json.dumps(rval))

         sd_stack_file = sd_video_file.replace(".mp4", "-stacked.jpg")
         sd_sfile = "/mnt/ams2/meteors/" + sd_video_file[0:10] + "/" + sd_stack_file
         print("SD STACK FILE?", sd_sfile)
         roi_file = sd_video_file.replace(".mp4", "-ROI.jpg")
         sd_img = cv2.imread(sd_sfile)
         x1,y1,x2,y2 = new_roi
         x1 = int(x1)
         y1 = int(y1)
         x2 = int(x2)
         y2 = int(y2)
         print(sd_img.shape)
         print(new_roi)
         img_h,img_w = sd_img.shape[0:2]
         x1,y1,x2,y2 = self.bound_crop(x1,y1,x2,y2, img_w,img_h)

         mj['hc'] = 1
         mj['roi'] = new_roi
         mj['human_roi'] = new_roi
         mj['run_crop_scan'] = 1
         mj['run_hd_crop_scan'] = 1
         print("saved ", mjf)
         save_json_file(mjf, mj)

         roi_img = sd_img[y1:y2,x1:x2]
         print("saving /mnt/ams2/meteors/" + sd_video_file[0:10] + "/" + roi_file)
         print("saving /mnt/ams2/METEOR_SCAN/" + sd_video_file[0:10] + "/" + roi_file)
         cv2.imwrite("/mnt/ams2/meteors/" + sd_video_file[0:10] + "/" + roi_file, roi_img,[cv2.IMWRITE_JPEG_QUALITY, 70])
         cv2.imwrite("/mnt/ams2/METEOR_SCAN/" + sd_video_file[0:10] + "/" + self.station_id + "_" + roi_file, roi_img,[cv2.IMWRITE_JPEG_QUALITY, 70])
         cv2.imwrite("/mnt/ams2/datasets/images/training/meteors/" + roi_file, roi_img, [cv2.IMWRITE_JPEG_QUALITY, 70])
         year = sd_video_file[0:4]
         day = sd_video_file[0:10]
         cloud_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + year + "/" + day + "/" 
         os.system("cp /mnt/ams2/meteors/" + sd_video_file[0:10] + "/" + roi_file + " " + cloud_dir)
         print("/mnt/ams2/datasets/images/training/meteors/" + "/" + roi_file)
         print("cp /mnt/ams2/meteors/" + sd_video_file[0:10] + "/" + roi_file + " " + cloud_dir)
         cmd = "/usr/bin/python3 Meteor.py 3 " + sd_video_file.replace(".mp4", ".json")
         print(cmd)
         os.system(cmd)


      return(resp)



   def make_month_select(self,select_month):
      options = ""
      mon_hist = {}
      #pick_files = ['2021_06_01']
      print("PER", self.scan_period)
      for month in sorted(self.scan_period['months'], reverse=True):
         el = month.split("_")
         year = el[0]
         mon = el[1]
         #month = year + "_" + mon
         options += '<li> <a data-id="goto_month:' + month + '" class="dropdown-item" href="javascript:void(0)">' + month + '</a></li>'
      month_select_icon = """ <i class="bi bi-calendar" style="font-size: 25px; color: #000000"; data-toggle="popover" title="Select Date" data-content="Select Date" data-id="{:s}"></i>""".format("month_select" ) 
      #month_select_icon = select_month

      month_select_link = '<div class="dropdown" id="MonthDropdown">'
      month_select_link += '<button style="font-size: 20px; background-color: Transparent; border: None" class="btn btn-secondary dropdown-toggle" type="button" id="dropdownMenuButton1" data-bs-toggle="dropdown" aria-expanded="false">' + month_select_icon + "</button>"
      month_select_link += '<ul id="select_month" class="dropdown-menu" aria-labelledby="dropdownMenuButton1" data-id="select_month:' + month + '">'
      month_select_html = month_select_link + options + "</ul></div>"
      return(month_select_html)

   def make_trash_icon(self, station_id, sd_vid):
      size = 12
      icon_trash = """<i class="bi bi-trash" style="font-size: {:s}px; color: {:s}"; data-toggle="popover" title="Re-classify non-meteor detection" data-content="Trash" data-id="trash:{:s}:{:s}"></i>""".format(str(12), str("#ffffff"), station_id, sd_vid) 

      icon_trash_obs_link = '<div class="dropdown" id="myDropdown">'
      icon_trash_obs_link += '<button style="font-size: 10px; background-color: Transparent; border: None" class="btn btn-secondary dropdown-toggle" type="button" id="dropdownMenuButton1" data-bs-toggle="dropdown" aria-expanded="false">' + icon_trash + "</button>"
      icon_trash_obs_link += '<ul class="dropdown-menu" aria-labelledby="dropdownMenuButton1" data-id="trash:' + station_id + ":" + sd_vid + '">'
      key =  station_id + ":" + sd_vid
      icon_trash_obs_link += '<li><a data-id="delete_meteor:' + key + ':clouds" class="dropdown-item" href="javascript:void(0)">Clouds</a></li>'
      icon_trash_obs_link += '<li><a data-id="delete_meteor:' + key + ':plane" class="dropdown-item" href="javascript:void(0)">Plane</a></li>'
      icon_trash_obs_link += '<li><a data-id="delete_meteor:' + key + ':bird" class="dropdown-item" href="javascript:void(0)">Bird</a></li>'
      icon_trash_obs_link += '<li><a data-id="delete_meteor:' + key + ':trees" class="dropdown-item" href="javascript:void(0)">Trees</a></li>'
      icon_trash_obs_link += '<li><a data-id="delete_meteor:' + key + ':firefly" class="dropdown-item" href="javascript:void(0)">Firefly</a></li>'
      icon_trash_obs_link += '<li><a data-id="delete_meteor:' + key + ':trees" class="dropdown-item" href="javascript:void(0)">Trees</a></li>'
      icon_trash_obs_link += '<li><a data-id="delete_meteor:' + key + ':moon" class="dropdown-item" href="javascript:void(0)">Moon</a></li>'
      icon_trash_obs_link += '<li><a data-id="delete_meteor:' + key + ':sat" class="dropdown-item" href="javascript:void(0)">Satellite</a></li>'
      icon_trash_obs_link += '<li><a data-id="delete_meteor:' + key + ':car_lights" class="dropdown-item" href="javascript:void(0)">Car Lights</a></li>'
      icon_trash_obs_link += '<li><a data-id="delete_meteor:' + key + ':rain_drops" class="dropdown-item" href="javascript:void(0)">Rain</a></li>'
      icon_trash_obs_link += '<li><a data-id="delete_meteor:' + key + ':snow" class="dropdown-item" href="javascript:void(0)">Snow</a></li>'
      icon_trash_obs_link += '<li><a data-id="delete_meteor:' + key + ':smoke_chimney" class="dropdown-item" href="javascript:void(0)">Smoke/Chimney</a></li>'
      icon_trash_obs_link += '<li><a data-id="delete_meteor:' + key + ':noise" class="dropdown-item" href="javascript:void(0)">Noise</a></li>'
      icon_trash_obs_link += '<li><a data-id="delete_meteor:' + key + ':other" class="dropdown-item" href="javascript:void(0)">Other Non Meteor</a></li>'
      icon_trash_obs_link += '</ul></div>'
      return(icon_trash_obs_link)

   def bound_crop(self,x1,y1,x2,y2,img_w,img_h):
      cw = x2 - x1
      ch = y2 - y1
      if cw > ch:
         ch = cw
      else:
         cw = ch
      if ch > 1080:
         ch = 1070
         cw = 1070
      if x1 < 0 or x2 < 0:
         x1 = 0 
         x2 = x1 + cw
      elif x2 > img_w or x1 > img_w:
         x2 = img_w - 1
         x1 = x2 - cw
      if y1 < 0 or y2 < 0:
         y1 = 0 
         y2 = y1 + ch
      elif y2 > img_h or y1 > img_h:
         y2 = img_h - 1
         y1 = y2 - ch
      return(int(x1),int(y1),int(x2),int(y2))

   def meteor_scan_hd_crop(self, crop_file, mj):
      crop_scale = 1
      self.load_frames(crop_file) 
      fn = 0
      frame_data = {}
      objects = {}
      for frame in self.sd_sub_frames:
         val = np.mean(frame)
         val = val * 3
         if val < 70:
            val = 70
         gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         _, thresh = cv2.threshold(gray_frame.copy(), val, 255, cv2.THRESH_BINARY)
         cnts = self.get_contours_simple(thresh)
         frame_data[fn] = {}
         frame_data[fn]['cnts'] = []
         for cnt in cnts:
            
            x,y,w,h,intensity,avg_px = cnt
            cx = int(x + (w/2))
            cy = int(y + (h/2))
            frame_data[fn]['cnts'].append(cnt)
            oid, objects = Detector.find_objects(fn,x,y,w,h,cx,cy,intensity,objects, 50 * crop_scale) 
          
         #cv2.imshow('pepe', thresh)
         #cv2.waitKey(30)
         fn += 1
      meteors = {}
      non_meteors = {}

      final_meteors = []
      for oid in objects:
         status, report = Detector.analyze_object(objects[oid])
         objects[oid]['report'] = report
         print(oid, objects[oid]['report']['class'] , objects[oid]['report']['bad_items'])
         if objects[oid]['report']['class'] == "meteor":
             meteors[oid] = objects[oid]
             final_meteors.append(objects[oid]) 
         else:
             non_meteors[oid] = objects[oid]

      #for fn in frame_data:
      #   print (fn, frame_data[fn])
      return(meteors, non_meteors, frame_data)

   def meteor_scan_crop(self, mjf):
      if "/" not in mjf:
         mjf = "/mnt/ams2/meteors/" + mjf[0:10] + "/" + mjf
      if cfe(mjf) == 0:
         return({})
      mj = load_json_file(mjf)
      if "sd_video_file" in mj:
         self.load_frames(mj['sd_video_file'])
         if len(self.sd_frames) == 0:
            print("FRAME ARE 0 CAN'T SCAN!")
            return(0)
      else:
         print("NO VIDEO FILE!")
         retun()
      if "human_roi" in mj:
         self.roi = mj['human_roi']
      elif "roi" in mj:
         self.roi = mj['roi']
      crop_frames = []
      big_crop_frames = []
      median_mask = None
      img_h,img_w = self.sd_frames[0].shape[:2]
      frame_data = {}
      fn = 0
      all_xs = []
      all_ys = []
      all_cnts = []
      # block out stars first!
      x1,y1,x2,y2 = self.roi
      x1,y1,x2,y2 = self.bound_crop(x1,y1,x2,y2, img_w,img_h)
      crop_x1 = x1
      crop_y1 = y1
      mask_img = self.sd_frames[0][y1:y2,x1:x2]
      try:
         mask_img = cv2.cvtColor(mask_img, cv2.COLOR_BGR2GRAY)
      except:
         print(mjf)
         print("COULD NOT MAKE MASK!")
         print(y1,y2,x1,x2)
         return({})

      crop_w = x2 - x1
      crop_h = y2 - y1
      if crop_w < 800:
         crop_scale = int(800 / crop_w)
      else:
         crop_scale = 1
      big_w = crop_w * crop_scale
      big_h = crop_h * crop_scale
      mask_img = cv2.resize(mask_img, (big_w,big_h))

      val = np.mean(mask_img)
      val = val * 1.3

      _, mask_thresh = cv2.threshold(mask_img.copy(), val, 255, cv2.THRESH_BINARY)
      cnts = self.get_contours_simple(mask_thresh)
      for cnt in cnts:
         x,y,w,h,intensity,avg_px = cnt
         print("CNT:", cnt)
         all_cnts.append((x,y,w,h))

      print("FRAMES:", len(self.sd_frames))
      for frame in self.sd_frames:
         frame_data[fn] = {}
         frame_data[fn]['cnts'] = []
         crop_frame = frame[y1:y2,x1:x2]
         if crop_w < 800:
            big_w = crop_w * crop_scale
            big_h = crop_h * crop_scale
            big_crop = cv2.resize(crop_frame, (big_w,big_h))
         else:
            crop_scale = 1
            big_crop = crop_frame
         if 3 <= len(big_crop_frames) < 5:
            median_mask = cv2.convertScaleAbs(np.mean(np.array(big_crop_frames), axis=0))
         elif len(big_crop_frames) < 3:
            median_mask = big_crop

         big_crop_sub = cv2.subtract(big_crop, median_mask)
         big_crop_sub= cv2.cvtColor(big_crop_sub, cv2.COLOR_BGR2GRAY)
         big_crop_sub = cv2.subtract(big_crop_sub,mask_thresh)

         cnts = self.get_contours_in_crop(big_crop_sub, all_cnts)
         show_crop_org = big_crop.copy()
         show_crop = big_crop.copy()
         for cnt in cnts:
            x,y,w,h,intensity,avg_px = cnt
            all_cnts.append((x,y,w,h))
            cx = x + int(w/2)
            cy = y + int(h/2)
            all_xs.append(cx)
            all_ys.append(cy)
            cnt_save = [fn,x,y,w,h,cx,cy,intensity,avg_px]
            frame_data[fn]['cnts'].append(cnt_save)
            cv2.rectangle(show_crop, (int(x), int(y)), (int(x+w) , int(y+h)), (255, 255, 255), 1)
         print(fn, cnts)

         crop_frames.append(crop_frame) 
         big_crop_frames.append(big_crop) 

         for x,y,w,h in all_cnts[:-1]:
            show_crop[y:y+h,x:x+w] = [0,0,0]

         mask_img_color = cv2.cvtColor(mask_thresh, cv2.COLOR_GRAY2BGR)
         if self.show == 1:
            show_crop= cv2.subtract(show_crop,mask_img_color)
            cv2.putText(show_crop, str(crop_scale) + "x",  (10, 10), cv2.FONT_HERSHEY_SIMPLEX, .3, (200, 200, 200), 1)
            cv2.imshow('crop', show_crop)
            cv2.imshow('sub', big_crop_sub)

            # cv2.imshow('mask', mask_thresh)

            if len(cnts) > 0:
               cv2.waitKey(30)
            else:
               cv2.waitKey(1)
         fn += 1
      objects = {}
      dist_from_last = 0
      fc = 0
      first_x = None
      first_y = None
      dist_from_start = 0
      for fn in frame_data:
         if len(frame_data[fn]['cnts']) == 1:
            
            (fn,x,y,w,h,cx,cy,intensity, avg_px) = frame_data[fn]['cnts'][0] 
            if first_x is not None:
               dist_from_start = calc_dist((first_x,first_y),(cx,cy))

            oid, objects = Detector.find_objects(fn,x,y,w,h,cx,cy,intensity,objects, 25 * crop_scale) 
            #if dist_from_start > last_dist_from_start or last_dist_from_start == 0:
            #   print(fn, "   *** FRAME DATA", fn, cx,cy,intensity,avg_px, dist_from_start)
            #else:
            #   print(fn, "   *** REJECT FRAME DATA", fn, cx,cy,intensity,avg_px, dist_from_start)
         elif len(frame_data[fn]['cnts']) > 1:
            # merge / the cnts
            frame_data[fn]['cnts'] = self.merge_clean_cnts(frame_data[fn]['cnts'])
            if fc > 1:
               for cnt in frame_data[fn]['cnts']:
                  (fn,x,y,w,h,cx,cy,intensity, avg_px) = cnt
                  if first_x is not None:
                     dist_from_start = calc_dist((first_x,first_y),(cx,cy))
                  oid , objects = Detector.find_objects(fn,x,y,w,h,cx,cy,intensity,objects, 25 * crop_scale) 
                  #if dist_from_start > last_dist_from_start or last_dist_from_start == 0 and first_x is not None:
                  #   print(fn, "   *** FRAME DATA", first_x, first_y, fn, cx,cy,intensity,avg_px, dist_from_start)
                  #else:
                  #   print(fn, "   *** REJECT FRAME DATA", first_x, first_y, fn, cx,cy,intensity,avg_px, dist_from_start)
         if first_x is None and len(frame_data[fn]['cnts']) > 0 and len(frame_data[fn+1]['cnts']) > 0:
            #print("FIRST FRAME SET!", cx,cy)
            first_x = cx
            first_y = cy
         else:
            last_dist_from_start = dist_from_start
         fc += 1
            
         

         fc += 1
      good_objs = {}
      bad_objs = {}
      for obj_id in objects:
         status, report = Detector.analyze_object(objects[obj_id])
         objects[obj_id]['report'] = report
         if len(objects[obj_id]['ofns']) < 3:
            bad_objs[obj_id] = objects[obj_id]
            continue
         good_objs[obj_id] = objects[obj_id]
      objects = good_objs


      new_show = show_crop_org.copy()
      for obj_id in objects:
         status, report = Detector.analyze_object(objects[obj_id])
         objects[obj_id]['report'] = report

         ic = 0
         first_x = None
         last_x = None
         seg_len = 0
         dist_from_start = 0
         last_dist_from_start = 0
         objects[obj_id]['dist_from_start'] = []
         objects[obj_id]['seg_len'] = []
         for i in range(0,len(objects[obj_id]['ofns'])):
            fn = objects[obj_id]['ofns'][i]
            x = objects[obj_id]['oxs'][i]
            y = objects[obj_id]['oys'][i]
            w = objects[obj_id]['ows'][i]
            h = objects[obj_id]['ohs'][i]
            cx = x + (w/2)
            cy = y + (h/2)
            if first_x is None :
               first_x = cx
               first_y = cy
               dist_from_start = 0
               last_dist_from_start = 0
               objects[obj_id]['dist_from_start'].append(0)
               objects[obj_id]['seg_len'].append(0)
               
            else:
               dist_from_start = calc_dist((first_x,first_y),(cx,cy))
               seg_len = dist_from_start - last_dist_from_start 
               objects[obj_id]['dist_from_start'].append(dist_from_start)
               objects[obj_id]['seg_len'].append(seg_len)
               

            ic += 1
            last_x = cx
            last_y = cy
            last_dist_from_start = dist_from_start

         end_found = 0
         while end_found == 0:
            len_fns = len(objects[obj_id]['ofns']) -1
            last_item = len(objects[obj_id]['ofns']) -1
            last_seg_len = objects[obj_id]['seg_len'][last_item]

            if last_item - 1 < len(objects[obj_id]['ofns']) + 1:
               last_seg_len2 = objects[obj_id]['seg_len'][last_item-1]
            else:
               last_seg_len2 = 3
            #print("LAST SEG2", last_item, len(objects[obj_id]['ofns']), last_seg_len2, last_seg_len)
            if (last_seg_len < 0 and last_item <= len(objects[obj_id]['ofns'])-1) or last_seg_len2 < 0:
               #print("DELETE LAST FRAME!!!", last_seg_len, last_seg_len2)
               if True:
                  del (objects[obj_id]['ofns'][last_item])
                  del (objects[obj_id]['oxs'][last_item])
                  del (objects[obj_id]['oys'][last_item])
                  del (objects[obj_id]['ows'][last_item])
                  del (objects[obj_id]['ohs'][last_item])
                  del (objects[obj_id]['ccxs'][last_item])
                  del (objects[obj_id]['ccys'][last_item])
                  del (objects[obj_id]['oint'][last_item])
                  del (objects[obj_id]['seg_len'][last_item])
                  del (objects[obj_id]['dist_from_start'][last_item])
            else:
               end_found = 1


      # FINAL OBJ HERE ALL SHOULD BE GOOD. ELSE IT WILL NEED MANUAL REDUCE!
      ic = 0
      final_objects = {}
      for obj_id in objects:
         status, report = Detector.analyze_object(objects[obj_id])
         objects[obj_id]['report'] = report
         final_objects[obj_id] = {}
         final_objects[obj_id]['obj_id'] = obj_id
         final_objects[obj_id]['ofns'] = []
         final_objects[obj_id]['oxs'] = []
         final_objects[obj_id]['oys'] = []
         final_objects[obj_id]['ows'] = []
         final_objects[obj_id]['ohs'] = []
         final_objects[obj_id]['oint'] = []
         final_objects[obj_id]['ccxs'] = []
         final_objects[obj_id]['ccys'] = []
         final_objects[obj_id]['rgb'] = []
         final_objects[obj_id]['dist_from_start'] = []
         final_objects[obj_id]['seg_len'] = []
         for i in range(0,len(objects[obj_id]['ofns'])):
            fn = objects[obj_id]['ofns'][i]
            x = objects[obj_id]['oxs'][i]
            y = objects[obj_id]['oys'][i]
            w = objects[obj_id]['ows'][i]
            h = objects[obj_id]['ohs'][i]
            oint = objects[obj_id]['oint'][i]
            dfs = objects[obj_id]['dist_from_start'][i]
            sgl  = objects[obj_id]['seg_len'][i]
            cx = x + (w/2)
            cy = y + (h/2)

            final_objects[obj_id]['ofns'].append(fn)
            final_objects[obj_id]['oxs'].append((x/crop_scale) + crop_x1)
            final_objects[obj_id]['oys'].append((y/crop_scale) + crop_y1)
            final_objects[obj_id]['ows'].append((w/crop_scale))
            final_objects[obj_id]['ohs'].append((h/crop_scale))
            final_objects[obj_id]['ccxs'].append(   ((x/crop_scale) + crop_x1) + ((w/crop_scale)/2)    ) 
            final_objects[obj_id]['ccys'].append(   ((y/crop_scale) + crop_y1) + ((h/crop_scale)/2) ) 
            final_objects[obj_id]['oint'].append((oint/crop_scale)) 
            final_objects[obj_id]['dist_from_start'].append((dfs/crop_scale))
            final_objects[obj_id]['seg_len'].append((seg_len/crop_scale))
            rgb_val = []
            cli = i / len(objects[obj_id]['ofns'])
            color = self.get_color(cli)
            for ccc in color:
               rgb_val.append(ccc)
            final_objects[obj_id]['rgb'].append(rgb_val)
            cv2.putText(new_show, str(ic),  (x, y), cv2.FONT_HERSHEY_SIMPLEX, .3, (rgb_val), 1)
            cv2.rectangle(new_show, (int(x), int(y)), (int(x+w) , int(y+h)), rgb_val, 1)
            ic += 1

      if self.show == 1:
         cv2.imshow('final', new_show)
         cv2.waitKey(30)
      bad_objs = []
      for obj in final_objects :
         if len(final_objects[obj]['ofns']) < 3:
            print("BAD OBJ:", obj)
            bad_objs.append(obj)
            continue
         #print("OBJID:", obj)
         #print("FINAL OBJECT:", final_objects[obj]['oxs'], final_objects[obj]['oys'])
         status, report = Detector.analyze_object(final_objects[obj])
         final_objects[obj]['report'] = report
         try:
            ransac_result = self.ransac_outliers(final_objects[obj]['ccxs'],final_objects[obj]['ccys'],"RANSAC ON CROP POINTS")
            final_objects[obj]['ransac'] = ransac_result
         except:
            print("THIS OBJECT IS BAD RANSAC FAILED!", final_objects)
            ransac_result = 0
            final_objects[obj]['ransac'] = ransac_result

      for bad_obj in bad_objs:
         print("DELETE BAD OBJ:")
         del final_objects[bad_obj]
      return(final_objects)
      #ransac_result = self.ransac_outliers(all_xs,all_ys,"RANSAC ON CROP POINTS")


   def merge_clean_cnts(self, cnts):
      # sort by cnt size
      cnts = sorted(cnts, key=lambda x: x[2]*x[3], reverse=True)  
      new_cnts = []
      unknown_cnts = []
      bx,by,bw,bh = cnts[0][0:4]
      bcx = bx + (bw/2) 
      bcy = by + (bh/2) 
      for cnt in cnts[1:]:
         cx,cy,cw,ch = cnt[0:4]
         ccx = cx + (cw/2) 
         ccy = cy + (ch/2) 
         dist_to_large = calc_dist((bcx,bcy),(ccx,ccy))
         min_dist = self.calc_min_dist(cnts[0],cnt)
         if (bw*bh) == 0:
            continue
         perc_big = (cw*ch)/(bw*bh)
         if False:
         #if perc_big < .5 and min_dist < 10:
            if ccx < bx:
               bx = ccx
            if ccx+cw> bx+bw:
               bw = (bx + cw ) - bx
            if ccy < by:
               by = ccy
            if ccy+ch> by+bh:
               bh = (by + bh + ch) - by
      cnts[0][0] = bx
      cnts[0][1] = by
      cnts[0][2] = bw
      cnts[0][3] = bh
      new_cnts.append((cnts[0]))
      return(new_cnts)

   def calc_min_dist(self,cnt_a,cnt_b):
      x1,y1,w,h = cnt_a[0:4]
      x2 = x1 + w
      y2 = y1 + h
      xx1,yy1,ww,hh = cnt_b[0:4]
      xx2 = xx1 + ww
      yy2 = yy1 + hh

      ass = [ [x1,y1], [x1,y2], [x2,y1], [x2,y2]]
      bass = [ [xx1,yy1], [xx1,yy2], [xx2,yy1], [xx2,yy2]]
      min_ds = []
      for a in ass:
         for b in bass:
            min_d = calc_dist(a,b)
            min_ds.append(min_d)
      min_dist = min(min_ds)
      return(min_dist)


   def get_color(self, red_to_green):
      assert 0 <= red_to_green <= 1
      # in HSV, red is 0 deg and green is 120 deg (out of 360);
      # divide red_to_green with 3 to map [0, 1] to [0, 1./3.]
      hue = red_to_green / 3.0
      r, g, b = colorsys.hsv_to_rgb(hue, 1, 1)
      return map(lambda x: int(255 * x), (r, g, b))

   def sync_media_day(self, day):
      local_dir = "/mnt/ams2/METEOR_SCAN/" + day + "/"
      cloud_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + day + "/"

      if cfe(cloud_dir, 1) == 0:
         print(cloud_dir)
         os.makedirs(cloud_dir)
      cmd = "ls -l " + cloud_dir + " > " + local_dir + "cloudfiles.txt"
      os.system(cmd)
      fp = open(local_dir + "cloudfiles.txt")
      for line in fp:
         print(line)

      local_files = glob.glob(local_dir + "*")
      for local_file in local_files:
         print(local_file)
         # we should only push the ALL media IF the meteor is a multi-station detection, or human confirmed
         # otherwise, only the thumbs / minimal info should be pushed
         cmd = "cp " + local_file + " " + cloud_dir
         print(cmd)
         os.system(cmd)

      #cmd = "rsync -auv " + local_dir + "*" + " " + cloud_dir
      #print(cmd)
      #os.system(cmd)

   def update_events_obs(self): 
      print("update events obs ")
      events_cloud_file= "/mnt/archive.allsky.tv/EVENTS/STATIONS/ALL_EVENTS_" + self.station_id + ".json.gz"
      events_local_file= "/mnt/ams2/EVENTS/ALL_EVENTS_" + self.station_id + ".json.gz"
      #if cfe(events_local_file) == 1:
      #   return() 
      if cfe("/mnt/ams2/EVENTS/",1) == 0:
         os.makedirs("/mnt/ams2/EVENTS")
      cmd = "cp " + events_cloud_file + " " + events_local_file
      os.system(cmd)
      cmd = "gunzip -f " + events_local_file
      os.system(cmd)
      all_events = load_json_file(events_local_file.replace(".gz", ""))
      print("ALL EVENTS FILE:", events_local_file)

      for ev in all_events['events']:
         obs_file, event_id, status = ev.split(":")
         print("OBS FILE IS:", obs_file)
         if str(status) == "0":
            status = "UNSOLVED"
         elif "missing" in status:
            status = "WMPL FAILED"
         mf = "/mnt/ams2/meteors/" + obs_file[0:10] + "/" + obs_file.replace(".mp4", ".json")
         if cfe(mf) == 1:
            rkey = "M:" + obs_file.replace(".mp4", "")
            print("RKEY IS:", rkey)
            print("MF IS:", mf)
            rval = self.r.get(rkey)
            if rval is not None:
               rval = json.loads(rval)
               rval["ev"] = event_id + ":" + status
               self.r.set(rkey, json.dumps(rval))
               print("UPDATE RED:", rkey, rval)
         else:
            print("THIS OBS NO LONGER EXISTS!?", event_id, mf)
            print("DELETEING:", rkey)
            #self.r.delete(rkey)

   def load_all_meteors_into_redis(self, day=None):
      self.update_events_obs()
      in_day = day
      self.all_meteors = {}
      self.meteor_dirs = []
      self.meteor_days = {}
      # get existing redis keys for time period or all if no day passed in
      mdd = sorted(glob.glob("/mnt/ams2/meteors/*"),reverse=True)
      if day is None:
         self.all_redis_keys = self.r.keys("M:*")
      else:
         self.all_redis_keys = self.r.keys("M:*" + day + "*")
         mdd = ["/mnt/ams2/meteors/" + day ]


      print("LOADING:", day)
      print("MDD:", mdd)
      # for each day get the local json meteor files
      for md in mdd:
         day = md.split("/")[-1]
         year = day[0:4]
         print("ZZZDAY:", day)
         if day not in self.meteor_days:
            self.meteor_days[day] = {}
            self.meteor_days[day]['meteors'] = []
         
         if cfe(md,1) == 1:
            self.meteor_dirs.append(md)
            self.mfiles = []
            self.get_mfiles( md)
            for mfile in self.mfiles:
               print("     METEOR FILES:", mfile)
               root_file = mfile.replace(".mp4", "")
               self.all_meteors[root_file] = {}
               root_day_file = root_file.replace(day + "_" , "")
               self.meteor_days[day]['meteors'].append(root_day_file)

      # set the redis file or delete it if the local file no longer exists
      for day_key in sorted(self.meteor_days.keys(), reverse=True):
         print("DOING DAY:", day_key, len(self.meteor_days[day_key]['meteors']))
         for key in self.meteor_days[day_key]['meteors']: 
            update = 0
            fkey = day_key + "_" + key
            rkey = "M:" + fkey 
            print(rkey)
            rval = self.r.get(rkey)
            if rval is None:
               print("BAD KEY!")
            else:
               rval = json.loads(self.r.get(rkey))

               if "final_trim" not in rval or "ffp" not in rval:
                  print("FINAL TRIM MISSING FROM RVAL!")
                  update = 1
            if rkey not in self.all_redis_keys or update == 1:
               print("UPDATE REDIS!")
               rval = self.mj_to_redis(fkey) 
               if rval == 0:
                  print("BAD FILE!", fkey)
               print("REDIS SAVING:", rkey)
               for rkey in rval:
                  print("   " + rkey, rval[rkey])
               self.r.set(rkey, json.dumps(rval))
            else:
               print("redis good", rval)


      print("ALL METEORS WITH CURRENT MJ INFO HAVE BEEN LOADED INTO REDIS!")

      # load scan files if they exist
      all_scans = {}
      pk_scans = glob.glob("/mnt/ams2/meteor_scan/*.pickle")
      for pk in pk_scans:
         try:
            with open(pk, 'rb') as handle:
               scan_data = pickle.load(handle)
         except:
            scan_data = {}

         for key in scan_data:
            all_scans[key] = scan_data[key]


      if in_day is None:
         rkey = "M:*"
         self.all_redis_keys = self.r.keys("M:*")
      else:
         rkey = "M:" + in_day + "*"
         self.all_redis_keys = self.r.keys(rkey)
         mdd = [in_day]
      print("RKEY1:", rkey, in_day)

      print(len(self.all_redis_keys), " meteors loaded into reddis")
      print(len(self.all_redis_keys), " redis keys for " , day)

      cc = 0
      for key in sorted(self.all_redis_keys, reverse=True):
         rkey = key
         mj = None
         rval = json.loads(self.r.get(key))
            


         if "mss" in rval:
            print("REDIS IS ALREADY GOOD FOR THIS METEOR!", key)
            #continue


         scan_key = key.replace("M:", "") + ".mp4"
         day = scan_key[0:10]
         mdir = "/mnt/ams2/meteors/" + day + "/"
         mf = mdir + scan_key.replace(".mp4", ".json")
         

         # check if the redis val is 100% up to date. If not reload it. 
         if "ev" not in rval:
            print(mf)
            try:
               mj = load_json_file(mf)
            except:
               print("CORRUPT JSON")
               continue
            event_id = 0
            solve_status = 0
            if "multi_station_event" in mj:

               if "event_id" in mj['multi_station_event']:
                  event_id = mj['multi_station_event']['event_id']
               if "solve_status" in mj['multi_station_event']:
                  solve_status = mj['multi_station_event']['solve_status']
            rval['ev'] = str(event_id) + ":" + str(solve_status)
            self.r.set(rkey,json.dumps(rval))
            print("ADDING EVENT!", rval)
         else:
            print("EV EXISTS!", rval['ev'])

         #print("CHECK :", scan_key)
         if scan_key in all_scans:
            meteor_scan_data = all_scans[scan_key]
            msd = 1 
         else:
            meteor_scan_data = None
            msd = 0
         good_roi = 0 
         good_ms_meteors = 0 
         good_msc_meteors = 0 

         good_msc_hd_meteors = 0 
         good_calib = 0 
         good_media = 0 
         hc = 0
         if "roi" in rval:
            if sum(rval['roi']) > 0:
               good_roi = 1
         if "ms_meteors" in rval:
            if rval['ms_meteors'] > 0:
               good_ms_meteors = 1
         if "msc_meteors" in rval:
            if rval['msc_meteors'] > 0:
               good_msc_meteors = 1
         if "hc" in rval:
            hc = 1


         if good_roi == 0:
            if msd == 1:
               if "roi" in meteor_scan_data:
                  roi = meteor_scan_data['roi']
                  good_roi = 1
               elif "meteor_scan_meteors" in meteor_scan_data:
                  if len(meteor_scan_data['meteor_scan_meteors']) > 0:
                     roi = meteor_scan_data['meteor_scan_meteors'][0]['roi']
                     rval['roi'] = meteor_scan_data['roi']
                     roi_good = 1
                     mj = load_json_file(mf)
                     mj['roi'] = rval['roi']
                     save_json_file(mf,mj)
                     rset(rkey, json.jumps(rval))

         media = {}
         roi_sd_file = mf.replace(".json", "-roi.jpg") 
         sd_stack_file = mf.replace(".json", "-stacked-tn.jpg") 
         good_hd_meteors = 0
         good_media = 0

         if cfe(roi_sd_file) == 1:
            good_sd_roi = 1
         else:
            good_sd_roi = 0

         if cfe(sd_stack_file) == 1:
            good_sd_stack = 1
         else:
            good_sd_stack = 0

         if self.show == 1:
            if good_sd_roi == 1:
               show_img = cv2.imread(roi_sd_file)
               cv2.imshow('pepe'  , show_img)
            elif good_sd_stack == 1:
               show_img = cv2.imread(sd_stack_file)
               cv2.imshow('pepe'  , show_img)
            cv2.waitKey(10)

         if good_sd_roi == 0 and good_roi == 1:
            print("ROI IMAGE MISSING.", roi_sd_file)
         if good_sd_stack == 0:
            print("STACK THUMB IMAGE MISSING.", sd_stack_file)
         meteor_scan_status = [good_roi, good_sd_roi, good_sd_stack, good_ms_meteors, good_msc_meteors, good_hd_meteors, good_media]
         rval['mss'] = meteor_scan_status
         print("SAVE REDIS:", rkey, rval)
         self.r.set(rkey, json.dumps(rval))
         cc = 1

   def make_meteor_media(self, day=None, meteor_file=None):
      index_html = ""
      self.ms_media_dir = "/mnt/ams2/METEOR_SCAN/" + day + "/" 
      self.meteor_dir = "/mnt/ams2/meteors/" + day + "/" 
      if cfe(self.ms_media_dir,1) == 0:
         os.makedirs(self.ms_media_dir) 
      if day is None:
         self.all_redis_keys = self.r.keys("M:*")
      else:
         self.all_redis_keys = self.r.keys("M:*" + day + "*" )

      if meteor_file is not None:
         rkey = meteor_file.replace(".json", "") 
         self.all_redis_keys = self.r.keys("M:" + rkey + "*" )
         print(self.all_redis_keys)
         day = meteor_file[0:10]
         in_day = day


      self.show = 0 
      print("Make Media", len(self.all_redis_keys), " meteors exist in reddis...")
      all_media_files = {}
      for rkey in self.all_redis_keys:
         
         self.sd_stack = None
         self.hd_stack = None
         self.sd_frames = None
         self.hd_frames = None
         root = rkey.replace("M:", "")
         if root not in all_media_files:
            all_media_files[root] = {}
         final_media = {}
         mjf = self.meteor_dir + root + ".json"
         print(mjf)
         if cfe(mjf) == 1:
            try:
               mj = load_json_file(mjf)
            except:
               print("THE MJF IS CORRUPT!", mjf)
               continue
         else:
            print("MJF is not found. should we delte the redis key?:", mjf)
            continue

         # preview image / cropped thumbs
         final_media['prev_img'] = self.station_id + "_" + root + "-PREV.jpg"
         final_media['roi_img'] = self.station_id + "_" + root + "-ROI.jpg"
         final_media['roihd_img'] = self.station_id + "_" + root + "-ROIHD.jpg" 
         # preview / cropped videos
         final_media['roi_vid'] = self.station_id + "_" + root + "-ROI.mp4"
         final_media['roihd_vid'] = self.station_id + "_" + root + "-ROIHD.mp4" 
         # SD/HD stack images
         final_media['sd_img'] = self.station_id + "_" + root + "-SD.jpg"
         final_media['hd_img'] = self.station_id + "_" + root + "-HD.jpg" 

         # trimmed videod clips 
         final_media['sd_vid'] = self.station_id + "_" + root + "-SD.mp4"
         final_media['hd_vid'] = self.station_id + "_" + root + "-HD.mp4" 


         for media_file in sorted(final_media):
            out_file = self.ms_media_dir + final_media[media_file]
            make_media = 0
            if "final_trim" not in mj:
               make_media = 1
            if cfe(out_file) == 1:
               print("     *****", media_file, "EXISTS")
               file_missing = 0
            else:
               print("     *****", media_file, "MISSING!")
               file_missing = 1
            print(out_file)
            if cfe(out_file) == 0 or make_media == 1:
               print("MAKING:", media_file, out_file, mjf)
               self.make_media(media_file, out_file, mjf, mj)

            if cfe(out_file) == 1:
               if "jpg" in out_file:
                  index_html += "<img src=" + out_file.split("/")[-1] + "><br>" + out_file.split("/")[-1] + "<br>\n"
               elif "mp4" in out_file:
                  index_html += "<video controls><source type='video/mp4' src='" + out_file.split("/")[-1] + "'></video><br>" + out_file.split("/")[-1] + "<br>\n"
               final_media[media_file] = {"file": final_media[media_file], "status": 1}
            else:
               final_media[media_file] = {"file": final_media[media_file], "status": 0}
               index_html += "FAILED <a href=" + out_file.split("/")[-1] + "></a>" + out_file.split("/")[-1] + "<br>\n"
         all_media_files[root] = final_media 
         mj['all_media_files'] = final_media

         try:
            save_json_file(self.ms_media_dir + "media.json", all_media_files)
         except:
            print("Problem saving json media file", sel.ms_media_dir + "media.json")
         fp = open(self.ms_media_dir + "media.html", "w")
         fp.write(index_html)
         fp.close()
         # 9 total media files for full HD & SD payload

         # 5 total media files for SD only payload

   def make_media(self, media_file_type, media_file_name, mf, mj):
       print("MAKE MEDIA FOR", mf)
       final_trim = None
       if True:
          if self.sd_stack is None:
             if "sd_stack" in mj:
                if mj["sd_stack"] != 0 and mj['sd_stack'] is not None:
                   if cfe(mj['sd_stack']) == 1:
                      self.sd_stack = cv2.imread(mj['sd_stack'])
                      #cv2.imshow('pepe', self.sd_stack)
                      #cv2.waitKey(30)
       if True:
          if self.hd_stack is None:
             if "hd_stack" in mj:
                if mj["hd_stack"] != 0 and mj['hd_stack'] is not None:
                   if cfe(mj['hd_stack']) == 1:
                      self.hd_stack = cv2.imread(mj['hd_stack'])
                      if self.hd_stack.shape[0] != 1920:
                         self.hd_stack = cv2.resize(self.hd_stack, (1920,1080))
                      #cv2.imshow('pepe2', self.hd_stack)
                      #cv2.waitKey(30)


       if media_file_type == "prev_img" and cfe(media_file_name) == 0:
          print("IMG:", media_file_type, media_file_name)
          try:
             self.prev_img = cv2.resize(self.sd_stack, (320,180))
             cv2.imwrite(media_file_name, self.prev_img, [cv2.IMWRITE_JPEG_QUALITY, 60])
          except:
             print("FAILED TO MAKE MEDIA FOR:", mj)

       if media_file_type == "roi_img" and "roi" in mj and cfe(media_file_name) == 0:
          x1,y1,x2,y2 = mj['roi']
          if sum(mj['roi']) > 0:
             x1,y1,x2,y2 = int(x1),int(y1),int(x2),int(y2)
             self.roi_img = self.sd_stack[y1:y2,x1:x2]
             print("ROI IMG:", media_file_type, media_file_name)
             try:
                cv2.imwrite(media_file_name, self.roi_img, [cv2.IMWRITE_JPEG_QUALITY, 60])
             except:
                print("error saving file.")
             if self.show == 1:
                cv2.imshow('pepe3', self.roi_img)
                cv2.waitKey(30)

       if media_file_type == "sd_img" and cfe(media_file_name) == 0:
          print("SD IMG:", media_file_type, media_file_name)
          self.sd_stack = cv2.resize(self.sd_stack, (640,360))
          cv2.imwrite(media_file_name, self.sd_stack, [cv2.IMWRITE_JPEG_QUALITY, 60])


       # MAKE SD ROI VID
       if media_file_type == "roi_vid" and cfe(media_file_name) == 0:
          if "roi" in mj:
             crop_box = ""
             for ff in mj['roi']:
                if crop_box != "":
                   crop_box += ","
                crop_box += str(ff)
             x1,y1,x2,y2 = mj['roi']
             crop_box = [x1,y1,x2-x1,y2-y1]
             
             crop_video(mj['sd_video_file'], media_file_name, crop_box) 
             print("JUST MADE SD CROP USING ROI VALS:", mj['roi'])
             print("FF CROP:", crop_box)
             if "meteor_scan_meteors" in mj:
                if len(mj["meteor_scan_meteors"]) > 0:
                   print("METEOR SCAN METEORS :", mj['meteor_scan_meteors'])

                   start = mj['meteor_scan_meteors'][0]['ofns'][0] - 10
                   end = mj['meteor_scan_meteors'][0]['ofns'][-1] + 10
                   if start < 0:
                      start = 0
                   media_file_name_temp = media_file_name.replace(".mp4", "-temp.mp4")
                   splice_video(media_file_name, start,  end,  media_file_name_temp, "frame")
                   os.system("mv " + media_file_name_temp + " " + media_file_name)


             print("SD CROP VID:", media_file_type, media_file_name)

       # MAKE HD ROI IMG
       if media_file_type == "roihd_img" and cfe(media_file_name) == 0:
          if "roi" in mj:
             if sum(mj["roi"]) > 0:
                hx1,hy1,hx2,hy2 = self.sd_to_hd_roi(mj['roi'], self.sd_stack.shape[1], self.sd_stack.shape[0])
                mj['roi_hd'] = [hx1,hy1,hx2,hy2]
                print("ROI HD:", hx1, hy1, hx2, hy2)
                if self.hd_stack is not None:
                   if self.hd_stack is not None:
                      self.hd_roi_img = self.hd_stack[hy1:hy2,hx1:hx2]
                      #print(hx1,hy1,hx2,hy2)
                      #cv2.imshow('pepe', self.hd_stack)
                      #cv2.waitKey(0)
                      print("HD IMG:", media_file_type, media_file_name)
                      cv2.imwrite(media_file_name, self.hd_roi_img, [cv2.IMWRITE_JPEG_QUALITY, 60])
                      if self.show == 1:
                         cv2.imshow('pepe4', self.hd_roi_img)
                         cv2.waitKey(30)
                   else:
                      print("NO HD STACK1!?", self.hd_stack)
                else:
                   print("NO HD STACK2!?", self.hd_stack)

       # MAKE HD ROI VID 
       if media_file_type == "roihd_vid" and cfe(media_file_name) == 0 and "meteor_scan_hd_crop_scan" in mj:
          if "roi" in mj:
             if sum(mj["roi"]) > 0:
                hx1,hy1,hx2,hy2 = self.sd_to_hd_roi(mj['roi'], self.sd_stack.shape[1], self.sd_stack.shape[0])
                hd_roi = [hx1,hy1,hx2-hx1,hy2-hy1]
                crop_video(mj['hd_trim'], media_file_name, hd_roi) 

                hdfns = []
                if type(mj['meteor_scan_hd_crop_scan']) == int:
                   print("NO HD CROP SCAN DATA YET FOR THIS OBS")
                   print("We will have to wait to trim the HD clip")
                else:
                   for obj_id in mj['meteor_scan_hd_crop_scan']['meteors']:
                      mobj = mj['meteor_scan_hd_crop_scan']['meteors'][obj_id]
                      if len(mobj['ofns']) > 2:
                         print("ADDING FRAMES")
                         hdfns.append(min(mobj['ofns']))
                         hdfns.append(max(mobj['ofns']))

                   if len(hdfns) > 1:
                      if max(hdfns) - min(hdfns) < 2:
                         print("BAD OBJs?:", hdfns)
                      else:
                         hd_start = min(hdfns) - 10
                         hd_end = max (hdfns) + 10
                         if hd_start < 5:
                            hd_start = 0
                         if 'ffp' in mj:
                            print(mj['ffp'])

                         print("HD START/END", hd_start,hd_end)
                         if hd_start < 0:
                            hd_start = 0
                         print("HD VID:", media_file_type, media_file_name, hd_start, hd_end)
                         temp_media_file_name = media_file_name.replace(".mp4", "-temp.mp4")
                         splice_video(media_file_name, hd_start,  hd_end,  temp_media_file_name, "frame")
                         os.system("mv " + temp_media_file_name + " " + media_file_name)




       # MAKE HD STCK IMG
       if media_file_type == "hd_img" and cfe(media_file_name) == 0:
          print("HD IMG:", media_file_type, media_file_name)
          if self.hd_stack is not None:
             cv2.imwrite(media_file_name, self.hd_stack, [cv2.IMWRITE_JPEG_QUALITY, 70])

       # SPLICE SD VIDEO
       print("MEDIA FILE TYPE IS :", media_file_type, media_file_name)
       if media_file_type == "sd_vid":
          trim_good = 1
          if "final_trim" not in mj:
             print("final trim missing")
             trim_good = 0
          if cfe(media_file_name) == 0 or trim_good == 0:
             if "ms_meteors" in mj:
                if len(mj["ms_meteors"]) > 0:
                   print("METEOR SCAN METEORS :", mj['meteor_scan_meteors'])

                   start = mj['meteor_scan_meteors'][0]['ofns'][0] - 10
                   end = mj['meteor_scan_meteors'][0]['ofns'][-1] + 10
                   if start < 0:
                      start = 0
                   print("SD SPLICE:", start, end)
                   splice_video(mj['sd_video_file'], start,  end,  media_file_name, "frame")

                   if "final_trim" not in mj:
                      mj['final_trim'] = {}
                   mj['final_trim']['sd'] = [start,end]
                   if "ffp" not in mj["final_trim"]:
                      mj['final_trim']['ffp'] = {}
                   mj['final_trim']['ffp']['sd'] = ffprobe(media_file_name)
             else:
                print("MISSING DATA REQUIRED TO MAKE THIS FILE!", mj.keys())
          if "final_trim" not in mj:
             print("final trim still missing")

       # SPLICE HD VIDEO
       if media_file_type == "hd_vid" and cfe(media_file_name) == 0:
          if "meteor_scan_hd_crop_scan" not in mj:
             print("NO MSHD CROP SCAN in mj", mj.keys())
          else:
             hdfns = []
             print("HD SCAN CROP IS HERE NOW WHAT!", mj['meteor_scan_hd_crop_scan'])

             if cfe(media_file_name) == 0:
                print("FINAL HD MEDIA NOT FOUND!", media_file_name)
                if type(mj['meteor_scan_hd_crop_scan']) == int:
                   if mj['meteor_scan_hd_crop_scan'] == 0:
                      print("HD CROP SCAN FAILED ON THIS OBS")
                   else:
                      del(mj['meteor_scan_hd_crop_scan'])
                else:
                   print("TRY TO FIND HD START AND END!")
                   for obj_id in mj['meteor_scan_hd_crop_scan']['meteors']:
                      mobj = mj['meteor_scan_hd_crop_scan']['meteors'][obj_id]
                      if len(mobj['ofns']) > 2:
                         print("ADDING FRAMES")
                         hdfns.append(min(mobj['ofns'])) 
                         hdfns.append(max(mobj['ofns'])) 
                   print("HDFNS:", hdfns)
                   if len(hdfns) > 1:
                      if max(hdfns) - min(hdfns) < 2:
                         print("BAD OBJs?:", hdfns)
                      else:
                         hd_start = min(hdfns) - 10
                         hd_end = max (hdfns) + 10
                         if hd_start < 5:
                            hd_start = 0
                         if 'ffp' in mj:
                            print(mj['ffp'])
                         
                         print("HD START/END", hd_start,hd_end)
                         if hd_start < 0:
                            hd_start = 0
                         print("HD VID:", media_file_type, media_file_name, hd_start, hd_end)
                         splice_video(mj['hd_trim'], hd_start,  hd_end,  media_file_name, "frame")

                         if "final_trim" not in mj:
                            mj['final_trim'] = {}
                         mj['final_trim']['hd'] = [hd_start,hd_end]
                         if "ffp" not in mj['final_trim']:
                            mj['final_trim']['ffp'] = {}
                         mj['final_trim']['ffp']['hd'] = ffprobe(media_file_name)
                         print(mj['final_trim'])
       try:
          save_json_file("test.json", mj)
          save_json_file(mf, mj)
          print("SAVED:", mf)
       except:
          print(mj)
          print("MEDIA ERROR SAVING JSON!", mf)
   


   def rescan_all_meteors(self, day=None, meteor_file=None):
      print("RESCAN METEORS:", day)

      force = False 
      if meteor_file is not None:
         force = True
      in_day = day
      self.single_scan = 0
      if day is None:
         self.all_redis_keys = self.r.keys("M:*")
      else:
         self.all_redis_keys = self.r.keys("M:*" + day + "*" )
      self.show = 0 
      if meteor_file is not None:
         rkey = meteor_file.replace(".json", "") 
         self.all_redis_keys = self.r.keys("M:" + rkey + "*" )
         print(self.all_redis_keys)
         day = meteor_file[0:10]
         in_day = day
         self.single_scan = 1
         #self.debug_meteor(meteor_file)


      all_media = self.get_ms_media(in_day)


      if False:
         # ??? NOT SURE WHAT THIS IS FOR
         for rkey in sorted(self.all_redis_keys, reverse=True):
            key = rkey.replace("M:", "")
            rval = self.r.get(rkey)
            rval = json.loads(rval)


            sd_stack = "/mnt/ams2/meteors/" + key[0:10] + "/" + key + "-stacked.jpg"
            hd_stack = "/mnt/ams2/meteors/" + key[0:10] + "/" + rval['hd'].replace(".mp4", "-stacked.jpg")
        
            if "roi" in rval:
               if cfe(sd_stack) == 1:
                  sd_img = cv2.imread(sd_stack)
               else:
                  sd_img = None
               if cfe(hd_stack) == 1:
                  hd_img = cv2.imread(hd_stack)
               else:
                  hd_img = None
               if sd_img is not None and hd_img is not None :
                  x1,y1,x2,y2 = rval['roi']
                  x1,y1,x2,y2 = self.bound_crop(x1,y1,x2,y2,sd_img.shape[1],sd_img.shape[0])

                  hx1,hy1,hx2,hy2 = self.sd_to_hd_roi(rval['roi'], sd_img.shape[1], sd_img.shape[0])
                  hd_crop = hd_img[hy1:hy2,hx1:hx2]
                  sd_crop = sd_img[y1:y2,x1:x2]
                  if self.show == 1:
                     cv2.rectangle(hd_img, (int(hx1), int(hy1)), (int(hx2) , int(hy2)), (255, 255, 255), 1)
                     cv2.rectangle(sd_img, (int(x1), int(y1)), (int(x2) , int(y2)), (255, 255, 255), 1)
                
                     cv2.imshow('hdf', hd_img)
                     cv2.imshow('sdf', sd_img)
                     try:
                        cv2.imshow('hd', hd_crop)
                     except:
                        print("     HD CROP FAILED?", hx1,hy1,hx2,hy2)
                     cv2.imshow('sd', sd_crop)
                     cv2.waitKey(30)
               else:
                  print(sd_stack, hd_stack)

               print(rval)


      # For each meteor in redis, check the status. 
      # run meteor_scan or meteor_scan_crop as needed
      # when scans are done run make_final_media unless it is already done

      for rkey in sorted(self.all_redis_keys, reverse=True):
         key = rkey.replace("M:", "")
         rval = self.r.get(rkey)
         rval = json.loads(rval)
         self.meteor_file = key + ".mp4"
         print(key, rval)
         if "mss" in rval and force != False:
            [good_roi, good_sd_roi, good_sd_stack, good_ms_meteors, good_msc_meteors, good_hd_meteors, good_media] = rval['mss']
         else:
            rval['mss'] = [0, 0, 0, 0, 0, 0, 0] 
            self.r.set(rkey,json.dumps(rval))
            [good_roi, good_sd_roi, good_sd_stack, good_ms_meteors, good_msc_meteors, good_hd_meteors, good_media] = rval['mss']
         mf = "/mnt/ams2/meteors/" + key[0:10] + "/"  + key + ".json" 

         if cfe(mf) == 1:
            try:
               self.mj = load_json_file(mf)
            except:
               print("CORRUPTED METEOR FILE!", mf)
               continue
         else:
            # THIS IS A TRASH'D METEOR
            self.r.delete(rkey)
            continue
         remake_movies = 0
         # before we continue and make sure the redis status is up to date with the file system files.
         if force is True:
            remake_movies = 1
         if "final_trim" in self.mj:
            if "ffp" not in self.mj['final_trim']:
               remake_movies = 1
         else:
            remake_movies = 1
         if remake_movies == 1:
            self.make_meteor_media(day, meteor_file=key)

         if "all_media" not in self.mj:
            remake_movies = 1

         print("REMAKE MEDIA", remake_movies) 

         if "meteor_scan_meteors" in self.mj:
             print("MSM TYPE:", type(self.mj['meteor_scan_meteors']))
             print("MSM :", self.mj['meteor_scan_meteors'])
             if type (self.mj['meteor_scan_meteors']) == dict:
                # this is a bad structure from an old run, reset it. 
                print("meteor_scan_meteors is a dict")
                good_ms_meteors = 0
                del (self.mj['meteor_scan_meteors'])
             else:
                good_ms_meteors = 1
                print("METEOR SCAN ALREADY DONE!")
         elif "meteor_scan_meteors" in self.mj:
            print("meteor_scan_meteors in mj but it should be ms_meteors?!")
            print("meteor_scan_meteors is not a dict")
            print(self.mj['meteor_scan_meteors'])
            print(self.mj.keys())



         # check or do meteor_scan LEVEL 1 first
         if ((good_ms_meteors == 0 or good_roi == 0 or "roi" not in rval) and "msf" not in rval and good_msc_meteors != 1) or remake_movies == 1:
            # meteor scan has not run so do that first.
               self.meteor_scan()
               msm_total = len(self.meteor_scan_meteors)
               if msm_total >= 1:
                  good_ms_meteors = 1
                  self.roi = self.meteor_scan_meteors[0]['roi']
                  self.mj['roi'] = self.roi
                  self.mj['meteor_scan_meteors'] = self.meteor_scan_meteors
                  rval['roi'] = self.roi
                  rval['mss'] = [1, 1, good_sd_stack, 1, good_msc_meteors, good_hd_meteors, good_media] 
               else:
                  self.mj['msf'] = 1
                  rval['msf'] = 1
               rval['lu'] = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

               self.r.set(rkey, json.dumps(rval))
               self.mj['last_update'] = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

               if len(self.mj.keys()) == 0:
                  print("MJ IS EMPTY WTF!", mf)
                  exit()


               save_json_file("test.json", self.mj)
               save_json_file(mf, self.mj)
               print("RAN METEOR SCAN and saved ", mf)

         # do the crop scan if needed
         rval = self.r.get(rkey)
         if rval is not None:
            rval = json.loads(rval)
         else:
            print("NO REDDIS!?", rkey)

         if (int(good_msc_meteors) == 0 and int(good_roi) == 1 and "mscf" not in rval ) or ("msc_meteors" not in rval and int(good_roi) == 1) or remake_movies == 1 :
            print(rkey, rval)
            if ("msc_meteors" in rval and ("roi" in self.mj or "roi" in rval)) :
               # we already did this, but redis must not know. 
               rval['msc_meteors'] = len(self.mj['msc_meteors'].keys())
               good_msc_meteors = 1
               rval['mss'] = [good_roi, good_sd_roi, good_sd_stack, good_ms_meteors, good_msc_meteors, good_hd_meteors, good_media] = rval['mss']
               self.r.set(rkey,json.dumps(rval))
               print("WE ALREADY DID IT!")
            elif "roi" in rval or "roi" in self.mj:
               if "roi" in self.mj and "roi" not in rval:
                  rval['roi'] = self.mj['roi']
                  print("ROI IN in mj")
               elif "roi" in rval and "roi" not in self.mj:
                  self.mj['roi'] = rval['roi'] 
                  print("ROI IN in rval ")
               else:
                  print(self.mj.keys())
                  print(rval)
                  for key in self.mj.keys():
                     print("MJ KEY:", key)

               print("LETS DO METEOR SCAN CROP!", rval['roi'])
               if "roi" in self.mj or "roi" in rval:
                  self.roi = rval['roi']

               final_objects = self.meteor_scan_crop(mf)

               if len(final_objects.keys()) > 0:
                  rval['mss'] = [good_roi, good_sd_roi, good_sd_stack, good_ms_meteors, 1, good_hd_meteors, good_media] 
                  rval['msc_meteors'] = len(final_objects) 
                  self.mj['msc_meteors'] = final_objects
               else:
                  rval['mscf'] = 1
                  self.mj['mscf'] = 1
               rval['lu'] = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
               self.r.set(rkey, json.dumps(rval))
               print("SETTING RED", rval)
               self.mj['last_update'] = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

               if len(self.mj.keys()) == 0:
                  print("MJ IS EMPTY WTF!", mf)
                  exit()
               save_json_file("test.json", self.mj)

               save_json_file(mf, self.mj)
               test = load_json_file(mf)
               print("RANMETEOR SCAN CROP and saved ", mf)
         else:
            print(rval)
            print("SKIP CROP METEOR BECAUSE:", good_msc_meteors, good_roi, good_ms_meteors )
            # CHECK MEDIA BEFORE GIVING UP
            mfn = mf.split("/")[-1].replace(".json", "")
            if "all_media" not in rval:
               print(all_media)
               print("GET MEDIA from all_media for", mfn)
               if mfn in all_media:
                  rval['all_media'] = all_media[mfn]
               else:
                  rval['all_media'] = {}
            print("MEDIA", rval['all_media'])
            if 'msc_meteors' in self.mj:
               print("   we did it already")
            else:
               print("   we tried and failed...")

         if "meteor_scan_hd_crop_scan" in self.mj :
            #if self.mj['meteor_scan_hd_crop_scan'] != 0:
            if True:
               good_hd_meteors = 0
               rval['mss'] = [good_roi, good_sd_roi, good_sd_stack, good_ms_meteors, good_msc_meteors, good_hd_meteors, good_media] 
               if self.mj['meteor_scan_hd_crop_scan'] == 0 : 
                  rval['mshdc_meteors'] = self.mj['meteor_scan_hd_crop_scan']
               elif self.mj['meteor_scan_hd_crop_scan'] == -1 : 
                  del(self.mj['meteor_scan_hd_crop_scan'])
                  good_hd_meteors = 0
                  rval['mss'] = [good_roi, good_sd_roi, good_sd_stack, good_ms_meteors, good_msc_meteors, good_hd_meteors, good_media] 

               else:
                  print (self.mj['meteor_scan_hd_crop_scan']['meteors'])
                  rval['mshdc_meteors'] = len(self.mj['meteor_scan_hd_crop_scan']['meteors'].keys())
                  good_hd_meteors = 1
                  rval['mss'] = [good_roi, good_sd_roi, good_sd_stack, good_ms_meteors, good_msc_meteors, good_hd_meteors, good_media] 
               print("SAVE REDIS:", rval)
               self.r.set(rkey, json.dumps(rval))
         if good_hd_meteors == 0:
            mj = {}
            if cfe(mf) == 1:
               print(mf)
               try:
                  mj = load_json_file(mf)
               except:
                  print("CORRUPTED METEOR FILE!", mf)
                  continue


            print("HD CROP SCAN HAS NOT BEEN DONE YET!", mj['hd_trim'])
            mfn = mf.split("/")[-1]
            hd_crop_file = "/mnt/ams2/METEOR_SCAN/" + mfn[0:10] + "/"  + self.station_id + "_" + mfn.replace(".json", "-ROIHD.mp4")

            if cfe(hd_crop_file) == 1 :
               print("HD CROP FILE GOOD", hd_crop_file)
               if "meteor_scan_hd_crop_scan" in self.mj:
                  print("HD CROP SCAN GOOD", hd_crop_file)
                  hd_ms_data = self.mj['meteor_scan_hd_crop_scan'] 
               elif "hdms_fail" not in self.mj:
                  meteors, non_meteors, frame_data = self.meteor_scan_hd_crop(hd_crop_file, mj)
                  hd_ms_data = {}
                  hd_ms_data['meteors'] = meteors
                  #hd_ms_data['non_meteors'] = non_meteors
                  #hd_ms_data['frame_data'] = frame_data
                  self.mj['meteor_scan_hd_crop_scan'] = hd_ms_data['meteors']
                  if len(hd_ms_data['meteors'].keys()) == 0:
                     self.mj['hdms_fail'] = 1
                  save_json_file(mf, self.mj)
                  print("SAVED HD CROP SCAN DATA IN ", mf)
            else:
               print("NO HD CROP FILE EXIST SO WE CAN'T DO THE HD CROP SCAN!!", hd_crop_file)
               if "roi" in self.mj:
                  print("ROI IS GOOD", self.mj['roi'])
               else:
                  print("NO ROI IN THE MJ!")
               if "hd_trim" in self.mj:
                  if self.mj['hd_trim'] != 0:
                     if cfe(self.mj['hd_trim']) == 1:
                        print("HD TRIM FILE WAS FOUND!", self.mj['hd_trim'])
                     else:
                        print("NO HD TRIM FILE:", self.mj['hd_trim'])
                  else:
                     print("NO HD TRIM FILE IS 0:", self.mj['hd_trim'])
               else:
                  print("NO HD TRIM INSIDE THE MJ:")
               self.mj['meteor_scan_hd_crop_scan'] = -1
               save_json_file(mf, self.mj)

         mfn = mf.split("/")[-1].replace(".json", "")
         self.make_meteor_media(day=in_day, meteor_file=mfn)


      # now just print a report of what is in redis to see how we did for the day. 
      # this will drive the media sync to the S3FS
      if self.single_scan == 1:
         return()
      if in_day is None:
         self.all_redis_keys = self.r.keys("M:*")
      else:
         self.all_redis_keys = self.r.keys("M:*" + in_day + "*" )
      final_scan_report = "<table><tr><td colspan=2>Preview</td><td>File</td><td>ROI</td><td>MS Meteors</td><td>MSC Meteors</td><td>MSHDC Meteors</td></tr>"
      all_media_size = 0
      for rkey in self.all_redis_keys:
         rval = json.loads(self.r.get(rkey))
         key = rkey.replace("M:", "")
         if "roi" in rval:
            if sum(rval['roi']) > 0:
               roi = 1
         else:
            roi = 0
         if "ms_meteors" in rval:
            ms_meteors = rval['ms_meteors']
         else:
            ms_meteors = 0
         if "msc_meteors" in rval:
            msc_meteors = rval['msc_meteors']
         else:
            msc_meteors = 0
         if "mshdc_meteors" in rval:
            mshdc_meteors = rval['mshdc_meteors']
         else:
            mshdc_meteors = 0
         roi_file = "/mnt/ams2/METEOR_SCAN/" + key[0:10] + "/" + self.station_id + "_" + key + "-ROI.jpg"
         prev_file = "/mnt/ams2/METEOR_SCAN/" + key[0:10] + "/" + self.station_id + "_" + key + "-PREV.jpg"
         if cfe(roi_file) == 1:
            roi_img = "<img width=180 height=180 src=" + roi_file.replace("/mnt/ams2", "") + ">"
         else:
            roi_img = ""
         if cfe(prev_file) == 1:
            prev_img = "<img src=" + prev_file.replace("/mnt/ams2", "") + ">"
         else:
            prev_img = ""
         if key in all_media:
            media = all_media[key]
         
         med_list = ""
         total_size = 0
         orig_json_link = "<a href=/meteors/" + key[0:10] + "/" + key + ".json" + ">" + key + "</a>"
         for med_obj in media:
            med_ext = med_obj['ext']
            med_size = med_obj['size']
            med_sync = med_obj['sync_status']
            med_link = "<a href=" + self.station_id + "_" + key + "-" + med_ext + ">" + med_ext + "</a>"
            med_list += med_sync + " " + med_link + " " + str(med_size) + "<br>"
            total_size+= med_size
            all_media_size += med_size
         med_list += "Total Size: " + str(total_size)

         final_scan_report += "<tr><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td></tr>\n".format(str(roi_img), str(prev_img), str(orig_json_link), str(roi), str(ms_meteors), str(msc_meteors), str(mshdc_meteors), str(med_list), "" )
         print("     ", rkey, roi, ms_meteors, msc_meteors, mshdc_meteors)

      final_scan_report += "</table>"
      final_scan_report += "Total Size for ALL media: " + str(all_media_size)

      ms_report_file = "/mnt/ams2/METEOR_SCAN/" + in_day + "/"  + self.station_id + "_msreport.html" 
      out = open(ms_report_file, "w")
      out.write(final_scan_report)
      out.close()


   def get_ms_media(self, day):
      all_media = {}
      ms_dir = "/mnt/ams2/METEOR_SCAN/" + day + "/" 
      ms_media = glob.glob(ms_dir + "*")
      for rkey in self.all_redis_keys:
         key = rkey.replace("M:", "")
         print("METEOR:", key)

         if key not in all_media:
            all_media[key] = []
         for media_file in ms_media:
            if key in media_file:
               md_fn = media_file.split("/")[-1]
               ext = md_fn.split("-")[-1]
               media_obj = {}
               media_obj['ext'] = ext
               media_obj['size'] = os.path.getsize(media_file)
               media_obj['sync_status'] = ""
               media_obj['sync_date'] = ""

               all_media[key].append(media_obj)

      save_json_file(ms_dir + self.station_id + "_" + "all_media.json", all_media)
      print("SAVED:", ms_dir + self.station_id + "_" + "all_media.json")

      return(all_media)


   def mj_to_redis_trash(self, root_file):
      day = root_file[0:10]
      mf = "/mnt/ams2/meteors/" + day + "/" + root_file + ".json" 
      print(mf)
      if cfe(mf) == 1:
         mj = load_json_file(mf)
      else:
         return(0)
      red_val = {}
      if "sd_video_file" in mj:
         red_val['sd'] = mj['sd_video_file'].split("/")[-1]
      
      if "hd_trim" in mj:
         if mj['hd_trim'] != 0 and mj['hd_trim'] is not None:
            print("HD TRIM IS NOT NONE???")  


   def mj_to_redis(self, root_file):
      day = root_file[0:10]
      mf = "/mnt/ams2/meteors/" + day + "/" + root_file + ".json" 
      print(mf)
      if cfe(mf) == 1:
         try:
            mj = load_json_file(mf)
         except:
            print("Corrupt json file", mf)
            mj = None
            return({})
      else:
         return(0)
      red_val = {}
      if "sd_video_file" in mj:
         red_val['sd'] = mj['sd_video_file'].split("/")[-1]
      
      if "hd_trim" in mj:
         if mj['hd_trim'] != 0 and mj['hd_trim'] is not None:
            red_val['hd'] = mj['hd_trim'].split("/")[-1]
      if "hc" in mj:
         red_val['hc'] = mj['hc']
      if "roi" in mj:
         red_val['roi'] = mj['roi']
      if "calib" in mj:
         red_val['calib'] = mj['calib']
      elif "cp" in mj:
         cp = mj['cp']
         if cp is not None:
            if math.isnan(cp['total_res_px']):
               cp['total_res_px'] = 9999
            red_val['calib'] = [cp['ra_center'], cp['dec_center'], cp['center_az'], cp['center_el'], cp['position_angle'], cp['pixscale'], float(len(cp['cat_image_stars'])), float(cp['total_res_px'])]
      if "multi_station_event" in mj:
         if "event_id" in mj['multi_station_event']:
            event_id = mj['multi_station_event']['event_id']
         if "solve_status" in mj['multi_station_event']:
            solve_status = mj['multi_station_event']['solve_status']
         red_val['ev'] = event_id + ":" + solve_status

      if "human_points" in mj:
         red_val['hp'] = 1
      if "ffp" in mj:
         red_val['ffp'] = mj['ffp']
      else:
         print("FFP MISSING")
         hd_vid = None
         red_val['ffp'] = {}
         if "hd_trim" in mj:
            if mj['hd_trim'] != 0 and mj['hd_trim'] is not None:
               
               if cfe(mj['hd_trim']) == 1:
                  hd_vid = mj['hd_trim']
                  red_val['ffp']['hd'] = ffprobe(mj['hd_trim'])
            else:
               hd_vid = None
         else:
            hd_vid = None
         if "sd_video_file" in mj:
            if cfe(mj['sd_video_file']) == 1:
               sd_vid = mj['sd_video_file']
               red_val['ffp']['sd'] = ffprobe(mj['sd_video_file'])
      if "final_trim" in mj:
         red_val['final_trim'] = mj['final_trim']
      if "all_media" in mj:
         red_val['all_media'] = mj['all_media']
      if "meteor_scan_meteors" in mj:
         red_val['ms_meteors'] = len(mj['meteor_scan_meteors'])
      if "msc_meteors" in mj:
         red_val['msc_meteors'] = len(mj['msc_meteors'])
      if "meteor_scan_hd_crop_scan" in mj:
         if type(mj['meteor_scan_hd_crop_scan']) == int:
            red_val['meteor_scan_hd_crop_scan'] = mj['meteor_scan_hd_crop_scan']
         else:
            red_val['meteor_scan_hd_crop_scan'] = len(mj['meteor_scan_hd_crop_scan'])


      return(red_val)
   



   def load_scan_redis(self):
      for key in self.scan_data:

         mdata = self.scan_data[key]
         rkey = "M:" + key
         rval = {}
         rval['sdv'] = key
         rval['hdv'] = mdata['mj_info']['hd_vid'] 
         if "roi" in mdata:
            rval['roi'] = mdata['roi']
         elif "meteor_scan_meteors" in mdata:
            if len(mdata['meteor_scan_meteors']) > 0:
               rval['roi'] = mdata['meteor_scan_meteors'][0]['roi']
            else:
               rval['roi'] = [0,0,0,0]
         else:
            rval['roi'] = [0,0,0,0]
         if "hc" in mdata:
            rval['hc'] = mdata['hc']
         if "hc" in mdata:
            rval['hc'] = mdata['hc']
         else:
            rval['hc'] = 0
         if "calib" in mdata['mj_info']:
            rval['calib'] = mdata['mj_info']['calib']

         if "event_id" in mdata['mj_info']:
            rval['event_id'] = mdata['mj_info']['event_id']
         else:
            event_id = 0
         if "solve_status" in mdata['mj_info']:
            rval['solve_status'] = mdata['mj_info']['solve_status']
         if "ffp" in mdata['mj_info']:
            rval['ffp'] = mdata['mj_info']['ffp']
         if "all_media" in mdata['mj_info']:
            rval['all_media'] = mdata['mj_info']['all_media']

         self.r.set(rkey, json.dumps(rval))
            
         print("LOADING RED:", rkey, rval)

   def check_scan_status_month(self,day=None):
      deleted_keys = []
      all_status = {}
      # first just display the current status of each file in the meteor scan for this month
      all_roi_imgs = {}
      if day is None:
         self.load_all_meteors_into_redis(day)
         
         self.rescan_all_meteors(day)
         self.make_meteor_media(day)
      else:
         if cfe("/mnt/ams2/METEOR_SCAN/" + day + "/", 1) == 0:
            os.makedirs("/mnt/ams2/METEOR_SCAN/" + day + "/")
         self.load_all_meteors_into_redis(day)
         print("DONE LOAD REDIS")
         #return()
         self.rescan_all_meteors(day)
         self.make_meteor_media(day)

      #print(len(self.scan_data), " scan_data")
      # RUN THE ABOVE TO CLEAN UP THE ENTIRE DAY!
      return()

      for mfn in self.scan_data:
         meteor_data = self.scan_data[mfn]
         # 1st scan status
         if "meteor_scan_meteors" in meteor_data:
            if len(meteor_data['meteor_scan_meteors']) > 0:
               meteor_scan_status = 1
            else:
               meteor_scan_status = 0
         else:
            meteor_scan_status = 0
         if "meteor_scan_crop_scan" in meteor_data:
            if len(meteor_data['meteor_scan_crop_scan']) > 0:
               meteor_crop_scan_status = 1
            else:
               meteor_crop_scan_status = 0
         else:
            meteor_crop_scan_status = 0
         date = mfn[0:10]
         mdir = "/mnt/ams2/meteors/" + date + "/" 
         meteor_scan_dir = "/mnt/ams2/METEOR_SCAN/" + date + "/" 
         if cfe(meteor_scan_dir,1) == 0:
            os.makedirs(meteor_scan_dir)
         
         meteor_scan_roi_file = meteor_scan_dir + mfn.replace(".mp4", "-roi.jpg")
         roi_file = mdir + mfn.replace(".mp4", "-roi.jpg")
         learning_roi_file = roi_file.replace("/mnt/ams2/meteors/" + date + "/" , "/mnt/ams2/datasets/images/training/meteors/")

         roi = [0,0,0,0]
         if "roi" not in meteor_data:
            if "meteor_scan_meteors" in meteor_data:
                if len(meteor_data['meteor_scan_meteors']):
                    roi = meteor_data['meteor_scan_meteors'][0]['roi']
         else:
            roi = meteor_data['roi']
         meteor_data['roi'] = roi

         if cfe(roi_file) == 1 and cfe(learning_roi_file) == 1 and cfe(meteor_scan_roi_file) == 1:
            print("ROI GOOD", roi_file)
            roi_img = cv2.imread(roi_file)
            all_roi_imgs[mfn] = roi_img
         else:

            print("ROI BAD", roi_file)
            # MAKE NEW ROI
            stack_file = mfn.replace(".mp4", "-stacked.jpg")
            stack_img = cv2.imread(mdir + stack_file)
            ih,iw = stack_img.shape[0:2]
            if "roi" in meteor_data:
               roi =meteor_data['roi']
            elif "meteor_scan_meteors" in meteor_data:
               if len(meteor_data['meteor_scan_meteors']) > 0:
                  roi =meteor_data['meteor_scan_meteors'][0]['roi']
            print("ROI:", roi)
            if sum(roi) != 0:
               x1,y1,x2,y2= int(roi[0]), int(roi[1]), int(roi[2]), int(roi[3])
               x1,y1,x2,y2 = self.bound_crop(x1,y1,x2,y2,iw,ih)
               self.scan_data[mfn]['roi'] = [x1,y1,x2,y2]
               roi_img =stack_img[y1:y2,x1:x2]
               all_roi_imgs[mfn] = roi_img
               cv2.imwrite(roi_file, roi_img,[cv2.IMWRITE_JPEG_QUALITY, 70])
               cv2.imwrite(meteor_scan_roi_file, roi_img,[cv2.IMWRITE_JPEG_QUALITY, 70])
               cv2.imwrite(learning_roi_file, roi_img,[cv2.IMWRITE_JPEG_QUALITY, 70])
               print("SAVED:", roi_file)
               print("SAVED:", learning_roi_file)
               #cv2.rectangle(stack_img, (int(x1), int(y1)), (int(x2) , int(y2)), (255, 255, 255), 1)
               #cv2.imshow('pepe', stack_img)
               #cv2.waitKey(30)

         ms_result = meteor_data['meteor_scan_result']
         all_status[mfn] = [meteor_scan_status,meteor_crop_scan_status] 
         print("MS RESULT:", ms_result)
         print(mfn, meteor_scan_status, meteor_crop_scan_status,ms_result)

      # make all meteor composite image

      blank_image = np.zeros((1080,1920,3),dtype=np.uint8)

      row = 0
      col = 0
      thumb_size = 100
      max_rows = int(1080/thumb_size)
      max_cols = int(1920/thumb_size)
      print("MAX METEORS ON 1 FRAME:", max_rows, max_cols, max_rows * max_cols)
      print("TOTAL WE HAVE:", len(all_roi_imgs.keys()))
      cc = 0
      rc = 0
      for roi_key in all_roi_imgs:
         mod = 0
         roi_img = all_roi_imgs[roi_key]
         roi_img = cv2.resize(roi_img, (thumb_size,thumb_size))
         x1 = cc * thumb_size 
         x2 = x1 + thumb_size
         y1 = rc * thumb_size
         y2 = y1 + thumb_size

         print("RC:CC", rc,cc, max_rows, max_cols)
         print("XY", x1, y1, x2, y2)
         print(roi_img.shape)
         blank_image[y1:y2,x1:x2] = roi_img
         if self.show == 1:
            cv2.imshow('pepe', blank_image)
            cv2.waitKey(30)
         if cc == max_cols - 1:
            rc += 1
            cc = 0
            mod = 1
         else:
            mod = 0


         cc += 1 - mod
         print("CC/MAX RC/MAX", cc, max_cols, rc, max_rows)
         if rc == max_rows :

            print("MAX ROWS AND COLS MET!")
            blank_image = np.zeros((1080,1920,3),dtype=np.uint8)
            cc = 0
            rc = 0
            mod = 0



      with open(self.SCAN_FILE, 'wb') as handle:
         pickle.dump(self.scan_data, handle, protocol=pickle.HIGHEST_PROTOCOL)
      print("SAVED", self.SCAN_FILE)


      # next check and make sure we have all meteors for the month

      mdirs = glob.glob("/mnt/ams2/meteors/" + self.month + "*")
      mds = []
      for md in mdirs:
         if cfe(md,1) == 1:
            mds.append(md + "/")
      for md in mds:
         self.get_mfiles( md)
         for mfile in self.mfiles:
            mfn = mfile.split("/")[-1]
            if mfn in self.scan_data:
               meteor_data = self.scan_data[mfn]
               if len(meteor_data['meteor_scan_meteors']) > 0:
                  meteor_data['meteor_scan_result'] = 1
               else:
                  meteor_data['meteor_scan_result'] = 0 
               self.scan_data[mfn] = meteor_data


            else:
               meteor_data = {}
               meteor_data['mfn'] = mfn

               mfile = mfile.replace(".mp4", ".json")
               my_meteor = Meteor(meteor_file=md+ mfile)
               my_meteor.meteor_scan()
               total_meteors = len(my_meteor.meteor_scan_meteors)
               meteor_data['mfn'] = mfn
               if total_meteors > 0:
                  mjf = "/mnt/ams2/meteors/" + mfn[0:10] + "/" + mfn.replace(".mp4", ".json")
                  if cfe(mjf) == 1:
                     mj = load_json_file(mjf)
                     mj['meteor_scan_meteors'] = my_meteor.meteor_scan_meteors
                     if "roi" not in mj:
                        if len(my_meteor.meteor_scan_meteors) > 0:
                           roi = my_meteor.meteor_scan_meteors[0]['roi']
                           if sum(roi) > 0:
                              mj['roi'] = roi 
                     save_json_file(mjf, mj)
                     print("SAVED:", mjf)

               # MJ VALS WE WANT TO GRAB FOR THE SCAN DB:
               #  version, dfv, manual_changes, aws_status, sync_status
               #  all_media_file, calib info (base & stars)
               mj_info = self.get_mj_info(my_meteor)
               meteor_data['mj_info'] = mj_info
               if 'hd_trim' in my_meteor.mj:
                  if cfe(my_meteor.mj['hd_trim']) == 1:
                     meteor_data['hd_trim'] = my_meteor.mj['hd_trim']

               meteor_data['total_meteors'] = total_meteors
               meteor_data['meteor_scan_meteors'] = my_meteor.meteor_scan_meteors
               meteor_data['meteor_scan_nonmeteors'] = my_meteor.meteor_scan_nonmeteors
               if len(meteor_data['meteor_scan_meteors']) > 0:
                  meteor_data['meteor_scan_result'] = 1
               else:
                  meteor_data['meteor_scan_result'] = 0 
               self.scan_data[mfn] = meteor_data

      # Store data (serialize)
      with open(self.SCAN_FILE, 'wb') as handle:
         pickle.dump(self.scan_data, handle, protocol=pickle.HIGHEST_PROTOCOL)
      print("SAVED", self.SCAN_FILE)

      print("FIRST SCAN DONE FOR ALL METEORS")

      # now do crop scan if needed 
      for key in self.scan_data:
         hc = 0
         tmsm = 0
         tnmsm = 0
         month = key[0:7]
         day = key[0:10]
         mdir = "/mnt/ams2/meteors/" + day + "/"
         cloud_files_dir = mdir + "/cloud_files/" 
         cloud_stage_dir = mdir + "/cloud_stage/" 
         meteor_learning_dir = "/mnt/ams2/datasets/images/training/meteors/" 
         non_meteor_learning_dir = "/mnt/ams2/datasets/images/training/nonmeteors/" 
         sd_stack_file = mdir + key.replace(".mp4", "-stacked.jpg")
         mjf = mdir + key.replace(".mp4", ".json")
         err_desc = ""
         
         if cfe(mjf) == 0:
            err_desc = "NO MJF?"
            deleted_keys.append(key)
         if cfe(sd_stack_file) == 1:
            sd_img = cv2.imread(sd_stack_file)
         else:
            continue

         # check the job status first before continue...

         roi = [0,0,0,0]
         if "hc" in self.scan_data[key]:
            hc = 1
         if "roi" in self.scan_data[key]:
            roi = self.scan_data[key]['roi']


         if "meteor_scan_meteors" not in self.scan_data[key] and sum(roi) != 0 and "meteor_scan_crop_scan_status" not in self.scan_data[key]:
            jobs_scan = 0
         else:
            jobs_scan = 1 

         if "meteor_scan_crop_scan" not in self.scan_data[key] and sum(roi) != 0 and "meteor_scan_crop_scan_status" not in self.scan_data[key]:
            jobs_scan_crop = 0
         else:
            jobs_scan_crop = 1 
 
         # other jobs: hd_scan, calibration, media
         #for fkey in self.scan_data[key]:
         #   print(fkey)
         print(key, jobs_scan, jobs_scan_crop)
         if jobs_scan == 1 and jobs_scan_crop == 1:
            print("DONE.", key)
            #continue
         else:
            print("THIS IS NOT DONE YET?")
            print(key, self.scan_data[key])
            print(key, jobs_scan, jobs_scan_crop)


         roi = [0,0,0,0]
         if "hc" in self.scan_data[key]:
            hc = 1
         if "roi" in self.scan_data[key]:
            roi = self.scan_data[key]['roi']
            print("USING HUMAN ROI")
         if "meteor_scan_meteors" in self.scan_data[key]:
            msm = self.scan_data[key]['meteor_scan_meteors']
            nmsm = self.scan_data[key]['meteor_scan_nonmeteors']
            tmsm = len(msm)
            tnmsm = len(nmsm)
         if sum(roi) == 0 and tmsm > 0:
            print("USING ORIG SCAN ROI")
            roi = msm[0]['roi']
         x1,y1,x2,y2 = roi
         x1,y1,x2,y2 = int(x1),int(y1),int(x2),int(y2)  
         roi = [x1,y1,x2,y2]
         if sum(roi) == 0:
            continue

         if self.show == 1:
            cv2.rectangle(sd_img, (int(x1), int(y1)), (int(x2) , int(y2)), (255, 255, 255), 1)
            cv2.imshow('pepe', sd_img)
         final_objects = {}
         if "meteor_scan_crop_scan" not in self.scan_data[key] and sum(roi) != 0 and "meteor_scan_crop_scan_status" not in self.scan_data[key]:
         #if True:
            self.roi = roi
            final_objects = self.meteor_scan_crop(mjf)
            for obj in final_objects:

               status, report = Detector.analyze_object(final_objects[obj])
               class_type = final_objects[obj]['report']['class']
            if len(final_objects) == 0:
               self.scan_data[key]['meteor_scan_crop_scan'] = {}
               self.scan_data[key]['meteor_scan_crop_scan_status'] = 0
            else:
               self.scan_data[key]['meteor_scan_crop_scan'] = final_objects 
               self.scan_data[key]['meteor_scan_crop_scan_status'] = 1
            for obj in final_objects:
               if final_objects[obj]['report']['class'] != 'meteor':
                  continue
               ox1 = int(min(final_objects[obj]['oxs']))
               oy1 = int(min(final_objects[obj]['oys']))
               ox2 = int(max(final_objects[obj]['oxs'])) + int(max(final_objects[obj]['ows']))
               oy2 = int(max(final_objects[obj]['oys'])) + int(max(final_objects[obj]['ohs']))
               cv2.rectangle(sd_img, (ox1,oy1),(ox2,oy2), (255, 255, 255), 1)

               for i in range(0,len(final_objects[obj]['ofns'])):
                  x = final_objects[obj]['oxs'][i]
                  y = final_objects[obj]['oys'][i]
                  w = final_objects[obj]['ows'][i]
                  h = final_objects[obj]['ohs'][i]
                  cx = int(x + (w/2))
                  cy = int(y + (h/2))
                  print("FINAL OBJECTS:", len(final_objects.keys() ))
                  rgb_val = final_objects[obj]['rgb'][i]
                  if final_objects[obj]['ransac'] != 0:
                     if final_objects[obj]['ransac'][7][i] == True:
                        sd_img[cy,cx] = rgb_val
                     else:
                        sd_img[cy,cx] = [0,0,255] 
                  else:
                     sd_img[cy,cx] = [0,0,255] 
                  
                  #cv2.rectangle(sd_img, (int(x), int(y)), (int(x+w) , int(y+h)), (255, 255, 255), 1)
               self.scan_data[key]['meteor_scan_crop_scan'] = final_objects
               self.scan_data[key]['meteor_scan_crop_scan_status'] = 1
         else:
            print("CROP SCAN ALREADY DONE!", key)
         if self.show == 1:
            cv2.imshow("FINAL", sd_img)
            cv2.waitKey(30)


         print(key, self.scan_data[key]['meteor_scan_result'], hc, roi, tmsm, tnmsm)
         if len(final_objects.keys())  > 0:
            mjf = "/mnt/ams2/meteors/" + mfn[0:10] + "/" + mfn.replace(".mp4", ".json")
            if cfe(mjf) == 1:
               mj = load_json_file(mjf)
               mj['meteor_scan_crop_meteors'] = final_objects
               save_json_file(mjf,mj)
      for key in deleted_keys:
         del self.scan_data[key]

      with open(self.SCAN_FILE, 'wb') as handle:
         pickle.dump(self.scan_data, handle, protocol=pickle.HIGHEST_PROTOCOL)

   def debug_meteor(self, mf):
      mday = mf[0:10]
      mdir = "/mnt/ams2/meteors/" + mday + "/" 
      mj = load_json_file(mdir + mf)
      mjr = load_json_file(mdir + mf.replace(".json", "-reduced.json"))
      stack_img = cv2.imread(mj['sd_stack'])
      ih, iw = stack_img.shape[:2]
      hdm_x = 1920/ iw
      hdm_y = 1080/ ih
      x1,y1,x2,y2 = mj['roi']
      roi_img = stack_img[y1:y2,x1:x2]

      cv2.rectangle(stack_img, (int(x1), int(y1)), (int(x2) , int(y2)), (255, 255, 255), 1)
      for row in mjr['meteor_frame_data']:
         print(row[2],row[3],row[4],row[5])
         sd_x = row[2] + (row[4]/2)
         sd_y = row[3] + (row[5]/2)
         sd_x = int(sd_x/hdm_x)
         sd_y = int(sd_y/hdm_y)
         roi_x = sd_x - x1
         roi_y = sd_y - y1
         print("RXVAL", roi_x,roi_y)
         cv2.rectangle(roi_img, (roi_x-2, roi_y-2), (roi_x+2 , roi_y+2), (255, 255, 255), 1)
         cv2.rectangle(stack_img, (sd_x-2, sd_y-2), (sd_x+2 , sd_y+2), (255, 255, 255), 1)
      
      cv2.imshow('pepe', stack_img)
      cv2.imshow('roipepe', roi_img)
      cv2.waitKey(0)

   def get_default_calib(self,station_id,cam_id):
      mcp_file = "/mnt/archive.allsky.tv/" + station_id + "/CAL/DATA/mcp_" + station_id + "_" + cam_id + ".json"
      print(mcp_file)
      if cfe(mcp_file) == 1:
         mcp = load_json_file(mcp_file)
      
      default_calib = load_json_file("/mnt/archive.allsky.tv/" + station_id + "/CAL/" + station_id + "_cal_range.json")
      these_cals = []
      for data in default_calib:
         if data[0] == cam_id:
            these_cals.append(data)
      print(these_cals[0])
      cam,date1,date2,az,el,pos,px,res = these_cals[0]
      mcp['center_az'] = az
      mcp['center_el'] = el
      mcp['position_angle'] = pos
      mcp['pixscale'] = px
      return(mcp)

   def get_remote_calib(self,station_id,cam_id):
      calds = glob.glob("/mnt/archive.allsky.tv/" + station_id + "/CAL/SRC/CLOUD_CAL/*")
      cal_dirs = []
      for temp in calds:
         if cam_id in temp:
            cal_dirs.append(temp)
      for cald in cal_dirs:
         print("CAL DIR:", cald)
         rf = cald.split("/")[-1]
         cal_file = cald + "/" + rf + "-stacked-calparams.json"
         cp = load_json_file(cal_file)
         print(cal_file)
      return(cp)


   def remote_reduce(self, station_id, meteor_video_file):
      clip_start_datetime = self.starttime_from_file(meteor_video_file)
      (f_datetime, cam_id, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(meteor_video_file)
      json_conf = load_json_file("/mnt/archive.allsky.tv/" + station_id + "/CAL/as6.json")
      mcp = self.get_default_calib(station_id,cam_id)
      mcp = update_center_radec(meteor_video_file,mcp,json_conf)



      #cal_params = self.get_remote_calib(station_id,cam_id)
      # cam, date, date, az, el, pos, px
      #print(default_calib)
      #exit()
      print("REMOTE REDUCE:", station_id, meteor_video_file)
      frame_data = {}
      self.load_frames(meteor_video_file)
      fns = []
      cxs = []
      cys = []
      xds = []
      yds = []
      fn = 0
      last_cx = None
      for frame in self.sd_frames:
         sub = cv2.subtract(frame, self.sd_frames[0])
         thresh_val = 100
         gray_frame = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
         show_frame = frame.copy()
         _, thresh_frame = cv2.threshold(gray_frame.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         cnts = self.get_contours_simple(thresh_frame)
         frame_data[fn] = {}
         if len(cnts) >= 1:
            frame_data[fn]['cnt'] = cnts[0]
            cnts = sorted(cnts, key=lambda x: x[2]*x[3], reverse=True)  
            x,y,w,h,intensity,px_avg = cnts[0]
            cx = x + (w/2)
            cy = y + (h/2)
            frame_data[fn]['cx'] = cx
            frame_data[fn]['cy'] = cy
            cxs.append(cx)
            cys.append(cy)
            fns.append(fn)
         
         for i in range(0,len(cxs)):
             
            cv2.rectangle(show_frame, (int(cxs[i]-5), int(cys[i]-5)), (int(cxs[i]+5) , int(cys[i]+5)), (255, 255, 255), 1)
               #cv2.rectangle(thresh_frame, (int(cx-5), int(cy-5)), (int(x+w) , int(y+h)), (255, 255, 255), 1)
       

         if len(cnts) >= 1:
            if last_cx is not None:
               xdiff = cx - last_cx
               ydiff = cy - last_cy
               xds.append(xdiff)
               yds.append(ydiff)
            else:
               xdiff = 0
               ydiff = 0
               xds.append(xdiff)
               yds.append(ydiff)

            frame_data[fn]['xd'] = xdiff
            frame_data[fn]['yd'] = ydiff
            print(fn,x,y,w,h,cx,cy,intensity,px_avg, xdiff, ydiff)
         else:
            print(fn,"NO CNT")
         fn += 1
         cv2.imshow('pepe', show_frame)
         cv2.waitKey(30)
         if len(cnts) >= 1:
            last_cx = cx
            last_cy = cy

      total_xd = (cxs[0] - cxs[-1] ) * -1
      total_yd = (cys[0] - cys[-1] ) * -1
      med_xd = total_xd / (fns[-1] - fns[0])
      med_yd = total_yd / (fns[-1] - fns[0])

      total_xd2 = (cxs[25] - cxs[-10] ) * -1
      total_yd2 = (cys[25] - cys[-10] ) * -1

      med_xd2 = total_xd2 / (fns[-10] - fns[25])
      med_yd2 = total_yd2 / (fns[-10] - fns[25])

      print("FIRST MED XY:", med_xd, med_yd)
      i = 0
      last_cx = None
      first_cx = None

      beg_cx = cxs[25]
      beg_cy = cys[25]
      beg_fn = fns[25]

      mc = 0
      hdm_x = 1920 / self.sd_frames[0].shape[1] 
      hdm_y = 1080 / self.sd_frames[0].shape[0] 
      print("HDM:", hdm_x, hdm_y, self.sd_frames[0])
      exit()
      mfd = []
      for fn in frame_data:
         frame = self.sd_frames[fn]
         if "cnt" in frame_data[fn]:
            if first_cx is None:
               first_cx = frame_data[fn]['cx']
               first_cy = frame_data[fn]['cy']
               frame_data[fn]['hd_x'] = frame_data[fn]['cx'] * hdm_x
               frame_data[fn]['hd_y'] = frame_data[fn]['cy'] * hdm_y
               first_frame = fn
            if last_cx is not None:
               if mc < 25:
                  est_x = frame_data[fn]['cx']
                  est_y = frame_data[fn]['cy']
               else:
                  est_x = beg_cx + (med_xd2 * (fn - beg_fn))
                  est_y = beg_cy + (med_yd2 * (fn - beg_fn))
               frame_data[fn]['est_x'] = est_x
               frame_data[fn]['est_y'] = est_y
               frame_data[fn]['xd'] = frame_data[fn]['cx'] - last_cx
               frame_data[fn]['yd'] = frame_data[fn]['cy'] - last_cy
               frame_data[fn]['hd_x'] = frame_data[fn]['est_x'] * hdm_x
               frame_data[fn]['hd_y'] = frame_data[fn]['est_y'] * hdm_y
            else:
               frame_data[fn]['est_x'] = frame_data[fn]['cx'] 
               frame_data[fn]['est_y'] = frame_data[fn]['cy']
               frame_data[fn]['hd_x'] = frame_data[fn]['cx'] * hdm_x
               frame_data[fn]['hd_y'] = frame_data[fn]['cy'] * hdm_y


            last_cx = frame_data[fn]['cx']
            last_cy = frame_data[fn]['cy']
            mc += 1
         else:
            error = 0
         if "est_x" in frame_data[fn]:
            err_x = frame_data[fn]['cx'] - frame_data[fn]['est_x']
            err_y = frame_data[fn]['cy'] - frame_data[fn]['est_y']
            print(fn, "CXY:", frame_data[fn]['cx'], frame_data[fn]['cy'], "ESTXY:", frame_data[fn]['est_x'], frame_data[fn]['est_y'],err_x,err_y )

            frame_data[fn]['hd_x'] = frame_data[fn]['est_x'] * hdm_x
            frame_data[fn]['hd_y'] = frame_data[fn]['est_y'] * hdm_y

            ex1 = frame_data[fn]['est_x']-5
            ey1 = frame_data[fn]['est_y']-5
            ex2 = frame_data[fn]['est_x']+5
            ey2 = frame_data[fn]['est_y']+5

            cx1 = frame_data[fn]['cx']-5
            cy1 = frame_data[fn]['cy']-5
            cx2 = frame_data[fn]['cx']+5
            cy2 = frame_data[fn]['cy']+5

            cv2.rectangle(frame, (int(ex1), int(ey1)), (int(ex2) , int(ey2)), (255, 0, 255), 1)
            cv2.rectangle(frame, (int(cx1), int(cy1)), (int(cx2) , int(cy2)), (255, 255, 255), 1)

            extra_sec = int(fn) / 25
            frame_time = clip_start_datetime + datetime.timedelta(0,extra_sec)
            dt = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S.%f")
            frame_data[fn]['dt'] = dt
         else:
            print(fn)
         cv2.imshow('pepe', frame)
         cv2.waitKey(0)

      for fn in frame_data:
         if "hd_x" in frame_data[fn]:
            hd_x = frame_data[fn]['hd_x']
            hd_y = frame_data[fn]['hd_y']
            tx, ty, ra ,dec , az, el = XYtoRADec(hd_x,hd_y,meteor_video_file,mcp,json_conf)
            print("FINAL", fn, frame_data[fn]['hd_x'], frame_data[fn]['hd_y'], az,el) 
            mfd.append((frame_data[fn]['dt'],fn,frame_data[fn]['est_x']-5,frame_data[fn]['est_y']-5, 5,5,99,ra,dec,az,el))
         else:
            print(fn)
      for data in mfd:
         print(data)

   def make_meteor_jsons(self, sd_video_file, hd_video_file, mfd):
      mj = {}
      mjr = {}
      (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(sd_video_file)
      sd_fn, dir = fn_dir(sd_video_file)
      if hd_video_file is not None:
         hd_fn, dir = fn_dir(hd_video_file)
         hd_stack_fn = hd_fn.replace(".mp4", "-stacked.jpg")
      stack_fn = sd_fn.replace(".mp4", "-stacked.jpg")

      date = sd_fn[0:10]
      mdir = "/mnt/ams2/meteors/" + date + "/"
      mj["sd_video_file"] = mdir + sd_fn
      mj["sd_stack"] = mdir + stack_fn
      mj["sd_objects"] = []
      if hd_video_file is not None:
         mj["hd_trim"] = mdir + hd_fn
         mj["hd_stack"] = mdir + hd_stack_fn
         mj["hd_video_file"] = mdir + hd_fn
         mj["hd_trim"] = mdir + hd_fn
         mj["hd_objects"] = []
      mj["meteor"] = 1

      # reduce
      mjr['api_key'] = "123"
      mjr['station_name'] = STATION_ID
      mjr['device_name'] = cam
      mjr["sd_video_file"] = mdir + sd_fn
      mjr["sd_stack"] = mdir + stack_fn
      if hd_video_file is not None:
         mjr["hd_video_file"] = mdir + sd_fn
         mjr["hd_stack"] = mdir + stack_fn
      mjr["event_start_time"] = ""
      mjr["event_duration"] = ""
      mjr["peak_magnitude"] = ""
      mjr["start_az"] = ""
      mjr["start_el"] = ""
      mjr["end_az"] = ""
      mjr["end_el"] = ""
      mjr["start_ra"] = ""
      mjr["start_dec"] = ""
      mjr["end_ra"] = ""
      mjr["end_dec"] = ""
      mjr['meteor_frame_data'] = mfd
 


   def meteor_scan(self ):
      print("METEOR SCAN", self.meteor_file)
      bad = 0
      if "sd_video_file" in self.mj:
         self.load_frames(self.mj['sd_video_file'])
         if len(self.sd_frames) == 0:
            print("FRAME ARE 0 CAN'T SCAN!")
            return(0)


      else:
         print("No video file.")
         return()
      all_xs = [] 
      all_ys = [] 
      fn = 0
      frame_data = {}
      # find the first layer of contours
      objects = {}
      ih,iw = self.sd_sub_frames[0].shape[:2]
      for frame in self.sd_sub_frames:
         frame_data[fn] = {}
         thresh_val = 5 
         gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         gray_frame = cv2.subtract(gray_frame, self.median_mask)
         _, thresh_frame = cv2.threshold(gray_frame.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         cnts = self.get_contours_simple(gray_frame )
         print(fn, len(cnts))
         #if len(cnts) > 10:
         #   cnts = self.get_contours_simple(gray_frame)
         frame_data[fn]['cnts'] = cnts
         for cnt in cnts:
            x,y,w,h,intensity,px_avg = cnt
            cx = x + int(w/2) 
            cy = y + int(h/2) 
            oid, objects = Detector.find_objects(fn,x,y,w,h,cx,cy,intensity,objects, 50) 
         #print(fn, len(cnts))
         fn += 1

      total_objs = len(objects.keys())
      pobjs = 0
      meteors = 0
      bigobjs = 0
      self.meteor_scan_nonmeteors = []
      self.meteor_scan_meteors = []
      self.meteor_scan_crops = []

      #objects = self.merge_close_objects(objects)

      for obj in objects:
         cx1,cy1,cx2,cy2 = self.bound_object(objects[obj],iw,ih)
         obj_roi = [cx1,cy1,cx2,cy2]
         objects[obj]['roi'] = obj_roi
         if len(objects[obj]['ofns']) > 2:
            status, report = Detector.analyze_object(objects[obj])
            #print(obj, objects[obj], report['class'])
            objects[obj]['report'] = report
            #print(report['bad_items'])
            #print("BIG PERC", report['big_perc'])
            if (report['big_perc'] > .6):
               bigobjs += 1

            pobjs += 1
            if report['class'] == 'meteor':
               meteors += 1
            #   print(fn)
               crop = self.sd_stacked_image[cy1:cy2,cx1:cx2]
               crop = cv2.resize(crop, (150,150))
               if self.show == 1:
                  cv2.imshow('meteor crop', crop)
                  cv2.waitKey(30)
               self.meteor_scan_meteors.append(objects[obj])
               self.meteor_scan_crops.append(crop)
            else:
               self.meteor_scan_nonmeteors.append(objects[obj])
            if self.show == 1:
               cv2.rectangle(self.sd_stacked_image, (int(cx1), int(cy1)), (int(cx2) , int(cy2)), (255, 255, 255), 1)
               cv2.putText(self.sd_stacked_image, str(report['class']),  (cx1, cy1), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
      #print("TOTAL OBJS:", total_objs)
      #print("TOTAL Persistent OBJS:", pobjs)
      #print("TOTAL BIG OBJS:", bigobjs)
      #print("TOTAL METEORS:", meteors)

      # eval clip with all objects
      if (meteors >= 3 and total_objs > 10) or (meteors >= 2 and total_objs > 100) :
         self.meteor_scan_meteors = []
         cv2.putText(self.sd_stacked_image, "BAD CAPTURE",  (250, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 200, 200), 1)
         bad = 1 
         #for obj in objects:
         #   if len(objects[obj]['ofns']) > 2:
         #      print(obj, objects[obj]['ofns'])
         #      print(obj, objects[obj]['report'])
         if self.show == 1:
            cv2.imshow('pepe', self.sd_stacked_image)
            cv2.waitKey(0)
         #self.purge_bad_capture() 

      #print(objects)
      if self.show == 1:
         cv2.imshow('pepe', self.sd_stacked_image)
         cv2.waitKey(0)

      self.save_learning_dataset()
      return()

   def save_learning_dataset(self):
      # save non-meteor objects larger than 10x10 in the nonmeteor label
      # save meteor objects in the meteor label
      # use even width/height but do not resize

      fn_root = self.meteor_file.split("/")[-1].replace(".json", "")

      oc = 1
      for non_meteor in self.meteor_scan_nonmeteors:
         roi = non_meteor['roi']
         obj_id = non_meteor['obj_id']
         learning_file = "/mnt/ams2/datasets/images/training/nonmeteors/" + fn_root + "_obj" + str(obj_id) + ".jpg"
         x1,y1,x2,y2 = roi
         crop_img = self.sd_stacked_image_orig[y1:y2,x1:x2]
         if self.show == 1:
            cv2.imshow('non meteor crop', crop_img)
            cv2.waitKey(30)
         cv2.imwrite(learning_file,crop_img)
         print("save non meteor", learning_file,  roi)
         oc += 1
      oc = 1
      for meteor in self.meteor_scan_meteors:
         roi = meteor['roi']
         obj_id = meteor['obj_id']
         x1,y1,x2,y2 = roi
         crop_img = self.sd_stacked_image_orig[y1:y2,x1:x2]
         if self.show == 1:
            cv2.imshow('meteor crop', crop_img)
            cv2.waitKey(30)
         learning_file = "/mnt/ams2/datasets/images/training/meteors/" + fn_root + "_obj" + str(obj_id) + ".jpg"
         print("save meteor", learning_file,  roi)
         cv2.imwrite(learning_file,crop_img)
         oc += 1


   def merge_close_objects(self, objects):
      matrix = {}
      for obj in objects:
         status, report = Detector.analyze_object(objects[obj])
         objects[obj]['report'] = report
         matrix[obj] = {}
         matrix[obj]['parent'] = 0
         matrix[obj]['children'] = []
         matrix[obj]['min_x'] = min(objects[obj]['oxs']) 
         matrix[obj]['min_y'] = min(objects[obj]['oys']) 

         matrix[obj]['max_x'] = max(objects[obj]['oxs']) + max(objects[obj]['ows']) 
         matrix[obj]['max_y'] = max(objects[obj]['oys']) + max(objects[obj]['ohs'])
      for pobj in matrix:
         pclass = objects[pobj]['report']['class']
         pmin_x = matrix[pobj]['min_x']
         pmin_y = matrix[pobj]['min_y']
         pmax_x = matrix[pobj]['min_x']
         pmax_y = matrix[pobj]['min_y']
         for cobj in matrix:
            if cobj == pobj:
               continue
            cmin_x = matrix[cobj]['min_x']
            cmin_y = matrix[cobj]['min_y']
            cmax_x = matrix[cobj]['min_x']
            cmax_y = matrix[cobj]['min_y']
            dist = calc_dist((pmax_x,pmax_y),(cmin_x,cmin_y))
            if dist < 50:
               if matrix[cobj]['parent'] == 0 and len(matrix[cobj]['children']) == 0:
                  matrix[cobj]['parent'] = pobj
                  matrix[pobj]['children'].append(cobj) 
                  print("PARENT, CHILD, DIST", pobj, cobj, dist)
            else:
               print("NO PARENT, CHILD, DIST", pobj, cobj, dist)


      new_objects = {}
      for obj in matrix:
         if matrix[obj]['parent'] == 0 and len(matrix[obj]['children']) == 0:
            print("NO RELATIONS/UNIQUE", obj, matrix[obj])
            new_objects[obj] = objects[obj]
         elif matrix[obj]['parent'] == 0 and len(matrix[obj]['children']) > 0 :
            print("PARENT", obj, matrix[obj])
            parent_object = objects[obj]

            pclass = parent_object['report']['class']
            for child in matrix[obj]['children']:
               child_object = objects[child]
               ok = 1
               if pclass == 'meteor' :
                  if abs(child_object['ofns'][0] - parent_object['ofns'][-1]) < 5:
                     ok = 1
                  else:
                     ok = 0
               if ok == 1:
                  for i in range(0, len(child_object['ofns'])):
                     parent_object['ofns'].append(child_object['ofns'][i])
                     parent_object['oxs'].append(child_object['oxs'][i])
                     parent_object['oys'].append(child_object['oys'][i])
                     parent_object['ows'].append(child_object['ows'][i])
                     parent_object['ohs'].append(child_object['ohs'][i])
                     parent_object['ccxs'].append(child_object['ccxs'][i])
                     parent_object['ccys'].append(child_object['ccys'][i])
                     parent_object['oint'].append(child_object['oint'][i])
            
               
            new_objects[obj] = parent_object
         else:
            print("   CHILD", obj, matrix[obj])



      print("merge obj done?", len(objects.keys()), len(new_objects.keys()))
      for obj_id in new_objects:
         obj = new_objects[obj_id]
         if len(obj['ofns']) >= 3:
            print(obj['ofns'])
            print(obj['oxs'])
            print(obj['oys'])
            print(obj['ccxs'])
            print(obj['ccys'])
            print(obj_id, obj['report'], "\n")
      return(new_objects)            

   def purge_bad_capture(self):
      hd_file = self.mj['hd_trim']
      sd_file = self.mj['sd_video_file']
      print("SD", sd_file)
      print("HD", hd_file)
      sd_fn = sd_file.split("/")[-1]
      hd_fn = hd_file.split("/")[-1]
      sd_wild = sd_fn.replace(".mp4", "*")
      hd_wild = sd_fn.replace(".mp4", "*")
      date = sd_wild[0:10]
      cloud_dir = "/mnt/ams2/meteors/" + date + "/cloud_files/"
      cloud_stage = "/mnt/ams2/meteors/" + date + "/cloud_stage/"
      meteor_dir = "/mnt/ams2/meteors/" + date + "/"
      bad_dir = "/mnt/ams2/bad_meteors/" + date + "/"
      if cfe(bad_dir,1) == 0:
         os.makedirs(bad_dir)
      cmd = "mv " + meteor_dir + sd_wild + " " + bad_dir
      print(cmd)
      os.system(cmd)

      cmd = "mv " + meteor_dir + hd_wild + " " + bad_dir
      print(cmd)
      os.system(cmd)

      cmd = "rm " + cloud_dir + sd_wild 
      print(cmd)
      os.system(cmd)

      cmd = "rm " + cloud_dir + hd_wild 
      print(cmd)
      os.system(cmd)

   def bound_object(self,obj,iw,ih):
      max_x = max(obj['oxs']) + max(obj['ows'])
      min_x = min(obj['oxs'])
      max_y = max(obj['oys']) + max(obj['ohs'])
      min_y = min(obj['oys'])

      if max_x - min_x > max_y - min_y:
         dim = max_x - min_x
      else:
         dim = max_y - min_y
      if dim < 250:
         dim = dim * 2.5

      cx = int((max_x+min_x) / 2)
      cy = int((max_y+min_y) / 2)

      x1 = cx - int(dim / 2)
      y1 = cy - int(dim / 2)
      x2 = cx + int(dim / 2)
      y2 = cy + int(dim / 2)

      if x1 < 0:
         x1 = 0
         x2 = dim
      if y1 < 0:
         y1 = 0
         y2 = dim
      if x2 > iw:
         x2 = iw
         x1 = iw - dim
      if y2 > ih:
         y2 = ih
         y1 = ih - dim

      return(int(x1),int(y1),int(x2),int(y2))

   def which_cnts(self,cnt_res):
      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res
      return(cnts)


   def dom_meteor(self, meteors):
      rpt = {}
      meteor_dict = {}
      for meteor in meteors:
         oid = meteor['obj_id']
         meteor_dict[oid] = meteor
         if oid not in rpt:
            rpt[oid] = {}
            rpt[oid]['score'] = 0
         rpt[oid]['fnlen'] = len(meteor['ofns'])
         rpt[oid]['sum_int'] = sum(meteor['oint'])
         tcx = int(meteor['oxs'][-1] + (meteor['ows'][-1]/2))
         tcy = int(meteor['oys'][-1] + (meteor['ohs'][-1]/2))
         cx = int(meteor['oxs'][0] + (meteor['ows'][0]/2))
         cy = int(meteor['oys'][0] + (meteor['ohs'][0]/2))
         rpt[oid]['dist'] = calc_dist((cx,cy),(tcx,tcy))
      best_len = 0
      best_dist = 0
      best_int = 0
      best_len_id = 0
      best_dist_id = 0
      best_int_id = 0
      for oid in rpt:
         print(oid, rpt[oid])
         if rpt[oid]['fnlen'] > best_len:
            best_len = rpt[oid]['fnlen']
            best_len_id = oid
         if rpt[oid]['sum_int'] > best_int:
            best_int = rpt[oid]['sum_int']
            best_int_id = oid
         if rpt[oid]['dist'] > best_dist:
            best_dist = rpt[oid]['dist']
            best_dist_id = oid
      rpt[best_len_id]['score'] += 1
      rpt[best_int_id]['score'] += 1
      rpt[best_dist_id]['score'] += 1
      final_score = []
      for oid in rpt:
         print("RPT:", oid, rpt[oid])
         final_score.append((oid,rpt[oid]['score']))
      
      final_score = sorted(final_score, key=lambda x: x[1], reverse=True)  
      print("FINAL SCORE:", final_score)
      dom_meteor_id = final_score[0][0]
      print("DOM METEOR_ID:", dom_meteor_id)
      dom_meteor = meteor_dict[dom_meteor_id]
      return(dom_meteor)
       

   def get_contours_in_crop(self,sub,past_cnts=[]):

      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub)

      thresh_val = int(max_val * .50)
      avg_px = np.mean(sub)
      for x,y,w,h in past_cnts:
         sub[y:y+h,x:x+w] = 0
      if thresh_val < avg_px + 10:
         thresh_val = avg_px + 10
      _, thresh_img = cv2.threshold(sub.copy(), thresh_val, 255, cv2.THRESH_BINARY)
      cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      cnts = self.which_cnts(cnt_res)

      conts = []
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         intensity = int(np.sum(sub[y:y+h,x:x+w]))
         px_avg = intensity / (w*h)
         if w >= 1 and h >= 1 and px_avg > 3:
            conts.append((x,y,w,h,intensity,px_avg))
      if self.show == 1:
         cv2.imshow('pepe', thresh_img)
         cv2.waitKey(30)

      return(conts)


   def get_contours_simple(self,sub):

      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub)

      thresh_val = int(max_val * .70)
      avg_px = np.mean(sub)
      if thresh_val < avg_px + 10:
         thresh_val = avg_px + 10
      _, thresh_img = cv2.threshold(sub.copy(), thresh_val, 255, cv2.THRESH_BINARY)
      cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      cnts = self.which_cnts(cnt_res)
      if len(cnts) > 25:
         thresh_val = 10 
         _, thresh_img = cv2.threshold(sub.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
         cnts = self.which_cnts(cnt_res)
      if len(cnts) > 25:
         thresh_val = 15 
         _, thresh_img = cv2.threshold(sub.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
         cnts = self.which_cnts(cnt_res)
      if len(cnts) > 25:
         thresh_val = 20
         _, thresh_img = cv2.threshold(sub.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
         cnts = self.which_cnts(cnt_res)
      if len(cnts) > 25:
         thresh_val = 25
         _, thresh_img = cv2.threshold(sub.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
         cnts = self.which_cnts(cnt_res)
      if len(cnts) > 25:
         thresh_val = 50 
         _, thresh_img = cv2.threshold(sub.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
         cnts = self.which_cnts(cnt_res)
      avg_px = np.median(sub)

      conts = []
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         intensity = int(np.sum(sub[y:y+h,x:x+w]))
         px_avg = intensity / (w*h)
         if w >= 1 and h >= 1 and px_avg > 5:
            #print("     ",x,y,w,h,intensity,px_avg)
            conts.append((x,y,w,h,intensity,px_avg))
      if self.show == 1:
         cv2.imshow('pepe', thresh_img)
         cv2.waitKey(30)

      return(conts)


   def load_frames(self,vid_file):
      self.sd_stacked_image = None
      if cfe(vid_file) == 0:
         self.sd_frames = []
         print("vid file not found!", vid_file)
         return()
      cap = cv2.VideoCapture(vid_file)
      self.sd_frames = []
      self.sd_sub_frames = []
      self.sd_thresh_frames = []
      last_frame = None
      go = 1
      frame_count = 0
      while go == 1:
         _ , frame = cap.read()
         if frame is None:
            if frame_count <= 5 :
               cap.release()
               return
            else:
               go = 0
         if frame is not None:
            if last_frame is not None:
               sub = cv2.subtract(frame, last_frame)
               self.sd_sub_frames.append(sub)
            else:
               sub = cv2.subtract(frame, frame)
               self.sd_sub_frames.append(sub)
            self.sd_frames.append(frame)

            thresh_val = 5 
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, thresh_frame = cv2.threshold(gray_frame.copy(), thresh_val, 255, cv2.THRESH_BINARY)
            self.sd_thresh_frames.append(thresh_frame)

            if self.sd_stacked_image is None:
               self.sd_stacked_image = Image.fromarray(frame)
            else:
               frame_pil = Image.fromarray(frame)
               self.sd_stacked_image=ImageChops.lighter(self.sd_stacked_image,frame_pil)
         if frame_count > 1499:
            go = 0
         frame_count += 1
         last_frame = frame

      self.sd_stacked_image=np.asarray(self.sd_stacked_image)
      self.sd_stacked_image_orig=self.sd_stacked_image.copy()
      self.median_mask = cv2.convertScaleAbs(np.mean(np.array(self.sd_frames), axis=0))

      self.median_mask = self.change_brightness(self.median_mask, -35)

      self.median_mask = cv2.GaussianBlur(self.median_mask, (15, 15), 0)
      self.median_mask = cv2.dilate(self.median_mask, None , iterations=8)

      self.median_mask = cv2.cvtColor(self.median_mask, cv2.COLOR_BGR2GRAY)


      cap.release()
      return

   def change_brightness(self, img, value=30):
      hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
      h, s, v = cv2.split(hsv)
      v = cv2.add(v,value)
      v[v > 255] = 255
      v[v < 0] = 0
      final_hsv = cv2.merge((h, s, v))
      img = cv2.cvtColor(final_hsv, cv2.COLOR_HSV2BGR)
      return img

   def ransac_outliers(self,XS,YS,title):
      XS = np.array(XS)
      YS = np.array(YS)
      RXS = XS.reshape(-1, 1)
      RYS = YS.reshape(-1, 1)
      #oldway
      #XS.reshape(-1, 1)
      #YS.reshape(-1, 1)

      self.sd_min_max = [int(min(XS))-50, int(min(YS))-50, int(max(XS))+50, int(max(YS)+50)]

      if len(XS) > 0:
         lr = linear_model.LinearRegression()
         lr.fit(RXS,RYS)

         # find good and bad
         ransac = RANSACRegressor()
         ransac.fit(RXS,RYS)
         inlier_mask = ransac.inlier_mask_
         outlier_mask = np.logical_not(inlier_mask)

         # predict
         line_X = np.arange(RXS.min(),RXS.max())[:,np.newaxis]
         line_Y = lr.predict(line_X)
         line_y_ransac = ransac.predict(line_X)

         #print("I", inlier_mask)
         #print("O", outlier_mask)

      # make plot for ransac filter
      import matplotlib
      matplotlib.use('TkAgg')
      from matplotlib import pyplot as plt
      title += " " + str(len(RXS)) + " / " + str(len(XS))

      fig = plt.figure()
      plt.title(title)
      plt.scatter(RXS[inlier_mask], RYS[inlier_mask], color='yellowgreen', marker='.',
            label='Inliers')
      plt.scatter(RXS[outlier_mask], RYS[outlier_mask], color='gold', marker='.',
            label='Outliers')
      plt.plot(line_X, line_Y, color='navy', linewidth=1, label='Linear regressor')
      plt.plot(line_X, line_y_ransac, color='cornflowerblue', linewidth=1,
         label='RANSAC regressor')
      plt.legend(loc='lower right')
      plt.xlabel("X")
      plt.ylabel("Y")
      plt.xlim(min(XS)-25, max(XS)+100)
      plt.ylim(min(YS)-25, max(YS)+100)
      plt.gca().invert_yaxis()
      #plt.show()
      fig.clf()
      plt.close(fig)
      #plt.clf()
      #plt.cla()
      #plt.close()
      IN_XS = RXS[inlier_mask].tolist()
      IN_YS = RYS[inlier_mask].tolist()
      OUT_XS = RXS[outlier_mask].tolist()
      OUT_YS = RYS[outlier_mask].tolist()


      return(IN_XS,IN_YS,OUT_XS,OUT_YS,line_X.tolist(),line_Y.tolist(),line_y_ransac.tolist(),inlier_mask.tolist(),outlier_mask.tolist())

   def get_meteor_media_sync_status(self, sd_vid): 
      # determine the current sync status for this meteor. 
      # does the meteor exist in dynamo with the right version?
      # is the media fully uploaded to the cloud drive (tiny jpg, prev_jpg, prev_vid, final_vid)
      day = sd_vid[0:10]
      lcdir = "/mnt/ams2/meteors/" + day + "/cloud_files/"
      lc_stage_dir = "/mnt/ams2/meteors/" + day + "/cloud_files/"
      cloud_files = []
      if True:
         wild = sd_vid.replace(".mp4", "")
         print("GLOB", lcdir + "/*" + wild  + "*")
         cfs = glob.glob(lcdir + "/*" + wild + "*")
         for cf in cfs:
            el = cf.split("-")
            ext = el[-1]
            if ext == "vid.mp4" :
               ext = el[-2] + "-" + el[-1]
            if ext == "crop.jpg" or ext == "crop.mp4":
               ext = el[-2] + "-" + el[-1]
            cloud_files.append(ext)

      if True:
         all_files = cloud_files
         stage_files = glob.glob(lc_stage_dir + "/*" + wild + "*")
         for cf in cfs:
            el = cf.split("-")
            ext = el[-1]
            if ext == "vid.mp4" :
               ext = el[-2] + "-" + el[-1]
            if ext == "crop.jpg" or ext == "crop.mp4":
               ext = el[-2] + "-" + el[-1]
            all_files.append(ext)
     
      sync_status = cloud_files
      self.sync_status = cloud_files
      self.all_media_files = all_files
      return(sync_status)


   def get_mfiles(self, mdir):
      temp = glob.glob(mdir + "/*.json")
      for json_file in temp:
          if "import" not in json_file and "report" not in json_file and "reduced" not in json_file and "calparams" not in json_file and "manual" not in json_file and "starmerge" not in json_file and "master" not in json_file:
            vfn = json_file.split("/")[-1].replace(".json", ".mp4")
            self.mfiles.append(vfn)






   def get_mj_info(self, my_meteor):
      mj = my_meteor.mj
      if "sd_video_file" in mj:
         sd_vid = mj['sd_video_file']
      else:
         sd_vid = None
      if "hd_trim" in mj:
         hd_vid = mj['hd_trim']
      else:
         hd_vid = None
      red_data = my_meteor.red_data
      if red_data is not None:
         if "meteor_frame_data" in red_data:
            if len(red_data['meteor_frame_data']) > 0:
               mfd = red_data['meteor_frame_data']
               duration = len(red_data['meteor_frame_data']) / 25
               event_start_time = red_data['meteor_frame_data'][0][0]
            else:
               mfd = []
               duration = 0
               event_start_datetime = self.starttime_from_file(my_meteor.meteor_file)
               event_start_datetime = event_start_datetime.strftime("%Y_%m_%d_%H_%M_%S")

         else:
            mfd = []
            duration = 0
            event_start_datetime = self.starttime_from_file(my_meteor.meteor_file)
            event_start_datetime = event_start_datetime.strftime("%Y_%m_%d_%H_%M_%S")
      if True:
         if "user_mods" in mj:
            user_mods = mj['user_mods']
         else:
            user_mods = {}

         if "version" in mj:
            version = mj['version']
         else:
            version = 1
         if "dfv" in mj:
            dfv = mj['dfv']
         else:
            dfv = 1
         if "last_update" in mj:
            last_update = mj['last_update']
         else:
            last_update = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

         if "final_trim" in mj:
            final_trim = mj['final_trim']
         else:
            final_trim = {}


         if "all_media_files" in mj and "sync_status" in mj:
            all_media_files = mj['all_media_files']
            sync_status = mj['sync_status']
         else:
            my_meteor.get_meteor_media_sync_status(my_meteor.vid_fn)
            sync_status = my_meteor.sync_status
            all_media_files = my_meteor.all_media_files

         event_id = 0
         solve_status = 0
         if "multi_station_event" in mj:
            if "event_id" in mj['multi_station_event']:
               event_id = mj['multi_station_event']['event_id']
            if "solve_status" in mj['multi_station_event']:
               solve_status = mj['multi_station_event']['solve_status']

         if "ffp" in mj:
            ffp = mj['ffp']
         else:
            ffp = {}
            if "hd_trim" in mj:
               if cfe(mj['hd_trim']) == 1:
                  hd_vid = mj['hd_trim']
                  ffp['hd'] = ffprobe(mj['hd_trim'])
               else:
                  hd_vid = None
            else:
               hd_vid = None
            if "sd_video_file" in mj:
               if cfe(mj['sd_video_file']) == 1:
                  sd_vid = mj['sd_video_file']
                  ffp['sd'] = ffprobe(mj['sd_video_file'])
               else:
                  sd_vid = None
            else:
               sd_vid = None

         if "sd_video_file" in mj:
            if cfe(mj['sd_video_file']) == 1:
               sd_vid = mj['sd_video_file']
         if "hd_trim" in mj:
            if cfe(mj['hd_trim']) == 1:
               hd_vid = mj['hd_trim']

         if "crop_box" in mj:
            crop_box = mj['crop_box']
         else:
            print("DEFINE HD CROP BOX FROM MS METEOR ROI CROP")
         if "cp" in mj:
            cp = mj['cp']
            if "total_res_px" not in cp:
               cp['total_res_px'] = 9999
            if "cat_image_stars" not in cp:
               cp['cat_image_stars'] = []
            if math.isnan(cp['total_res_px']):
               cp['total_res_px'] = 9999
            calib = [cp['ra_center'], cp['dec_center'], cp['center_az'], cp['center_el'], cp['position_angle'], cp['pixscale'], float(len(cp['cat_image_stars'])), float(cp['total_res_px'])]
            if "cat_image_stars" in cp:
               cat_image_stars = cp['cat_image_stars']
            else:
               cat_image_stars = []
         else:
            cat_image_stars = []
            calib = []
      mj_info = {}
      print("SELF:",my_meteor.meteor_file)
      if sd_vid is not None and sd_vid != 0:
         mj_info['sd_vid'] = sd_vid.split("/")[-1]
      if hd_vid is not None and hd_vid != 0:
         mj_info['hd_vid'] = hd_vid.split("/")[-1]
      mj_info['dfv'] = dfv
      mj_info['version'] = version
      mj_info['ffp'] = ffp
      mj_info['calib'] = calib
      mj_info['cat_image_stars'] = cat_image_stars
      mj_info['sync_status'] = sync_status
      mj_info['all_media_files'] = all_media_files
      mj_info['user_mods'] = user_mods
      mj_info['event_id'] = event_id
      mj_info['solve_status'] = solve_status
      mj_info['last_update'] = last_update

      my_meteor.mj['last_update'] = last_update
      my_meteor.mj['all_media_files'] = all_media_files
      my_meteor.mj['sync_status'] = sync_status
      my_meteor.mj['ffp'] = ffp
      my_meteor.mj['version'] = version
      my_meteor.mj['dfv'] = dfv

      return(mj_info)

   def starttime_from_file(self, filename):
      (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(filename)
      trim_num = get_trim_num(filename)
      extra_sec = int(trim_num) / 25
      event_start_time = f_datetime + datetime.timedelta(0,extra_sec)
      return(event_start_time)

   def remake_mj(self, root_file):
      mfile = "/mnt/ams2/meteors/" + root_file[0:10] + "/" + root_file + ".json"
      (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(root_file)
      base_file = fy + "_" + fmon + "_" + fd + "_" + fh + "_" + fm
      hd_wild = "/mnt/ams2/meteors/" + root_file[0:10] + "/" + base_file + "*HD-meteor.mp4"
      pos_hds = glob.glob(hd_wild)
      def_mj = {}
      def_mj['sd_video_file'] = mfile.replace(".json", ".mp4")
      def_mj['sd_stack'] = mfile.replace(".json", "-stacked.jpg")

      if len(pos_hds) >= 1:
         def_mj['hd_trim'] = pos_hds[0]
         def_mj['hd_stack'] = pos_hds[0].replace(".mp4", "-stacked.mp4")
         def_mj['hd_video_file'] = pos_hds[0]
      return(def_mj)


