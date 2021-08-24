from Classes.Filters import Filters 
import sys
import glob
from lib.PipeUtil import cfe

def all_bad(F):
   print("Check for bad days!")
   mdirs = glob.glob("/mnt/ams2/meteors/*")
   for mdir in sorted(mdirs, reverse=True):
      if cfe(mdir,1) == 1:
         all_files = get_files(mdir )
         if len(all_files) > 50:
            print("SHOULD WE FILTER?", mdir, len(all_files))
            input

def get_files(mdir):
   temp = glob.glob(mdir + "/*.json")
   af = []
   for f in temp:
      if "import" not in f and "report" not in f and "reduced" not in f and "calparams" not in f and "manual" not in f and "starmerge" not in f and "master" not in f:
         af.append(f)
   return(af)

if __name__ == "__main__":
   if len(sys.argv) == 3:
      cmd = sys.argv[1]
      day = sys.argv[2]
      F = Filters()
      if cmd == "all_bad":
         all_bad(F )

      if cmd == "fd":
         F.check_day(day)
      if cmd == "fm":
         print("FILTER MONTH", day)
         F.filter_month(day)
