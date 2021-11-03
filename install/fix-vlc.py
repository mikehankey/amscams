#!/usr/bin/python3 
import os

gst_desktop_temp = """

[Desktop Entry]
Version=1.0
Type=Application
Name=GST YYY
Comment=
Exec=/usr/bin/gst-launch-1.0 rtspsrc location="rtsp://192.168.76.XXX/user=admin&password=&channel=0&stream=0.sdp" latency=100 ! queue ! rtph264depay  ! avdec_h264 ! videoconvert ! video/x-raw ! autovideosink
Icon=
Terminal=false
StartupNotify=false



"""

vlc_desktop_temp = """
[Desktop Entry]
Version=1.0
Type=Application
Name=VLC YYY
Comment=
Exec=/usr/bin/vlc rtsp://192.168.76.XXX:554/user=admin_password=_channel=1_stream=1.sdp
Icon=vlc
Terminal=false
StartupNotify=false

"""

if True:
   os.system("sudo apt remove vlc")
   os.system("sudo apt install gstreamer1.0-libav")
   os.system("sudo apt purge vlc")
   os.system("sudo snap remove vlc")
   os.system("sudo apt autoremove")
   os.system("sudo snap install vlc")

if os.path.exists("/home/ams/amscams/install/desktop") is False:
   os.makedirs("/home/ams/amscams/install/desktop")

for i in range(1, 8):
   print(i)
   ip_digit = "7" + str(i)
   temp = vlc_desktop_temp.replace("XXX", str(ip_digit))
   temp = temp.replace("YYY", "VLC_CAM" + str(i))
   desk_file = "/home/ams/amscams/install/desktop/VLC_CAM" + str(i) + ".desktop"
   fp = open(desk_file, "w")
   fp.write(temp)
   fp.close()
   os.system("chmod +x " + desk_file)
   os.system("sudo desktop-file-install " + desk_file)
   os.system("cp " + desk_file + " " + "/home/ams/Desktop")


   temp = gst_desktop_temp.replace("XXX", str(ip_digit))
   temp = temp.replace("YYY", "GS_CAM" + str(i))
   desk_file = "/home/ams/amscams/install/desktop/GST_CAM" + str(i) + ".desktop"
   fp = open(desk_file, "w")
   fp.write(temp)
   fp.close()
   os.system("chmod +x " + desk_file)
   os.system("sudo desktop-file-install " + desk_file)
   os.system("cp " + desk_file + " " + "/home/ams/Desktop")

   os.system("sudo chown -R ams /home/ams")
   if os.path.exists("/usr/bin/vlc") is False:
      os.system("ln -s /snap/bin/vlc /usr/bin/vlc ")




