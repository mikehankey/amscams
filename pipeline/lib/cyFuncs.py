from lib.PipeUtil import angularSeparation
import numpy as np
from lib.conversions import datetime2JD 
from lib.cyjd2LST import *
import math
J2000_DAYS = 2451545.0


def cyaltAz2RADec(azim, elev, jd, lat, lon):
    """ Convert azimuth and altitude in a given time and position on Earth to right ascension and 
        declination. 
    Arguments:
        azim: [float] Azimuth (+east of due north) in radians.
        elev: [float] Elevation above horizon in radians.
        jd: [float] Julian date.
        lat: [float] Latitude of the observer in radians.
        lon: [float] Longitde of the observer in radians.
    Return:
        (RA, dec): [tuple]
            RA: [float] Right ascension (radians).
            dec: [float] Declination (radians).
    """


    #cdef double lst, ha, ra, dec

    # Calculate Local Sidereal Time
    lst = math.radians(cyjd2LST(jd, math.degrees(lon)))
    
    # Calculate hour angle
    ha = math.atan2(-math.sin(azim), math.tan(elev)*math.cos(lat) - math.cos(azim)*math.sin(lat))
    
    # Calculate right ascension
    ra = (lst - ha + 2*math.pi)%(2*math.pi)

    # Calculate declination
    dec = math.asin(math.sin(lat)*math.sin(elev) + math.cos(lat)*math.cos(elev)*math.cos(azim))

    return (ra, dec)


def refractionTrueToApparent(elev):
    """ Correct the true elevation of a star for refraction to apparent elevation. The temperature and air
        pressure are assumed to be unknown. 
        Source: https://en.wikipedia.org/wiki/Atmospheric_refraction
    Arguments:
        elev: [float] Apparent elevation (radians).
    Return:
        [float] True elevation (radians).
    """

    #cdef double refraction

    # Don't apply refraction for elevation below -0.5 deg
    if elev > math.radians(-0.5):

        # Refraction in radians
        refraction = math.radians(1.02/(60*math.tan(math.radians(math.degrees(elev) + 10.3/(math.degrees(elev) + 5.11)))))

    else:
        refraction = 0.0

    # Apply the refraction
    return elev + refraction

def refractionApparentToTrue(elev):
    """ Correct the apparent elevation of a star for refraction to true elevation. The temperature and air
        pressure are assumed to be unknown.
        Source: Explanatory Supplement to the Astronomical Almanac (1992), p. 144.
    Arguments:
        elev: [float] Apparent elevation (radians).
    Return:
        [float] True elevation (radians).
    """

    #cdef double refraction

    # Don't apply refraction for elevation below -0.5 deg
    if elev > math.radians(-0.5):

        # Refraction in radians
        refraction = math.radians(1.0/(60*math.tan(math.radians(math.degrees(elev) + 7.31/(math.degrees(elev) + 4.4)))))

    else:
        refraction = 0.0

    # Correct the elevation
    return elev - refraction


def equatorialCoordPrecession(start_epoch, final_epoch, ra, \
    dec):
    """ Corrects Right Ascension and Declination from one epoch to another, taking only precession into 
        account.
        Implemented from: Jean Meeus - Astronomical Algorithms, 2nd edition, pages 134-135
    
    Arguments:
        start_epoch: [float] Julian date of the starting epoch.
        final_epoch: [float] Julian date of the final epoch.
        ra: [float] Input right ascension (radians).
        dec: [float] Input declination (radians).
    
    Return:
        (ra, dec): [tuple of floats] Precessed equatorial coordinates (radians).
    """

    #cdef double T, t, zeta, z, theta, A, B, C, ra_corr, dec_corr


    T = (start_epoch - J2000_DAYS )/36525.0
    t = (final_epoch - start_epoch)/36525.0

    # Calculate correction parameters in degrees
    zeta  = ((2306.2181 + 1.39656*T - 0.000139*T**2)*t + (0.30188 - 0.000344*T)*t**2 + 0.017998*t**3)/3600
    z     = ((2306.2181 + 1.39656*T - 0.000139*T**2)*t + (1.09468 + 0.000066*T)*t**2 + 0.018203*t**3)/3600
    theta = ((2004.3109 - 0.85330*T - 0.000217*T**2)*t - (0.42665 + 0.000217*T)*t**2 - 0.041833*t**3)/3600

    # Convert parameters to radians
    zeta  = math.radians(zeta)
    z     = math.radians(z)
    theta = math.radians(theta)

    # Calculate the next set of parameters
    A = math.cos(dec  )*math.sin(ra + zeta)
    B = math.cos(theta)*math.cos(dec)*math.cos(ra + zeta) - math.sin(theta)*math.sin(dec)
    C = math.sin(theta)*math.cos(dec)*math.cos(ra + zeta) + math.cos(theta)*math.sin(dec)

    # Calculate right ascension
    ra_corr = (math.atan2(A, B) + z + 2*math.pi)%(2*math.pi)

    # Calculate declination (apply a different equation if close to the pole, closer then 0.5 degrees)
    if (math.pi/2 - math.fabs(dec)) < math.radians(0.5):
        dec_corr = np.sign(dec)*math.acos(math.sqrt(A**2 + B**2))
    else:
        dec_corr = math.asin(C)


    return ra_corr, dec_corr



