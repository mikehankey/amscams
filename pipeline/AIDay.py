from Classes.AIDB import AllSkyDB
import sys
import os

print("Init DB Starting")
AIDB = AllSkyDB()
print("Init DB Complete")

date = sys.argv[1]
meteor_dir = "/mnt/ams2/meteors/"
if date == "ALL":
   mdirs = os.listdir(meteor_dir)
   for md in sorted(mdirs,reverse=True):
      if os.path.isdir(meteor_dir + md) is True:
         print("DO THE DAY!")
         date = md
         AIDB.load_all_meteors(date)
         AIDB.reconcile_db(date)
   AIDB.check_update_status(date)

else:
   print("Load")
   AIDB.load_all_meteors(date)

   AIDB.verify_media_day(date)
   AIDB.reconcile_db(date)

   # print("Update")
   # print("Reconcile")
   AIDB.check_update_status(date)
