import sqlite3
import json
from lib.PipeUtil import load_json_file, save_json_file
import os
import glob
import time

def check_update_non_meteor_table(con,cur):
   latest = False
   for row in cur.execute("PRAGMA table_info('non_meteors_confirmed')").fetchall():
      print(row[1])
      if row[1] == 'multi_class_conf':
         latest = True
   if latest is False:
      print("Make non_meteors_confirmed table.")
      create_table = """
       CREATE TABLE IF NOT EXISTS "non_meteors_confirmed" (
        "sd_vid"     INTEGER,
        "hd_vid"     INTEGER,
        "roi"   TEXT,
        "meteor_yn"        REAL,
        "fireball_yn"       REAL,
        "multi_class"   TEXT,
        "multi_class_conf"      REAL,
        "human_confirmed"   INTEGER,
        "human_label"   TEXT,
        "last_updated"   INTEGER
       );
      """
      cur.execute(create_table)
      con.commit()
      
def purge():

   # move confirmed non-meteors still in the meteor dir to the non-meteor dir
   # remove the meteors database record
   # insert non-meteor record in non_meteors table
   sql = """
            SELECT sd_vid, hd_vid, roi, meteor_yn_conf, fireball_yn_conf, mc_class, mc_class_conf, human_confirmed 
              FROM meteors
             WHERE human_confirmed = -1
          ORDER BY sd_vid desc
   """
   cur.execute(sql)
   rows = cur.fetchall()
   dds = {}
   rc = 0
   for row in rows:
      if rc > 10:
         exit()
      rc += 1
      sd_vid, hd_vid, roi, meteor_yn_conf, fireball_yn_conf, mc_class, mc_class_conf, human_confirmed = row
      mdir = "/mnt/ams2/meteors/" + sd_vid[0:10] + "/"
      nmdir = "/mnt/ams2/non_meteors_confirmed/" + sd_vid[0:10] + "/"
      if nmdir not in dds:
         if os.path.exists(nmdir) is False:
            os.makedirs(nmdir)
            dds[nmdir] = 1
      gfiles_sd = glob.glob(mdir + sd_vid.replace(".mp4", "*"))
      for gf in gfiles_sd:
         cmd = "mv " + gf + " " + nmdir
         print(cmd)
         os.system(cmd)
      gfiles_hd = glob.glob(mdir + hd_vid.replace(".mp4", "*"))
      for gf in gfiles_hd:
         cmd = "mv " + gf + " " + nmdir
         print(cmd)
         os.system(cmd)
      sql = """
         INSERT OR REPLACE INTO non_meteors_confirmed 
                                (sd_vid, hd_vid, roi, meteor_yn, fireball_yn, 
                                multi_class, multi_class_conf, human_confirmed, last_updated)
                         VALUES (?,?,?,?,?,?,?,?,?)
      """
      last_updated = time.time()
      vals = (sd_vid, hd_vid, roi, meteor_yn_conf, fireball_yn_conf, mc_class, mc_class_conf, human_confirmed, last_updated)
      print(sql, vals)
      cur.execute(sql, vals)

      sql = """
         DELETE FROM meteors where sd_vid = ?
      """
      vals = [sd_vid]
      print(sql, vals)
      cur.execute(sql, vals)

      con.commit()

      #exit()
if __name__ == "__main__":
   json_conf = load_json_file("../conf/as6.json")
   con = sqlite3.connect(json_conf['site']['ams_id']+ "_ALLSKY.db")
   con.row_factory = sqlite3.Row
   cur = con.cursor()
   check_update_non_meteor_table(con,cur)
   purge()
