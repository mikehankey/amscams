import sys
import json, csv
import time
from lib.PipeUtil import dist_between_two_points
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from windrose import WindroseAxes
import matplotlib.cm as cm
import numpy as np
from lib.PipeUtil import load_json_file, save_json_file
import requests
import ssl
from scipy.interpolate import make_interp_spline

def plot_file(wind_file):
   alts = []
   press = []
   speeds = []
   dirs = []
   temps = []
   relhs = []
   fp = open(wind_file)
   for line in fp:
      line = line.replace("\n", "")
      data = line.split(",")
   plot_wind_data(alts, press, speeds, dirs, temps, relhs, plot_file)

def parse_sounding (proj_file, proj_data):
   plot_file = proj_file.replace(".json", "_WEATHER.png")
   mean_wind_file = proj_file.replace(".json", "-mean-wind.csv")
   print("WIND DATA:", proj_data['wind_data'].keys())
   wd = proj_data['wind_data']
   nc = 0
   lines = []
   line_data = []
   for sid in wd:
      if "html" in wd[sid]:
         html = wd[sid]['html']
         html = html.replace("<PRE>", "\n<PRE>")
         lines = html.split("\n")
         start = False 
         ltype = None
         for line in lines:
            if "<H2>" in line:
               ltype = "MAIN"
               title = line
            if "<H3>" in line:
               ltype = "SUB"
               title = line

            if "<PRE>" in line:
               start = True
               nc += 1
            if "</PRE>" in line:
               start = False 
            if start == True:
               print(nc, start, ltype, line)
               line_data.append((nc, sid, title, ltype, line))

   merge_data = {}
   for line in line_data:
      if line[3] == "MAIN":
         data = line[4].split()
         print(data)
         sid = line[2]
         if len(data) == 11:
            if data[0] == "PRES" or data[0] == "hPa":
               continue
            abin = int(float(data[1]) / 100)
            if abin not in merge_data:
               merge_data[abin] = []
            print(data)
            print("ABIN", abin)
            merge_data[abin].append(data)

   final_data = []
   for abin in merge_data:
      #print(abin, merge_data[abin])
      presses= []
      heights = []
      temp_cs = []
      dwpts = []
      relhs = []
      mixrs = []
      wind_dirs = []
      wind_speeds = []
      thtas = []
      thtes = []
      thtvs = []
      for data in merge_data[abin]:
         pr, ht, temp_c, dwpt, relh, mixr, wind_dir, wind_speed, thta, thte, thtv = data
         presses.append(float(pr))
         heights.append(float(ht))
         temp_cs.append(float(temp_c))
         dwpts.append(float(dwpt))
         relhs.append(float(relh))
         mixrs.append(float(mixr))
         wind_dirs.append(float(wind_dir))
         wind_speeds.append(float(wind_speed))
         thtas.append(thta)
         thtes.append(thte)
         thtvs.append(thtv)

      if len(presses) == 0:
         continue

      elif len(presses) == 1:
         mpress = float(presses[0])
         mtemp = float(temp_cs[0])
         mdwpt = float(dwpts[0])
         mrelh = float(relhs[0])
         mwind_dir = float(wind_dirs[0])
         mwind_speeds = float(wind_speeds[0])
      elif 1 < len(presses) == 3:
         mpress = np.mean(presses)
         mtemp = np.mean(temp_cs)
         mdwpt = np.mean(dwpts)
         mrelh = np.mean(relhs)
         mwind_dir = np.mean(wind_dirs)
         mwind_speed = np.mean(wind_speeds)
      else:
         mpress = np.median(presses)
         mtemp = np.median(temp_cs)
         mdwpt = np.median(dwpts)
         mrelh = np.median(relhs)
         mwind_dir = np.median(wind_dirs)
         mwind_speed = np.median(wind_speeds)
      #print(abin * 100, round(mpress,2), round(mtemp,2), round(mdwpt,2), round(mrelh,2), round(mwind_dir,2), round(mwind_speed,2))
      final_data.append((abin * 100, round(mpress,2), round(mtemp,2), round(mdwpt,2), round(mrelh/100,2), round(mwind_dir,2), round(mwind_speed,2)))

   final_data = sorted(final_data, key=lambda x: x[0], reverse=False)

   alts = []
   press = []
   speeds = []
   dirs = []
   temps = []
   relhs = []

   dfn_data = []
   for row in final_data:
      alts.append(row[0])
      press.append(row[1])
      temps.append(row[2])
      relhs.append(row[4])
      dirs.append(row[5])
      speeds.append(row[6])
      dfn_data.append((row[0], row[2]+273.15, row[1]*100,row[4],row[6],row[5]))
      print((row[0], row[2]+273.15, row[1]*100,row[4],row[6],row[5]))
  


   fieldnames=['#Height','TempK','Press','RHum','Wind', 'Wdir']
   #Height,TempK,Press,RHum,Wind,WDir
   with open(mean_wind_file, 'w', newline='') as f:
      writer = csv.writer(f)
      writer.writerow(fieldnames)
      writer.writerows(dfn_data)

   print(mean_wind_file)
   input("wait")
   plot_wind_data(alts, press, speeds, dirs, temps, relhs, plot_file)
   print("DONE")

