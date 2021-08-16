import datetime
#import Classes.Events
from Classes.Events import Events
from Classes.EventRunner import EventRunner
import sys
import sys
if __name__ == "__main__":
   import sys
   if len(sys.argv) > 1:
      date = sys.argv[1]
   else:
      date = None
   EVR = EventRunner(date=date)
   #EVR.station_kml_for_day(date)
   EVR.make_all_obs_index(date)
   EVR.make_vida_plots(date)
   #EVR.update_all_events_index()
   #EVR.all_event_stats()
   #EVR.update_all_stations_events()

