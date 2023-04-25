import sqlite3
import os
import time
import requests
from datetime import datetime
import numpy as np
import cv2
import json
import datetime as dt
import os
from lib.PipeUtil import load_json_file, convert_filename_to_date_cam, get_trim_num, mfd_roi, save_json_file, bound_cnt, get_file_info
import sys
import glob
from Classes.ASAI import AllSkyAI 
from Classes.ASAI_Detect import ASAI_Detect 

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 

class AllSkyDB():

   def __init__(self):
      from lib.DEFAULTS import SHOW
      self.SHOW = SHOW
      self.AI_VERSION = 3.2
      self.home_dir = "/home/ams/amscams/"
      self.data_root = "/mnt/ams2"
      self.msdir = self.data_root + "/METEOR_SCAN/"
      self.mdir = self.data_root + "/meteors/"
      self.models_loaded = False 
      
      self.today = datetime.now().strftime("%Y_%m_%d")
      if os.path.exists("windows.json") is True:
         self.win_config = load_json_file("windows.json")
         self.meteor_dir = self.win_config['meteor_dir'] 
         self.non_meteor_dir = self.win_config['non_meteor_dir'] 
      else:
         self.meteor_dir = "/mnt/ams2/meteors/"
         self.non_meteor_dir = "/mnt/ams2/non_meteors/"
      self.json_conf = load_json_file("../conf/as6.json")
      self.lat = float(self.json_conf['site']['device_lat'])
      self.lon = float(self.json_conf['site']['device_lng'])
      self.alt = float(self.json_conf['site']['device_alt'])

      self.station_id = self.json_conf['site']['ams_id']
      self.db_file = self.home_dir + "/pipeline/" + self.station_id + "_ALLSKY.db"

      print("\rUSING DB FILE: " + self.db_file, end="")

      if os.path.exists(self.db_file ) is False:
         self.make_fresh_db()

      self.con = self.connect_database(self.station_id)
      self.cur = self.con.cursor()

      self.check_make_tables()

      self.ASAI = AllSkyAI()
      self.update_summary()
      #self.ASAI.load_all_models()
      self.ASD = ASAI_Detect()
      self.check_update_status()
      #self.reconcile_db()

   def non_meteor_inventory(self):
      """
      Places non-meteors could be
      ---------------------------
         AUTO_NON_METEORS - Moved automatically by program need review before committed
         FILESYSTEM : /mnt/ams2/non_meteors 
         DATABASE: ???

         CONFIRMED_NON_METEORS -- Human confirmed as a non-meteor. May be labeled or not. 
         /mnt/ams2/non_meteors_confirmed

         could be in before purge runs!?
         /mnt/ams2/meteors

      """

   def check_make_tables(self):
      print("CHECK MAKE TABLES")

      try:
         self.cur.execute("SELECT fireball_yn FROM non_meteors_confirmed limit 1")
         self.cur.fetchone()
         print("meteor table ok")
      except sqlite3.OperationalError as e:
         #if e.args[0].startswith('no such table'):
         print("NON_METEOR_CONFIRMED TABLE NEEDS TO BE UPDATED!")
         if True:
            # Creating table
            table = """ 
                CREATE TABLE IF NOT EXISTS "non_meteors_confirmed" (
                    "sd_vid"     TEXT,
                    "hd_vid"     TEXT,
                    "roi"   TEXT,
                    "meteor_yn"        REAL,
                    "fireball_yn"       REAL,
                    "multi_class"   TEXT,
                    "multi_class_conf"      REAL,
                    "human_confirmed"   INTEGER,
                    "human_label"   TEXT,
                    "last_updated"   INTEGER,
                    PRIMARY KEY("sd_vid")
                ); 
            """
            print("non_meteors_confirmed table created")   
            print(table)
            self.cur.execute(table)




      try:
         self.cur.execute("SELECT fireball_yn_conf FROM meteors limit 1")
         self.cur.fetchone()
         print("meteor table ok")
      except sqlite3.OperationalError as e:
         #if e.args[0].startswith('no such table'):
         print("METEOR TABLE NEEDS TO BE UPDATED!")
         cmd = "mv " + self.db_file + " " + self.db_file + ".bak"
         os.system(cmd)
         self.make_fresh_db()

      try:
         self.cur.execute("SELECT * FROM deleted_meteors")
         self.cur.fetchone()
         print("deleted meteors table ok")
      except sqlite3.OperationalError as e:
         if e.args[0].startswith('no such table'):

            print("deleted_meteors table does not exist")
            # Creating table
            table = """ CREATE TABLE deleted_meteors (
               sd_vid TEXT,
               hd_vid TEXT,
               PRIMARY KEY("sd_vid")
            )
      
            """
            print("deleted_meteors table created")   
            print(table)
            self.cur.execute(table)
      print("check make tables good")

   def report_day(self,date):
      sql = "SELECT root_fn, hd_vid, meteor_yn, meteor_yn_conf,fireball_yn_conf,mc_class, roi, ai_resp from meteors where sd_vid like ?"
      ivals = [date + "%"]
      self.cur.execute(sql, ivals)
      rows = self.cur.fetchall()
      for row in rows:
         root_fn, hd_vid, meteor_yn, meteor_yn_conf,fireball_yn_conf, mc_class, roi, ai_resp = row
         print(root_fn, hd_vid, meteor_yn_conf, fireball_yn_conf, mc_class, ai_resp)
 

   def make_fresh_db(self):
      # check if the SQL DB is created yet.
      if os.path.exists(self.db_file) is False:
         print("*** DB FILE DOESN'T EXIST:", self.db_file)
         cmd = "cat ALLSKYDB.sql | sqlite3 " + self.db_file
         print(cmd)
         os.system(cmd)
         #cmd = "python3.6 testDB.py load ALL"
         #os.system(cmd)
         #confirm = input("Load all meteors? [Y]es or any key to quit.")
         #if confirm == "Y":
         #   self.load_all_meteors()
         #else:
         #   exit()
      else:
         print("DB FILE ALREADY EXIST:", self.db_file)
         today = datetime.now().strftime("%Y_%m_%d")
         #cmd = "python3.6 testDB.py load " + today
         #os.system(cmd)

   def check_update_status(self, in_date = None):
      print("\rCheck update scan status...",end="")
      # check to make sure the ml_samples table has the lastest patch
      if os.path.exists("../conf/sqlite.json") is True:
         sql_conf = load_json_file("../conf/sqlite.json")
      else:
         sql_conf = {}
         sql_conf['updates'] = {}

      if os.path.exists("db_backups") is False:
         os.makedirs("db_backups")
       
      # if the DB exists but is not the latest version start over. 
      if "db_version" not in sql_conf:
         # this is an old DB, start over.
         if os.path.exists(self.db_file):
            cmd = "mv " + self.db_file + " db_backups/" + self.db_file + self.today
            print(cmd)
            os.system(cmd)
         sql_conf['db_version'] = 1
         save_json_file("../conf/sqlite.json", sql_conf)

         self.make_fresh_db()

      #self.purge_deleted_meteors()
      sql = "SELECT * from station_summary" 
      rows = self.cur.fetchall()


      update_summary = 1
      if len(rows) == 0:
         update_summary = 1
      if update_summary == 1:
         self.update_summary()


   def update_summary(self):
      # This function will just update the stats in the main summary table

      # get total number of METEORS in the systems 
      sql = "SELECT count(*) as ccc from meteors"
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      total_meteor_obs = rows[0][0]

      # get total number of METEORS in the system marked as meteor_yn_conf >= 50 
      sql = "SELECT count(*) as ccc from meteors WHERE meteor_yn_conf >= 50 or fireball_yn_conf >= 50 or mc_class = 'meteor'"
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      total_meteor_obs_yes = rows[0][0]

      # get total number of METEORS in the system marked as meteor_yn_conf <= 50  
      sql = "SELECT count(*) as ccc from meteors WHERE meteor_yn_conf <= 50 AND fireball_yn_conf >= 50 AND mc_class = 'meteor'"
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      total_meteor_obs_no = rows[0][0]

      # get total number of METEORS in the system marked as meteor_yn = 0
      sql = "SELECT count(*) as ccc from meteors WHERE meteor_yn_conf = ''"
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      total_meteor_obs_not_run = rows[0][0]

      # get total number of METEORS in the system marked as human = 1
      sql = "SELECT count(*) as ccc from meteors WHERE human_confirmed = 1"
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      total_meteor_human_confirmed = rows[0][0]


      # get total number of METEORS in the system marked as reduced = 1
      sql = "SELECT count(*) as ccc from meteors WHERE reduced = 1"
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      total_meteor_reduced = rows[0][0]

      # get total number of METEORS BY DAY 
      sql = "SELECT count(*), substr(root_fn,0,11) as sdd from meteors GROUP BY sdd ORDER BY sdd DESC"
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      if len(rows) > 0:
         last_day_scanned = rows[0][1]
         first_day_scanned = rows[-1][1]
      else:
         last_day_scanned = None
         first_day_scanned = None
      total_days_scanned = len(rows)

      # get total METEOR samples BY DAY 
      sql = "SELECT count(*) as ccc from ml_samples WHERE meteor_yn_conf >= 50"
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      ai_meteor_learning_samples = rows[0][0]

      # get total NON METEOR samples BY DAY 
      sql = "SELECT count(*) as ccc from ml_samples WHERE meteor_yn_conf <= 50 "
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      ai_non_meteor_learning_samples = rows[0][0]

      # get total FIREBALLS BY DAY 
      sql = "SELECT count(*) as ccc from meteors WHERE fireball_yn_conf >= 50 "
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      total_fireball_obs = rows[0][0]

      sql = """
         INSERT OR REPLACE INTO station_stats(
          station_id, total_meteor_obs, total_fireball_obs, total_meteors_human_confirmed, first_day_scanned, 
          last_day_scanned, total_days_scanned, ai_meteor_yes, ai_meteor_no, ai_meteor_not_scanned, ai_meteor_learning_samples, 
          ai_non_meteor_learning_samples, total_red_meteors, total_not_red_meteors, total_multi_station, total_multi_station_failed, total_multi_station_success) 
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)


      """
      ivals = [self.station_id, total_meteor_obs, total_fireball_obs, total_meteor_human_confirmed, first_day_scanned, last_day_scanned, total_days_scanned, total_meteor_obs_yes, total_meteor_obs_no, total_meteor_obs_not_run, ai_meteor_learning_samples, ai_non_meteor_learning_samples, total_meteor_reduced, total_meteor_obs - total_meteor_reduced, 0, 0, 0]
      if True:
         print("Total Meteor Obs:", total_meteor_obs)
         print("Total Meteor Obs AI Yes:", total_meteor_obs_yes)
         print("Total Meteor Obs AI No:", total_meteor_obs_no)
         print("Total Meteor Obs AI Not Run:", total_meteor_obs_not_run)
         print("Total Meteor Human Confirmed:", total_meteor_human_confirmed)
         print("Total Meteors Reduced:", total_meteor_reduced)
      self.cur.execute(sql, ivals)
      self.con.commit()


   def reconcile_db(self, in_date=None):
      print("Reconcile DB")
      #AIDB.load_all_meteors(date)
      # Figure out where we are with AI scans, what is not loaded yet and what has not been scanned.
      # then load / scan data that is missing. 
      # Essentially bring the database up to date with file system data and not done ai/scanning
      # This includes making ROI files as needed (should replace all MeteorScan Functions!)
      # This includes 'scan-in-stack' for non-reduced or problem captures

    
      if self.models_loaded is False :
         self.models_loaded = True
         self.ASAI.load_all_models()
         self.models = {}


      if in_date is None:
         self.load_all_meteors()
      else:
         self.load_all_meteors(in_date)
   

      print("RECONCILE DB.")

      if True:
         meteor_roots = []
         if in_date is None:
            sql = "SELECT root_fn, meteor_yn, meteor_yn_conf,roi, sync_status, hd_vid,reduced, ai_resp, mc_class from meteors order by root_fn desc"
         else:
            sql = "SELECT root_fn, meteor_yn, meteor_yn_conf,roi, sync_status, hd_vid,reduced, ai_resp, mc_class from meteors where sd_vid like '" + in_date + "%' order by root_fn desc"


         self.cur.execute(sql)
         #rows = self.cur.fetchall()
         found = 0
         not_found = 0
         for row in self.cur.fetchall():
            ai_r = row[7]
            mc_class = row[8]
            print(ai_r) 
            if ai_r != "" and ai_r is not None:
               ai_r = json.loads(ai_r)
               if "ai_version" in ai_r: 
                  if ai_r['ai_version'] >= self.AI_VERSION and mc_class is not None :
                     print("\rSkip at latest AI already.",end="")
                     continue
            roi = row[3]
            if roi != "":
               try:
                  roi = json.loads(roi)
               except:
                  roi = []

            sync_status = row[4]
            hd_vid = row[5]
            reduced = row[6]
            if sync_status != "" and sync_status is not None:
               try:
                  sync_status = json.loads(sync_status)
               except:
                  sync_status = []

            root_fn = row[0]

            root = row[0]
            meteor_yn = row[1]
            meteor_yn_conf = row[2]
            print("\rROW:" +  root , end="")
            #if isinstance(roi,str) is True and "[" in roi:
            #   roi = eval(roi)
            #else:
            #   roi = None
            if "AMS" not in root:
               date = root[0:10]
               mdir = "/mnt/ams2/meteors/" + date + "/" 
               msdir = "/mnt/ams2/METEOR_SCAN/" + date + "/" 
               roi_file = msdir + self.station_id + "_" + root + "-ROI.jpg"
               red_file = mdir + root + "-reduced.json"
            if os.path.exists(red_file) is True:
               reduced = 1
            else:
               reduced = 0
            print("RED:", red_file, reduced)
            if True:
               if os.path.exists(roi_file) is True:
                  print("ROI FILE FOUND.", roi_file)
                  roi_exists = 1
                  roi_img = cv2.imread(roi_file)
                  try:
                     roi_img = cv2.resize(roi_img,(64,64))
                     found += 1
                  except:
                     print("ROI BAD:", roi_file)
                     os.system("rm " + roi_file)
                  if True:
                     #resp = self.ASAI.meteor_yn(root_fn, None,roi_img, roi)

                     try:
                        resp = self.ASAI.meteor_yn(root_fn, None,roi_img, roi)
                     except:
                        resp = None


                     if resp is not None:
                        print("AI RESP:", resp)
                        self.insert_ml_sample(resp)
                     else:
                        print("AI RESP IS NONE! " + root_fn)
                  #try:
                  #except:
                  #   print("meteor_yn failed!", root) 
                  #   resp = None
                  if resp is not None:
                     sql = """ UPDATE meteors 
                        SET meteor_yn_conf = ?,
                            fireball_yn_conf = ?,
                            mc_class = ?,
                            mc_class_conf = ?,
                            reduced = ?,
                            ai_resp = ?
                        WHERE sd_vid = ? """
                     
                     task = [resp['meteor_yn'],resp['fireball_yn'], resp['mc_class'], resp['mc_class_conf'], reduced, json.dumps(resp), resp['root_fn'] + ".mp4"]

                     self.cur.execute(sql, task)
                     self.con.commit()
               else:
                  #print("TRY TO MAKE ROI???")
                  self.verify_media(root_fn, hd_vid, roi, sync_status, reduced,red_file)
                  roi_exists = 0
                  not_found += 1

            meteor_roots.append(root)
         #print(len(meteor_roots) , " meteors not processed")
         #print("roi not found")

         #for mr in meteor_roots:
         #   sql = """SELECT roi_fn from ml_samples where root_fn = ? and (meteor_yn_conf > 50 or fireball_yn_conf > 50 or multi_class like "%meteor%") """
         #   bind_vars = [mr]
         #   self.cur.execute(sql, bind_vars)
         #   rows = self.cur.fetchall()
         #   print(mr, len(rows))
      print("END RECONCILE DB")

   def qc_day(self, day):
      sql = """SELECT root_fn, meteor_yn, meteor_yn_conf, fireball_yn, mc_class, ai_resp
             FROM meteors order by root_fn desc limit 100;"""

   def delete_sql_meteor(self, root_fn):

      sql = """DELETE FROM meteors 
                WHERE root_fn = ?
            """ 
      ivals = [root_fn]
      self.cur.execute(sql, ivals)
      print("DELETE:", sql, ivals )
      self.con.commit()
     

   def insert_ml_sample(self, resp):
      #insert into the ROI DB!!!
      in_data = {}
      el = resp['root_fn'].split("_")
      ext = el[-1]
      camera_id = ext.split("-")[0]
      in_data['station_id']  = self.station_id
      in_data['camera_id']  = camera_id
      in_data['root_fn'] = resp['root_fn']
      x1,y1,x2,y2 = resp['roi']
      in_data['roi_fn'] = resp['root_fn'] + "_" + str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2) + ".jpg"
      if "roi_fn" not in resp:
         resp['roi_fn'] = in_data['roi_fn']
      in_data['main_class'] = ""
      in_data['sub_class'] = ""
      in_data['meteor_yn_conf'] = resp['meteor_yn']
      in_data['fireball_yn_conf'] = resp['fireball_yn']
      in_data['multi_class'] = resp['mc_class']
      in_data['multi_class_conf'] = resp['mc_class_conf']
      sql = """
             INSERT OR REPLACE INTO ml_samples(station_id, camera_id, root_fn, roi_fn, meteor_yn_conf, fireball_yn_conf, multi_class, multi_class_conf) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      """
      ivals = [self.station_id, camera_id, resp['root_fn'], resp['roi_fn'], resp['meteor_yn'], resp['fireball_yn'], resp['mc_class'], resp['mc_class_conf']]
      self.cur.execute(sql, ivals)
      self.con.commit()


   def update_meteor_ai_result(self, root, resp):   

      if resp is not None:
         sql = """ UPDATE meteors
                      SET meteor_yn_conf = ?,
                          fireball_yn = ?,
                          mc_class = ?,
                          mc_class_conf = ?,
                          ai_resp = ?,
                          roi = ?
                    WHERE sd_vid = ? """
         task = [resp['meteor_yn'], resp['fireball_yn'], resp['mc_class'], resp['mc_class_conf'], json.dumps(resp), json.dumps(resp['roi']),root + ".mp4"]
         print(sql)
         print(task)
         self.cur.execute(sql, task)
         self.con.commit()

   
   def starttime_from_file(self, filename):
      print("START TIME FILE:", filename)
      (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(filename)
      trim_num = get_trim_num(filename)
      extra_sec = int(trim_num) / 25
      extra_sec += 2
      event_start_time = f_datetime + dt.timedelta(0,extra_sec)
      return(event_start_time)

   def get_mfiles(self, mdir):
      temp = glob.glob(mdir + "/*.json")
      mfiles = []
      for json_file in temp:
         if "\\" in json_file:
            json_file = json_file.replace("\\", "/")
         if "frame" not in json_file and "events" not in json_file and "index" not in json_file and "cloud" not in json_file and "import" not in json_file and "report" not in json_file and "reduced" not in json_file and "calparams" not in json_file and "manual" not in json_file and "starmerge" not in json_file and "master" not in json_file:
            vfn = json_file.split("/")[-1].replace(".json", ".mp4")
            mfiles.append(vfn)
      return(mfiles)

   def play_video(self, root_fn, stack_img_org):
      frames = self.load_video_frames(root_fn, stack_img_org)
      for frame in frames:
         frame = cv2.resize(frame, (1280,720))
         cv2.imshow('pepe', frame)
         cv2.waitKey(30)
   

   def reducer(self,in_date=None):
      if in_date is None:
         sql = "SELECT root_fn, meteor_yn, meteor_yn_conf,fireball_yn,roi, sync_status, hd_vid,reduced, ai_resp from meteors order by root_fn desc"
      else:
         sql = "SELECT root_fn, meteor_yn, meteor_yn_conf,fireball_yn, roi, sync_status, hd_vid,reduced, ai_resp from meteors where sd_vid like '" + in_date + "%' order by root_fn desc"
      self.cur.execute(sql)
      #rows = self.cur.fetchall()
      found = 0
      not_found = 0
      for row in self.cur.fetchall():
         root_fn = row[0]
         meteor_yn = row[1]
         meteor_yn_conf = row[1]
         fireball_yn = row[3]
         roi = row[4]
         sync_status = row[5]
         hd_vid = row[6]
         reduced = row[7]
         ai_resp = row[8]
         print("Reducer: ", reduced)
         if reduced == 0:
            if roi != "" and roi is not None:
               roi = json.loads(roi)
               if sum(roi) > 0 and os.path.exists(self.meteor_dir + root_fn[0:10] + "/" + root_fn + ".mp4"):
                  print("NEEDS REDUCE:", row[0])
                  self.reduce_meteor_roi(root_fn, roi)
               else:
                  print("NEEDS REDUCE BUT NO SD VIDEO :(", row[0], roi, ai_resp)
                  print("TRASH?!") 
                  if os.path.exists(self.meteor_dir.replace("/meteors/","/trash/") + root_fn[0:10] + "/" + root_fn + ".mp4"):
                     sql = "DELETE from meteors where root_fn = '" + root_fn + "'"
                     self.cur.execute(sql)
                     self.con.commit()

                  
                  if sum(roi) > 0:
                     print("...")            

   def get_contours(self, thresh_img,sub):   

      cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      cnts = self.which_cnts(cnt_res)

      conts = []
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         intensity = int(np.sum(sub[y:y+h,x:x+w]))
         px_avg = intensity / (w*h)
         if w >= 1 and h >= 1 and px_avg > 5:
            #print("     ",x,y,w,h,intensity,px_avg)
            conts.append((x,y,w,h,intensity,px_avg))
      return(conts)

   def which_cnts(self, cnt_res):
      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res
      return(cnts)
   
   def reduce_meteor_roi(self,root_fn,roi):
      root_f = root_fn.replace(self.station_id + "_", "")
      video_file = self.meteor_dir + root_f[0:10] + "/" + root_fn + ".mp4"
      if os.path.exists(video_file) is False:
         print("No sd video!", video_file)
         return()
      cap = cv2.VideoCapture(video_file)
      grabbed = True
      last_frame = None
      stacked_frame = None
      x1,y1,x2,y2 = roi
      frames = []
      if True:
         while grabbed is True:
            grabbed, frame = cap.read()
            if not grabbed :
               break
            frame = cv2.resize(frame, (1920,1080))
            frames.append(frame[y1:y2,x1:x2])

      print("VIDEO CROPPED FRAMES:", len(frames))
 
      # check for motion in the cropped frames
      fn = 0

      for frame in frames:
         sub_frame = cv2.subtract(frame, frames[0])
         sub_frame = cv2.cvtColor(sub_frame, cv2.COLOR_BGR2GRAY)
         sub_sum = np.sum(sub_frame)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub_frame)
         thresh_val = max_val * .8
         if thresh_val < 50:
            thresh_val = 50
         if thresh_val < np.mean(sub_frame) * 1.2:
            thresh_val = np.mean(sub_frame) * 1.2
         _, thresh_frame = cv2.threshold(sub_frame, thresh_val, 255, cv2.THRESH_BINARY)
         cnts = self.get_contours(thresh_frame,sub_frame)

         print(fn, sub_sum,max_val, np.sum(thresh_frame), cnts)
         fn += 1

      return(frames)

   def load_video_frames(self,root_fn, stack_img_org):

      root_f = root_fn.replace(self.station_id + "_", "")
      video_file = self.meteor_dir + root_f[0:10] + "/" + root_fn + ".mp4"
      cap = cv2.VideoCapture(video_file)
      grabbed = True
      last_frame = None
      stacked_frame = None

      frames = []
      if True:
         while grabbed is True:
            grabbed, frame = cap.read()
            if not grabbed :
               break
            frames.append(frame)
      return(frames)

   def review_meteors(self, filters=None):
      hdm_x = 1920 / 1280
      hdm_y = 1080 / 720
      root_data_dir = "Y:/"
      fields = "root_fn"
      table = "meteors"
      key_press = ""
      where = ""
      order_by = "ORDER BY root_fn"
      self.cur.execute("""
         SELECT M.root_fn, M.roi, MS.roi_fn, MS.meteor_yn, MS.meteor_yn_conf, MS.multi_class, MS.multi_class_conf, M.human_confirmed 
            FROM meteors as M LEFT JOIN ml_samples as MS ON M.root_fn = MS.root_fn 
            ORDER BY M.root_fn DESC limit 50000
      """)
      rows = self.cur.fetchall()

      i = 0
      self.new_rois = {}
      while True:
         delete_this = False
         non_meteor = False
         human_confirm = False
   
         root_fn = rows[i][0]
         if root_fn not in self.new_rois:
            roi = rows[i][1]
         else:
            roi = self.new_rois[root_fn]

         roi_fn = rows[i][2]

         if roi_fn is not None:
            if "RX" in roi_fn:
               rx = roi_fn.split("-RX_")
               rx = rx[-1].replace(".jpg", "")
               x1,y1,x2,y2 = rx.split("_")
               roi = [int(x1),int(y1),int(x2),int(y2)]

         meteor_yn = rows[i][3]
         meteor_yn_conf = rows[i][4]
         multi_class = rows[i][5]
         multi_class_conf = rows[i][6]
         human_confirmed = rows[i][7]

         mday = root_fn[0:10]
         mdir = root_data_dir + "meteors/" + mday + "/"
         msdir = root_data_dir + "METEOR_SCAN/" + mday + "/"
         roi_file = msdir +  root_fn + "-ROI.jpg"
         stack_file = mdir +  root_fn + "-stacked.jpg"
         sd_video_file = mdir +  root_fn + ".mp4"
         json_file = mdir +  root_fn + ".json"

         status = []
         print(roi_file)
         if os.path.exists(json_file) is True:
            status.append(1)
         else:
            status.append(0)

         if os.path.exists(sd_video_file) is True:
            status.append(1)
         else:
            status.append(0)

         if os.path.exists(stack_file) is True:
            status.append(1)
         else:
            status.append(0)

         if os.path.exists(roi_file) is True:
            status.append(1)
         else:
            status.append(0)

         detect_color = [128,128,128]

         if meteor_yn is not None and meteor_yn_conf is not None:
            if meteor_yn == 1:
               meteor_yn = "METEOR"
               detect_color = [0,128,0]
            else:
               meteor_yn = "NON-METEOR"
               detect_color = [0,0,255]
            desc = str(meteor_yn) + " " + str(meteor_yn_conf)[:4] + "%" 
            desc += " - " + str(multi_class) + " " + str(multi_class_conf)[:4] + "%"
            desc2 = root_fn + " "  + str(i) + " / " + str(len(rows))
         else:
            desc = "not scanned"
            desc2 = root_fn + " "  + str(i) + " / " + str(len(rows))
         if isinstance(roi, str) is True:
            if roi != "":
               roi = eval(roi)
         if len(roi) == 4:
            x1,y1,x2,y2 = roi
            x1 = int(x1 / hdm_x)
            y1 = int(y1 / hdm_y)
            x2 = int(x2 / hdm_x)
            y2 = int(y2 / hdm_y)
         else:
            x1,y1,x2,y2 = 0,0,0,0
         if os.path.exists(stack_file) is True:
            stack_img_org = cv2.imread(stack_file)
            stack_img = cv2.resize(stack_img_org, (1280,720))
            cv2.imshow('pepe', stack_img)

            (roi, self.new_rois, stack_img) = self.handle_keypress(root_fn, roi_fn, stack_img_org, key_press, roi, self.new_rois)
            if len(roi) == 4:
               x1,y1,x2,y2 = roi
               x1 = int(x1 / hdm_x)
               y1 = int(y1 / hdm_y)
               x2 = int(x2 / hdm_x)
               y2 = int(y2 / hdm_y)
            stack_img = cv2.resize(stack_img_org, (1280,720))
            cv2.rectangle(stack_img, (x1,y1), (x2,y2), (255, 255, 255), 1)

            cv2.putText(stack_img, desc,  (10, 20), cv2.FONT_HERSHEY_SIMPLEX, .6, detect_color, 1)
            cv2.putText(stack_img, desc2,  (10, 710), cv2.FONT_HERSHEY_SIMPLEX, .6, detect_color, 1)
            cv2.imshow('pepe', stack_img)
            key_press = cv2.waitKeyEx(0)

            if key_press == 113:
               cv2.destroyAllWindows()
               return()
            if key_press == 102:
               i += 1
            if key_press == 97:
               i -= 1



         else:
            desc2 = root_fn + " "  + str(i) + " / " + str(len(rows))

            blank_image = np.zeros((720,1280,3),dtype=np.uint8)
            cv2.putText(blank_image, desc2,  (10, 710), cv2.FONT_HERSHEY_SIMPLEX, .6, detect_color, 1)
            cv2.imshow('pepe', blank_image)
            key_press = cv2.waitKey(0)
            if key_press == 113:
               cv2.destroyAllWindows()

               return()
            if key_press == 102:
               i += 1
            if key_press == 97:
               i -= 1

   def verify_media_day(self, selected_day):
      print("\rVerify Media                             ", end="")
      sql = "SELECT sd_vid, hd_vid, roi, sync_status, ai_resp from meteors where sd_vid like ? " #and meteor_yn = ''" 
      self.cur.execute(sql, [selected_day + "%"])
      rows = self.cur.fetchall()
      loaded_meteors = {}

      for row in rows:
         sd_vid, hd_vid, roi, sync_status, ai_resp = row
         root_fn = sd_vid.split("/")[-1].replace(".mp4", "")
         self.check_make_roi(root_fn, roi)
      #exit()


      for row in rows:
         loaded_meteors[row[0]] = 1
         sd_vid = row[0]
         hd_vid = row[1]
         roi = row[3]
         ai_resp = row[4]
         root_file = sd_vid.replace(".mp4", "")
         roi_fn = self.station_id + "_" + root_file + "-ROI.jpg"
         roi_file = self.msdir + roi_fn 
         red_file = "/mnt/ams2/meteors/" + root_file[0:10] + "/" + root_file + "-reduced.json" 
         print("MEDIA:", sd_vid, hd_vid, roi, ai_resp)
         if os.path.exists(red_file) is True:
            reduced = 1
         else:
            reduced = 0
         if row[2] != "" and row[2] is not None:
            print("ROW2:", row[2])
            roi = json.loads(row[2])
         else:
            roi = None
         if row[3] != "":
            try:
               sync_status = json.loads(row[3])
            except:
               print("No current sync status.")
         else:
            sync_status = []
         if ai_resp is not None and ai_resp != "":
            ai_resp = json.loads(ai_resp)
            if "ai_version" in ai_resp:
               if ai_resp['ai_version'] >= self.AI_VERSION and os.path.exists(roi_file) is True:
                  print("\rSKIP DONE!",end="")
                  continue
         
         self.verify_media(root_file, hd_vid, roi, sync_status,reduced,red_file)
      print("\rFinished verify media", end="")

   def check_make_roi(self, root_file, roi):
      roi_file = "/mnt/ams2/METEOR_SCAN/" + root_file[0:10] + "/" + root_file + "-ROI.jpg"
      if os.path.exists(roi_file) is False:
         print("NO ROI FILE FOUND!", roi_file)
      else:
         print("YES ROI FILE FOUND!", roi_file)
      if roi is None or roi == "":
         print("ROI VALS MISSING!", roi)
      else:
         print("YES ROI VAL", roi)



   def verify_media(self, root_file, hd_vid, roi, sync_status,reduced=1,red_file=None):
      # Multi-level checks here. Starting with...
      # LOCAL MEDIA (files on this HD)
      # roi file
      print("VERIFY MEDIA")
 
      roi_exists = False

      if roi == "":
         roi = None 
      else:
         roi_el = str(roi).split(",")
         if len(roi_el) != 4:
            roi = None
         else:
            x1,y1,x2,y2 = roi
     
      roi_file = self.msdir + root_file[0:10] + "/" + self.station_id + "_" + root_file + "-ROI.jpg"
      if roi is not None and os.path.exists(roi_file) is True: 
         #print("\rROI :", roi, roi_file, os.path.exists(roi_file))
         tsz,td = get_file_info(roi_file)

         if "roi_jpg" not in sync_status or tsz == 0:
            if isinstance(sync_status, str) is True:
               try: 
                  sync_status = json.loads(sync_status)
               except:
                  sync_status = []
            if isinstance(sync_status, dict) is True:
               sync_status = []
            sync_status.append('ROI.jpg')
            sync_status = sorted(list(set(sync_status)))

         if os.path.exists(roi_file) is True and tsz > 0:
            print("ROI JPG GOOD!", roi_file, tsz)
            roi_exists = True
            sync_status.append('ROI.jpg')
            sync_status = sorted(list(set(sync_status)))
         else:
            stack_file = self.mdir + root_file[0:10] + "/" + root_file + "-stacked.jpg"
            if os.path.exists(stack_file) is True:
               stack_img = cv2.imread(stack_file)
               stack_img = cv2.resize(stack_img,(1920,1080))

               roi_img = stack_img[y1:y2,x1:x2]  
               roi_file = self.msdir + root_file[0:10] + "/" + self.station_id + "_" + root_file + "-ROI.jpg"
               cv2.imwrite(roi_file, roi_img)
               roi_exists = True
            sync_status.append('ROI.jpg')
            sync_status = sorted(list(set(sync_status)))
      else:
         print("ROI IS NONE! WHY?/CAN WE FIX IT!", root_file)
         if False:
            print("We can't make an ROI image because there is no ROI defined! What should we do? ")
            print("1) Check for a reduced file again? Maybe it is not updated? red=", reduced )
            print("2) Check the stack image for AI detects?")
            print("2a) Then run those through video detection and reduction?")
            print("2b) Then if they are meteors accept them")
            print("2c) Else accept the most prominent object?")

         # Check the stack for objects
         if reduced == 1 and red_file is not None:
            print("MAKE ROI FROM REDUCED FILE")
            if os.path.exists(red_file) is True:
               try:
                  red_data = load_json_file(red_file)
               except:
                  print("   NO VALID REDUCED FILE!")
                  red_data = {}
               if "meteor_frame_data" in red_data:
                  print("   MFD FOUND!")
                  mfd = red_data['meteor_frame_data']
             
                  x1,y1,x2,y2 = mfd_roi(mfd)
                  print("   NEW ROI:!", x1,y1,x2,y2)
                  stack_file = self.mdir + root_file[0:10] + "/" + root_file + "-stacked.jpg"
                  stack_img = cv2.imread(stack_file)
                  stack_img = cv2.resize(stack_img, (1920,1080))
                  #print(x1,y1,x2,y2)
                  roi_val = [x1,y1,x2,y2]
                  roi_img = stack_img[y1:y2,x1:x2]
                  roi_file = self.msdir + root_file[0:10] + "/" + self.station_id + "_" + root_file + "-ROI.jpg"
                  try:
                     cv2.imwrite(roi_file,roi_img)
                  except:
                     print("BAD ROI IMG WRITE")
                  #print("Saved:", roi_file) 
                  print("STACK SIZE!", stack_img.shape)
                  print("ROI SIZE!", roi_img.shape)
                  print("FIXED ROI FROM REDUCED FILE!", roi_file)

         else:
      
            print("REDUCED FILE NOT FOUND!!", red_file)
            stack_file = self.mdir + root_file[0:10] + "/" + root_file + "-stacked.jpg"
            if os.path.exists(stack_file) is True:
               print("\r *** DETECT IN STACK " + root_file, end="")
               detect_img, roi_imgs, roi_vals = self.ASD.detect_in_stack(stack_file )
               print("DONE DETECT IN STACK.")
               meteor_found = False 
               if roi_imgs is not None:
                  if len(roi_imgs) > 0:
                     for i in range(0, len(roi_imgs)):
                        print("Working on roi img", roi_imgs[i].shape)
                        roi_img = roi_imgs[i]
                        roi_val = roi_vals[i]
                        print("Try YN")
                        resp = self.ASAI.meteor_yn(root_file, None,roi_img,roi_val)
                        print("END YN")
                        if resp is not None:
                           self.insert_ml_sample(resp)
                           if resp['meteor_yn'] >50 or resp['fireball_yn'] >50 or "meteor" in resp['mc_class']:
                              self.update_meteor_ai_result(root_file, resp)
                              # save the ROI image!
                              roi_file = self.msdir + root_file[0:10] + "/" + self.station_id + "_" + root_file + "-ROI.jpg"
                              print("SAVE NEW METEOR ROI:", roi_file)
                              cv2.imwrite(roi_file, roi_img)
                              meteor_found = True
                           else:
                              # only save roi if a meteor has not been found
                              if meteor_found is False:
                                 self.update_meteor_ai_result(root_file, resp)
                                 roi_file = self.msdir + root_file[0:10] + "/" + self.station_id + "_" + root_file + "-ROI.jpg"
                                 print("SAVE NEW METEOR ROI:", roi_file)
                                 cv2.imwrite(roi_file, roi_img)
                        else:
                           print("AI RESP IS NONE!")
                        print("AI RESP:", resp)
                        #YOYO

                     #try:
                     #except: 
                     #   print("FAILED AI.meteor_yn CHECK!", roi_val)
               if meteor_found is False:
                  print("Meteor not found in AI stack scan!")


            else:
               print("NO STACK FILE FOUND!", stack_file)
         #try:
         #except:
         #   print("FAILED TO DETECT IN STACK!")


      # UPDATE THE DB WITH LATEST MEDIA SYNC STATUS (Local & Cloud)
      # Status : Key Not Found = Local & Cloud media not exist; 1 = local media exists; 2 = local and cloud media exists
      # Rules: Only push cloud media if: Human confirmed is True, or Multi-Station Confirmed is True, or AI Meteor is True (and high?)
 

      # CLOUD MEDIA (files on wasabi drive)

   def load_stations(self):
      my_network = {}
      from lib.PipeUtil import dist_between_two_points
      url = "https://archive.allsky.tv/EVENTS/ALL_STATIONS.json"
      response = requests.get(url)
      content = response.content.decode()
      stations =json.loads(content)
      for station in stations:
         t_station_id = station['station_id']
         try:
            slat = float(station['lat'])
            slon = float(station['lon'])
            alt = float(station['alt'])
         except:
            slat = 0
            slon = 0
         dist = int(dist_between_two_points(self.lat, self.lon, slat, slon))
         if dist < 300:
            print("***", t_station_id, dist) 
            my_network[t_station_id] = {}
            my_network[t_station_id]['dist_to_me'] = dist
            my_network[t_station_id]['lat'] = slat
            my_network[t_station_id]['lon'] = slon
            my_network[t_station_id]['alt'] = alt
            my_network[t_station_id]['operator'] = station['operator_name']
            my_network[t_station_id]['city'] = station['city']
         else:
            print(t_station_id, dist) 
         self.json_conf['my_network'] = my_network
      save_json_file("../conf/as6.json", self.json_conf)
      return(stations)
     

   def load_all_meteors(self, selected_day = None):
      if self.models_loaded is False:
         self.ASAI.load_all_models()
         self.models_loaded = True

      if selected_day is not None:
         print("\rLoad meteors for day: " + selected_day, end= "")
         sql = "SELECT sd_vid, reduced from meteors where sd_vid like ?" 
         self.cur.execute(sql, [selected_day + "%"])
      else:
         sql = "SELECT sd_vid,reduced from meteors " 
         self.cur.execute(sql)


      rows = self.cur.fetchall()
      loaded_meteors = {}
      print("Rows already loaded:", len(rows))
      rc = 0 
      for row in rows:
         print("ROW:", rc, row[0])
         loaded_meteors[row[0]] = row[1]
         rc += 1

      if selected_day is None:
         dirs = os.listdir(self.meteor_dir)
      else:
         dirs = [selected_day]
      self.mdirs = []
      self.mfiles = []
      
      errors = {}
      for ddd in sorted(dirs,reverse=True):
         if os.path.isdir(self.meteor_dir + ddd):
            self.mdirs.append(self.meteor_dir + ddd + "/")
            if os.path.exists(self.msdir + ddd) is False:
               os.makedirs(self.msdir + ddd) 

      for mdir in sorted(self.mdirs):  
         mfiles = self.get_mfiles(mdir )
         self.mfiles.extend(mfiles)
      # Main file loop here. 1 iter per meteor 
      mc = 0
      for mfile in sorted(self.mfiles, reverse=True):
         mc += 1
         print("Meteor file", mc, mfile)
         #if "STATION_EVENT" in mfile:
         #   continue
         # each iter is 1 meteor json file getting loaded into the SQL.
         # break out into a function?
         if mfile in loaded_meteors :
            if loaded_meteors[mfile] == 1:
               foo = 1
               print("   Already loaded", mfile) 
               continue
         mdir = mfile[0:10]
         el = mfile.split("_")
         mjf = self.meteor_dir + mdir + "/" + mfile.replace(".mp4", ".json")
         mjrf = self.meteor_dir + mdir + "/" + mfile.replace(".mp4", "-reduced.json")
         start_time = None
         if os.path.exists(mjf) is True:
            mj = load_json_file(mjf)
            try:
               mj = load_json_file(mjf)
            except:
               errors[mjf] = "couldn't open json file"
               continue

         mfd = ""
         if os.path.exists(mjrf) is True:
            try:
               mjr = load_json_file(mjrf)
            except:
               mjr = None
            if mjr is not None:
               if "meteor_frame_data" in mjr :
                  if len(mjr['meteor_frame_data']) > 0:
                     mfd = mjr['meteor_frame_data']
                     start_time = mfd[0][0]
            reduced = 1
         else:
            mjr = None
            reduced = 0

         if start_time is None:
            start_time = self.starttime_from_file(mfile)
            start_time = start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
         if "sd_video_file" not in mj:
            continue
         sd_vid = mj['sd_video_file'].split("/")[-1]
         hd_vid = ""
         if "hd_trim"  in mj:
            if mj['hd_trim'] is not None:
               if isinstance(mj['hd_trim'], str) is True:
                  hd_vid = mj['hd_trim'].split("/")[-1]

         if 'multi_station_event' in mj:
            mse = 1
            if "event_id" in mj['multi_station_event']:
               event_id = mj['multi_station_event']['event_id']
            else:
               event_id = 0
               mse = 0
         else:
            mse = 0
            event_id = 0

         if "hc" in mj :
            human_confirmed = 1
         else:
            human_confirmed = 0
 
        
         if "user_mods" in mj :
            if len(mj['user_mods'].keys()) > 0:
               human_confirmed = 1
               user_mods = mj['user_mods']
            else:
               user_mods = ""
         else:
            user_mods = ""
         ang_vel = 0
         if "best_meteor" in mj:
            if "report" in mj['best_meteor']:
               if "ang_vel" in mj['best_meteor']['report']:
                  ang_vel =  mj['best_meteor']['report']['ang_vel']

         if mjr is not None:
            if "meteor_frame_data" in mjr:
               mfd = mjr['meteor_frame_data']

         calib = ""
         if "cp" in mj:
            cp = mj['cp']
            if cp is not None:
               if "cat_image_stars" not in cp:
                  cp['cat_image_stars'] = []
                  cp['user_stars'] = []
               print(cp.keys())
               if "total_res_px" not in cp:
                  cp['total_res_px'] = 999
               try:
                  calib = [cp['ra_center'], cp['dec_center'], cp['center_az'], cp['center_el'], cp['position_angle'], cp['pixscale'], float(len(cp['cat_image_stars'])), float(cp['total_res_px'])]
                  mj['calib'] = calib
               except:
                  print("mj calib issue")

         if "calib" in mj:
            calib = mj['calib']
         if "sync_status" in mj:
            sync_status = json.dumps(mj['sync_status'])
         else:
            sync_status = ""

         if mfd != "":
            duration = len(mfd) / 25
         else:
            duration = "0"

         hd_roi = ""
         if "hd_roi" in mj:
            hd_roi = mj['hd_roi']
         if mjr is not None:
            if "meteor_frame_data" in mjr:
               x1,y1,x2,y2 = mfd_roi(mfd)
               mj['hd_roi'] = [x1,y1,x2,y2]
               hd_roi = [x1,y1,x2,y2]
   

         ext = el[-1]
         camera_id = ext.split("-")[0]

         #self.verify_media(self.station_id, mfile.replace(".mp4", ""))

         in_data = {}
         in_data['station_id'] = self.station_id
         in_data['camera_id'] = camera_id
         in_data['root_fn'] = mfile.replace(".mp4", "")
         in_data['sd_vid'] = sd_vid
         in_data['hd_vid'] = hd_vid
         in_data['start_datetime'] = start_time
         in_data['meteor_yn'] = ""
         in_data['meteor_yn_conf'] = ""
         in_data['human_confirmed'] = human_confirmed
         in_data['reduced'] = reduced
         in_data['multi_station'] = mse
         in_data['event_id'] = event_id
         in_data['ang_velocity'] = float(ang_vel)
         in_data['duration'] = float(duration)
         if hd_roi != "":
            in_data['roi'] = json.dumps(hd_roi)
         in_data['sync_status'] = sync_status
         in_data['calib'] = json.dumps(calib)
         in_data['mfd'] = json.dumps(mfd)
         in_data['user_mods'] = json.dumps(user_mods)
         if mfile in loaded_meteors:
            del (in_data['human_confirmed'])
            print("SKIP already loaded")
            continue
            #self.update_meteor(in_data)
            #print("UPDATE EXISTING")
         else: 
            self.dynamic_insert(self.con, self.cur, "meteors", in_data)
            #print("INSERT NEW")
         mj['in_sql'] = 1
         save_json_file(mjf, mj)


   def connect_database(self,station_id):
      con = sqlite3.connect(station_id + "_ALLSKY.db")
      con.row_factory = sqlite3.Row
      return(con)

   def update_meteor(self, in_data):
      sql = "UPDATE meteors set "
      vals = ""
      for field in in_data:
         if vals != "" and in_data[field] != "":
            vals += ","
         if isinstance(in_data[field], int) is True or isinstance(in_data[field], float) is True:  
            vals += field + " = " + str(in_data[field]) 
         elif in_data[field] == "":
            foo = "bar"
         else:
            vals += field + " = '" + in_data[field] + "'"
            
      sql += vals + " WHERE root_fn = '" + in_data['root_fn'] + "'"
      print(sql)
      print("\r updating: " + in_data['root_fn'] , end="")
      self.cur.execute(sql)
      self.con.commit()
 


   def dynamic_select(self, table, fields, where):
      self.cur.execute("SELECT " + fields + "FROM " + table + " WHERE " + where)
      rows = cur.fetchall()
      return(rows)


   def dynamic_insert(self,con, cur, table_name, in_data):
      # Pass in the table name 
      # and a dict of key=value pairs
      # then the dict will be converted to sql and insert or replaced into the table. 
      
   
      values = []
      fields = []
      sql = "INSERT INTO " + table_name + " ( "
      vlist = ""
      flist = "" 
      for key in in_data:
         if flist != "":
            flist += ","
            vlist += ","
         flist += key 
         vlist += "?" 
         fields.append(key)
         values.append(in_data[key])

      flist += ")"
      vlist += ")"
      sql += flist + " VALUES (" + vlist 

      cur.execute(sql, values)
      con.commit()
      return(cur.lastrowid)



   def help(self, stack_img_org, stack_img):
      help_items = [] 
      help_items.append("Navigate Meteors")
      help_items.append("   [F9] = search filters")
      help_items.append("   [A] = previous meteor ")
      help_items.append("   [F] = next meteor")
      help_items.append("(Navigating past a meteor without pressing [X] or [Y] will 'human confirm' the ML class)")

      help_items.append("Overide ROI Classification (Meteor/Non Meteor)")
      help_items.append("   [Y] = Set ROI class to Meteor")
      help_items.append("   [X] = Set ROI class to NON-Meteor")

      help_items.append("Adjust ROI")
      help_items.append("   [up/down/left/right] = move center ROI")
      help_items.append("   [+] / [-]            = make ROI bigger/smaller")
      help_items.append("Meteor")
      help_items.append("   [P] = play video")
      help_items.append("   [M] = show meteor points")
      help_items.append("   [R] = reduce meteor points")
      help_items.append("Astrometry")
      help_items.append("   [S] = show stars")
      help_items.append("   [F] = fit stars")
      help_items.append("Special")
      help_items.append("   [ESC] = Quit Program")
      help_items.append("   [?]   = Toggle Help ")
      yy = 25 
      for row in help_items:

         cv2.putText(stack_img, row,  (25, yy), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,0,255), 1)
         yy += 30 

      cv2.imshow('pepe', stack_img)
      cv2.waitKey(0)


   def handle_keypress(self,root_fn, roi_fn, stack_img_org, key_press, roi, new_rois):
      modded = False
      x1,y1,x2,y2 = 0,0,0,0
      mod_x1 = 0
      mod_x2 = 0
      mod_y1 = 0
      mod_y2 = 0
      stack_img = cv2.resize(stack_img_org, (1280,720))
      new_roi_img = stack_img_org[y1:y2,x1:x2]
      hdm_x = 1920 / 1280
      hdm_y = 1080 / 720
      if key_press == 2490368:
         # move up
         mod_x1 = 0
         mod_y1 = -10
         mod_x2 = 0
         mod_y2 = -10
         modded = True
      if key_press == 2621440:
         # move down
         mod_x1 = 0
         mod_y1 = 10
         mod_x2 = 0
         mod_y2 = 10
         modded = True
      if key_press == 2424832:
         # move down
         mod_x1 = -10
         mod_y1 = 0
         mod_x2 = -10
         mod_y2 = 0
         modded = True
      if key_press == 2555904:
         # move down
         mod_x1 = 10
         mod_y1 = 0
         mod_x2 = 10
         mod_y2 = 0
         modded = True

      if key_press == 47:
         self.help(stack_img_org, stack_img)
         modded = False

      if key_press == 45:
         # minus
         mod_x1 = 10
         mod_y1 = 10
         mod_x2 = -10
         mod_y2 = -10
         modded = True
      if key_press == 61:
         # plus
         mod_x1 = -10
         mod_y1 = -10
         mod_x1 = 10
         mod_y2 = 10
         modded = True
      if key_press == 112:
         # [p] play
         self.play_video(root_fn, stack_img_org)
         
      if modded is True:
         if root_fn in new_rois:
            x1,y1,x2,y2 = new_rois[root_fn]
         else:
            if len(roi) == 4:
               x1,y1,x2,y2 = roi

         x1 += mod_x1
         y1 += mod_y1
         x2 += mod_x2
         y2 += mod_y2

         new_roi_img = stack_img_org[y1:y2,x1:x2]
         new_roi_img_filename =  root_fn + "-RX_" + str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2) + ".jpg"
         
         x1 = int(x1/hdm_x)
         y1 = int(y1/hdm_y)
         x2 = int(x2/hdm_x)
         y2 = int(y2/hdm_y)

         # bound the new cnt
         ww = x2 - x1
         hh = y2 - y1
         if ww > hh:
            size = int(ww / 2)
         else:
            size = int(hh / 2)
         cx1 = int((x1+x2) / 2)
         cy1 = int((y1+y2) / 2)
         x1,y1,x2,y2 = bound_cnt(cx1,cy1,1280,720, size)
         cv2.rectangle(stack_img, (x1,y1), (x2,y2), (255, 255, 255), 1)

         x1 = int((x1*hdm_x) )
         y1 = int((y1*hdm_y) )
         x2 = int((x2*hdm_x) )
         y2 = int((y2*hdm_y) )

         roi = [x1,y1,x2,y2]
         new_rois[root_fn] = roi

         cv2.putText(stack_img, "HANDLE",  (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (9,8,255), 1)
         cv2.imshow('pepe', stack_img)
         #cv2.waitKeyEx(0)

      return(roi, new_rois, stack_img)

   def auto_reject_mc(self):
      sql = """SELECT root_fn, hd_vid, meteor_yn_conf,fireball_yn_conf,mc_class, mc_class_conf, roi,ai_resp 
                 FROM meteors 
                WHERE (
                      mc_class != 'meteor' 
                  AND mc_class != 'fireball')
                  AND (
                      mc_class_conf >  meteor_yn_conf 
                   OR mc_class_conf > fireball_yn_conf)
                  AND mc_class_conf >= 98 
                  AND meteor_yn_conf <= 70
                  AND fireball_yn_conf <= 70
            """
 

   def auto_reject_day(self, date, RN=None ):
      # check all meteors for a day and reject if they don't have the right AI results
      # Skip this AI check on meteors that have been manually detected, reduced or edited. 
      non_meteor_dir = self.non_meteor_dir + date
      # as of 4/2023, human values were not in the meteors table!
      sql = "SELECT root_fn, hd_vid, meteor_yn_conf,fireball_yn_conf,mc_class, mc_class_conf, roi,ai_resp from meteors where sd_vid like ?"
      ivals = [date + "%"]
      self.cur.execute(sql, ivals)
      rows = self.cur.fetchall()
      ai_info = []
      for row in rows:
         root_fn, hd_vid, meteor_yn_conf,fireball_yn_conf, mc_class, mc_class_conf, roi,ai_resp = row
         decision = "ACCEPT"
         # AI has not run yet so just accept it
         if meteor_yn_conf is None or fireball_yn_conf is None or mc_class is None:
            decision = "ACCEPT"
            print("MISSING AI DATA FOR", root_fn, meteor_yn_conf, fireball_yn_conf, mc_class, mc_class_conf)
            if mc_class is None:
               mc_class = "unknown"
               mc_class_conf = 50
            if meteor_yn_conf is None or meteor_yn_conf == "":
               meteor_yn_conf = 50
            if fireball_yn_conf is None or fireball_yn_conf == "":
               fireball_yn_conf = 50
            #continue

         # AI Reject conditions
         if (int(meteor_yn_conf) < 51 and int(fireball_yn_conf) < 51 and "meteor" not in mc_class) or \
               (int(meteor_yn_conf) < 70 and "meteor" not in mc_class and int(mc_class_conf) >= 98) or \
               (int(meteor_yn_conf) <= 1 and int(fireball_yn_conf) <= 1) or \
               (int(meteor_yn_conf) <= 5 and int(fireball_yn_conf) <= 51 and \
                  "meteor" not in mc_class and int(mc_class_conf) >= 52):

            mjf = "/mnt/ams2/meteors/" + root_fn[0:10] + "/" + root_fn + ".json"
            if os.path.exists(mjf) is True:
               mj = load_json_file(mjf)
            else:
               mj = {}
        
         
            # Override if the "hc" human confirm does not exist and no manual edits exist
            if "hc" in mj :
               decision = "ACCEPT"
            if "user_mods" in mj:
                if "frames" in mj['user_mods']:
                   if len(mj['user_mods']['frames']) > 0:
                      decision = "ACCEPT"

            if decision == "REJECT":


               print("AI REJECT CURRENT ROI", root_fn, hd_vid, meteor_yn_conf, fireball_yn_conf, mc_class, mc_class_conf )
               print("AI seeking alternative ROI...")
               stack_file = "/mnt/ams2/meteors/" + root_fn[0:10] + "/" + root_fn + "-stacked.jpg"
               img = cv2.imread(stack_file)
               #img = RN.get_stack_img_from_root_fn(root_fn)
               if RN is not None:
                  if img is not None:
                     #objects = RN.detect_objects_in_stack(self.station_id, root_fn, img.copy())
                     objects = []

                  else:
                     objects = []
               else:
                  objects = []
               meteor_found = False
               for oo in objects:
                  if oo[0] > 90:
                     print("METEOR OBJ FOUND HERE:", oo)
                     meteor_found = True 
                     new_roi = oo[1]
                     print("OBJECTS AI ACCEPT", root_fn, hd_vid, oo[0], oo[0], "meteor", oo[0], new_roi)
                     roi = new_roi
                  #fireball_yn_conf = oo[0]
                  #meteor_yn_conf = oo[0]
                  #mc_class_conf = oo[0]
                  #mc_class = "meteor"
                     print("Need to reduce new location!")
                     decision = "ACCEPT"
            print("AI CHECK:", decision, root_fn, meteor_yn_conf, fireball_yn_conf, mc_class, mc_class_conf)
            ai_info.append((decision, root_fn, hd_vid, roi, meteor_yn_conf, fireball_yn_conf, mc_class, mc_class_conf ))

      rejects = []
      for aid in ai_info:
         print(aid)     
         if aid[0] == "REJECT":
            print("AID:", aid)
            rejects.append(aid)
      if os.path.exists(self.mdir + date) is False:
         os.makedirs(self.mdir + date)
      save_json_file(self.mdir + date + "/" + self.station_id + "_" + date + "_AI_DATA.info", ai_info)
      print("saved:", self.mdir + date + "/" + self.station_id + "_" + date + "_AI_DATA.info")
      print("REJECTS:", len(rejects))
      if len(rejects) > 0:
         if os.path.exists(non_meteor_dir) is False:
            os.makedirs(non_meteor_dir)
         for data in rejects:
            print("REJECT data:", data)

            sd_root = data[1].replace(".mp4", "")
            if ".json" in sd_root:
               sd_root = sd_root.replace(".json", "")
            if "/" in sd_root:
               sd_root = sd_root.split("/")[-1]

            hd_root = data[2].replace(".mp4", "")
            # reject these files and move to non-meteor dir unless
            # it is a MSE event or human / manual confirm exists
            mjf = self.meteor_dir + date + "/" + sd_root + ".json"
            print("MJF:", mjf)
            if os.path.exists(mjf):
               print("REJECT METEOR MJF EXISTS", mjf)
               try:
                  mj = load_json_file(mjf)
               except:
                  print("BAD MJF:", mjf)
                  continue
               #if "multi_station_event" in mj or "human_confirmed" in mj or "hc" in mj or "manual" in mj or "human_points" in mj:
        
               #   continue
               if "human_confirmed" in mj or "hc" in mj or "manual" in mj or "human_points" in mj:
                  print("   KEEP: Multi station or Human confirmed already")
                  continue
               else:
                  print("   REJECT:", self.mdir + sd_root, self.mdir + hd_root)
                  cmd = "mv " + self.mdir + date + "/" + sd_root + "* " + non_meteor_dir + "/"
                  print(cmd)
                  os.system(cmd)
                  cmd = "mv " + self.mdir + date + "/" + hd_root + "* " + non_meteor_dir + "/"
                  print(cmd)
                  os.system(cmd)
            else:
               print("MJF DOES NOT EXIST", mjf)
               print("DELETE", mjf.replace(".json", ""))
               root_fn = mjf.split("/")[-1].replace(".json", "")
               self.delete_sql_meteor(root_fn)
      else:
         print("There are no meteors worthy of rejection.")
      print("Finished auto_reject_day !")

   def mc_rejects(self):
      # select and reject rows matching the MC reject case
      reject_dir = "/mnt/ams2/non_meteors/classes/"
      sql = """SELECT sd_vid,hd_vid, meteor_yn_conf, fireball_yn_conf,mc_class,mc_class_conf,ai_resp FROM meteors
                WHERE (
                      mc_class_conf >  meteor_yn_conf
                  AND mc_class_conf > fireball_yn_conf)
                  AND mc_class_conf >= 98
                  AND meteor_yn <= 60 
                  AND fireball_yn <= 60 
                  AND mc_class not like 'meteor%'
                  AND mc_class not like 'orion%'
                  AND root_fn not like '2019%'
                  AND human_confirmed != 1
                  AND multi_station != 1
            """
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      ai_info = []
      for row in rows:
         sd_vid,hd_vid,meteor_yn_conf,fireball_yn_conf, mc_class,mc_class_conf,ai_resp = row
         print(sd_vid, meteor_yn_conf, fireball_yn_conf, mc_class, mc_class_conf)
         if ai_resp is not None:
            ai_resp = json.loads(ai_resp)
            if int(ai_resp['ai_version']) <= self.AI_VERSION:
               print("SKIP DONE")
               continue
         mdir = "/mnt/ams2/meteors/" + sd_vid[0:10] + "/" 
         if os.path.exists(mdir  + sd_vid) is True:
            print("REJECT:", sd_vid, hd_vid, meteor_yn_conf, fireball_yn_conf, mc_class, mc_class_conf)
         else:
            print("DELETE:", sd_vid, hd_vid, meteor_yn_conf, fireball_yn_conf, mc_class, mc_class_conf)

      print("Done mc rejects.") 

   def check_file_location(self, root_file):
      date = root_file[0:10]
      wild = root_file + "*"
      mdir = "/mnt/ams2/meteors/{}/".format(date)
      msdir = "/mnt/ams2/METEOR_SCAN/{}/".format(date)
      nmdir = "/mnt/ams2/non_meteors/{}/".format(date)
      nmcdir = "/mnt/ams2/non_meteors_colnfirmed/{}/".format(date)

      meteor_files = glob.glob(mdir + wild)
      meteor_scan_files = glob.glob(msdir + wild)
      non_meteor_files = glob.glob(nmdir + wild)
      non_meteor_confirmed_files = glob.glob(nmcdir + wild)
      #print("FILES:", root_file, meteor_files, meteor_scan_files, non_meteor_files, non_meteor_confirmed_files)
      return(meteor_files, meteor_scan_files, non_meteor_files, non_meteor_confirmed_files)


   def purge(self):
      # move confirmed non-meteors still in the meteor dir to the non-meteor dir
      # remove the meteors database record
      # insert non-meteor record in non_meteors table
      sql = """
               SELECT sd_vid, hd_vid, roi, meteor_yn, fireball_yn, mc_class, mc_class_conf, 
                      human_confirmed 
                 FROM meteors 
                WHERE human_confirmed = -1 
                   OR deleted = 1
      """
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      dds = {}

      for row in rows:
         sd_vid, hd_vid, roi, meteor_yn, fireball_yn, mc_class, mc_class_conf, human_confirmed = row
        

         root_fn = sd_vid.replace(".mp4", "")
         hd_root_fn = hd_vid.replace(".mp4", "")
         date = root_fn[0:10]
         nm_dir = "/mnt/ams2/non_meteors_confirmed/" + date + "/" 
         m_dir = "/mnt/ams2/meteors/" + date + "/" 
         if os.path.exists(nm_dir) is False:
            os.makedirs(nm_dir)

         if False:
            mf, msf, nmf, nmcf = self.check_file_location(root_fn)
            if len(mf) > 0 or len(msf) > 0 or len(nmf) > 0:
               print("Need to move files!", root_fn) 
            elif (len(mf) == 0 and len(msf) == 0 and len(nmf) == 0): 
               print("All Files moved!") 
            elif (len(nmcf) == 0):
               print("All Files moved!") 
            else :
               print("No files found.") 

            mf, msf, nmf, nmcf = self.check_file_location(hd_root_fn)
            if len(mf) > 0 or len(msf) > 0 or len(nmf) > 0:
               print("Need to move HD files!", hd_root_fn) 
            elif (len(mf) == 0 and len(msf) == 0 and len(nmf) == 0): 
               print("All HD Files moved!") 
            elif (len(nmcf) == 0):
               print("All Files moved!") 
            else :
               print("No files found.") 
         cmd = "mv " + m_dir + root_fn + "* " + nm_dir
         print(cmd)
         os.system(cmd)
         cmd = "mv " + m_dir + hd_root_fn + "* " + nm_dir
         print(cmd)
         os.system(cmd)

         if True: 
            isql = """INSERT OR REPLACE INTO non_meteors_confirmed (sd_vid, hd_vid, roi, meteor_yn, fireball_yn, multi_class, 
                                                               multi_class_conf, human_confirmed, last_updated)
                                                       VALUES (?,?,?,?, ?, ?, ?, ?, ?)"""
            ivals = [ sd_vid, hd_vid, roi, meteor_yn, fireball_yn, mc_class, mc_class_conf, human_confirmed, time.time()]
            print(isql)
            print(ivals)
            try:
               self.cur.execute(isql, ivals)
            except:
               print("sql issue")

         if  True: 
            isql = """INSERT OR REPLACE INTO deleted_meteors(sd_vid, hd_vid)
                                                       VALUES (?,?)"""
            ivals = [ sd_vid, hd_vid]
            print(isql)
            print(ivals)
            self.cur.execute(isql, ivals)

         if  True: 

            dsql = "DELETE FROM meteors WHERE sd_vid = ?"
            dvals = [sd_vid]
            self.cur.execute(dsql, dvals)
            print(dsql, dvals)
         self.con.commit()



   def load_meteor_into_db(self, root_fn):

      date = root_fn[0:10]

      mdir = "/mnt/ams2/meteors/{}/".format(date)
      mfile = mdir + root_fn + ".json"

      if os.path.exists(mfile) is False:
         return(False, "no mfile: "+ mfile) 
      else:
         # each iter is 1 meteor json file getting loaded into the SQL.
         # break out into a function?
         if mfile in loaded_meteors :
            if loaded_meteors[mfile] == 1:
               foo = 1
               return 
         mdir = mfile[0:10]
         el = mfile.split("_")
         mjf = self.meteor_dir + mdir + "/" + mfile.replace(".mp4", ".json")
         mjrf = self.meteor_dir + mdir + "/" + mfile.replace(".mp4", "-reduced.json")
         start_time = None
         if os.path.exists(mjf) is True:
            try:
               mj = load_json_file(mjf)
            except:
               errors[mjf] = "couldn't open json file"
               return 

         mfd = ""
         if os.path.exists(mjrf) is True:
            try:
               mjr = load_json_file(mjrf)
            except:
               mjr = None
            if mjr is not None:
               if "meteor_frame_data" in mjr :
                  if len(mjr['meteor_frame_data']) > 0:
                     mfd = mjr['meteor_frame_data']
                     start_time = mfd[0][0]
            reduced = 1
         else:
            mjr = None
            reduced = 0

         if start_time is None:
            start_time = self.starttime_from_file(mfile)
            start_time = start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
         if "sd_video_file" not in mj:
            return 
         sd_vid = mj['sd_video_file'].split("/")[-1]
         hd_vid = ""
         if "hd_trim"  in mj:
            if mj['hd_trim'] is not None:
               if isinstance(mj['hd_trim'], str) is True:
                  hd_vid = mj['hd_trim'].split("/")[-1]

         if 'multi_station_event' in mj:
            mse = 1
            if "event_id" in mj['multi_station_event']:
               event_id = mj['multi_station_event']['event_id']
            else:
               event_id = 0
               mse = 0
         else:
            mse = 0
            event_id = 0

         if "hc" in mj :
            human_confirmed = 1
         else:
            human_confirmed = 0



         if "user_mods" in mj :
            if len(mj['user_mods'].keys()) > 0:
               human_confirmed = 1
               user_mods = mj['user_mods']
            else:
               user_mods = ""
         else:
            user_mods = ""
         ang_vel = 0
         if "best_meteor" in mj:
            if "report" in mj['best_meteor']:
               if "ang_vel" in mj['best_meteor']['report']:
                  ang_vel =  mj['best_meteor']['report']['ang_vel']

         if mjr is not None:
            if "meteor_frame_data" in mjr:
               mfd = mjr['meteor_frame_data']

         calib = ""
         if "cp" in mj:
            cp = mj['cp']
            if cp is not None:
               calib = [cp['ra_center'], cp['dec_center'], cp['center_az'], cp['center_el'], cp['position_angle'], cp['pixscale'], float(len(cp['cat_image_stars'])), float(cp['total_res_px'])]
               mj['calib'] = calib

         if "calib" in mj:
            calib = mj['calib']
         if "sync_status" in mj:
            sync_status = json.dumps(mj['sync_status'])
         else:
            sync_status = ""

         if mfd != "":
            duration = len(mfd) / 25
         else:
            duration = "0"

         hd_roi = ""
         if "hd_roi" in mj:
            hd_roi = mj['hd_roi']
         if mjr is not None:
            if "meteor_frame_data" in mjr:
               x1,y1,x2,y2 = mfd_roi(mfd)
               mj['roi'] = [x1,y1,x2,y2]
               mj['hd_roi'] = [x1,y1,x2,y2]
               hd_roi = [x1,y1,x2,y2]


         ext = el[-1]
         camera_id = ext.split("-")[0]

         #self.verify_media(self.station_id, mfile.replace(".mp4", ""))

         in_data = {}
         in_data['station_id'] = self.station_id
         in_data['camera_id'] = camera_id
         in_data['root_fn'] = mfile.replace(".mp4", "")
         in_data['sd_vid'] = sd_vid
         in_data['hd_vid'] = hd_vid
         in_data['start_datetime'] = start_time
         in_data['meteor_yn'] = ""
         in_data['meteor_yn_conf'] = ""
         in_data['human_confirmed'] = human_confirmed
         in_data['reduced'] = reduced
         in_data['multi_station'] = mse
         in_data['event_id'] = event_id
         in_data['ang_velocity'] = float(ang_vel)
         in_data['duration'] = float(duration)
         if hd_roi != "":
            in_data['roi'] = json.dumps(hd_roi)
         in_data['sync_status'] = sync_status
         in_data['calib'] = json.dumps(calib)
         in_data['mfd'] = json.dumps(mfd)
         in_data['user_mods'] = json.dumps(user_mods)
         if mfile in loaded_meteors:
            del (in_data['human_confirmed'])
            self.update_meteor(in_data)
            #print("UPDATE EXISTING")
         else:
            self.dynamic_insert(self.con, self.cur, "meteors", in_data)
            #print("INSERT NEW")
         mj['in_sql'] = 1
         save_json_file(mjf, mj)
         return(True, mjf + " loaded")


   def ai_check(self, roi_file):
      url = "http://localhost:5000/AI/METEOR_ROI/?file={}".format(roi_file)
      print(url)
      if os.path.exists(roi_file) is True:
         print("ROI FILE EXISTS!", roi_file)

         if True:
            url = "http://localhost:5000/AI/METEOR_ROI/?file={}".format(roi_file)
            try:
               response = requests.get(url)
               content = response.content.decode()
               content = json.loads(content)
               print(content)
               return(content)
            except Exception as e:
               print("HTTP ERR:", e)
      else:
         print("NO ROI FILE EXISTS!", roi_file)

   def reactivate_meteor(self, mjf):
      from lib.insert_meteor_json import insert_meteor_json
      mfn = mjf.split("/")[-1]
      mfn = mfn.replace(self.station_id + "_", "")
      mdir = "/mnt/ams2/meteors/" + mfn[0:10] + "/"
      nmdir = "/mnt/ams2/non_meteors/" + mfn[0:10] + "/"
      nmcdir = "/mnt/ams2/non_meteors_confirmed/" + mfn[0:10] + "/"
      if os.path.exists(nmdir + mfn + ".json"):
         hd_root_fn = None
         try:
            mj = load_json_file(nmdir + mfn + ".json")
         except:
            print("FAILED TO LOAD JSON!", nmdir + mfn + ".json")
            return()
         root_fn = mfn.replace(".json", "")
         if "hd_trim" in mj:
            if mj['hd_trim'] != 0 and mj['hd_trim'] is not None:
               hd_root_fn = mj['hd_trim'].split("/")[-1].replace(".mp4", "")
               print("HD:", hd_root_fn,mj['hd_trim'])
            else:
               print("NO HD")

         else:
            print("NO HD")
            print("WILDS:", root_fn )

         print("WILDS:", root_fn, hd_root_fn)
         #move these from the nm dir to the meteor dir
         cmd = "mv " + nmdir + root_fn + "* " + mdir 
         print(cmd)
         os.system(cmd)
         if hd_root_fn is not None:
            cmd = "mv " + nmdir + hd_root_fn + "* " + mdir 
            print(cmd)
            os.system(cmd)

         if "/" in root_fn:
            root_fn = root_fn.split("/")[-1]
         insert_meteor_json(root_fn, self.con, self.cur )
      else:
         print("NO JS:", nmdir + mfn + ".json")




   def fix_non_meteors(self):
      # still need to ? add ai string to the json

      # fix up / org non meteors
      ai_data_file = "/mnt/ams2/non_meteors/NM_AI_DATA.info"
      if os.path.exists(ai_data_file) is True:
         ai_data = load_json_file(ai_data_file)
      else:
         ai_data = {}
      data_file = "/mnt/ams2/non_meteors/nm.info"
      cmd = "cd /mnt/ams2/non_meteors/; find . |grep json |grep -v redu | sort -r > " + data_file
      print(cmd)
      sz, td = get_file_info(data_file)
      if td > 60 or td == 0 or os.path.exists(data_file) is False or True:
         print("REMAKE NON METEOR INDEX:", td, data_file)
         os.system(cmd)
         time.sleep(1)
      print("OPEN", data_file)
      fp = open(data_file)
      ai_files = {}
      for line in fp:
         line = line.replace("\n", "")
         el = line.split("/")
         if len(el) > 2:

            day = el[1]
            mfile = el[2]
            mdir = "/mnt/ams2/meteors/" + day + "/" 
            nmdir = "/mnt/ams2/non_meteors/" + day + "/" 
            msdir = "/mnt/ams2/METEOR_SCAN/" + day + "/" 
            red_file = nmdir + mfile.replace(".json", "-reduced.json")
            roi_file = msdir + self.station_id + "_" + mfile.replace(".json", "-ROI.jpg")


            if os.path.exists(roi_file) is True:
               roi_img = cv2.imread(roi_file)
            else:
               print("NO ROI FOUND:", roi_file)
               roi_img = None

            if roi_img is not None:
               if roi_img.shape[0] != roi_img.shape[1]:
                  print("ROI IMG SHAPE IS NOT EQUAL?", roi_img.shape)
                  roi_img = None

            if os.path.exists(red_file) is True and roi_img is None:
               fo = 1
               #print(day, mfile, red_file)
               print("REMAKE ROI IMAGE!")
               roi_img = self.make_roi_from_mfd(red_file, roi_file)


            if os.path.exists(red_file) is False and roi_img is None:
               print( red_file, roi_file)
               continue

            if roi_img is not None:
               root_fn = roi_file.split("/")[-1].replace("-ROI.jpg", "") 
               roi = [0,0,0,0]
               if root_fn in ai_data:
                  resp = ai_data[root_fn]
               else:
                  resp = self.ai_check(roi_file)
               if resp is not None:
                  if "ai_saved" not in resp:
                     resp['ai_saved'] = 1
                     mj = load_json_file(nmdir + mfile)
                     mj['ai'] = resp
                     save_json_file(nmdir + mfile, mj)
                     print("SAVED AI INTO JSON", mfile)

               if resp is not None:
                  meteor_yes_no = max([resp['meteor_yn'], resp['fireball_yn']]) 
                  if resp['mc_class_conf'] > meteor_yes_no:
                     final_class = resp['mc_class'] 
                     final_conf = resp['mc_class_conf'] 
                  else:
                     final_class = "meteor"
                     final_conf = meteor_yes_no
                  resp['final_class'] = final_class
                  resp['final_conf'] = final_conf
                  print("   METEOR/FIREBALL YN:", meteor_yes_no)
                  print("   MULTI CLASS:", resp['mc_class'], resp['mc_class_conf'])
               else:
                  print("AI FAILED!")
                  final_class = "" 
                  meteor_yn = -1 
                  fireball_yn = -1 
                  final_conf = -1 
               if final_class is not None and final_class != "": 
                  desc = final_class + " " + str(final_conf)[0:4]
               else:
                  desc = "NO AI"
               ai_data[root_fn] = resp
               if "meteor" in desc or (meteor_yes_no > 50 and "orion" in desc) or (meteor_yes_no > 50 and "star" in desc) :
                  self.reactivate_meteor(root_fn)
               if "meteor" in desc:
                  detect_color = [0,255,0]
               else:
                  detect_color = [0,0,255]
               if self.SHOW == 1 and "meteor" in desc:
                  cv2.putText(roi_img, desc,  (10, 20), cv2.FONT_HERSHEY_SIMPLEX, .6, detect_color, 1)
                  cv2.imshow('pepe', roi_img)
                  cv2.waitKey(30)
            else:
               print("NO ROI IMG EXISTS OR IMG IS NONE", roi_file, mfile)
      save_json_file(ai_data_file, ai_data)

      print("saved:", ai_data_file)

   def make_roi_from_mfd(self, red_file, roi_file):
      if self.SHOW == 1:
         cv2.namedWindow('pepe')
         cv2.resizeWindow("pepe", 1920, 1080)
      rdata = load_json_file(red_file)
      stack_file = red_file.replace("-reduced.json", "-stacked.jpg")
      img = cv2.imread(stack_file)
      img = cv2.resize(img, (1920,1080))
      if "meteor_frame_data" in rdata:
         mfd = rdata['meteor_frame_data']
      else:
         mfd = None
      if mfd is not None and len(mfd) > 1:
         x1,y1,x2,y2 = mfd_roi(mfd)
         roi_img = img[y1:y2,x1:x2]
         cv2.imwrite(roi_file, roi_img)

      print(stack_file)
      print(img.shape)
      if self.SHOW == 1:
         #cv2.rectangle(img, (x1,y1), (x2,y2), (255, 255, 255), 1)
         #cv2.imshow('pepe', img)
         #cv2.resizeWindow("pepe", 1920, 1080)
         cv2.waitKey(30)
         cv2.imshow('pepe', roi_img)
         cv2.waitKey(30)
      return(roi_img)

