import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import sys
import json
import pandas as pd
import numpy as np

def load_json_file(json_file):
   with open(json_file, 'r' ) as infile:
      json_data = json.load(infile)
   return json_data

date = sys.argv[1]

data_file = "/mnt/f/EVENTS/DAYS/{:s}_PLOTS_ALL_RADIANTS.json".format(date)
data = load_json_file(data_file)
rad_df = pd.read_json(data_file)

for row in data:
   print(row)
print(data_file)

# Sample data: replace this with your radiant positions.
longitudes = data['x']
latitudes = data['y'] 
latitudes = [-x for x in latitudes]
sizes = [1 for x in latitudes]

fig, ax = plt.subplots(subplot_kw={'projection': ccrs.Sinusoidal(central_longitude=270)})
ax.scatter(longitudes, latitudes, s=sizes, transform=ccrs.PlateCarree(), color='red' )


# Draw gridlines at 15-degree intervals
gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=False, linewidth=0.5, color='gray', alpha=0.5, linestyle='--', xlocs=np.arange(0, 361, 15), ylocs=np.arange(-90, 91, 15))

# Manually define the tick labels based on your desired order
long_ticks = [90, 60, 30, 0, 330, 300, 270, 240, 210, 180, 150, 120, 90]
long_positions = [-180, -150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150, 180]

for tick, position in zip(long_ticks, long_positions):
    ax.text(position, 0, str(tick)+'°', va='bottom', ha='center', transform=ccrs.PlateCarree(), color='gray')

# Add latitude tick labels in the center
yticks = np.arange(-90, 91, 30)
for ytick in yticks:
    ax.text(0, ytick, str(ytick)+'°', va='bottom', ha='center', transform=ccrs.PlateCarree(), color='gray')




# Set the extent to cover the whole globe
ax.set_global()
print(rad_df)
plt.show()

