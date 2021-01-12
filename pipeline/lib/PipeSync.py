'''

functions to sync the meteor archive with the wasabi dir

'''
import cv2
import glob
import os
from lib.DEFAULTS import *
from lib.PipeUtil import cfe, load_json_file, save_json_file
from lib.PipeAutoCal import fn_dir

def prep_month(year_day, json_conf):
   mdirs = glob.glob("/mnt/ams2/meteors/" + year_day + "*")
   for dd in sorted(mdirs, reverse=True):
      fn,dir = fn_dir(dd)
      do_meteor_day_prep(fn,json_conf)

def do_meteor_day_prep(day, json_conf,phase=1):

   amsid = json_conf['site']['ams_id']
   # for each day we want to do these things in this order.
   # run confirm / reject_mask filter on all meteors
   if phase == 1:
      cmd = "./Process.py reject_masks " + day
      print(cmd)
      os.system(cmd)

      # build the index and sync
      cmd = "./Process.py mmi_day " + day
      print(cmd)
      os.system(cmd)

      # sync index files
      cmd = "./Process.py sid " + day
      print(cmd)
      os.system(cmd)

      year = day[0:10]
      event_dir = "/mnt/ams2/meteor_archive/" + amsid + "/" + year + "/" + day + "/"
   
      cmd = "rm " + event_dir + "*AMS*"
      print(cmd)
      os.system(cmd)

      cmd = "./Process.py efd " + day
      print(cmd)
      os.system(cmd)

      cmd = "./Process.py sync_prev_all " + day
      print(cmd)
      os.system(cmd)
   print("PHASE", phase)
   if int(phase) == 2:
      # check for multi-station events 
      cmd = "./Process.py efd " + day
      print(cmd)

      # sync prev files for MS events 
      cmd = "./Process.py sync_prev_all " + day
      print(cmd)

      # run the confirm/reduce on all meteors 
      cmd = "./Process.py confirm " + day
      print(cmd)
      os.system(cmd)

      # run the refit on all (MS) meteors 
      cmd = "./Process.py refit_meteors " + day
      print(cmd)
      os.system(cmd)

      # build the index and sync (Again)
      cmd = "./Process.py mmi_day " + day
      print(cmd)
      os.system(cmd)

      # sync index files
      cmd = "./Process.py sid " + day
      print(cmd)
      os.system(cmd)

      # sync prev files
      cmd = "./Process.py sync_prev_all " + day
      print(cmd)
      os.system(cmd)

      # Now all events for this day should be prepped and the 'min-data' sync'd. 
      # mini-data is the txt data + 1 thumb preview image for the multi-station events
      # rm past station data and re-sync
      year = day[0:10]
      event_dir = "/mnt/ams2/meteor_archive/" + amsid + "/" + year + "/" + day + "/"
   
      cmd = "rm " + event_dir + "*AMS*"
      print(cmd)
      os.system(cmd)

      cmd = "./Process.py efd " + day
      print(cmd)
      os.system(cmd)

      cmd = "./Process.py solve_day " + day
      print(cmd)
      os.system(cmd)



def sync_conf(json_conf ):
   amsid = json_conf['site']['ams_id']
   cloud_dir = "/mnt/archive.allsky.tv/" + amsid + "/CAL/"
   if cfe(cloud_dir + "as6.json") == 0:
      cmd = "cp ../conf/as6.json " + cloud_dir 
      os.system(cmd)

def sync_meteor_preview_all(day,json_conf ):
   amsid = json_conf['site']['ams_id']
   year = day[0:4]
   mdir = "/mnt/ams2/meteors/" + day + "/"
   lcdir = mdir + "cloud_files/"
   files = glob.glob(mdir + "*.json")
   meteors = []
   mi = {}
   meteor_data = []
   for mf in files:
      if "reduced" not in mf and "stars" not in mf and "man" not in mf and "star" not in mf and "import" not in mf and "archive" not in mf and "cal" not in mf and "frame" not in mf:
         meteors.append(mf)
   cloud_dir = "/mnt/archive.allsky.tv/" + json_conf['site']['ams_id'] + "/METEORS/" + year + "/" + day + "/" 
   print("Checking cloud...", cloud_dir)
   if cfe(cloud_dir,1) == 0:
      os.makedirs(cloud_dir)


   cloud_prev_files = glob.glob(cloud_dir + "*prev.jpg")
   print(cloud_dir)
   in_cloud = {}
   for cf in cloud_prev_files:
      fn, dir = fn_dir(cf)
      #fn = fn.replace(".json", "-prev.jpg")
      #fn = amsid + "_" + fn
      in_cloud[fn] = 1

   ns = 0

   

   for mm in meteors:
      fn, fnd = fn_dir(mm)
      mj = load_json_file(mm)
      if "multi_station_event" in mj:
         fn = fn.replace(".json", "-prev.jpg")
         fn = amsid + "_" + fn 
         if fn in in_cloud:
            print("File syncd already:", fn)
         else:
            print("File not syncd already:", fn)
            sync_meteor_preview(mm, json_conf, 0)

   cmd = "rsync -av " + lcdir + " " + cloud_dir
   os.system(cmd)


def sync_meteor_preview(meteor_file,json_conf,ccd=1 ):
   if "/mnt/ams2/meteors" not in meteor_file:
      day = meteor_file[0:10]
      meteor_file = meteor_file.replace(".mp4", "")
      meteor_file = meteor_file.replace(".json", "")
      meteor_file = "/mnt/ams2/meteors/" + day + "/" + meteor_file + ".json"

   amsid = json_conf['site']['ams_id']
   stack = meteor_file.replace(".json", "-stacked.jpg")
   prev = stack.replace("-stacked.jpg", "-prev.jpg")
   prev_fn,ddd = fn_dir(prev)
   prev_dir = ddd + "/cloud_files/"
   prev = prev_dir + amsid + "_" + prev_fn
   if cfe(prev_dir, 1) == 0:
      os.makedirs(prev_dir)
   year = prev_fn[0:4]
   day = prev_fn[0:10]
   cloud_dir = "/mnt/archive.allsky.tv/" + amsid + "/METEORS/" + year + "/" + day + "/" 
   cloud_prev = cloud_dir + prev_fn
   if cfe(prev) == 0:
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
   if ccd == 1:
      print("Checking cloud...", cloud_prev)
      if cfe(cloud_dir,1) == 0:
         os.makedirs(cloud_dir)
   #cmd = "rsync -auv " + prev + " " + cloud_dir 
   cmd = "cp " + prev + " " + cloud_dir 
   print(cmd)
   #os.system(cmd)

def sync_index_day(day,json_conf ):
   amsid = json_conf['site']['ams_id']
   year = day[0:4]
   sync_conf(json_conf)
   mif = "/mnt/ams2/meteors/" + day + "/" + day + "-" + amsid + ".meteors"
   mif_detail = "/mnt/ams2/meteors/" + day + "/" + day + "-" + amsid + "-detail.meteors.gz"
   cloud_dir = "/mnt/archive.allsky.tv/" + amsid + "/METEORS/" + year + "/" + day + "/" 
   cloud_indx = cloud_dir +  day + "-" + amsid + ".meteors"
   cloud_detail = cloud_dir +  day + "-" + amsid + "-detail.meteors.gz"
   if cfe(cloud_dir,1) == 0:
      print("making:", cloud_dir)
      os.makedirs(cloud_dir)
   cmd = "rsync -auv " + mif + " " + cloud_indx
   os.system(cmd)
   print(cmd)
   cmd = "rsync -auv " + mif_detail + " " + cloud_detail
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
