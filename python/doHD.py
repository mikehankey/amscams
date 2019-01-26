#!/usr/bin/python3

import time
from pathlib import Path
import json
import sys
import os
import glob
import datetime
from detectlib import *
from caliblib import save_json_file

json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)

crop_on = 0
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

def eof_processing(sd_file, trim_num, dur):
   merge_files = []
   sd_datetime, sd_cam, sd_date, sd_h, sd_m, sd_s = convert_filename_to_date_cam(sd_file)
   offset = int(trim_num) / 25
   print("TRIM SEC OFFSET: ", offset)
   meteor_datetime = sd_datetime + datetime.timedelta(seconds=offset)
   print("METEOR CLIP START DATETIME:", meteor_datetime) 
   hd_glob = "/mnt/ams2/HD/" + sd_date + "_*" + sd_cam + "*"
   hd_files = sorted(glob.glob(hd_glob))
   for hd_file in hd_files:
      el = hd_file.split("_")
      if len(el) == 8 and "meteor" not in hd_file and "crop" not in hd_file:
         hd_datetime, hd_cam, hd_date, hd_h, hd_m, hd_s = convert_filename_to_date_cam(hd_file)
         time_diff = meteor_datetime - hd_datetime
         time_diff_sec = time_diff.total_seconds() 
         if 0 < time_diff_sec < 90:
            print("HERE ARE THE 2 FILES:", hd_file)
            merge_files.append(hd_file)
   # take the last 5 seconds of file 1
   # take the first 5 seconds of file 2 
   # merge them together to make file 3
   hd_trim1 = ffmpeg_trim(merge_files[0], str(55), str(5), "-temp-" + str(trim_num) + "-HD-meteor")
   hd_trim2 = ffmpeg_trim(merge_files[1], str(0), str(5), "-temp-" + str(trim_num) + "-HD-meteor")
   print(hd_trim1)
   print(hd_trim2)
   # cat them together

   hd_datetime, sd_cam, sd_date, sd_h, sd_m, sd_s = convert_filename_to_date_cam(merge_files[0])
   new_clip_datetime = hd_datetime + datetime.timedelta(seconds=55)
   new_hd_outfile = new_clip_datetime.strftime("%Y_%m_%d_%H_%M_%S" + "_" + "000" + "_" + sd_cam + ".mp4")

 
   ffmpeg_cat(hd_trim1, hd_trim2, new_hd_outfile)
   hd_trim = new_hd_outfile.replace(".mp4", "-trim0-HD-trim.mp4")
   os.system("cp " + new_hd_outfile + " " + hd_trim)

   return(new_hd_outfile, hd_trim)


