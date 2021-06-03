from Classes.Meteor import Meteor
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
   if cmd == "meteor_status":
      meteor_file = input("Enter full path to the meteor json file") 
      my_meteor = Meteor(meteor_file=meteor_file)
      my_meteor.meteor_status()
      my_meteor.meteor_scan()


   if cmd == "scan":
      if len(sys.argv) >= 3:
         day = sys.argv[2]
      else:
         day = input("Enter the day you want to scan (YYYY_MM_DD): ")
      meteors = glob.glob("/mnt/ams2/meteors/" + day + "/*.json")

      #for testing
      #meteors = ['/mnt/ams2/meteors/2021_03_23/2021_03_23_04_13_00_000_010001-trim-0096.json']

      for meteor_file in meteors:

         if "reduced" not in meteor_file:
            mj = load_json_file(meteor_file)
            if "meteor_scan_info" in mj:
               if "sd_objects" in mj['meteor_scan_info']:
                  print("METEOR SCAN DONE", len(mj['meteor_scan_info']['sd_objects']), " total objects")
               else:
                  print("no SD objects found in meteor scan data:", meteor_file)
                  for key in mj['meteor_scan_info']:
                     print(key)
                     for skey in mj['meteor_scan_info'][key]:
                        print(skey, mj['meteor_scan_info'][key][skey])

               if mj['meteor_scan_info'] == 0:
                  print(" STATUS: NO METEORS FOUND")
                  #continue
            if "crop_scan" in mj:
               print("CROP SCAN DONE:")
               print("    STATUS:", mj['crop_scan']['status'], mj['crop_scan']['desc'])
               #continue
            print(meteor_file)
            my_meteor = Meteor(meteor_file=meteor_file)
            print("My Meteor:", my_meteor.sd_vid)
            go = 1
            if "sd_objects" not in my_meteor.meteor_scan_info:
               go = 1

            if my_meteor.meteor_scan_info is None or go == 1:
               my_meteor.meteor_scan()
            #   my_meteor.save_meteor_files()
            #   my_meteor.make_cache_files()
            #if my_meteor.best_meteor is not None and "crop_scan" not in my_meteor.meteor_scan_info :
            #   my_meteor.meteor_scan_crop()
            #my_meteor.report_objects(my_meteor.sd_objects)
      print("FINISHED THE SCAN FOR ", day)

