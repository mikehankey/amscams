from Classes.AIDB import AllSkyDB
from datetime import datetime 
import datetime as dt
import sys
import os

today = datetime.now()
yest = today - dt.timedelta(days=1)
yest = yest.strftime("%Y_%m_%d")
today = datetime.now().strftime("%Y_%m_%d")

print("\rInit DB Starting",end="")
AIDB = AllSkyDB()
if len(sys.argv) > 1:
   date = sys.argv[1]
else:
   date = today
print("\rDate:" + date, end="")
meteor_dir = "/mnt/ams2/meteors/"
if date == "ALL" or date == "all":
   mdirs = os.listdir(meteor_dir)
   for md in sorted(mdirs,reverse=True):
      if os.path.isdir(meteor_dir + md) is True:
         date = md
         AIDB.load_all_meteors(date)
         AIDB.reconcile_db(date)
   AIDB.check_update_status(date)

else:
   AIDB.load_all_meteors(date)
   AIDB.verify_media_day(date)
   AIDB.reconcile_db(date)

   AIDB.reducer(date)
   AIDB.check_update_status(date)
   #print("\rDONE DAY:" + date + "                                   ",end="" )