def find_hd_file_new(sd_file, trim_num, dur = 5):
   sd_datetime, sd_cam, sd_date, sd_h, sd_m, sd_s = convert_filename_to_date_cam(sd_file)
   print("SD FILE: ", sd_file)
   print("TRIM NUM: ", trim_num)
   if trim_num > 1400:
      print("END OF FILE PROCESSING NEEDED!")
      hd_file, hd_trim = eof_processing(sd_file, trim_num, dur)
      return(hd_file, hd_trim) 
   offset = int(trim_num) / 25
   print("TRIM SEC OFFSET: ", offset)
   meteor_datetime = sd_datetime + datetime.timedelta(seconds=offset)
   print("METEOR CLIP START DATETIME:", meteor_datetime) 
   hd_glob = "/mnt/ams2/HD/" + sd_date + "_*" + sd_cam + "*"
   hd_files = sorted(glob.glob(hd_glob))
   for hd_file in hd_files:
      el = hd_file.split("_")
      if len(el) == 8 and "meteor" not in hd_file and "crop" not in hd_file:
         hd_datetime, hd_cam, hd_date, hd_h, hd_m, hd_s = convert_filename_to_date_cam(hd_file)
         time_diff = meteor_datetime - hd_datetime
         time_diff_sec = time_diff.total_seconds() 
         if 0 < time_diff_sec < 60:
            print("TIME DIFF:", hd_file, meteor_datetime, hd_datetime, time_diff_sec)
            time_diff_sec = time_diff_sec - 3
            dur = int(dur) + 1
            if time_diff_sec < 0:
               time_diff_sec = 0
            hd_trim = ffmpeg_trim(hd_file, str(time_diff_sec), str(dur), "-trim-" + str(trim_num) + "-HD-meteor")
            print("HD TRIM:", hd_trim)
            return(hd_file, hd_trim)
      #else:
      #   print("LEN EL:", len(el), hd_file)

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

   hd_files = glob.glob(hd_wild_card) 
   for hd_file in (hd_files):
      print("HD FILE", hd_file)
      hd_datetime, hd_cam, hd_date, hd_h, hd_m, hd_s = convert_filename_to_date_cam(hd_file)
   if len(hd_files) == 0:
      print("No HD file found.", hd_wild_card)
      exit()
   print("HD FILE?:", hd_file)
   print("TIMEOFF?:", sd_datetime, hd_datetime)
   time_offset = sd_datetime - hd_datetime
   print ("Time offset: ", sd_datetime - hd_datetime)
   tos_ts = time_offset.total_seconds()

   # trim the hd file ss= time offset to end of file (60 - time offset) and put in temp1
   if int(tos_ts) >= 0:
      hd_file1 = ffmpeg_trim(hd_file, str(tos_ts), str(60 - int(tos_ts)), "-sd_linked.mp4")
   else:
      print("TOS_TS = ", tos_ts)
      exit()

   # then find the next hd_file (increment datetime + 1 minute, determine/find filename and then trim from beginning of file with duration of time offset into temp2
   next_hd_datetime = hd_datetime + datetime.timedelta(0,60)
   next_hd_wildcard = hd_video_dir + "/" + next_hd_datetime.strftime("%Y_%m_%d_%H_%M") + "*" + hd_cam + ".mp4"
   print ("NEXT HD WILDCARD", next_hd_wildcard)
   # cat temp1 and temp2 to get the sd_mirrored HD file.
   next_hd_files =  glob.glob(next_hd_wildcard)

   if len(next_hd_files) == 0:
      print("No NEXT HD file found.", hd_wild_card)
      exit()

   for next_hd_file in (glob.glob(next_hd_wildcard)):
      print("NEXT HD FILE", hd_file)
      next_hd_datetime, next_hd_cam, next_hd_date, next_hd_h, next_hd_m, next_hd_s = convert_filename_to_date_cam(next_hd_file)

   # trim the next HD file from the start to the original offset
   hd_file2 = ffmpeg_trim(next_hd_file, str(0), str(tos_ts), "-sd_linked")
   hd_outfile = hd_video_dir + "/" + str(sd_date) + "_" + sd_h + "_" + sd_m + "_" + sd_s + "_000_" + sd_cam + "-HD-sync.mp4"
   ffmpeg_cat(hd_file1, hd_file2, hd_outfile)

   cmd = "cp " +hd_outfile + " " + proc_dir + sd_date + "/" 
   print(cmd)
   os.system(cmd)
   final_hd_outfile = proc_dir + "/" + str(sd_date) + "/" + str(sd_date) + "_" + sd_h + "_" + sd_m + "_" + sd_s + "_000_" + sd_cam + "-HD-sync.mp4"
   return(final_hd_outfile)



def ffmpeg_trim (filename, trim_start_sec, dur_sec, out_file_suffix):

   outfile = filename.replace(".mp4", out_file_suffix + ".mp4")
   cmd = "/usr/bin/ffmpeg -y -i " + filename + " -y -ss 00:00:" + str(trim_start_sec) + " -t 00:00:" + str(dur_sec) + " -c copy " + outfile
   print (cmd)
   os.system(cmd)
   return(outfile)

def trim_event(event):
   low_start = 0
   high_end = 0
   start_frame = int(event[0][0])
   end_frame = int(event[-1][0])
   if low_start == 0:
      low_start = start_frame
   if start_frame < low_start:
      low_start = start_frame
   if end_frame > high_end:
      high_end = end_frame

   start_frame = int(low_start)
   end_frame = int(high_end)
   frame_elp = int(end_frame) - int(start_frame)
   start_sec = int(start_frame / 25) - 3
   if start_sec <= 0:
      start_sec = 0
   dur = int(frame_elp / 25) + 3 + 2
   if dur >= 60:
      dur = 59
   if dur < 1:
      dur = 2

   pad_start = '{:04d}'.format(start_frame)
   outfile = ffmpeg_trim(mp4_file, start_sec, dur, "-trim" + str(pad_start))

