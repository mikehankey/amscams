"""

test that all pip libs are installed for all python versions

"""
import os

python_versions = ['python3', 'sudo /usr/bin/python3', 'sudo /usr/bin/python3.6']

fp = open("pip.conf")
for line in fp:
   line = line.replace("\n", "")
   for pv in python_versions:
      cmd = pv + " -m pip install " + line
      print(cmd)
      os.system(cmd)
