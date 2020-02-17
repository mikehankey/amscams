import cgitb
import glob

from datetime import datetime

from lib.CGI_Tools import print_error
from lib.FileIO import cfe 
from lib.Minutes_Tools import *

PAGE_TEMPLATE = "/home/ams/amscams/pythonv2/templates/minute_details.html"

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

   # Where is the bigger version (without -tn)
   full_path_bigger = MINUTE_FOLDER +  os.sep + analysed_minute['year'] + os.sep + str(analysed_minute['month']).zfill(2) + "_" + str(analysed_minute['day']).zfill(2) + os.sep + IMAGES_MINUTE_FOLDER + os.sep +  analysed_minute['full'].replace(MINUTE_TINY_STACK_EXT,'')
   
   if(cfe(full_path_bigger)!=1):
      print_error('Impossible to find the full version of the SD stack ('+full_path_bigger+')')
   
   template = template.replace('{STACK}',full_path_bigger)


   # Search for related video

   #Build path for glob
   video_full_path  = MINUTE_FOLDER +  os.sep + analysed_minute['year'] + os.sep + str(analysed_minute['month']).zfill(2) + "_" + str(analysed_minute['day']).zfill(2) + os.sep + VIDEOS_FAILED_MINUTE_FOLDER + os.sep
   video_full_path  += analysed_minute['full'].replace('.png','.mp4').replace(analysed_minute['sec'],'*').replace(analysed_minute['min'],'*').replace('tn','')
   print("FULL PATH " + video_full_path + "<br>")
   
   
   
   #analysed_minute['full'].replace(MINUTE_TINY_STACK_EXT,'-trim*').replace('.png','.mp4').replace(analysed_minute['sec'],'*').replace(analysed_minute['min'],'*').replace(analysed_minute['ms'],'*')
   print("FULL PATH " + video_full_path + "<br>")
   r = glob.glob(video_full_path)
   print(r)
  
   
   if(cfe(video_full_path)==1):
      print(video_full_path)
   else:
      print(video_full_path + " not FOUND")

   print(template)
   print(analysed_minute)

