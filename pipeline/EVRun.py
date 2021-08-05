import datetime
from decimal import Decimal
import Classes.Events
from Classes.Events import Events
from Classes.EventRunner import EventRunner 
import sys

if __name__ == "__main__":
   import sys
   if sys.argv[1] == "today":
      sys.argv[1] = datetime.datetime.today().strftime('%Y_%m_%d')
   if sys.argv[1] == "yest":
      yest = datetime.datetime.today() - datetime.timedelta(days=1)
      yest = yest.strftime('%Y_%m_%d')
      sys.argv[1] = yest 
   print(sys.argv[1])

   EV = Events()
   EVR = EventRunner(date=sys.argv[1],use_cache=0)

   if len(sys.argv) > 2:
      if sys.argv[2] == "EOD":
         EVR.EOD_report(sys.argv[1])
         exit()

   print("LIST EVENTS")
   EVR.list_events_for_day()
   print("UPDATE EVENTS")
   EVR.update_events_for_day()
   print("EOD REPORT ")
   EVR.update_station_event_ids(sys.argv[1])
   EV.make_missing_data_list()
   EVR.EOD_report(sys.argv[1])
