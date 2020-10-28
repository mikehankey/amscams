"""

FFFuncs.py - GENERIC functions for ffmpeg

"""

from lib.PipeVideo import load_frames_simple 
from lib.PipeImage import stack_frames
from lib.PipeUtil import convert_filename_to_date_cam, cfe
from lib.PipeAutoCal import fn_dir

import cv2
import os, sys, subprocess
import datetime

def snap_video(in_file):
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(in_file)
   w,h,total_frames = ffprobe(in_file)
   date = fy + "_" + fd + "_" + fm

   if True:
      fs = int(fs)
      if fs > 30:
         # seconds to 60
         sec_to_60 = 60 - fs
         sec_to_30 = 90 - fs
      elif fs < 30:
         sec_to_60 = 60 - fs
         sec_to_30 = 30 - fs
      frame_to_60 = int(sec_to_60 * 25)
      frame_to_30 = int(sec_to_30 * 25)
      if frame_to_60 == 1500 or frame_to_60 == 1501:
         frame_to_60 = 0
      date_next_60 = f_datetime + datetime.timedelta(seconds=sec_to_60)
      date_next_30 = f_datetime + datetime.timedelta(seconds=sec_to_30)
      out_60_fn = date_next_60.strftime("%Y_%m_%d_%H_%M_%S_000_") + cam + ".jpg"
      out_30_fn = date_next_30.strftime("%Y_%m_%d_%H_%M_%S_000_") + cam + ".jpg"


   if w == "1920":
      hd_outdir = "/mnt/ams2/SNAPS/" + date + "/1920p/" 
      sd_outdir = "/mnt/ams2/SNAPS/" + date + "/360p/" 
   else:
      hd_outdir = None
      sd_outdir = "/mnt/ams2/SNAPS/" + date + "/360p/" 
   if hd_outdir is not None:
      if cfe(hd_outdir, 1) == 0:
         os.makedirs(hd_outdir)
   if cfe(sd_outdir, 1) == 0:
      os.makedirs(sd_outdir)
   print("60:", frame_to_60, total_frames)
   print("30:", frame_to_30, total_frames)
   if frame_to_60 < total_frames:
      outfile = sd_outdir + out_60_fn
      cmd = """ /usr/bin/ffmpeg -i """ + in_file + """ -vf select="between(n\,""" + str(frame_to_60) + """\,""" + str(frame_to_60+1) + """),setpts=PTS-STARTPTS" -y -update 1 """ + outfile + " >/dev/null 2>&1"
      print(cmd)
      os.system(cmd)
   print("SNAPS:", outfile)
   if frame_to_30 < total_frames:
      outfile = sd_outdir + out_30_fn
      cmd = """ /usr/bin/ffmpeg -i """ + in_file + """ -vf select="between(n\,""" + str(frame_to_30) + """\,""" + str(frame_to_30+1) + """),setpts=PTS-STARTPTS" -y -update 1 """ + outfile + " >/dev/null 2>&1"
      print(cmd)
      os.system(cmd)

   print("SNAPS:", outfile)

def splice_video(in_file, start, end, outfile=None, type="frame"):
   # type = frame or sec 
   print("ff split video")
   # convert start and end frame #s to seconds
   if type == "frame":
      start_sec = start / 25
      end_sec = end / 25
      dur = end_sec - start_sec
   else:
      start_sec = start
      end_sec = end 
      dur = end_sec - start_src
   if outfile is None:
      outfile = in_file.replace(".mp4", "-trim-" + str(start) + ".mp4")

   cmd = "/usr/bin/ffmpeg -y -i  " + video_file + " -ss 00:00:" + str(start_sec) + " -t 00:00:" + str(dur) + " -c copy " + outfile
   os.system(cmd)
   return(outfile)



