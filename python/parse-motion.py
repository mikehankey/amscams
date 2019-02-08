#!/usr/bin/python3

from pathlib import Path
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
   cmd = "/usr/bin/ffmpeg -y -f concat -safe 0 -i " + cat_file + " -c copy " + outfile
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
   hd_outfile = hd_video_dir + "/" + str(sd_date) + "_" + sd_h + "_" + sd_m + "_" + sd_s + "_000_" + sd_cam + "-HD-sync.mp4"
   ffmpeg_cat(hd_file1, hd_file2, hd_outfile)

   cmd = "cp " +hd_outfile + " " + proc_dir + sd_date + "/" 
   print(cmd)
   os.system(cmd)
   final_hd_outfile = proc_dir + "/" + str(sd_date) + "/" + str(sd_date) + "_" + sd_h + "_" + sd_m + "_" + sd_s + "_000_" + sd_cam + "-HD-sync.mp4"
   return(final_hd_outfile)



def ffmpeg_trim (filename, trim_start_sec, dur_sec, out_file_suffix):

   outfile = filename.replace(".mp4", out_file_suffix + ".mp4")
   cmd = "/usr/bin/ffmpeg -i " + filename + " -y -ss 00:00:" + str(trim_start_sec) + " -t 00:00:" + str(dur_sec) + " -c copy " + outfile
   print (cmd)
   os.system(cmd)
   return(outfile)

def setup_dirs(filename):
   el = filename.split("/")
   fn = el[-1]
   working_dir = filename.replace(fn, "")
   data_dir = working_dir + "/data/"
   images_dir = working_dir + "/images/"
   file_exists = Path(data_dir)
   if file_exists.is_dir() == False:
      print("Make the dir.")
      os.system("mkdir " + data_dir)

   file_exists = Path(images_dir)
   if file_exists.is_dir() == False:
      print("Make the dir.")
      os.system("mkdir " + images_dir)

def get_frame_data(filename):
   bpt_total = 0
   bptv_total = 0
   bc = 0
   file = open(filename, "r")
   frame_data = []
   for line in file:
      line = line.replace("\n", "")
      frame_data.append(line)
      (frameno, mo, bpf, bpt,bptv,cons_mo) = line.split(","); 
      bpt_total = int(bpt_total) + int(bpt)
      bptv_total = int(bptv_total) + int(bptv)
      bc = bc + 1
   bpt_avg = int(bpt_total / bc)
   bptv_avg = int(bptv_total / bc)
   return(frame_data, bpt_avg, bptv_avg)

def eval_event(event):
   first = int(event[0][0])
   last = int(event[-1][0])
   event_len = len(event)
   fdiff = last - first +1
   if event_len > 0:
      perc = fdiff / event_len
   return(fdiff, perc)

def get_events(frame_data, bpt_avg, bptv_avg):
   nm = 0
   event = []
   events = []

   for line in frame_data:
      (frameno, mo, bpf, bpt,bptv,cons_mo) = line.split(","); 
      if int(cons_mo) >= 1:
      #if (int(bpt) > int(bpt_avg) or int(bptv) > int(bptv_avg)) or int(cons_mo) >= 1: 
         cns = cns + 1
         nm = 0
      else:
         cns = 0
         nm = nm + 1
      if cns >= 1 or int(cons_mo) >= 1:
      #   print("LAST BPT/BPTV vs BPT/BPTV", frameno, bpf, bpt_avg, bptv_avg, last_bpt, last_bptv, bpt, bptv, cons_mo, cns, nm)
         data = (frameno, mo, bpf, bpt,bptv,cons_mo) 
         event.append(data)
      if (len(event) >= 2 ) and nm >=3:
         events.append(event)
         event = []
      #   print ("ADD EVENT", len(event), nm)
      elif nm >3 and len(event) > 0:
         event = []
      #   print ("CLEAR EVENT", len(event), nm)
      #print("DEBUG:", frameno, len(event), cns, cons_mo, nm)

   return(events)

def join_arr(arr1, arr2):
   new_arr = []
   for x in arr1:
      new_arr.append(x)
   for x in arr2:
      new_arr.append(x)
   return(new_arr)


def merge_events_new(valid_events):
   chain_on = 0
   temp_arr = []
   merged_events = []
   ec = 0
   for event in valid_events:
      first_frame = event[0][0]
      last_frame = event[-1][0]
      print ("VALID EVENT:", ec, first_frame, last_frame)

      if ec > 0:
         # there is an event following this one, see if it is 
         # close enough to merge
         prev_end = valid_events[ec-1][-1][0] 
      
         print ("PREV END / THIS FRAME", ec, prev_end, first_frame) 
         if int(first_frame) - int(prev_end) <= 100:
            chain_on = 1
            print ("These events should be merged.", ec-1, ec, chain_on)
            temp_arr = temp_arr + event
         else:
            if len(temp_arr) > 0:
               # there are already some merged events so save those.
               merged_events.append(temp_arr)
               temp_arr = event
            else:
               # there are not any merged events already so start up a new
               # list
               temp_arr = event
            chain_on = 0  
      else:
         temp_arr = event

        
     
      ec = ec + 1
     
   if len(temp_arr) > 0:  
      merged_events.append(temp_arr)
      temp_arr = [] 


   print("TOTAL VALID EVENTS:", len(valid_events))
   for event in valid_events:
      print("VALID:", event[0][0], event[-1][0])
   print("TOTAL MERGED EVENTS:", len(merged_events))
   for event in merged_events:
      print("MERGED:", event[0][0], event[-1][0])
   return(merged_events)

