'''
   Pipeline Video Functions
'''
import subprocess
import cv2
import numpy as np
import time
from PIL import ImageFont, ImageDraw, Image, ImageChops
import datetime
import os
import glob

from lib.PipeAutoCal import fn_dir
from lib.PipeImage import stack_frames_fast , stack_stack, mask_frame, stack_frames
from lib.PipeUtil import cfe, save_json_file, convert_filename_to_date_cam, get_masks, load_json_file
from lib.DEFAULTS import * 
from lib.PipeMeteorTests import ang_dist_vel, angularSeparation

def ffmpeg_cats(files, outfile=None):
   print("FILES:", files)
   files = sorted(files[2:])
   list = ""
   for file in files:
      list += "file '" + file + "'\n"
   list_file = "tmp_vids/cat.txt"
   outfile = files[2].replace(".mp4", "") 
   last_fn, ld = fn_dir(files[-1])
   outfile = outfile + "__" + last_fn
   fp = open(list_file, "w")
   fp.write(list)
   fp.close()
   cmd = "/usr/bin/ffmpeg -f concat -safe 0 -i " +list_file + " -c copy -y " + outfile
   print(cmd)
   os.system(cmd)


def ffmpeg_cat(file1, file2, outfile=None):
   list = "file '" + file1 + "'\n"
   list += "file '" + file2 + "'\n"
   outfile = file1.replace(".mp4", "-cat.mp4")

   list_file = "./tmp_vids/cat.txt"
   fp = open(list_file, "w")
   fp.write(list)
   fp.close()
   cmd = "/usr/bin/ffmpeg -f concat -safe 0 -i " +list_file + " -c copy -y " + outfile
   print(cmd)
   os.system(cmd)
      

def ffprobe(video_file):
   default = [704,576]
   print("FFP:")
   #try:
   if True:
      cmd = "/usr/bin/ffprobe " + video_file + " > /tmp/ffprobe72.txt 2>&1"
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   #except:
   #    return(0,0,0)
   #try:
   #time.sleep(2)
   output = None
   if True:
      fpp = open("/tmp/ffprobe72.txt", "r")
      for line in fpp:
         if "Duration" in line:
            el = line.split(",")
            dur = el[0]
            dur = dur.replace("Duration: ", "")
            el = dur.split(":")
            tsec = el[2]
            total_frames = float(tsec) * 25
         if "Stream" in line:
            output = line
      fpp.close()
      print("OUTPUT: ", output)
      print("TSEC:", dur)
      print("DUR:", dur)
      print("TF:", total_frames)
      if output is None:
         print("FFPROBE PROBLEM:", video_file)
         exit()

      el = output.split(",")
      if "x" in el[3]:
         dim = el[3].replace(" ", "")
      elif "x" in el[2]:
         dim = el[2].replace(" ", "")

      w, h = dim.split("x")
   return(w,h, total_frames)


def find_crop_size(min_x,min_y,max_x,max_y, img_w, img_h, hdm_x=1, hdm_y=1 ):
   sizes = [[1280,720],[1152,648],[1024,576],[869,504],[768,432], [640,360], [320, 180]]

   w = max_x - min_x
   h = max_y - min_y
   mid_x = int(((min_x + max_x) / 2))
   mid_y = int(((min_y + max_y) / 2))

   best_w = img_w 
   best_h = img_h
   for mw,mh in sizes:
      if w * 1.4 < mw and h * 1.4 < mh :
         best_w = mw
         best_h = mh
   print("BEST CROP SIZE IS: ", best_w, best_h)



   if (best_w/2) + mid_x > img_w:
      cx1 = mid_x + (best_w + mid_x ) - img_w 
      cx1 = img_w - best_w
   elif mid_x - (best_w/2) < 0:
      cx1 = 0
   else:
      cx1 = int(mid_x - (best_w/2))
   if (best_h/2) + mid_y > img_h:
      cy1 = 1079 - best_h
   elif mid_y - (best_h/2) < 0:
      cy1 = 0
   else:
      cy1 = int(mid_y -  (best_h/ 2))
   cx1 = int(cx1)
   cy1 = int(cy1)
   cx2 = int(cx1 + best_w)
   cy2 = int(cy1 + best_h)
   cw = cx2 - cx1
   ch = cy2 - cy1

   if cx2 > img_w:
      print("CROP OUTSIDE OF WIDTH:", cx2)
      cx1 = img_w - cw
      cx2 = cx1 + cw
      print("FIXED :", cx1, cx2)

   if cy2 > img_h:
      cy1 = img_h - ch
      cy2 = img_h + ch

   if cx2 < 0 :
      cx1 = 0 
      cx2 = 0 + cw
   if cy2 < 0 :
      cy1 = 0 + ch
      cy2 = 0 + ch
   
   scx1, scx2 = sorted([cx1, cx2], reverse=False)

   scy1, scy2 = sorted([cy1, cy2], reverse=False)
   print(scx1, scy1, scx2, scy1)
   return(scx1,scy1,scx2,scy2,mid_x,mid_y)


