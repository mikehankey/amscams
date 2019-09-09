import cgitb

from lib.MeteorReduce_Tools import * 


PAGE_TEMPLATE = "/home/ams/amscams/pythonv2/templates/reducePage.v2.html"

# Return an error message
def get_error(msg):
   return "div class='alert alert-danger'>"+msg+"</div>"

# Display an error message on the page
def print_error(msg):
   print("<div id='main_container' class='container mt-4 lg-l'>"+get_error(msg)+"</div>")
   sys.exit(0)



# GENERATES THE REDUCE PAGE METEOR
# from a URL 
# cmd=reduce2
# &video_file=[PATH]/[VIDEO_FILE].mp4
def reduce_meteor2(json_conf,form):
   
   # Debug
   cgitb.enable()

   # Build the page based on template  
   with open(PAGE_TEMPLATE, 'r') as file:
      template = file.read()

   # Here we have the possibility to "empty" the cache, ie regenerate the files even if they already exists
   # we just need to add "clear_cache=1" to the URL
   if(form.getvalue("clear_cache") is not None):
      clear_cache = True
   else:
      clear_cache = False

   # Get Video File & Analyse the Name to get quick access to all info
   video_full_path = form.getvalue("video_file")

   if(video_full_path is not None):
      analysed_name = name_analyser(video_full_path)
   else:
      print_error("<b>You need to add a video file in the URL.</b>")

   # Test if the name is ok
   if(len(analysed_name)==0):
      print_error(video_full_path + " <b>is not valid video file name.</b>")
   elif(os.path.isfile(video_full_path) is False):
      print_error(video_full_path + " <b>not found.</b>")
  
   # Is it HD? 
   HD = ("HD" in analysed_name)
   
   # Retrieve the related JSON file that contains the reduced data
   meteor_json_file = video_full_path.replace(".mp4", ".json") 

   # Does the JSON file exists?
   if(os.path.isfile(meteor_json_file) is False):
      print_error(meteor_json_file + " <b>not found.</b><br>This detection may had not been reduced yet or the reduction failed.")
   
   # Add the JSON Path to the template
   template = template.replace("{JSON_FILE}", str(meteor_json_file))   # Video File  

   # Parse the JSON
   meteor_json_file = load_json_file(meteor_json_file) 

   # Get the HD frames
   HD_frames = get_HD_frames(analysed_name,clear_cache)
   #print(get_cache_path(analysed_name,"frames") +"<br>")

   # Get the stacks
   stack = get_stacks(analysed_name,clear_cache)
   #print(get_cache_path(analysed_name,"stacks") +"<br>")
    
   # Get the thumbs (cropped HD frames)
   thumbs = get_thumbs(analysed_name,meteor_json_file,HD,HD_frames,clear_cache)
   #print(get_cache_path(analysed_name,"cropped") +"<br>")

  
  
   # Fill Template with data
   template = template.replace("{VIDEO_FILE}", str(video_full_path))   # Video File  
   template = template.replace("{STACK}", str(stack))                  # Stack File 
   template = template.replace("{EVENT_START_TIME}", str(meteor_json_file['event_start_time'])) # Start time
   template = template.replace("{EVENT_DURATION}", str(meteor_json_file['event_duration']))     # Duration
   template = template.replace("{EVENT_MAGNITUDE}", str(meteor_json_file['peak_magnitude']))    # Peak_magnitude
   
   #template =  get_stars_table(template,"{STAR_TABLE}",meteor_json_file,"{STAR_COUNT}")   # Stars table
   #template =  get_reduction_table(analysed_name,template,"{RED_TABLE}",meteor_json_file,'{FRAME_COUNT}') # Reduction Table

   #print(get_stars_table(meteor_json_file))

   # Display Template
   print(template)