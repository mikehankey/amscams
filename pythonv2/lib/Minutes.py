import glob
import re
import cgitb

from datetime import datetime, timedelta
from lib.Get_Cam_ids import get_the_cam_ids
from lib.Minutes_Tools import *

PAGE_TEMPLATE = "/home/ams/amscams/pythonv2/templates/browse_minutes.html"
PERIODS = ['minutes','hours','days']
 
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



# Transform the result of a minute_index to get the full path to the stackeds
# minute_file is actually the hour of the stack (ex: 11:16:26.000) > 2020_01_05_00_00_09_000_010038-stacked-tn.png	
def get_details(cam_id,year,month,day,minute_file):
   return str(year)+'_'+str(month)+'_'+str(day)+minute_file.replace(':','_').replace('.','_') + '-' + MINUTE_STACK_EXT + '.png'

# Get Results from the minutes indexes
def get_minute_index_res(selected_start_date, selected_end_date,selected_period,selected_cam_ids):
   
   # Get the minute index of the selected or current year / month / day
   # for the END DATE
   cur_date = selected_end_date
   json_index =  get_daily_index(cur_date.day,cur_date.month,cur_date.year)
 
   how_many_cams = len(selected_cam_ids)
   res = []
 
   
   while(json_index is not None and cur_date>=selected_start_date):
   
      json_data = load_json_file(json_index)
      print(json_data)
      sys.exit(0)
      # Res per cams
      for cam in json_data['cams']:
         print(cam['cam'])

      
      
      
      
      sys.exit(0)
      cur_date = cur_date - timedelta(1)
      json_index =  get_daily_index(cur_date.day,cur_date.month,cur_date.year) 

   print(res)


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
   
   # CAM IDS
   if(selected_cam_ids is not None):
      selected_cam_ids = sorted(selected_cam_ids.split(','))  # Sorted for a best view on the page
   else:
      selected_cam_ids = get_the_cam_ids() # ALL BY DEFAULT

   # PERIOD
   if(selected_period is not None):
      selected_period = [selected_period]
   else:
      selected_period = PERIODS[0] # See PERIODS 
 
   # Build the period picker 
   template = template.replace("{START_DATE}",selected_start_date.strftime("%Y/%m/%d"));
   template = template.replace("{END_DATE}",selected_end_date.strftime("%Y/%m/%d"));

   # Build the cam ids dd
   template = template.replace('{CAM_IDS}',get_select(selected_cam_ids,'cams'))

   # Build the period
   template = template.replace('{PERIODS}',get_select(selected_period,'periods'))
   
   # Retrieve the results
   res = get_minute_index_res(selected_start_date, selected_end_date,selected_period,selected_cam_ids)

   # Display Template
   print(template)

