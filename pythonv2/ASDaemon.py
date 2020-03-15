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
         * launches scan_stack.py cd (purge/clean disk)  
         * checks time sync and makes sure it is ok
         * checks for new tasks from the admin server and executes as needed
         * runs git pulls and cron updates 
      - ASDaemon.py will manage the pipeline process, which is:
      ffmpeg_record -> min_file.mp4 -> 
         scan_stack -> vals.json & stack.png -> 
         flex_detect dv (detect vals) -> -maybe-meteors,-toomany,-detect,-nonmeteor -> 
         flex_detect vms (verify meteors) -> old meteor file & arc meteor files -> 
         sync-archive files ->
         run_detect -> 
         solve.py 
"""      
   

import daemon
import time

from lib.UtilLib import check_running

def main_thread():
   log_file = "/mnt/ams2/temp/ASDaemon_log.txt"
   log = open(log_file, "w") 
   while True:
      log.write("The time is now " + str(time.ctime()) + "\n")

      ########## MAIN VIDEO PROCESSING TASKS ###############
      # TASK #1 - manage the ffmpeg recording processes
      # check status of ffmpeg running process  
      # check status of recently saved video files
      # if process is not running or video files are not being saved
      # ping cam to see if it responds 
      # restart the ffmpeg recording process if ping is good
      # log cam restarts, after X failed restarts don't try to keep restarting, instead just restart once every hour
      ffprocs = check_running("ffmpeg")
      log.write("FFMPEG RUNNING PROCESSES:" + str(ffprocs) + "\n")
 

      # TASK #2 - manage the scan and stack processing 

      # TASK #3 - manage the vals detection processing 

      # TASK #4 - manage the meteor verify processing 


      
      ########## ARCHIVE TASKS ###############
      # TASK #1 - manage the indexing and archive syncing processing 
      # run meteor index, run create archive index, run sync wasabi (detects, archive data) 
      # TASK #2 - check for API TASKS (deletes, point updates) and apply 
   
      ########## DISK AND ADMIN TASKS ###############
      # TASK #1 - check and purge disk as needed
      # TASK #2 - check and log time sync info, fix as needed 
      # TASK #3 - do git pulls 
      # TASK #4 - update crontabs as needed 
      # TASK #5 - run apt-gets or pip installs as directed 
       
      ########## CALIBRATION / DATA TUNING ###############
      # TASK #1 - attempt blind solving if the system is not calibrated yet
      # TASK #2 - re-fit meteors in the archive that need it (new caps or caps with high > res)
      # TASK #3 - run re-point-picking on files in archive as needed.

      ########## EVENT DETECTION & SOLVING ###############
      # Check for multi-station events


   # sleep after loops
   time.sleep(5)

def run():
   # before running make sure another daemon process is not already running!
   da_running = check_running("ASDaemon.py")
   if da_running > 1:
      print("AS6Daemon.py is already running! quitting.", da_running)
      exit()
   with daemon.DaemonContext():
      main_thread()

if __name__ == "__main__":
   print("RUN DAM")
   run()
