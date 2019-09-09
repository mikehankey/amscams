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


# Add Reduction Table to the template
def get_reduction_table(template,template_marker,meteor_data,template_marker_count):
   
   red_table = """
   <table class="table table-dark table-striped table-hover td-al-m mb-2 pr-5" >
      <thead>
         <tr>
            <th></th><th></th><th>#</th><th>Time</th><th>RA/DEC</th><th>AZ/EL</th><th>X/Y</th><th>w/h</th><th>Max px</th><th colspan="4"></th>
         </tr>
      </thead>
   """

   if "meteor_frame_data" in meteor_data:
      for frame_data in meteor_data['meteor_frame_data']:
         frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el = frame_data
         row_id   = "tr" + str(fn)
         xy_wh    = str(hd_x) + "," + str(hd_y) + " " + str(w) + "," + str(h)
         az_el    = str(az) + "/" + str(el) 
         ra_dec    = str(ra) + "/" + str(dec) 

         fr_id = "fr_row" + str(fn)
         cmp_img_url = prefix  + str(fn) + ".png"
         cmp_img = "<img alt=\"" + str(fn) + "\" width=\"50\" height=\"50\" src=" + cmp_img_url + " class=\"img-fluid select_meteor\">"

         del_frame_link = "javascript:del_frame('" + str(fn) + "','" + meteor_json_file +"')"


         red_table2 = red_table + """
         <tr id="fr_{:s}">
         <td>{:s}</td>
         <td>{:s}</td>
         <td>{:s}</td>
         <td>{:s}</td>
         <td>{:s}</td>
         <td>{:s}</td>
         <td>{:s}</td>
         <td><a class="btn btn-danger btn-sm delete_frame"><i class="icon-delete"></i></a></td>
         <td><a class="btn btn-success btn-sm select_meteor"><i class="icon-target"></i></a></td>
         </tr>
      """.format(str(fn), str(cmp_img ), str(fn), str(frame_time),str(xy_wh), str(max_px),str(ra_dec),str(az_el))

      red_table += "</tbody></table>"

      # Add the Table to the template
      template = template.replace(template_marker, red_table)  

      # Add the # of stars in the template
      template = template.replace(template_marker_count,str(len(meteor_data['meteor_frame_data'])))

   else:
      # No start found
      template = template.replace(template_marker, get_error('No Frame Found - Please, reduce the detection.'))  
      template = template.replace(template_marker_count,"0")

   return template


# Add Stars table and stars count to the template
def get_stars_table(template,template_marker,meteor_data,template_marker_count):
    
   stars_table = """<table class="table table-dark table-striped table-hover td-al-m"><thead>
         <tr>
            <th>Name</th><th>mag</th><th>Cat RA/Dec</th><th>Res &deg;</th><th>Res. Pixels</th>
         </tr>
      </thead>
      <tbody>
   """
   if "cat_image_stars" in meteor_data['cal_params']:
      for star in meteor_data['cal_params']['cat_image_stars']:
         (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist) = star
         
         # Clean the star name
         good_name =  dcname.encode("ascii","xmlcharrefreplace")
         good_name = str(good_name).replace("b'", "")
         good_name = str(good_name).replace("'", "")
         enc_name = good_name 
         ra_dec = str(ra) + "&deg;/" + str(dec) + "&deg;"

         
         # Get the Star row
         stars_table = stars_table + "<tr><td>"+str(enc_name)+"</td><td>"+str(mag)+"</td><td>"+str(ra_dec)+"</td><td>"+str('{0:.4g}'.format(match_dist))+"&deg;</td><td>"+str('{0:.4g}'.format(cat_dist))+"</td></tr>"
    

      stars_table += "</tbody></table>"

      # Add the Table to the template
      template = template.replace(template_marker, stars_table)  

      # Add the # of stars in the template
      template = template.replace(template_marker_count,str(len(meteor_data['cal_params']['cat_image_stars'])))

   else:
      # No start found
      template = template.replace(template_marker, get_error('No Star Found'))  
      template = template.replace(template_marker_count,"0")

   return template



# GENERATES THE REDUCE PAGE METEOR
# from a URL 
# cmd=reduce2
# &video_file=[PATH]/[VIDEO_FILE].mp4
def reduce_meteor2(json_conf,form):
   
   # Debug
   cgitb.enable()

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
   
    # We parse the JSON
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

   # Build the page based on template  
   with open(PAGE_TEMPLATE, 'r') as file:
      template = file.read()
  
   # Fill Template with data
   template = template.replace("{VIDEO_FILE}", str(video_full_path))   # Video File  
   template = template.replace("{STACK}", str(stack))                  # Stack File 
   template = template.replace("{EVENT_START_TIME}", str(meteor_json_file['event_start_time'])) # Start time
   template = template.replace("{EVENT_DURATION}", str(meteor_json_file['event_duration']))     # Duration
   template = template.replace("{EVENT_MAGNITUDE}", str(meteor_json_file['peak_magnitude']))    # Peak_magnitude
   
   template =  get_stars_table(template,"{STAR_TABLE}",meteor_json_file,"{STAR_COUNT}")   # Stars table
   template =  get_reduction_table(template,"{RED_TABLE}",meteor_json_file,'{FRAME_COUNT}') # Reduction Table

   #print(get_stars_table(meteor_json_file))

   # Display Template
   print(template)