def check_hd_motion(frames, trim_file):

   height, width = frames[0].shape

   max_cons_motion, frame_data, moving_objects, trim_stack = check_for_motion(frames, trim_file)
   stacked_image_np = np.asarray(trim_stack)
   found_objects, moving_objects = object_report(trim_file, frame_data)

   stacked_image = draw_obj_image(stacked_image_np, moving_objects,trim_file, stacked_image_np)

   cv2.namedWindow('pepe')
   cv2.imshow('pepe', stacked_image)
   cv2.waitKey(5)

   passed,all_objects = test_objects(moving_objects, trim_file, stacked_image_np)
   max_x = 0
   max_y = 0
   min_x = frames[0].shape[1]
   min_y = frames[0].shape[0]
   for object in all_objects:
      if(object['meteor_yn'] == 1):
         print(object)
         box = object['box']
         w = box[2] - box[0] + 25
         h = box[3] - box[1] + 25
         x = box[0]
         y = box[1]
       
         cx = x + (w/2)
         cy = y + (h/2)
 
         print("W,H,x,y", w,h,x,y)

         w = w * 2
         h = h * 2
         if w > h:
            h = w
         else:
            w = h
 
         x = cx - (w/2)
         y = cy - (h/2)
        

         print("W,H,x,y", w,h,x,y)

         crop = "crop=" + str(w) + ":" + str(h) + ":" + str(x) + ":" + str(y)
 
         if crop_on == 1:
            min_x,min_y,max_x,max_y = box
            w = max_x - min_x
            h = max_y - min_y
            print("BOX: ", box)
            print("CROP: ", crop)
            crop_out_file = trim_file.replace(".mp4", "-crop.mp4")
            scaled_out_file = trim_file.replace(".mp4", "-scaled.mp4")
            pip_out_file = trim_file.replace(".mp4", "-pip.mp4")
            cmd = "ffmpeg -y -i " + trim_file + " -filter:v \"" + crop + "\" " + crop_out_file
            print(cmd)
            os.system(cmd)
    
            cmd = "ffmpeg -y -i " + trim_file + " -s 720x480 -c:a copy " + scaled_out_file
            print(cmd)
            os.system(cmd)

            cmd = "/usr/bin/ffmpeg -y -i " + scaled_out_file + " -i " + crop_out_file + " -filter_complex \"[1]scale=iw/1:ih/1 [pip];[0][pip] overlay=main_w-overlay_w-10:main_h-overlay_h-10\" -profile:v main -level 3.1 -b:v 440k -ar 44100 -ab 128k -s 1920x1080 -vcodec h264 -acodec libfaac " + pip_out_file
            print(cmd)
            os.system(cmd)

#'box': [612, 187, 653, 303]

def crop_hd(hd_file,box_str):
   #x,y,mx,my = box_str.split(",")
   x,y,mx,my = box_str

   #hd_mx = 1
   #hd_my = 1
   #x = float(x) * hd_mx
   #y = float(y) * hd_my
   #mx = float(mx) * hd_mx
   #my = float(my) * hd_my

   w = float(mx) - float(x)
   h = float(my) - float(y)

   x = int(x)
   y = int(y)
   w = int(w)
   h = int(h)

   print("XY: ",x,y,mx,my,w,h)

   crop = "crop=" + str(w) + ":" + str(h) + ":" + str(x) + ":" + str(y)
   print("CROP: ", crop)
   crop_out_file = hd_file.replace(".mp4", "-crop.mp4")
   cmd = "/usr/bin/ffmpeg -y -i " + hd_file + " -filter:v \"" + crop + "\" " + crop_out_file
   print(cmd)
   os.system(cmd)
   return(crop_out_file)

meteor_file = sys.argv[1]
dur_sec = sys.argv[2]
if int(float(dur_sec)) < 1:
   dur_sec = 3
elif 1 < int(float(dur_sec)) < 2 :
   dur_sec = 5
else:
   dur_sec = int(dur_sec) + 1

