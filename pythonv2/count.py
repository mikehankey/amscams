#!/usr/bin/python3
import numpy as np
import glob
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from lib.FileIO import load_json_file
json_conf = load_json_file("../conf/as6.json")

def count_days(days):
   data = {}
   for day in days:
      data = count_day(day, data)
   plot_data(data)

def plot_data(data):
   dx = []
   dy = []
   for d in sorted(data.keys()):
      #di = d.replace("2019_12_14", "")
      di = int(d.replace("_", ""))
      out = str(d) + "," + str(data[d])
      print(out)
      dx.append(di)
      dy.append(data[d])
   plt.xticks(rotation=90)
   plt.xticks(np.arange(min(dx), max(dx)+1, 10))

   plt.plot(dx, dy)
   plt.savefig("/mnt/ams2/gem-plot.png")

def count_day(day, data):
   glob_dir = "/mnt/ams2/meteors/" + day + "/*-HD-meteor-stacked.png"
   files = glob.glob(glob_dir)
   for file in files:
      fn = file.split("/")[-1]
      date_int = fn[0:15]
      print(file)
      if date_int not in data:
         data[date_int] = 1
      else:
         data[date_int] = data[date_int] + 1
   return(data)

count_days(("2019_12_12", "2019_12_13", "2019_12_14", "2019_12_15", "2019_12_16"))
