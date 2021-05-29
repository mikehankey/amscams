from Classes.MeteorNew import Meteor
from Classes.DisplayFrame import DisplayFrame





if __name__ == "__main__":
   import sys
   if len(sys.argv) > 1:
      cmd = sys.argv[1]
   else:
      print("   COMMANDS:")
      print("   1) Scan meteors for 1 day -- will run all detections, calibrations and syncs needed to complete meteor processing.")
      print("   2) Examine meteor -- will load meteor and provide all options / status.")
      cmd = input("Enter the command you want to run. ")
      if cmd == "1":
         cmd = "scan"
      if cmd == "2":
         cmd = "meteor_status"
   if cmd == "scan":
      all_meteor = Meteor()
      meteor_date = input("Enter Date")
      all_meteor.mdir = "/mnt/ams2/meteors/" + meteor_date + "/" 
      all_meteor.get_mfiles(all_meteor.mdir)
      for mfile in all_meteor.mfiles:
         print(mfile)
         mfile = mfile.replace(".mp4", ".json")
         my_meteor = Meteor(meteor_file=all_meteor.mdir + mfile)
         my_meteor.meteor_scan()


   if cmd == "meteor_status":
      meteor_file = input("Enter full path to the meteor json file")
      my_meteor = Meteor(meteor_file=meteor_file)
      my_meteor.meteor_scan()
