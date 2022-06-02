from Classes.AllSkyNetwork import AllSkyNetwork
import os
import sys
import datetime as dt
from datetime import datetime

cmd = sys.argv[1]

ASN = AllSkyNetwork()
now = datetime.now()
yest = now - dt.timedelta(days=1)
yest = yest.strftime("%Y_%m_%d")
today = datetime.now().strftime("%Y_%m_%d")

if len(sys.argv) < 1:
   ASN.help()
   exit()

if cmd == "refresh_day":
   force = 0
   event_day = sys.argv[2]
   ASN.set_dates(event_day)
   ASN.day_solve(event_day,force)
   ASN.day_load_solves(event_day)
   ASN.publish_day(event_day)

if cmd == "update_meteor_days":
   ASN.update_meteor_days()

if cmd == "help":
   print("CMD:", cmd)
   ASN.help()

if cmd == "day_load_solves":
   event_day = sys.argv[2]
   ASN.help()
   ASN.set_dates(event_day)
   ASN.day_load_solves(event_day)

if cmd == "plane_test_day":
   print("CMD:", cmd)
   event_day = sys.argv[2]
   ASN.help()
   ASN.set_dates(event_day)
   ASN.plane_test_day(event_day)

if cmd == "report":
   print("CMD:", cmd)
   event_day = sys.argv[2]
   ASN.help()
   ASN.set_dates(event_day)
   ASN.quick_report(event_day)

if cmd == "rsync_data":
   print("CMD:", cmd)
   event_day = sys.argv[2]
   date = event_day
   ASN.help()
   ASN.set_dates(date)
   ASN.rsync_data_only(event_day)

if cmd == "resolve_failed_day" or cmd == "rerun_failed":
   ASN.help()
   ASN.set_dates(sys.argv[2])
   event_day = sys.argv[2].replace("_", "")
   event_day = event_day.replace("-", "")
   event_day = event_day.replace("/", "")
   ASN.resolve_failed_day(event_day)

if cmd == "resolve_event":
   ASN.help()
   ASN.resolve_event(sys.argv[2])

if cmd == "publish_day":
   event_day = sys.argv[2]
   ASN.help()
   ASN.publish_day(event_day)

if cmd == "publish_event":
   event_day = sys.argv[2]
   ASN.help()
   force = 0
   ASN.publish_event(event_id)



if cmd == "day_solve":
   event_day = sys.argv[2]
   ASN.help()
   ASN.set_dates(event_day)
   force = 0
   ASN.day_solve(event_day,force)

if cmd == "validate_events":
   event_day = sys.argv[2]
   ASN.help()
   ASN.set_dates(event_day)
   force = 0
   ASN.validate_events(event_day)



if cmd == "load_day_sql":
   force = 0
   ASN.help()
   date = sys.argv[2]
   if date == "today":
      date = today
   if date == "yest":
      date = yest 
   ASN.day_load_sql(date, force)
   print("Done load")


if cmd == "coin_events":
   event_day = sys.argv[2]
   ASN.help()
   ASN.set_dates(event_day)
   force = 0
   ASN.day_coin_events(event_day,force)


if cmd == "day_load_solve_results":
   ASN.help()
   ASN.day_load_solve_results(sys.argv[2])

if cmd == "do_all":
   ASN.help()
   if len(sys.argv) == 4:
      force = 1
   else:
      force = 0
   date = sys.argv[2]
   if date == "today":
      date = today
   if date == "yest":
      date = yest 

   # don't load every time, this call takes a while!
   # this should be handled in set_dates! need to test/confirm though
   # this should be done on the AWS side and the gz file is all that should be 
   # downloaded. However, this is not always the case!
   #os.system("./DynaDB.py udc " + date)

   force = 1

   ASN.day_load_sql(date, force)
   print("Done load")
   ASN.day_coin_events(date,force)
   print("Done coin")
   ASN.day_solve(date,force)

   ASN.day_load_solves(date)

   ASN.plane_test_day(date)

   print("Done solve")
   ASN.rsync_data_only(date)
   ASN.publish_day(date)


if cmd == "day_solve" or cmd == 'ds' or cmd == "solve_day":
   ASN.help()
   force = 0
   date = sys.argv[2]
   if date == "today":
      date = today
   if date == "yest":
      date = yest 
   ASN.day_solve(date,force)
   print("Done solve")

if cmd == "sync_dyna_day":
   ASN.help()
   date = sys.argv[2]
   ASN.sync_dyna_day(date)

if cmd == "check_event_status" or cmd == 'ces':
   ASN.help()
   event_id = sys.argv[2]
   ASN.check_event_status(event_id)
if cmd == "status":
   if len(sys.argv) < 2:
      print("No date provided!")
      print("USAGE: ./AllSkyNetwork status [YYYY_MM_DD]")
   event_day = sys.argv[2]
   ASN.help()
   ASN.set_dates(event_day)
   ASN.update_all_event_status(sys.argv[2])
   ASN.day_status(sys.argv[2])
