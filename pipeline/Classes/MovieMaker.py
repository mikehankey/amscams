import cv2
import glob
import os
import sys
import datetime
from datetime import timedelta
from lib.PipeUtil import load_json_file, save_json_file
import numpy as np
from PIL import ImageFont, ImageDraw, Image, ImageChops

class MovieMaker():

   def __init__(self):
      print("Movie Maker")
      self.movie_width = 1920
      self.movie_height = 1080
      self.sd_dir = "/mnt/ams2/SD/proc2/"
      self.min_dict = {}
      if os.path.exists("../conf/as6.json") :
         self.json_conf = load_json_file("../conf/as6.json")
      else:
         self.json_conf = None
      self.cams = []
      
      if self.json_conf is not None:
         self.station_id = self.json_conf['site']['ams_id']
      else:
         self.station_id = "AMSX"
         
      #content = u'\N{COPYRIGHT SIGN}'.encode('utf-8')
      #symbol = content.decode('utf-8')
      symbol = "(c) "
      self.photo_credit = self.json_conf['site']['ams_id'] + " - " + self.json_conf['site']['operator_name'] + " " + self.json_conf['site']['operator_city']

      if self.json_conf['site']['operator_state'] is not None:
         self.photo_credit += " " + self.json_conf['site']['operator_state'] + ","
      self.photo_credit += " " + self.json_conf['site']['operator_country']
      self.photo_credit += " - ALLSKY.COM"
      
      if self.json_conf is not None:
         for cnum in sorted(self.json_conf['cameras'].keys()):
            cams_id = self.json_conf['cameras'][cnum]['cams_id']
            self.cams.append(cams_id)

   def make_timelapse(self, cam_id, start, end):
      self.mp4_files = []
      (start_datetime, start_date_str, cam) = self.date_to_datetime(start)
      (end_datetime, end_date_str, cam) = self.date_to_datetime(end)
      self.start_datetime = start_datetime
      self.end_datetime = end_datetime
      print("make tl", start_datetime, end_datetime, )
      delta = end_datetime - start_datetime

      # get all day and night files for all days
      for i in range(delta.days + 1):
         day = start_datetime + timedelta(days=i)
         day_str = day.strftime("%Y_%m_%d")
         self.update_min_dict(day_str )
         files = os.listdir(self.sd_dir + day_str + "/")
         day_files = os.listdir(self.sd_dir + "daytime/" + day_str + "/")
         for ff in files:
            if "mp4" not in ff:
               continue
            if "crop" in ff or "trim" in ff:
               continue 
            if cam_id in ff: 
               self.mp4_files.append(day_str + "/" + ff)

         for ff in day_files:
            if "mp4" not in ff:
               continue
            if "crop" in ff or "trim" in ff:
               continue 
            if cam_id in ff: 
               self.mp4_files.append("daytime/" + day_str + "/images/" + ff)


      cv2.namedWindow('pepe')
      for ff in sorted(self.mp4_files):
         day_str = ff[0:10]
         if "daytime" in ff:
            stack_file = self.sd_dir + ff.replace(".mp4", "-snap.jpg")
            #if os.path.exists(stack_file) is False:
            #   stack_file = self.sd_dir + ff.replace(".mp4", "-stacked-tn.jpg")
         else:
            stack_file = self.sd_dir + ff.replace(".mp4", "-stacked.jpg")

         options = {}
         options['photo_credit'] = self.photo_credit
         ai_file = stack_file.replace("-stacked.jpg", "-ai.json")
         if os.path.exists(ai_file):
            try:
               ai_data = load_json_file(ai_file)
            except:
               ai_data = {}
               #os.remove(ai_file)
            options['ai_data'] = ai_data

         (file_datetime, file_datetime_str, cam) = self.date_to_datetime(ff.split("/")[-1])


         options['datetime_str'] = file_datetime_str 

      
         self.add_to_min_dict(stack_file, options)



      for day in sorted(self.min_dict.keys()):
         for hour in sorted(self.min_dict[day].keys()):
            for minute in sorted(self.min_dict[day][hour].keys()):
               cur_date_str = day + "_" + hour + "_" + minute
               cur_datetime = datetime.datetime.strptime(cur_date_str, "%Y_%m_%d_%H_%M")
               if self.start_datetime <= cur_datetime <= self.end_datetime:
                  continue

               if "img_file" in self.min_dict[day][hour][minute][cam_id]:
                  img_file = self.min_dict[day][hour][minute][cam_id]['img_file']
               else:
                  print(day, hour, minute, "missing image file!")
                  img_file = None
                  #img_file = self.min_dict[day][hour][minute][cam_id]['img_file']
               if "options" in self.min_dict[day][hour][minute][cam_id]:
                  options = self.min_dict[day][hour][minute][cam_id]['options']
               else:
                  options = {}

               print(day, hour, minute, img_file, options)
               if img_file is None: 
                  min_file = self.get_min_file(cam, day, hour, minute) 

                  if min_file is not None and os.path.exists(min_file) is False:
                     self.make_snap(video_file)
                     img_file = img_file.replace("-stacked-tn.jpg", "-snap.jpg")
                     img_file = img_file.replace("-stacked.jpg", "-snap.jpg")
                 
               frame = self.render_frame(img_file, options)

               cv2.imshow('pepe', frame)
               cv2.waitKey(30)


   def get_min_file(self, cam, day, hour, minute):
      min_check_wild = self.sd_dir + day + "/" + day + "_" + hour + "_" + minute + "*" + cam + ".mp4"
      min_check_day_wild = self.sd_dir + "daytime/" + day + "/" +  day + "_" + hour + "_" + minute + "*" + cam + ".mp4"

      print("CHECK:", min_check_wild)
      print("DAY CHECK:", min_check_day_wild)

      files = glob.glob(min_check_wild)
      for f in files:
         if "trim" in f or "crop" in f:
            continue
         else:
            return(f)

      files = glob.glob(min_check_wild)
      for f in files:
         if "trim" in f or "crop" in f:
            continue
         else:
            return(f)
      return(None) 

   def snap_day(self, day):
      day_dir = self.sd_dir + "daytime/" + day + "/"
      day_files = os.listdir(day_dir)
      for df in day_files:
         video_file = day_dir + df 
         image_file = day_dir + "images/" + df.replace(".mp4", "-snap.jpg")
         print("VIDEO FILE/IMAGE FILE", video_file, image_file)
         if os.path.exists(image_file) is False and "mp4" in video_file:
            
            self.make_snap(video_file)
         else:
            print("skip done:", image_file)

   def make_snap(self, video_file):
      video_fn = video_file.split("/")[-1]
      snap_dir = video_file.replace(video_fn, "")
      snap_fn = video_fn.replace(".mp4", "-snap.jpg")
      snap_dir += "images/" 
      fail = 0
      if os.path.exists(video_file):
         cap = cv2.VideoCapture(video_file)
         while True:
            grabbed , color_frame = cap.read()
            if color_frame is not None:
               color_frame = cv2.resize(color_frame, (640,360))
               if color_frame is not None:
                  cv2.imwrite(snap_dir + snap_fn, color_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                  print("saved" , snap_dir + snap_fn)
                  break
            else:
               print("Failed...", video_file)
               fail += 1
               if fail > 10:
                  exit ()

   def render_frame(self, img_file, options={}):

      #if (img_file) is not None:
      #   video_file = img_file.replace("-stacked-tn.jpg", ".mp4")
      #   video_file = img_file.replace("images/", "")
      #   img_file = img_file.replace("-stacked-tn.jpg", "-snap.jpg")

      if (img_file) is None:
         frame = np.zeros((self.movie_height,self.movie_width,3),dtype=np.uint8)
      elif os.path.exists(img_file):
         frame = cv2.imread(img_file)
         frame = cv2.resize(frame, (self.movie_width, self.movie_height))
      else:
         frame = np.zeros((self.movie_height,self.movie_width,3),dtype=np.uint8)
      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
      image = Image.fromarray(frame)
      draw = ImageDraw.Draw(image)
      #font = ImageFont.load_default()
      font = ImageFont.truetype("/usr/share/fonts/truetype/DejaVuSans.ttf", 24, encoding="unic" )

      if "photo_credit" in options: 
         draw.text((10, self.movie_height-30), str(options['photo_credit']), font = font, fill="white")
      if "datetime_str" in options: 
         draw.text((self.movie_width-325, self.movie_height-30), str(options['datetime_str'][0:16]), font = font, fill="white")
 
      return(cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR))

   def add_to_min_dict(self, image_file, options):
      img_fn = image_file.split("/")[-1]
      el = img_fn.split("_")
      year = el[0]
      month = el[1]
      dom = el[2]
      day = year + "_" + month + "_" + dom
      hour = el[3]
      minute = el[4]
      second = el[5]
      fsec = el[6]
      cid = el[7].split("-")[0]
      #print(self.min_dict.keys())
      #print(self.min_dict[day][hour][minute])

      self.min_dict[day][hour][minute][cid]['img_file'] = image_file
      self.min_dict[day][hour][minute][cid]['options'] = options

   def update_min_dict(self,day):
      if day not in self.min_dict:
         self.min_dict[day] = {}
      for hour in range (0,24):
         hour = "{:02d}".format(hour)
         self.min_dict[day][hour] = {}
         for minute in range (0,60):
            minute = "{:02d}".format(minute)
            self.min_dict[day][hour][minute] = {}
            for cid in self.cams:
               if cid not in self.min_dict[day][hour][minute]:
                  self.min_dict[day][hour][minute][cid] = {}
            

   def date_to_datetime(self,in_date):
      data = in_date.split("_")
      if len(data) == 6:
         fy,fm,fd,fh,fmin,fs, = data[:6]
         cam = None
         fms = "000"
         f_date_str = fy + "-" + fm + "-" + fd + " " + fh + ":" + fmin + ":" + fs
         f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
      elif len(data) >= 8:
         fy,fm,fd,fh,fmin,fs,fms,cam = data[:8]
         f_date_str = fy + "-" + fm + "-" + fd + " " + fh + ":" + fmin + ":" + fs
         f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
      if cam is not None:
         cam = cam.replace(".png", "")
         cam = cam.replace(".jpg", "")
         cam = cam.replace(".json", "")
         cam = cam.replace(".mp4", "")
      return(f_datetime, f_date_str, cam)
