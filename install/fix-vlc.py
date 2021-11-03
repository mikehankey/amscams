#!/usr/bin/python3 
import os

gst_desktop_temp = """
/usr/bin/gst-launch-1.0 rtspsrc location="rtsp://192.168.76.XXX/user=admin&password=&channel=0&stream=1.sdp" latency=100 ! queue ! rtph264depay  ! avdec_h264 ! videoconvert ! video/x-raw ! autovideosink
"""

vlc_desktop_temp = """
[Desktop Entry]
Version=1.0
Type=Application
Name=Cam1
Comment=
Exec=/usr/bin/vlc rtsp://192.168.76.XXX:554//user=admin_password=_channel=1_stream=0.sdp?real_stream
Icon=vlc
Path=
Terminal=false
StartupNotify=false

"""

if False:
   os.system("sudo apt remove vlc")
   os.system("sudo apt install gstreamer1.0-libav")
   os.system("sudo apt purge vlc")
   os.system("sudo snap remove vlc")
   os.system("sudo apt autoremove")
   os.system("sudo snap install vlc")

for i in range(1, 8):
   print(i)
   ip_digit = "7" + str(i)
   temp = vlc_desktop_temp.replace("XXX", str(ip_digit))
   desk_file = "/home/ams/Desktop/CAM" + str(i) + ".desktop"
   fp = open(desk_file, "w")
   fp.write(temp)
   fp.close()
   os.system("chmod +x " + desk_file)


   temp = gst_desktop_temp.replace("XXX", str(ip_digit))
   desk_file = "/home/ams/Desktop/GST_CAM" + str(i) + ".desktop"
   fp = open(desk_file, "w")
   fp.write(temp)
   fp.close()
   os.system("chmod +x " + desk_file)

   os.system("sudo chown -R ams /home/ams")
   os.system("ln -s /snap/bin/vlc /usr/bin/vlc ")




