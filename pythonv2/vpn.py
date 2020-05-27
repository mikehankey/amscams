#!/usr/bin/python3

from lib.FileIO import load_json_file

import socket
import requests
import subprocess
import sys
import os 
import time
import json
json_conf = load_json_file("../conf/as6.json")

json_conf['site']['API_HOST'] = "35.165.208.121"

API_HOST = "http://" + json_conf['site']['API_HOST']


def check_running():
   cmd = "/sbin/ifconfig -a | grep 172.27.232 | grep -v grep | wc -l"
   print(cmd)
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   output = int(output.replace("\n", ""))
   print(output)
   return(int(output))




try:
   cmd = sys.argv[1]
   if cmd == 'stop':
      cmd ="/etc/init.d/openvpn stop"
      os.system(cmd)
      time.sleep(3)
      cmd ="killall openvpn"
      os.system(cmd)
   else:
      running = check_running()
      if running == 0:
         cmd ="/usr/sbin/openvpn --config /etc/openvpn/as6vpn.ovpn &"
         os.system(cmd)
except:
   # check if a VPN connect request exists
   # and then connect if it does
   hostname = socket.gethostname()
   url = API_HOST + "/vpnc/" + hostname 
   r = requests.get(url)
   
   if "404" in r.text or False:
      running = check_running()
      print ("running = ", running)
      if running > 0: 
         print ("Terminate running VPN connection.")
         cmd ="killall openvpn"
         os.system(cmd)
         cmd ="ip link delete tun0"
         os.system(cmd)
   else:
      print ("VPN Connect Request Present.", r.text)
      running = check_running()
      if running == 0:
         cmd ="/usr/sbin/openvpn --config /etc/openvpn/as6vpn.ovpn &"
         os.system(cmd)
      