def make_preview_videos(date, json_conf):

   html_header = """

      <style> 
         #theater {
            float: left;
            padding: 20px;
            margin: 10px;
            background-color: #ccc;
            text-align: center;

          }

      </style> 

   """

   row_html = """
      <div id="theater">
         <video id="video" src="VIDEO_FILE" controls="true"></video>
         <label>
         <br/>LABEL</label>
      </div>


   """

   del_link = """
      <span><a href=/pycgi/webUI.py?cmd=override_detect&jsid=FILE_KEY>DEL</a></span>
   """
   #20200728022632000010004-trim-0365 

   html = ""

   year, month, day = date.split("_")
   disp_date = year + "/" + month + "/" + day
   meteor_dir = METEOR_ARC_DIR + year + "/" + month + "/" + day + "/"
   html_outfile = meteor_dir + "report.html"
   print(meteor_dir)
   if cfe(meteor_dir, 1) == 0:
      return()
   crop_files = glob.glob(meteor_dir + "*crop.mp4")
   if len(crop_files) == 0:
      return()
   html_header += "<h1>" + str(len(crop_files)) + " Meteors for " + STATION_ID + " on " + disp_date + "</h1>"
   
   for file in crop_files:
      print(file)
      js_id = file.split("/")[-1]
      js_id = js_id.replace(".mp4", "")
      js_id = js_id.replace("_", "")
      js_id = js_id.replace("-HD-crop", "")
      this_del = del_link.replace("FILE_KEY", js_id)
      thumb_file = file.replace(".mp4", "-thumb.mp4")
 
      js_file = file.replace("-HD-crop.mp4", ".json")
      if cfe(js_file) == 0:
         print("DELETE THESE MATCHING FILES:", js_file)
         continue
      js = load_json_file(js_file)
      xs, ys, azs, els, ras, decs, ints = flatten_frames(js['frames'])
      if "ang_dist" not in js['report']:
         ang_dist, ang_vel = ang_dist_vel(xs,ys)
         ang_sep = angularSeparation(np.radians(ras[0]), np.radians(decs[0]), np.radians(ras[-1]), np.radians(decs[-1]))
         ang_sep = np.degrees(ang_sep)
         print("ANG:", ang_dist, ang_vel)
         js['report']['ang_dist'] = ang_dist
         js['report']['ang_vel'] = ang_vel
         js['report']['ang_sep'] = ang_sep
         print("SAVE JS:", js_file)
         save_json_file(js_file, js)
 
 
      if cfe(thumb_file) == 0:
         make_preview_video(file, json_conf)
      label = "Angular Vel / Dist: " + str(ang_vel)[0:4] + " / " + str(ang_dist)[0:4] + "<br> Angular Separation: " + str(ang_sep) + "<br>" + this_del
      new_row = row_html.replace("VIDEO_FILE", thumb_file)
      new_row = new_row.replace("LABEL", label)
      html += new_row
   out = open(html_outfile, "w")
   out.write(html_header)
   out.write(html)
   out.close()
   print(html)
   print(html_outfile)

def flatten_frames(frames):
   xs = []
   ys = []
   azs = []
   els = []
   ras = []
   decs = []
   ints = []
   for frame in frames:
      xs.append(frame['x'])
      ys.append(frame['y'])
      azs.append(frame['az'])
      els.append(frame['el'])
      ras.append(frame['ra'])
      decs.append(frame['dec'])
      if "intensity" in frame:
         ints.append(frame['intensity'])
      else:
         ints.append(0)
   return(xs,ys,azs,els,ras, decs,ints)

