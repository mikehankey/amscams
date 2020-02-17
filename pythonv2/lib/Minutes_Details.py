import cgitb
 
from lib.Minutes_Tools import *
from datetime import datetime

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
   full_path_bigger = MINUTE_FOLDER +  + os.sep + analysed_minute['year'] + os.sep + str(analysed_minute['month']).zfill(2) + "_" + str(analysed_minute['day']).zfill(2) + os.sep + IMAGES_MINUTE_FOLDER + os.sep +  analysed_minute['full'].replace(MINUTE_TINY_STACK_EXT,'')
   print(full_path_bigger) 

   print(template)
   print(analysed_minute)

