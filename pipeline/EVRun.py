import Classes.Events
from Classes.Events import Events
from Classes.EventRunner import EventRunner 
import sys

if __name__ == "__main__":
   import sys
   EVR = EventRunner(date=sys.argv[1])
   EVR.list_events_for_day()

   EVR.update_events_for_day()
   #EV.make_missing_data_list()
