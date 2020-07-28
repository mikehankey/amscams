import sys
from dvrip import DVRIPCam
from time import sleep
import json

#FILL IN YOUR DETAILS HERE:
CameraUserName = "admin"
CameraPassword = ""
CameraIP = '192.168.76.71'
BitrateRequired = 7000
#END OF USER DETAILS


if len(sys.argv) > 1:
    CameraIP = str(sys.argv[1])

cam = DVRIPCam(CameraIP,CameraUserName,CameraPassword)

if cam.login():
    print ("Success! Connected to " + CameraIP)
else:
    print ("Failure. Could not connect to camera!")

def camera_settings():
   sleep(2)
   print ("Current encoding settings:")
   #enc_info = cam.get_info("Simplify.Encode")
   cam_info = cam.get_info("Camera.ParamEx")
   print (cam_info)
   cam_info[0]['BroadTrends']['AutoGain'] = 1
   cam.set_info("Camera.ParamEx", cam_info)
   print ("\r\n")
   cam.close()

def encoding_settings():
   sleep(2)
   enc_info[0]['MainFormat']['Video']['BitRate'] = BitrateRequired
   cam.set_info("Simplify.Encode", enc_info)
   print ("Sent new bitrate settings\r\n")
   sleep(5)
   print ("New encoding settings:")
   print(cam.get_info("Simplify.Encode"))
   print(cam.get_info("Simplify.Encode"))
   sleep(5)
