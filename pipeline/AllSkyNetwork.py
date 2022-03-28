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

if cmd == "help":
   print("CMD:", cmd)
   ASN.help()

if cmd == "resolve_failed_day":
   ASN.help()
   event_day = sys.argv[2].replace("_", "")
   event_day = event_day.replace("-", "")
   event_day = event_day.replace("/", "")
   ASN.resolve_failed_day(event_day)

if cmd == "resolve_event":
   ASN.help()
   ASN.resolve_event(sys.argv[2])


if cmd == "coin_events":
   event_day = sys.argv[2]
   ASN.help()
   ASN.set_dates(event_day)
   force = 0
   ASN.day_coin_events(event_day,force)

if cmd == "day_load_solve_results":
   ASN.help()
   ASN.day_load_solve_results(sys.argv[2])

if cmd == "day_load_sql":
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

   os.system("./DynaDB.py udc " + date)

   ASN.day_load_sql(date, force)
   print("Done load")
   ASN.day_coin_events(date,force)
   print("Done coin")
   ASN.day_solve(date,force)
   print("Done solve")


if cmd == "day_solve" or cmd == 'ds':
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

   ASN.help()
   ASN.day_status(sys.argv[2])
