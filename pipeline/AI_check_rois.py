"""
run with python3.6 + Tensorflow or equiv build. 
"""

import sys
import os
import requests
import json
from lib.PipeUtil import load_json_file, save_json_file

json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']
day = sys.argv[1]

mdir = "/mnt/ams2/meteors/" + day + "/"
msdir = "/mnt/ams2/METEOR_SCAN/" + day + "/"
ai_dict_file = mdir + station_id + "_" + day + "_AI_DICT.info" 
if os.path.exists(ai_dict_file):
   ai_dict = load_json_file(ai_dict_file)
else:
   ai_dict = {}

# test the AI server if not running start it and sleep for 30 seconds

url = "http://localhost:5000/"
try:
   response = requests.get(url)
   content = response.content.decode()
   print(content)
except Exception as e:
   if "HTTP" in str(e):
      print("HTTP ERR:", e)
      os.system("/usr/bin/python3.6 AIServer.py > /dev/null 2>&1 & ") 
      print("Starting AI Sleep for 40 seconds.")
      time.sleep(40)

files = os.listdir(mdir)
meteor_json_files = []
for ff in files:
   if "json" in ff and "reduced" not in ff and os.path.exists(mdir + ff.replace(".json", ".mp4")):
      print(ff)
      # this should be a unique meteor-json / id
      meteor_json_files.append(ff)

for mj in meteor_json_files:
   roi_file = msdir + station_id + "_" + mj.replace(".json", "-ROI.jpg")
   if os.path.exists(roi_file) is True:
      print("ROI FILE EXISTS!", roi_file)

      if mj not in ai_dict or True:
         url = "http://localhost:5000/AI/METEOR_ROI/?file={}".format(roi_file)
         try:
            response = requests.get(url)
            content = response.content.decode()
            ai_dict[mj] = json.loads(content)
            print(content)
         except Exception as e:
            print("HTTP ERR:", e)


      else:
         print("Did it already", mj)
   else:
      print("NO ROI FILE EXISTS!", roi_file)
save_json_file(ai_dict_file, ai_dict)
print("Saved AI Dictionary:", ai_dict_file)