def merge_events(valid_events):
   print("VALID EVENTS", len(valid_events))
   for event in valid_events:
      print("VALID:", event)
   merged_events = []
   non_merged_events = []
   max_events = len(valid_events)
   # more than one event, lets merge them if they are close in frame start / overlapping
   ec = 0
   track = {}
   last_merged_frame = 0


   for ec in range (0, len(valid_events)): 
    
      event = valid_events[ec]
      #print("TRACK (last/current):", last_merged_frame, event[0][0])
      if last_merged_frame < int(event[0][0]):
         if ec + 1 < max_events:
            print ("EC NOT DONE YET:", ec)
            s1 = int(valid_events[ec][-1][0])
            s2 = int(valid_events[ec+1][0][0])
            if s2 - s1 < 100:
               new = join_arr(valid_events[ec], valid_events[ec+1])
               merged_events.append(new)
               last_merged_frame = int(new[-1][0])
               track[ec] = 1
               track[ec+1] = 1
               ec = ec + 1
            else:
               non_merged_events.append(event)
         else:
      #      print ("SOLO", event)
            non_merged_events.append(event)
      else:
         print("SKIP! This frame was already merged.")
            #merged_events.append(event)
      ec = ec + 1
   print("MERGED EVENTS:", len(merged_events))
   for event in merged_events:
      print("     EV", event)
   print("NON MERGED EVENTS:", len(non_merged_events))
   for event in non_merged_events:
      print("     EV", event)

   new_arr = join_arr(merged_events, non_merged_events)   

   for event in merged_events:
      print("ME:", event)
   for event in non_merged_events:
      print("NONME:", event)
   for event in new_arr:
      print("NEW:", event)

   exit()
   return(new_arr)

cns = 0
nm = 0

def trim_event(event):
   start_frame = int(event[0][0])
   end_frame = int(event[-1][0])


   start_frame = start_frame - 50 
   end_frame = end_frame + 30
   if start_frame <= 0:  
      start_frame = 0
   if end_frame >= 1499:  
      start_frame = 1499
   frame_elp = int(end_frame) - int(start_frame)
   

   start_sec = start_frame / 25 
   if start_sec <= 0:
      start_sec = 0
   dur = (frame_elp / 25) + 2
   if dur >= 60:
      dur = 59
   if dur < 1:
      dur = 2

   pad_start = '{:04d}'.format(start_frame)
   print("TRIMINFO: ", mp4_file, pad_start, start_sec, dur)
   outfile = ffmpeg_trim(mp4_file, start_sec, dur, "-trim" + str(pad_start))

filename = sys.argv[1]

trim_base = filename.replace("-motion.txt", "-trim-");
mp4_file = filename.replace("-motion.txt", ".mp4");
setup_dirs(filename)
(frame_data, bpt_avg, bptv_avg) = get_frame_data(filename)


print("FRAMES: ", len(frame_data))

events = get_events(frame_data, bpt_avg, bptv_avg)
print ("EVENTS", len(events))
for event in events:
   print("EV: ", event)
valid_events = []
for event in events:
   fdiff, fperc = eval_event(event)
   if .8 < fperc < 1.8:
      print("EVENT:", fdiff, fperc, event)
      if len(event) > 2:
         valid_events.append(event)
   else:
      print ("REJECT:", fdiff, fperc,event)

print ("VALID EVENTS", len(valid_events))

if len(valid_events) > 1:
   merged_events = merge_events_new(valid_events)
   #if len(valid_events) > 1:
   #   merged_events = merge_events(merged_events)
else:
   merged_events = valid_events
#merged_events = valid_events


print ("FINAL MERGED EVENTS", len(merged_events))

for event in merged_events:
   print("TRIM:", event)
   trim_event(event)

el = filename.split("/")
fn = el[-1]
dir = filename.replace(fn, "")
stack_file = dir + fn
stack_file = stack_file.replace("-motion.txt", "-stacked.png")
cmd = "mv " + filename + " " + dir + "data/"
print(cmd)
#os.system(cmd)
cmd = "mv " + stack_file + " " + dir + "images/"
print(cmd)
os.system(cmd)



# END NEW LOGIC
exit()