def eqRefractionTrueToApparent(ra, dec, jd, lat, lon):
    """ Correct the equatorial coordinates for refraction. The correction is done from true to apparent
        coordinates.
    
    Arguments:
        ra: [float] J2000 Right ascension in radians.
        dec: [float] J2000 Declination in radians.
        jd: [float] Julian date.
        lat: [float] Latitude in radians.
        lon: [float] Longitude in radians.
    Return:
        (ra, dec):
            - ra: [float] Apparent right ascension in radians.
            - dec: [float] Apparent declination in radians.
    """

    #cdef double azim, alt

    # Precess RA/Dec from J2000 to the epoch of date
    ra, dec = equatorialCoordPrecession(J2000_DAYS, jd, ra, dec)

    # Convert coordinates to alt/az
    azim, alt = cyraDec2AltAz(ra, dec, jd, lat, lon)

    # Correct the elevation
    alt = refractionTrueToApparent(alt)

    # Convert back to equatorial
    ra, dec = cyaltAz2RADec(azim, alt, jd, lat, lon)

    # Precess RA/Dec from the epoch of date to J2000
    ra, dec = equatorialCoordPrecession(jd, J2000_DAYS, ra, dec)


    return (ra, dec)


def cyjd2LST(jd, lon):
    """ Convert Julian date to apparent Local Sidereal Time. The times is apparent, not mean!
    Source: J. Meeus: Astronomical Algorithms
    Arguments:
        jd: [float] Decimal julian date, epoch J2000.0.
        lon: [float] Longitude of the observer in degrees.
    
    Return:
        lst [float] Apparent Local Sidereal Time (deg).
    """

    #cdef double gst

    t = (jd - J2000_DAYS)/36525.0

    # Calculate the Mean sidereal rotation of the Earth in radians (Greenwich Sidereal Time)
    gst = 280.46061837 + 360.98564736629*(jd - J2000_DAYS) + 0.000387933*t**2 - (t**3)/38710000.0
    gst = (gst + 360)%360


    # Compute the apparent Local Sidereal Time (LST)
    return (gst + lon + 360)%360


