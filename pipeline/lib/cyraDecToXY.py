
from lib.conversions import datetime2JD 
from lib.cyjd2LST import *
import math
from lib.PipeUtil import angularSeparation

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
        x_poly_rev: [ndarray float] Distortion polynomial in X direction for reverse mapping.
        y_poly_rev: [ndarray float] Distortion polynomail in Y direction for reverse mapping.
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
    #cdef double radius, sin_ang, cos_ang, theta, x, y, r, dx, dy, x_img, y_img, r_corr, r_scale
    #cdef double x0, y0, xy, k1, k2, k3, k4

    # Init output arrays
    #cdef np.ndarray[FLOAT_TYPE_t, ndim=1] x_array = np.zeros_like(ra_data)
    #cdef np.ndarray[FLOAT_TYPE_t, ndim=1] y_array = np.zeros_like(ra_data)

    # Precalculate some parameters
    #cdef double sl = sin(radians(lat))
    #cdef double cl = cos(radians(lat))


    # Compute the current RA of the FOV centre by adding the difference in between the current and the 
    #   reference hour angle
    ra_centre = math.radians((ra_ref + cyjd2LST(jd, 0) - h0 + 360)%360)
    dec_centre = math.radians(dec_ref)

    # Correct the reference FOV centre for refraction
    if refraction:
        ra_centre, dec_centre = eqRefractionTrueToApparent(ra_centre, dec_centre, jd, radians(lat), \
            radians(lon))


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

        ra = radians(ra_data[i])
        dec = radians(dec_data[i])

        ### Gnomonization of star coordinates to image coordinates ###

        # Apply refraction
        if refraction:
            ra, dec = eqRefractionTrueToApparent(ra, dec, jd, radians(lat), radians(lon))


        # Compute the distance from the FOV centre to the sky coordinate
        radius = radians(angularSeparation(degrees(ra), degrees(dec), degrees(ra_centre), \
            degrees(dec_centre)))

        # Compute theta - the direction angle between the FOV centre, sky coordinate, and the image vertical
        sin_ang = cos(dec)*sin(ra - ra_centre)/sin(radius)
        cos_ang = (sin(dec) - sin(dec_centre)*cos(radius))/(cos(dec_centre)*sin(radius))
        theta   = -atan2(sin_ang, cos_ang) + radians(pos_angle_ref) - pi/2.0

        # Calculate the standard coordinates
        x = degrees(radius)*cos(theta)*pix_scale
        y = degrees(radius)*sin(theta)*pix_scale

        ### ###

        # Set initial distorsion values
        dx = 0
        dy = 0

        # Apply 3rd order polynomial + one radial term distortion
        if dist_type == "poly3+radial":

            # Compute the radius
            r = sqrt((x - x0)**2 + (y - y0)**2)

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
            r = sqrt(x**2 + y**2)/(x_res/2.0)
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

