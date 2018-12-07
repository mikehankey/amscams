#!/usr/bin/python3

import json
import sys
import os
import glob
import datetime


json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)


sd_video_dir = json_conf['site']['sd_video_dir']
hd_video_dir = json_conf['site']['hd_video_dir']
proc_dir = json_conf['site']['proc_dir']

def ffmpeg_cat (file1, file2, outfile):
   cat_file = "/tmp/cat_files.txt"
   fp = open(cat_file, "w")
   fp.write("file '" + file1 + "'\n")
   fp.write("file '" + file2 + "'\n")
   fp.close()
   cmd = "ffmpeg -y -f concat -safe 0 -i " + cat_file + " -c copy " + outfile
   print(cmd)
   os.system(cmd)


def convert_filename_to_date_cam(file):
   el = file.split("/")
   filename = el[-1]
   filename = filename.replace(".mp4" ,"")
   fy,fm,fd,fh,fmin,fs,fms,cam = filename.split("_")
   f_date_str = fy + "_" + fm + "_" + fd 
   f_datetime_str = fy + "-" + fm + "-" + fd + " " + fh + ":" + fmin + ":" + fs 
   f_datetime = datetime.datetime.strptime(f_datetime_str, "%Y-%m-%d %H:%M:%S")
   return(f_datetime, cam, f_date_str, fh, fmin, fs)

def find_hd_file(sd_file):
   sd_datetime, sd_cam, sd_date, sd_h, sd_m, sd_s = convert_filename_to_date_cam(sd_file)
   el = sd_file.split("/")
   el_f = el[-1]
   hd_datetime = ""
   meteor_dir = sd_file.replace(el_f, "")
   print ("SD File", sd_file)
   print ("SD Datetime ", sd_datetime)
   print ("SD Cam", sd_cam)

   hd_wild_card = hd_video_dir + sd_date + "_" + sd_h + "_" + sd_m + "*" + sd_cam + ".mp4"
   print ("HD Wildcard: ", hd_wild_card)

   for hd_file in (glob.glob(hd_wild_card)):
      print("HD FILE", hd_file)
      hd_datetime, hd_cam, hd_date, hd_h, hd_m, hd_s = convert_filename_to_date_cam(hd_file)
   time_offset = sd_datetime - hd_datetime
   print ("Time offset: ", sd_datetime - hd_datetime)
   tos_ts = time_offset.total_seconds()

   # trim the hd file ss= time offset to end of file (60 - time offset) and put in temp1
   if int(tos_ts) >= 0:
      hd_file1 = ffmpeg_trim(hd_file, str(tos_ts), str(60 - int(tos_ts)), "-sd_linked.mp4")

   # then find the next hd_file (increment datetime + 1 minute, determine/find filename and then trim from beginning of file with duration of time offset into temp2
   next_hd_datetime = hd_datetime + datetime.timedelta(0,60)
   next_hd_wildcard = hd_video_dir + "/" + next_hd_datetime.strftime("%Y_%m_%d_%H_%M") + "*" + hd_cam + ".mp4"
   print ("NEXT HD WILDCARD", next_hd_wildcard)
   # cat temp1 and temp2 to get the sd_mirrored HD file.
   for next_hd_file in (glob.glob(next_hd_wildcard)):
      print("NEXT HD FILE", hd_file)
      next_hd_datetime, next_hd_cam, next_hd_date, next_hd_h, next_hd_m, next_hd_s = convert_filename_to_date_cam(next_hd_file)

   # trim the next HD file from the start to the original offset
   hd_file2 = ffmpeg_trim(next_hd_file, str(0), str(int(tos_ts)), "-sd_linked")
   hd_outfile = hd_video_dir + "/" + str(sd_date) + "_" + sd_h + "-" + sd_m + "-" + sd_s + "-" + sd_cam + "-HD-sync.mp4"
   ffmpeg_cat(hd_file1, hd_file2, hd_outfile)

   cmd = "cp " +hd_outfile + " " + proc_dir + sd_date + "/" 
   print(cmd)
   os.system(cmd)
   final_hd_outfile = proc_dir + "/" + str(sd_date) + "/" + str(sd_date) + "_" + sd_h + "-" + sd_m + "-" + sd_s + "-" + sd_cam + "-HD-sync.mp4"
   return(final_hd_outfile)
#sd_file = sys.argv[1]
#hd_file = find_hd_file(sd_file)


def ffmpeg_trim (filename, trim_start_sec, dur_sec, out_file_suffix):
   #ffmpeg -i /mnt/ams2/meteors/2018-09-20/2018-09-20_22-20-05-cam5-hd.mp4 -ss 00:00:46 -t 00:00:06 -c copy /mnt/ams2/meteors/2018-09-20/2018-09-20_22-20-05-cam5-hd-trim.mp4

   outfile = filename.replace(".mp4", out_file_suffix + ".mp4")
   cmd = "ffmpeg -i " + filename + " -y -ss 00:00:" + str(trim_start_sec) + " -t 00:00:" + str(dur_sec) + " -c copy " + outfile
   print (cmd)
   os.system(cmd)
   return(outfile)


filename = sys.argv[1]

events = []
event = []

file = open(filename, "r")
trim_base = filename.replace("-motion.txt", "-trim-");
mp4_file = filename.replace("-motion.txt", ".mp4");

hd_file = find_hd_file(mp4_file)
print("HD FILE:", hd_file)

for line in file:
   line = line.replace("\n", "")
   (frameno, mo, bpf, cons_mo) = line.split(","); 
   if (int(cons_mo) > 0):
      #print ("Cons:", cons_mo);
      event.append([frameno,mo,bpf,cons_mo])
   else:
      #print ("Event Len:", len(event)   )
      if len(event) > 10:
         events.append(event)
      event = []

event_count = 1
for event in events:
   print ("Event:", event)
   start_frame = int(event[0][0])
   end_frame = int(event[-1][0])
   frame_elp = int(end_frame) - int(start_frame)
   start_sec = int(start_frame / 25) - 5
   if start_sec <= 0:
      start_sec = 0
   dur = int(frame_elp / 25) + 5 + 3
   outfile = ffmpeg_trim(mp4_file, start_sec, dur, "-trim" + str(event_count))
   
   hd_outfile = ffmpeg_trim(hd_file, start_sec, dur, "-trim" + str(event_count))
   event_count = event_count + 1;
   print ("EVENT Start frame: ", start_frame, start_sec)
   print ("EVENT End frame: ", end_frame, start_sec + dur)
   print ("Total frames: ", frame_elp, dur)
   print(hd_outfile)
   #reject_filters(outfile)
   
