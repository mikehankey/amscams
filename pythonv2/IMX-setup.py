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

#FILL IN YOUR DETAILS HERE:
CameraUserName = "admin"
CameraPassword = ""
CameraIP = '192.168.76.71'
BitrateRequired = 7000
#END OF USER DETAILS


def get_network_settings(cam):
   test_info = cam.get_info("NetWork.NetCommon")
   enc = test_info['GateWay'].encode()
   print(enc.decode())

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