def make_preview_video(video_file, json_conf, width=THUMB_W, height=THUMB_H):
   new_file = video_file.replace(".mp4", "-thumb.mp4")
   cmd = "/usr/bin/ffmpeg -i " + video_file + " -vcodec libx264 -crf 30 -vf 'scale=" + str(width) + ":" + str(height) + "' -y " + new_file + " >/dev/null 2>&1"
   print(cmd)
   os.system(cmd)
   frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 1, [], 1,[])
   stack_image = stack_frames(color_frames)
   new_stack = new_file.replace(".mp4", "-stacked.jpg")
   img2 = cv2.resize(stack_image, (width,height))
   cv2.imwrite(new_stack, img2)

   # add stack to video: 
   final_file = new_file.replace("-thumb", "-temp")
   cmd = "/usr/bin/ffmpeg -loop 1 -framerate 25 -t 1 -i " + new_stack + " -i " + new_file + " -filter_complex '[0:0] [1:0] concat=n=2:v=1:a=0' " + final_file + " >/dev/null 2>&1"
   os.system(cmd)
   cmd = "mv " + final_file + " " + new_file
   os.system(cmd)
   os.system("rm " + new_stack)
       

def find_hd_file(sd_file, sd_start_trim, sd_end_trim, trim_on =1):
   print("SD/HD: ", sd_file)
   print("SD Trim Num: ", sd_start_trim)
   print("SD Trim Num End: ", sd_end_trim)

   dur_frames = sd_end_trim - sd_start_trim 

   (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(sd_file)
   #if sd_start_trim > 1400:
   #   hd_file, hd_trim = eof_processing(sd_file, trim_num, dur)
   #   time_diff_sec = int(trim_num / 25)
   #   if hd_file != 0:
   #      return(hd_file, hd_trim, time_diff_sec, dur)
   offset = int(sd_start_trim) / 25
   meteor_datetime = sd_datetime + datetime.timedelta(seconds=offset)
   hd_glob = "/mnt/ams2/HD/" + sd_y + "_" + sd_m + "_" + sd_d + "_*" + sd_cam + "*.mp4"
   hd_files = sorted(glob.glob(hd_glob))
   for hd_file in hd_files:
      el = hd_file.split("_")
      if len(el) == 8 and "meteor" not in hd_file and "crop" not in hd_file and "trim" not in hd_file:
         hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(hd_file)
         time_diff = meteor_datetime - hd_datetime
         time_diff_sec = time_diff.total_seconds()
         if 0 < time_diff_sec < 60:
            time_diff_sec = time_diff_sec 
            if sd_start_trim == 0:
               sd_start_trim = 1
            if time_diff_sec < 0:
               time_diff_sec = 0
            if trim_on == 1:
               print("TRIMTRIMTIRM")
               print("HD FILE:", hd_file, time_diff_sec)
               hd_trim_start = int(time_diff_sec * 25)
               hd_trim_end = int(time_diff_sec * 25) + int(dur_frames)
               hd_out = hd_file.replace(".mp4", "-trim-" + str(hd_trim_start) + "-HD.mp4")
               if cfe(hd_out) == 0:
                  ffmpeg_splice(hd_file, hd_trim_start, hd_trim_end , hd_out)
            else:
               print("NOOOOOOOOOOOOOOOOOOOOOO TRIMMMMMMMMMMMMMMM")
               hd_trim = None
            return(hd_file, hd_out, time_diff_sec )
   # No HD file was found. Trim out the SD Clip and then upscale it.
   print("NO HD FOUND!")

   time_diff_sec = int(trim_num / 25)
   dur = int(dur) + 1 + 3
   print("UPSCALE FROM SD!", time_diff_sec, dur)
   time_diff_sec = time_diff_sec - 1
   if "passed" in sd_file:
      sd_trim = ffmpeg_trim(sd_file, str(time_diff_sec), str(dur), "-trim" + str(o_trim_num) + "")
   else:
      sd_trim = ffmpeg_trim(sd_file, str(time_diff_sec), str(dur), "-trim-" + str(trim_num) + "-SD-meteor")
   hd_trim = upscale_sd_to_hd(sd_trim)
   if "-SD-meteor-HD-meteor" in hd_trim:
      orig_hd_trim = hd_trim
      hd_trim = hd_trim.replace("-SD-meteor", "")
      hdf = hd_trim.split("/")[-1]
      os.system("mv " + orig_hd_trim + " /mnt/ams2/HD/" + hdf)
      print("HD F: mv " + orig_hd_trim + " /mnt/ams2/HD/" + hdf)
      hd_trim = "/mnt/ams2/HD/" + hdf

   return(sd_file,hd_trim,str(0),str(dur))


def ffmpeg_splice(video_file, start, end, outfile):

   cmd = "/usr/bin/ffmpeg -i " + video_file + " -vf select='between(n\," + str(start) + "\," + str(end) + ")' -reset_timestamps 1 -vsync 0 " + " " + outfile + " > /dev/null 2>&1 "
   #cmd = "/usr/bin/ffmpeg -i " + video_file + " -vf select='between(n\," + str(start) + "\," + str(end) + ")' -reset_timestamps 1 -vsync 0 -start_number " + str(start) + " " + outfile + " > /dev/null 2>&1 "


   print(cmd)
   os.system(cmd)


def scan_stack_file(file, vals = []):

   start_time = time.time()

   fn = file.split("/")[-1]
   day = fn[0:10]
   proc_dir = PROC_BASE_DIR + "/" + day + "/"
   proc_img_dir = proc_dir + "images/"
   proc_data_dir = proc_dir + "data/"
   if cfe(proc_img_dir, 1) == 0:
      os.makedirs(proc_img_dir)
   if cfe(proc_data_dir, 1) == 0:
      os.makedirs(proc_data_dir)
   stack_file = proc_img_dir + fn.replace(".mp4", "-stacked-tn.png")
   json_file = proc_data_dir + fn.replace(".mp4", "-vals.json")

   frames = []
   gray_frames = []
   sub_frames = []

   sum_vals = []
   max_vals = []
   avg_max_vals = []
   pos_vals = []
   fd = []

   stacked_image = None
   fc = 0

   cap = cv2.VideoCapture(file)

   while True:
      grabbed , frame = cap.read()
      #if fc < len(vals):
      #   if vals[fc] == 0  and fc > 20:
      #      print("SKIP FRAME:", fc, vals[fc])
      #      fc = fc + 1
      #      continue

      if not grabbed and fc > 5:
         print(fc)
         break

      try:
         small_frame = cv2.resize(frame, (0,0),fx=.5, fy=.5)
      except:
         print("Bad video file:", file)


      if True:
         gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
         if fc > 0:
            sub = cv2.subtract(gray, gray_frames[-1])
         else:
            sub = cv2.subtract(gray, gray)

         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub)
         if max_val < 10:
            sum_vals.append(0)
            max_vals.append(0)
            pos_vals.append((0,0))
         else:
            _, thresh_frame = cv2.threshold(sub, 15, 255, cv2.THRESH_BINARY)
            #min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(thresh_frame)
            sum_val =cv2.sumElems(thresh_frame)[0]
            #mx = mx * 2
            #my = my * 2
            sum_vals.append(sum_val)
            max_vals.append(max_val)
            if max_val > 1:
               avg_max_vals.append(max_val)
            pos_vals.append((mx,my))
         gray_frames.append(gray)

      if True:
         if max_val > 10 or fc < 10:
            avg_max = np.median(avg_max_vals)
            if avg_max > 0:
               diff = (max_val / avg_max) * 100
            else:
               diff = 0
            if max_val > avg_max * 1.2 or fc <= 10:
               #print("STAK THE FRAME", avg_max, max_val, diff, fc)
               frame_pil = Image.fromarray(small_frame)
               if stacked_image is None:
                  stacked_image = stack_stack(frame_pil, frame_pil)
               else:
                  stacked_image = stack_stack(stacked_image, frame_pil)

      frames.append(frame)
      if fc % 100 == 1:
         print(fc)
      fc += 1
   cv_stacked_image = np.asarray(stacked_image)
   cv_stacked_image = cv2.resize(cv_stacked_image, (PREVIEW_W, PREVIEW_H))
   cv2.imwrite(stack_file, cv_stacked_image)
   print(stack_file)


   vals = {}
   vals['sum_vals'] = sum_vals
   vals['max_vals'] = max_vals
   vals['pos_vals'] = pos_vals
   if cfe(stack_file) == 0:
      #logger("scan_stack.py", "scan_and_stack_fast", "Image file not made! " + stack_file + " " )
      print("ERROR: Image file not made! " + stack_file)
      #time.sleep(10)
   save_json_file(json_file, vals)
   elapsed_time = time.time() - start_time
   #os.system("mv " + file + " " + proc_dir)
   print("saved.", json_file)
   print("MIKE REMOVE EXIT!")
   exit()

   if cfe(stack_file) == 0:
      print("No stack file made!?")
      logger("scan_stack.py", "scan_and_stack_fast", "Image file not made! " + stack_file + " " )
      exit()

   # mv video file if it is not already in proc2 dir
   if "proc2" not in file:
      cmd = "mv " + file + " " + proc_dir
      print(cmd)
   else:
      print("File already in proc dir!")

   print("Elp:", elapsed_time)
   


