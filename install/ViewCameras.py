import os

i = input("Enter the cam number you want to view [1,2,3,4,5,6,7]")
go = True
options = [1,2,3,4,5,6,7]

e = input("Enter the encoding type of the camera 1) H264 2) H265 (if one doesn't work try the other)")
if e == "1":
    enc_type = "h264"
else:
    enc_type = "h265"



while go is True: 
   if int(i) not in options:
      go = False
      continue

   ip = "192.168.76.7" + str(i)
   if enc_type == "h264":
      cmd = """/usr/bin/gst-launch-1.0 rtspsrc location="rtsp://{:s}/user=admin&password=&channel=0&stream=0.sdp" latency=100 !  queue ! rtph264depay  ! avdec_h264 ! videoconvert ! video/x-raw !  autovideosink """.format(ip)
   else:
      cmd = """/usr/bin/gst-launch-1.0 rtspsrc location="rtsp://{:s}/user=admin&password=&channel=0&stream=0.sdp" latency=100 ! queue ! rtph265depay ! avdec_h265 ! videoconvert ! video/x-raw ! autovideosink""".format(ip)
   print(cmd)
   os.system(cmd)
   i = input("Enter the cam number you want to view [1,2,3,4,5,6,7]")
   try:
      if int(i) not in options:
         print("I NOT IN OPTIONS!")
         go = False
   except:
      print("FAIL!")
      go = False


