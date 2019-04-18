import datetime
import glob
import cv2
import os
#import time
from lib.UtilLib import convert_filename_to_date_cam
from lib.FileIO import load_json_file
from lib.ImageLib import find_min_max_dist,bigger_box




def doHD(sd_video_file, json_conf):
   sd_w = 704
   sd_h = 576
   hd_w = 1920
   hd_h = 1080

   hdm_x = 2.7272
   hdm_y = 1.875

   # All steps to find and reduce HD file and save in archive and cloud
   # find HD file
   # trim HD file
   # handle EOF exceptions
   # crop HD file
   # make stacks for Crop,crop obj, HD & HD obj
   # make meteor json file with HD reduction and meteor info
   # if HD reduction fails, note this in the JSON file
   # preserve original objects json in new json file
   # copy all meteor files to the meteor archive
   # upload to VMA

   json_file = sd_video_file.replace(".mp4", ".json")
   objects = load_json_file(json_file)
   for object in objects:
      if object['meteor'] == 1:
   

         el = sd_video_file.split("-trim")
         min_file = el[0] + ".mp4"
         ttt = el[1].split(".")
         trim_num = int(ttt[0])
  
         start_frame = object['history'][0][0]
         end_frame = object['history'][-1][0]
         frame_dur = end_frame - start_frame  

         start_sec = (start_frame / 25) 
         frame_dur_sec = (frame_dur / 25) + 3

         #print("SF:", start_frame, end_frame, frame_dur) 

         if start_sec - 1 < 0:
            start_sec = 0
         else:
            start_sec = start_sec - 1

         if frame_dur_sec + start_sec + 1 >= 59:
            frame_dur_sec = 59 - start_sec
         else:
            frame_dur_sec = frame_dur_sec + 1
         if frame_dur_sec < 5:
            frame_dur_sec = 5

         if frame_dur > 180:
            frame_dur_sec = frame_dur_sec +  4
         #print("SS:", start_sec, frame_dur_sec) 
         frame_dur_sec = frame_dur_sec + 3
         #print(min_file,start_sec,frame_dur_sec)
         hd_file, hd_trim,trim_time_offset, trim_dur = find_hd_file_new(min_file, trim_num, frame_dur_sec)

         #print("HD:", hd_file, hd_trim)
         if hd_file == None or hd_file == 0:
            return(None,None,None,None,None,None)
         (max_x,max_y,min_x,min_y) = find_min_max_dist(object['history'])
         (min_x,min_y,max_x,max_y) = bigger_box(min_x,min_y,max_x,max_y,sd_w,sd_h,25)
         hd_min_x = min_x * hdm_x
         hd_max_x = max_x * hdm_x
         hd_min_y = min_y * hdm_y
         hd_max_y = max_y * hdm_y

         sd_box= (min_x,min_y,max_x,max_y)
         hd_box= (hd_min_x,hd_min_y,hd_max_x,hd_max_y)
         crop_out_file = crop_hd(hd_trim,hd_box)
         #print("HD TRIM:", hd_trim)
         return(hd_file,hd_trim,crop_out_file,hd_box,trim_time_offset, trim_dur)
   return(0,0,0,0,0,0)

def archive_meteor (sd_video_file,hd_file,hd_trim,crop_out_file,hd_box,hd_objects,json_conf):
   print(archive_meteor)

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
   cmd = "/usr/bin/ffmpeg -y -i " + hd_file + " -filter:v \"" + crop + "\" " + crop_out_file + " >/dev/null 2>&1"
   print(cmd)
   os.system(cmd)
   return(crop_out_file)


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
         box = object['box']
         w = box[2] - box[0] + 25
         h = box[3] - box[1] + 25
         x = box[0]
         y = box[1]

         cx = x + (w/2)
         cy = y + (h/2)

         w = w * 2
         h = h * 2
         if w > h:
            h = w
         else:
            w = h

         x = cx - (w/2)
         y = cy - (h/2)
    
         crop = "crop=" + str(w) + ":" + str(h) + ":" + str(x) + ":" + str(y)

         if crop_on == 1:
            min_x,min_y,max_x,max_y = box
            w = max_x - min_x
            h = max_y - min_y
            crop_out_file = trim_file.replace(".mp4", "-crop.mp4")
            scaled_out_file = trim_file.replace(".mp4", "-scaled.mp4")
            pip_out_file = trim_file.replace(".mp4", "-pip.mp4")
            cmd = "ffmpeg -y -i " + trim_file + " -filter:v \"" + crop + "\" " + crop_out_file+ " >/dev/null 2>&1"
            os.system(cmd)

            cmd = "ffmpeg -y -i " + trim_file + " -s 720x480 -c:a copy " + scaled_out_file
            os.system(cmd)

            cmd = "/usr/bin/ffmpeg -y -i " + scaled_out_file + " -i " + crop_out_file + " -filter_complex \"[1]scale=iw/1:ih/1 [pip];[0][pip] overlay=main_w-overlay_w-10:main_h-overlay_h-10\" -profile:v main -level 3.1 -b:v 440k -ar 44100 -ab 128k -s 1920x1080 -vcodec h264 -acodec libfaac " + pip_out_file + " >/dev/null 2>&1"
            os.system(cmd)





