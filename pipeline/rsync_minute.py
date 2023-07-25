#!/usr/bin/python3
"""

Sync an entire minute to the cloud dir for this host.


"""

import os
import argparse
from lib.PipeUtil import load_json_file, save_json_file


if __name__ == "__main__":
    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(description="AllSky7 Sync Minute Script")
    jsc = load_json_file("../conf/as6.json")
    station_id = jsc['site']['ams_id']
    # Add arguments
    parser.add_argument("cmd", type=str, help="Command you want to run: minute!")
    parser.add_argument("min_string", type=str, help="Minute string you want to match on")
    parser.add_argument("--cam_id", type=float, help="Optional Cam ID")
    parser.add_argument("--daytime", type=float, help="Set to 1 if the event occured in the daytime")
    parser.add_argument("--auto", type=float, help="Auto yes to all prompts (for crons)")

    # Parse the arguments
    args = parser.parse_args()

    # Calculate the area
    if args.cmd == "min":
       date_data = args.min_string.split("_")
       date = date_data[0] + "_" + date_data[1] + "_" + date_data[2]
       if args.cam_id is not None:
          hd_path = "/mnt/ams2/" + args.min_string + "*" + args.cam_id + "*"
       else:
          hd_path = "/mnt/ams2/" + args.min_string + "*" 
       if args.daytime is not None:
          if args.cam_id is None:
             sd_path = "/mnt/ams2/SD/proc2/daytime/" + date + "/" + args.min_string + "*" 
          else:
             sd_path = "/mnt/ams2/SD/proc2/daytime/" + date + "/" + args.min_string + "*" + args.cam_id + "*"
    cmd1 = "mkdir -p /mnt/archive.allsky.tv/" + station_id + "/MIN_FILES/" + date + "/HD/" 
    cmd2 = "mkdir -p /mnt/archive.allsky.tv/" + station_id + "/MIN_FILES/" + date + "/SD/" 
    cmd3 = "rsync -auv " + hd_path + " /mnt/archive.allsky.tv/" + station_id + "/MIN_FILES/" + date + "/HD/" 
    cmd4 = "rsync -auv " + sd_path + " /mnt/archive.allsky.tv/" + station_id + "/MIN_FILES/" + date + "/SD/" 
    print(cmd1)
    print(cmd2)
    print(cmd3)
    print(cmd4)
    print(args.auto)
    if args.auto is None:
       confirm = input("Do you want to run these commands?")
       if confirm == "y" or confirm == "Y" or confirm == "yes":
          print("running commands")
          os.system(cmd1)
          os.system(cmd2)
          os.system(cmd3)
          os.system(cmd4)
