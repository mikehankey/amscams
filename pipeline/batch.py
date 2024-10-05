#!/usr/bin/python3

import os
import datetime as dt
from datetime import datetime
today = datetime.now()
for i in range (1, 30):
   yest = today - dt.timedelta(days=i)
   date = str(yest)[0:10].replace("-", "_")
   print(date)
   #cmd = "./AllSkyNetwork.py do_all " + date

   cmd = "python PLT.py all_rad " + date
   os.system(cmd)
   cmd = "./AllSkyNetwork.py publish_day " + date
   os.system(cmd)
