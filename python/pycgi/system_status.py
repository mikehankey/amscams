#!/usr/bin/python3
import subprocess 
video_dir = "/mnt/ams2/"
print ("Content-type: text/html\n\n")

print ("<h2>AllSky6 System Status</h2>")
print ("<h2>Video Stream Recording </h2>")
cmd = "ps -aux |grep \"ffmpeg\" | grep \"HD\" | grep -v grep | wc -l"
output = subprocess.check_output(cmd, shell=True).decode("utf-8")
output = int(output.replace("\n", ""))
print(str(output) + " HD Streams recording<BR>")

cmd = "ps -aux |grep \"ffmpeg\" | grep \"SD\" | grep -v grep | wc -l"
output = subprocess.check_output(cmd, shell=True).decode("utf-8")
output = int(output.replace("\n", ""))
print(str(output) + " SD Streams recording<BR>")

cmd = "ls -l " + video_dir + "/SD/*.mp4 |wc -l"
output = subprocess.check_output(cmd, shell=True).decode("utf-8")
output = int(output.replace("\n", ""))
print(str(output) + " Video files in processing queue. <BR>")

print ("<h2>Disk Space Utilization</h2>")
print ("<PRE>")

cmd = "df -h" 
output = subprocess.check_output(cmd, shell=True).decode("utf-8")
#output = int(output.replace("\n", ""))
print(str(output) )

print ("</PRE>")


