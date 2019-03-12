"""Prints the heliocentric state vector of the earth using SpiceyPy (SPICE).
"""
from __future__ import print_function  # Needed for Python 2 compatibility
import sys
import spiceypy as sp

# These data files were obtained from
# http://naif.jpl.nasa.gov/pub/naif/generic_kernels
LEAP_SECOND_FILE = "/home/ams/amscams/pythonv2/data/naif0011.tls"
EPHEMERIDES_FILE = "/home/ams/amscams/pythonv2/data/de432s.bsp"

def earth_position(input_utc):
    sp.furnsh([LEAP_SECOND_FILE, EPHEMERIDES_FILE])
    # Convert UTC to ephemeris time

    epoch = sp.utc2et(input_utc)
    # State (position and velocity in cartesian coordinates)
    # of EARTH as seen from SUN in the ecliptic J2000 coordinate frame.
    state, lt, = sp.spkezr("EARTH", epoch, "ECLIPJ2000", "NONE", "SUN")
    # Show the output
    ex = float(state[0])/ 149597870.700 
    ey = float(state[1])/149597870.700 
    ez = float(state[2])/149597870.700 
    evx = (float(state[3])*86400)/149597870.700 
    evy = (float(state[4])*86400)/149597870.700 
    evz = (float(state[5])*86400)/149597870.700 
    # As a sanity check, print the speed
    evl = (state[3]**2 + state[4]**2 + state[5]**2)**.5
    #print("# Orbital speed [sqrt(dX^2 + dY^2 + dZ^2)]")
    #print("Speed = {} km/s".format(float(speed)))
    return(ex,ey,ez,evx,evy,evz,evl)


