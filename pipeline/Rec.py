from Classes.Reconcile import Reconcile
from Classes.SyncAWS import SyncAWS
import sys
import os
from lib.PipeUtil import load_json_file, save_json_file, cfe
json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']
api_key = json_conf['site']['api_key']

if __name__ == "__main__":
   os.system("python3 Register.py")
   print(len(sys.argv))
   cmd = sys.argv[1]

   if cmd == "index_all_meteors_aws":
      # function to reconcile deletes and file indexes between AWS and local station
      R = Reconcile()
      #R.get_cloud_media()
      #exit()
      R.index_all_meteors_aws()
      
   if cmd == "rec_media":

      year = sys.argv[2]
      mon = sys.argv[3]
      R = Reconcile(year,mon)
      R.rec_media(year,mon)
      exit()
      

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


   if cmd == "del_aws_all":
      date = sys.argv[2]
      year, mon, day = date.split("_")
      R = Reconcile(year, mon)
      R.reconcile_all_aws_obs()
   if cmd == "del_aws_day":
      js_conf = load_json_file("../conf/as6.json")
      station_id = js_conf['site']['ams_id']
      #os.system("./Process.py purge_meteors")
      date = sys.argv[2]
      year, mon, day = date.split("_")
      #R = Reconcile(year, mon)
      os.system("./Process.py purge_meteors")
      SAWS = SyncAWS(station_id, api_key)
      SAWS.delete_aws_meteors(date)

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
      os.system("./Process.py purge_meteors")
      os.system("python3 ./Filter.py fd " + year + "_" + mon)
      R = Reconcile(year, mon)
      os.system("./Process.py purge_meteors")
      SAWS = SyncAWS(R.station_id, api_key)
      SAWS.delete_aws_meteors(date)
      os.system("python3 Meteor.py 8 " + sys.argv[2])
      os.system("python3 Meteor.py 1 " + sys.argv[2])
      os.system("python3 Meteor.py 8 " + sys.argv[2])
      os.system("python3 AWS.py push_day " + sys.argv[2])
      #R.reconcile_day(sys.argv[2])
      #os.system("python3 AWS.py sd " + sys.argv[2])

