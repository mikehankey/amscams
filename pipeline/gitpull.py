import os
import datetime
now = datetime.datetime.now().strftime("%Y_%m_%d")
git_save_dir = "/home/ams/git_save/" + now + "/"
git_root = "/home/ams/amscams/"

if os.path.exists(git_save_dir) is False:
   os.makedirs(git_save_dir)

cmd = "git pull > /home/ams/gitlog.txt 2>&1"
os.system(cmd)
fp = open("/home/ams/gitlog.txt")
errors = False
for line in fp:
   line = line.replace("\n", "")
   if errors is True and "/" in line:
      print("STASH:", line)
      line = line.replace(" ", "")
      line = line.replace("\t", "")
      cmd = "mv " + git_root + line + " " + git_save_dir
      print(cmd)
      os.system(cmd)

   if "error" in line:
      errors = True
