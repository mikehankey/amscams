from datetime import datetime
import time
import glob
from lib.PipeUtil import cfe, save_json_file, convert_filename_to_date_cam, load_json_file, day_or_night   , get_file_info
from lib.PipeUtil import day_or_night, check_running
import datetime as dt
import os
import subprocess



def check_sync_cal_ai_db(json_conf):
   # make sure the recent as6.json is copied up the cloud
   # make sure the masks are in the cloud
   # make sure the cal summary files etc are in the cloud? this should already be happening
   # make sure / copy up JPG versions of the source calibration files (LATER we only need a subset not all of them. Really the 'best' per some time frequency 4x per month? 
   # for now we will check / add masks
   # but first, check the json conf to see if we are already done with all this anyway.
   print("Check sync Cal")
   do_sync = 0
   station_id = json_conf['site']['ams_id']
   if "sync_cal" not in json_conf:
      print("No sync cal in json conf", json_conf.keys())
      do_sync = 1
   else:
      if "mask_files" not in json_conf['sync_cal']:
         do_sync = 1
         print("No mask files in cal in json conf sync cal")
   if do_sync == 1:      
      if True:
         print("Sync mask files.")
         cloud_mask_dir = "/mnt/archive.allsky.tv/" + station_id + "/CAL/MASKS/"
         local_mask_dir = "/mnt/ams2/meteor_archive/" + station_id + "/CAL/MASKS/"
         if os.path.exists(cloud_mask_dir) is False:
            os.makedirs(cloud_mask_dir)
        
         cmd = "cp " + local_mask_dir + "*mask* " + cloud_mask_dir
         print(cmd)
         os.system(cmd)
         json_conf['sync_cal'] = {}
         json_conf['sync_cal']['mask_files'] = {}
         print("SAVE json conf")
         save_json_file("../conf/as6.json", json_conf)      
   else:
      print("Mask files are already sync'd")

   # CHECK IF AI IS INSTALLED ALREADY
   if "ml" not in json_conf:
      json_conf['ml'] = {}
      py36 = "/usr/bin/python3.6"
      if os.path.exists(py36) is True:
         print("Python 3.6 is installed.")
         json_conf['ml']['python36'] = True
      else: 
         print("*** Python 3.6 is NOT installed.")
         json_conf['ml']['python36'] = False 
      try:
         #import tensorflow as tf
         print("Tensor Flow IS installed.")
         json_conf['ml']['tensor_flow'] = True
      except:
         print("*** Tensor Flow IS NOT installed.")
         json_conf['ml']['tensor_flow'] = False 
      save_json_file("../conf/as6.json", json_conf)      
   else:
      print("ML already setup.")

   # check if the SQL DB is created yet.
   db_file = station_id + "_ALLSKY.db"
   if os.path.exists(db_file) is False:
      print("*** DB FILE DOESN'T EXIST:", db_file)
      cmd = "cat ALLSKYDB.sql | sqlite3 " + db_file
      print(cmd)
      os.system(cmd)
      cmd = "python3.6 testDB.py load ALL" 
      os.system(cmd)
   else: 
      print("DB FILE EXIST:", db_file)
      today = datetime.now().strftime("%Y_%m_%d")
      cmd = "python3.6 testDB.py load " + today
      os.system(cmd)

      os.system("gzip -kf " + db_file) 
      cloud_db_dir = "/mnt/archive.allsky.tv/" + station_id + "/DB/" 
      if os.path.exists(cloud_db_dir) is False:
         os.makedirs(cloud_db_dir)
      dbfile_2021 = db_file.replace(".db", "-2021.db.gz")
      if os.path.exists(cloud_db_dir + dbfile_2021) is False:
         os.system("cp " + db_file + ".gz " + cloud_db_dir + dbfile_2021 ) 
   #print("EXIT")   
   #exit()
         
def gitpull(json_conf):
   print("TEMP GIT CHECKOUT...")
   os.system("cd /home/ams/amscams/install; git checkout astrometry-install.sh")
   print("git pull > /home/ams/lastpull.txt")
   os.system("git pull > /home/ams/lastpull.txt")



   print("update flask.")
   os.system("cd /home/ams/amscams/install; ./update-flask-assets.sh ")
   return()
   if cfe("lib/version") == 1:
      fp = open("lib/version")
      for line in fp:
         line = line.replace("\n", "")
         install_version = float(line)
      fp.close()
   else:
      install_version = 0
      latest_version = 3.0
  
   cl_v = "/mnt/archive.allsky.tv/APPS/version"
   if cfe(cl_v) == 1: 
      fp = open(cl_v)
      for line in fp:
         line = line.replace("\n", "")
         latest_version = float(line)
      fp.close()
   else:
      latest_version = 3

   print("INSTALLED VERSION IS ", install_version)
   print("LATEST VERSION IS ", latest_version)
   if install_version != latest_version:
      print("Code not up to date. We should sync.")
      os.system("git pull")
      os.system("cd /home/ams/amscams/install; ./update-flask-assets.sh ")
   print("DONE GIT PULL.")


