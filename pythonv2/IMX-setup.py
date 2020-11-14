#!/usr/bin/python3

import sys
from dvrip import DVRIPCam
from time import sleep
import json
import time
from datetime import datetime
import os
import ephem

from lib.FileIO import load_json_file, save_json_file, cfe


import socket, struct


def hex2ip(hex_ip):
    addr_long = int(hex_ip,16)
    hex(addr_long)
    hex_ip = socket.inet_ntoa(struct.pack(">L", addr_long))
    return '.'.join(hex_ip.split('.')[::-1])


def ip2hex(ip):
    ip = '.'.join(ip.split('.')[::-1])
    p = ''.join([hex(int(x)+256)[3:] for x in ip.split('.')])
    return "0x"+p.upper()




#FILL IN YOUR DETAILS HERE:
CameraUserName = "admin"
CameraPassword = ""
CameraIP = '192.168.76.71'
BitrateRequired = 7000
#END OF USER DETAILS
print(hex2ip('0x014CA8C0'))
print(ip2hex('192.168.76.1'))
print("0x014CA8C0")


def get_network_settings(cam):
   net_common = cam.get_info("NetWork.NetCommon")
   net_dns = cam.get_info("NetWork.NetDNS")
   net_dhcp = cam.get_info("NetWork.NetDHCP")

   new_net_dhcp = {'Address': '0x08080808', 'SpareAddress': '0x04040808'}
   new_dhcp = [{'Enable': False, 'Interface': 'eth0'}, {'Enable': False, 'Interface': 'eth1'}, {'Enable': False, 'Interface': 'eth2'}, {'Enable': False, 'Interface': 'eth3'}, {'Enable': False, 'Interface': 'bond0'}]

   net_common['GateWay'] = "0x014CA8C0"
   net_common['HostIP'] = ""

   print("NetWork.NetCommon:",net_common)
   print("Network.NetDNS:", net_dns)
   print("Network.NetDHCP:", net_dhcp)
   print("Network.NetIPAdaptive:", net_ip_adaptive)
   #print(enc.decode())

def login(CameraIP, CameraUserName, CameraPassword):
   cam = DVRIPCam(CameraIP,CameraUserName,CameraPassword)
   if cam.login():
      print ("Success! Connected to " + CameraIP)
   else:
      print ("Failure. Could not connect to camera!")
   return(cam)


cam = login(CameraIP, CameraUserName, CameraPassword)
get_network_settings(cam)
cam.close()
