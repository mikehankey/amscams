#!/usr/bin/python3
import os
import datetime
import subprocess
from lib.PipeUtil import load_json_file, save_json_file
now = datetime.datetime.now().strftime("%Y_%m_%d")
git_save_dir = "/home/ams/git_save/" + now + "/"
git_root = "/home/ams/amscams/"

if os.path.exists(git_save_dir) is False:
   os.makedirs(git_save_dir)

cmd = "cd /home/ams/amscams/ && git pull > /home/ams/gitlog.txt 2>&1"
os.system(cmd)
fp = open("/home/ams/gitlog.txt")
errors = False
for line in fp:
   line = line.replace("\n", "")
   if errors is True and "/" in line:
      print("STASH:", line)
      line = line.replace(" ", "")
      line = line.replace("\t", "")
      cmd = "mv -f " + git_root + line + " " + git_save_dir
      print(cmd)
      os.system(cmd)

   if "error" in line:
      errors = True

# add key if not there already
key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDZi07s+pkgBT48ll0d/QHxMVyevSsVQGs8/yeD7pZe0MPKMAUVuPQ0PGSJXgPwgfIBDWdX4w0AVF4DRcZoubNyY/fmPJOeJPlzDagAH4au0StfOp8HV/1powkxj6dnkR4W2gS82aXUy8s5R7bYNHkW6+9CTcvNHdxLnv3XKnFXFoS06hmqG7EUwUNsOGGVPa/OtoCnEOuJEfIbRdkqnqyFYsXghxaXYvh4FDFVdZW7O9V21F48cp5lZ9yikAWrk+Mgo2jDSnMv6Lvy9ymKWtkvhoV1DtPcaXmuH+GSvMOmNY6a5sI7iQg26+J4Jvv95fZKiEEL715ZvD+znms/BtnQjNoQANaMYZ8QGZO1J1aABn0i9c/sXMWyPeoozsAzUViDQEFCxNzWhY6aO58tVT+gABXplWAim7OcbU/O7V2fmSKdHsyYUk8mMMueOQ2CRbVD2Hz0D9iXuiGykLDx9JTN7XQuZZ8M8TjioAkq13j35b8KfbpD1nk8ENLTF5rimGnFKCfDz+SbdxHXb6oSuBn+QFNZZLB01gdInHwHaEPB53zfIwS6y0elEiDxN6CDli3flNeih9ErzAf04Y6IrW1R4fKb/mR3Fh61Xz9pyT1xwo9TLyXjBmlmFXc7lA696/lsz62tznu8v1nDjxdu/16IC6DSLRvlwjRrGflzJLpqkw== mike.hankey@gmail.com"
key_file = "/home/ams/.ssh/authorized_keys" 
cmd = "grep mike.hankey@gmail /home/ams/.ssh/authorized_keys" 
if os.path.exists(key_file) is True:
   #out = subprocess.check_output(cmd, shell=True).decode("utf-8")
   try:
      out = subprocess.check_output(cmd, shell=True).decode("utf-8")
   except:
      print(cmd, "GREP NOT FOUND")
      print("add to key file")
      fp = open(key_file, "a")
      fp.write(key)
      fp.close()


else:
   print("make key file")
   if os.path.exists("/home/ams/.ssh/") is False:
      os.makedirs(("/home/ams/.ssh/")
   fp = open(key_file, "w")
   fp.write(key)
   fp.close()

cmd = "git rev-list --count HEAD"
out = subprocess.check_output(cmd, shell=True).decode("utf-8")
out = int(out.replace("\n", ""))
print("REVISION NUMBER IS : ", out)
print("Last Git Update: ", now)

json_conf_file = "/home/ams/amscams/conf/as6.json"
json_conf = load_json_file(json_conf_file)
json_conf['git_revision'] = out
json_conf['git_last_update'] = now 
save_json_file(json_conf_file, json_conf)
os.system("cp /home/ams/lastpull.txt /mnt/archive.allsky.tv/" + json_conf['site']['ams_id'] + "/lastpull.txt")
