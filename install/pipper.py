import pkg_resources
import sys
import os
# see what we have

region = os.getenv("region")

installed = {pkg.key for pkg in pkg_resources.working_set}

APT_EXE = "apt-get install --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages "
fp = open("apt.conf")
for line in fp:
   cmd = APT_EXE + line
   print(cmd)
   os.system(cmd)


fp = open("pip.conf")
PYTHON_EXE = "" + sys.executable 
for line in fp:
   line = line.replace("\n", "")
   if "3.6" in PYTHON_EXE and ("fitsio" in line or "pyfits" in line or "uwsgi" in line):
      print("SKIP:", line)
      continue
   if line in installed:
      print("OK : ", line)
   else:
      cmd = PYTHON_EXE + " -m pip install " + line
      if region == 'cn':
         line += " -i https://pypi.mirrors.ustc.edu.cn/simple/"
      print(cmd)
      os.system(cmd)
