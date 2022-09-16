import sys
import cv2
import os
import requests
import json
from lib.PipeUtil import load_json_file, save_json_file

json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']


def check_start_ai_server():
   # test the AI server if not running start it and sleep for 30 seconds

   url = "http://localhost:5000/"
   try:
      response = requests.get(url)
      content = response.content.decode()
   except Exception as e:
      if "HTTP" in str(e):
         print("HTTP ERR:", e)
         os.system("/usr/bin/python3.6 AIServer.py > /dev/null 2>&1 & ") 
         print("Starting AI Sleep for 40 seconds.")
         time.sleep(40)

def check_ai_img(image=None, ai_file=None):
   if image is not None and ai_file is None:
      cv2.imwrite("/mnt/ams2/temp.jpg", image)
      image_file = "/mnt/ams2/temp.jpg"
   
   if True:
      url = "http://localhost:5000/AI/METEOR_ROI/?file={}".format(ai_file)
      try:
         response = requests.get(url)
         content = response.content.decode()
      except Exception as e:
         print("HTTP ERR:", e)
   return(content)

if __name__ == "__main__":
   check_start_ai_server()
   image_file = sys.argv[1]
   if os.path.exists(image_file): 
      check_ai_img(None, image_file)
