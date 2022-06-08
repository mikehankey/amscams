
import os
import sys

if os.path.exists("tensorflow-installed.txt") :
   print("python3.6 with tensorflow is already installed.")
   exit()

if os.path.exists("/usr/bin/python3.6") is False and os.path.exists("/usr/local/bin/python3.6") is False:
   print("NO PYTHON3.6 INSTALL IT.")
   cmd = "sudo add-apt-repository -y ppa:deadsnakes/ppa"
   os.system(cmd)
   cmd = "sudo apt-get update"
   os.system(cmd)
   cmd = "sudo apt-get -y install python3.6"
   os.system(cmd)
   cmd = "wget https://bootstrap.pypa.io/get-pip.py"
   os.system(cmd)
   cmd = "sudo python3.6 get-pip.py"
   os.system(cmd)
   #cmd = "sudo python3.6 -m pip uninstall pillow"
   #os.system(cmd)
   cmd = "sudo python3.6 -m pip install --upgrade pillow"
   os.system(cmd)
   cmd = "sudo python3.6 -m pip install --upgrade opencv-python"
   os.system(cmd)
   cmd = "sudo python3.6 -m pip install --upgrade ephem"
   os.system(cmd)


if os.path.exists("tensorflow-2.4.4-cp36-cp36m-linux_x86_64.whl") is False:
   cmd = "wget https://archive.allsky.tv/AMS9/tensorflow-2.4.4-cp36-cp36m-linux_x86_64.whl"
   os.system(cmd)
   cmd = "sudo python3.6 -m pip install /home/ams/amscams/install/tensorflow-2.4.4-cp36-cp36m-linux_x86_64.whl"
   os.system(cmd)

cmd = "sudo python3.6 -m pip install tensorboard"
os.system(cmd)
cmd = "sudo python3.6 -m pip install tb-nightly"
os.system(cmd)

cmd = "sudo python3.6 -m pip install pillow"
os.system(cmd)

cmd = "sudo python3.6 -m pip install sklearn"
os.system(cmd)

cmd = "sudo python3.6 -m pip install scikit-image"
os.system(cmd)

cmd = "sudo python3.6 -m pip install opencv-python"
os.system(cmd)

cmd = "sudo python3.6 -m pip install --force-reinstall --upgrade flask"
os.system(cmd)
cmd = "sudo python3.6 -m pip install --force-reinstall --upgrade flask_httpauth"
os.system(cmd)


cmd = "sudo python3 -m pip install --force-reinstall --upgrade pillow"
os.system(cmd)
cmd = "sudo python3 -m pip install --force-reinstall --upgrade markupsafe"
os.system(cmd)
cmd = "sudo python3 -m pip install --force-reinstall --upgrade flask"
os.system(cmd)
cmd = "sudo python3 -m pip install --force-reinstall --upgrade Click" 
os.system(cmd)
cmd = "sudo python3 -m pip install --force-reinstall --upgrade six"
os.system(cmd)
cmd = "sudo python3 -m pip install --force-reinstall --upgrade requests"
os.system(cmd)
cmd = "sudo python3 -m pip install --force-reinstall --upgrade flask_httpauth"
os.system(cmd)

cmd = "touch tensorflow-installed.txt"
os.system(cmd)

if os.path.exists("../pipeline/models") is False:
   os.makedirs("../pipeline/models")

if os.path.exists("/home/ams/amscams/pipeline/models/ASAI-v2.7z") is False:
   cmd = "cp /mnt/archive.allsky.tv/AMS1/ML/ASAI-v2.7z ../pipeline/models/"
   os.system(cmd)
   cmd = "7z e /home/ams/amscams/pipeline/models/ASAI-v2.7z"
   os.system(cmd)
