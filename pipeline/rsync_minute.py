#!/usr/bin/python3
"""

Sync an entire minute to the cloud dir for this host.


"""

import os
import argparse
import glob
from lib.PipeUtil import load_json_file, save_json_file
from stackVideo import stack_video

def make_save_index_html(wild_path):
   wild = wild_path.split("/")[-1]
   wild = wild
   path = wild_path.replace(wild, "")
   wild = wild[0:-1]
   print("PATH", path)
   if "SD" in wild_path:
      desc = "<h1>SD MINUTE FILES MATCHING {:s}</h1>".format(wild)
   if "HD" in wild_path:
      desc = "<h1>HD MINUTE FILES MATCHING {:s}</h1>".format(wild)


   files = os.listdir(path)
   page = desc
   for f in files:
      print(wild, f)
      if wild not in f:
         continue
      if "mp4" in f:
         vid_file = f
         stack_file = vid_file.replace(".mp4", "-stacked.jpg")
         thumb_file = vid_file.replace(".mp4", "-stacked-tn.jpg")
         video_link = "<a href={:s}>{:s} Video</a><br>".format(vid_file, f.replace(".mp4", "") )
         thumb = "<a href={:s}><img src={:s}></a><br>{:s}".format(stack_file, thumb_file, video_link)
         page += thumb
   index_file = wild + "_index.html"
   fp = open(path + index_file , "w")
   fp.write(page)
   fp.close()
   print("saved : ", path + index_file)

if __name__ == "__main__":
    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(description="AllSky7 Sync Minute Script")
    jsc = load_json_file("../conf/as6.json")
    station_id = jsc['site']['ams_id']
    # Add arguments
    parser.add_argument("cmd", type=str, help="Command you want to run: minute!")
    parser.add_argument("min_string", type=str, help="Minute string you want to match on")
    parser.add_argument("--cam_id", type=str, help="Optional Cam ID")
    parser.add_argument("--daytime", type=float, help="Set to 1 if the event occured in the daytime")
    parser.add_argument("--auto", type=float, help="Auto yes to all prompts (for crons)")
    parser.add_argument("--stack", type=int, help="Include full stacks of the images [0 or 1] default 1", default=1)
    parser.add_argument("--sd", type=int, help="Include sd files [0 or 1] default 1", default=1)
    parser.add_argument("--hd", type=int, help="Include hd files [0 or 1] default 1", default=1)
    parser.add_argument("--html", type=int, help="Make index.html in media folders [0 or 1] default 1", default=1)

    # Parse the arguments
    args = parser.parse_args()

    # deal with uploading minute files
    if args.cmd == "min":
       date_data = args.min_string.split("_")
       date = date_data[0] + "_" + date_data[1] + "_" + date_data[2]
       if args.cam_id is not None:
          hd_path = "/mnt/ams2/HD/" + args.min_string + "*" + args.cam_id + "*"
       else:
          hd_path = "/mnt/ams2/HD/" + args.min_string + "*" 

       if args.daytime is not None:
          if args.cam_id is None:
             sd_path = "/mnt/ams2/SD/proc2/daytime/" + date + "/" + args.min_string + "*" 
          else:
             sd_path = "/mnt/ams2/SD/proc2/daytime/" + date + "/" + args.min_string + "*" + args.cam_id + "*"
       else:
          if args.cam_id is None:
             sd_path = "/mnt/ams2/SD/proc2/" + date + "/" + args.min_string + "*" 
          else:
             sd_path = "/mnt/ams2/SD/proc2/" + date + "/" + args.min_string + "*" + args.cam_id + "*"

       if args.stack == 1:
          # stack sd files if not done already
          if args.sd == 1:
             vid_files = glob.glob(sd_path + "*.mp4")
             for vid in vid_files:
                sf = vid.replace(".mp4", "-stacked.jpg")
                if os.path.exists(sf) is False:
                   result = stack_video(vid)
                   print("STACKED VIDEO:", result)
          if args.hd == 1:
             # stack hd files if not done already
             vid_files = glob.glob(hd_path + "*.mp4")
             for vid in vid_files:
                sf = vid.replace(".mp4", "-stacked.jpg")
                if os.path.exists(sf) is False:
                   result = stack_video(vid)
                   print("STACKED VIDEO:", result)

       if args.html == 1:
          # make and save html for sd & hd folders
          make_save_index_html(sd_path)
          make_save_index_html(hd_path)

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
          print(cmd1)
          os.system(cmd1)
          print(cmd2)
          os.system(cmd2)
          if args.hd == 1:
             print(cmd3)
             os.system(cmd3)
          if args.sd == 1:
             print(cmd4)
             os.system(cmd4)