def get_sounding(project_id):
   ssl._create_default_https_context = ssl._create_unverified_context
   proj_file = "DFM/" + project_id + "/" + project_id + ".json"
   proj_data = load_json_file(proj_file)
   if "wind_data" in proj_data:
      # already did it 
      return(proj_file, proj_data)

   # get location and time of fall
   date, stime = proj_data['exposure_time'].split("T")
   year,month,day = date.split("-")
   hour,minute,second = stime.split(":")
   lat = proj_data['slat']
   lon = proj_data['slon']

   # if US region 
   fp = open("DFM/stations_us.txt")
   data = []
   for line in fp:
      if line[0] == "#":
         continue
      line = line.replace("\n", "")
      rdata = line.split("\t")
      sname, slat, slon, country, sid = rdata
      dist_from_station = dist_between_two_points(float(lat), float(lon), float(slat), float(slon))
      data.append((sname, slat, slon, country, sid, dist_from_station ))
   data = sorted(data, key=lambda x: x[5], reverse=False)

   # grab 5 closest stations
   proj_data['wind_stations'] = data[0:5]

   # build the links for 5 closest stations
   c = 0
   wind_data = {}
   for r in data:
      sid = r[4]
      if len(sid) == 6:
         sid = sid[0:5]
      base_link = "http://weather.uwyo.edu/cgi-bin/sounding?region=naconf&TYPE=TEXT%3ALIST&YEAR={:s}&MONTH={:s}&FROM={:s}00&TO={:s}23&STNM={:s}".format(year, month, day, day, sid) 
      wind_data[sid] = {}
      wind_data[sid]['link'] = base_link
      if c >= 3:
         break
      c += 1

   # fetch wind data for 5 closest stations
   for sid in wind_data:
      if "html" not in wind_data[sid]:
         print("FETCH:", wind_data[sid]['link'])
         #try:
         count = 0
         if True:
            doit = True
            while doit is True:
               resp = requests.get(wind_data[sid]['link'])
               content = resp.content.decode()
               if "Sorry" not in content :
                  wind_data[sid]['html'] = content
                  doit = False
               else:
                  if "fail" not in wind_data[sid] :
                     wind_data[sid]['fail'] = 0
                  else:
                     wind_data[sid]['fail'] += 1
                  print("Pause 3 seconds...")
                  count += 1
                  time.sleep(3)
               if count > 3:
                  doit = False

            print("GOOD", content) 
         #except: 
         else:
            if "fail" not in wind_data[sid] :
               wind_data[sid]['fail'] = 0
            else:
               wind_data[sid]['fail'] += 1
            print("FAIL", sid, wind_data[sid]['link']) 
      #input("Continue?")

   proj_data['wind_data'] = wind_data
   save_json_file(proj_file, proj_data)

   return(proj_file, proj_data)

