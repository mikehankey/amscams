#!/usr/bin/python3

from pathlib import Path
import os

def cfe(file,dir = 0):
   if dir == 0:
      file_exists = Path(file)
      if file_exists.is_file() is True:
         return(1)
      else:
         return(0)
   if dir == 1:
      file_exists = Path(file)
      if file_exists.is_dir() is True:
         return(1)
      else:
         return(0)




if cfe("/var/www/html/pycgi/dist", 1) == 0:
   print("Dist dir missing!")
if cfe("/var/www/html/pycgi/src", 1) == 0:
   print("Dist dir missing!")
if cfe("/var/www/html/pycgi/video_player.html", 0) == 0:
   print("Video Player missing!")
try:
   import sympy
except:
   print("Sympy is missing!")

cmd = "echo '<a href=/pycgi/webUI.py>Login</a>' > /var/www/html/index.html"
print(cmd)
os.system(cmd) 

print("Setup data drive.")
print("Update AMS ID and device lat/lon.")
print("Run File Index Script.")
print("Setup camera numbers!")
print("ADD API_HOST to as6.json!")
print("SETUP VPN to as6.json!")

os.system("apt-get install ntp")
