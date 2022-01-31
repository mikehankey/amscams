#!/usr/bin/python3 
import sys
import os
import datetime as dt
from datetime import datetime
today = datetime.now()

now = datetime.now()
yest = today - dt.timedelta(days=1)
yest = yest.strftime("%Y_%m_%d")
today = datetime.now().strftime("%Y_%m_%d")
print(today)
print(yest)
last_45 = []
for i in range (1, 45):
   yest2 = now - dt.timedelta(days=i)
   date = str(yest2)[0:10].replace("-", "_")
   last_45.append(date)

   #os.system("./Process.py hs " + date)

date_arg = sys.argv[1]


if date_arg == "today":
   date_val = today
elif date_arg == "yest":
   date_val = yest 
else:
   date_val = date_arg 


# run the events
cmd = "python3 EVRun.py " + date_val 
print(cmd)
os.system(cmd)

year, month, day = date_val.split("_")
cmd = "bash /mnt/ams2/EVENTS/" + year + "/" + month + "/" + day + "/rsync.jobs"
os.system(cmd)

cmd = "./plot_event_month.py " + date_val 
print(cmd)
os.system(cmd)

year, month, day = date_val.split("_")
os.system("rsync -auv /mnt/ams2/EVENTS/" + year + "/" + month + "/" + day + "/*.json /mnt/archive.allsky.tv/EVENTS/" + year + "/" + month + "/" + day + "/")


exit()
   # run the solver

if False:
   cmd = "python3 solveWMPL.py sd " + today
   print(cmd)
   #os.system(cmd)
   # update the stations

   cmd = "python3 EVStations.py " + today
   print(cmd)
   os.system(cmd)
   # update the EM Files 
   cmd = "python3 EM.py aer " + today
   print(cmd)
   os.system(cmd)

   cmd = "python3 PLT.py all_rad " + today 
   print(cmd)
   os.system(cmd)

   # run the events again
   cmd = "python3 EVRun.py " + today 
   print(cmd)
   os.system(cmd)

   #print(cmd)
   #cmd = "python3 EM.py aei " + today
   os.system(cmd)

