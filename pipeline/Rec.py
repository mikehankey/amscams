from Classes.Reconcile import Reconcile
import sys


R = Reconcile()
if __name__ == "__main__":
   if len(sys.argv) == 2:
      year = sys.argv[1]
      R = Reconcile(year)
   if len(sys.argv) == 3:
      year = sys.argv[1]
      mon = sys.argv[2]
      R = Reconcile(year, mon)

   R.reconcile_media()
