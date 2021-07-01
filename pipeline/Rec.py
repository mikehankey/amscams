from Classes.Reconcile import Reconcile
import sys
import os

if __name__ == "__main__":
   print(len(sys.argv))
   cmd = sys.argv[1]
   if cmd == "rec":
      year = sys.argv[2]
      mon = sys.argv[3]
      print("FF:", year, mon)
      R = Reconcile(year, mon)
      os.system("./Process.py purge_meteors")
      os.system("python3 ./Filter.py fm " + year + "_" + mon)
      R.fix_missing_cloud_files(year,mon)
      #R.reconcile_cloud_media(year, mon)
      R.update_cloud_index(year, mon)
      R.reconcile_media()
      #R.reconcile_cloud_media(year, mon)
      R.save_rec_data()
      R.fix_missing_cloud_files(year,mon)
      os.system("python3 AWS.py sm " + year + "_" + mon)



