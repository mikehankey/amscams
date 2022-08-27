from Classes.EventManager import EventManager
import sys

if __name__ == "__main__":
   import sys
   # command then date or partial date
   # aer = all event report -- makes ALL_RADIANTS file and others

   if len(sys.argv) < 3:
      print("You need at least 2 args [CMD] [YYYY_MM_DD]. ")
   else:
      el = sys.argv[2].split("_")
      if len(el) == 3:
         EM = EventManager(cmd=sys.argv[1], day=sys.argv[2])
      if len(el) == 2:
         EM = EventManager(cmd=sys.argv[1], month=sys.argv[2])
      if len(el) == 1:
         print("YEAR:", sys.argv[2])
         EM = EventManager(cmd=sys.argv[1], year=sys.argv[2])
      EM.controller()
