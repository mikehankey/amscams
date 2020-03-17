#!/usr/bin/python3


""" 
   ASDaemon.py - main processing manager
      - should run 24/7 and a cron should exist that restarts it, if it is not running, or has crashed.
      - handles / manages all recording, processing tasks, disk management, sync'ing, jobs etc:
         * checks ffmpeg recording state, (is it running, & is it saving files), kills/restarts threads as needed
         * checks scan_stack.py bs processing state restarts as needed
         * launches flex_detect.py bv (batch detect values)  
         * launches flex_detect.py vms (verify meteors)  
         * launches doDay.py (sync/publish)  
         * launches doDay.py cd (purge/clean disk)  
         * checks time sync and makes sure it is ok
         * checks for new tasks from the admin server and executes as needed
         * runs git pulls and cron updates 
         * check for VPN connection requests 
      - ASDaemon.py will manage the pipeline process, which is:
      ffmpeg_record -> min_file.mp4 -> 
         scan_stack -> vals.json & stack.png -> 
         flex_detect dv (detect vals) -> -maybe-meteors,-toomany,-detect,-nonmeteor -> 
         flex_detect vms (verify meteors) -> old meteor file & arc meteor files -> 
         sync-archive files ->
         run_detect -> 
         solve.py 
"""      
   
import sys
import os
import daemon
import time
import json 
from datetime import datetime , timedelta

from lib.UtilLib import check_running
from lib.FileIO import load_json_file , cfe
from lib.ASDaemonLib import day_or_night, get_files, run_verify_meteors, run_vals_detect, exec_cmd, update_latest, get_proc_stats, proc_index, fix_days

