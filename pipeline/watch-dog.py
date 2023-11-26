#!/usr/bin/python3 

# updated watch dog. 

import glob
import subprocess
import datetime
from datetime import datetime as dt
import os
import time

#import sendgrid
#from sendgrid.helpers.mail import *
#from amscommon import read_config
from lib.PipeUtil import load_json_file, save_json_file, cfe
import psutil

def run_df():
   df_data = []
   mounts = {}
   if True:
      cmd = "df -h "
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
      #Filesystem                 Size  Used Avail Use% Mounted on

      for line in output.split("\n"):
         #line = line.replace("  ", " ")
         temp = " ".join(line.split())
         disk_data = temp.split(" ")
         if len(disk_data) > 5:
            file_system = disk_data[0]
            size = disk_data[1]
            used  = disk_data[2]
            avail = disk_data[3]
            used_perc = disk_data[4]
            mount = disk_data[5]
            #print(mount, used_perc)
            if mount == "/" or mount == "/mnt/ams2" or mount == "/mnt/archive.allsky.tv" or mount == "/home":
               df_data.append((file_system, size, used, avail, used_perc, mount))
               used_perc = used_perc.replace(" ", "")
               mounts[mount] = int(used_perc.replace("%", ""))
   else:
      print("Failed du")

   return(df_data, mounts)

def check_disk(json_conf, wd):

   df_data, mounts = run_df()
   if "data_dir" in json_conf:
      data_dir = json_conf['data_dir']
   else:
      data_dir = "/mnt/ams2"

   #hd_files = sorted(glob.glob("/mnt/ams2/HD/*.mp4"))
   #if len(hd_files) > 22000:
   #   del_needed = 1

   wd['df_data'] = df_data
   wd['mounts'] = mounts
   return(wd)

def get_file_info(file):
   cur_time = int(time.time())
   st = os.stat(file)
   size = st.st_size
   mtime = st.st_mtime
   tdiff = cur_time - mtime
   tdiff = tdiff / 60
   return(size, tdiff)


def check_running(cam_num, type, json_conf):
   cam_key = 'cam' + str(cam_num)
   cam_ip = json_conf['cameras'][cam_key]['ip']

   if type == "HD":
      cmd = "ps -aux |grep \"ffmpeg\" | grep \"HD\" | grep " + cam_ip + " | grep -v grep | wc -l"
   else:
      cmd = "ps -aux |grep \"ffmpeg\" | grep \"SD\" | grep " + cam_ip + " | grep -v grep | wc -l"
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   output = int(output.replace("\n", ""))
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
   cmd = "ping -c 1 " + config['cameras'][key]['ip'] + " >/dev/null"

   response = os.system(cmd)
   if response == 0:
      return(1)
   else:
      return(0)

def check_corrupt(cam_num, stream_type):
   files = sorted(glob.glob("/mnt/ams2/SD/" + "*" + cam_num + "*.mp4"), reverse=True)
   corrupt = 0
   for file in sorted(files,reverse=True)[0:10]:
      if cfe(file) == 1:
         size, old = get_file_info(file)  
         if 1 < old <= 15 and size < 100:
            corrupt += 1
   return(corrupt)

def check_stream(cam_num, stream_type):
   bad = 0
   config = load_json_file("../conf/as6.json")
   if stream_type == 'SD': 
      cmd = "find /mnt/ams2/SD/*.mp4 -mmin -5 |grep mp4 | grep -v proc | grep " + str(cam_num) + " |wc -l"
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
      output = int(output.replace("\n", ""))
      if int(output) > 0:
         return(output)
      else:
         return(0)
   if stream_type == 'HD':
      cmd = "find /mnt/ams2/HD -mmin -5 |grep " + str(cam_num) + " |wc -l"
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
      output = int(output.replace("\n", ""))
      if int(output) > 0:
         return(output) 
      else:
         return(0) 



   return(bad)

def uptime():  
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
        return uptime_seconds

def check_license():
    # check this is a valid install
    sid = json_conf['site']['ams_id'].replace("AMS","")
    if 150 <= int(sid) <= 159 or 163 <= int(sid) <= 167:
        os.system("./disable.py 1")


