import requests
import random
import datetime
import boto3
import sqlite3
import platform
import math
import shutil
import json
from lib.PipeUtil import load_json_file, save_json_file
from lib.PipeVideo import load_frames_simple
import numpy as np
import sys
import os
import cv2
from Classes.ASAI import AllSkyAI
import redis
from Classes.Detector import Detector
DD = Detector()

class ReviewNetwork():
   def __init__(self, date):

      self.movie_counter = 0
      self.errors = []
      if os.path.exists("admin_conf.json") is True:
         self.admin_conf = load_json_file("admin_conf.json")
         self.data_dir = self.admin_conf['data_dir']
         self.learning_repo = "/mnt/f/AI/DATASETS/NETWORK_PREV/"
      else:
         self.data_dir = "/mnt/ams2/"
         self.learning_repo = "/mnt/ams2/AI/DATASETS/NETWORK_PREV/"

      print("Review Network Meteors")
      self.ASAI = AllSkyAI()
      self.ASAI.load_all_models()
      self.local_event_dir = "/mnt/f/EVENTS"
      self.cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS"
      self.cloud_dir = "/mnt/archive.allsky.tv/"


      self.year, self.month, self.day = date.split("_")
      self.date = date
      self.local_evdir = self.local_event_dir + "/" + self.year + "/" + self.month + "/" + self.day  + "/"
      self.cloud_evdir = self.cloud_event_dir + "/" + self.year + "/" + self.month + "/" + self.day   + "/"
      #self.s3_evdir = self.s3_event_dir + "/" + self.year + "/" + self.month + "/" + self.day   + "/"

      self.obs_dict_file = self.local_evdir + self.date + "_OBS_DICT.json"
      self.all_obs_file = self.local_evdir + self.date + "_ALL_OBS.json"
      self.all_obs_gz_file = self.local_evdir + self.date + "_ALL_OBS.json.gz"
      self.cloud_all_obs_file = self.cloud_evdir + self.date + "_ALL_OBS.json"
      self.cloud_all_obs_gz_file = self.cloud_evdir + self.date + "_ALL_OBS.json.gz"
      self.obs_review_file = self.local_evdir + date + "_OBS_REVIEWS.json"

      self.good_obs_json = None
      self.user =  os.environ.get("USERNAME")
      if self.user is None:
         self.user =  os.environ.get("USER")
      self.platform = platform.system()

      self.home_dir = "/home/" + self.user + "/"
      self.amscams_dir = self.home_dir + "amscams/"

      self.local_event_dir = self.data_dir + "/EVENTS"
      self.db_dir = self.local_event_dir + "/DBS/"
      if os.path.exists(self.db_dir) is False:
         os.makedirs(self.db_dir)
      self.cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS"
      self.s3_event_dir = "/mnt/allsky-s3/EVENTS"

      self.r = redis.Redis("allsky-redis.d2eqrc.0001.use1.cache.amazonaws.com", port=6379, decode_responses=True)
      self.API_URL = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi"
      self.dynamodb = boto3.resource('dynamodb')



      # DB FILE!
      self.db_file = self.db_dir + "/ALLSKYNETWORK_" + date + ".db"

      if os.path.exists(self.db_file) is False:
         os.system("cat ALLSKYNETWORK.sql | sqlite3 " + self.db_file)
      if os.path.exists(self.db_file) is False:
         print("DB FILE NOT FOUND.", self.db_file)
         return ()
      self.con = sqlite3.connect(self.db_file)
      self.con.row_factory = sqlite3.Row
      self.cur = self.con.cursor()

   def get_sql_events(self,date):
      sql = """
         SELECT event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,
                lats, lons, event_status, run_date, run_times
          FROM events
         WHERE event_minute like ?
      """
      vals = [date + "%"]
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      events = {}
      for row in rows:
         event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times, lats, lons, event_status, run_date, run_times = row
         events[event_id] = [event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times, lats, lons, event_status, run_date, run_times]
         print(event_id)
      return(events)

   def review_events(self,date):
      cv2.namedWindow("ALLSKYOS")
      self.year, self.month, self.day = date.split("_")
      self.date = date
      self.movie_dir = self.local_event_dir + "/" + self.year + "/" + self.month + "/" + self.day  + "/MOVIE/"
      self.local_evdir = self.local_event_dir + "/" + self.year + "/" + self.month + "/" + self.day  + "/"
      self.cloud_evdir = self.cloud_event_dir + "/" + self.year + "/" + self.month + "/" + self.day   + "/"
      self.all_obs_file = self.local_evdir + date + "_ALL_OBS.json"
      self.obs_review_file = self.local_evdir + date + "_OBS_REVIEWS.json"
      self.min_events = self.local_evdir + date + "_MIN_EVENTS.json"

      self.human_event_review_file = self.local_evdir + date + "_HUMAN_EVENT_REVIEW.json"
      if os.path.exists(self.movie_dir) is False:
         os.makedirs(self.movie_dir)

      if os.path.exists(self.human_event_review_file) is True:
         self.human_event_review_data = load_json_file(self.human_event_review_file) 
      else:
         self.human_event_review_data = {}
      self.obs_img_dir = self.local_event_dir + "/" + self.year + "/" + self.month + "/" + self.day   + "/OBS/"
      all_obs = load_json_file(self.all_obs_file)
      self.min_events = load_json_file(self.min_events)
      self.review_data = load_json_file(self.obs_review_file)
      rc = 0
      counter = 0

      self.events = self.get_sql_events(date)


      last_show_img = None
      skip = 10
      ec = 0
      for row in self.min_events:
         for eid in self.min_events[row].keys():
            if len(set(self.min_events[row][eid]['stations'])) > 1:
              # if ec < skip :
              #    continue
              # ec += 1

               avg_time = self.average_times(self.min_events[row][eid]['start_datetime'])
               self.min_events[row][eid]['stime'] = avg_time
               event_id = self.date_to_event_id(avg_time)
               self.event_id = event_id
               print("EVENT START TIME:", avg_time, event_id)
               print("EVENT ID:", event_id)
               sql_status =  self.events[event_id][9]
               if event_id in self.events:
                  print("EVENT SQL STATUS:", self.events[event_id][9])
               else:
                  print("EVENT ID NOT IN SQL!")
               event_file = self.local_evdir + event_id + "/" + event_id + "-event.json"
               fail_file = self.local_evdir + event_id + "/" + event_id + "-fail.json"
               if os.path.exists(event_file) is True:
                  try:
                     event_data = load_json_file(event_file)
                  except:
                     print("FAILED READING:", event_file)
               else:
                  event_data = {}
               if event_id in self.events:
                  event_data['sql_data'] = self.events[event_id]
                  event_data['event_id'] = event_id
               if os.path.exists(event_file):
                  wmpl_status = "SOLVED"
               elif os.path.exists(event_file) is False and os.path.exists(fail_file) is True:
                  wmpl_status = "FAILED"
               else:
                  wmpl_status = "PENDING"
               if sql_status != wmpl_status:
                  print("UPDATE SQL STATUS FOR EVENT ID!", event_id, wmpl_status)

               if row in self.human_event_review_data:
                  if eid in self.human_event_review_data[row] : 
                     if isinstance(self.human_event_review_data[row][eid], int) is True:
                        self.human_event_review_data[row][eid] = {}
                     if "human_key" in self.human_event_review_data[row][eid]:
                        human_key = self.human_event_review_data[row][eid]['human_key']
                     else:
                        human_key = None
                  else:
                     human_key = None
               else:
                  human_key = None
               ai_yns,ai_event_yn,comp_img,comp_clean_img = self.event_obs_comp(self.min_events[row][eid],counter ,human_key)
               if row not in self.human_event_review_data:
                  self.human_event_review_data[row] = {}
               if eid not in self.human_event_review_data[row]:
                  self.human_event_review_data[row][eid] = {}
               self.human_event_review_data[row][eid]['ai_event_yn'] = ai_event_yn
               if row not in self.human_event_review_data:
                  self.human_event_review_data[row] = {}

               print("saved:", self.human_event_review_file)
               counter += 1
               event_data['wmpl_status'] = wmpl_status 
               event_data['sql_status'] = sql_status
               event_data['human_key'] = human_key
               #if comp_img.shape[0] > 1080:
               #   comp_img = cv2.resize(comp_img,(1280,720))
               #   comp_clean_img = cv2.resize(comp_clean_img,(1280,720))
               show_img, console_img = self.make_console_image(comp_img, comp_clean_img, event_data)
               if last_show_img is not None:
                  self.transition_next_event(last_show_img, show_img,20)


               cv2.imshow('ALLSKYOS', show_img)
               key = cv2.waitKey(220)
               self.save_movie_frame(show_img)
               print("KEY IS", key)
               if key == 110 or key == 109:
                  if eid not in self.human_event_review_data[row]:
                     self.human_event_review_data[row][eid] = {}
                  self.human_event_review_data[row][eid]['human_key'] = key
                  save_json_file(self.human_event_review_file, self.human_event_review_data) 
               if key == 118:
                  self.play_videos(event_data, show_img, console_img)
               self.play_videos(event_data, show_img, console_img)
               last_show_img = show_img
         rc += 1
         #if rc > 100:
         #   exit()

   def play_videos(self, event_data, base_img_sm, base_image):
      orig_img = base_img_sm.copy() 
      show_img = orig_img.copy()
      desc = "Loading video frames..."
      cv2.putText(show_img, desc,  (int(show_img.shape[1]/4), int(show_img.shape[0]/2)), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,255,0), 1)
      cv2.imshow('ALLSKYOS', show_img)
      self.save_movie_frame(show_img)
      cv2.waitKey(120)
      obs = event_data['sql_data'][4]
      if isinstance(obs,str) is True:
         obs = json.loads(obs)
      video_files = []
      for root_fn in obs:
         print(root_fn)
         cloud_media = self.get_cloud_urls(root_fn)
         for media_type in cloud_media:
            if media_type == "prev_vid_file":
               local_file = cloud_media['local_cache_dir'] + cloud_media[media_type].split("/")[-1]
               video_files.append((root_fn, local_file))
               if os.path.exists(local_file) is False:
                  cmd = "cp " + cloud_media[media_type] + " " + cloud_media['local_cache_dir'] + cloud_media[media_type].split("/")[-1]
                  print(cmd)
                  os.system(cmd)
         print("CM", cloud_media)



      # now get the frames for each video file
      self.all_frames = {}
      self.marked_frames = {}
      fc = 0
      flat_frames = []
      first_stack_img = None
      for root_fn, video_file in video_files:
         vid_fn = video_file.split("/")[-1]

         stack_img = None
         if stack_img is None:
            if root_fn in self.stack_imgs:
               stack_img = self.stack_imgs[obs[0]]
            else:
               st = root_fn.split("_")[0]
               rt = root_fn.replace(st + "_", "")
               if rt in self.stack_imgs:
                  stack_img = self.stack_imgs[rt]
         if first_stack_img is None and stack_img is not None:
            first_stack_img = stack_img

         self.all_frames[vid_fn] = load_frames_simple(video_file)
         marked_frames = []
         flat_frames = []
         for frame in self.all_frames[vid_fn]:
            #print("OVERLAY STACK ON IMAGES!", stack_img.shape, root_fn)
            if stack_img is not None:
               print("STACKING", stack_img.shape)
               marked_frame = cv2.addWeighted(frame, .95, stack_img, .05, .5)
            else:
               print("NOT STACKING")
               marked_frame = frame
            marked_frames.append(marked_frame)
            flat_frames.append(frame)
         self.all_frames[vid_fn] = flat_frames 
         self.marked_frames[vid_fn] = marked_frames

         fc += 1

      sx = 320
      sy = 180

      #self.stack_imgs = {}
      #self.clean_stack_imgs = {}

      # ALL VIDEO FRAMES ARE LOADED. 
      # VIDEO VALIDATION OR TRIMMING SHOULD HAPPEN HERE
      self.validate_video_frames()

      print("DO WE HAVE A STACK IMGS for this obs??? WAIT", show_img.shape)

      trans_frames = self.transition_video_start(show_img, flat_frames, first_stack_img, sx,sy)

      for vid_fn in self.all_frames:
         fc = 0
         for frame in self.all_frames[vid_fn]:
            if fc in self.all_frame_info[vid_fn]:
               action = self.all_frame_info[vid_fn][fc]['action']
            else:
               action = False
            if action is True:
               flat_frames.append(frame)
               show_img_with_player = orig_img.copy()
               frame = cv2.resize(frame, (640,360))
               print("MAIN:", show_img_with_player.shape)
               print("CROP:", sy,sy+frame.shape[0],sx,sx+frame.shape[1])
               show_img_with_player[sy:sy+frame.shape[0],sx:sx+frame.shape[1]] = frame
               self.save_movie_frame(show_img_with_player)
               cv2.imshow('ALLSKYOS', show_img_with_player)
               self.save_movie_frame(show_img_with_player)
               cv2.waitKey(60)
            fc += 1

   def validate_video_frames(self):
      self.all_frame_info = {}
      for vid_fn in self.all_frames:
         self.all_frame_info[vid_fn] = {}
         print("VID:", vid_fn , len(self.all_frames[vid_fn]))
         fc = 0
         max_pxs = []
         ff_mask = None
         for frame in self.all_frames[vid_fn]:
            self.all_frame_info[vid_fn][fc] = {}
            sub = cv2.subtract(frame, self.all_frames[vid_fn][0])
            gray = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)

            if ff_mask is None:

               first_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
               ffg_avg = np.mean(first_gray)
               if ffg_avg * 2 < 100 or ffg_avg * 2 > 120:
                  ffg_avg = 100 
               else:
                  ffg_avg = ffg_avg * 2 
               print("BG AVG / THRESH:", ffg_avg)
               _, ff_mask = cv2.threshold(first_gray, ffg_avg, 255, cv2.THRESH_BINARY)
               ff_mask =  cv2.dilate(ff_mask, None, iterations=4)
               cv2.imshow('MASK', ff_mask)
               cv2.waitKey(100)

            gray = cv2.subtract(gray, ff_mask)
            self.all_frame_info[vid_fn][fc]['max_px'] = np.max(gray)
            max_pxs.append(self.all_frame_info[vid_fn][fc]['max_px'])
            avg_px = np.mean(max_pxs[0:10])
            thresh = 10
            if thresh < 10:
               thresh = 10
            _, thresh_img = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
            self.all_frame_info[vid_fn][fc]['sub'] = gray
            self.all_frame_info[vid_fn][fc]['thresh'] = thresh
            if avg_px < 5:
               avg_px = 5 
            self.all_frame_info[vid_fn][fc]['rolling_max'] = avg_px 

            temp_cnts = []
            cnts = self.get_contours(thresh_img)
            dupes = {}
            for cnt in cnts:
               x,y,w,h = cnt
               cx = int(x + (w/2))
               cy = int(y + (h/2))
               key = str(cx) + "." + str(cy)
               if key not in dupes:
                  temp_cnts.append(cnt)
                  dupes[key] = 1

            self.all_frame_info[vid_fn][fc]['cnts'] = temp_cnts
            print(fc, temp_cnts)
            if self.all_frame_info[vid_fn][fc]['max_px'] >= self.all_frame_info[vid_fn][fc]['rolling_max'] * 1.0 and fc > 3:
               cv2.imshow('MASK', thresh_img)
               cv2.waitKey(30)


               #print("*", fc,  self.all_frame_info[vid_fn][fc]['rolling_max'], self.all_frame_info[vid_fn][fc]['max_px'])
               self.all_frame_info[vid_fn][fc]['action'] = True
               sframe = cv2.resize(frame, (640,360))
               cv2.putText(sframe, str(fc),  (50,50), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0,255,0), 1)

               dimg = np.zeros((360,1280,3),dtype=np.uint8)
               thresh_img = cv2.cvtColor(thresh_img, cv2.COLOR_GRAY2BGR)
               sframe = cv2.resize(sframe,(640,360))
               thresh_img = cv2.resize(thresh_img,(640,360))
               dimg[0:360,0:640] = sframe
               dimg[0:360,640:1280] = thresh_img 

               cv2.imshow("DEBUG", dimg)
               cv2.waitKey(100)
            else:
               #print(fc,  self.all_frame_info[vid_fn][fc]['rolling_max'], self.all_frame_info[vid_fn][fc]['max_px'])
               self.all_frame_info[vid_fn][fc]['action'] = False
               self.all_frame_info[vid_fn][fc]['cnts'] = []

            fc += 1

      # clean up cnts , remove dupes, plug holes determine start and end.
      objects = {}
      used_points = {}


      for vid_fn in self.all_frames:
         point_img = np.zeros((360,640,3),dtype=np.uint8)
         for fc in range(0, len(self.all_frames[vid_fn])):
            frame = self.all_frame_info[vid_fn][fc]['sub']
            SD_H, SD_W = frame.shape[:2]
            max_val = np.max(frame)
            temp_cnts = []
            for cnt in self.all_frame_info[vid_fn][fc]['cnts'] :
               x,y,w,h = cnt
               cx = (x + (w/2))
               cy = (y + (h/2))
               key = str(cx) + "." + str(cy)
               if key not in used_points:
                  used_points[key] = 1
                  intensity = frame[int(cy),int(cx)]
                  print("SDW:", SD_W)
                  oid, objects = Detector.find_objects(fc,x,y,w,h,cx,cy,intensity,objects, SD_W * .1)
                  #obj_id, objects = DD.find_object(objects, fc,cx, cy, SD_W, SD_H, max_val, 0, 0, None)
                  print("OBJECT ID:", oid)
                  cnt = x,y,w,h,oid
                  temp_cnts.append(cnt)
               else:
                  print("ignore dupe cnt")
                  used_points[key] += 1
            self.all_frame_info[vid_fn][fc]['cnts'] = temp_cnts
         for fc in range(0, len(self.all_frames[vid_fn])):
            temp_cnts = []
            for cnt in self.all_frame_info[vid_fn][fc]['cnts'] :
               x,y,w,h,obj_id = cnt
               cx = (x + (w/2))
               cy = (y + (h/2))
               dcx = int(cx*2)
               dcy = int(cy*2)

               cv2.putText(point_img, str(obj_id),  (dcx,dcy), cv2.FONT_HERSHEY_SIMPLEX, .5, (0,255,0), 1)
               cv2.circle(point_img,(dcx,dcy), 3, (128,128,128), 1)
               key = str(cx) + "." + str(cy)
               if key not in used_points:
                  used_points[key] = 1
                  temp_cnts.append(cnt)
               elif used_points[key] <= 1:
                  used_points[key] = 1
                  temp_cnts.append(cnt)
               else:
                  print("ignore dupe cnt")
                  used_points[key] += 1
            self.all_frame_info[vid_fn][fc]['cnts'] = temp_cnts
         cv2.imshow("POINT IMAGE", point_img)
         cv2.waitKey(300)

      for vid_fn in self.all_frames:
         print("VID:", vid_fn , len(self.all_frames[vid_fn]))
         fc = 0
         first_frame = None
         last_frame = None
         no_action = 0
         for frame in self.all_frames[vid_fn]:
            if fc not in self.all_frame_info[vid_fn]:
               continue
            if first_frame is True and self.all_frame_info[vid_fn][fc]['action'] is False:
               no_action += 1
            if first_frame is None and self.all_frame_info[vid_fn][fc]['action'] is True:
               print("***** START!!! *****")
               first_frame = fc
            print(fc, self.all_frame_info[vid_fn][fc]['rolling_max'], self.all_frame_info[vid_fn][fc]['max_px'] , self.all_frame_info[vid_fn][fc]['action'],self.all_frame_info[vid_fn][fc]['cnts'])
            if first_frame is not None and no_action >= 5 and last_frame is None:
               print("***** END!!! *****")
               last_frame = fc
            fc += 1

      print("MOVING OBJECTS IN THIS CLIP")
      for obj_id in objects:
         status, report = Detector.analyze_object(objects[obj_id])
         print(obj_id, objects[obj_id])
         print(status, report)

      #input("DONE VAL FRAMES")


   def save_movie_frame(self, frame):
      count_file = '{0:05d}'.format(self.movie_counter)
      cv2.imwrite(self.movie_dir + str(count_file) + ".jpg", frame)
      print("SAVING:", self.movie_dir + self.event_id + "_" + str(count_file) + ".jpg" )
      self.movie_counter += 1
      

   def transition_video_start(self, base_img, video_frames,stack_img, sx,sy,fw=640,fh=360):
      # just setup the transition into the video from a base image! 
      print("HELLOW")
      if len(video_frames) <= 0:
         desc = "NO VIDEO FRAMES FOUND..."
         show_img = base_img.copy()
         cv2.putText(show_img, desc,  (int(show_img.shape[1]/4), int(show_img.shape[0]/2)), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,255,0), 1)
         cv2.imshow('ALLSKYOS', show_img)
         self.save_movie_frame(show_img)
         cv2.waitKey(200)
         return()
      if stack_img is None:
         frame = video_frames[0]
      else:
         frame = stack_img
      frame = cv2.resize(frame,(fw,fh))
      dur = 20
      half_height = int(frame.shape[0] / 2)
      trans_frms = []
      #ssy = int(sy + half_height)
      sx = int(sx)
      for i in range (0, dur):
         y1 = int((half_height) - ((i/dur) * half_height))
         y2 = int((half_height) + ((i/dur) * half_height))
       
         print(sy, sx)
         trans_fr = frame[y1:y2,0:frame.shape[1]]
         
         show_img = base_img.copy()
         show_img[sy+y1:sy+y2, sx+0:sx+frame.shape[1] ] = trans_fr
         self.save_movie_frame(show_img)
         cv2.imshow("ALLSKYOS", show_img)
         cv2.waitKey(45)
      return(trans_frms)

   def transition_next_event(self, image1, image2,dur=20,style=None):
      # from right to left
      styles = ["r2l", "l2r", "t2b", "b2t"]
      if style is None:
         random.shuffle(styles)
         style = styles[0]
      if style == "r2l":
         for i in range(0,dur):
            show_img = image1
            y1 = 0
            y2 = image1.shape[0]
            x1 = int(image1.shape[1] - (i * (image1.shape[1]/dur)))
            x2 = image1.shape[1]
            show_img[y1:y2,x1:x2] = image2[y1:y2,x1:x2]
            self.save_movie_frame(show_img)
            cv2.imshow("ALLSKYOS", show_img)
            cv2.waitKey(45)
      if style == "l2r":
         for i in range(0,dur):
            show_img = image1
            y1 = 0
            y2 = image1.shape[0]
            x1 = 0
            x2 = int(0 + (i * (image1.shape[1]/dur)))
            show_img[y1:y2,x1:x2] = image2[y1:y2,x1:x2]
            self.save_movie_frame(show_img)
            cv2.imshow("ALLSKYOS", show_img)
            cv2.waitKey(45)
      if style == "t2b":
         for i in range(0,dur):
            show_img = image1
            y1 = 0
            y2 = int(0 + (i * (image1.shape[0]/dur)))
            x1 = 0
            x2 = image1.shape[1]
            show_img[y1:y2,x1:x2] = image2[y1:y2,x1:x2]
            self.save_movie_frame(show_img)
            cv2.imshow("ALLSKYOS", show_img)
            cv2.waitKey(45)
      if style == "b2t":
         for i in range(0,dur):
            show_img = image1
            y1 = 0
            y2 = int(image1.shape[0] - (i * (image1.shape[0]/dur)))
            x1 = 0
            x2 = image1.shape[1]
            show_img[y1:y2,x1:x2] = image2[y1:y2,x1:x2]
            self.save_movie_frame(show_img)
            cv2.imshow("ALLSKYOS", show_img)
            cv2.waitKey(45)


      
   

   def get_cloud_urls(self, root_file):
      st_id = root_file.split("_")[0]
      year = root_file.split("_")[1]
      month = root_file.split("_")[2]
      dom = root_file.split("_")[3]
      date = year + "_" + month + "_" + dom
      # local dir for caching cloud content jpgs/mp4s
      local_cache_dir = self.local_evdir + "OBS/"

      cloud_meteor_vdir = "https://archive.allsky.tv/" + st_id + "/METEORS/" + year + "/" + date + "/" 
      cloud_meteor_dir = "/mnt/archive.allsky.tv/" + st_id + "/METEORS/" + year + "/" + date + "/" 
      cloud_prev_img_file = cloud_meteor_dir + root_file + "-prev.jpg"
      cloud_prev_vid_file = cloud_meteor_dir + root_file + "-180p.mp4"
      cloud_prev_img_url = cloud_meteor_vdir + root_file + "-prev.jpg"
      cloud_prev_vid_url = cloud_meteor_vdir + root_file + "-180p.mp4"
      cloud_media = {}
      cloud_media['prev_img_file'] = cloud_prev_img_file
      cloud_media['prev_vid_file'] = cloud_prev_vid_file
      cloud_media['prev_img_url'] = cloud_prev_img_url 
      cloud_media['prev_vid_url'] = cloud_prev_vid_url 
      cloud_media['local_cache_dir'] = local_cache_dir
      return(cloud_media)


   def make_console_image(self,comp_img, comp_clean_img,event_data=None):
      event_id = event_data['event_id']
      logo = cv2.imread("logo.png")
      #nw = int(1920)
      nw = int(logo.shape[1] * .2)
      nh = int(logo.shape[0] * .2)
      dsize = (nw,nh)
      logo = cv2.resize(logo, dsize, interpolation = cv2.INTER_AREA)
 
      multi_x = 1920 / comp_img.shape[1]
      comp_img = cv2.resize(comp_img, (int(comp_img.shape[1] * multi_x), int(comp_img.shape[0] * multi_x)))

      #logo = cv2.resize(logo, (220,54))
      print("LOGO:", logo.shape)
      console_img = np.zeros((1080,1920,3),dtype=np.uint8)
      print("EVENT DATA!", event_data)
      margin = 0 
      console_img[1080-logo.shape[0]:1080,0:logo.shape[1]] = logo
      console_img[margin:comp_img.shape[0]+margin, margin:comp_img.shape[1]+margin]  = comp_img

      desc = "ALLSKYOS> EVENT REPORT FOR: " + event_id
      cv2.putText(console_img, desc,  (480, 1000), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 1)
      desc = "ALLSKYOS> SOLVER STATUS: " + event_data['wmpl_status']
      if "SOLVED" in event_data['wmpl_status']:
         cv2.putText(console_img, desc,  (480, 1030), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 1)
      elif "FAIL" in event_data['wmpl_status']:
         cv2.putText(console_img, desc,  (480, 1030), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 1)
      else:
         cv2.putText(console_img, desc,  (480, 1030), cv2.FONT_HERSHEY_SIMPLEX, 1, (128,128,128), 1)

      if "SOLVE" in event_data['wmpl_status'] :
         (sol_status, v_init, v_avg, start_ele, end_ele, a, e) = self.eval_sol(event_data)
         desc = "ALLSKYOS> SOLUTION: " + sol_status 
         if "BAD" in sol_status:
            sol_status = "INVALID"
            desc = "ALLSKYOS> SOLUTION: " + sol_status
            cv2.putText(console_img, desc,  (480, 1060), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 1)
         elif "GOOD" in sol_status:
            desc = "ALLSKYOS> SOLUTION: " + sol_status
            cv2.putText(console_img, desc,  (480, 1060), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 1)
      
      show_img = cv2.resize(console_img,(1280,720))
      print("EVENT DATA:", event_data.keys())
      return(show_img, console_img )


   def event_obs_comp(self,min_event,counter,human_key):
      #print(min_event.keys())
      descs = []
      obs_files = min_event['files']
      fobs = []
      nobs = []
      odir = self.local_evdir + "OBS/"
      oc = 0
      for fn in obs_files:
          
         if "AMS" in fn:
            st_id = fn.split("_")[0]
            fn2 = fn.replace(st_id + "_", "")
            if os.path.exists(odir + fn2 + "-prev.jpg"):
               fn = fn2
            
         if os.path.exists(odir + fn + "-prev.jpg"):
            fobs.append(odir + fn + "-prev.jpg")
            desc = min_event['stations'][oc]
            descs.append(desc)
         else:
            fobs.append(None)
            desc = min_event['stations'][oc]
            descs.append(desc)
            nobs.append(fn)
         oc += 1
      if len(fobs) > 1:
         ai_yns,ai_event_yn,comp_img,comp_img_clean = self.make_event_comp(fobs, descs,counter,human_key)
         return(ai_yns,ai_event_yn,comp_img,comp_img_clean)
      else:
         return(None,None,None,None)
  
   def make_event_comp(self,fobs,descs,counter,human_key):
      self.stack_images = {}
      cell_w = 320
      cell_h = 180 
      self.stack_imgs = {}
      self.clean_stack_imgs = {}

      cells_per_row = 4 
      if len(fobs) > 12:
         cells_per_row = 5
      if len(fobs) > 20:
         cells_per_row = 6 
      if len(fobs) > 30:
         cells_per_row = 8 

      hdm_x = 1920 / cell_w 
      hdm_y = 1080 / cell_h 
      print("MAKE EVENT COMP IMAGE",counter)
      print("---------------------")
      print("FOBS:", len(fobs))
      ai_yns = []
      f_rows = len(fobs) / cells_per_row
      f_rows = math.ceil(f_rows) 
      if f_rows <= 0:
         f_rows = 1
      else:
         f_rows = math.ceil(f_rows) 
      ch = f_rows * 180
      if len(fobs) <= cells_per_row:
         cw = len(fobs) * 320
      else:
         cw = cells_per_row * 320

      comp_img = np.zeros((ch,cw,3),dtype=np.uint8)
      comp_img_clean = np.zeros((ch,cw,3),dtype=np.uint8)
      fc = 0
      fr = 0
      cc = 0
      for fob in fobs:
         desc = descs[cc]
         if fc < cells_per_row:
            x1 = fc * 320
            x2 = x1 + 320
         else:
            x1 = 0
            x2 = 320
            fc = 0
            fr += 1
         y1 = fr * 180
         y2 = y1 + 180
         meteor_yn = False
         if fob is not None:
            img = cv2.imread(fob)
            clean_img = img.copy()
            mp4_fn = fob.split("/")[-1].replace("-prev.jpg",".mp4")
            if mp4_fn in self.review_data:
               ai_data = self.review_data[mp4_fn]
               meteor_yn = self.is_meteor(ai_data)
               print("AID:", ai_data)
               if "roi" in ai_data:
                  rx1,ry1,rx2,ry2 = int(ai_data['roi'][0]/hdm_x), int(ai_data['roi'][1]/hdm_y),int(ai_data['roi'][2]/hdm_x), int(ai_data['roi'][3]/hdm_y)
               if "ai" in ai_data:
                  if ai_data['ai']['meteor_yn_confidence'] < 50 and ai_data['ai']['meteor_fireball_yn_confidence'] < 50:
                     img = cv2.rectangle(img, (rx1,ry1), (rx2, ry2) , (128, 128, 255), 1)
                  else:
                     img = cv2.rectangle(img, (rx1,ry1), (rx2, ry2) , (128, 255, 128), 1)

               ai_data['objects'] = sorted(ai_data['objects'], key=lambda x: (x[0]), reverse=True) 
               con_rad = 20
               for obj in ai_data['objects']:
                  if obj[0] > 50:
                     roi = obj[1]
                     rx1,ry1,rx2,ry2 = int(roi[0]/hdm_x), int(roi[1]/hdm_y),int(roi[2]/hdm_x), int(roi[3]/hdm_y)
                     #cv2.circle(asimg,(new_cat_x,new_cat_y), 3, (128,128,128), 1)
                     #img = cv2.rectangle(img, (rx1,ry1), (rx2, ry2) , (128, 255, 255), 1)
                     cx1 = int((rx1+rx2)/2)
                     cy1 = int((ry1+ry2)/2)
                     if meteor_yn >= 98:
                        img = cv2.circle(img, (cx1,cy1), con_rad, (128, 255, 128), 1)
                     else:
                        img = cv2.circle(img, (cx1,cy1), con_rad, (128, 128, 128), 1)
                     con_rad -= 5
                     if con_rad < 10:
                        con_rad = 10

         else:
            img = np.zeros((180,320,3),dtype=np.uint8)
            clean_img = np.zeros((180,320,3),dtype=np.uint8)
 
          
         if False:
            root_fn = fob.split("/")[-1].replace("-prev.jpg", "")
            root_fn2 = None
            if "AMS" in root_fn:
               st_id = root_fn.split("_")[0]
               root_fn2 = root_fn.replace(st_id + "_", "")
            if root_fn2 is not None:
               if root_fn2 in self.stack_imgs:
                  stack_img = self.stack_imgs[root_fn2] 
                  stack_clean_img = self.clean_stack_imgs[root_fn2] 
            if root_fn in self.stack_imgs:
               stack_img = self.stack_imgs[root_fn] 
               stack_clean_img = self.clean_stack_imgs[root_fn] 

               stack_img = self.stack_imgs[root_fn] 
               stack_clean_img = self.clean_stack_imgs[root_fn] 

         if fob is None:
            continue
         print("FOB IS:", fob)
         root_fn = fob.split("/")[-1].replace("-prev.jpg", "")
         print("ROOT FN IS :", root_fn)
         root_fn = fob.split("/")[-1].replace("-prev.jpg", "")
         print("ROOT FN FOR STACK LOADER IS:", root_fn)
         self.stack_imgs[root_fn]  = img
         self.clean_stack_imgs[root_fn]  = clean_img

         
         #print("SELF.STACK_IMGS:", self.stack_imgs)
         print("ROOT FN IS:", root_fn)

         comp_img[y1:y2,x1:x2] = img
         comp_img_clean[y1:y2,x1:x2] = clean_img
         cv2.putText(comp_img, desc,  (x1+5,y2-10), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,255,0), 1)
         ai_yns.append(meteor_yn)
         if meteor_yn > 50:
            cv2.putText(comp_img, "AI+",  (x2-30,y2-10), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,255,0), 1)
         if meteor_yn < 50:
            cv2.putText(comp_img, "AI-",  (x2-30,y2-10), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
         cc += 1
         fc += 1

      if human_key is not None:
         print("HUMAN KEY!", human_key)
         if human_key == 109:
            cv2.putText(comp_img, "HUMAN VALID",  (5,15), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,255,0), 1)
         else :
            cv2.putText(comp_img, "HUMAN INVALID" ,  (5,15), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
      
      yes = 0
      no = 0
      for xx in ai_yns:
         if xx < 50 or xx is False:
            no += 1
         else: 
            yes += 1
      if yes >= 2 and yes / len(ai_yns) >= .5:
         ai_event_yes_no = True
      else:
         ai_event_yes_no = False 
      if ai_event_yes_no is True:
         cv2.putText(comp_img, "AI VALID",  (comp_img.shape[1]-55,15), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,255,0), 1)
      else:
         cv2.putText(comp_img, "AI INVALID",  (comp_img.shape[1]-65,15), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)

      return(ai_yns, ai_event_yes_no, comp_img, comp_img_clean )

   def is_meteor(self, ai_data ):
      met_yn = 0
      for obj in ai_data['objects']:
         if obj[0] > 50:
            if obj[0] > met_yn:
               met_yn = obj[0]  
      if "ai" in ai_data:
         if ai_data['ai']['meteor_yn_confidence'] > 50 or ai_data['ai']['meteor_fireball_yn_confidence'] > 50:
            if ai_data['ai']['meteor_yn_confidence'] > ai_data['ai']['meteor_fireball_yn_confidence']:
               met_yn = ai_data['ai']['meteor_yn_confidence']  
            else:
               met_yn = ai_data['ai']['meteor_fireball_yn_confidence']

      return(met_yn)

   def review_meteors(self,date,auto=True):
      SHOW = 1
      if os.path.exists(self.learning_repo + date + "/METEOR/") is False:
         os.makedirs(self.learning_repo + date + "/METEOR/")
      if os.path.exists(self.learning_repo + date + "/NON_METEOR/") is False:
         os.makedirs(self.learning_repo + date + "/NON_METEOR/")
      if os.path.exists(self.learning_repo + date + "/UNSURE/") is False:
         os.makedirs(self.learning_repo + date + "/UNSURE/")

      self.year, self.month, self.day = date.split("_")
      self.date = date
      self.local_evdir = self.local_event_dir + "/" + self.year + "/" + self.month + "/" + self.day  + "/"
      self.cloud_evdir = self.cloud_event_dir + "/" + self.year + "/" + self.month + "/" + self.day   + "/"
      self.all_obs_file = self.local_evdir + date + "_ALL_OBS.json"
      self.obs_review_file = self.local_evdir + date + "_OBS_REVIEWS.json"
      self.min_events_file = self.local_evdir + date + "_MIN_EVENTS.json"
      self.obs_img_dir = self.local_event_dir + "/" + self.year + "/" + self.month + "/" + self.day   + "/OBS/"

      #self.learning_repo_yes = self.obs_img_dir + "/METEOR/"
      #self.learning_repo_no = self.obs_img_dir + "/NON_METEOR/"

      self.learning_repo_yes = self.learning_repo + "/METEOR/"
      self.learning_repo_no = self.learning_repo + "/NON_METEOR/"

      if os.path.exists(self.learning_repo_yes) is False:
         os.makedirs(self.learning_repo_yes)
      if os.path.exists(self.learning_repo_no) is False:
         os.makedirs(self.learning_repo_no)

      self.year, self.month, self.day = date.split("_")
      self.date = date
      self.local_evdir = self.local_event_dir + "/" + self.year + "/" + self.month + "/" + self.day  + "/"
      self.cloud_evdir = self.cloud_event_dir + "/" + self.year + "/" + self.month + "/" + self.day   + "/"
      self.all_obs_file = self.local_evdir + date + "_ALL_OBS.json"
      self.obs_review_file = self.local_evdir + date + "_OBS_REVIEWS.json"
      self.min_events_file = self.local_evdir + date + "_MIN_EVENTS.json"
      self.obs_img_dir = self.local_event_dir + "/" + self.year + "/" + self.month + "/" + self.day   + "/OBS/"

      #self.learning_repo_yes = self.obs_img_dir + "/METEOR/"
      #self.learning_repo_no = self.obs_img_dir + "/NON_METEOR/"

      self.learning_repo_yes = self.learning_repo + "/METEOR/"
      self.learning_repo_no = self.learning_repo + "/NON_METEOR/"

      if os.path.exists(self.learning_repo_yes) is False:
         os.makedirs(self.learning_repo_yes)
      if os.path.exists(self.learning_repo_no) is False:
         os.makedirs(self.learning_repo_no)


      if os.path.exists(self.obs_img_dir) is False:
         os.makedirs(self.obs_img_dir) 

      if os.path.exists(self.obs_review_file) is True:
         review_data = load_json_file(self.obs_review_file)
      else:
         review_data = {}

      if os.path.exists(self.min_events_file) is True:
         self.min_events = load_json_file(self.min_events_file)
      else:
         self.min_events = {}
      self.ms_obs = {}
      for minute in self.min_events:
         for ev_id in self.min_events[minute]:
            if len(set(self.min_events[minute][ev_id]['stations'])) > 1:
               for i in range(0,len(self.min_events[minute][ev_id]['stations'])):
                  st_id = self.min_events[minute][ev_id]['stations'][i]
                  fn = self.min_events[minute][ev_id]['files'][i]
                  self.ms_obs[fn] = self.min_events[minute][ev_id]

      c = 0


      try:
         all_obs = load_json_file(self.all_obs_file)
      except:
         return()
      all_obs = sorted(all_obs, key=lambda x: x['station_id'] + "_" + x['sd_video_file'])
      #for i in range(0, len(all_obs)):
      i = 0
      go = True
      cloud_files = {}
      while go is True:
         if i >= len(all_obs):
            go = False
            break
         obs = all_obs[i]
         st_id = obs['station_id']
         if st_id not in cloud_files:
            if os.path.exists(self.cloud_dir + st_id + "/METEORS/" + self.year + "/" + self.date + "/"):
               cloud_files[st_id] = os.listdir(self.cloud_dir + st_id + "/METEORS/" + self.year + "/" + self.date + "/")
            else:
               cloud_files[st_id] = []




         sd_vid = obs['sd_video_file']

         if sd_vid in review_data:
            if "objects" in review_data[sd_vid]:
               print("skipping already have objects in the review data.", i)
               i = i + 1
               continue


         print("AI SCANNING", i, sd_vid)
         root_fn = sd_vid.split("/")[-1].replace(".mp4", "")
         if "roi" in obs:
            roi = obs['roi']
         else:
            roi = [0,0,0,0]
         if "meteor_frame_data" in obs:
            mfd = obs['meteor_frame_data']
         else:
            mfd = []

         prev_file = self.obs_img_dir + sd_vid.replace(".mp4", "-prev.jpg")


         cloud_prev_file = self.cloud_dir + st_id + "/METEORS/" + self.year + "/" + self.date + "/" + st_id + "_" + sd_vid.replace(".mp4", "-prev.jpg")
         cloud_prev_fn = st_id + "_" + sd_vid.replace(".mp4", "-prev.jpg")
         fns = [row[1] for row in obs['meteor_frame_data']]
         print("TEST1")
         if cloud_prev_fn not in cloud_files[st_id]:
            review_data[sd_vid] = ["NO_CLOUD_FILE",[0,0,0,0]]
            print("NO CLOUD FILE.")
            i = i + 1
            continue

         cloud_prev_url = cloud_prev_file.replace("/mnt/", "https://")
         if sd_vid not in review_data:
            review_data[sd_vid] = {}

         get_objects = False
         if "objects" not in review_data[sd_vid] and "ai" not in review_data[sd_vid]:
            get_objects = True
         elif review_data[sd_vid]['objects'] is None:
            get_objects = True
         else:
            continue

         print("Get image file", cloud_prev_url)
         if os.path.exists(prev_file) is False:
            try:
               res = requests.get(cloud_prev_url, stream=True, timeout=3)
            except:
               continue
            if res.status_code == 200:
               with open(prev_file,'wb') as f:
                  shutil.copyfileobj(res.raw, f)
               img = cv2.imread(prev_file)
            else:
               print('Image Couldn\'t be retrieved')
               continue
         else:
            img = cv2.imread(prev_file)
         
         #img = cv2.imread(cloud_prev_file)
         try:
            bimg = cv2.resize(img, (1920,1080))
         except:
            print("BAD IMG!", prev_file)
            i += 1
            #os.remove(prev_file)
            #exit()
            continue

         objects = self.detect_objects_in_stack(st_id, root_fn, img.copy())
         print("OBJECTS:", objects)
         print("REVIEW DATA:", review_data[sd_vid])
         if isinstance(review_data[sd_vid],  dict) is not True:
            review_data[sd_vid] = {}

         review_data[sd_vid]['objects'] = objects

         try:
            x1,y1,x2,y2 = self.mfd_roi(mfd)
         except:
            # here we should search for top 10 bright spots 
            # until we find a meteor or give up. 
            # right now it is only looking for 1 spot! 
            x1,y1,x2,y2 = 0,0,0,0
            gray = cv2.cvtColor(bimg, cv2.COLOR_BGR2GRAY)
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray)
            x1,x2 = mx,mx
            y1,y2 = my,my
      
         bimg = cv2.resize(img, (1920,1080))

         aix = int((x1 + x2) / 2)
         aiy = int((y1 + y2) / 2)
         aix1 = int(aix - (224/2))
         aix2 = int(aix + (224/2))
         aiy1 = int(aiy - (224/2))
         aiy2 = int(aiy + (224/2))
         if aix1 < 0:
            aix1 = 0
            aix2 = 224
         if aiy1 < 0:
            aiy1 = 0
            aiy2 = 224
         if aix1 >= 1920:
            aix1 = 1919 - 224 
            aix2 = 1919 
         if aiy1 >= 1080:
            aiy1 = 1079 - 224 
            aiy2 = 1079 
         if i % 10 == 0:
            save_json_file(self.obs_review_file, review_data)

         if True:
            sx1 = int(aix1 / 6)
            sy1 = int(aiy1 / 6)
            sx2 = int(aix2 / 6)
            sy2 = int(aiy2 / 6)
            learn_img = img[sy1:sy2,sx1:sx2]

            ai_roi_str = "AI_" + str(aix1) + "_" + str(aiy1) + "_" + str(aix2) + "_" + str(aiy2)

            learn_fn = st_id + "_" + sd_vid.replace(".mp4", ai_roi_str + ".jpg")

            bimg = cv2.rectangle(bimg, (aix1,aiy1), (aix2, aiy2) , (128, 255, 255), 1)
            if sd_vid in review_data:
               if len(review_data[sd_vid]) == 2 and "objects" not in review_data[sd_vid]:
                  label,roi = review_data[sd_vid]
               else:
                  label = review_data[sd_vid]

            cv2.imwrite(prev_file, img)
            #learn_img = cv2.resize(learn_img,(64,64))

            root_fn = prev_file.split("/")[-1]
            roi_file = "tmp.jpg" 

            cv2.imwrite(roi_file, learn_img)

            oimg=None
            roi = [aix1,aiy1,aix2,aiy2]

            obs_id = st_id + "_" + sd_vid.replace(".mp4", "")
            if obs_id in self.ms_obs:
               multi_station = True
               desc = "MULTI STATION EVENT"
               cv2.putText(bimg, desc,  (800,50), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,255,0), 1)
            else:
               multi_station = False


            if "ai" not in review_data[sd_vid]:
               result = self.ASAI.meteor_yn(root_fn,roi_file,oimg,roi)
               result['learn_fn'] = learn_fn
               review_data[sd_vid]['ai'] = result
               review_data[sd_vid]['roi'] = [aix1,aiy1,aix2,aiy2]

            result['multi_station'] = multi_station

            if "meteor" in result['mc_class'] or (result['meteor_yn'] > 80 or result['fireball_yn'] > 80) or multi_station is True:
               label = "METEOR:" + result['mc_class'] + " / " + str(round(result['meteor_yn'],1)) + "% Meteor " + str(round(result['fireball_yn'],1)) + "% Fireball"
               cv2.putText(bimg, label,  (aix1,aiy2), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
               save_dir = self.learning_repo_yes
            else:
               label = "NON_METEOR:" + result['mc_class'] + " / " + str(round(result['meteor_yn'],1)) + "% Meteor " + str(round(result['fireball_yn'],1)) + "% Fireball"
               cv2.putText(bimg, label,  (aix1,aiy2), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,0,255), 1)
               save_dir = self.learning_repo_no
            

            show_img = cv2.resize(bimg,(1280,720))

            key = ""
            meteor_confirmed = False 
            non_meteor_confirmed = False 
            if key == 109:
               # meteor Y 
               save_dir = self.learning_repo_yes 
               meteor_confirmed = True
               review_data[sd_vid]['human_label'] = "METEOR"
               cv2.imwrite(save_dir + learn_fn, learn_img)
            if key == 110:
               # meteor N
               non_meteor_confirmed = True
               review_data[sd_vid]['human_label'] = "NON_METEOR"
               save_dir = self.learning_repo_no
               cv2.imwrite(save_dir + learn_fn, learn_img)

            if key == 115:
               # save json!
               save_json_file(self.obs_review_file, review_data)
            i = i + 1
      save_json_file(self.obs_review_file, review_data)
      
   def detect_objects_in_stack(self, station_id, root_fn, img):
      date = root_fn[0:10]
      objects = []
      show_img = img.copy()
      show_img = cv2.resize(img.copy(), (1920,1080))
      tn_img = cv2.resize(img.copy(), (320,180))
      iw = 320
      ih = 180
      if img.shape[0] != 1080:
         img = cv2.resize(img, (1920,1080))
      tries = 0
      if len(img.shape) == 3:
         gray = cv2.cvtColor(tn_img, cv2.COLOR_BGR2GRAY)
      else:
         gray = img
      tn_size = 38
      while tries < 10:
         if True:
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray)
            pxd = max_val - np.mean(gray)
            if pxd < 10:
               # not enough Pixel Diff between brightest and avg 
               tries += 1
               continue
            x1,x2 = mx,mx
            y1,y2 = my,my
            aix = int((x1 + x2) / 2)
            aiy = int((y1 + y2) / 2)
            aix1 = int(aix - (tn_size/2))
            aix2 = int(aix + (tn_size/2))
            aiy1 = int(aiy - (tn_size/2))
            aiy2 = int(aiy + (tn_size/2))
            if aix1 < 0:
               aix1 = 0
               aix2 =tn_size 
            if aiy1 < 0:
               aiy1 = 0
               aiy2 = tn_size 
            if aix1 >= iw:
               aix1 = iw - 1 - tn_size 
               aix2 = iw 
            if aiy1 >= ih:
               aiy1 = ih - 1 - tn_size
               aiy2 = ih
            gray[aiy1:aiy2,aix1:aix2] = 0
            hdm_x = 1920 / 320
            hdm_y = 1080 / 180
            roi_img = tn_img[aiy1:aiy2,aix1:aix2] 
            if roi_img.shape[0] != roi_img.shape[1]:
               continue 

            roi = [int(aix1*hdm_x),int(aiy1*hdm_y),int(aix2*hdm_x),int(aiy2*hdm_y)]
            roi_file = "test.jpg"
            cv2.imwrite("test.jpg", roi_img)
   
            #meteor_prev_yn,meteor_or_star_perc = self.ASAI.meteor_prev_yn(roi_img)
            meteor_prev_yn = self.ASAI.meteor_prev_yn(roi_img)

            aix1,aiy1,aix2,aiy2 = roi
            show_img = cv2.rectangle(show_img, (aix1-2,aiy1-2), (aix2+2, aiy2+2) , (128, 255, 255), 1)
            #result = self.score_met_ai(result)
            save_fn = station_id + "_" + root_fn + str(aix1) + "_" + str(aiy1) + "_" + str(aix2) + "_" + str(aiy2) + ".jpg"
            if meteor_prev_yn >= 80:
               save_file = self.learning_repo + date + "/METEOR/" + save_fn
            elif meteor_prev_yn <= 50:
               save_file = self.learning_repo + date + "/NON_METEOR/" + save_fn 
            else:
               save_file = self.learning_repo + date + "/UNSURE/" + save_fn
            roi_img = cv2.resize(roi_img,(224,244))
            print("SAVING:", save_file)
            cv2.imwrite(save_file, roi_img)
            label_data = [round(meteor_prev_yn,2),roi]
            objects.append(label_data)
            label = str(round(meteor_prev_yn,2)) + "% meteor"
            if aiy2 < ih / 2:
               cv2.putText(show_img, label,  (aix1,aiy2), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
            else:
               cv2.putText(show_img, label,  (aix1,aiy1), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
            tries += 1
      return(objects) 

   def score_met_ai(self, ai):
      score = 0
      if ai['meteor_yn_confidence'] > 50:
         score += 1
      if ai['meteor_fireball_yn_confidence'] > 50:
         score += 1
      if ai['meteor_prev_yn'] > 50:
         score += 1
      if ai['meteor_or_plane'] != "":
         if ai['meteor_or_plane'][0] == "METEOR":
            score += 1
      if ai['fireball_or_plane'] != "":
         if ai['fireball_or_plane'][0] == "FIREBALL":
            score += 1
      if "meteor" in ai['mc_class']:
         score += 1
      ai['meteor_score'] = score
      return(ai)

   def mfd_roi(self, mfd):
      xs = [row[2] for row in mfd]
      ys = [row[3] for row in mfd]
      cx = np.mean(xs)
      cy = np.mean(ys)
      min_x = min(xs)
      max_x = max(xs)
      min_y = min(ys)
      max_y = max(ys)
      w = max_x - min_x
      h = max_y - min_y
      if w > h:
         roi_size = int(w * 1.25)
      else:
         roi_size = int(h * 1.25)

      x1 = int(cx - int(roi_size/2))
      x2 = int(cx + int(roi_size/2))
      y1 = int(cy - int(roi_size/2))
      y2 = int(cy + int(roi_size/2))
      roi_w = x2 - x1
      roi_h = y2 - y1
      if roi_w != roi_h:
         if roi_w < roi_h:
            roi_size = roi_w
         else:
            roi_size = roi_h
      else:
         roi_size = roi_w
      if roi_size > 1070:
         print("METEOR IS TOO BIG TO MAKE AN ROI!")
         hd_roi = [0,0,1920,1080]
         return(hd_roi)
      # check if the ROI BOX extends offframe
      off_frame = self.check_off_frame(x1,y1,x2,y2,1920,1080)
      if len(off_frame) > 0:
         x1,y1,x2,y2 = self.fix_off_frame(x1,y1,x2,y2,1920,1080, off_frame)
      return(x1,y1,x2,y2)
      
      
      
   def check_off_frame(self,x1,y1,x2,y2,w,h):
      off_frame = []

      #print("check_off_frame", x1,y1,x2,y2,w,h)
      if x1 < 0:
         off_frame.append('left')
      if x2 > w - 1:
         off_frame.append('right')
      if y1 < 0:
         off_frame.append('top')
      if y2 > h - 1:
         off_frame.append('bottom')
      return(off_frame)
      
      
   def average_times(self, times):
      tt = []
      for stime in times:
         s_datestamp, s_timestamp = self.date_str_to_datetime(stime)
         tt.append(s_timestamp)
      avg_time = np.median(tt)
      dt = datetime.datetime.fromtimestamp(avg_time)
      dt_str = dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
      return(dt_str)
      
   def date_str_to_datetime(self, date_str):
      if "." in date_str:
         dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S.%f")
      else:
         dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
      ts = datetime.datetime.timestamp(dt)
      return(dt, ts)

   def date_to_event_id(self, datetime_str):
      event_id = datetime_str.replace("-", "")
      event_id = event_id.replace("_", "")
      event_id = event_id.replace(":", "")
      event_id = event_id.replace(" ", "_")
      if "." in event_id:
         event_id = event_id.split(".")[0]
      return(event_id)
      
      
   def eval_sol(self, data):
      print(data.keys())
      event_status = data['wmpl_status']
      if "traj" not in data:
         return("BAD", 0, 0, 0, 0, 0, 0)

      v_init = round(data['traj']['v_init'] / 1000,2)
      v_avg = round(data['traj']['v_avg'] /1000,2)
      end_ele = round(data['traj']['end_ele']  / 1000,2)
      start_ele = round(data['traj']['start_ele'] / 1000,2)

      if "orb" in data:
         if data['orb'] is not None:
            if data['orb']['a'] is not None:
               a = data['orb']['a']
               e = data['orb']['e']
            else:
               a = -1
               e = 99
         else:
            a = -1
            e = 99
      else:
         a = -1
         e = 99
      sol_status = ""
      if v_init > 100 or v_avg > 100:
         sol_status += "BAD_VEL;"
      if start_ele >= 200 or start_ele < 0:
         sol_status += "BAD_TRAJ_START;"
      if end_ele >= 200 or end_ele < 0:
         sol_status += "BAD_TRAJ_END;"
      if a < 0:
         sol_status += "BAD_ORB_a;"
      if e > 1:
         sol_status += "BAD_ORB_e;"
      if sol_status == "":
         sol_status = "GOOD"

      return(sol_status, v_init, v_avg, start_ele, end_ele, a, e)
      
      
      
 

   def get_contours(self,sub):
      cont = []
      cnt_res = cv2.findContours(sub.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      noise = 0
      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         if w >= 1 and h >= 1:
            cont.append((x,y,w,h))
      return(cont)