def main_thread():
   current_date = datetime.now().strftime("%Y_%m_%d")
   log_file = "/mnt/ams2/temp/ASDaemon_log.txt"
   log = open(log_file, "w") 
   json_conf = load_json_file("../conf/as6.json")
   total_cams = len(json_conf['cameras'])
   cam_ids = []
   jobs = {}
   state = {}
   state['sun_status'] = [day_or_night(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), json_conf), time.time()]
   state['last_update'] = ""
   state['ffprocs'] = 0
   state['FFPROC_THRESH'] = total_cams * 2
   state['pending_files'] = 0
   status, state['current_load'] = exec_cmd("uptime |sed -E 's/.*load average: (.+?),.*/\\1/g'")
   state['current_load'] = float(state['current_load'].split(",")[0])
   state['last_index'] = 0
   state['last_sync'] = 0
   state['latest'] = 0 
   state['scan_stack'] = time.time()
   state['vals_detect'] = time.time()
   state['fix_day'] = time.time()
   state['verify_meteors'] = 0
   state['check_disk'] = time.time()
   state['do_day'] = time.time()
   state['cam_info'] = []

   
   proc_file = "/mnt/ams2/SD/proc2/json/proc_stats.json"
   if cfe(proc_file) == 1:
      state['proc_stats'] = load_json_file(proc_file)
   else:
      state['proc_stats'] = ""

   for cam in json_conf['cameras']:
      cam_info = {}
      cam_info['cam_id'] = json_conf['cameras'][cam]['cams_id']
      cam_info['ip'] = json_conf['cameras'][cam]['ip']
      cam_info['sd_url'] = json_conf['cameras'][cam]['sd_url']
      cam_info['hd_url'] =json_conf['cameras'][cam]['hd_url']
      state['cam_info'].append(cam_info)


   while True:
      # get current state info (but only for items that have not been updated accordingly e.g. don't have to check all these everytime.
      current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      current_date = datetime.now().strftime("%Y_%m_%d")
      state['last_update'] = current_time

      # update sun status every 10 minutes
      if time.time() - state['sun_status'][1] > 600:
         state['load'] = exec_cmd("uptime")
         state['sun_status'] = [day_or_night(current_time, json_conf), time.time()]
         print("UPDATE SUN", state['sun_status'])
      else:
         print("SUN OK", state['sun_status'], time.time() - state['sun_status'][1])
      log.write("The time is now " + current_time + "\n")

      ########## MAIN VIDEO PROCESSING TASKS ###############
      # TASK #1 - manage the ffmpeg recording processes
      # check status of ffmpeg running process  
      # check status of recently saved video files
      # if process is not running or video files are not being saved
      # ping cam to see if it responds 
      # restart the ffmpeg recording process if ping is good
      # log cam restarts, after X failed restarts don't try to keep restarting, instead just restart once every hour
      state['ffprocs'] = check_running("ffmpeg")
      state['pending_files'] = get_files("/mnt/ams2/SD/", "*")



      if state['ffprocs'] < state['FFPROC_THRESH']:
         log.write("ERROR: FFMPEG RUNNING PROCESSES BELOW THRESH:" + str(state['ffprocs']) + "\n")
         #bad_cams = find_bad_cams() 
         # here we should : 
            # determine which cam(s) are down, log info, run the watch-dog
            # we should figure out if cam is perm down or just temp down. If perm down, only recheck 1x per X hours
      else:
         print("FF GOOD:" + str(state['ffprocs']) + "\n")

      # TASK #2 -- UPDATE THE LATEST IMAGES
      if time.time() - state['latest'] > 300:
         update_latest(state['cam_info'],state['pending_files'])
         state['latest'] = time.time()

      # TASK #2 - manage the scan and stack processing 
      # only start this process is the total pending files is < 500
      if len(state['pending_files']) < 500: 
         print("Less than 500 files in the pending queue. This is good! We can do some more jobs.")

      scan_running = check_running("scan_stack.py bs")
      if scan_running == 0:
         print("scan_stack.py is not running.")
         cmd = "./scan_stack.py bs " + current_date + " > /dev/null 2>&1 &"
         state['scan_stack'] = time.time()
         print(cmd)
         os.system(cmd)
      else:
         print("scan_stack.py is running.")
      # TASK #3 - manage the vals detection processing 
      if time.time() - state['vals_detect'] > 600:
         run_vals_detect(current_date)
         state['vals_detect'] = time.time()

      # TASK #4 - manage the meteor verify processing 
      if time.time() - state['verify_meteors'] > 900:
         run_verify_meteors(current_date)
         state['verify_meteors'] = time.time()
      else:
         print("Verify last run:", time.time() - state['verify_meteors'] ) 

      # TASK #4 fix any missing files for past days
      if time.time() - state['fix_day'] > 6000:
         fix_days()
         state['fix_day'] = time.time()
      else:
         print("Verify last run:", time.time() - state['verify_meteors'] )
 

      
      ########## ARCHIVE TASKS ###############
      # TASK #1 - manage the indexing and archive syncing processing 
      # run meteor index, run create archive index, run sync wasabi (detects, archive data) 

      # TASK #2 - check for API TASKS (deletes, point updates) and apply 
   
      ########## DISK AND ADMIN TASKS ###############
      # TASK #1 - check and purge disk as needed (once every 8 hrs/ 28,800 seconds)

      if time.time() - state['check_disk'] > 28800:
         os.system("./doDay.py cd")
         state['check_disk'] = time.time()

      # TASK #2 - run doDay tasks
      if time.time() - state['do_day'] > 3600:
         os.system("./doDay.py batch 3")
         state['do_day'] = time.time()
       
      ########## CALIBRATION / DATA TUNING ###############
      # TASK #1 - attempt blind solving if the system is not calibrated yet
      # TASK #2 - re-fit meteors in the archive that need it (new caps or caps with high > res)
      # TASK #3 - run re-point-picking on files in archive as needed.

      ########## EVENT DETECTION & SOLVING ###############
      # Check for multi-station events


      # sleep after loops
      print("Sleep 30.")
      for key in state:
         if key == 'pending_files':
            print(key, len(state[key]))
         elif key == 'proc_stats':
            for pk in state['proc_stats']:
            
               print(pk, state[key][pk])

         elif key == "latest" or key == "scan_stack" or key == "vals_detect" or key == "verify_meteors" or key == "check_disk" or key == "do_day":
            print(key, time.time() - state[key])
  
         else:
            print(key, state[key])
      time.sleep(30)

def run():
   # before running make sure another daemon process is not already running!
   da_running = check_running("ASDaemon.py")
   if da_running > 1:
      print("AS6Daemon.py is already running! quitting.", da_running)
      exit()
   with daemon.DaemonContext():
      main_thread()

if __name__ == "__main__":
   if len(sys.argv) >= 2:
      cmd = sys.argv[1]
   else:
      cmd = ""
   if cmd == "":
      print("Starting AllSky Daemon")
      main_thread()
   if cmd == "proc_index":
      proc_index()
   if cmd == "fix_days":
      fix_days()
   if cmd == "update_proc":
      update_proc_index(sys.argv[2])
