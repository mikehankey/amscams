from astropy.coordinates import EarthLocation, AltAz, get_sun, get_moon, SkyCoord
from astropy import units as u
from matplotlib.patches import Circle
import matplotlib.pyplot as plt
import numpy as np

# Define observer's location (latitude, longitude)
latitude = 0 * u.deg
longitude = 0 * u.deg
observer_location = EarthLocation(lat=latitude, lon=longitude, height=0)

# Create AltAz frame for the observer's location
observer_frame = AltAz(location=observer_location, obstime="2023-08-15T00:00:00")

# Create an array of azimuth and altitude angles
az_array = np.linspace(0, 360, 361) * u.deg
alt_array = np.linspace(-90, 90, 181) * u.deg

# Create a grid of azimuth and altitude angles
az_grid, alt_grid = np.meshgrid(az_array, alt_array)

# Convert grid to SkyCoord object in AltAz frame
grid_coords = SkyCoord(az=az_grid, alt=alt_grid, frame=observer_frame)

# Calculate separation angles to the Sun and Moon
sun_coords = get_sun(grid_coords.obstime)
moon_coords = get_moon(grid_coords.obstime, observer_location)
sun_sep = grid_coords.separation(sun_coords)
moon_sep = grid_coords.separation(moon_coords)

# Determine which points are below the horizon, not too close to Sun/Moon, and brighter than magnitude 0
visible_points = (grid_coords.alt > 0 * u.deg) & (sun_sep > 10 * u.deg) & (moon_sep > 10 * u.deg)

# Create a figure and axis for the star map
fig, ax = plt.subplots(figsize=(10, 6), subplot_kw={'projection': 'polar'})
ax.set_theta_zero_location("N")
ax.set_theta_direction(-1)
ax.set_rlim(0, 90)
ax.set_yticklabels([])

# Plot visible stars as circles
circle_radius = 90 - grid_coords.alt[visible_points].value
circle_azimuth = grid_coords.az[visible_points].to_value(u.deg)
for radius, azimuth in zip(circle_radius, circle_azimuth):
    circle = Circle((np.radians(azimuth), radius), 0.5 * u.deg.value, fill=False, color='black', alpha=0.5)
    ax.add_patch(circle)

plt.title("Star Map - All Stars Brighter than Magnitude 0")
plt.show()

