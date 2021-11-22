
import os
import sys

if os.path.exists("tensorflow-2.4.4-cp36-cp36m-linux_x86_64.whl") is False:
   cmd = "wget https://archive.allsky.tv/AMS9/tensorflow-2.4.4-cp36-cp36m-linux_x86_64.whl"
   os.system(cmd)
if os.path.exists("/usr/bin/python3.6") is False:
   print("NO PYTHON3.6 INSTALL IT.")
   cmd = "sudo add-apt-repository ppa:deadsnakes/ppa"
   os.system(cmd)
   cmd = "sudo apt-get update"
   os.system(cmd)
   cmd = "sudo apt-get install python3.6"
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


cmd = "sudo python3.6 -m pip install /home/ams/amscams/install/tensorflow-2.4.4-cp36-cp36m-linux_x86_64.whl"
os.system(cmd)

cmd = "sudo python3.6 -m pip install tensorboard"
os.system(cmd)
cmd = "sudo python3.6 -m pip install tb-nightly"
os.system(cmd)

cmd = "sudo python3 -m pip install --upgrade pillow"
os.system(cmd)
