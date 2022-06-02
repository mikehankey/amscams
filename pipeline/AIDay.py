from Classes.AIDB import AllSkyDB
from Classes.ASAI import AllSkyAI 
from datetime import datetime 
import datetime as dt
import sys
import os

#from Classes.ReviewNetwork import ReviewNetwork

today = datetime.now()
yest = today - dt.timedelta(days=1)
yest = yest.strftime("%Y_%m_%d")
today = datetime.now().strftime("%Y_%m_%d")

print("Init DB Starting.")
AIDB = AllSkyDB()
print("Init DB Started.")


if len(sys.argv) > 2:
   cmd = sys.argv[2]
   if cmd == "load_all":
      AIDB.load_all_meteors()
      exit()
   if cmd == "nm_report":
      AIDB.non_meteor_report()
      exit()
   if cmd == "purge":
      date = sys.argv[1]
      AIDB.purge()
      exit()


   if cmd == "report":
      date = sys.argv[1]
      AIDB.report_day(date)
      exit()
   if cmd == "reject":
      date = sys.argv[1]
      #AIDB.mc_rejects()
      #print("DONE MC REJECTS.")
      #exit()

      #RN = ReviewNetwork(date)
      AIDB.auto_reject_day(date )
      exit()


AIDB.load_stations()
#exit()

if len(sys.argv) > 1:
   date = sys.argv[1]
else:
   date = today

if date == "today":
   date = today
if date == "yest":
   date = yest 
meteor_dir = "/mnt/ams2/meteors/"
if date == "ALL" or date == "all":
   mdirs = os.listdir(meteor_dir)
   for md in sorted(mdirs,reverse=True):

      if os.path.isdir(meteor_dir + md) is True:
         #RN = ReviewNetwork(md)

         #if os.path.exists(RN.learning_repo + md + "/METEOR/") is False:
         #   os.makedirs(RN.learning_repo + md + "/METEOR/")
         #if os.path.exists(RN.learning_repo + md + "/NON_METEOR/") is False:
         #   os.makedirs(RN.learning_repo + md + "/NON_METEOR/")
         #if os.path.exists(RN.learning_repo + md + "/UNSURE/") is False:
         #   os.makedirs(RN.learning_repo + md + "/UNSURE/")
         ai_file = meteor_dir + md + "/" + AIDB.station_id + "_" + md + "_AI_DATA.info"
         print("AIFILE:", ai_file)
         #exit()
         if os.path.exists(ai_file) and date != today and date != yest:
            print("AI DONE FOR THIS DAY ALREADY!")
            continue 
         date = md
         AIDB.load_all_meteors(date)
         AIDB.verify_media_day(date)
         AIDB.reconcile_db(date)
         os.system("/usr/bin/python3.6 myEvents.py " + date)

         #RN = ReviewNetwork(date)

         AIDB.auto_reject_day(date )
         print("DONE AIDay FOR " + date)
         os.system("/usr/bin/python3 Rec.py del_aws_day " + md)
         #AIDB.check_update_status(date)

else:

   #RN = ReviewNetwork(date)
   #if os.path.exists(RN.learning_repo + date + "/METEOR/") is False:
   #   os.makedirs(RN.learning_repo + date + "/METEOR/")
   #if os.path.exists(RN.learning_repo + date + "/NON_METEOR/") is False:
   #   os.makedirs(RN.learning_repo + date + "/NON_METEOR/")
   #if os.path.exists(RN.learning_repo + date + "/UNSURE/") is False:
   #   os.makedirs(RN.learning_repo + date + "/UNSURE/")
   print("Load day", date)
   AIDB.load_all_meteors(date)
   print("Verify Media", date)
   AIDB.verify_media_day(date)
   print("Reconcile DB", date)
   AIDB.reconcile_db(date)
   print("My Events", date)
   os.system("/usr/bin/python3.6 myEvents.py " + date)
   print("Auto reject day")
   AIDB.auto_reject_day(date )

   print("Del Aws", date)
   os.system("/usr/bin/python3 Rec.py del_aws_day " + date)
   print("DONE AIDay FOR " + date)
   print("Reducer", date)
   AIDB.reducer(date)
   #AIDB.check_update_status(date)
