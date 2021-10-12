import datetime
from decimal import Decimal
from Classes.EventReport import EventReport
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

   ER = EventReport(date=sys.argv[1],use_cache=0)
   ER.evaluate_event_planes()
   exit()
   ER.report_minutes()
   ER.report_events()
   ER.kml_event_report()

   #ER.ops_report()
