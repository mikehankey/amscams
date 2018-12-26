#!/usr/bin/python3


import subprocess
import cgi
import cgitb
import os

#print("Content-type: text/html\n\n")
form = cgi.FieldStorage()
file = form.getvalue('video_file')
#print ("reprocess...", file)

cmd = "cd /home/ams/amscams/python; ./redo.py " + file + " >/tmp/rep.txt 2>&1 " 
#print (cmd)
os.system(cmd)
print("Location: archive-side.py?cmd=examine&video_file=" + file + "\n\n")
