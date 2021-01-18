from datetime import datetime
from lib.PipeUtil import cfe, save_json_file, convert_filename_to_date_cam, load_json_file, day_or_night   , get_file_info
from lib.PipeUtil import day_or_night, check_running
import datetime as dt
import os

def update_code(json_conf):
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


def run_jobs(json_conf):
   running = check_running("Process.py run_jobs")
   if running >= 3:
      print("Already running.")
      return()
   today = datetime.now().strftime("%Y_%m_%d")
   yest = (datetime.now() - dt.timedelta(days = 1)).strftime("%Y_%m_%d")
   sun, az, alt = day_or_night(datetime.now(), json_conf, 1)
   print(sun, az, alt)
   cmds = []
   cmds.append(('all', "Clean disk / Purge old files", "cd /home/ams/amscams/pythonv2; ./doDay.py cd"))
   cmds.append(('day', "Make Meteor Index", "cd /home/ams/amscams/pipeline; ./Process.py mmi_all"))
   cmds.append(('day', "Move Day Files", "cd /home/ams/amscams/pythonv2; ./move_day_files.py"))
   cmds.append(('day', "Run Calibs (if daytime)", "cd /home/ams/amscams/pipeline; ./Process.py ca"))
   #cmds.append(('day', "Super Cal", "cd /home/ams/amscams/pipeline; ./Process.py super_cal"))
   cmds.append(('day', "Run Master Stacks for Current Night", "cd /home/ams/amscams/pythonv2; ./autoCal.py cal_index"))
   cmds.append(('all', "Update the proc index", "cd /home/ams/amscams/pythonv2; ./ASDaemon.py proc_index"))
   cmds.append(('all', "Update the file index", "cd /home/ams/amscams/pythonv2; ./batchJobs.py fi"))
   #cmds.append(('all', "Run Master Stacks for Current Night", "cd /home/ams/amscams/pythonv2; ./batchJobs.py sna 1"))
   cmds.append(('all', "Run Master Stacks for Current Night", "cd /home/ams/amscams/pipeline; ./Process.py hs " + today))
   cmds.append(('all', "Run Master Stacks for Last Night", "cd /home/ams/amscams/pipeline; ./Process.py hs " + yest))

   cmds.append(('day', "Run Master Stacks for Current Night", "cd /home/ams/amscams/pythonv2; ./autoCal.py meteor_index"))
   cmds.append(('all', "Batch Meteor Thumbs", "cd /home/ams/amscams/pythonv2; ./batchJobs.py bmt"))
   cmds.append(('all', "Run Vals Detector", "cd /home/ams/amscams/pythonv2; ./flex-detect.py bv " + today))
   cmds.append(('all', "Run Vals Detector", "cd /home/ams/amscams/pythonv2; ./flex-detect.py bv " + yest))
   cmds.append(('all', "Run Verify Meteor", "cd /home/ams/amscams/pythonv2; ./flex-detect.py vms " + today))
   cmds.append(('all', "Run Verify Meteor", "cd /home/ams/amscams/pythonv2; ./flex-detect.py vms " + yest))
   cmds.append(('day', "Run Reject Filters", "cd /home/ams/amscams/pipeline; ./Process.py reject_masks " + today))
   cmds.append(('day', "Run Reject Filters", "cd /home/ams/amscams/pipeline; ./Process.py reject_masks " + yest))
   # run it 2x to get rid of hotspots
   cmds.append(('day', "Run Reject Filters", "cd /home/ams/amscams/pipeline; ./Process.py reject_masks " + today))
   cmds.append(('day', "Run Reject Filters", "cd /home/ams/amscams/pipeline; ./Process.py reject_masks " + yest))
   cmds.append(('day', "Reduce / Confirm Meteors", "cd /home/ams/amscams/pipeline; ./Process.py confirm " + today))
   cmds.append(('day', "Reduce / Confirm Meteors", "cd /home/ams/amscams/pipeline; ./Process.py confirm " + yest))
   cmds.append(('day', "Meteor Prep", "cd /home/ams/amscams/pipeline; ./Process.py meteor_prep " + today))
   cmds.append(('day', "Meteor Prep", "cd /home/ams/amscams/pipeline; ./Process.py meteor_prep " + yest))
   cmds.append(('day', "Cal Wiz", "cd /home/ams/amscams/pipeline; ./Process.py cal_wiz"))
   cmds.append(('day', "Meteor Prep", "cd /home/ams/amscams/pipeline; ./Process.py meteor_prep " + today + " 2" ))
   cmds.append(('day', "Meteor Prep", "cd /home/ams/amscams/pipeline; ./Process.py meteor_prep " + yest + " 2"))

   #cmds.append(('all', "Run Audit", "cd /home/ams/amscams/pipeline; ./Process.py audit " + today))

   for cmd in cmds :
      if sun == "day":
         print(cmd[2])
         os.system(cmd[2])
      else:
         if cmd[0] == 'all':
            print(cmd[2])
            os.system(cmd[2])
   
