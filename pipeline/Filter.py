from Classes.Filters import Filters 
import sys


if __name__ == "__main__":
   if len(sys.argv) == 3:
      cmd = sys.argv[1]
      day = sys.argv[2]
      F = Filters()
      if cmd == "fd":
         F.check_day(day)
      if cmd == "fm":
         print("FILTER MONTH", day)
         F.filter_month(day)
