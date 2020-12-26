'''

functions to sync the meteor archive with the wasabi dir

'''
import cv2
import glob
import os
from lib.DEFAULTS import *
from lib.PipeUtil import cfe, load_json_file, save_json_file
from lib.PipeAutoCal import fn_dir

def sync_meteor_preview(meteor_file,json_conf ):
   amsid = json_conf['site']['ams_id']
   stack = meteor_file.replace(".json", "-stacked.jpg")
   prev = stack.replace("-stacked.jpg", "-prev.jpg")
   prev_fn,ddd = fn_dir(prev)
   year = prev_fn[0:4]
   day = prev_fn[0:10]
   cloud_dir = "/mnt/archive.allsky.tv/" + amsid + "/METEORS/" + year + "/" + day + "/" 
   cloud_prev = cloud_dir + prev_fn
   img = cv2.imread(stack)
   img =  cv2.resize(img, (320,180))
   cv2.imwrite(prev, img)
   prev_tmp = prev.replace(".jpg", "-temp.jpg")
   cmd = "convert " + prev + " -quality 80 " + prev_tmp 
   os.system(cmd)
   os.system("mv " + prev_tmp + " " + prev)
   #if cfe(prev) == 0:
   #   os.system(cmd)
   #   print(cmd)
   print("Checking cloud...", cloud_prev)
   if cfe(cloud_dir,1) == 0:
      os.makedirs(cloud_dir)
   cmd = "rsync -auv " + prev + " " + cloud_dir 
   print(cmd)
   os.system(cmd)

def sync_index_day(day,json_conf ):
   amsid = json_conf['site']['ams_id']
   year = day[0:4]
   mif = "/mnt/ams2/meteors/" + day + "/" + day + "-" + amsid + ".meteors"
   cloud_dir = "/mnt/archive.allsky.tv/" + amsid + "/METEORS/" + year + "/" + day + "/" 
   cloud_indx = cloud_dir +  day + "-" + amsid + ".meteors"
   if cfe(cloud_dir,1) == 0:
      print("making:", cloud_dir)
      os.makedirs(cloud_dir)
   cmd = "rsync -auv " + mif + " " + cloud_indx
   os.system(cmd)
   print(cmd)

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
