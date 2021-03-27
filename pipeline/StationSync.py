from skimage.measure import ransac, LineModelND, CircleModel
import glob
import os
import datetime

from sklearn.linear_model import RANSACRegressor
from sklearn.datasets import make_regression

from PIL import ImageFont, ImageDraw, Image, ImageChops

from DisplayFrame import DisplayFrame
from Detector import Detector
from Camera import Camera
from Calibration import Calibration
from lib.PipeAutoCal import gen_cal_hist,update_center_radec, get_catalog_stars, pair_stars, scan_for_stars, calc_dist, minimize_fov, AzEltoRADec , HMS2deg, distort_xy, XYtoRADec, angularSeparation
from lib.PipeUtil import load_json_file, save_json_file, cfe
from lib.FFFuncs import best_crop_size, ffprobe



class StationSync():

   def __init__(self, cmd=None, day=None, month=None,year=None,force=0):
      self.today = datetime.datetime.now().strftime("%Y_%m_%d")
      self.yesterday = (datetime.datetime.now() - datetime.timedelta(days = 1)).strftime("%Y_%m_%d")
      self.json_conf = load_json_file("../conf/as6.json")
      if cfe("../conf/sync_status.json") == 1:
         self.sync_status = load_json_file("../conf/sync_status.json")
      else:
         self.sync_status = self.update_sync_status()
         save_json_file("../conf/sync_status.json", self.sync_status)


      self.force = force
      self.DF = DisplayFrame()
      self.cmd = cmd
      self.day = day
      self.month = month
      self.year = year
      if year is not None:
         self.batch_mode = "year"
         self.cloud_dir = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/"
         self.cloud_file_index = self.cloud_dir + "cloud_event_files_" + self.year + ".txt"
      if month is not None:
         self.batch_mode = "month"
         self.year, self.month = month.split("_")
         self.cloud_dir = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/"
         self.cloud_file_index = self.cloud_dir + "cloud_event_files_" + self.year + "_" + self.month + ".txt"
      if day is not None:
         self.date = day
         self.day, self.year, self.month = day.split("_")

         self.batch_mode = "day"
         self.cloud_dir = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/"
         self.cloud_file_index = self.cloud_dir + "cloud_event_files_" + self.year + "_" + self.month + "_" + self.day
      self.local_dir = self.cloud_dir.replace("/archive.allsky.tv/", "/ams2/")
      self.local_file_index = self.cloud_file_index.replace("/archive.allsky.tv/", "/ams2/")

   def controller(self):
      if self.cmd is None:
         return()
      if self.cmd == 'sd' or self.cmd == 'sync_day':
         self.sync_day()
         return()
      if self.cmd == 'sm' or self.cmd == 'sync_month':
         self.sync_month()
         return()
      if self.cmd == 'sy' or self.cmd == 'sync_year':
         self.sync_year()
         return()

   def sync_month(self):
      #f_datetime = datetime.datetime.strptime(date_str, "%Y_%m_%d_%H_%M_%S")

      for d in range(1,31):
         if d < 10:
            ds = "0" + str(d)
         else:
            ds = str(d)
         date_str = self.year + "_" + self.month + "_" + ds
         meteor_dir = "/mnt/ams2/meteors/" + date_str + "/"
         mjs = []
         if date_str in self.sync_status:
            sync_status = self.sync_status[date_str]
            if sync_status == 1:
               print("we already sync'd this dir")

         if cfe(meteor_dir, 1) == 1 and sync_status == 0:
            amjs = glob.glob(meteor_dir + "*.json")
            for mj in amjs:
               if "reduced" not in mj:
                  mjs.append(mj)
            if len(mjs) > 0:
               self.day = ds
               self.date = date_str
               self.sync_day()
               print("SYNC'D: ", date_str, len(mjs), "meteors")

            else:
               print("No meteors to sync on", date_str)

   def sync_year(self):
      mdirs = self.get_meteor_dirs(wild=self.year)
      for md in mdirs:
         mday = md.split("/")[-1]
         if mday in self.sync_status:
            status = self.sync_status[mday]
         else:
            status = 0
         if status == 0:
            self.date = mday
            self.sync_day() 
            print("SYNC YEAR:", mday,status)



   def sync_day(self):
      
      sync_log = "/mnt/ams2/meteors/" + self.date + "/sync.txt"
      print("SYNC DAY:", self.date)

      if self.force == 1 or cfe(sync_log) == 0:
          cmd = "./DynaDB.py sync_db_day " + self.date
          print(cmd)
          os.system(cmd)

          cmd = "./Process.py ded " + self.date
          print(cmd)
          os.system(cmd)
   
          cmd = "./Process.py sync_prev_all " + self.date 
          print(cmd)
          os.system(cmd)

          #cmd = "./Process.py sync_final_day " + self.date 
          #print(cmd)
          #os.system(cmd)
      else:
         print("This date is already sync'd")

      data = {}
      data['last_sync'] = self.today
      save_json_file(sync_log, data)

   def update_sync_status(self):
      print("Update sync status")
      mdirs = self.get_meteor_dirs()
      mdays = {}
      for mdir in sorted(mdirs, reverse=True):
         mday = mdir.split("/")[-1]
         sync_file = mdir + "/sync.txt" 
         if cfe(sync_file) == 1:
            status = 1
         else:
            status = 0
         mdays[mday] = status
      return(mdays)

   def get_meteor_dirs(self, wild=""):
      temp = glob.glob("/mnt/ams2/meteors/*" + wild + "*")
      mdirs = []
      for md in temp:
         if cfe(md,1) == 1:
            mdirs.append(md)
      return(mdirs)

   def get_meteor_files(self,meteor_dir):
      temp = glob.glob(meteor_dir + "/*.json")
      for js in temp:
         if "reduced" not in js:
            meteor_files.append(js)
      return(meteor_files)

 

if __name__ == "__main__":
   import sys
   print(sys.argv)

   if len(sys.argv) < 3:
      print("You need at least 2 args [CMD] [YYYY_MM_DD]. ")
   else:
      el = sys.argv[2].split("_")
      if len(el) == 3:
         SS = StationSync(cmd=sys.argv[1], day=sys.argv[2])
      if len(el) == 2:
         SS = StationSync(cmd=sys.argv[1], month=sys.argv[2])
      if len(el) == 1:
         SS = StationSync(cmd=sys.argv[1], year=sys.argv[2])
      SS.controller()



   #cmd = "./Process.py remaster_day " + day
   #print(cmd)
   #os.system(cmd)







