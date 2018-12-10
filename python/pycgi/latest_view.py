#!/usr/bin/python3
import subprocess 
import time
video_dir = "/mnt/ams2/"
rand = time.time()
print ("Content-type: text/html\n\n")

print ("<link href='https://fonts.googleapis.com/css?family=Roboto:100,400,300,500,700' rel='stylesheet' type='text/css'>")
print ("<link href='scale.css' rel='stylesheet' type='text/css'>")
print ("<div align=\"center\" class=\"fond\" style=\"width: 100%\">")
print("<h2>Latest View</h2> Updated Once Every 5 Minutes")
print ("<div>")
print ("<div class=\"style_prevu_kit\" style=\"background-color:#cccccc;\"><img src=../out/latest-1.jpg?" + str(rand) + " width=640 height=360></div>")
print ("<div class=\"style_prevu_kit\" style=\"background-color:#cfcfcf;\"><img src=../out/latest-2.jpg?" + str(rand) + " width=640 height=360></div>")
print ("</div>")
print ("<div>")
print ("<div class=\"style_prevu_kit\" style=\"background-color:#cccccc;\"><img src=../out/latest-3.jpg?" + str(rand) + " width=640 height=360></div>")
print ("<div class=\"style_prevu_kit\" style=\"background-color:#cfcfcf;\"><img src=../out/latest-4.jpg?" + str(rand) + " width=640 height=360></div>")
print ("</div>")
print ("<div>")
print ("<div class=\"style_prevu_kit\" style=\"background-color:#cccccc;\"><img src=../out/latest-5.jpg?" + str(rand) + " width=640 height=360></div>")
print ("<div class=\"style_prevu_kit\" style=\"background-color:#cfcfcf;\"><img src=../out/latest-6.jpg?" + str(rand) + " width=640 height=360></div>")
print ("</div>")
print ("</div>")
