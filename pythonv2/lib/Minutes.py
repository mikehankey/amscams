import re
import cgitb

from datetime import datetime, timedelta
from lib.Get_Cam_ids import get_the_cam_ids
from lib.Meteor_Index import get_meteor_date_cam
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
def get_min_details(cam_id,year,month,day,minute_file):
   return MINUTE_SD_FOLDER +  os.sep + str(year) + '_' + str(month)+'_'+str(day) + os.sep + IMAGES_MINUTE_SD_FOLDER + os.sep + str(year)+'_'+str(month)+'_'+str(day)+'_'+minute_file.replace(':','_').replace('.','_') + '_' + cam_id + MINUTE_STACK_EXT + '.png'



# Get Results from the minutes indexes
def get_minute_index_res(selected_end_date,selected_cam_ids):
   
   # Get the minute index of the selected or current year / month / day
   # for the END DATE
   cur_date = selected_end_date
   json_index =  get_daily_index(cur_date.day,cur_date.month,cur_date.year)
   res = [] 
   if(json_index is not None):
  
      #while(json_index is not None and cur_date>=selected_start_date):
      
      json_data = load_json_file(json_index)
      date = json_data['date'] # Format Y/M/D
      date = datetime.strptime(date,"%Y/%m/%d") 

      for cam in json_data['cams']: 
         links = []
      
         for _min in cam['min']:
            links.append(_min) 
         res.append({"cam":cam['cam'],"links":links})
         
      #cur_date = cur_date - timedelta(1)
      json_index =  get_daily_index(cur_date.day,cur_date.month,cur_date.year) 
   
   return res,cur_date.day,cur_date.month,cur_date.year


# Get Cam Res from JSON
def get_cam_res(res,cam_id,cur_index):
   for r in res:
      if(r['cam']==cam_id):
         try:
            return r['links'][cur_index]
         except:
            return False
   return False

# Create HTML version of the results
def create_minute_html_res(res,cam_ids,year,month,day, meteor_only):

   how_many_cams = len(cam_ids)
   cam_ids = sorted(cam_ids)
   cam_title = ""

   # First line: all the cams_ids
   for cam_id in cam_ids:
      cam_title += "<div style='width:100%; max-width: 350px;'><h2 style='margin-right:1rem'>Cam#" + str(cam_id) + " <button style='padding: .2rem .5rem;float: right;' class='btn btn-primary play_anim_thumb' data-rel='"+ str(cam_id) +"'><span class='icon-youtube'></span></button></h2></div>" 
 
   toReturn = "<div class='d-flex justify-content-around'>"+ cam_title + "</div>"

   # The other lines: the detection per cam
   cur_index = 0
   how_many_false = 0
   we_have_res = 1

   # Get Meteor Detection info
   meteor_index = get_meteor_date_cam(day,month,year)
   
   
   while(we_have_res==1):
      toReturn += "<div class='d-flex justify-content-around'>"
      for cam_id in cam_ids:

         cam_res = get_cam_res(res,cam_id,cur_index)
 
         if(cam_res is not False):
            t = get_min_details(cam_id,year,month,day,cam_res)

            # Do we have a meteor there?
            index = os.path.basename(t).replace(MINUTE_STACK_EXT+'.png','')
            how_many_meteors = 0

            if(index in meteor_index):
               how_many_meteors = len(meteor_index[index])

            extra_class = ''
            if(how_many_meteors!=0):
               extra_class = 'meteor'

            if(meteor_only == False):
               toReturn += "<div class='minute "+extra_class+"'><a class='d-block' href='webUI.py?cmd=minute_details&stack="+t+"'><img src='"+t+"' data-rel='"+cam_res+"' class='img-fluid cam_"+str(cam_id)+"'/></a><span style='font-size:.75rem'>"+cam_res+"</span></div>"
            elif(meteor_only== True and extra_class == 'meteor'):
               toReturn += "<div class='minute "+extra_class+"'><a class='d-block' href='webUI.py?cmd=minute_details&stack="+t+"'><img src='"+t+"' data-rel='"+cam_res+"' class='img-fluid cam_"+str(cam_id)+"'/></a><span style='font-size:.75rem'>"+cam_res+"</span></div>"


         else:
            toReturn += "<div style='padding: 0 1rem 1rem 0;width: 100%;height: 169px; background-color: transparent;max-width: calc(250px + 1rem);'></div>"
            how_many_false+=1

         if(how_many_false==len(cam_ids)):
            we_have_res=0  

      cur_index+=1
      toReturn += "</div>"
   
    
   
   return toReturn

# Generate Browse Minute page
def browse_minute(form):
   # Debug
   cgitb.enable()

   selected_end_date = form.getvalue('limit_day') 
   selected_period   = form.getvalue('period')
   selected_cam_ids  = form.getvalue('cams_ids')
   meteor_only       = form.getvalue('meteor')
   
   # Build the page based on template  
   with open(PAGE_TEMPLATE, 'r') as file:
      template = file.read()

   # Meteor_only
   if(meteor_only is not None):
      if(meteor_only == 1):
         meteor_only = True    
      else:
         meteor_only = False
   else:
      meteor_only = False     

   # Default dates 
   if (selected_end_date is None): 
      selected_end_date = datetime.now() - timedelta(days=1)
   else:
      selected_end_date = datetime.strptime(selected_end_date,"%Y_%m_%d") 
   
   # CAM IDS
   if(selected_cam_ids is not None):
      selected_cam_ids = sorted(selected_cam_ids.split(','))  # Sorted for a best view on the page
   else:
      selected_cam_ids = get_the_cam_ids() # ALL BY DEFAULT

   # PERIOD
   #if(selected_period is not None):
   #   selected_period = [selected_period]
   #else:
   #   selected_period = PERIODS[0] # See PERIODS 
 
   # Build the date picker 
   template = template.replace("{END_DATE}",selected_end_date.strftime("%Y/%m/%d"));

   # Build the cam ids dd
   template = template.replace('{CAM_IDS}',get_select(selected_cam_ids,'cams'))

   # Build the period
   #template = template.replace('{PERIODS}',get_select(selected_period,'periods'))
   
   # Retrieve the results
   res, day, month, year = get_minute_index_res(selected_end_date,selected_cam_ids,meteor_only)
 
   # Create HTML results
   if(len(res)>0):
      res = create_minute_html_res(res,selected_cam_ids,year,str(month).zfill(2),str(day).zfill(2))
   else:
      res = "<div class='alert alert-danger'>No minute stacks found for " + selected_end_date.strftime("%Y/%m/%d") + '.</div>'
   
   template = template.replace('{RES}',res)
   
   # Display Template
   print(template)

