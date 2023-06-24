#!/usr/bin/python3
#geolocator = Nominatim(user_agent="geoapiExercises")
from prettytable import PrettyTable as pt
import pandas as pd
import datetime 
import time 
import math
import glob
import numpy as np
import os
import requests
import sys
from lib.PipeUtil import save_json_file, load_json_file, get_file_info, dist_between_two_points 
from Classes.AllSkyNetwork import AllSkyNetwork

import plotly.express as px
import plotly.graph_objects as go
from geopy.geocoders import Nominatim
import seaborn as sns

class AMSAPI():
   def __init__(self):
      #if ams_event_id is not None:
      #   self.year, self.ams_event_id = ams_event_id.split("-")
      #elif year is not None:
      #   self.year = year

     ams_key = load_json_file("ams.key")
     self.ams_api_key = ams_key['ams_key']
     self.json_conf = load_json_file("../conf/as6.json")
     self.lat = self.json_conf['site']['device_lat']
     self.lon = self.json_conf['site']['device_lng']
     self.stations = load_json_file("/mnt/f/EVENTS/ALL_STATIONS.json")
     self.station_dict = {}
     self.as7_dir = "/mnt/f/EVENTS/"
     self.ams_as7_dir = "/mnt/f/EVENTS/AMS_AS7/"
     self.geolocator = Nominatim(user_agent="geoapiExercises")
     self.events = {}
     self.obs = {}
     for row in self.stations:
        if row['lat'] != "" and row['lon'] != "" and "cameras" in row:
           self.station_dict[row['station_id']] = row

   def ams_as7_report(self, data):
      temp = {}
      tb = pt()
      tb.field_names = ["AMS ID", "AMS Date (utc)", "Country", "AS7 Stations", "AS7 Obs", "AS7 Event ID"]
      for ev_id in data['ams_events'].keys():
         new_ev_id = int(ev_id)
         temp[new_ev_id] = data['ams_events'][ev_id]
      data['ams_events'] = temp

      final = []

      for ev_id in sorted(data['ams_events'].keys(), reverse=True):
         print(data['ams_events'][ev_id].keys())
         if type(ev_id) == str:
            ams_id = ev_id.replace("Event #", "")
         as7_station_count = 0
         as7_event_id = "" 
         as7_date_utc = "" 
         ams_date_utc = data['ams_events'][ev_id]['avg_date_utc'] 
         if "country_code" in data['ams_events'][ev_id]:
            c_code = data['ams_events'][ev_id]['country_code']
         else:
            c_code = "no geo"
         if "allsky7" in data['ams_events'][ev_id]:
            if len(data['ams_events'][ev_id]['allsky7']['stations']) > 0:
               as7_station_count = len(data['ams_events'][ev_id]['allsky7']['stations'])      
            if "obs_data" in data['ams_events'][ev_id]['allsky7']:
               as7_obs_count = len(data['ams_events'][ev_id]['allsky7']['obs_data'])
            else:
               as7_obs_count = 0
            if "event_data" in data['ams_events'][ev_id]['allsky7']:
               evd = data['ams_events'][ev_id]['allsky7']
               print(evd.keys())
               if evd['event_data'] is not None:
                  # AS7 solution exists
                  if "event_id" in evd['event_data']:
                     as7_event_id = evd['event_data']['event_id']
                  if "start_datetime" in evd['event_data']:
                     as7_date_utc = evd['event_data']['start_datetime']
         #print(ev_id, ams_date_utc, as7_date_utc, as7_station_count, as7_event_id) 
         final.append((ev_id, ams_date_utc, c_code, as7_station_count, as7_obs_count, as7_event_id))

      final = sorted(final, key=lambda x: x[1], reverse=True)
      for row in final:
         ev_id, ams_date_utc, as7_date_utc, as7_station_count, as7_obs_count, as7_event_id = row
         tb.add_row([ev_id, ams_date_utc, as7_date_utc, as7_station_count, as7_obs_count, as7_event_id])
      print(tb)

   def get_bearing(self, lat1, long1, lat2, long2):
      dLon = (long2 - long1)
      x = math.cos(math.radians(lat2)) * math.sin(math.radians(dLon))
      y = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(dLon))
      brng = np.arctan2(x,y)
      brng = np.degrees(brng)
      if brng < 0:
         brng += 360

      return brng

   def get_ams_events(self, year, min_reports):
      cache_file = "ams_" + year + ".json"
      go = False
      if os.path.exists(cache_file) is False:
         go = True
      else: 
         sz, td = get_file_info(cache_file)
         if (td / 60 / 60) > 1:
            go = True
            print("GO=TRUE TIME DIFF DAYS:", td / 60 / 60, go)
         else:
            go = False
            print("GO=FALSE TIME DIFF DAYS:", td / 60 / 60, go)

      if go is True:
         url = "http://www.amsmeteors.org/members/api/open_api/get_events"
         data = {'api_key' : self.ams_api_key, 'year' : year, 'format' : 'json', 'min_reports':  5}
         r = requests.get(url, params=data)
         my_data = r.json()
         save_json_file(cache_file, my_data )
      else:
          
         my_data = load_json_file(cache_file)
         print(cache_file)
         print("Using cache file: " + cache_file)
      temp = {}
      for ams_event_id in sorted(my_data['result']):
         new_event_id = ams_event_id.replace("Event #", "")
         new_event_id = int(new_event_id.replace(year + "-", ""))

         temp[new_event_id] = my_data['result'][ams_event_id]
      my_data['result'] = temp
      return(my_data)

   def get_ams_event(self, year, event_id):

      url = "http://www.amsmeteors.org/members/api/open_api/get_event"
      data = {'api_key' : self.ams_api_key, 'year' : year, 'event_id' : event_id, 'format' : 'json', 'ratings': 1, 'override': 1}
      r = requests.get(url, params=data)
      my_data = r.json()
      event_key = "Event #" + str(event_id) + "-" + str(year)
      start_lat =  my_data['result'][event_key]['start_lat']
      start_long =  my_data['result'][event_key]['start_long']
      end_lat =  my_data['result'][event_key]['end_lat']
      end_long =  my_data['result'][event_key]['end_long']
      event_datetime = my_data['result'][event_key]['avg_date_utc']
      impact_lat = my_data['result'][event_key]['impact_lat'];
      impact_long = my_data['result'][event_key]['impact_long']



      type = 'datetime'
      dates = []
      #dates = get_ams_reports(year, event_id, type)
      #better_event_datetime =  avg_dates(event_datetime, dates)


      return(start_lat, start_long, end_lat, end_long, impact_lat, impact_long, event_datetime)

   def get_station_obs(self, station_id, ams_event_data):
      #print("AMS DATA", ams_event_data)
      #print("AMS DATE:", ams_event_data['avg_date_utc'])
      try:
         date_utc_dt = datetime.datetime.strptime(ams_event_data['avg_date_utc'], "%Y-%m-%d %H:%M:%S")
      except:
         print("AMS UTC TIME ERROR ", ams_event_data['event_id'])
         return([]) 
      wild_minute = date_utc_dt.strftime('%Y_%m_%d_%H_%M')
      wild_day = date_utc_dt.strftime('%Y_%m_%d')
      wild_year = date_utc_dt.strftime('%Y')

      # check if there are meteors already logged in the archive folder
      cloud_wild = "/mnt/archive.allsky.tv/" + station_id + "/METEORS/" + wild_year + "/" + wild_day + "/" + station_id + "_" + wild_minute + "*"
      cloud_files = glob.glob(cloud_wild)
      #print("CLOUD WILD:", cloud_wild)
      #print("CLOUD FILES:", cloud_files)
      #if len(cloud_files) > 0:
      return(cloud_files)
      # check if there are meteors logged inside the DYNA DB

   def ams_as7_event_map(self, ams_event_data):
      print("DISABLED!")
      exit()
      data = {}
      data['lat'] =  []
      data['long'] =  []
      data['size'] =  []
      data['colors'] =  []
      data['texts'] =  []
      fig = go.Figure()
      for station in ams_event_data['allsky7']['stations']:
         sdata = ams_event_data['allsky7']['stations'][station] 
         lat,lon,alt = sdata['location']
         data['lat'].append(round(float(lat),1))
         data['long'].append(round(float(lon),1))
         data['texts'].append(station)
         if "cloud_files" not in ams_event_data['allsky7']['stations'][station]:
            color = "gray"
         elif len(ams_event_data['allsky7']['stations'][station]['cloud_files']) > 0:
            color = "green"
         else:
            color = "orange"
         data['colors'].append(color)
      fig.add_trace(go.Scattergeo(name="ALLSKY7 STATIONS", lon = data['long'], lat=data['lat'], text = data['texts'], marker_color=data['colors'], mode='markers' ))
      scopes = ['africa', 'asia', 'europe', 'north america', 'south america', 'usa', 'world']
      if "country_code" not in ams_event_data:
         ams_event_data['country_code'] = 'world'

      if ams_event_data['country_code'] == 'us':
        geo_scope='usa'
      elif ams_event_data['country_code'] == 'nz' or ams_event_data['country_code'] == 'au' or ams_event_data['country_code'] == 'kr':
        geo_scope='world'
      elif ams_event_data['country_code'] == 'world':
        geo_scope='world'
      else:
        geo_scope='europe'
 
      fig.update_geos(
              fitbounds="locations", 
        scope=geo_scope,
        resolution=110,
        showcountries=True,countrycolor="Black",
        showsubunits=True, subunitcolor="Blue"
      )
      fig.update_layout(
        mapbox_style='open-street-map',
        title = 'AMS EVENT ID:' + str(ams_event_data['ams_event_id']) + " " + ams_event_data['avg_date_utc'] + " UTC",
        height=720, 
        width=1280, 
        margin={"r":50,"t":50,"l":50,"b":50}
      )
      # add ams track line
      fig.add_trace(go.Scattergeo(name="WITNESS GROUND TRACK", lon = [ams_event_data['start_long'], ams_event_data['end_long']], lat=[ams_event_data['start_lat'],ams_event_data['end_lat']], text = ["WITNESS GROUND TRACK"], marker_color=['red'], mode='lines' ))
      fig.show()
      #fig.write_image("/mnt/ams2/fig1.jpg")
      return(fig)

   def load_events_for_day(self, date):

      date = date.replace("-", "_")
      y,m,d = date.split("_")
      day_dir = self.as7_dir + y + "/" + m + "/" + d + "/"
      self.event_file = day_dir + date + "_ALL_EVENTS.json"
      self.obs_file = day_dir + date + "_ALL_obs.json"
      if os.path.exists(self.event_file) is True:
         self.events[date] = load_json_file(self.event_file)
      else:
         self.events[date] = []
      if os.path.exists(self.obs_file) is True:
         self.obs[date] = load_json_file(self.obs_file)
      else:
         self.obs[date] = []

      print("Loaded ALLSKY7 events for day:", date, len(self.events[date]))

   def find_obs(self, avg_date_utc, lat,lon):
      tdate = avg_date_utc.split(" ")[0].replace("-", "_")
      try:
         tdate_dt = datetime.datetime.strptime(avg_date_utc, "%Y-%m-%d %H:%M:%S")
      except:
         return(None)
      found = []
      print(len(self.obs[tdate]), "TOTAL OBS")
      self.obs.keys()
      for obs in self.obs[tdate]:
         if "event_start_time" not in obs:
            obs['event_start_time'] = ""
         if obs['event_start_time'] != "":
            obs_dt =  datetime.datetime.strptime(obs['event_start_time'], "%Y-%m-%d %H:%M:%S.%f")
         else:
            fst = obs['sd_video_file'][0:19]
            obs_dt =  datetime.datetime.strptime(fst, "%Y_%m_%d_%H_%M_%S")
         tdiff = (tdate_dt - obs_dt).total_seconds() / 60
         #print("TD:", obs['station_id'], tdiff)
         if abs(tdiff) < 10:
             station = obs['station_id']
             if station in ASN.station_dict:
                slat = AA.station_dict[station]['lat']
                slon = AA.station_dict[station]['lon']
                op_status = AA.station_dict[station]['op_status']
                photo_credit = ASN.photo_credits[station]
             else:
                slat = 0
                slon = 0
             dist_from_obs = dist_between_two_points(float(lat), float(lon), float(slat), float(slon))
             print("   ", station, dist_from_obs)
             if dist_from_obs < 450: 
                print("   OBS:",   dist_from_obs, "dist", tdiff, "minutes", station, slat, slon, obs['station_id'], obs['sd_video_file'])
                obs['tdiff'] = tdiff
                obs['dist_from_ams'] = dist_from_obs
                found.append(obs)
      print("AS7 OBS NEAR ", avg_date_utc, lat, lon, len(found))
      return(found)

   def find_event(self, avg_date_utc, lat,lon):
      #check for AS7 events with a few minutes of the date passed in
      events = []
      try:
         avg_date_dt =  datetime.datetime.strptime(avg_date_utc, "%Y-%m-%d %H:%M:%S")
      except:
         print(avg_date_utc)
         input("AMS avg_date_dt is BAD:")
         return(None)

      tdate = avg_date_utc.split(" ")[0].replace("-", "_")
      for row in self.events[tdate]:
         if len(row['start_datetime'])  > 0:
            event_dt = datetime.datetime.strptime(min(row['start_datetime'][0]), "%Y-%m-%d %H:%M:%S.%f")
            elp_time = (avg_date_dt - event_dt).total_seconds()
         else:
            elp_time = 99999
         if abs(elp_time / 60) <= 3:
            # make sure the matched event is close to the ams event within a few 100 km!
            dist_from_station = dist_between_two_points(float(lat), float(lon), float(np.mean(row['lats'])), float(np.mean(row['lons'])))
            if dist_from_station < 600:
               events.append(row)
      if len(events) > 0:
         temp_ev = []
         for ev in events:
            for st in ev['start_datetime']:
               if type(st) != str:
                  min_st = min(st)
                  ev['start_datetime'] = min_st

            temp_ev.append(ev)
         events = temp_ev
         if len(events) == 1:
            return(events[0])
         else:
            for event in events:
               print("   AS7 EVENT:", event['stations'], event['start_datetime'])
            print("More than one AS7 event found!?")
            return(events[0])
   


   def populate_as7_data(self, ams_event_data):
     
      for station in ams_event_data['allsky7']['stations']:
          if station in ASN.photo_credits and station in ASN.station_dict:
             print("\t", station, AA.station_dict[station]['lat'], AA.station_dict[station]['lon'], AA.station_dict[station]['op_status'],  ASN.photo_credits[station], ams_event_data['allsky7']['stations'][station]) 
             print("\t", station, AA.station_dict[station]['lat'], AA.station_dict[station]['lon'], AA.station_dict[station]['op_status'],  ASN.photo_credits[station], ams_event_data['allsky7']['stations'][station]) 
      return(ams_event_data)


   def create_map(self, title,points, lines, center_lat, center_lon, zoom):
       # Set up the map layout
       palette = sns.color_palette("dark", len(points) + len(lines))
       colors = []
       for r,g,b in palette:
          c = "rgb(" + str(r*255) + "," + str(g*255) + "," + str(b*255) + ")"
          colors.append(c)


       layout = go.Layout(
           mapbox_style='open-street-map',
           mapbox_center_lon=center_lon,
           mapbox_center_lat=center_lat,
           mapbox_zoom=zoom
       )

       # Create Scattermapbox traces for points and lines
       data = []

       # Add points as scatter markers
       ic = 0
           #trace = go.Scattermapbox(
       for point in points:
           trace = go.Scattergeo(
               name = point['name'],
               lat=[point['lat']],
               lon=[point['lon']],
               mode='markers',
               marker=dict(
                   size=20,
                   symbol=point['symbol'],
                   color=colors[ic],
                   opacity=point['opacity'],

               )
           )
           data.append(trace)
           ic += 1

       # Add lines as scatter lines
               #text=line['name'],
       for line in lines:
           trace = go.Scattergeo(
               name="AMS Witness Ground Track",
               textposition='bottom right',
               lat=line['lats'],
               lon=line['lons'],
               mode='lines+text',
               line=dict(
                   color='red',
                   width=2
               )
           )
           data.append(trace)

       layout['title_text'] = title
       layout['font_color'] = 'black'
       #layout['mapbox_style'] ='open-street-map'
       # Create the figure
       print("LAYOUT:", layout)
       fig = go.Figure(data=data, layout=layout)

       scopes = ['africa', 'asia', 'europe', 'north america', 'south america', 'usa', 'world']
       if "country_code" not in ams_event_data:
          ams_event_data['country_code'] = 'world'

       if ams_event_data['country_code'] == 'us':
         geo_scope='usa'
       elif ams_event_data['country_code'] == 'nz' or ams_event_data['country_code'] == 'au' or ams_event_data['country_code'] == 'kr':
         geo_scope='world'
       elif ams_event_data['country_code'] == 'world':
         geo_scope='world'
       else:
         geo_scope='europe'
 
       fig.update_geos(
              fitbounds="locations", 
        scope=geo_scope,
        resolution=110,
        showcountries=True,countrycolor="Black",
        showsubunits=True, subunitcolor="Blue"
       )

       fig.update_geos(
           scope=geo_scope,
           showcountries=True,
           showsubunits=True, subunitcolor="Blue"
       ) 

       fig.update_layout(
        title = 'AMS EVENT ID:' + str(ams_event_data['ams_event_id']) + " " + ams_event_data['avg_date_utc'] + " UTC",
        height=720, 
        width=1280, 
        margin={"r":50,"t":50,"l":50,"b":50}
       )

       fig.show()

       return fig


