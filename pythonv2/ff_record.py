#!/usr/bin/python3
import glob
import sys
import subprocess
import os
import time

import json

json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)



video_dir = "/mnt/ams2"

def check_running(cam_num, type):

   cam_key = 'cam' + str(cam_num)
   cam_ip = json_conf['cameras'][cam_key]['ip']

   cmd = "ps -aux |grep \"ffmpeg\" | grep " + cam_ip + " | grep -v grep | wc -l"
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   output = int(output.replace("\n", ""))
   return(int(output))


def start_capture(cam_num):
   cam_key = 'cam' + str(cam_num)
   cam_ip = json_conf['cameras'][cam_key]['ip']
   sd_url = json_conf['cameras'][cam_key]['sd_url']
   hd_url = json_conf['cameras'][cam_key]['hd_url']
   cams_id = json_conf['cameras'][cam_key]['cams_id']
   if "status" in json_conf['cameras'][cam_key]:
      status = json_conf['cameras'][cam_key]
   else:
      status = "ACTIVE"

   running = check_running(cam_num, "HD")
   if running == 0 and status == "ACTIVE":
      #cmd = "/usr/bin/ffmpeg -i 'rtsp://" + cam_ip + hd_url + "' -rtsp_transport tcp -c copy -map 0 -f segment -strftime 1 -segment_time 60 -segment_format mp4 \"" + video_dir + "/HD/" + "%Y_%m_%d_%H_%M_%S_000_" + cams_id + ".mp4\" 2>&1 > /dev/null & "

      cmd = "/usr/bin/ffmpeg -rtsp_transport tcp -i 'rtsp://" + cam_ip + hd_url + "' -c copy -map 0 -f segment -strftime 1 -segment_time 60 -segment_format mp4 '/mnt/ams2/HD/%Y_%m_%d_%H_%M_%S_000_010001.mp4' -vf scale=480x270 -f segment -strftime 1 -segment_time 60 -segment_format mp4 '/mnt/ams2/SD/%Y_%m_%d_%H_%M_%S_000_010001.mp4' 2>&1 > /dev/null & "


      print(cmd)
   
      os.system(cmd)
      time.sleep(2)
   else: 
      print ("ffmpeg already running for cam:", cam_num)



def stop_capture(cam_num):
   #print ("Stopping capture for ", cam_num)
   #cmd = "kill -9 `ps -aux | grep ffmpeg |grep -v grep| awk '{print $2}'`"
   cmd = "ps -aux | grep ffmpeg |grep -v grep| awk '{print $2}'"
   print(cmd)
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   pids = output.split("\n")
   for pid in pids:
      print (pid)
      if pid != "":
         cmd = "kill -9 "+ pid
         print(cmd)
         os.system(cmd)
         time.sleep(1)

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
   stop_capture("1")
if (cmd == "start"):
   start_capture(cam_num)
if (cmd == "start_all"):
   start_capture("1")
   start_capture("2")
   start_capture("3")
   start_capture("4")
   start_capture("5")
   start_capture("6")

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



#ffmpeg -i rtsp://192.168.76.71/av0_1 -c copy -map 0 -f segment -segment_time 60 -segment_format mp4 "1/capture-1-%03d.mp4" &
