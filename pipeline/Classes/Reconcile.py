from lib.PipeUtil import cfe, load_json_file, save_json_file, get_file_info
import os
from pushAWS import make_obs_data
import glob
from datetime import datetime

"""
 Reconcile -- Class for reconciling meteor data with latest detection, redis storage, calib, media, cloud, backup/archive and AWS. 



"""

class Reconcile():
   def __init__(self, year=None,month=None):
      self.data_dir = "/home/ams/amscams/DATA/"
      if cfe(self.data_dir, 1) == 0:
         os.makedirs(self.data_dir)
      if year is not None and month is None:
         self.rec_file = self.data_dir + "reconcile_" + year + ".json"
      elif year is not None and month is not None:
         self.rec_file = self.data_dir + "reconcile_" + year + "_" + month + ".json"
      self.json_conf = load_json_file("../conf/as6.json")
      self.station_id = self.json_conf['site']['ams_id']
      if cfe(self.rec_file) == 1:
         self.rec_data = load_json_file(self.rec_file)
      else:
         self.rec_data = {}
      self.mfiles = []
      
      if month is None:
         self.get_all_meteor_files(year)
      else:
         self.get_all_meteor_files(year, month)

         self.rec_data['mfiles'] = self.mfiles
         save_json_file(self.rec_file, self.rec_data, True)
      if "meteor_index" not in self.rec_data:
         self.rec_data['meteor_index'] = {}   
      c = 0

      new = 0
      for root_file in self.rec_data['mfiles']:
         print(c, root_file)   
         date = root_file[0:10]
         meteor_file = "/mnt/ams2/meteors/" + date + "/" + root_file + ".json"
         month = date[0:7]
         if c > 0 and last_month != month and new >= 500:
            # incrementally save
            save_json_file(self.rec_file, self.rec_data,True)
            new = 0

         if root_file not in self.rec_data['meteor_index']:
            print("GET OBS:", c, new, meteor_file)
            self.rec_data['meteor_index'][root_file] = {}
            self.rec_data['meteor_index'][root_file]['last_update'] = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            self.rec_data['meteor_index'][root_file]['obs_data'] = make_obs_data(self.station_id, date, meteor_file) 
            new = new + 1
         else:
            print("OBS GET DONE.")

         c += 1
         last_month = month

      self.get_scan_media(year,month)
      new = 1
      if new >= 1:    
         print("saving " + year + " data")
         save_json_file(self.rec_file, self.rec_data)


   def day_month_stats(self):
      for root_file in self.rec_data['meteor_index']:
         day = root_file[0:10]
         mon = root_file[0:7]
         if day not in self.rec_data['day_data']:
            self.rec_data['day_data'][day] = 1
         else:
            self.rec_data['day_data'][day] += 1
         if mon not in self.rec_data['month_data']:
            self.rec_data['month_data'][mon] = 1 
         else:
            self.rec_data['month_data'][mon] += 1 

      for day in self.rec_data['day_data']:
         print(day, self.rec_data['day_data'][day])
      for mon in self.rec_data['month_data']:
         print(mon, self.rec_data['month_data'][mon])
       
   def get_scan_media(self, year, mon):
      if mon is not None:
         wild = year + "_" + mon
      else :
         wild = year
      os.system("find /mnt/ams2/METEOR_SCAN/ > ../conf/meteor_scan_media.txt")
      fp = open("../conf/meteor_scan_media.txt")
      #for key in self.rec_data['meteor_index']:
      #   print(key)
      for line in fp:
         if wild not in line:
            continue
         line = line.replace("\n", "")
         fn = line.split("/")[-1]
         fn = fn.replace(self.station_id + "_","")
         ext = fn.split("-")[-1]
         root = fn.replace("-" + ext, "")
         if root in self.rec_data['meteor_index']:
            self.rec_data['meteor_index'][root]['exts'] = []
            self.rec_data['meteor_index'][root]['cloud_files'] = []
            self.rec_data['meteor_index'][root]['exts'].append(ext)
            print("ROOT FOUND!", root)
         else:
            print("ROOT NOT FOUND IN INDEX?", root)
            print(self.rec_data['meteor_index'].keys())
            input()
       
         

   def get_all_meteor_files(self, year, mon):
      if mon is None:
         mdirs = glob.glob("/mnt/ams2/meteors/" + year + "*")
      else:
         mdirs = glob.glob("/mnt/ams2/meteors/" + year + "_" + mon + "*")
      mds = []
      for md in mdirs:
         if cfe(md,1) == 1:
            mds.append(md + "/")

      for md in sorted(mds,reverse=True):
         print(md)
         self.get_mfiles(md)

   def get_mfiles(self, mdir):
      temp = glob.glob(mdir + "/*.json")
      for json_file in temp:
          if "frame" not in json_file and "import" not in json_file and "report" not in json_file and "reduced" not in json_file and "calparams" not in json_file and "manual" not in json_file and "starmerge" not in json_file and "master" not in json_file:
            root = json_file.split("/")[-1].replace(".json", "")

            self.mfiles.append(root)
