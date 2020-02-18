import cgitb 
import subprocess 

from datetime import datetime

from lib.MeteorReduce_Tools import get_stacks
from lib.CGI_Tools import print_error
from lib.FileIO import cfe 
from lib.Minutes_Tools import *
from lib.VIDEO_VARS import HD_H, HD_W

PAGE_TEMPLATE = "/home/ams/amscams/pythonv2/templates/minute_details.html"
HD_TMP_STACK_EXT = "_HD_tmp_stack.png"

# Temporarily resize SD Stack
def getResizeSDStack(_input):
   # Here the stack is SD, we resize it to HD for a better view in the meteor track picker
   tmp_pseudo_HD_stack = _input.replace('.png',HD_TMP_STACK_EXT)
   
   if(cfe(tmp_pseudo_HD_stack)):
      return tmp_pseudo_HD_stack
   else:
      # We create it!
      cmd = "ffmpeg -y -i " +  _input + " -vf scale="+str(HD_W)+":"+str(HD_H)+" " + tmp_pseudo_HD_stack
       # Test if it's doable
   try:
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")    
   except subprocess.CalledProcessError as e:
      #print("Command " + cmd + "  return on-zero exist status: " + e.returncode)
      return False
   
   return tmp_pseudo_HD_stack
 

def minute_details(form):
   # Debug
   cgitb.enable()
   stack = form.getvalue('stack') 

   analysed_minute = minute_name_analyser(stack)
   string_date = analysed_minute['year']+'/'+analysed_minute['month']+'/'+analysed_minute['day']+' '+analysed_minute['hour']+':'+analysed_minute['min']+':'+analysed_minute['sec']
   date = datetime.strptime(string_date,"%Y/%m/%d %H:%M:%S") 
   
   # Build the page based on template  
   with open(PAGE_TEMPLATE, 'r') as file:
      template = file.read()

   template = template.replace('{DATE}',string_date)
   template = template.replace('{CAM_ID}',analysed_minute['cam_id'])

   # Do we have the bigger version (without -tn)?
   full_path_bigger = MINUTE_FOLDER +  os.sep + analysed_minute['year'] + '_' + str(analysed_minute['month']).zfill(2) + "_" + str(analysed_minute['day']).zfill(2) + os.sep + IMAGES_MINUTE_FOLDER + os.sep +  analysed_minute['full'].replace(MINUTE_TINY_STACK_EXT,'')
   
   if(cfe(full_path_bigger)!=1):
      full_path_bigger = stack
   
   # Here the stack is SD, we resize it to HD for a better view in the meteor track picker
   HD_stack = getResizeSDStack(full_path_bigger)
   if(HD_stack is not False):
      full_path_bigger = HD_stack

   template = template.replace('{STACK}',full_path_bigger)
    
   # SEARCH FOR RELATED VIDEO
   video_full_path  = MINUTE_FOLDER +  os.sep + analysed_minute['year'] + '_'+ str(analysed_minute['month']).zfill(2) + "_" + str(analysed_minute['day']).zfill(2) + os.sep + analysed_minute['full'].replace('-'+MINUTE_STACK_EXT+'.png','.mp4')
   
   if(cfe(video_full_path)!=1):
      print_error(video_full_path + " not FOUND")

   template = template.replace('{VIDEO}',video_full_path)
 
   print(template)