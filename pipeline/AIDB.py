import sqlite3
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

   ai_data = load_json_file(ai_data_file)
   for key in ai_data:
      print("INSERT OR REPLACE AI FILE", key, ai_data[key])

   for mfile in mfiles:
      ai_file = station_id + "_" + mfile.replace(".mp4", "-ROI.jpg")
      if ai_file not in ai_data:
         print("INSERT MISSING MFILE (NOT REDUCED?)", mfile, ai_file)

   

def insert_meteor(con, cur, in_data):
   sql = '''
        INSERT OR REPLACE INTO meteors(meteor_fn, hd_trim, start_datetime, reduced, syncd, meteor_yn, meteor_yn_conf, fireball_yn, fireball_yn_conf, multi_class, multi_class_conf)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)
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

