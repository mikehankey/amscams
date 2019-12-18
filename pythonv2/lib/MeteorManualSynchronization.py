import cgitb
import os
import sys
import json

from lib.MeteorReducePage import print_error


MANUAL_SYNC_TEMPLATE_STEP1 = "/home/ams/amscams/pythonv2/templates/manual_reduction_template_step1.html"

# First step of the manual synchronization
def manual_synchronization(form):
   
   # Debug
   cgitb.enable()

   stack_file = form.getvalue('stack')
   video_file = form.getvalue('video')
   type_file  = form.getvalue('type')    # HD or SD
   json_file  = form.getvalue('json')


   # Build the page based on template  
   with open(MANUAL_SYNC_TEMPLATE_STEP1, 'r') as file:
      template = file.read()

   # Here we have the possibility to "empty" the cache, ie regenerate the files (stacks) even if they already exists
   # we just need to add "clear_cache=1" to the URL
   if(form.getvalue("clear_cache") is not None):
      clear_cache = True
   else:
      clear_cache = False

    # Video File
   if(video_file is None):
      print_error("<b>You need to add a video file in the URL.</b>")
      
    
   analysed_name = get_analysed_name(json_file)
   
 
   # No matter if the stack is SD or not
   # we resize it to HD
   stack = get_stacks(analysed_name,clear_cache, True)
   # We add it to the template
   template = template.replace("{STACK}", str(stack))  
  
   # Add Video to template
   template = template.replace("{VIDEO}", str(video_file))

   # Add Initial type to template
   template = template.replace("{TYPE}", str(type_file))

   # Add json
   template = template.replace("{JSON}",str(json_file))

   print(template)  