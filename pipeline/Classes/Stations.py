from lib.PipeUtil import load_json_file
import os
import subprocess
import time
from prettytable import PrettyTable as pt

class Stations():
   def __init__(self):
      print("ALL SKY STATIONS")
      # use this class to load up station data and perform basic station functions
      self.start = time.time()

   def load_station_data(self):
      # we have station data in more than one place
      # this will pull them together and put them in just 
      # a few arrays

      # this is the main / master source but might have missing / incomplete info
      dyna_station_data = load_json_file("/mnt/f/EVENTS/ALL_STATIONS.json")
      self.rurls = {}
      self.dyna_stations = {}
      self.photo_credits = {}
      operator_name = "" 
      city = "" 
      state = ""
      country = ""


      for row in dyna_station_data:
         sid = row['station_id']
         self.dyna_stations[sid] = row
         if "operator_name" in row:
            operator_name = row['operator_name']
         else:
            row['operator_name'] = ""
         if "city" in row:
            city = row['city']
         else:
            row['city'] = ""
         if "state" in row:
            state = row['state']
         else:
            row['state'] = ""
         if "country" in row:
            country = row['country']
         else:
            row['country'] = ""

         if operator_name == "" or operator_name == " " :
            self.photo_credits[sid] = sid + " unknown"
         elif operator_name != "" and city != "" and state != "" and ("United States" in country or "US" in country):
            self.photo_credits[sid] = operator_name + " " + city + "," + state + " " +  country
         elif operator_name != "":
            self.photo_credits[sid] = operator_name + " " + city + "," + country
         else:
            self.photo_credits[sid] = sid

      # this is the EU stations file url is the main thing we are missing
      if os.path.exists("stations.json"):
         #std = os.stat("stations.json")
         ctime = os.path.getctime("stations.json") 
         time_diff = (time.time() - ctime) / 60 / 60 / 24
      else:
         time_diff = 9999

      if time_diff > 1:
         cmd = "wget -q https://allsky7.net/stations/stations.json -O stations.json"
         os.system(cmd)
      self.station_data = load_json_file("stations.json")

      for data in self.station_data['stations']:
         station = data['name']
         url = data['url']
         operator = data['operator']
         location = data['location']
         country = data['country']
         self.rurls[station] = url

      # now populate the photo credits and 
      # remote urls for all stations

      self.station_loc = {}
      for st_id in self.dyna_stations:
         row = self.dyna_stations[st_id]
         lat = row['lat']
         lon = row['lon']
         alt = row['alt']
         self.station_loc[st_id] = [lat,lon,alt]

      # get vp hosts 

      self.vpn_hosts = {}
      #cmd = "grep 10.8.0 /mnt/archive.allsky.tv/AMS1/info.txt"
      cmd = "grep 10.8.0 vpn.txt" #/mnt/archive.allsky.tv/AMS1/info.txt"
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
      lines = output.split("\n")

      for line in lines :
         if "10.8.0" in line and "," in line:
            data = line.split(" ")[0]
            sid,ip = data.split(",")
            self.vpn_hosts[sid] =  ip
            if "AMS" not in sid:
               sid = "AMS" + sid
            if sid not in self.rurls:
               self.rurls[sid] = "http://" + ip

      # get exta hosts dataplicity, port fwd, custom vpns etc
      output = open("extra_hosts.txt")
      for data in output:
         sid,ip = data.split(",")
         if sid not in self.rurls:
            self.rurls[sid] = ip

      tb = pt()
      tb.field_names = ["Station", "Location","Credits", "Remote URL"]
      for station_id in self.rurls:
         if station_id not in self.dyna_stations:
            print(station_id, "missing from dyna_stations")
         elif station_id not in self.station_loc:
            print(station_id, "missing from station_loc")
         elif station_id not in self.photo_credits:
            print(station_id, "missing from photo_credits")
         elif station_id not in self.rurls:
            print(station_id, "missing from rurls")
         else:
            #print(station_id, self.station_loc[station_id]) #, self.photo_credits[station_id], self.rurls[station_id])
            tb.add_row([station_id,  self.station_loc[station_id], self.photo_credits[station_id], self.rurls[station_id]])
      print(tb)
