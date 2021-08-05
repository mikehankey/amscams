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
   # run the events
   cmd = "python3 EVRun.py " + today
   print(cmd)
   os.system(cmd)
   # run the solver
   cmd = "python3 solveWMPL.py sd " + today
   print(cmd)
   os.system(cmd)
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
   cmd = "python3 EVRun.py " + yest
   print(cmd)
   os.system(cmd)

   #print(cmd)
   #cmd = "python3 EM.py aei " + today
elif date_arg == "yest":
   # run the events
   cmd = "python3 EVRun.py " + yest 
   print(cmd)
   os.system(cmd)
   # run the solver
   cmd = "python3 solveWMPL.py sd " + yest 
   print(cmd)
   os.system(cmd)
   # update the stations

   cmd = "python3 EVStations.py " + yest  
   print(cmd)
   os.system(cmd)
   # update the EM Files 
   cmd = "python3 EM.py aer " + yest 
   print(cmd)
   os.system(cmd)

   cmd = "python3 PLT.py all_rad " + yest 
   print(cmd)
   os.system(cmd)

   # run the events again
   cmd = "python3 EVRun.py " + yest
   print(cmd)
   os.system(cmd)
else:
   # run the events
   cmd = "python3 EVRun.py " + date_arg 
   print(cmd)
   os.system(cmd)
   # run the solver
   cmd = "python3 solveWMPL.py sd " + date_arg 
   print(cmd)
   os.system(cmd)
   # update the stations

   cmd = "python3 EVStations.py " + date_arg 
   print(cmd)
   os.system(cmd)
   # update the EM Files
   cmd = "python3 EM.py aer " + date_arg 
   print(cmd)
   os.system(cmd)

   cmd = "python3 PLT.py all_rad " + date_arg 
   print(cmd)
   os.system(cmd)

   # run the events again
   cmd = "python3 EVRun.py " + date_arg 
   print(cmd)
   os.system(cmd)

if date_arg == 'reindex':
   year = sys.argv[2]
   print("REINDEX " + year)


