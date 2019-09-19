from lib.REDUCE_VARS import *

# input: video,x_start,y_start,x_end,y_end, stack
# output: the cropped frames 
# Note: the stack is needed because is the only file name we're sure has the proper format
def create_crop_frames(form):
   video_file = form.getvalue('video')
   x_start = form.getvalue('x_s')
   y_start = form.getvalue('y_s')
   x_end = form.getvalue('x_e')
   y_end = form.getvalue('y_e')
   stack = formet.getvalue('stack')

