#!/usr/bin/python3

from lib.FileIO import load_json_file, save_json_file, cfe

import socket
import requests
import subprocess
import sys
import os 
import time
import json
json_conf = load_json_file("../conf/as6.json")

def get_file_info(file):
   cur_time = int(time.time())
   if cfe(file) == 1:
      st = os.stat(file)

      size = st.st_size
      mtime = st.st_mtime
      tdiff = cur_time - mtime
      tdiff = tdiff / 60
      return(size, tdiff)
   else:
      return(0,0)

def auto_update():
   print("AUTO UPDATE")
   sys_log_file = "/home/ams/amscams/install/system_log.json"
   update_needed = 0
   restart_uwsgi = 0
   if os.path.exists(sys_log_file) is False:
      update_needed = 1
      sys_log = {}
   else:
      sys_log = load_json_file(sys_log_file)

   if os.path.exists("/home/ams/amscams/install/last_run.txt") is False:
      update_needed = 1
   else:
      cmd = "diff /home/ams/amscams/install/last_run.txt /home/ams/amscams/install/pip-updates.sh |wc -l "
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
      print("UPDATE DIFF:", output)
      try:
         if int(output) > 0:
            update_needed = 1
      except:
         print("Problem with update diff.")

   # PIP
   if "pip" not in sys_log:
      sys_log['pip'] = {}
      update_needed = 1
   if "pip_version" not in sys_log['pip']:
      cmd = "pip3 --version"
      print("PIP VERSION", cmd)
      try:
         sys_log['pip']['pip_version'] = subprocess.check_output(cmd, shell=True).decode("utf-8")
      except:
         sys_log['pip']['pip_version'] = "CHECK FAILED!"
         print("get pip version failed")
   if "uwsgi" not in sys_log:
      sys_log['uwsgi'] = {}
      restart_uwsgi = 1
   else:
      if "last_restart" not in sys_log['uwsgi']: 
         sys_log['uwsgi']['last_restart'] = time.time()
         restart_uwsgi = 1

   if "bin_pip_check" not in sys_log['pip']:
      # make sure pip exists in the /usr/bin/bin dir. 
      # If it doesn't check if it is in /usr/local/bin 
      # if found then sym link it
      if os.path.exists("/usr/bin/pip") is False and os.path.exists("/usr/local/bin/pip") is True:
         cmd = "ln -s /usr/local/bin/pip* /usr/bin/"
         print(cmd)
         os.system(cmd)
         print("DID BIN PIP CHECK")
      sys_log['pip']['bin_pip_check'] = True


   if update_needed == 1:
      cmd = "cd /home/ams/amscams/install; sudo ./pip-updates.sh"
      print(cmd)
      os.system(cmd)
      cmd = "cp /home/ams/amscams/install/pip-updates.sh /home/ams/amscams/install/last_run.txt "
      os.system(cmd)


      cmd = "cd /home/ams/amscams/install; sudo ./update-cron.sh"
      print(cmd)
 
   if restart_uwsgi == 1:
      # Stop flask (so new code will work)
      cmd = "cd /home/ams/amscams/pipeline; ./stop-uwsgi.sh > /tmp/ssgi.txt 2>&1"
      print(cmd)
      os.system(cmd)
   save_json_file(sys_log_file, sys_log)      

def check_running():
   cmd = "/sbin/ifconfig -a | grep 10.8.0 | grep -v grep | wc -l"
   print(cmd)
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   output = int(output.replace("\n", ""))
   print(output)
   return(int(output))

# check if flask admin is enabled and make sure it is runnniing if it is


if "flask_admin" in json_conf:
   cmd = "ps -aux |grep \"wsgi\" | grep -v grep | wc -l"
   print(cmd)
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   flask_running = int(output.replace("\n", ""))
   print("FLASK:", flask_running)
   if flask_running == 0:
      print("FLASK RUNNING:", flask_running)
      if cfe("/home/ams/amscams/pipeline/key.pem") == 1: 
         cmd = "cd /home/ams/amscams/pipeline; /home/ams/amscams/pipeline/run-uwsgi-ssl > /tmp/sgi.txt 2>&1 & "
      else:
         cmd = "cd /home/ams/amscams/pipeline; /home/ams/amscams/pipeline/run-uwsgi.sh > /tmp/sgi.txt 2>&1 & "
      print(cmd)
      os.system(cmd)
else:
   print("Flask admin not enabled.")


if os.path.exists("vpn.run") is True:
   print("VPN SCRIPT RUNNING ALREADY!")
   ss, tt = get_file_info("vpn.run")
   print("Script running for", tt, "seconds")
   if tt < 1200:
      # exit in case there is some other update going...
      exit()
else:
   os.system("touch vpn.run")


amsid = json_conf['site']['ams_id'].upper()
auto_update()

# remove update lock script before continue
if os.path.exists("vpn.run") is True:
   os.system("rm vpn.run")


# check if a VPN connect request exists
# and then connect if it does

vpn_url = "http://archive.allsky.tv/" + amsid + "/cmd/vpn"
r = requests.get(vpn_url)

if "404" in r.text or "Error" in r.text:
   vpn_connect = 0
else:
   vpn_connect = 1

print("R:", r.text)
running = check_running()
print("VPN CONNECT:", vpn_connect)
print("RUNNING:", running)
print(type(vpn_connect), type(running))
if vpn_connect == 1:
   print("VPN CONNECT:", vpn_connect)
if running == 1:
   print("RUNNING:", running)

if vpn_connect >= 1 and running == 0:   
   # connect request exists make connection
   cmd ="/usr/sbin/openvpn --config /etc/openvpn/" + amsid + ".ovpn &"
   print(cmd)
   os.system(cmd)
if int(vpn_connect) == 0 and int(running) >= 1:   
   print ("Terminate running VPN connection, it is no longer requested.")
   cmd ="/usr/bin/killall openvpn"
   print(cmd)
   os.system(cmd)
   #cmd ="ip link delete tun0"
   #os.system(cmd)