def load_wd_status(json_conf):
   wd_file = "../conf/watchdog-status.json"

   if cfe(wd_file) == 1:
      wd = load_json_file(wd_file)
   else:
      wd = 0

   if wd == 0:
      wd = {}
      wd['last_system_reboot'] = uptime() 
      wd['system_reboots'] = []
      wd['cams'] = {}
      for cam in json_conf['cameras']:
         wd['cams'][cam] = {}
         cams_id = json_conf['cameras'][cam]['cams_id']
         ip = json_conf['cameras'][cam]['ip']

         wd['cams'][cam]['cams_id'] = cams_id
         wd['cams'][cam]['ip'] = ip
         wd['cams'][cam]['last_ping'] = 9999
         wd['cams'][cam]['last_reboot'] = 0
         wd['cams'][cam]['last_restart'] = 0 
         wd['cams'][cam]['last5_hd_files'] = 0 
         wd['cams'][cam]['last5_sd_files'] = 0 
         wd['cams'][cam]['no_ping_for'] = 0
         wd['cams'][cam]['no_sd_stream_for'] = 0
         wd['cams'][cam]['no_hd_stream_for'] = 0
         wd['cams'][cam]['last_sd_stream_time'] = 0
         wd['cams'][cam]['last_hd_stream_time'] = 0
         wd['cams'][cam]['corrupt_files'] = 0

         wd['cams'][cam]['reboots'] = []
         wd['cams'][cam]['restarts'] = []
      save_json_file(wd_file, wd)
   else:
      wd = load_json_file(wd_file)
      if wd == 0:
         wd = {}
   return(wd)

def check_pings(json_conf, wd):
   num_cams = len(json_conf['cameras'].keys()) + 1
   # Check Pings
   bad = 0
   for i in range (1,num_cams):
      res = ping_cam(i)
      cam = "cam" + str(i)
      if res == 0: 
         errors.append("Cam " + str(i) + "did not respond to ping")
         ping_errors = 1
         cams_with_err[str(i)] = "no ping"
         cams_with_np[str(i)] = "no ping"
         cur_time = int(time.time())
         wd['cams'][cam]['last_ping'] = cur_time 
         wd['cams'][cam]['no_ping_for'] = cur_time - wd['cams'][cam]['no_ping_for']
      else:
         cur_time = int(time.time())
         wd['cams'][cam]['last_ping'] = cur_time
         wd['cams'][cam]['no_ping_for'] = 0
   return(wd)


def check_streams(json_conf, wd):
   # Check SD Streams
   stream_errors = 0
   for i in range (1,len(json_conf['cameras']) + 1):
      key = "cam" + str(i)
      cams_id = json_conf['cameras'][key]['cams_id']
      res = check_stream(str(cams_id), "SD")
      if res == 0:
         errors.append("Cam " + str(cams_id) + "SD Stream not present. ")
         stream_errors = 1
         cams_with_err[str(i)] = "no SD stream"
         cur_time = int(time.time())
         wd['cams'][key]['last5_sd_files'] = res
      else:
         cur_time = int(time.time())
         wd['cams'][key]['last5_sd_files'] = res
         wd['cams'][key]['last_sd_stream_time'] = cur_time
      corrupt_files = check_corrupt(str(cams_id), "SD")
      wd['cams'][key]['corrupt_files'] = corrupt_files


   # Check HD Streams
   for i in range (1,len(json_conf['cameras'])+1):
      key = "cam" + str(i)
      res = check_stream(str(cams_id), "HD")
      if res == 0:
         errors.append("Cam " + str(cams_id) + "HD Stream not present. ")
         cams_with_err[str(i)] = "no HD stream"
         stream_errors = 1

         cur_time = int(time.time())
         wd['cams'][key]['last5_hd_files'] = res
         wd['cams'][key]['no_hd_stream_for'] = cur_time - wd['cams'][cam]['last_hd_stream_time']
      else:
         cur_time = int(time.time())
         wd['cams'][key]['no_hd_stream_for'] = 0
         wd['cams'][key]['last5_hd_files'] = res
         wd['cams'][key]['last_hd_stream_time'] = cur_time

   return(wd)

def check_ffmpeg_procs(json_conf, wd) :
   # check ffmpeg process
   for i in range (1,len(json_conf['cameras'])+1):
      hd_run = check_running(str(i), "HD", json_conf)
      sd_run = check_running(str(i), "SD", json_conf)
   if int(hd_run) == 0 or int(sd_run) == 0:
      cams_with_err[str(i)] = "no FFMPEG Process Running " + str(i)
      stream_errors = 1
   return(wd)

