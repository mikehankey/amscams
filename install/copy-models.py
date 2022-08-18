import os

if os.path.exists("../pipeline/models") is False:
   os.makedirs("../pipeline/models")

cmd = "sudo chown -R ams:ams /home/ams/amscams/pipeline/models"
os.system(cmd)

if os.path.exists("/home/ams/amscams/pipeline/models/ASAI-v2.7z") is False:
   cmd = "sudo cp /mnt/archive.allsky.tv/AMS1/ML/ASAI-v2.7z ../pipeline/models/"
   os.system(cmd)
   cmd = "sudo chown -R ams:ams /home/ams/amscams/pipeline/models"
   os.system(cmd)
   cmd = "cd /home/ams/amscams/pipeline/models; 7z e /home/ams/amscams/pipeline/models/ASAI-v2.7z"
   os.system(cmd)

cmd = "python3.6 -m pip install requests"
os.system(cmd)
