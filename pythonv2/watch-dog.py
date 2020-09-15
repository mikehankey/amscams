#!/usr/bin/python3 

import subprocess
import datetime
import os
import time
#import sendgrid
#from sendgrid.helpers.mail import *
#from amscommon import read_config
from lib.FileIO import load_json_file
import psutil

def check_running(cam_num, type, json_conf):
   cam_key = 'cam' + str(cam_num)
   cam_ip = json_conf['cameras'][cam_key]['ip']

   if type == "HD":
      cmd = "ps -aux |grep \"ffmpeg\" | grep \"HD\" | grep " + cam_ip + " | grep -v grep | wc -l"
   else:
      cmd = "ps -aux |grep \"ffmpeg\" | grep \"SD\" | grep " + cam_ip + " | grep -v grep | wc -l"
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   output = int(output.replace("\n", ""))
   print("RUNNING:", output)
   return(int(output))


def clean_zombies():
   kill_zombies("sro-settings.py", 10)
   kill_zombies("examine-still.py", 60)
   kill_zombies("stack-runner.py", 60)
   kill_zombies("PV.py", 60)
   kill_zombies("fast_frames5.py", 60)
   kill_zombies("auto-brightness.py", 60)

def kill_zombies(process_name, tlimit):
   for p in filter_by_name(process_name):
      diff = time.time() - p.create_time()
      min = int(diff/60)
      print ("found", p.cmdline(), p.pid, min, " minutes")
      if min > tlimit:
         print("Killing:", p.pid, p.name())
         os.system("kill -9 " + str(p.pid))
      

def filter_by_name(process_name):
    for process in psutil.process_iter():
        try:
            #print(process.name)
            if process_name in str(process.cmdline()) :
                yield process
        except psutil.NoSuchProcess:
            pass


def sendmail(tom, frm, subject, msg):
   sg = sendgrid.SendGridAPIClient(apikey=os.environ.get('SENDGRID_API_KEY'))
   from_email = Email(tom)
   to_email = Email(frm)
   content = Content("text/html", msg)
   mail = Mail(from_email, subject, to_email, content)
   response = sg.client.mail.send.post(request_body=mail.get())
   print(response.status_code)
   print(response.body)
   print(response.headers)

def check_disk_space():
   derrs = []
   cmd = "df -H | grep -vE '^Filesystem|tmpfs|cdrom' | awk '{ print $5 \" \" $1 }'"
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   lines = output.split("\n")
   for line in lines:
      line = line.replace("%", "")
      if len(line) > 0:
         perc, vol = line.split(" ")
         if int(perc) >= 85:
            derrs.append("Disk volume " + str(vol) + " is " + str(perc) + "% full!")
   return(derrs)
           

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

def check_stream(cam_num, stream_type):
   bad = 0
   config = load_json_file("../conf/as6.json")
   print("CHECKING STREAM ", stream_type, cam_num)
   if stream_type == 'SD': 
      cmd = "find /mnt/ams2/SD/*.mp4 -mmin -5 |grep mp4 | grep -v proc | grep " + str(cam_num) + " |wc -l"
      print(cmd)
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
      output.replace("\n", "")
      if int(output) > 0:
         print ("SD cam ", str(cam_num), " is good", output)
         return(1)
      else:
         print ("SD cam ", str(cam_num), " is bad. Restart.", output)
         return(0)
   if stream_type == 'HD':
      cmd = "find /mnt/ams2/HD -mmin -5 |grep " + str(cam_num) + " |wc -l"
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
      output.replace("\n", "")
      if int(output) > 0:
         print ("HD cam ", str(cam_num), " is good", output)
         return(1) 
      else:
         print ("HD cam ", str(cam_num), " is bad. Restart.", output)
         return(0) 



   return(bad)
errors = []
config = load_json_file("../conf/as6.json")
json_conf = config
obs_name = config['site']['obs_name']
#print (obs_name)

clean_zombies()
cams_with_err = {}
cams_with_np = {}
# Check disk space 
derrs = []
#derrs = check_disk_space()
#print (derrs)

# Check Pings
bad = 0
for i in range (1,7):
   res = ping_cam(i)
   print ("Cam " + str(i) + " " + str(res))
   if res == 0: 
      errors.append("Cam " + str(i) + "did not respond to ping")
      ping_errors = 1
      cams_with_err[str(i)] = "no ping"
      cams_with_np[str(i)] = "no ping"

# Check SD Streams
stream_errors = 0
for i in range (1,7):
   key = "cam" + str(i)
   cams_id = config['cameras'][key]['cams_id']
   res = check_stream(str(cams_id), "SD")
   if res == 0:
      errors.append("Cam " + str(cams_id) + "SD Stream not present. ")
      stream_errors = 1
      cams_with_err[str(i)] = "no SD stream"

# Check HD Streams
for i in range (1,7):
   res = check_stream(str(cams_id), "HD")
   if res == 0:
      errors.append("Cam " + str(cams_id) + "HD Stream not present. ")
      cams_with_err[str(i)] = "no HD stream"
      stream_errors = 1

# check ffmpeg process
for i in range (1,7):
   hd_run = check_running(str(i), "HD", json_conf)
   sd_run = check_running(str(i), "SD", json_conf)
   if int(hd_run) == 0 or int(sd_run) == 0:
      print("NO FFMPEG RUNNING FOR CAM:", str(i))
      cams_with_err[str(i)] = "no FFMPEG Process Running " + str(i)
      stream_errors = 1

print("CAMS WITH ER:", cams_with_err)

msg = "Error messages for " + obs_name + "<BR>\n"
for error in derrs: 
   msg = msg + error + "<BR>\n"
   print (error)

for error in errors: 
   msg = msg + error + "<BR>\n"
   print (error)

if stream_errors == 1:
   for bad_cam in cams_with_err:
      print("BAD:", bad_cam, cams_with_err[bad_cam])
      if bad_cam not in cams_with_np:
         os.system("../python/ffmpeg_record.py stop " + bad_cam)
         time.sleep(3)
         os.system("../python/ffmpeg_record.py start_all")
      else: 
         print("This cam is down, no point in restarting.")

if len(derrs) > 0 or len(errors) > 0:
   #sendmail('mike.hankey@gmail.com', 'mike.hankey@gmail.com', 'AS6 Alert', msg)
   fp = open("/mnt/ams2/tmp/wd.txt", "w")
   fp.write(msg)
   fp.close()
