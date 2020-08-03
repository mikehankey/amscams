'''

functions to sync the meteor archive with the wasabi dir

'''

import glob
import os
from lib.DEFAULTS import *
from lib.PipeUtil import cfe, load_json_file, save_json_file



def sync_day(inday):
   year, month, day = inday.split("_")
   ddd = inday.split("_")
   this_arc_dir = METEOR_ARC_DIR + year + "/" + month + "/" + day + "/"

   # load the sync index for this day
   si_file = this_arc_dir + "sync.json"
   if cfe(si_file) == 1:
      sync_index = load_json_file (si_file)
   else:
      sync_index = {}
   
   # get local archive files for this day
   arc_files = glob.glob(this_arc_dir + "*")
   for af in arc_files:
      sf = af.split("/")[-1]
      if sf not in sync_index:
         sync_index[sf] = {}
         sync_index[sf]['arc_file'] = af
         cf = af.replace("ams2/meteor_archive", "archive.allsky.tv")
         sync_index[sf]['cloud_file'] = cf
         sync_index[sf]['status'] = 0


   # get cloud files for this day
   cloud_file = {}
   this_cloud_dir, cloud_meteor_files = get_cloud_meteor_files(inday) 
   if cfe(this_cloud_dir, 1) == 0:
      os.makedirs(this_cloud_dir)
   for cf in cloud_meteor_files:
      sf = cf.split("/")[-1]
      if sf in sync_index:
         sync_index[sf]['status'] = 1
         sync_index[sf]['cloud_file'] = cf 

   for sf in sync_index:
      if sync_index[sf]['status'] == 0:
         arc_file = sync_index[sf]['arc_file']
         cloud_file = sync_index[sf]['cloud_file']
         status = sync_index[sf]['status']
         cmd = "cp " + arc_file + " " + cloud_file
         if "crop" in arc_file and status != 1:
            print(cmd)
            os.system(cmd)
         sync_index[sf]['cloud_file'] = cloud_file
         #sync_index[sf]['status'] = 1
            


   save_json_file(si_file, sync_index)
   print("saved:", si_file)
   exit()

def get_cloud_meteor_files(inday):
   year, month, day = inday.split("_")
   this_cloud_dir = CLOUD_METEOR_DIR + year + "/" + month + "/" + day + "/" 
   cloud_meteor_files = glob.glob(this_cloud_dir + "*")
   print(this_cloud_dir)
   print(cloud_meteor_files)
   return(this_cloud_dir, cloud_meteor_files)
