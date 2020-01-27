import sys 

from lib.FileIO import load_json_file,save_json_file, cfe
from lib.CGI_Tools import redirect_to
from lib.Get_Station_Id import get_station_id
from lib.REDUCE_VARS import METEOR_ARCHIVE


def fix_hd_vid_form(hd_video_file,json_file,cur_video_file):
   if(cfe(hd_video_file)!=1):
      print("ERROR " + hd_video_file + " is missing")
      sys.exit(0)

   if(cfe(json_file)!=1):
      print("ERROR " + json_file + " is missing")
      sys.exit(0)

   # We replace hd_trim by hd_video_file in the json
   md = load_json_file(json_file)
   if(md):
      md['hd_trim'] =  hd_video_file
      save_json_file(json_file,md)

      # Redirect to reduce page (not reduce2!)
      redirect_to('/pycgi/webUI.py?cmd=reduce&video_file='+ cur_video_file)
   else:
      print("ERROR PARSING JSON FILE " + json_file)
      sys.error(0)

def fix_hd_vid(form):
  
   hd_video_file = form.getvalue("hd_video_file")
   json_file = form.getvalue("json_file")
   cur_video_file = form.getvalue("cur_video_file")
   
   fix_hd_vid_real_inline(hd_video_file,cur_video_file,json_file) 


# Inline video fix HD Vid
def fix_hd_vid_real_inline(hd_video_file,cur_video_file,json_file):
    if(cfe(hd_video_file)!=1):
      print("ERROR " + hd_video_file + " is missing")
      sys.exit(0)

   if(cfe(json_file)!=1):
      print("ERROR " + json_file + " is missing")
      sys.exit(0)

   # We replace hd_trim by hd_video_file in the json
   md = load_json_file(json_file)
   if(md):
      md['hd_trim'] =  hd_video_file
      save_json_file(json_file,md)

      # Redirect to reduce page (not reduce2!)
      redirect_to('/pycgi/webUI.py?cmd=reduce&video_file='+ cur_video_file)
   else:
      print("ERROR PARSING JSON FILE " + json_file)
      sys.error(0)



# Fix the old detection where the hd_trim file (defined in the JSON) is messed up
# replace the wrong value of hd_trim by replace(".json", ".mp4") 
def fix_hd_vid_inline(): 
   station_id = get_station_id()
   ms_detect_file = METEOR_ARCHIVE + station_id + "/DETECTS/" + "ms_detects.json" 
   ms_data = load_json_file(ms_detect_file) 
   ct = 0
   for day in sorted(ms_data, reverse=True):
      for f in ms_data[day]:
         meteor_day = f[0:10]
         orig_meteor_json_file = "/mnt/ams2/meteors/" + meteor_day + "/" + f
         video_file = orig_meteor_json_file.replace(".json", ".mp4") 
         json_data = load_json_file(orig_meteor_json_file)
         if 'archive_file' not in json_data:
            if 'hd_trim' in json_data:
               if(json_data['hd_trim'] is not None):
                  if cfe(json_data['hd_trim'])==0:
                     print(json_data['hd_trim']  + " > " + video_file)
                     json_data['hd_trim']  = video_file
                     save_json_file(orig_meteor_json_file,json_data)
                     ct +=1 

   print(str(ct) + " detection have been fixed: the old hd_trim path in the JSON has been replaced by the right one.")