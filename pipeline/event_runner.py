#!/usr/bin/python3
import os
pref = "2021_03"
start = 1
end = 24
for day in range(start, end):
   if day < 10:
      sday = "0" + str(day)
   else:
      sday = str(day)
   cmd = "./solveWMPL.py sd " + pref + "_" + sday
   print(cmd)
   os.system(cmd)
