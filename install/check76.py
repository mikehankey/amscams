#!/usr/bin/python3

import os

os.system("ip a |grep 192.168.76 > ip.txt")
fp = open("ip.txt")
lc = 0
for line in fp:
   lc += 1

if lc == 0:
   print("The ip is down.")
   os.system("netplan apply")
else:
   print("The ip is up.")
