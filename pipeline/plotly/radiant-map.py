import matplotlib.pyplot as plt
import os
import cartopy.crs as ccrs
import sys
import json
import pandas as pd
import numpy as np
import datetime

from skyfield.api import load, Topos
from skyfield.timelib import Time



def transform_longitude(lon):
    #return lon - 360 if lon > 90 else lon
    return(lon)

def load_json_file(json_file):
   with open(json_file, 'r' ) as infile:
      json_data = json.load(infile)
   return json_data

def get_event_day_dir(date_str):
    if len(date_str) != 8:
        raise ValueError("Invalid date format. Expected format: YYYYMMDD.")
    
    event_dir = "/mnt/f/EVENTS/" + date_str[:4] + "/" + date_str[4:6] + "/" + date_str[6:] + "/"
    date_str2 = date_str[:4] + "_" + date_str[4:6] + "_" + date_str[6:] + "_"
    event_file = event_dir + date_str2 + "ALL_EVENTS.json"
    if os.path.exists(event_file) is False:
       event_file = None
    print(event_dir, event_file)
    return(event_dir, event_file)



date = sys.argv[1]

#data_file = "/mnt/f/EVENTS/DAYS/{:s}_PLOTS_ALL_RADIANTS.json".format(date)
#data = load_json_file(data_file)
#rad_df = pd.read_json(data_file)

event_dir, event_file = get_event_day_dir(date)
longitudes = []
latitudes = []
showers = []
if event_file is not None:
   events_data = load_json_file(event_file)
   for ev in events_data:
      if "shower" in ev:
         shower = ev['shower']['shower_code']
      else:
         shower = ""
      if "rad" in ev:
         
          if ev['rad']['ecliptic_helio']['L_h'] is not None and ev['rad']['ecliptic_helio']['B_h'] is not None:
             #print(ev['rad']['ecliptic_helio'])
             lon = np.degrees(ev['rad']['ecliptic_helio']['L_h'])
             lat = np.degrees(ev['rad']['ecliptic_helio']['B_h'])
             print(shower, lat, lon)
             latitudes.append(lat)
             longitudes.append(lon)
             showers.append(shower)


# Sample data: replace this with your radiant positions.
sizes = [1 for x in latitudes]

# Transform the longitudes

# Create the Sinusoidal projection with central_longitude set to 0
fig_width = 800 / 72  # 800 pixels at 72 DPI
fig_height = 600 / 72  # 600 pixels at 72 DPI

fig, ax = plt.subplots(figsize=(fig_width, fig_height), subplot_kw={'projection': ccrs.Sinusoidal(central_longitude=0)})
ax.set_global()
ax.scatter(longitudes, latitudes, s=sizes, transform=ccrs.PlateCarree(), color='red')


# Manually add gridlines at 15° intervals
for x in np.arange(0, 361, 15):
    ax.plot([x, x], [-90, 90], transform=ccrs.PlateCarree(), linestyle='--', alpha=0.5, color='gray' )
for y in np.arange(-90, 91, 15):
    ax.plot([0, 360], [y, y], transform=ccrs.PlateCarree(), linestyle='--', color='gray', alpha=0.5 )

# Add tick labels at 30° intervals manually for latitude
for y in np.arange(-90, 91, 30):
    if y != 0:
        ax.annotate(str(y) + '°', xy=(0, y), xycoords=ccrs.PlateCarree()._as_mpl_transform(ax),
                    va='center', ha='center' )

# Add tick labels for longitude in the middle
for x in np.arange(-180, 181, 30):
    ax.annotate(str(x) + '°', xy=(x, 0), xycoords=ccrs.PlateCarree()._as_mpl_transform(ax),
                ha='center', va='center' )


plt.show()
