import sys

from lib.FileIO import load_json_file,save_json_file, cfe

def fix_hd_vid(form):

   # DEBUG
   cgitb.enable();

   hd_video_file = form.getvalue("hd_video_file")
   json_file = form.getvalue("json_file")

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
   else:
      print("ERROR PARSING JSON FILE " + json_file)
      sys.error(0)