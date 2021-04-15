
import Classes.Events 
from Classes.Events import Events
import sys

if __name__ == "__main__":
   import sys
   fv = {}
   fv['stations'] = None
   fv['solve_status'] = None
   fv['start_date'] = None
   fv['end_date'] = None
   fv['stations'] = None
   EV = Events(fv)
   EV.load_events()
   EV.status()
   #EV.make_missing_data_list()
