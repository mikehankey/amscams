#!/usr/bin/python3
import subprocess 
import time
video_dir = "/mnt/ams2/"
rand = time.time()
print ("Content-type: text/html\n\n")



import json

json_file = open('../../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)




print ("<link href='https://fonts.googleapis.com/css?family=Roboto:100,400,300,500,700' rel='stylesheet' type='text/css'>")
print ("<link href='scale.css' rel='stylesheet' type='text/css'>")
print ("<div align=\"center\" class=\"fond\" style=\"width: 100%\">")
print("<h2>Latest View</h2> Updated Once Every 5 Minutes")
print ("<div>")

for cam_num in range(1,7):
   cam_key = 'cam' + str(cam_num)
   cam_ip = json_conf['cameras'][cam_key]['ip']
   sd_url = json_conf['cameras'][cam_key]['sd_url']
   hd_url = json_conf['cameras'][cam_key]['hd_url']
   cams_id = json_conf['cameras'][cam_key]['cams_id']

   print ("<div class=\"style_prevu_kit\" style=\"background-color:#cccccc;\"><img src=/mnt/ams2/latest/" + cams_id + ".jpg?" + str(rand) + " width=640 height=360></div>")
print ("</div>")
print ("</div>")
print ("</div>")
