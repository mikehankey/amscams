"""

Functions for handling meteor deletes across :
   - the original meteor detection dir (/mnt/ams2/meteors/)
   - the meteor archive dir (/mnt/ams2/meteor_archive/STATION/METEORS/Y/M/D/)
   - the LIVE meteor dir (/mnt/ams2/meteor_archive/STATION/LIVE/METEORS/YYYY_MM_DD/
   - the CLOUD meteor archive dir (/mnt/archive.allsky.tv/STATION/METEORS/Y/M/D/)
   - the CLOUD LIVE meteor dir (/mnt/archive.allsky.tv/STATION/LIVE/METEORS/YYYY_MM_DD/

   eventually the meteor archive / LIVE dirs MAY merge into one dir. so there will be less dirs to deal with
   but for now, when we delete a meteor it needs to be deleted from all these places. 

   Meteor deletes will be called from :
      - the host station admin panel (in two different places meteors and archive)
      - cron jobs that execute 'Network Manager' initiated deletes.

"""
from lib.DEFAULTS import *
from lib.PipeUtil import cfe, load_json_file
import glob
import os

def fn_dir (file):
   fn = file.split("/")[-1]
   dir = file.replace(fn, "")
   return(fn, dir)

def delete_all_meteor_files(mf):
   find_meteor_files(mf)

def find_meteor_files(mf):
   archive_file = None
   hdrf = None
   """ Find all files associated with this meteor. """ 
   rf = mf.split("/")[-1]
   el = rf.split(".")
   rf = el[0]

   day = rf[0:10] 
   year, mon, dom = day.split("_")

   meteor_json = "/mnt/ams2/meteors/" + day + "/" + rf + ".json"
   meteor_arc_json = "/mnt/ams2/meteor_archive/" + STATION_ID + "/METEOR/" + year + "/" + mon + "/" + dom + "/" + rf + ".json"
   if cfe(meteor_arc_json) == 1:
      aj = load_json_file(meteor_arc_json)

   if cfe(meteor_json) == 1:
      mj = load_json_file(meteor_json)
      if 'hd_trim' in mj:
         hd_trim = mj['hd_trim']
         hdrf = hd_trim.split("/")[-1]
      if 'archive_file' in mj:
         archive_file = mj['archive_file']
   else:
      print("No meteor json!", meteor_json)
      return()
   arc_fn, arc_dir = fn_dir(archive_file)
   arc_fn = arc_fn.replace(".json", "")
   arc_fn = arc_fn.replace(".mp4", "")

   hdrf = hdrf.replace(".mp4","")

   LIVE_DIR_WILD = "/mnt/ams2/meteor_archive/" + STATION_ID + "/LIVE/METEORS/" + day + "/" + hdrf + "*"
   METEOR_DIR_WILD = "/mnt/ams2/meteors/" + day + "/" + rf + "*"
   METEOR_DIR_HD_WILD = "/mnt/ams2/meteors/" + day + "/" + hdrf + "*"
   ARC_DIR_WILD = arc_dir + arc_fn + "*"
   CLOUD_DIR_WILD = ARC_DIR_WILD.replace("ams2/meteor_archive", "archive.allsky.tv")

   DEL_DIR = "/mnt/ams2/ADMIN_DELETED/"
   if cfe(DEL_DIR, 1) == 0:
      os.makedirs(DEL_DIR)
   cmds = []
   cmds.append("mv " + LIVE_DIR_WILD + " /mnt/ams2/ADMIN_DELETED/")
   cmds.append("mv " + METEOR_DIR_WILD + " /mnt/ams2/ADMIN_DELETED/")
   cmds.append("mv " + METEOR_DIR_HD_WILD + " /mnt/ams2/ADMIN_DELETED/")
   cmds.append("mv " + ARC_DIR_WILD + " /mnt/ams2/ADMIN_DELETED/")
   cmds.append("rm " + CLOUD_DIR_WILD + " &")

   for cmd in cmds:
      print(cmd)
      #os.system(cmd)

    
