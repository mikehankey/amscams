import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import numpy as np

def transform_longitude(lon):
    return lon - 360 if lon > 90 else lon

# Sample data
longitudes = [10, 20, 30, 40, 50]
latitudes = [5, 15, -10, -15, 0]

# Transform the longitudes
longitudes_transformed = [transform_longitude(lon) for lon in longitudes]

fig, ax = plt.subplots(subplot_kw={'projection': ccrs.Sinusoidal(central_longitude=270)})
ax.scatter(longitudes_transformed, latitudes, transform=ccrs.PlateCarree(), color='red')

# Draw gridlines at 15-degree intervals
gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=False, linewidth=0.5, color='gray', alpha=0.5, linestyle='--', xlocs=np.arange(-180, 181, 15), ylocs=np.arange(-90, 91, 15))

# Manually define the tick labels based on your desired order
long_ticks = [90, 60, 30, 0, 330, 300, 270, 240, 210, 180, 150, 120, 90]
long_positions = [-180, -150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150, 180]

for tick, position in zip(long_ticks, long_positions):
    ax.text(position, 0, str(tick)+'°', va='bottom', ha='center', transform=ccrs.PlateCarree(), color='gray')

# Add latitude tick labels in the center
yticks = np.arange(-90, 91, 30)
for ytick in yticks:
    ax.text(0, ytick, str(ytick)+'°', va='bottom', ha='center', transform=ccrs.PlateCarree(), color='gray')

ax.set_global()
plt.show()

