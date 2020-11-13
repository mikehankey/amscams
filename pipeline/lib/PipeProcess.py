from datetime import datetime
from lib.PipeUtil import cfe, save_json_file, convert_filename_to_date_cam, load_json_file, day_or_night   , get_file_info
from lib.PipeUtil import day_or_night, check_running
import datetime as dt
import os

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
   cmds.append(('day', "Clean disk / Purge old files", "cd /home/ams/amscams/pythonv2; ./doDay.py cd"))
   cmds.append(('day', "Move Day Files", "cd /home/ams/amscams/pythonv2; ./move_day_files.py"))
   cmds.append(('all', "Update the proc index", "cd /home/ams/amscams/pythonv2; ./ASDaemon.py proc_index"))
   cmds.append(('all', "Update the file index", "cd /home/ams/amscams/pythonv2; ./batchJobs.py fi"))
   #cmds.append(('all', "Run Master Stacks for Current Night", "cd /home/ams/amscams/pythonv2; ./batchJobs.py sna 1"))
   cmds.append(('all', "Run Master Stacks for Current Night", "cd /home/ams/amscams/pipeline; ./Process.py hs " + today))
   cmds.append(('all', "Run Master Stacks for Last Night", "cd /home/ams/amscams/pipeline; ./Process.py hs " + yest))
   cmds.append(('day', "Run Master Stacks for Current Night", "cd /home/ams/amscams/pythonv2; ./autoCal.py cal_index"))
   cmds.append(('day', "Run Master Stacks for Current Night", "cd /home/ams/amscams/pythonv2; ./autoCal.py meteor_index"))
   cmds.append(('all', "Batch Meteor Thumbs", "cd /home/ams/amscams/pythonv2; ./batchJobs.py bmt"))
   cmds.append(('day', "Run Calibs (if daytime)", "cd /home/ams/amscams/pipeline; ./Process.py ca"))
   cmds.append(('all', "Run Vals Detector", "cd /home/ams/amscams/pythonv2; ./flex-detect.py bv " + today))
   cmds.append(('all', "Run Vals Detector", "cd /home/ams/amscams/pythonv2; ./flex-detect.py bv " + yest))
   cmds.append(('all', "Run Verify Meteor", "cd /home/ams/amscams/pythonv2; ./flex-detect.py vms " + today))
   cmds.append(('all', "Run Verify Meteor", "cd /home/ams/amscams/pythonv2; ./flex-detect.py vms " + yest))
   cmds.append(('all', "Run Audit", "cd /home/ams/amscams/pipeline; ./Process.py audit " + today))

   for cmd in cmds :
      if sun == "day":
         print(cmd[2])
         os.system(cmd[2])
      else:
         if cmd[0] == 'all':
            print(cmd[2])
            os.system(cmd[2])
   