def find_hd_file_new(sd_file, trim_num, dur = 5, trim_on =1):

   (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(sd_file)
   if trim_num > 1400:
      hd_file, hd_trim = eof_processing(sd_file, trim_num, dur)
      time_diff_sec = int(trim_num / 25)
      return(hd_file, hd_trim, time_diff_sec, dur)
   offset = int(trim_num) / 25
   meteor_datetime = sd_datetime + datetime.timedelta(seconds=offset)
   hd_glob = "/mnt/ams2/HD/" + sd_y + "_" + sd_m + "_" + sd_d + "_*" + sd_cam + "*.mp4"
   hd_files = sorted(glob.glob(hd_glob))
   for hd_file in hd_files:
      el = hd_file.split("_")
      if len(el) == 8 and "meteor" not in hd_file and "crop" not in hd_file:
         hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(hd_file)
         time_diff = meteor_datetime - hd_datetime
         time_diff_sec = time_diff.total_seconds()
         if 0 < time_diff_sec < 60:
            time_diff_sec = time_diff_sec - 3
            dur = int(dur) + 1 + 3
            if trim_num == 0:
               trim_num = 1
            if time_diff_sec < 0:
               time_diff_sec = 0
            if trim_on == 1:
               hd_trim = ffmpeg_trim(hd_file, str(time_diff_sec), str(dur), "-trim-" + str(trim_num) + "-HD-meteor")
            else:
               hd_trim = None
            return(hd_file, hd_trim, time_diff_sec, dur)
   return(None,None,None,None)


def eof_processing(sd_file, trim_num, dur):
   merge_files = []
   sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s = convert_filename_to_date_cam(sd_file)
   offset = int(trim_num) / 25
   print("TRIM SEC OFFSET: ", offset)
   meteor_datetime = sd_datetime + datetime.timedelta(seconds=offset)
   print("METEOR DATETIME:", meteor_datetime)
   #hd_glob = "/mnt/ams2/HD/" + sd_date + "_*" + sd_cam + "*"
   hd_glob = "/mnt/ams2/HD/" + sd_y + "_" + sd_m + "_" + sd_d + "_*" + sd_cam + "*"
   print("HD GLOB:", hd_glob)
   hd_files = sorted(glob.glob(hd_glob))
   print("HD FILES:", len(hd_files))
   for hd_file in hd_files:
      el = hd_file.split("_")
      if len(el) == 8 and "meteor" not in hd_file and "crop" not in hd_file and "-HD-" not in hd_file:
         hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(hd_file)
         time_diff = meteor_datetime - hd_datetime
         time_diff_sec = time_diff.total_seconds()
         print(meteor_datetime, hd_datetime, time_diff_sec,hd_file) 
         if -90 < time_diff_sec < 90:
            print("TIME:", time_diff_sec, hd_file)
            merge_files.append(hd_file)
   # take the last 5 seconds of file 1
   # take the first 5 seconds of file 2
   # merge them together to make file 3
   print("MERGE FILES:", merge_files)
   if len(merge_files) == 0:
      return(0,0)

   hd_trim1 = ffmpeg_trim(merge_files[0], str(55), str(5), "-temp-" + str(trim_num) + "-HD-meteor")
   hd_trim2 = ffmpeg_trim(merge_files[1], str(0), str(5), "-temp-" + str(trim_num) + "-HD-meteor")
   # cat them together

   print("TRIM FILES:", hd_trim1, hd_trim2)

   #hd_datetime, sd_cam, sd_date, sd_h, sd_m, sd_s = convert_filename_to_date_cam(merge_files[0])
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(merge_files[0])
   new_clip_datetime = hd_datetime + datetime.timedelta(seconds=55)
   new_hd_outfile = new_clip_datetime.strftime("%Y_%m_%d_%H_%M_%S" + "_" + "000" + "_" + sd_cam + ".mp4")
   print("HD TRIM1,2,NEW:", hd_trim1, hd_trim2, new_hd_outfile)
   ffmpeg_cat(hd_trim1, hd_trim2, new_hd_outfile)
   hd_trim = new_hd_outfile.replace(".mp4", "-trim-0-HD-trim.mp4")
   cmd = "cp " + new_hd_outfile + " " + hd_trim
   os.system(cmd)

   return(new_hd_outfile, hd_trim)


def ffmpeg_cat (file1, file2, outfile):
   cat_file = "/tmp/cat_files.txt"
   fp = open(cat_file, "w")
   fp.write("file '" + file1 + "'\n")
   fp.write("file '" + file2 + "'\n")
   fp.close()
   cmd = "/usr/bin/ffmpeg -y -f concat -safe 0 -i " + cat_file + " -c copy " + outfile + " >/dev/null 2>&1"
   print(cmd)
   os.system(cmd)



def ffmpeg_trim (filename, trim_start_sec, dur_sec, out_file_suffix):

   outfile = filename.replace(".mp4", out_file_suffix + ".mp4")
   cmd = "/usr/bin/ffmpeg -y -i " + filename + " -y -ss 00:00:" + str(trim_start_sec) + " -t 00:00:" + str(dur_sec) + " -c copy " + outfile+ " >/dev/null 2>&1"
#   print (cmd)
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
   dur = int(frame_elp / 25) + 3 + 3
   if dur >= 60:
      dur = 59
   if dur < 2:
      dur = 3 

   pad_start = '{:04d}'.format(start_frame)
   outfile = ffmpeg_trim(mp4_file, start_sec, dur, "-trim" + str(pad_start))


def get_masks(this_cams_id, json_conf, hd = 0):
   #hdm_x = 2.7272
   #hdm_y = 1.875
   my_masks = []
   cameras = json_conf['cameras']
   for camera in cameras:
      if str(cameras[camera]['cams_id']) == str(this_cams_id):
         if hd == 1:
            masks = cameras[camera]['hd_masks']
         else:
            masks = cameras[camera]['masks']
         for key in masks:
            mask_el = masks[key].split(',')
            (mx, my, mw, mh) = mask_el
            masks[key] = str(mx) + "," + str(my) + "," + str(mw) + "," + str(mh)
            my_masks.append((masks[key]))
   return(my_masks)


def load_video_frames(trim_file, json_conf, limit=0, mask=1,crop=()):
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(trim_file)
   cap = cv2.VideoCapture(trim_file)
   frames = []
   frame_count = 0
   go = 1
   while go == 1:
      _ , frame = cap.read()
      #print(frame_count)
      if frame is None:
         if frame_count <= 5 :
            cap.release()
            return(frames)
         else:
            go = 0
      else:
         if limit != 0 and frame_count > limit:
            cap.release()
            return(frames)
         if len(frame.shape) == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         if len(crop) == 4:
            ih,iw = frame.shape
            x1,y1,x2,y2 = crop
            x1 = x1 - 25
            y1 = y1 - 25
            x2 = x2 + 25
            y2 = y2 + 25
            if x1 < 0:
               x1 = 0 
            if y1 < 0:
               y1 = 0 
            if x1 > iw -1:
               x1 = iw -1 
            if y1 > ih -1:
               y1 = ih -1 
            crop_frame = frame[y1:y2,x1:x2]
            frame = crop_frame

         frames.append(frame)
         frame_count = frame_count + 1
   cap.release()
   if len(crop) == 4:
      return(frames,x1,y1)
   else:
      return(frames)

def ffmpeg_dump_frames(video_file, out_dir):
   jpg_out = out_dir + "frames%05d.png"
   #"960" height="540"
   syscmd = "/usr/bin/ffmpeg -i " + video_file + " -s 960x540 -ss 00:00:00  " + jpg_out
   print(syscmd)
   os.system(syscmd)
   jpg_tout = out_dir + "frames%05d-t.png"
   syscmd = "/usr/bin/ffmpeg -i " + video_file + " -s 360x240 -ss 00:00:00  " + jpg_tout
   os.system(syscmd)


