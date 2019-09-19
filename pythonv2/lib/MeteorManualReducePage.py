import cgitb
import re

from lib.MeteorReducePage import print_error
from lib.MeteorReduce_Tools import *
from lib.REDUCE_VARS import *

PAGE_TEMPLATE = "/home/ams/amscams/pythonv2/templates/manual_reduction_template.html"

def manual_reduction(form):
   
   # Debug
   cgitb.enable()

   # Build the page based on template  
   with open(PAGE_TEMPLATE, 'r') as file:
      template = file.read()

   # Here we have the possibility to "empty" the cache, ie regenerate the files (stacks) even if they already exists
   # we just need to add "clear_cache=1" to the URL
   if(form.getvalue("clear_cache") is not None):
      clear_cache = True
   else:
      clear_cache = False

   # Get Video File & Analyse the Name to get quick access to all info
   video_full_path = form.getvalue("video_file")

   if(video_full_path is not None):

      if("trim" in video_full_path):
         # If we're dealing with an "old" detection, the file name can have 
         # -trimdddd before the extension, we need to remove this part 
         # to properly anaylyse the name
         tmp_video_full_path_matches =  re.finditer(OLD_FILE_NAME_REGEX, video_full_path, re.MULTILINE)
         tmp_fixed_video_full_path = ""
         for matchNum, match in enumerate(tmp_video_full_path, start=1):
            for groupNum in range(0, len(match.groups())): 
               if("-" not in match.group(groupNum)):
                  tmp_fixed_video_full_path = tmp_fixed_video_full_path + "_" + match.group(groupNum)
            groupNum = groupNum + 1
         print('NEW NAME ' + tmp_fixed_video_full_path )
      
      
      #analysed_name = name_analyser(video_full_path)
   else:
      print_error("<b>You need to add a video file in the URL.</b>")

   # Get the stacks
   #stack = get_stacks(analysed_name,clear_cache)
   #print(get_cache_path(analysed_name,"stacks") +"<br>")

  

   #print("STACK " + stack)