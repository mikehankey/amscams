import cgitb
import os
import sys
import json

from lib.MeteorReducePage import print_error
from lib.Old_JSON_converter import get_analysed_name
from lib.MeteorReduce_Tools import get_stacks


MANUAL_SYNC_TEMPLATE_STEP1 = "/home/ams/amscams/pythonv2/templates/manual_sync_template_step0.html"

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
 
    # Video File
   if(video_file is None):
      print_error("<b>You need to add a video file in the URL.</b>")
       
   analysed_name = get_analysed_name(json_file)
   
   # No matter if the stack is SD or not
   # we resize it to HD
   stack = get_stacks(analysed_name,True, True)

   # We add it to the template
   template = template.replace("{STACK}", str(stack))  
  
   # Add Video to template
   template = template.replace("{VIDEO}", str(video_file))

   # Add Initial type to template
   template = template.replace("{TYPE}", str(type_file))

   # Add json
   template = template.replace("{JSON}",str(json_file))

   print(template)  