import pkg_resources
import sys
import os
# see what we have
installed = {pkg.key for pkg in pkg_resources.working_set}

fp = open("pip.conf")
PYTHON_EXE = sys.executable 
for line in fp:
   line = line.replace("\n", "")
   if "3.6" in PYTHON_EXE and "pyfits" in line:
      continue
   if line in installed:
      print("OK : ", line)
   else:
      cmd = PYTHON_EXE + " -m pip install " + line
      print(cmd)
      os.system(cmd)
