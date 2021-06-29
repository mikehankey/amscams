from Classes.Reconcile import Reconcile
import sys


if __name__ == "__main__":
   print(len(sys.argv))
   cmd = sys.argv[1]
   if cmd == "rec":
      year = sys.argv[2]
      mon = sys.argv[3]
      print("FF:", year, mon)
      R = Reconcile(year, mon)
      R.fix_missing_cloud_files(year,mon)
      exit()
      R.reconcile_cloud_media(year, mon)
      R.update_cloud_index(year, mon)
      R.reconcile_media()
      R.reconcile_cloud_media(year, mon)
      R.save_rec_data()