def run_jobs(json_conf):

   today = datetime.now().strftime("%Y_%m_%d")
   yest = (datetime.now() - dt.timedelta(days = 1)).strftime("%Y_%m_%d")
   year,month, day = today.split("_")

   # this will only run 1x for each file and then only on new files. 
   running = check_running("refit_meteor_year")
   print("Refit meteor year", running)
   if int(running) == 0:
      cmd = "./recal.py refit_meteor_year " + year + " > refit_run_log.txt 2>&1 &"
      print(cmd)
      os.system(cmd)
   else:
      print("Refit meteor year is running already in the background... ", running)

   os.system("killall flex-detect.py")
   rj_start = time.time()
   # make sure DynaDB is not already running. If it is kill it.
   running = check_running("DynaDB.py")
   if running > 0:
      os.system("kill -9 $(ps aux | grep 'rerun.py' | awk '{print $2}')")
   running = check_running("rerun.py")
   if running > 0:
      os.system("kill -9 $(ps aux | grep 'DynaDB' | awk '{print $2}')")


   # log heartbeat with network
   msg = "info:run_jobs:Run jobs started"
   cmd = "./log.py '" + msg + "'"
   os.system(cmd)
   running = check_running("Process.py run_jobs")
   if running >= 3:
      print("Already running.")
      return()



   three_day = (datetime.now() - dt.timedelta(days = 2)).strftime("%Y_%m_%d")
   four_day = (datetime.now() - dt.timedelta(days = 3)).strftime("%Y_%m_%d")
   five_day = (datetime.now() - dt.timedelta(days = 4)).strftime("%Y_%m_%d")
   six_day = (datetime.now() - dt.timedelta(days = 5)).strftime("%Y_%m_%d")
   sun, az, alt = day_or_night(datetime.now(), json_conf, 1)
   print(sun, az, alt)

   # update from git hub(Change to work 1x per x hours)
   print("CHECK CODE UPDATES.")
   update_code = 0
   if cfe('/home/ams/lastpull.txt') == 0:
      update_code = 1
   else:
      size, tdiff = get_file_info("/home/ams/lastpull.txt")

      if tdiff / 60 > .00005:
         print("UPDATE CODE.")
         update_code = 1
      else:
         print("Code was last updated", tdiff / 60, "hours ago")

   print("UPDATE CODE?", update_code)
   if update_code == 1:

      gitpull(json_conf)


   # Sync cal files to the cloud as needed
   print("checking cloud dir") 
   check_sync_cal_ai_db(json_conf)
   amsid = json_conf['site']['ams_id']
   # check to make sure the cloud drive is setup and cal sync'd
   cloud_conf_dir = "/mnt/archive.allsky.tv/" + amsid + "/CAL/"
   cloud_conf_file = cloud_conf_dir + "as6.json"


   if cfe(cloud_conf_dir,1) == 0:
      os.makedirs(cloud_conf_dir)
   if cfe(cloud_conf_file) == 0:
      os.system("cp ../conf/as6.json " + cloud_conf_file)
   else:
      print("Cloud conf file is good.")

   # Once every 5 hours run the events for yesterday and today, IF WMPL is installed
   #if "dynamodb" in json_conf:
   if True:
      running = check_running("DynaDB.py")
      if running > 0:
         os.system("kill -9 $(ps aux | grep 'rerun.py' | awk '{print $2}')")
         os.system("kill -9 $(ps aux | grep 'DynaDB' | awk '{print $2}')")
      run_load = 0
      if cfe("/home/ams/loaded_last.txt") == 0:
         run_load = 1
         os.system("touch /home/ams/loaded_last.txt")
         print("load meteors .")
      else:
         size, tdiff = get_file_info("/home/ams/loaded_last.txt")
         print("Last Loaded Data :", tdiff/60, "hours ago")
         if int(tdiff) / 60 > 1:
            run_load = 1 


      if run_load == 1:

         print("./DynaDB.py ddd " + yest + "")
         os.system("./DynaDB.py ddd " + yest + " > /home/ams/ddd.txt")
         print("./DynaDB.py ddd " + today + "")
         os.system("./DynaDB.py ddd " + today + " >> /home/ams/ddd.txt")
         os.system("touch /home/ams/loaded_last.txt")

   if "WMPL" in json_conf:
      print("WMPL EXIST.")
      run_solve = 0
      if cfe("/home/ams/solved_last.txt") == 0:
         run_solve = 1
         os.system("touch /home/ams/solved_last.txt")
         print("Run events.")
      else:
         size, tdiff = get_file_info("/home/ams/solved_last.txt")
         print("Last Update:", tdiff)
         if int(tdiff) / 60 > 5:
            #os.system("./solveWMPL.py sd " + yest + "")
            os.system("touch /home/ams/solved_last.txt")

            #os.system("./DynaDB.py load_day " + today + "")
            ##os.system("./Process.py ded " + today + "")
            #os.system("./solveWMPL.py sd " + today + "")
            os.system("touch /home/ams/solved_last.txt")

   # Remove old files in the SD dir likely corrupted) 
   sd_files = glob.glob("/mnt/ams2/SD/*.mp4")
   for file in sd_files:
      (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      elp = f_datetime - datetime.now()
      days_old = abs(elp.total_seconds()) / 86400
      print("SD FILE IS DAYS OLD:", days_old)
      if (days_old > 5):
         cmd = "rm " + file 
         print(cmd)
         os.system(cmd)
   sd_files = glob.glob("/mnt/ams2/SD/*.mp4")
   if len(sd_files) > 0:
      # restart scan stack if it is running.
      restart_scan = 0
      try:
         if cfe("/home/ams/scan-restart.txt") == 1:
            size, tdiff = get_file_info("/home/ams/scan-restart.txt")
            if tdiff / 60 > 2:
               restart_scan = 1
         else:
            restart_scan = 1

         if restart_scan == 1:
            cmd = "kill -9 $(ps aux | grep 'scan_stack' | awk '{print $2}')"
            print(cmd)
            os.system(cmd)
            os.system("touch /home/ams/scan-restart.txt")
      except:
         print("Scan stack is not running at all.")


   cmds = []
   cmds.append(('all', "Night Stacks", "cd /home/ams/amscams/pipeline; ./Process.py hsh " + today + "" ))
   cmds.append(('all', "Night Stacks", "cd /home/ams/amscams/pipeline; ./Process.py hsh " + yest + ""))
   cmds.append(('all', "Monitor", "cd /home/ams/amscams/pipeline; ./monitor.py "))
   cmds.append(('all', "Clean disk / Purge old files", "cd /home/ams/amscams/pythonv2; ./doDay.py cd"))
   cmds.append(('all', "Clean disk / Purge old files", "cd /home/ams/amscams/pipeline; ./Process.py rm_corrupt"))
   cmds.append(('all', "Make Meteor Index", "cd /home/ams/amscams/pipeline; ./Process.py mmi_day " + today))
   cmds.append(('all', "Make Meteor Index", "cd /home/ams/amscams/pipeline; ./Process.py mmi_day " + yest))


   cmds.append(('day', "Make Meteor Index", "cd /home/ams/amscams/pipeline; ./Process.py mmi_all"))
   cmds.append(('day', "Move Day Files", "cd /home/ams/amscams/pythonv2; ./move_day_files.py"))
   cmds.append(('all', "Update the proc index", "cd /home/ams/amscams/pythonv2; ./ASDaemon.py proc_index"))
   cmds.append(('all', "Update the file index", "cd /home/ams/amscams/pythonv2; ./batchJobs.py fi"))
   cmds.append(('all', "Run Master Stacks for Current Night", "cd /home/ams/amscams/pipeline; ./Process.py hs " + today))
   cmds.append(('all', "Run Master Stacks for Last Night", "cd /home/ams/amscams/pipeline; ./Process.py hs " + yest))
   cmds.append(('all', "Run Master Stacks for Current Night", "cd /home/ams/amscams/pythonv2; ./autoCal.py meteor_index"))

   cmds.append(('all', "Run Master Stacks for Current Night", "cd /home/ams/amscams/pythonv2; ./autoCal.py cal_index"))
   cmds.append(('all', "(Update default cal)", "cd /home/ams/amscams/pipeline; ./Process.py cal_defaults"))
   #cmds.append(('day', "(Fixup any bad cal files)", "cd /home/ams/amscams/pipeline; ./Process.py refit_all all bad "))
   cmds.append(('all', "Run Calibs (if daytime)", "cd /home/ams/amscams/pipeline; ./Process.py ca"))
   cmds.append(('all', "Cal Status", "cd /home/ams/amscams/pipeline; ./recal.py status all "))
   cmds.append(('all', "Batch Apply Bad", "cd /home/ams/amscams/pipeline; ./recal.py batch_apply_bad all 20"))
   #cmds.append(('day', "Super Cal", "cd /home/ams/amscams/pipeline; ./Process.py super_cal"))
   #cmds.append(('all', "Run Master Stacks for Current Night", "cd /home/ams/amscams/pythonv2; ./batchJobs.py sna 1"))

   cmds.append(('all', "Batch Meteor Thumbs", "cd /home/ams/amscams/pythonv2; ./batchJobs.py bmt"))
   cmds.append(('all', "Run Vals Detector", "cd /home/ams/amscams/pythonv2; ./flex-detect.py bv " + today))
   cmds.append(('all', "Run Vals Detector", "cd /home/ams/amscams/pythonv2; ./flex-detect.py bv " + yest))

   cmds.append(('all', "Run Verify Meteor", "cd /home/ams/amscams/pythonv2; ./flex-detect.py vms " + today))
   cmds.append(('all', "Run Verify Meteor", "cd /home/ams/amscams/pythonv2; ./flex-detect.py vms " + yest))

   cmds.append(('all', "Run Vals Detector", "cd /home/ams/amscams/pythonv2; ./flex-detect.py bv " + three_day))
   cmds.append(('all', "Run Vals Detector", "cd /home/ams/amscams/pythonv2; ./flex-detect.py bv " + four_day))
   cmds.append(('all', "Run Vals Detector", "cd /home/ams/amscams/pythonv2; ./flex-detect.py bv " + five_day))
   cmds.append(('all', "Run Verify Meteor", "cd /home/ams/amscams/pythonv2; ./flex-detect.py vms " + three_day))
   cmds.append(('all', "Run Verify Meteor", "cd /home/ams/amscams/pythonv2; ./flex-detect.py vms " + four_day))
   cmds.append(('all', "Run Verify Meteor", "cd /home/ams/amscams/pythonv2; ./flex-detect.py vms " + five_day))
   
   #cmds.append(('day', "Run Reject Filters", "cd /home/ams/amscams/pipeline; ./Process.py reject_masks " + today))
   #cmds.append(('day', "Run Reject Filters", "cd /home/ams/amscams/pipeline; ./Process.py reject_masks " + yest))
   # run it 2x to get rid of hotspots
   #cmds.append(('day', "Run Reject Filters", "cd /home/ams/amscams/pipeline; ./Process.py reject_masks " + today))
   #cmds.append(('day', "Run Reject Filters", "cd /home/ams/amscams/pipeline; ./Process.py reject_masks " + yest))
   #cmds.append(('day', "Run Reject Filters", "cd /home/ams/amscams/pipeline; ./Process.py reject_planes " + today))
   #cmds.append(('day', "Run Reject Filters", "cd /home/ams/amscams/pipeline; ./Process.py reject_planes " + yest))
   #cmds.append(('day', "Reduce / Confirm Meteors", "cd /home/ams/amscams/pipeline; ./Process.py confirm " + today))
   #cmds.append(('day', "Reduce / Confirm Meteors", "cd /home/ams/amscams/pipeline; ./Process.py confirm " + yest))

   #cmds.append(('day', "Meteor Prep", "cd /home/ams/amscams/pipeline; ./Process.py meteor_prep " + today))
   #cmds.append(('day', "Meteor Prep", "cd /home/ams/amscams/pipeline; ./Process.py meteor_prep " + yest))
   #cmds.append(('day', "Cal Wiz", "cd /home/ams/amscams/pipeline; ./Process.py cal_wiz"))
   #cmds.append(('day', "Meteor Prep", "cd /home/ams/amscams/pipeline; ./Process.py meteor_prep " + today + " 2" ))
   #cmds.append(('day', "Meteor Prep", "cd /home/ams/amscams/pipeline; ./Process.py meteor_prep " + yest + " 2"))
   #cmds.append(('day', "Cal Init", "cd /home/ams/amscams/pipeline; ./auto_run_cal.py"))

   #cmds.append(('all', "Run Audit", "cd /home/ams/amscams/pipeline; ./Process.py audit " + today))

   for cmd in cmds :
      if sun == "day":
         print(cmd[2])
         st = time.time()
         os.system(cmd[2] + " > /home/ams/run_jobs.txt 2>&1")
         elp = time.time() - st
         print("ELP:", elp)
      else:
         if cmd[0] == 'all':
            print(cmd[2])
            st = time.time()
            os.system(cmd[2]  + " > /home/ams/run_jobs.txt 2>&1")
            elp = time.time() - st
            print("ELP:", elp)

   msg = "info:run_jobs:Run jobs ended"
   cmd = "./log.py '" + msg + "'"
   #os.system(cmd)
   rj_elp = time.time() - rj_start
   print("RJ ELP:", rj_elp)
   cmd = "echo 'elapsed run time: " + str(rj_elp) + " ' >> /home/ams/run_jobs.txt "
   os.system(cmd)

   
