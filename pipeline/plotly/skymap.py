from astropy.coordinates import SkyCoord, AltAz, EarthLocation
from astropy import units as u
import matplotlib.pyplot as plt

# Define a position on Earth (latitude, longitude)
latitude = 40 * u.deg
longitude = -75 * u.deg

# Example star coordinates (Right Ascension and Declination)
star_ra = [30, 45, 60] * u.deg
star_dec = [20, 30, 40] * u.deg

# Create a SkyCoord object for star positions
star_positions = SkyCoord(ra=star_ra, dec=star_dec, frame='icrs')

# Create an EarthLocation for the observer's location
observer_location = EarthLocation(lat=latitude, lon=longitude, height=0)

# Create an AltAz frame for the observer's location
observer_frame = AltAz(location=observer_location, obstime="2023-08-15T00:00:00")

# Convert star positions to Altitude-Azimuth coordinates for plotting
star_altaz = star_positions.transform_to(observer_frame)

# Plot the star map
plt.scatter(star_altaz.az, star_altaz.alt)
plt.xlabel('Azimuth (degrees)')
plt.ylabel('Altitude (degrees)')
plt.title('Star Map')
plt.grid()
plt.show()

