import cgitb

from lib.MeteorReducePage import print_error
from lib.MeteorReduce_Tools import * 

PAGE_TEMPLATE = "/home/ams/amscams/pythonv2/templates/manual_reduction_template.html"

def manual_reduction(form):
   
   # Debug
   cgitb.enable()

   # Build the page based on template  
   with open(PAGE_TEMPLATE, 'r') as file:
      template = file.read()

   # Get Video File & Analyse the Name to get quick access to all info
   video_full_path = form.getvalue("video_file")

   # Get the stacks
   stack = get_stacks(analysed_name,clear_cache)
   #print(get_cache_path(analysed_name,"stacks") +"<br>")

   if(video_full_path is not None):
      analysed_name = name_analyser(video_full_path)
   else:
      print_error("<b>You need to add a video file in the URL.</b>")

   print("STACK " + stack)