if __name__ == '__main__':
   # 
   # this script should batch check AMS events and AS7 obs and make sure the obs are detected, 
   # important and updloaded, HD saved and shared to cloud all of these types of events should 
   # be considered "AMS EVENTS" -- this is code for big events.
   #

   # final output of this should be a AMS_ALLSKY7_DATA.json -- which has the merged results? (part1)
   # also need to do something for the MIN files / non-detected stuff. (part2)
   # part 1 = associate detected meteors
   # part 2 = associate minute files
   # part 3 = save all media in cloud regardless if the meteor is present or not

   year = sys.argv[1]
   AA = AMSAPI()
   ASN = AllSkyNetwork()
   ASN.load_stations_file()
   resp = AA.get_ams_events(year, 7)
   ams_as7_data = []
   ams_as7_data_file = AA.ams_as7_dir + year + "_AMS_AS7.json"
   temp = {}

   # load this year's previous run's data file if it exists
   if os.path.exists(ams_as7_data_file) is True:
      data = load_json_file(ams_as7_data_file)
      AA.ams_as7_report(data)
      ams_events = data['ams_events']
      for key in ams_events:
         if type(key) is str:
            if year in key:
               nkey = int(key.replace(year + "-", ""))
               temp[nkey] = ams_events[key]
            else:
               temp[key] = ams_events[key]
         else:
            temp[key] = ams_events[key]
      ams_events = temp
      data['ams_events'] = temp
   else:
      data = {}
      data['ams_events'] = {}
      ams_events = {}

   print("Loaded", ams_as7_data_file)

   print("AMS ONLY:", resp['result'].keys())
   print("AMS-AS7 :", data['ams_events'].keys())

   ams_ids = resp['result'].keys()
   ams_as7_ids = data['ams_events'].keys()

   # check which AMS events have already been processed 
   not_done_ams_ids = [] 
   done_ams_ids = [] 
   for ams_id in ams_ids:
      if ams_id in ams_as7_ids:
         print("Done already.", ams_id)
         done_ams_ids.append(ams_id)
         not_done_ams_ids.append(ams_id)
      else:
         print("Not Done already.", ams_id)
         not_done_ams_ids.append(ams_id)

   ams_as7_events = []
   ams_as7_nomatch_events = []
   #for ams_event_id in sorted(resp['result'], reverse=True):
   ec = 1
   total = len(not_done_ams_ids)
   print("DONE:", len(done_ams_ids))
   print("NOT DONE:", len(not_done_ams_ids))

   # only work on events that are not done yet
   for ams_event_id in sorted(not_done_ams_ids):
      print("Doing", ams_event_id,  ec, "of", total)
      ec += 1
      if ams_event_id not in ams_events:
         ams_events[ams_event_id] = resp['result'][ams_event_id]
         ams_events[ams_event_id]['ams_event_id'] = ams_event_id
         ams_events[ams_event_id]['allsky7'] = {}
         ams_events[ams_event_id]['allsky7']['stations'] = {}
      else:
         print("SKIP AMS EVENT ALREADY DONE", ams_event_id)
         #continue

      # get some geoloc data about the event (requires service / api or else dies after a few tries)
      if False: # "geoloc" not in ams_events[ams_event_id] or ams_events[ams_event_id]['geoloc'] == None:
         print("geoloc not in ams_events data yet",  ams_events[ams_event_id].keys())
         try:
         #if True:
            location = AA.geolocator.reverse(str(ams_events[ams_event_id]['start_lat'])+","+str(ams_events[ams_event_id]['start_long']))
            time.sleep(1)
            if location is not None:
               print("DID GEOLOC FOR ", ams_event_id, location.raw['address'])
               
               ams_events[ams_event_id]['country_code'] = location.raw['address']['country_code']
               ams_events[ams_event_id]['geoloc'] = location.raw['address']

               data['ams_events'] = ams_events
               #save_json_file(ams_as7_data_file, data)

               #save_json_file(ams_as7_data_file, ams_events)
         except:
            ams_events[ams_event_id]['country_code'] = "world" 
            ams_events[ams_event_id]['geoloc'] = None
            input("GEOLOC FAIL")

      ams_events[ams_event_id]['avg_date_utc'] = resp['result'][ams_event_id]['avg_date_utc']
      ams_events[ams_event_id]['date'] = resp['result'][ams_event_id]['avg_date_utc'].split(" ")[0]
      event_date = ams_events[ams_event_id]['date']

      # load all sky 7 events for this day if not already loaded
      if event_date not in AA.events:
         AA.load_events_for_day(event_date)   

      #if "allsky7_check_complete" not in ams_events[ams_event_id]:
      if True:
         # find AS7 event
         as7_event = AA.find_event(ams_events[ams_event_id]['avg_date_utc'], ams_events[ams_event_id]['end_lat'], ams_events[ams_event_id]['end_long'])
         # find AS7 obs 
         as7_obs = AA.find_obs(ams_events[ams_event_id]['avg_date_utc'], ams_events[ams_event_id]['end_lat'], ams_events[ams_event_id]['end_long'])
 
         ams_events[ams_event_id]['allsky7']['event_data'] = as7_event
         ams_events[ams_event_id]['allsky7']['obs_data'] = as7_obs
         ams_events[ams_event_id]['allsky7_check_complete'] = True

         if as7_event is not None:
            print("AS7 EVENT:", as7_event['event_id'])
            print("   STATIONS:", as7_event['stations'])
            print("   FILES:", len(as7_event['files']))
            print("   OBS:", len(as7_obs))

         # tag/append all stations on the map within 650 km of the event
         for st_id in AA.station_dict:
            if AA.station_dict[st_id]['op_status'] == "ACTIVE":
            #if True:
               dist_from_station = dist_between_two_points(float(AA.station_dict[st_id]['lat']), float(AA.station_dict[st_id]['lon']), float(resp['result'][ams_event_id]['epicenter_lat']), float(resp['result'][ams_event_id]['epicenter_long']))
               bearing = AA.get_bearing(float(AA.station_dict[st_id]['lat']), float(AA.station_dict[st_id]['lon']), float(resp['result'][ams_event_id]['epicenter_lat']), float(resp['result'][ams_event_id]['epicenter_long']))
               if dist_from_station < 650:
                  ams_events[ams_event_id]['allsky7']['stations'][st_id] = {}
                  ams_events[ams_event_id]['allsky7']['stations'][st_id]['station_id'] = st_id
                  ams_events[ams_event_id]['allsky7']['stations'][st_id]['station_distance'] = float(round(dist_from_station,2) )
                  ams_events[ams_event_id]['allsky7']['stations'][st_id]['station_bearing'] = float(round(bearing,1) )
                  ams_events[ams_event_id]['allsky7']['stations'][st_id]['location'] = [AA.station_dict[st_id]['lat'], AA.station_dict[st_id]['lon'], AA.station_dict[st_id]['alt']]

      points = []
      lines = []
      texts = []

      used_st = {}
      title = "AMS EVENT:" + str(ams_event_id) + " " + ams_events[ams_event_id]['avg_date_utc']
      if as7_event is not None:
         for event in as7_event:
            print("E", event)

      for obs in as7_obs:
         oid = obs['station_id'] + "_" + obs['sd_video_file']
         used_st[obs['station_id']] = {} 
         print("OBS:", oid)
         if "meteor_frame_data" in obs:
            azs = [row[9] for row in obs['meteor_frame_data']]
            els = [row[10] for row in obs['meteor_frame_data']]
         else:
            azs = []
            els = []
         used_st[obs['station_id']]['azs'] = azs
         used_st[obs['station_id']]['els'] = els

         print("AS7 OBS FOUND")



      for st in ams_events[ams_event_id]['allsky7']['stations']:
         lat, lon, alt = ams_events[ams_event_id]['allsky7']['stations'][st]['location']
         point = {}
         point['lat'] = lat
         point['lon'] = lon 
         point['name'] = st
         point['text_position'] = "top right" 
         if st in used_st:
            point['symbol'] = 'square'
            point['opacity'] = 1
            #point['angle'] = used_st[st]['mean_az']
         else:
            point['symbol'] = "circle"
            point['opacity'] = .2
            #point['angle'] = 0
         points.append(point)
         texts.append(st)
      line = {}
      ams_event_data = ams_events[ams_event_id]
      line['lats'] = [ams_event_data['start_lat'],ams_event_data['end_lat']]
      line['lons'] = [ams_event_data['start_long'],ams_event_data['end_long']]
      line['name'] = "AMS WITNESS GROUND TRACK"
      lines.append(line)

      clat = float(ams_event_data['end_lat'])
      clon = float(ams_event_data['end_long'])
      zoom = 4

      

      map_fig2 = AA.create_map(title, points, lines, clat, clon, zoom)

      #exit()
      if len(ams_events[ams_event_id]['allsky7']['stations']) > 0 and as7_event is not None:
         ams_events[ams_event_id] = AA.populate_as7_data(ams_events[ams_event_id]) 
         #map_fig = AA.ams_as7_event_map(ams_events[ams_event_id])


         #map_fig2 = AA.create_map(points, lines, clat,clon, zoom=4)
         ams_as7_events.append((ams_event_id, as7_event, as7_obs))
      else:
         ams_events[ams_event_id] = AA.populate_as7_data(ams_events[ams_event_id]) 
         #map_fig2 = AA.create_map(points, lines, clat,clon, zoom=4)
         #map_fig = AA.ams_as7_event_map(ams_events[ams_event_id])
         ams_as7_nomatch_events.append((ams_event_id, as7_event, as7_obs))



      data['ams_events'] = ams_events
      data['ams_as7_events'] = ams_as7_events
      save_json_file(ams_as7_data_file, data)

   data['ams_events'] = ams_events
   data['ams_as7_events'] = ams_as7_events
   save_json_file(ams_as7_data_file, data)
   AA.ams_as7_report(data)


