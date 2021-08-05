#!/usr/bin/python3
import time
import os
from lib.PipeUtil import load_json_file, check_running

local_unsolved ="/mnt/ams2/EVENTS/ALL_EVENTS_INDEX_UNSOLVED.json"
cloud_unsolved ="/mnt/archive.allsky.tv/EVENTS/ALL_EVENTS_INDEX_UNSOLVED.json"

cmd = "cp " + cloud_unsolved + " " + local_unsolved
os.system(cmd)


running = check_running("solveWMPL.py")
print("RUNNING:", running)


events = load_json_file(local_unsolved)
events = sorted(events, key=lambda x: (x['id']), reverse=True)
for ev in events:
   id =ev['id']
   running = check_running("solveWMPL.py")
   while(running > 5):
      time.sleep(30)
      running = check_running("solveWMPL.py")

   cmd = "./solveWMPL.py se " + id + " &"

   print(cmd)
   os.system(cmd)

