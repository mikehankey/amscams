import colorsys
from decimal import Decimal
import pickle
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
from lib.PipeAutoCal import gen_cal_hist,update_center_radec, get_catalog_stars, pair_stars, scan_for_stars, calc_dist, minimize_fov, AzEltoRADec , HMS2deg, distort_xy, XYtoRADec, angularSeparation
from lib.PipeUtil import load_json_file, save_json_file, cfe, convert_filename_to_date_cam,get_trim_num
from lib.FFFuncs import best_crop_size, ffprobe
import boto3
import socket




class Meteor():

   def __init__(self, meteor_file=None, min_file=None,detect_obj=None):
      self.show = 0
      self.DF = DisplayFrame()
      self.SCAN_DIR = "/mnt/ams2/METEOR_SCAN/"
      self.SCAN_REPORT_DIR = "/mnt/ams2/METEOR_SCAN/REPORTS/"
      if cfe(self.SCAN_DIR,1) == 0:
         os.makedirs(self.SCAN_DIR)
      if cfe(self.SCAN_REPORT_DIR,1) == 0:
         os.makedirs(self.SCAN_REPORT_DIR)
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



   def make_meteor_image_html(self, data):
      sd_vid = data['mfn']
      meteor_dir = "/mnt/ams2/meteors/" + sd_vid[0:10] + "/" 
      root_file = sd_vid.replace(".mp4", "")
      felm = root_file.split("_")
      year = felm[0]
      mon = felm[1]
      dom = felm[2]

      prev_img = sd_vid.replace(".mp4", "-prev.jpg")
      prev_img = self.station_id + "_" + prev_img
      stack_thumb = sd_vid.replace(".mp4", "-stacked-tn.jpg")
      ms_result = data['meteor_scan_result']


      if "hc" in data:
         thumb_color = "green"
      else:
         thumb_color = "white"

      icon_html = self.make_icons(self.station_id, sd_vid, thumb_color)
   
      meteor_link = "/meteor/" + self.station_id + "/" + sd_vid[0:10] + "/" + sd_vid
      if "meteor_scan_crop_scan" in data:
         if len(data['meteor_scan_crop_scan']) > 0:
            print(data['meteor_scan_crop_scan'])
            ms_result = 1
      if "roi" not in data:
         ms_result = 0
      if ms_result == "good" or str(ms_result) == "1" :
         # use the ROI image
         print("DATA:", data)
         for key in data:
            print(key)
         roi = data['roi']
         img_file = meteor_dir+ root_file + "-roi.jpg"
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
      img_url = img_file.replace("/mnt/ams2", "")
      # 2020_12_13_07_02_00_000_010005-trim-0314_obj5.jpg
      show_date = mon + "/" + dom
      img_html = """
         
         <div class="meteor_gallery" id="gl_{:s}_{:s}" style="background-color: #000000; background-image: url({:s}); background-repeat: no-repeat; background-size: 100%; width: {:s}px; height: {:s}px; border: 1px #000000 solid; float: left; color: #fcfcfc; margin:5px ">
         <div style='width: 100%; height:80%'>{:s}</div><div>{:s}</div></div>
      """.format(str(self.station_id), str(root_file), str(img_url), str(iw), str(ih),show_date, icon_html )
      return(img_html)

   def delete_local_meteor(self, sd_video_file, reclass): 
      month = sd_video_file[0:7]
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
         mj = load_json_file(mjf)
         if "hd_trim" in mj:
            hd_vid = mj['hd_trim'].split("/")[-1]
            hd_wild = hd_vid.replace(".mp4", "*")
         mj['meteor_deleted'] = reclass
         save_json_file(mjf, mj)

      # remove the file from the SCAN FILE

      SCAN_FILE = self.SCAN_DIR + self.station_id + "_" + month + "_scan.pickle"
      print ("DELETE FROM SCAN FILE!", SCAN_FILE)
      #try:
      if True:
         if cfe(SCAN_FILE) == 1:
            with open(SCAN_FILE, 'rb') as handle:
               scan_data = pickle.load(handle)
            print("MFN:", mfn)
            mfn = mfn.replace(".json", ".mp4")
            del(scan_data[mfn])
            # Store data (serialize)
            with open(SCAN_FILE, 'wb') as handle:
               pickle.dump(scan_data, handle, protocol=pickle.HIGHEST_PROTOCOL)
            print("SAVED", SCAN_FILE)
         else:
            print("COULD NOT FIND SCAN FILE",SCAN_FILE)
      #except:
      #   print("Failed to save pickle scan file", SCAN_FILE)


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
      


   def scan_report(self, scan_date, page_num=1,per_page=500):
      print("Scan report for " + scan_date, page_num, per_page)
      row_data = {}
      idx_data = {}
      if scan_date == "today":
         scan_date = datetime.datetime.now().strftime("%Y_%m_%d")   
      good_html = "<div class='container-fluid'>"
      bad_html = "<div class='container-fluid'>"
      month = scan_date[0:7]
      SCAN_FILE = self.SCAN_DIR + self.station_id + "_" + month + "_scan.pickle"

      if cfe(SCAN_FILE) == 1:
         with open(SCAN_FILE, 'rb') as handle:
            scan_data = pickle.load(handle)
      else:
         scan_data = {}
      print(len(scan_data.keys()), "meteor records for the month " + month)
      deleted_keys = []
      for key in sorted(scan_data.keys(), reverse=True):
         mjf = "/mnt/ams2/meteors/" + key[0:10] + "/" + key.replace(".mp4", ".json")
         if cfe(mjf) == 1:
            print("MJF GOOD:", mjf)
         else:
            print("MJF BAD:", mjf)
            deleted_keys.append(mjf)
            continue
         data = scan_data[key]
         row_data[key] = data
         ms_result = data['meteor_scan_result']
         if ms_result == 1 or ms_result == "1":
            ms_result = "good"
         ms_meteors = len(data['meteor_scan_meteors'])
         ms_non_meteors = len(data['meteor_scan_nonmeteors'])
         idx_data[key] = {} 
         idx_data[key]['msm'] = [] 
         i = 0
         for obj in row_data[key]['meteor_scan_meteors']:
            if "report" in obj:
               del obj['report']
               i += 1
               idx_data[key]['msm'].append(obj)
         if "roi" in row_data[key]:
            idx_data[key]['roi'] = row_data[key]['roi']
         if "hc" in row_data[key]:
            idx_data[key]['hc'] = 1 
         if "hd_trim" in row_data[key]:
            idx_data[key]['hdv'] = row_data[key]['hd_trim'].split("/")[-1]
         idx_data[key]['calib'] = row_data[key]['mj_info']['calib']
         #print("ROW:", row_data[key])
         if "event_id" in row_data[key]['mj_info']:
            event_id = row_data[key]['mj_info']['event_id']
         if "event_status" in row_data[key]['mj_info']:
            if event_id != 0 and event_id != "0":
               event_id += ":" + str(row_data[key]['mj_info']['event_status'])
               idx_data['e'] = event_id

         print ("{:s}    {:s}    {:s}    {:s}".format(key, str(ms_result),str(ms_meteors),str(ms_non_meteors)))
         img_html = self.make_meteor_image_html(data)
         print("MS RSULT!", ms_result)
         if str(ms_result) == "good" or str(ms_result) == "1" or ms_result == 1:
            good_html += img_html
         else:
            bad_html += img_html

      #for dk in deleted_keys:
      #   del scan_data[dk]

      good_html += "</div><div style='clear:both'></div>"
      bad_html += "</div><div style='clear:both'></div>"
      month_select = self.make_month_select(month)
      good_msg = "<table ><tr><td ><h3>Detections Classified as Meteors for " + month + "</h2></td><td>" + month_select + "</td></tr></table>"
      good_msg += "<p>if you do not see a meteor in the thumbnail it is either a bad capture or the meteor crop area is missing or wrong.<br>"
      good_msg += "In both cases click the thumbnail to fix the problem </p>"

      bad_msg = "<h3>Detections Classified as Non Meteors for " + month + "</h3>"
      bad_msg += "<p>Confirm these are bad meteors and they will be removed from the queue. <br>If you see good meteors in this section, human confirm them as meteors and they will move to the meteor confirmed list.</p>"
      all_html = good_msg + good_html + bad_msg + bad_html
      report_file = self.SCAN_REPORT_DIR + self.station_id + "_" + month + "_METEOR_SCAN.html"
      fp = open(report_file, "w")
      fp.write(all_html)
      print("saved ", report_file)
      stats = {}
      return(all_html, idx_data, stats)

   def make_icons(self, station_id, sd_vid, thumb_color="white"):
      video_url = "/meteors/" + sd_vid[0:10] + "/" + sd_vid
      key = station_id + ":" + sd_vid
      icon_html = """
         <table ><tr>
         <td><a class="video_link" data-id="video_link:{:s}:{:s}:{:s}" href="javascript:void(0)"><i class="bi bi-caret-right-square" style="color: white" data-toggle="popover" title="Play Video" data-content="SD Video"></i></a></td><td>
         <td><a class="confirm_meteor" data-id="confirm_meteor:{:s}:{:s}" href="javascript:void(0)"><i class="bi bi-hand-thumbs-up" style="color: {:s}" data-toggle="popover" title="Confirm Meteor Detection" data-content="Confirm Meteor Detection"></i></a></td><td>
         <td><a class="recrop_meteor" data-id="recrop_meteor:{:s}" href="javascript:void(0)"><i class="bi bi-crop" style="color: white" data-toggle="popover" title="Recrop ROI" data-content="Recrop ROI."></i></td><td>

      """.format(station_id, sd_vid, video_url,station_id,sd_vid,thumb_color, key)
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

 

   def update_roi_crop(self, sd_video_file, new_roi):
      # save in the original json file

      # save in pickle db
      # push to aws
      resp = {}
      resp['msg'] = str(sd_video_file) + str(new_roi)
      mjf = "/mnt/ams2/meteors/" + sd_video_file[0:10] + "/" + sd_video_file.replace(".mp4", ".json")
      if cfe(mjf) == 1:
         mj = load_json_file(mjf)
         mj['hc'] = 1
         mj['roi'] = new_roi
         save_json_file(mjf, mj)

      # update pickle
      month = sd_video_file[0:7]
      SCAN_FILE = self.SCAN_DIR + self.station_id + "_" + month + "_scan.pickle"
      print ("UPDATE SCAN FILE!", SCAN_FILE)
      key = sd_video_file
      if True:
         if cfe(SCAN_FILE) == 1:
            with open(SCAN_FILE, 'rb') as handle:
               scan_data = pickle.load(handle)
            data = scan_data[sd_video_file]
            if len(data['meteor_scan_meteors']) > 0:
               data['meteor_scan_meteors'][0]['roi'] = new_roi
            data['roi'] = new_roi
            data['hc'] = 1
            scan_data[key] = data

            with open(SCAN_FILE, 'wb') as handle:
               pickle.dump(scan_data, handle, protocol=pickle.HIGHEST_PROTOCOL)

         sd_stack_file = sd_video_file.replace(".mp4", "-stacked.jpg")
         roi_file = sd_video_file.replace(".mp4", "-roi.jpg")
         sd_img = cv2.imread("/mnt/ams2/meteors/" + sd_video_file[0:10] + "/" + sd_stack_file)
         x1,y1,x2,y2 = new_roi
         x1 = int(x1)
         y1 = int(y1)
         x2 = int(x2)
         y2 = int(y2)
         print(sd_img.shape)
         print(new_roi)
         roi_img = sd_img[y1:y2,x1:x2]
         cv2.imwrite("/mnt/ams2/meteors/" + sd_video_file[0:10] + "/" + roi_file, roi_img,[cv2.IMWRITE_JPEG_QUALITY, 70])
         cv2.imwrite("/mnt/ams2/datasets/images/training/meteors/" + roi_file, roi_img, [cv2.IMWRITE_JPEG_QUALITY, 70])
         year = sd_video_file[0:4]
         day = sd_video_file[0:10]
         cloud_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + year + "/" + day + "/" 
         os.system("cp /mnt/ams2/meteors/" + sd_video_file[0:10] + "/" + roi_file + " " + cloud_dir)
         print("/mnt/ams2/datasets/images/training/meteors/" + "/" + roi_file)
         print("cp /mnt/ams2/meteors/" + sd_video_file[0:10] + "/" + roi_file + " " + cloud_dir)


      return(resp)

   def make_month_select(self,select_month):
      pick_files = glob.glob("/mnt/ams2/METEOR_SCAN/*.pickle")
      options = ""
      for pick in pick_files:
         pick = pick.split("/")[-1]
         el = pick.split("_")
         year = el[1]
         mon = el[2]
         month = year + "_" + mon
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
      if x1 < 0:
         x1 = 0 
         x2 = x1 + cw
      if y1 < 0:
         y1 = 0 
         y2 = y1 + ch
      if x2 > img_w:
         x2 = img_w - 1
         x1 = x2 - cw
      if y2 > img_h:
         y2 = img_h - 1
         y1 = y2 - ch
      return(int(x1),int(y1),int(x2),int(y2))

   def meteor_scan_crop(self, mjf):
      if cfe(mjf) == 0:
         return({})
      mj = load_json_file(mjf)
      if "sd_video_file" in mj:
         self.load_frames(mj['sd_video_file'])
      else:
         print("NO VIDEO FILE!")
         retun()
      print("SCAN IN CROP!", len(self.sd_frames))
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
         all_cnts.append((x,y,w,h))


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
            if dist_from_start > last_dist_from_start or last_dist_from_start == 0:
               print(fn, "   *** FRAME DATA", fn, cx,cy,intensity,avg_px, dist_from_start)
            else:
               print(fn, "   *** REJECT FRAME DATA", fn, cx,cy,intensity,avg_px, dist_from_start)
         elif len(frame_data[fn]['cnts']) > 1:
            # merge / the cnts
            frame_data[fn]['cnts'] = self.merge_clean_cnts(frame_data[fn]['cnts'])
            if fc > 1:
               for cnt in frame_data[fn]['cnts']:
                  (fn,x,y,w,h,cx,cy,intensity, avg_px) = cnt
                  if first_x is not None:
                     dist_from_start = calc_dist((first_x,first_y),(cx,cy))
                  oid , objects = Detector.find_objects(fn,x,y,w,h,cx,cy,intensity,objects, 25 * crop_scale) 
                  if dist_from_start > last_dist_from_start or last_dist_from_start == 0 and first_x is not None:
                     print(fn, "   *** FRAME DATA", first_x, first_y, fn, cx,cy,intensity,avg_px, dist_from_start)
                  else:
                     print(fn, "   *** REJECT FRAME DATA", first_x, first_y, fn, cx,cy,intensity,avg_px, dist_from_start)
         else:
            print(fn, frame_data[fn])
         if first_x is None and len(frame_data[fn]['cnts']) > 0 and len(frame_data[fn+1]['cnts']) > 0:
            print("FIRST FRAME SET!", cx,cy)
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

         #print(obj_id, objects[obj_id])
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
               
            #print("FINAL OBJ", first_x, first_y, fn, cx,cy,dist_from_start,seg_len)

            ic += 1
            last_x = cx
            last_y = cy
            last_dist_from_start = dist_from_start

         end_found = 0
         while end_found == 0:
            len_fns = len(objects[obj_id]['ofns']) -1
            print("LEN FNS:", len_fns)
            last_item = len(objects[obj_id]['ofns']) -1
            last_seg_len = objects[obj_id]['seg_len'][last_item]

            if last_item - 1 < len(objects[obj_id]['ofns']) + 1:
               last_seg_len2 = objects[obj_id]['seg_len'][last_item-1]
            else:
               last_seg_len2 = 3
            print("LAST SEG2", last_item, len(objects[obj_id]['ofns']), last_seg_len2, last_seg_len)
            if (last_seg_len < 0 and last_item <= len(objects[obj_id]['ofns'])-1) or last_seg_len2 < 0:
               print("DELETE LAST FRAME!!!", last_seg_len, last_seg_len2)
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
         print("OBJID:", obj)
         print("FINAL OBJECT:", final_objects[obj]['oxs'], final_objects[obj]['oys'])
         status, report = Detector.analyze_object(final_objects[obj])
         final_objects[obj]['report'] = report
         try:
            ransac_result = self.ransac_outliers(final_objects[obj]['ccxs'],final_objects[obj]['ccys'],"RANSAC ON CROP POINTS")
            final_objects[obj]['ransac'] = ransac_result
         except:
            print("THIS IS BAD!", final_objects[obj])
            ransac_result = 0
            final_objects[obj]['ransac'] = ransac_result

      print("FINAL OBJECTS : ", final_objects)
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


   def check_scan_status_month(self):
      deleted_keys = []
      all_status = {}
      # first just display the current status of each file in the meteor scan for this month
      all_roi_imgs = {}
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
         meteor_scan_dir = "/mnt/ams2/meteors_scan/" + date + "/" 
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
                  rgb_val = final_objects[obj]['rgb'][i]
                  if final_objects[obj]['ransac'][7][i] == True:
                     sd_img[cy,cx] = rgb_val
                  else:
                     sd_img[cy,cx] = [0,0,255] 
                  #cv2.rectangle(sd_img, (int(x), int(y)), (int(x+w) , int(y+h)), (255, 255, 255), 1)
               self.scan_data[key]['meteor_scan_crop_scan'] = final_objects
               self.scan_data[key]['meteor_scan_crop_scan_status'] = 1
         else:
            print("CROP SCAN ALREADY DONE!", key)
         if self.show == 0:
            cv2.imshow("FINAL", sd_img)
            cv2.waitKey(30)


         print(key, self.scan_data[key]['meteor_scan_result'], hc, roi, tmsm, tnmsm)
      for key in deleted_keys:
         del self.scan_data[key]

      with open(self.SCAN_FILE, 'wb') as handle:
         pickle.dump(self.scan_data, handle, protocol=pickle.HIGHEST_PROTOCOL)

         

   def meteor_scan(self):
      print("METEOR SCAN", self.meteor_file)
      bad = 0
      if "sd_video_file" in self.mj:
         self.load_frames(self.mj['sd_video_file'])
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

      objects = self.merge_close_objects(objects)

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
            cv2.waitKey(30)
         #self.purge_bad_capture() 

      #print(objects)
      if self.show == 1:
         cv2.imshow('pepe', self.sd_stacked_image)
         cv2.waitKey(90)

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


      for obj in new_objects:
         print("NEW", obj, new_objects[obj])

      print("merge obj done?", len(objects.keys()), len(new_objects.keys()))
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
            print("     ",x,y,w,h,intensity,px_avg)
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
         print("THRESH VAL", thresh_val)
         _, thresh_img = cv2.threshold(sub.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
         cnts = self.which_cnts(cnt_res)
      if len(cnts) > 25:
         thresh_val = 15 
         print("THRESH VAL", thresh_val)
         _, thresh_img = cv2.threshold(sub.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
         cnts = self.which_cnts(cnt_res)
      if len(cnts) > 25:
         thresh_val = 20
         print("THRESH VAL", thresh_val)
         _, thresh_img = cv2.threshold(sub.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
         cnts = self.which_cnts(cnt_res)
      if len(cnts) > 25:
         thresh_val = 25
         print("THRESH VAL", thresh_val)
         _, thresh_img = cv2.threshold(sub.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
         cnts = self.which_cnts(cnt_res)
      if len(cnts) > 25:
         thresh_val = 50 
         print("THRESH VAL", thresh_val)
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
            print("     ",x,y,w,h,intensity,px_avg)
            conts.append((x,y,w,h,intensity,px_avg))
      if self.show == 1:
         cv2.imshow('pepe', thresh_img)
         cv2.waitKey(30)

      return(conts)


   def load_frames(self,vid_file):
      self.sd_stacked_image = None
      if cfe(vid_file) == 0:
         print("vid file not found!", vid_file)

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
      print(len(XS), len(YS))
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
         print(len(RXS))
         print(len(RYS))
         ransac.fit(RXS,RYS)
         inlier_mask = ransac.inlier_mask_
         outlier_mask = np.logical_not(inlier_mask)

         # predict
         line_X = np.arange(RXS.min(),RXS.max())[:,np.newaxis]
         line_Y = lr.predict(line_X)
         line_y_ransac = ransac.predict(line_X)

         print("I", inlier_mask)
         print("O", outlier_mask)

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


      return(IN_XS,IN_YS,OUT_XS,OUT_YS,line_X,line_Y,line_y_ransac,inlier_mask,outlier_mask)

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
          if "reduced" not in json_file and "calparams" not in json_file and "manual" not in json_file and "starmerge" not in json_file and "master" not in json_file:
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
