import sys
import cgitb
import json

from lib.REDUCE_VARS import *

# input: video,x_start,y_start,x_end,y_end, stack
# output: the cropped frames 
# Note: the stack is needed because is the only file name we're sure has the proper format
def create_crop_frames(form):

   # Debug
   cgitb.enable() 
   
   # Get the Data
   video_file = form.getvalue('video')
   x_start = form.getvalue('x_s')
   y_start = form.getvalue('y_s')
   x_end = form.getvalue('x_e')
   y_end = form.getvalue('y_e')
   stack = formet.getvalue('stack')

   # Get All Frames -y -hide_banner -loglevel panic
   cmd = 'ffmpeg   -i ' + analysed_name['full_path'] + ' -s ' + str(HD_W) + "x" + str(HD_H) + ' ' +  destination + EXT_HD_FRAMES + '%04d' + '.png' 
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   #cmd = 'ffmpeg -y -hide_banner -loglevel panic  -i ' + video_file + ' -s ' + str(HD_W) + "x" + str(HD_H) + ' ' +  destination + EXT_HD_FRAMES + '%04d' + '.png' 
   #output = subprocess.check_output(cmd, shell=True).decode("utf-8")

   #return glob.glob(destination+"*"+EXT_HD_FRAMES+"*.png")