def load_frames_fast(trim_file, json_conf, limit=0, mask=0,crop=(),color=0,resize=[], sun_status="night"):
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(trim_file)
   cap = cv2.VideoCapture(trim_file)

   #if "HD" in trim_file:
   #   masks = get_masks(cam, json_conf,1)
   #else:
   #   masks = get_masks(cam, json_conf,1)

   masks = []

   mask_imgs, sd_mask_imgs = load_mask_imgs(json_conf)

   if cam in mask_imgs:
      mask_img = mask_imgs[cam]
   else:
      mask_img = None




   if "crop" in trim_file:
      masks = None

   color_frames = []
   frames = []
   subframes = []
   sum_vals = []
   pos_vals = []
   max_vals = []
   frame_count = 0
   last_frame = None
   go = 1
   while go == 1:
      if True :
         _ , frame = cap.read()
         if frame is None:
            if frame_count <= 5 :
               cap.release()
               return(frames,color_frames,subframes,sum_vals,max_vals,pos_vals)
            else:
               go = 0
         else:
            if color == 1:
               if sun_status == "day" and frame_count % 25 == 0:
                  color_frames.append(frame)
               else:
                  color_frames.append(frame)
            if limit != 0 and frame_count > limit:
               cap.release()
               return(frames,color_frames,subframes,sum_vals,max_vals,pos_vals)
            if len(resize) == 2:
               frame = cv2.resize(frame, (resize[0],resize[1]))

            if True: 
               frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
               if mask == 1 and frame is not None:
                  if frame.shape[0] == 1080:
                     hd = 1
                  else:
                     hd = 0
                  #masks = get_masks(cam, json_conf,hd)
                  #frame = mask_frame(frame, [], masks, 5)

               if last_frame is not None:
                  subframe = cv2.subtract(frame, last_frame)
                  if mask_img.shape[0] != subframe.shape[0]: 
                     mask_img = cv2.resize(mask_img,(subframe.shape[1],subframe.shape[0]))
                     print(mask_img.shape, subframe.shape)
                  subframe= cv2.subtract(subframe, mask_img)

                  sum_val =cv2.sumElems(subframe)[0]
                  if sum_val > 10 :
                     _, thresh_frame = cv2.threshold(subframe, 5, 255, cv2.THRESH_BINARY)
                     #cv2.imshow('pepe', thresh_frame)
                     #cv2.waitKey(0)
                     sum_val =cv2.sumElems(thresh_frame)[0]
                  else: 
                     sum_val = 0
                  subframes.append(subframe)


                  if sum_val > 10:
                     min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(subframe)
                  else:
                     max_val = 0
                     mx = 0
                     my = 0
                  if frame_count < 5:
                     sum_val = 0
                     max_val = 0
                  sum_vals.append(sum_val)
                  max_vals.append(max_val)
                  pos_vals.append((mx,my))
               else:
                  blank_image = np.zeros((frame.shape[0] ,frame.shape[1]),dtype=np.uint8)
                  subframes.append(blank_image)
                  sum_val = 0
                  sum_vals.append(0)
                  max_vals.append(0)
                  pos_vals.append((0,0))

            frames.append(frame)
            last_frame = frame
      frame_count = frame_count + 1
   cap.release()
   return(frames, color_frames, subframes, sum_vals, max_vals,pos_vals)

#def get_masks():


#def find_hd_file():

def load_frames_simple(trim_file):
   cap = cv2.VideoCapture(trim_file)
   frames = []
   go = 1
   frame_count = 0
   while go == 1:
      _ , frame = cap.read()
      if frame is None:
         if frame_count <= 5 :
            cap.release()
            return(frames)
         else:
            go = 0
      if frame is not None:
         frames.append(frame)
      if frame_count > 1499:
         go = 0
      frame_count += 1

   cap.release()
   return(frames)


def load_mask_imgs(json_conf):
   mask_files = glob.glob("/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/CAL/MASKS/*mask*.png" )
   mask_imgs = {}
   sd_mask_imgs = {}
   for mf in mask_files:
      mi = cv2.imread(mf, 0)
      omh, omw = mi.shape[:2]
      fn,dir = fn_dir(mf)
      fn = fn.replace("_mask.png", "")
      mi = cv2.resize(mi, (1920, 1080))
      sd = cv2.resize(mi, (omw, omh))
      mask_imgs[fn] = mi
      sd_mask_imgs[fn] = sd
   return(mask_imgs, sd_mask_imgs)

#def trim_crop_video():
