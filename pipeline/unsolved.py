#!/usr/bin/python3
import time
import os
from lib.PipeUtil import load_json_file, check_running

local_unsolved ="/mnt/ams2/EVENTS/UNSOLVED_IDS.json"
cloud_unsolved ="/mnt/archive.allsky.tv/EVENTS/UNSOLVED_IDS.json"

cmd = "cp " + cloud_unsolved + " " + local_unsolved
os.system(cmd)


running = check_running("solveWMPL.py")
print("RUNNING:", running)


events = load_json_file(local_unsolved)
for eid in sorted(events, reverse=True):
   running = check_running("solveWMPL.py")
   while(running > 5):
      time.sleep(30)
      running = check_running("solveWMPL.py")

   cmd = "./solveWMPL.py se " + eid + " &"

   print(cmd)
   #os.system(cmd)

