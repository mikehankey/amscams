from Classes.SyncAWS import SyncAWS 
from lib.PipeUtil import load_json_file, cfe, save_json_file
import sys
import glob 
json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']
api_key = json_conf['site']['api_key']

SAWS = SyncAWS(station_id, api_key)
amf = SAWS.AWS_DIR + station_id + "_ALL_METEORS.json"
amd = SAWS.AWS_DIR + station_id + "_ALL_METEOR_DIRS.json"

def index_local_meteors(): 
   SAWS.get_mdirs()
   for mdir in sorted(SAWS.mdirs, reverse=True):
      print("Getting ", mdir, len(SAWS.mfiles))
      SAWS.get_mfiles(mdir)
   save_json_file(amd, SAWS.mdirs)
   save_json_file(amf, SAWS.mfiles)

def sync_batch(wild=None):
   SAWS.sync_meteor_wild(wild)

def sync_file(sd_vid):
   SAWS.sync_meteor(sd_vid) 
   SAWS.sync_meteor_media([sd_vid]) 
   day = sd_vid[0:10]
   SAWS.upload_cloud_media(day, [sd_vid])
   SAWS.sync_meteor(sd_vid) 


def sync_day_data_only(day):
   SAWS.sync_meteor_day_data_only(day)

def sync_day(day):
   mdir = "/mnt/ams2/meteors/" + day + "/"
   SAWS.sync_meteor_day(day)
   exit()
   # SYNC MEDIA FUNCS
   SAWS.delete_aws_meteors(day)
   SAWS.delete_cloud_media(day)
   SAWS.get_mfiles(mdir)
   SAWS.sync_meteor_media(SAWS.mfiles)
   SAWS.upload_cloud_media(day, SAWS.mfiles)
   for sd_vid in SAWS.mfiles:
      SAWS.sync_meteor(sd_vid)

def sync_month(wild):
   print("/mnt/ams2/meteors/" + "*")
   temp = glob.glob("/mnt/ams2/meteors/" + wild + "*")
   for mdir in sorted(temp,reverse=True):
      print("md", mdir)
      if cfe(mdir, 1) == 1:
         day = mdir.split("/")[-1]
         print("Day:", day)
         sync_day(day)



# MAIN! 
if len(sys.argv) == 1:
   print(""" Enter a command:
      * Sync File 
      python3 AWS.py sf meteor_fn
      * Sync Day
      python3 AWS.py sd YYYY_MM_DD
      * Sync Month
      python3 AWS.py sm YYYY_MM
      * Sync Year
      python3 AWS.py sy YYYY
      * Sync All
      python3 AWS.py sy YYYY
      * Re-index local meteor files
      python3 AWS.py index 
   """)
else:
   if sys.argv[1] == "sb":
      sync_batch(sys.argv[2]) 
   if sys.argv[1] == "sd":
      sync_day(sys.argv[2]) 
   if sys.argv[1] == "sm":
      sync_month(sys.argv[2]) 
   if sys.argv[1] == "sf":
      sync_file(sys.argv[2]) 
   if sys.argv[1] == "sd_data":
      sync_day_data_only(sys.argv[2]) 
