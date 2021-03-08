#!/usr/bin/python3

from lib.FileIO import load_json_file, cfe

import socket
import requests
import subprocess
import sys
import os 
import time
import json
json_conf = load_json_file("../conf/as6.json")


def auto_update():
   update_needed = 0
   if cfe("/home/ams/amscams/install/last_run.txt") == 0:
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
   if update_needed == 1:
      cmd = "cd /home/ams/amscams/install; sudo ./pip-updates.sh"
      print(cmd)
      os.system(cmd)
      cmd = "cp /home/ams/amscams/install/pip-updates.sh /home/ams/amscams/install/last_run.txt "
      os.system(cmd)
 
      # Stop flask (so new code will work)
      cmd = "cd /home/ams/amscams/pipeline; /home/ams/amscams/pipeline/run-uwsgi-ssl > /tmp/sgi.txt 2>&1"
      os.system(cmd)
      

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




amsid = json_conf['site']['ams_id'].upper()
auto_update()
#exit()
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

if vpn_connect == 1 and running == 0:   
   # connect request exists make connection
   cmd ="/usr/sbin/openvpn --config /etc/openvpn/" + amsid + ".ovpn &"
   print(cmd)
   os.system(cmd)
if vpn_connect == 0 and running == 1:   
   print ("Terminate running VPN connection, it is no longer requested.")
   cmd ="/usr/bin/killall openvpn"
   print(cmd)
   os.system(cmd)
   #cmd ="ip link delete tun0"
   #os.system(cmd)
      