def list_to_video(list_file, out_file, fps=25, ow=640, oh=360):
   print("ff list to video")
   cmd = "/usr/bin/ffmpeg -r " + str(fps) + " -f concat -safe 0 -i " + list_file + " -c:v libx264 -pix_fmt yuv420p -vf 'scale=" + ow + ":" + oh + "' " + outfile
   os.system(cmd)

   # lower bit rate
   outfile_lr = outfile.replace(".mp4", "-lr.mp4")
   cmd = "/usr/bin/ffmpeg -i " + outfile + " -vcodec libx264 -crf " + crf + " -y " + outfile_lr
   os.system(cmd)
   cmd = "mv " + outfile_lr + " " + outfile
   os.system(cmd)


   print("Made video from list:", out_file)
   return(out_file)

def vid_to_imgs(file, out_dir):
   tmp = file.split("/")[-1]
   fn,ext = tmp.split(".")
   cmd = "/usr/bin/ffmpeg -i " + file + " " + out_dir + fn + "-%04d.png > /dev/null 2>&1"
   os.system(cmd)
   print("Images exported to:", out_dir)

def imgs_to_vid (in_dir, out_file, wild="", fps=25, crf=20, img_type= "jpg"):
   print("FFFuncs: images_to_video")
   wild = "*" + wild + "*." + img_type
   cmd = "/usr/bin/ffmpeg -framerate " + fps + " -pattern_type glob -i '" + in_dir + wild + "' -c:v libx264 -pix_fmt yuv420p -y " + out_file + " >/dev/null 2>&1"
   print(cmd)
   os.system(cmd)
   outfile_lr = out_file.replace(".mp4", "-lr.mp4")
   cmd = "/usr/bin/ffmpeg -i " + out_file + " -vcodec libx264 -crf " + crf + " -framerate " + fps + " -y " + outfile_lr
   print(cmd)
   os.system(cmd)
   cmd = "mv " + outfile_lr + " " + out_file
   os.system(cmd)
   print("VIDEO READY:", out_file)


def slow_stack_video(video_file, OUT_DIR, stack_lim=10):
   
   sd_frames = load_frames_simple(video_file)
   fc = 0
   stack_lim = int(stack_lim)
   vid_fn = video_file.split("/")[-1]
   stack_fn = vid_fn.replace(".mp4", ".jpg")
   short_frames = []
   print(stack_lim)
   for frame in sd_frames:
      short_frames.append(frame)
      if fc % stack_lim == 0 and fc > 0 and len(short_frames) > 0:
         print("Stacking...", frame.shape)
         stack_image = stack_frames(short_frames)
         short_frames = []
         num = "{:04d}".format(fc)
         tfn = stack_fn.replace(".jpg", "-" + str(num) + ".jpg")
         outfile = OUT_DIR + tfn
         cv2.imwrite(outfile, stack_image)
         print(outfile)
      fc += 1



def crop_video(in_file, out_file, crop_box):
   print("ff crop")

def resize_video(in_file, out_file, size, bit_rate=20):
   print("ff resize")

def lower_bitrate(in_file, crf):
   outfile_lr = in_file.replace(".mp4", "-lr.mp4")
   cmd = "/usr/bin/ffmpeg -i " + in_file + " -vcodec libx264 -crf " + str(crf) + " -y " + outfile_lr
   print(cmd)

   os.system(cmd)
   cmd = "mv " + outfile_lr + " " + in_file
   print(cmd)
   os.system(cmd)

def ffprobe(video_file):
   default = [704,576]
   #try:
   if True:
      cmd = "/usr/bin/ffprobe " + video_file + " > /tmp/ffprobe72.txt 2>&1"
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   #except:
   #    print("Couldn't probe.")
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
            tmin = el[1]
            tmin_sec = float(tmin) * 60
            total_frames = (float(tsec)+tmin_sec) * 25
         if "Stream" in line:
            output = line
      fpp.close()
      if output is None:
         print("FFPROBE PROBLEM:", video_file)
         return(0,0,0,0)

      el = output.split(",")
      if "x" in el[3]:
         dim = el[3].replace(" ", "")
         bitrate = el[4]
         bitrate  = bitrate.split(" ")[1]
      elif "x" in el[2]:
         dim = el[2].replace(" ", "")
         bitrate = el[3]
         bitrate  = bitrate.split(" ")[1]

      w, h = dim.split("x")
   return(w,h, bitrate, int(total_frames))