box = sys.argv[3]
trim_adj = sys.argv[4]
if int(trim_adj) < 50:
   trim_adj = 0
else: 
   trim_adj = int(trim_adj) - 50
meteor_day_dir = sys.argv[5]

el = meteor_file.split("-trim") 
base = el[0]
trim = el[-1]
num,trash = trim.split("-")

num = int(num) + int(trim_adj)

min_file = base + ".mp4"

meteor_suffix = "-trim" + str(num) + "-meteor"

trim_start_sec = int(num) / 25 
if trim_start_sec < 0:
   trim_star_sec = 0


print("METEOR FILE : ", meteor_file)
print("BASE MIN FILE : ", min_file)
hd_file,hd_trim = find_hd_file_new(min_file, int(num), dur_sec)

el = hd_trim.split("/")
hdt = meteor_day_dir + el[-1]

cmd = "./stack-stack.py stack_vid " + hdt
print(cmd)
os.system(cmd)

hd_trim_crop = hd_trim.replace(".mp4", "-crop.mp4")

el = hd_trim_crop.split("/")
hdtc = meteor_day_dir + el[-1]



print("HD FILE : ", hd_trim)
print("BOX: ", box)

# make bigger box for plate solving...
hd_stack = hdt.replace(".mp4", "-stacked.png")
hd_stack_img = cv2.imread(hd_stack, 0)
print(hd_stack)

print("IMAGES:", hd_stack)
bigger_crop,plate_box = bigger_box(box, hd_stack, hd_stack_img)
meteor_json = {}
meteor_json_file =meteor_file.replace(".mp4", ".json")
el = meteor_json_file.split("/")
mf = el[-1]
meteor_json_file = meteor_day_dir + mf

a,b,c,d = box.split(",")
nbox = [int(a),int(b),int(c),int(d)]
meteor_json['box'] = nbox
meteor_json['bigger_box'] = plate_box




print("JSON: ", meteor_json_file)
save_json_file(meteor_json_file, meteor_json)


crop_hd(hd_trim, plate_box)




cmd = "mv " + hd_trim + " " + meteor_day_dir
os.system(cmd)
cmd = "mv " + hd_trim_crop + " " + meteor_day_dir
os.system(cmd)

el = hd_trim_crop.split("/")
hdtc_fn = el[-1]
new_hd_trim_crop = meteor_day_dir + hdtc_fn

cmd = "./stack-stack.py stack_vid " + new_hd_trim_crop
os.system(cmd)


#hd_trim_crop = cv2.imread(hdtc)

print("REDUCE")
trim_crop_file = el[-1]
#trim_crop_file = trim_crop_file.replace(".mp4", "-crop.mp4")
cmd = "./detect-filters.py reduce_hd_crop " + meteor_file + " " + meteor_day_dir + trim_crop_file
print(cmd)
os.system(cmd)


#print(hd_file, trim_start_sec, dur_sec, "-meteor")
meteor_file_hd = hd_file.replace(".mp4", meteor_suffix + ".mp4")
ffmpeg_trim (hd_file, trim_start_sec, dur_sec, meteor_suffix)
print("METEOR HD:", meteor_file_hd)
hd_frames = load_video_frames(meteor_file_hd)


#stacked_hd = stack_frames(hd_frames)



print("NBOX: ", plate_box)

min_x,min_y,max_x,max_y = plate_box

min_x = int(min_x)
max_x = int(max_x)
min_y = int(min_y)
max_y = int(max_y)


cv2.rectangle(hd_stack_img, (min_x, min_y), (max_x,max_y), (255, 0, 0), 2)
#cv2.rectangle(hd_frames[0], (10, 10), (20, 20), (255, 0, 0), 2)

cv2.imshow('pepe', hd_stack_img)
cv2.waitKey(10)


exit()
crop_out_file = trim_file.replace(".mp4", "-crop.mp4")
scaled_out_file = trim_file.replace(".mp4", "-scaled.mp4")
pip_out_file = trim_file.replace(".mp4", "-pip.mp4")
cmd = "ffmpeg -y -i " + trim_file + " -filter:v \"" + crop + "\" " + crop_out_file
print(cmd)
os.system(cmd)

