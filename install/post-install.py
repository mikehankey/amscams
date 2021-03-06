#!/usr/bin/python3


from pathlib import Path
import os
import json

def load_json_file(json_file):
   try:
      with open(json_file, 'r' ) as infile:
         json_data = json.load(infile)
   except:
      json_data = False
   return json_data


def cfe(file,dir = 0):
   if dir == 0:
      file_exists = Path(file)
      if file_exists.is_file() is True:
         return(1)
      else:
         return(0)
   if dir == 1:
      file_exists = Path(file)
      if file_exists.is_dir() is True:
         return(1)
      else:
         return(0)

json_conf = load_json_file("../conf/as6.json")



if cfe("/var/www/html/pycgi/dist", 1) == 0:
   print("Dist dir missing!")
if cfe("/var/www/html/pycgi/src", 1) == 0:
   print("Dist dir missing!")
if cfe("/var/www/html/pycgi/video_player.html", 0) == 0:
   print("Video Player missing!")
try:
   import sympy
except:
   print("Sympy is missing!")

cmd = "echo '<a href=/pycgi/webUI.py>Login</a>' > /var/www/html/index.html"
print(cmd)
os.system(cmd) 

print("Setup data drive.")
print("Update AMS ID and device lat/lon.")
print("Run File Index Script.")
print("Setup camera numbers!")
print("ADD API_HOST to as6.json!         \"API_HOST\" : \"52.27.42.7\", ")
print("SETUP VPN to as6.json!")

os.system("apt-get install ntp")

# make default masks
for cam in json_conf['cameras']:
   print(json_conf['cameras'][cam]['cams_id'])
   fp = open("../conf/mask-" + json_conf['cameras'][cam]['cams_id'] + ".txt", "a")
   fp.write("0 0 0 0")
   fp.close()
