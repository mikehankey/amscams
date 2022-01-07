import sqlite3
import numpy as np
import cv2
import json
import datetime as dt
import os
from lib.PipeUtil import load_json_file, convert_filename_to_date_cam, get_trim_num, mfd_roi, save_json_file, bound_cnt
import sys
import glob
from Classes.ASAI import AllSkyAI 

class AllSkyDB():

   def __init__(self):
      print("ASAI DB")
      if os.path.exists("windows.json") is True:
         self.win_config = load_json_file("windows.json")
         self.meteor_dir = self.win_config['meteor_dir'] 
      else:
         self.meteor_dir = "/mnt/ams2/meteors/"
      self.json_conf = load_json_file("../conf/as6.json")
      self.station_id = self.json_conf['site']['ams_id']
      self.con = self.connect_database(self.station_id)
      self.cur = self.con.cursor()
      self.ASAI = AllSkyAI()
      self.ASAI.load_all_models()
      self.check_update_status()

   def check_update_status(self):
      print("Check update scan status...")
      # check to make sure the ml_samples table has the lastest patch
      if os.path.exists("../conf/sqlite.json") is True:
         sql_conf = load_json_file("../conf/sqlite.json")
      else:
         sql_conf = {}
         sql_conf['updates'] = {}

      # Do alters / db updates / table adds
      if "ml_samples_alter" not in sql_conf['updates']:
         try:
            sql = "ALTER TABLE ml_samples ADD COLUMN meteor_or_plane real"
            self.cur.execute(sql)
            sql = "ALTER TABLE ml_samples ADD COLUMN meteor_or_bird real"
            self.cur.execute(sql)
            sql = "ALTER TABLE ml_samples ADD COLUMN meteor_or_firefly real"
            self.cur.execute(sql)
            sql = "ALTER TABLE ml_samples ADD COLUMN scan_version real"
            self.cur.execute(sql)
         except:
            print("ml_samples Table already altered")
            sql_conf['updates']['ml_samples_alter'] = {}

      # Check if summary table exists, if not make it and populate it. 
      if "station_summary_table" not in sql_conf['updates']:
         try:
            sql = """
               CREATE TABLE "station_summary" (
	       "station_id"	TEXT,
	       "total_meteor_obs"	INTEGER,
	       "total_fireball_obs"	INTEGER,
	       "total_meteors_human_confirmed"	INTEGER,
	       "first_day_scanned"	TEXT,
	       "last_day_scanned"	TEXT,
	       "total_days_scanned"	INTEGER,
	       "ai_meteor_yes"	INTEGER,
	       "ai_meteor_no"	INTEGER,
	       "ai_meteor_samples"	INTEGER,
	       "ai_non_meteor_samples"	INTEGER
               );
            """
            self.cur.execute(sql)
         except:
            print("station_summary Table already altered")
            sql_conf['updates']['station_summary_table'] = {}
         save_json_file("../conf/sqlite.json", sql_conf) 

      self.purge_deleted_meteors()
      print("END PURGE:")
      sql = "SELECT * from station_summary" 
      rows = self.cur.fetchall()


      print("STATION SUMMARY", len(rows))
      update_summary = 0
      if len(rows) == 0:
         update_summary = 1
      if update_summary == 1:
         self.update_summary()

   def purge_deleted_meteors(self):
      # this will check each meteor in the DB. 
      # if it does not exist on the file system it will be removed from the DB
      sql = "SELECT root_fn, roi, mfd from meteors WHERE meteor_yn = '' order by root_fn desc"
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      found = 0
      not_found = 0
      good = 0
      bad = 0
      for row in rows:
         root_file = row[0]
         mfile = "/mnt/ams2/meteors/" + root_file[0:10] + "/" + root_file + ".json"
         if os.path.exists(mfile) is True:
            good += 1
         else:
            bad += 1
            print("NOT FOUND!:", mfile)
      print("GOOD FILES:", good)
      print("BAD FILES:", bad)

   def update_summary(self):
      # This function will just update the stats in the main summary table

      # get total number of METEORS in the systems 
      sql = "SELECT count(*) as ccc from meteors"
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      total_meteor_obs = rows[0][0]

      # get total number of METEORS in the system marked as meteor_yn = 1
      sql = "SELECT count(*) as ccc from meteors WHERE meteor_yn = 1"
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      total_meteor_obs_yes = rows[0][0]

      # get total number of METEORS in the system marked as meteor_yn = 0
      sql = "SELECT count(*) as ccc from meteors WHERE meteor_yn = 0"
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      total_meteor_obs_no = rows[0][0]

      # get total number of METEORS in the system marked as meteor_yn = 0
      sql = "SELECT count(*) as ccc from meteors WHERE meteor_yn = ''"
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


      print("Total Meteor Obs:", total_meteor_obs)
      print("Total Meteor Obs AI Yes:", total_meteor_obs_yes)
      print("Total Meteor Obs AI No:", total_meteor_obs_no)
      print("Total Meteor Obs AI Not Run:", total_meteor_obs_not_run)
      print("Total Meteor Human Confirmed:", total_meteor_human_confirmed)
      print("Total Meteors Reduced:", total_meteor_reduced)

      if True:
         meteor_roots = []
         print("Do a quick update to make sure the old detects just need to be updated...")
         sql = "SELECT root_fn, roi, mfd from meteors WHERE meteor_yn = '' order by root_fn desc"
         self.cur.execute(sql)
         rows = self.cur.fetchall()
         found = 0
         not_found = 0
         for row in rows:
            root = row[0]
            roi = row[1]
            mfd = row[2]
            if isinstance(roi,str) is True and "[" in roi:
               roi = eval(roi)
            else:
               roi = None


            if "AMS" not in root:
               date = root[0:10]
               mdir = "/mnt/ams2/meteors/" + date + "/" 
               msdir = "/mnt/ams2/METEOR_SCAN/" + date + "/" 
               roi_file = msdir + self.station_id + "_" + root + "-ROI.jpg"
               print("ROI FILE:", roi_file)
               if os.path.exists(roi_file) is True:
                  roi_exists = 1
                  roi_img = cv2.imread(roi_file)
                  #print(found, "ROI FILE FOUND!", roi_file)
                  found += 1
                  try:
                     resp = self.ASAI.meteor_yn(None,roi_img)
                  except:
                     resp = None
                  if resp is not None:
                     sql = """ UPDATE meteors 
                        SET meteor_yn = ?,
                            meteor_yn_conf = ?
                        WHERE sd_vid = ? """
                     task = [resp['final_meteor_yn'],resp['final_meteor_yn_conf'],root + ".mp4"]

                     #cur = con.cursor()
                     self.cur.execute(sql, task)
                     print("SQL:", sql)
                     print("TASK:", task)
                     self.con.commit()

                     print("UPDATE", task)
               else:
                  #print(not_found, "ROI FILE NOT FOUND!", roi_file)
                  roi_exists = 0
                  not_found += 1
            else:
               print("ROOT:", root)

            meteor_roots.append(root)
         print(len(meteor_roots) , "loaded")


         #for mr in meteor_roots:
         #   sql = """SELECT roi_fn from ml_samples where root_fn = ? and (meteor_yn_conf > 50 or fireball_yn_conf > 50 or multi_class like "%meteor%") """
         #   bind_vars = [mr]
         #   self.cur.execute(sql, bind_vars)
         #   rows = self.cur.fetchall()
         #   print(mr, len(rows))
        

      

   
   def starttime_from_file(self, filename):
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
               print(rx)
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
         print("ROI:", roi)
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
               print("QUIT!")
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

               print("QUIT!")
               return()
            if key_press == 102:
               i += 1
            if key_press == 97:
               i -= 1

      

   def load_all_meteors(self, selected_day = None):
      print("SDAY:", selected_day)
      if selected_day is None:
         dirs = os.listdir(self.meteor_dir)
      else:
         dirs = [selected_day]
      self.mdirs = []
      self.mfiles = []
      print("DIRS:", dirs)

      for ddd in sorted(dirs,reverse=True):
         if os.path.isdir(self.meteor_dir + ddd):
            self.mdirs.append(self.meteor_dir + ddd + "/")

      for mdir in sorted(self.mdirs):
         mfiles = self.get_mfiles(mdir )
         print(len(mfiles), mdir)
         self.mfiles.extend(mfiles)
 
      print("MFILES:", len(self.mfiles))
      for mfile in sorted(self.mfiles, reverse=True):
         print(mfile.replace(".mp4", ""))
         mdir = mfile[0:10]
         el = mfile.split("_")
         mjf = self.meteor_dir + mdir + "/" + mfile.replace(".mp4", ".json")
         mjrf = self.meteor_dir + mdir + "/" + mfile.replace(".mp4", "-reduced.json")
         start_time = None
         if os.path.exists(mjf) is True:
            try:
               mj = load_json_file(mjf)
            except:
               print("COULD NOT LOAD THE MJF:", mjf)
               continue
         if 'in_sql' in mj:
            print("XXX MJ already loaded into SQL!")
            #continue

         mfd = ""
         if os.path.exists(mjrf) is True:
            mjr = load_json_file(mjrf)
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
            event_id = mj['multi_station_event']['event_id']
         else:
            mse = 0
            event_id = 0

         if "hc" in mj :
            human_confirmed = 1
         else:
            human_confirmed = 0
 
        
         if "user_mods" in mj :
            human_confirmed = 1
            user_mods = mj['user_mods']
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
               x1,y1,x2,y2 = mfd_roi(mjr['meteor_frame_data'])
               mj['hd_roi'] = [x1,y1,x2,y2]
               hd_roi = [x1,y1,x2,y2]

         ext = el[-1]
         camera_id = ext.split("-")[0]
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
         in_data['roi'] = json.dumps(hd_roi)
         in_data['sync_status'] = sync_status
         in_data['calib'] = json.dumps(calib)
         in_data['mfd'] = json.dumps(mfd)
         in_data['user_mods'] = json.dumps(user_mods)
         #print(in_data)
         self.dynamic_insert(self.con, self.cur, "meteors", in_data)
         mj['in_sql'] = 1
         save_json_file(mjf, mj)


   def connect_database(self,station_id):
      con = sqlite3.connect(station_id + "_ALLSKY.db")
      con.row_factory = sqlite3.Row
      return(con)


   def dynamic_select(self, con, cur, table, fields, where):
      cur.execute("SELECT " + fields + "FROM " + table + " WHERE " + where)
      rows = cur.fetchall()
      return(rows)


   def dynamic_insert(self,con, cur, table_name, in_data):
      # Pass in the table name 
      # and a dict of key=value pairs
      # then the dict will be converted to sql and insert or replaced into the table. 
   
      values = []
      fields = []
      sql = "INSERT OR REPLACE INTO " + table_name + " ( "
      vlist = ""
      flist = "" 
      for key in in_data:
         print("KEY IS:", key)
         print("FLIST IS:", flist)
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
      print("SQL", sql)
      print("FIELDS", fields)
      print("VALUES", values)
      print(len(fields))
      print(len(values))
      cur.execute(sql, values)
      con.commit()
      return(cur.lastrowid)


   def insert_ml_sample(self,con, cur, in_data):
      sql = '''
        INSERT OR REPLACE INTO ml_samples(station_id,camera_id,root_fn,roi_fn, meteor_yn_final, meteor_yn_final_conf, main_class, sub_class, meteor_yn, meteor_yn_conf, fireball_yn, fireball_yn_conf, multi_class, multi_class_conf, human_confirmed, human_label, suggest_class, ignore)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
      '''
      print("INSERTED:", in_data)
      cur.execute(sql, in_data)
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
      print("KEY:", key_press) 
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
         print("OLD ROI FILE:", roi_fn)
         print("NEW ROI IMG:", new_roi_img_filename)
         
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
