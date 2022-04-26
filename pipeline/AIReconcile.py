"""

AI Script to reconcile meteor & non meteor files between file system, SQL DB and AWS. 

"""

import sqlite3
import os
import sys
from lib.PipeUtil import load_json_file, save_json_file
from lib.load_meteor import load_meteor

json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']

obs_ids_file = "/mnt/ams2/meteors/" + station_id + "_OBS_IDS.json"
db_file = station_id + "_ALLSKY.db"
con = sqlite3.connect(db_file)
cur = con.cursor()

obs_ids = load_json_file(obs_ids_file)
obs_dict = {}
for x,y in obs_ids:
   obs_dict[x] = y

sql = """
         SELECT root_fn, hd_vid, meteor_yn_conf, fireball_yn_conf, mc_class, mc_class_conf, human_confirmed, multi_station, ang_velocity, duration, peak_intensity 
           FROM meteors
       ORDER BY root_fn DESC
      """
cur.execute(sql)
rows = cur.fetchall()
sql_meteors = {}
my_data = []
print("LEN:", len(rows))
sql_deletes = {}
for row in rows:
   root_fn, hd_vid, meteor_yn_conf, fireball_yn_conf, mc_class, mc_class_conf, human_confirmed, multi_station, ang_velocity, duration, peak_intensity = row
   oid = station_id + "_" + root_fn + ".json" 
   if oid in obs_dict:
      met_live = True
   else:
      met_live = False 
      sql_deletes[root_fn] = True
   sql_meteors[oid] = [root_fn, hd_vid, meteor_yn_conf, fireball_yn_conf, mc_class, mc_class_conf, human_confirmed, multi_station, ang_velocity, duration, peak_intensity, met_live]
   print(sql_meteors[oid])

sql_inserts = {}
for oid in obs_dict:
   if oid not in sql_meteors:
      sql_inserts[oid] = True
      print("Missing from SQL DB (needs loading!):", oid)

print("TOTAL OBS IDS:", len(obs_dict.keys()))
print("TOTAL SQL IDS:", len(sql_meteors.keys()))
print("TOTAL SQL DELETES NEEDED:", len(sql_deletes.keys()))
print("TOTAL SQL INSERTS NEEDED:", len(sql_inserts.keys()))
print("TOTAL SQL IDS:", len(sql_meteors.keys()) - len(sql_deletes.keys()) + len(sql_inserts.keys()))

for oid in sql_inserts:
   st = oid.split("_")[0]
   mfile = oid.replace(st + "_", "")
   print("insert oid", oid)
   mdata,errors = load_meteor(station_id, mfile)
