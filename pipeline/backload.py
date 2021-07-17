#!/usr/bin/python3

# script to re-run back events and remake the event cache files in the wasabi dir
import sys  
import os
from datetime import datetime
from calendar import monthrange
import datetime as dt
import glob
from lib.PipeUtil import cfe

start_year = sys.argv[1]

mdays = glob.glob("/mnt/ams2/meteors/" + start_year + "*")
all_days = []
for mday in mdays:
   if cfe(mday, 1) == 1:
      md = mday.split("/")[-1]
      all_days.append(md)

for day in sorted(all_days,reverse=True):
   rec = "python3 Rec.py rec_day " + day 
   print(rec)
   os.system(rec)