def plot_wind_data(alts, press, speeds, dirs, temps, relhs, plot_file):

   wind_plot_file = plot_file.replace(".png", "-windrose.png")

   ax = WindroseAxes.from_ax()
   ax.bar(dirs, speeds, normed=True, opening=0.8, edgecolor='white')
   ax.set_legend()

   plt.savefig(wind_plot_file, dpi=72)

   fig, (ax1, ax2, ax3,ax4,ax5) = plt.subplots(1,5)
   fig.set_size_inches(12,4)
   fig.tight_layout(pad=5.0)
   ax1.plot(speeds, alts)
   ax1.set_xlabel("Wind Speed")
   ax1.set_ylabel("Altitude")


   ax2.plot(dirs, alts)
   ax2.set_xlabel("Wind Dir")

   ax3.plot(temps, alts)
   ax3.set_xlabel("TempK")

   ax4.plot(press, alts)
   ax4.set_xlabel("Press")

   ax5.plot(relhs, alts)
   ax5.set_xlabel("Relh")
   fig.suptitle(fall_name + " Atmospheric Data" ,  fontsize=16)

   #plot_file = cal_dir + "plots/" + station_id + "_" + cam_id + "_CAL_PLOTS.png"
   fig.savefig(plot_file, dpi=72)
   print(plot_file)
   #plt.show()

def plot_wind_file(wind_file):
   fp = open(wind_file)
   
   plot_file = wind_file.replace(".csv", ".png")
   wind_plot_file = wind_file.replace(".csv", "-windrose.png")
   
   alts = []
   speeds = []
   dirs = []
   temps = []
   press = []
   relh = []
   
   for line in fp :
      if line[0] == "#" :
         continue
   
      line = line.replace("\n", "")
      data = line.split(",")
      print(data)
      Height, TempK, Press, RHum, Wind, WDir = data
      h = int(float(Height)/1000) 
      p = int(float(Press) / 1000)
      t = int(float(TempK))
      # -180 if the value has been reversed already
      wd = round(float(WDir),0) - 180
      w = round(float(Wind),0)
      r = round(float(RHum),1)
      alts.append(h)
      press.append(p)
      speeds.append(w)
      dirs.append(wd)
      temps.append(t)
      relh.append(r)
   
   
   ax = WindroseAxes.from_ax()
   ax.bar(dirs, speeds, normed=True, opening=0.8, edgecolor='white')
   ax.set_legend()
   plt.savefig(wind_plot_file, dpi=72)

   fig, (ax1, ax2, ax3,ax4,ax5) = plt.subplots(1,5)
   fig.set_size_inches(12,4)
   fig.tight_layout(pad=5.0)
   ax1.scatter(speeds, alts)
   ax1.set_xlabel("Wind Speed")
   ax1.set_ylabel("Altitude")
   
   ax2.scatter(dirs, alts)
   ax2.set_xlabel("Wind Dir")
   
   ax3.scatter(temps, alts)
   ax3.set_xlabel("TempK")
   
   ax4.scatter(press, alts)
   ax4.set_xlabel("Press")
   
   ax5.scatter(relh, alts)
   ax5.set_xlabel("Relh")
   fig.suptitle(fall_name + " Atmospheric Data" ,  fontsize=16)
   
   #plot_file = cal_dir + "plots/" + station_id + "_" + cam_id + "_CAL_PLOTS.png"
   fig.savefig(plot_file, dpi=72)
   print(plot_file)
   plt.show()
   
   
if __name__ == "__main__": 
   fall_name = ""
   proj_name = sys.argv[1]
   #proj_file, proj_data = get_sounding("Muskogee")
   if proj_name == "plot_file":
      plot_file(sys.argv[2])
   else:
      proj_file, proj_data = get_sounding(proj_name)
      proj_data = parse_sounding(proj_file, proj_data)
   exit()
