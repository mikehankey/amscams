import glob
import re
import cgitb

from datetime import datetime, timedelta
from lib.Get_Cam_ids import get_the_cam_ids

PAGE_TEMPLATE = "/home/ams/amscams/pythonv2/templates/browse_minutes.html"
PERIODS = ['minute','hour','day']

# Build the Cam multi-selector & periods
def get_select(selected_cam_ids,_type):
   toReturn = ""

   if(_type == 'cams'):
      cam_ids = get_the_cam_ids()
   else:
      cam_ids = PERIODS

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

   selected_start_date = form.getvalue('start_date') 
   selected_end_date = form.getvalue('end_date') 
   selected_period   = form.getvalue('period')
   selected_cam_ids = form.getvalue('cams_ids')
   
   # Build the page based on template  
   with open(PAGE_TEMPLATE, 'r') as file:
      template = file.read()

   # Default dates 
   if (selected_start_date is None and selected_end_date is None):
      selected_start_date = datetime.now()- timedelta(days=1)
      selected_end_date   = datetime.now() 
   else:
      selected_start_date = datetime.strptime(selected_start_date,"%Y/%m/%d") 
      selected_end_date  = datetime.strptime(selected_end_date,"%Y/%m/%d") 
   
   template = template.replace("{START_DATE}",start_datetime.strftime("%Y/%m/%d"));
   template = template.replace("{END_DATE}",end_datetime.strftime("%Y/%m/%d"));

   # CAM IDS
   if(selected_cam_ids is not None):
      selected_cam_ids = selected_cam_ids.split(',')
   else:
      selected_cam_ids = []

   # PERIOD
   if(selected_period is not None):
      selected_period = [selected_period]
   else:
      selected_period = PERIODS[0] # See PERIODS 


   # Build the cam ids dd
   template = template.replace('{CAM_IDS}',get_select(selected_cam_ids,'cams'))

   # Build the period
   template = template.replace('{PERIODS}',get_select(selected_period,'periods'))
   
   # Display Template
   print(template)

