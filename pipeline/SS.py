
from Classes.StationSync import StationSync

if __name__ == "__main__":
   import sys
   print(sys.argv)

   if len(sys.argv) < 3:
      print("You need at least 2 args [CMD] [YYYY_MM_DD]. ")
   else:
      el = sys.argv[2].split("_")
      if len(el) == 3:
         SS = StationSync(cmd=sys.argv[1], day=sys.argv[2])
      if len(el) == 2:
         SS = StationSync(cmd=sys.argv[1], month=sys.argv[2])
      if len(el) == 1:
         SS = StationSync(cmd=sys.argv[1], year=sys.argv[2])
      SS.controller()



   #cmd = "./Process.py remaster_day " + day
   #print(cmd)
   #os.system(cmd)