def cyraDecToXY(ra_data, \
    dec_data, jd, lat, lon, x_res, \
    y_res, h0, ra_ref, dec_ref, pos_angle_ref, pix_scale, \
    x_poly_rev, y_poly_rev, \
    dist_type, refraction=True, equal_aspect=False, force_distortion_centre=False):
    """ Convert RA, Dec to distorion corrected image coordinates. 
    Arguments:
        RA_data: [ndarray] Array of right ascensions (degrees).
        dec_data: [ndarray] Array of declinations (degrees).
        jd: [float] Julian date.
        lat: [float] Latitude of station in degrees.
        lon: [float] Longitude of station in degrees.
        x_res: [int] X resolution of the camera.
        y_res: [int] Y resolution of the camera.
        h0: [float] Reference hour angle (deg).
        ra_ref: [float] Reference right ascension of the image centre (degrees).
        dec_ref: [float] Reference declination of the image centre (degrees).
        pos_angle_ref: [float] Rotation from the celestial meridial (degrees).
        pix_scale: [float] Image scale (px/deg).
        x_poly_rev: [ndarray float] Distortion polynomial in X direction for reverse mapmath.ping.
        y_poly_rev: [ndarray float] Distortion polynomail in Y direction for reverse mapmath.ping.
        dist_type: [str] Distortion type. Can be: poly3+radial, radial3, radial4, or radial5.
        
    Keyword arguments:
        refraction: [bool] Apply refraction correction. True by default.
        equal_aspect: [bool] Force the X/Y aspect ratio to be equal. Used only for radial distortion. \
            False by default.
        force_distortion_centre: [bool] Force the distortion centre to the image centre. False by default.
    
    Return:
        (x, y): [tuple of ndarrays] Image X and Y coordinates.
    """

    #cdef int i
    #cdef double ra_centre, dec_centre, ra, dec
    #cdef double radius, math.sin_ang, math.cos_ang, theta, x, y, r, dx, dy, x_img, y_img, r_corr, r_scale
    #cdef double x0, y0, xy, k1, k2, k3, k4

    # Init output arrays
    #cdef np.ndarray[FLOAT_TYPE_t, ndim=1] 
    x_array = np.zeros_like(ra_data)
    y_array = np.zeros_like(ra_data)
    #cdef np.ndarray[FLOAT_TYPE_t, ndim=1] 

    # Precalculate some parameters
    #cdef double sl = math.sin(radians(lat))
    #cdef double cl = math.cos(radians(lat))


    # Compute the current RA of the FOV centre by adding the difference in between the current and the 
    #   reference hour angle
    ra_centre = math.radians((ra_ref + cyjd2LST(jd, 0) - h0 + 360)%360)
    dec_centre = math.radians(dec_ref)

    # Correct the reference FOV centre for refraction
    if refraction:
        ra_centre, dec_centre = eqRefractionTrueToApparent(float(ra_centre), float(dec_centre), jd, math.radians(float(lat)), \
            math.radians(float(lon)))


    # If the radial distortion is used, unpack radial parameters
    if dist_type.startswith("radial"):


        # Force the distortion centre to the image centre
        if force_distortion_centre:
            x0 = 0.5
            y0 = 0.5
        else:
            # Read distortion offsets
            x0 = x_poly_rev[0]
            y0 = x_poly_rev[1]


        # Aspect ratio
        if equal_aspect:
            xy = 0.0
        else:
            xy = x_poly_rev[2]


        # Distortion coeffs
        k1 = x_poly_rev[3]
        k2 = x_poly_rev[4]
        k3 = x_poly_rev[5]
        k4 = x_poly_rev[6]

    # If the polynomial distortion was used, unpack the offsets
    else:
        x0 = x_poly_rev[0]
        y0 = y_poly_rev[0]


    # Convert all equatorial coordinates to image coordinates
    for i in range(ra_data.shape[0]):

        ra = math.radians(ra_data[i])
        dec = math.radians(dec_data[i])

        ### Gnomonization of star coordinates to image coordinates ###

        # Apply refraction
        if refraction:
            ra, dec = eqRefractionTrueToApparent(ra, dec, jd, math.radians(float(lat)), math.radians(float(lon)))


        # Compute the distance from the FOV centre to the sky coordinate
        radius = math.radians(angularSeparation(math.degrees(ra), math.degrees(dec), math.degrees(ra_centre), \
            math.degrees(dec_centre)))

        # Compute theta - the direction angle between the FOV centre, sky coordinate, and the image vertical
        math.sin_ang = math.cos(dec)*math.sin(ra - ra_centre)/math.sin(radius)
        math.cos_ang = (math.sin(dec) - math.sin(dec_centre)*math.cos(radius))/(math.cos(dec_centre)*math.sin(radius))
        theta   = -math.atan2(math.sin_ang, math.cos_ang) + math.radians(pos_angle_ref) - math.pi/2.0

        # Calculate the standard coordinates
        x = math.degrees(radius)*math.cos(theta)*pix_scale
        y = math.degrees(radius)*math.sin(theta)*pix_scale

        ### ###

        # Set initial distorsion values
        dx = 0
        dy = 0

        # Apply 3rd order polynomial + one radial term distortion
        if dist_type == "poly3+radial":

            # Compute the radius
            r = math.sqrt((x - x0)**2 + (y - y0)**2)

            # Calculate the distortion in X direction
            dx = (x0
                + x_poly_rev[1]*x
                + x_poly_rev[2]*y
                + x_poly_rev[3]*x**2
                + x_poly_rev[4]*x*y
                + x_poly_rev[5]*y**2
                + x_poly_rev[6]*x**3
                + x_poly_rev[7]*x**2*y
                + x_poly_rev[8]*x*y**2
                + x_poly_rev[9]*y**3
                + x_poly_rev[10]*x*r
                + x_poly_rev[11]*y*r)

            # Calculate the distortion in Y direction
            dy = (y0
                + y_poly_rev[1]*x
                + y_poly_rev[2]*y
                + y_poly_rev[3]*x**2
                + y_poly_rev[4]*x*y
                + y_poly_rev[5]*y**2
                + y_poly_rev[6]*x**3
                + y_poly_rev[7]*x**2*y
                + y_poly_rev[8]*x*y**2
                + y_poly_rev[9]*y**3
                + y_poly_rev[10]*y*r
                + y_poly_rev[11]*x*r)


        # Apply a radial distortion
        elif dist_type.startswith("radial"):

            # Compute the normalized radius to horizontal size
            r = math.sqrt(x**2 + y**2)/(x_res/2.0)
            r_corr = r

            # Apply the 3rd order radial distortion
            if dist_type == "radial3":

                # Compute the new radius
                r_corr = (1.0 - k1 - k2)*r + k1*r**2 - k2*r**3

            # Apply the 4th order radial distortion
            elif dist_type == "radial4":

                # Compute the new radius
                r_corr = (1.0 - k1 - k2 - k3)*r + k1*r**2 - k2*r**3 + k3*r**4


            # Apply the 5th order radial distortion
            elif dist_type == "radial5":

                # Compute the new radius
                r_corr = (1.0 - k1 - k2 - k3 - k4)*r + k1*r**2 - k2*r**3 + k3*r**4 - k4*r**5


            # Compute the scaling term
            if r == 0:
                r_scale = 0
            else:
                r_scale = (r_corr/r - 1)

            # Compute distortion offsets
            dx = (x - x0)*r_scale
            dy = (y - y0)*r_scale/(1.0 + xy)



        # Add the distortion
        x_img = x - dx
        y_img = y - dy


        # Calculate X image coordinates
        x_array[i] = x_img + x_res/2.0

        # Calculate Y image coordinates
        y_array[i] = y_img + y_res/2.0


    return x_array, y_array

