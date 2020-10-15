#!/usr/bin/python3

import os
import datetime as dt
from datetime import datetime
today = datetime.now()
for i in range (1, 45):
   yest = today - dt.timedelta(days=i)
   date = str(yest)[0:10].replace("-", "_")
   print(date)
   os.system("./Process.py hs " + date)
#   os.system("./Process.py ar " + date)
