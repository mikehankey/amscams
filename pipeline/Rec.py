from Classes.Reconcile import Reconcile
import sys


if __name__ == "__main__":
   print(len(sys.argv))
   if len(sys.argv) == 2:
      year = sys.argv[1]
      R = Reconcile(year)
   if len(sys.argv) == 3:
      year = sys.argv[1]
      mon = sys.argv[2]
      print("FF:", year, mon)
      R = Reconcile(year, mon)
   #R.reconcile_report(year,mon)

   R.reconcile_cloud_media(year, mon)
   R.update_cloud_index(year, mon)
   R.reconcile_media()
   R.reconcile_cloud_media(year, mon)
   R.save_rec_data()
