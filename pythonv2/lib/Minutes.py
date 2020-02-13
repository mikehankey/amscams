import glob
import re
import cgitb

from lib.Get_Cam_ids import get_the_cam_ids

PAGE_TEMPLATE = "/home/ams/amscams/pythonv2/templates/browse_minutes.html"


# Build the Cam multi-selector
def get_cam_ids(selected_cam_ids):
   toReturn = ""
   cam_ids = get_the_cam_ids()

   # By Default All cams are selected
   if(len(selected_cam_ids)==0):
      selected_cam_ids = cam_ids

   for cam_id in cam_ids:
      if(cam_id in selected_cam_ids):
         opts = "selected"
      else:
         opts = ""
      toReturn += "<option value='"+cam_id+"' "+opts+">"+cam_id+"</option>"
   return toReturn


# Generate Browse Minute page
def browse_minute(form):
   # Debug
   cgitb.enable()

   period   = form.getvalue('period')
   selected_cam_ids = form.getvalue('cams_ids')

   if(selected_cam_ids is not None):
      selected_cam_ids = selected_cam_ids.split(',')
   else:
      selected_cam_ids = []


   # Build the page based on template  
   with open(PAGE_TEMPLATE, 'r') as file:
      template = file.read()

   # Build the cam ids dd
   template = template.replace('{CAM_IDS}',get_cam_ids(selected_cam_ids))
   
   # Display Template
   print(template)

