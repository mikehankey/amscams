#!/usr/bin/python3

import glob
import sys
import subprocess
import os
import time

import json
from caliblib import load_json_file

json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)



video_dir = "/mnt/ams2"


def ping_cam(cam_num):
   #config = read_config("conf/config-" + str(cam_num) + ".txt")
   config = load_json_file("../conf/as6.json")

   key = "cam" + str(cam_num)
   cmd = "ping -c 1 " + config['cameras'][key]['ip']

   response = os.system(cmd)
   if response == 0:
      print ("Cam is up!")
      return(1)
   else:
      print ("Cam is down!")
      return(0)


def check_running(cam_num, type):

   cam_key = 'cam' + str(cam_num)
   cam_ip = json_conf['cameras'][cam_key]['ip']

   if type == "HD":
      cmd = "ps -aux |grep \"ffmpeg\" | grep \"HD\" | grep " + cam_ip + " | grep -v grep | wc -l"
   else: 
      cmd = "ps -aux |grep \"ffmpeg\" | grep \"SD\" | grep " + cam_ip + " | grep -v grep | wc -l"
   print(cmd)
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   output = int(output.replace("\n", ""))
   return(int(output))


def start_capture(cam_num):

   ping_ok = ping_cam(cam_num)
   if ping_ok == 0:
      print("NO PING ON CAM!", cam_num)
      return()

   cam_key = 'cam' + str(cam_num)
   cam_ip = json_conf['cameras'][cam_key]['ip']
   sd_url = json_conf['cameras'][cam_key]['sd_url']
   hd_url = json_conf['cameras'][cam_key]['hd_url']
   cams_id = json_conf['cameras'][cam_key]['cams_id']
   running = check_running(cam_num, "HD")
   if running == 0:
      cmd = "/usr/bin/ffmpeg -rtsp_transport tcp -r 25 -i 'rtsp://" + cam_ip + hd_url + "' -c copy -map 0 -f segment -reset_timestamps 1 -segment_time 60 -segment_format mp4 -segment_atclocktime 1 -strftime 1 \"" + video_dir + "/HD/" + "%Y_%m_%d_%H_%M_%S_000_" + cams_id + ".mp4\" 2>&1 > /dev/null & "
      print(cmd)
      os.system(cmd)
      #time.sleep(2)
   else: 
      print ("ffmpeg already running for cam:", cam_num)

   running = check_running(cam_num, "SD")
   if running == 0:
      #  /usr/bin/ffmpeg -rtsp_transport tcp -r 25 -i 'rtsp://192.168.76.71/user=admin&password=&channel=1&stream=0.sdp' 
      #  -c:v copy -flags +global_header -c:a aac -b:a 128k -map 0 -strict -2 -f segment -reset_timestamps 1 -segment_time 60 
      #  -segment_format mp4 -segment_atclocktime 1 -strftime 1 "/mnt/ams2/HD/%Y_%m_%d_%H_%M_%S_000_010049.mp4" 

      # old command changed on 7/22/24 to support IMX307 
      #cmd = "/usr/bin/ffmpeg -rtsp_transport tcp -r 25 -i 'rtsp://" + cam_ip + sd_url + "' -c copy -map 0 -f segment -reset_timestamps 1 -segment_time 60 -segment_format mp4 -segment_atclocktime 1 -strftime 1 \"" + video_dir + "/SD/" + "%Y_%m_%d_%H_%M_%S_000_" + cams_id + ".mp4\" 2>&1 > /dev/null & "
      cmd = "/usr/bin/ffmpeg -rtsp_transport tcp -r 25 -i 'rtsp://" + cam_ip + sd_url + "' -c copy -map 0 -flags +global_header -c:a aac -b:a 128k -strict -2 -f segment -reset_timestamps 1 -segment_time 60 -segment_format mp4 -segment_atclocktime 1 -strftime 1 \"" + video_dir + "/SD/" + "%Y_%m_%d_%H_%M_%S_000_" + cams_id + ".mp4\" 2>&1 > /dev/null & "
      print(cmd)
      os.system(cmd)
      #time.sleep(2)
   else: 
      print ("ffmpeg already running for cam:", cam_num)


def stop_capture(cam_num):
   #print ("Stopping capture for ", cam_num)
   if cam_num != "all":
      for cam in json_conf['cameras']:
         camn = cam.replace("cam","")
         if str(cam_num) == str(camn):
            cam_ip = json_conf['cameras'][cam]['ip']
            cmd = "kill -9 `ps -aux | grep ffmpeg | grep " + cam_ip + " |grep -v grep| awk '{print $2}'`"
   else:
      cmd = "kill -9 `ps -aux | grep ffmpeg |grep -v grep| awk '{print $2}'`"
   print(cmd)
   try:
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   except:
      output = "ffmpeg process for this cam is not running. " +  str(cam_num)
 
   print (output)

def purge(cam_num):
   cur_time = int(time.time())
   #cmd = "rm " + cam_num + "/*"
   #print (cmd)
   #os.system(cmd)

   for filename in (glob.glob(video_dir + '/' + cam_num + '/*.mp4')):
      st = os.stat(filename)
      mtime = st.st_mtime
      tdiff = cur_time - mtime
      tdiff = tdiff / 60 / 60 / 24
      if tdiff >= .8:
         cmd = "rm " + filename
         print(cmd)
         os.system(cmd)
         #file_list.append(filename)




try:
   cmd = sys.argv[1]
   cam_num = sys.argv[2]
except:
   do_all = 1


if (cmd == "stop"):
   if cam_num != "all":
      stop_capture(cam_num)
   else:
      for i in range(0,len(json_conf['cameras'].keys())):
         num = str(i + 1)
         stop_capture(num)


if (cmd == "start"):
   start_capture(cam_num)
if (cmd == "start_all"):
   for i in range(0,len(json_conf['cameras'].keys())):
      num = str(i + 1)
      start_capture(num)

if (cmd == "purge"):
   purge(cam_num)

if (cmd == "check_running"):
   running = check_running(cam_num, "HD")
   print (running)
   running = check_running(cam_num, "SD")
   print (running)

if (cmd == "purge_all"):
   purge("1")
   purge("2")
   purge("3")
   purge("4")
   purge("5")
   purge("6")
   if "cam7" in json_conf['cameras']:
      purge("7")



#ffmpeg -i rtsp://192.168.76.71/av0_1 -c copy -map 0 -f segment -segment_time 60 -segment_format mp4 "1/capture-1-%03d.mp4" &
