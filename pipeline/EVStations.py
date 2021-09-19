import datetime
import os
#import Classes.Events
from Classes.Events import Events
from Classes.EventRunner import EventRunner
from Classes.UserReview import UserReview 
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
   if sys.argv[1] == "all_time":
      EVR.make_alltime_obs_index()
      os.system("./best_meteors.py")
      exit()
   if sys.argv[1] == "purge":
      EVR.purge_dead_meteors()
      exit()
   if sys.argv[1] == "unsolved":
      EVR.make_unsolved_list()
   EVR.all_stations_kml()
   #exit()
   EVR.aws_stats()
   UR = UserReview()
   UR.process_reviews_for_day(date)
   #exit()
   EVR.station_kml_for_day(date)
   EVR.make_all_obs_index(date)
   
   #EVR.make_vida_plots(date)
   #EVR.update_all_events_index()
   #EVR.all_event_stats()
   #EVR.update_all_stations_events()

