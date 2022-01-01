import os
import sys


date = sys.argv[1]
files = os.listdir("/mnt/ams2/meteors/" + date + "/") 
data = {}
for ff in files:
   if "reduced" in ff or "cloud" in ff or "report" in ff or "star" in ff:
      continue
   if "json" not in ff:
      continue
   el = ff.split("_")
   print(el)
   ex = el[7].split("-")[0]
   if ex not in data:
      data[ex] = 1
   else:
      data[ex] += 1


print("Stats by cam for " + date)
for dd in sorted(data):
   print(dd, data[dd])
