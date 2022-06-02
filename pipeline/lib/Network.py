import requests
import os
from lib.Utils import load_json_file, save_json_file 

def fetch_url(url, save_file=None, json=None):
    r = requests.get(url)
    if save_file is None:
       if json == 1:
          return(r.json())
       else:
          return(r.text)

    else:
       open(save_file, 'wb').write(r.content)

def get_station_data():
   station_dict = {}
   station_data_file = "Data/STATION_DATA/station_data.json"
   if os.path.exists("Data/STATION_DATA/") == 0:
      os.makedirs("Data/STATION_DATA/")
   if os.path.exists("Data/STATION_DATA/station_data.json") == 0:
      station_data = fetch_url("https://archive.allsky.tv/EVENTS/ALL_STATIONS.json", json=1)
      save_json_file("Data/STATION_DATA/station_data.json", station_data)
   else:
      station_data = load_json_file(station_data_file)
   for row in station_data:
      print(row)
      station_dict[row['station_id']] = row    
   return(station_data, station_dict)

#fetch_url("https://archive.allsky.tv/AMS18/CAL/2021_07_16_00_32_02_000_010103.png", "test.png")
#get_station_data()