def cyraDec2AltAz(ra, dec, jd, lat, lon):
    """ Convert right ascension and declination to azimuth (+East of due North) and altitude. Same epoch is
        assumed, no correction for refraction is done.
    Arguments:
        ra: [float] Right ascension in radians.
        dec: [float] Declination in radians.
        jd: [float] Julian date.
        lat: [float] Latitude in radians.
        lon: [float] Longitude in radians.
    Return:
        (azim, elev): [tuple]
            azim: [float] Azimuth (+east of due north) in radians.
            elev: [float] Elevation above horizon in radians.
        """

    #cdef double lst, ha, azim, sin_elev, elev

    # Calculate Local Sidereal Time
    lst = math.radians(cyjd2LST(jd, math.degrees(lon)))

    # Calculate the hour angle
    ha = lst - ra

    # Constrain the hour angle to [-pi, pi] range
    ha = (ha + math.pi)%(2*math.pi) - math.pi

    # Calculate the azimuth
    azim = math.pi + math.atan2(math.sin(ha), math.cos(ha)*math.sin(lat) - math.tan(dec)*math.cos(lat))

    # Calculate the sine of elevation
    sin_elev = math.sin(lat)*math.sin(dec) + math.cos(lat)*math.cos(dec)*math.cos(ha)

    # Wrap the sine of elevation in the [-1, +1] range
    sin_elev = (sin_elev + 1)%2 - 1

    elev = math.asin(sin_elev)

    return (azim, elev)
