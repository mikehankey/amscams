import sqlite3
import os
from lib.PipeUtil import load_json_file
import sys
import glob

def connect_database():
   con = sqlite3.connect("AMS1_AllSky.db")
   con.row_factory = sqlite3.Row
   return(con)


def get_mfiles(mdir):
   temp = glob.glob(mdir + "/*.json")
   mfiles = []
   for json_file in temp:
      if "import" not in json_file and "report" not in json_file and "reduced" not in json_file and "calparams" not in json_file and "manual" not in json_file and "starmerge" not in json_file and "master" not in json_file:
         vfn = json_file.split("/")[-1].replace(".json", ".mp4")
         mfiles.append(vfn)
   return(mfiles)

def insert_meteors_for_day(con, cur, station_id, date):
   ai_data_file = "/mnt/ams2/meteors/" + date + "/" + station_id + "_" + date + "_AI_SCAN.info"
   mdir = "/mnt/ams2/meteors/" + date + "/"
   mfiles = get_mfiles(mdir)
   json_conf = load_json_file("../conf/as6.json")
   station_id = json_conf['site']['ams_id']
   root_files = {}

   ai_data = load_json_file(ai_data_file)
   for key in ai_data:
      if "ROI.jpg" in key:
         root_key = key.replace("-ROI.jpg", "")
      if ".mp4" in key:
         root_key = key.replace(".mp4", "")
      if ".json" in key:
         root_key = key.replace(".json", "")
      if "-stacked.jpg" in key:
         root_key = key.replace("-stacked.jpg", "")
      if "AMS" not in root_key:
         root_key = station_id + "_" + root_key

      el = root_key.split("_")
      extra = el[-1].split("-")
      cam_id = extra[0]
      print("ST/CAM/ROOT:", station_id, cam_id, root_key)
      root_files[root_key] = {}
      root_files[root_key]['station_id'] = station_id
      root_files[root_key]['cam_id'] = cam_id
      root_files[root_key]['meteor_fn'] = root_key

     
      mjf = mdir + key.replace(".mp4",  ".json")
      mjrf = mdir + key.replace(".mp4", "-reduced.json")
      if os.path.exists(mjf) is True:
         mj = load_json_file(mjf)
      else:
         print("NO MJF?!", mjf)
      if os.path.exists(mjrf) is True:
         mjr = load_json_file(mjrf)
         reduced = True
      else:
         print("not found:", mjrf)
         mjr = None
         reduced = False 

      if mjr is not None:
         if "meteor_frame_data" in mjr:
            mfd = mjr['meteor_frame_data']
         else:
            mfd = None
      else:
         mfd = None

      root_files[root_key]['sd_vid'] = mj['sd_video_file'].split("/")[-1]
      try:
         root_files[root_key]['hd_vid'] = mj['hd_trim'].split("/")[-1]
      except:
         root_files[root_key]['hd_vid'] = None
      if mfd is not None:
         if len(mfd) > 0:
            root_files[root_key]['start_datetime'] = mfd[0][0]
         else:
            root_files[root_key]['start_datetime'] = 0
      else:
         root_files[root_key]['start_datetime'] = 0
      root_files[root_key]['meteor_yn_final'] = 0
      root_files[root_key]['meteor_yn_final_conf'] = 0
      root_files[root_key]['meteor_yn'] = 0
      root_files[root_key]['meteor_yn_conf'] = 0
      root_files[root_key]['fireball_yn'] = 0
      root_files[root_key]['fireball_yn_conf'] = 0
      root_files[root_key]['multi_class'] = 0
      root_files[root_key]['multi_class_conf'] = 0
      root_files[root_key]['reduced'] = reduced
      root_files[root_key]['multi_station'] = 0
      root_files[root_key]['event_id'] = 0
      root_files[root_key]['ang_velocity'] = 0
      root_files[root_key]['duration'] = 0
      root_files[root_key]['roi'] = 0
      root_files[root_key]['sync_status'] = 0
      root_files[root_key]['calib'] = 0
      root_files[root_key]['mfd'] = 0
      rd = root_files[root_key]
      row_val = (rd['station_id'], rd['cam_id'],rd['meteor_fn'],rd['sd_vid'],rd['hd_vid'],rd['start_datetime'],rd['meteor_yn_final'], rd['meteor_yn_final_conf'], rd['meteor_yn'],rd['meteor_yn_conf'],rd['fireball_yn'],rd['fireball_yn_conf'],rd['multi_class'],rd['multi_class_conf'],rd['reduced'],rd['multi_station'],rd['event_id'],rd['ang_velocity'],rd['duration'],rd['roi'],rd['sync_status'],rd['calib'],rd['mfd'])

      print("INSERT OR REPLACE METEORS ROW ", row_val)
   exit()
   for mfile in mfiles:
      ai_file = station_id + "_" + mfile.replace(".mp4", "-ROI.jpg")
      if ai_file not in ai_data:
         print("INSERT MISSING MFILE (NOT REDUCED?)", mfile, ai_file)

   

def insert_meteor(con, cur, in_data):
   sql = '''
        INSERT OR REPLACE INTO meteors(station_id,camera_id,meteor_fn, sd_vid,hd_vid, start_datetime, meteor_yn, meteor_yn_conf, fireball_yn, fireball_yn_conf, multi_class, multi_class_conf, reduced, multi_station, event_id, ang_velocity, duration, roi, sync_status, calib)
        VALUES(?,?,?, ?,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
     '''
   cur.execute(sql, in_data)
   con.commit()
   return(cur.lastrowid)

def create_tables(cur):

   # Create table
   cur.execute('''
     CREATE TABLE station_conf (
        station_id TEXT, 
        lat REAL, 
        lon REAL, 
        alt REAL, 
        observatory_name TEXT, 
        operator_name TEXT, 
        operator_address TEXT, 
        operator_city TEXT, 
        operator_state TEXT, 
        operator_country TEXT, 
        operator_email TEXT, 
        operator_mobile TEXT, 
        photo_credit TEXT, 
        cameras TEXT, 
        pin_code TEXT, 
        api_key TEXT)
        ''')

   cur.execute('''
      CREATE TABLE meteors (
         meteor_fn TEXT PRIMARY KEY, 
         hd_trim TEXT, 
         start_datetime DATE, 
         roi TEXT, 
         reduced INT, 
         syncd INT, 
         human_confirmed INT, 
         human_label TEXT, 
         meteor_yn INT, 
         meteor_yn_conf REAL, 
         fireball_yn INT, 
         fireball_yn_conf REAL, 
         multi_class TEXT, 
         multi_class_conf REAL)
         ''')


   #cur.execute('''CREATE TABLE roi_sample 
   #            (roi_fn, main_class, sub_class, human_label, meteor_yn, fireball_yn, multi_class, confidence)''')

   #cur.execute('''CREATE TABLE non_meteors 
   #            (roi_fn, main_class, sub_class, human_label, meteor_yn, fireball_yn, multi_class)''')



con = connect_database()
cur = con.cursor()
#create_tables(cur)
date = sys.argv[1]
station_id = "AMS1"
insert_meteors_for_day(con, cur, station_id, date)