def handle_errors(json_conf, wd):
   msg = "Error messages for " + obs_name + "<BR>\n"
   for error in derrs: 
      msg = msg + error + "<BR>\n"

   for error in errors: 
      msg = msg + error + "<BR>\n"

   if stream_errors == 1:
      cur_time = int(time.time())
      for bad_cam in cams_with_err:
         bad_key = "cam" + str(bad_cam)
         if bad_cam not in cams_with_np:

            # Should we reboot the cam
            # if the cam has had 10 restarts since the last reboot reboot the cam for a maximum of 1x per hour
            # MIKE TEST TEMP
            os.system("../python/ffmpeg_record.py stop " + bad_cam)
            time.sleep(3)
            if len(wd['cams'][bad_key]['restarts']) > 5:
               wd['cams'][bad_key]['restarts'] = []
               wd['cams'][bad_key]['reboots'].append(cur_time)
               os.system("./IMX291.py reboot " + wd['cams'][bad_key]['ip'] + "&")
               log = open("/mnt/ams2/logs/cam_reboots.txt", "a")
               log.write(str(cur_time) + " reboot:" + str(bad_cam) + wd['cams'][bad_key]['ip'])
               time.sleep(30)

            # MIKE TEST TEMP
            os.system("../python/ffmpeg_record.py start " + str(bad_cam))
            wd['cams'][bad_key]['restarts'].append(cur_time)
            wd['cams'][bad_key]['last_restart'] = cur_time
         else: 
            print("This cam is down, no point in restarting.")

   # Should we reboot the server if there are corrupt files of 50% or more and the server has not been rebooted in 12 hours then reboot it
   tc = 0
   for key in wd['cams']:
      tc += wd['cams'][key]['corrupt_files']
   print("Total corrupt files system wide in last 10 minutes.", tc)   

   if len(derrs) > 0 or len(errors) > 0:
      #sendmail('mike.hankey@gmail.com', 'mike.hankey@gmail.com', 'AS6 Alert', msg)
      fp = open("/mnt/ams2/tmp/wd.txt", "w")
      fp.write(msg)
      fp.close()



# MAIN START
errors = []
json_conf = load_json_file("../conf/as6.json")

print("CHECK LICENSE")
check_license()
#exit()

clean_zombies()
cams_with_err = {}
cams_with_np = {}

wd = load_wd_status(json_conf)

wd = check_pings(json_conf, wd)
wd = check_ffmpeg_procs(json_conf, wd) 
wd = check_streams(json_conf, wd)
wd = check_disk(json_conf, wd)
#print(wd['mounts'])
now = dt.now()

day = now.strftime("%Y_%m_%d")
now_dt = now.strftime("%Y_%m_%d %H:%M:%S")
min = now.strftime("%M")
if min == "00":
   os.system("git pull")

#print("Last PC reboot:", wd['last_system_reboot']) 
print('{0:<25} {1:<20} '.format("Report Time:", now_dt))
for key in wd['cams']:
   print('{0:<25} {1:<20} '.format("Cam:", wd['cams'][key]['cams_id']))
   print('{0:<25} {1:<20} '.format("IP:", wd['cams'][key]['ip']))
   print('{0:<25} {1:<20} '.format("Last Ping:", dt.fromtimestamp(wd['cams'][key]['last_ping']).strftime('%Y-%m-%d %H:%M:%S')))
   print('{0:<25} {1:<20} '.format("Last FF Restart:", dt.fromtimestamp(wd['cams'][key]['last_restart']).strftime('%Y-%m-%d %H:%M:%S')))
   print('{0:<25} {1:<20} '.format("Last SD File:", dt.fromtimestamp(wd['cams'][key]['last_sd_stream_time']).strftime('%Y-%m-%d %H:%M:%S')))
   print('{0:<25} {1:<20} '.format("Last HD File:", dt.fromtimestamp(wd['cams'][key]['last_hd_stream_time']).strftime('%Y-%m-%d %H:%M:%S')))
   print('{0:<25} {1:<20} '.format("No SD Stream for:", wd['cams'][key]['no_sd_stream_for']))
   print('{0:<25} {1:<20} '.format("No HD Stream for:", wd['cams'][key]['no_hd_stream_for']))
   print('{0:<25} {1:<20} '.format("Corrupted Files:", wd['cams'][key]['corrupt_files']))
   print("")

   #for test in wd['cams'][key]:
   #   print("     ", test) #, wd['cams'][key][test])

print("")
print("Disk Utilization")
print('{0:<25} {1:<20} '.format("Mount Point", "% Full"))
for disk in wd['df_data']:
   #print(disk)
   dev, total, used, free, perc, mount_point = disk
   print('{0:<25} {1:<20} '.format(mount_point, perc))

#save_json_file(wd_file, wd)
#print("saved:", wd_file)
