#!/usr/bin/python3 
import sys
import os

print("DIS:", sys.argv)
go = sys.argv[1]

if int(go) == 1:
    cmd = "/usr/bin/python3 ca.py ca -c cam7 -p 7676"
    os.system(cmd)
    print(cmd)
    cmd = "/usr/bin/python3 ca.py ca -c cam6 -p 7676"
    print(cmd)
    os.system(cmd)
    cmd = "/usr/bin/python3 ca.py ca -c cam5 -p 7676"
    os.system(cmd)
    print(cmd)
    cmd = "/usr/bin/python3 ca.py ca -c cam4 -p 7676"
    os.system(cmd)
    print(cmd)
    cmd = "/usr/bin/python3 ca.py ca -c cam3 -p 7676"
    os.system(cmd)
    print(cmd)
    cmd = "/usr/bin/python3 ca.py ca -c cam2 -p 7676"
    os.system(cmd)
    print(cmd)
    cmd = "/usr/bin/python3 ca.py ca -c cam1 -p 7676"
    os.system(cmd)
    print(cmd)
