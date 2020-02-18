import cgitb
import os
import glob
import sys
import subprocess 

from lib.Cleanup_Json_Conf import PATH_TO_CONF_JSON
from lib.CGI_Tools import print_error
from lib.FileIO import cfe
from lib.Minutes_Tools import whatever_minute_name_analyser, minute_name_analyser, MINUTE_STACK_EXT, MINUTE_HD_VID_FOLDER, MINUTE_SD_FOLDER, DATA_MINUTE_SD_FOLDER, IMAGES_MINUTE_SD_FOLDER
from lib.Minutes_Details import HD_TMP_STACK_EXT
from lib.Frame_Tools import load_frames_fast

MANUAL_RED_MINUTE_PAGE_TEMPLATE_STEP1 = "/home/ams/amscams/pythonv2/templates/minute_manual_reduction_template_step0.html"


# FIRST STEP: WE DEFINE THE ROI
def define_ROI(form):

   # Get stack
   stack = form.getvalue('stack')

   # Build the page based on template  
   with open(MANUAL_RED_MINUTE_PAGE_TEMPLATE_STEP1, 'r') as file:
      template = file.read()

   # We dont have any other info for the page
   template = template.replace("{STACK}",stack) 
    
   # Display Template
   print(template) 


# SECOND STEP: GET HD 
def automatic_detect(form):

   cgitb.enable()
   
   # In form we should have
   stack = form.getvalue('stack')
   # ROI
   x = form.getvalue('x_start')
   y = form.getvalue('y_start')
   w = form.getvalue('w')
   h = form.getvalue('h')

   # Get Org Stack folder
   org_stack_folder = os.path.dirname(os.path.abspath(stack))
   org_stack_folder = org_stack_folder.replace(IMAGES_MINUTE_SD_FOLDER,DATA_MINUTE_SD_FOLDER)
 
   # Do we have a HD version on the video of this stack?
   # Ex: 
   # stack    = /mnt/ams2/SD/proc2/2020_02_17/images/2020_02_17_11_12_20_000_010039_HD_tmp_stack.png
   # SD video => /mnt/ams2/SD/proc2/2020_02_17/2020_02_17_11_12_20_000_010039.mp4
   # HD video => /mnt/ams2/HD/2020_02_17_11_12_XX_XXX_010039.mp4
   analysed_minute = minute_name_analyser(stack.replace(HD_TMP_STACK_EXT, MINUTE_STACK_EXT+'.png').replace("-stacked-stacked","-stacked"))
  
   # Search for HD
   HD_path = MINUTE_HD_VID_FOLDER + os.sep + analysed_minute['full'].replace( MINUTE_STACK_EXT+'.png','.mp4')
   HD_found = False
   SD_found = False

   # Search same path:
   if(cfe(HD_path)==1):
      HD_found = True 

   # Search for almost the same path (same hour, same minute)
   if(HD_found is False):
      tmp_almost_path = MINUTE_HD_VID_FOLDER + os.sep + analysed_minute['year'] + '_' + analysed_minute['month'] + '_' + analysed_minute['day'] + '_' + analysed_minute['hour'] + '_' + analysed_minute['min'] + '_' + '*' +  analysed_minute['cam_id'] + '*' + '.mp4'
      filelist = glob.glob(tmp_almost_path)
      if(len(filelist)==1):
         HD_found = True 
         HD_path = filelist[0]

   # HD hasn't been found, we search for SD vid and we resize it
   if(HD_found is False):
      tmp_almost_path = MINUTE_SD_FOLDER + os.sep + analysed_minute['year'] + '_' + analysed_minute['month'] + '_' + analysed_minute['day']  + os.sep + analysed_minute['year'] + '_' + analysed_minute['month'] + '_' + analysed_minute['day'] + '_' + analysed_minute['hour'] + '_' + analysed_minute['min'] + '_' + '*' +  analysed_minute['cam_id'] + '*' + '.mp4'
      filelist = glob.glob(tmp_almost_path)
      if(len(filelist)==1):
         SD_found = True 
         SD_path = filelist[0] 

   if(HD_found is False and SD_found is False):
      print_error('Impossible to find the related SD or HD video.') 

   # Now we need to crop the frames 
   if(HD_found is True):
      input_path = HD_path
   elif(SD_found is True):
      input_path = SD_path

   # The cropped video is tmp stored under /mnt/ams2/SD/proc2/[YYYY_MM_DD]/data/
   output_path = input_path.replace('.mp4','-cropped.mp4')
   output_path = org_stack_folder + os.sep + os.path.basename(output_path)
      
   # Create cropped video
   cmd = 'ffmpeg -y -i  '+input_path+' -filter:v "crop='+w+':'+h+':'+x+':'+y+'" '+ output_path
   
   # Test if it's doable
   try:
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")   
   except subprocess.CalledProcessError as e:
      print_error("Command " + cmd + "  return on-zero exist status: " + str(e.returncode))

   #  load_frames_fast to get subframes and sum/max val info this also includes (mx,my) brightest point in subframe .
   analysed_minute_name = whatever_minute_name_analyser(output_path)
   hd_frames,hd_color_frames,hd_subframes,sum_vals,max_vals = load_frames_fast(output_path, analysed_minute_name, 0, 0, None, 0,[])
   
   
   #print("<br>HD FRAMES<br>")
   #print(hd_frames)
   #print("<br>HD COLOR FRAMES<br>")
   #print(hd_color_frames)
   #print("<br>HD SUB FRAMES<br>")
   #print(hd_subframes)
   #print("<br>HD sum_vals<br>")
   #print(sum_vals)
   #print("<br>HD max_vals<br>")
   #print(max_vals)
 
 
  

         


