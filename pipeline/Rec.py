from Classes.Reconcile import Reconcile
from Classes.SyncAWS import SyncAWS
import sys
import os
from lib.PipeUtil import load_json_file, save_json_file, cfe
json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']
api_key = json_conf['site']['api_key']

if __name__ == "__main__":
   print(len(sys.argv))
   cmd = sys.argv[1]
   if cmd == "rec":
      year = sys.argv[2]
      mon = sys.argv[3]
      print("FF:", year, mon)
      R = Reconcile(year, mon)
      # delete all of the AWS meteors of ALL time that don't exist on system
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


   if cmd == "del_aws":
      R = Reconcile(year, mon)
      R.reconcile_all_aws_obs()
   if cmd == "rpt":
      year = sys.argv[2]
      mon = sys.argv[3]
      print("REPORT!", year,mon)
      R = Reconcile(year, mon)
      #R = Reconcile()
      R.rec_report()

   if cmd == "rec_day":
      date = sys.argv[2]
      year, mon, day = sys.argv[2].split("_")
      R = Reconcile(year, mon)

      SAWS = SyncAWS(R.station_id, api_key)
      SAWS.delete_aws_meteors(date)
      os.system("python3 Meteor.py 8 " + sys.argv[2])
      os.system("python3 Meteor.py 1 " + sys.argv[2])
      os.system("python3 Meteor.py 8 " + sys.argv[2])
      os.system("python3 AWS.py push_day " + sys.argv[2])
      #R.reconcile_day(sys.argv[2])
      #os.system("python3 AWS.py sd " + sys.argv[2])

