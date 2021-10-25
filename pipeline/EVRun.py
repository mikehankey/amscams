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
      if sys.argv[2] == "kml":
         EVR.kml_plane_pairs()

      if sys.argv[2] == "quick":
         print("QUICK REPORT")
         EVR.quick_report(sys.argv[1])
         exit()


   if len(sys.argv) > 2:
      if sys.argv[2] == "EOD":
         EVR.EOD_report(sys.argv[1])
         exit()

   #EVR.del_bad_obs_from_events(sys.argv[1])
   #print("LIST EVENTS")

   # EVENT LOGIC!
   """
      1) Make the OBS by minute file from ALL OBS for a given day (should use ALL_OBS_KEYS file currently does not exist) * Make this on AWS server 1x per hour or something...
      2) From OBS by minute create the event_groups file
      3) From event groups file run the planes check and make ALL_PLANES FILE
      4) From the ALL_PLANES file create 'official' event IDs and event Files
      5) For each Event ID run the solver
      6) Once all events have been solved make the summary reports

   """
  # EVR.sync_event_dir()
  # exit()
   #EVR.EOD_summary()
   #exit()
   EVR.plane_station_stats()
   exit()
   EVR.coin_events()
   EVR.coin_solve()
   EVR.run_solve_jobs()
   EVR.make_events_file_from_coin()
   EVR.sync_event_dir()
   EVR.load_dyna_events()
   print("FINISH SOLVE FOR DAY", sys.argv[1]) 

   #EVR.obs_by_minute()
   exit()
   EVR.list_events_for_day()
   input("Wait")
   print("UPDATE EVENTS")
   EVR.update_events_for_day()

   print("EOD REPORT ")
   EVR.update_station_event_ids(sys.argv[1])
   EV.make_missing_data_list()
   EVR.EOD_report(sys.argv[1])
