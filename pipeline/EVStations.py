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
   #EVR = EventRunner()
   #EVR.make_vida_plots(date)
   #EVR.update_events_index_day(date)
   #EVR.update_station_event_ids(date)
   #EVR.make_all_obs_index(date)
   #EVR.update_all_events_index()
   #exit()

   EVR = EventRunner()
   EVR.station_kml_for_day(date)
   exit()
   EVR.make_all_obs_index(date)

   EVR.make_vida_plots(date)
   #EVR.update_all_events_index()
   #EVR.all_event_stats()
   #EVR.update_all_stations_events()
   #EVR.all_event_stats()

