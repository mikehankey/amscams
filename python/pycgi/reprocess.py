#!/usr/bin/python3 

import subprocess
import cgi
import cgitb
import os

#print("Content-type: text/html\n\n")
form = cgi.FieldStorage()
file = form.getvalue('video_file')
#print ("reprocess...", file)
print("Content-type: text/html\n\n")

#cmd = "cd /home/ams/amscams/python; ./redo.py " + file + " >/tmp/rep.txt 2>&1 " 
#cmd = "cd /home/ams/amscams/python; ./redo.py " + file + " >/dev/null 2>&1 " 
cmd = "cd /home/ams/amscams/python; ./detect-filters.py sf " + file + " >/dev/null 2>&1 " 
print(cmd)
#os.system(cmd)
#magic = str(subprocess.check_output(cmd, shell=True))
#magic = magic.replace("b", "")
#magic = magic.replace("'", "")


#print("Location: archive-side.py?cmd=examine&video_file=" + file + "\n\n")
