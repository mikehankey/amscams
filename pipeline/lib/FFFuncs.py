"""

FFFuncs.py - GENERIC functions for ffmpeg

"""
from lib.PipeVideo import load_frames_simple 
from lib.PipeImage import stack_frames
import cv2
import os, sys

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
