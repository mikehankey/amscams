//#########################################################################################
//  A set of geometric and vector arithmetic functions plus coordinate conversions
//
//  ---------------------------------------------------------------------------------------
//  Ver   Date        Author       Description
//  ----  ----------  -----------  ---------------------------------------------------------
//  1.00  2018-04-19  Gural        Original implementation
//
//#########################################################################################


//=========================================================================================
//========   Structure and function prototypes for pre-detection image processing  ========
//=========================================================================================

void    UnitVector(double *a, double *b, double *c);

double  DotProduct(double *a, double *b);

void    CrossProduct(double *a, double *b, double *c);

void    ScaleVector(double a, double *b, double *c);

void    SumVector(double *a, double *b, double *c);

void    DifferenceVector(double *a, double *b, double *c);

void    ScaleAndSumVectors(double a, double *b, double c, double *d, double *e);

//-----------------------------------------------------------------------------------------

void     RADec_to_AzimElev( double  RA,        //... all angles in radians
	                        double  DEC,
	                        double  latitude,  //... geodetic
	                        double  LST,
	                        double *Azim,      //... measured around east of due north
	                        double *Elev );    //... angle above horizon


void     AzimElev_to_RADec( double  azim,      //... measured around east of due north
	                        double  elev,      //... angle above horizon
	                        double  latitude,  //... geodetic
	                        double  LST,
	                        double *RA,
	                        double *DEC );     //... ALL angles in radians
void     RADec_to_Standard( double  RA,          //... RA/DEC in radians
	                        double  DEC,
	                        double  RAcenter, 
	                        double  DECcenter,
	                        double *Xstandard,   
	                        double *Ystandard ); 

void     Standard_to_RADec( double  Xstandard,      
	                        double  Ystandard,
	                        double  RAcenter,     //... RA/DEC in radians
	                        double  DECcenter,
	                        double *RA,   
	                        double *DEC ); 

void             RADec2xyz( double  RA, 
	                        double  DEC, 
	                        double  rmag, 
	                        double *v );

void             xyz2RADec( double *v, 
	                        double *RA, 
	                        double *DEC, 
	                        double *rmag );


void        RADec_to_SAZZA( int      nstars, 
	                        double  *RA, 
	                        double  *DEC,
	                        double   latitude, 
	                        double   LST,
	                        double  *SAZ, 
	                        double  *ZA );

void        SAZZA_to_RADec( int      nstars, 
	                        double  *SAZ, 
	                        double  *ZA,
	                        double   latitude, 
	                        double   LST,
	                        double  *RA, 
	                        double  *DEC );

void   SAZZA_to_Tangential( double  SAZ,          //... SAZ and ZA in radians
	                        double  ZA,
	                        double  SAZcenter, 
	                        double  ZAcenter,
	                        double *Hstandard,   
	                        double *Vstandard ); 

void   Tangential_to_SAZZA( double  Hstandard,
	                        double  Vstandard,
	                        double  SAZcenter,     //... SAZ and ZA in radians
	                        double  ZAcenter,
	                        double *SAZ,
	                        double *ZA);

//-----------------------------------------------------------------------------------------

double  SphericalAngularDistance_RADec(double ra1, double dec1, double ra2, double dec2);

double  SphericalAngularDistance_SAZZA(double SAZ1, double ZA1, double SAZ2, double ZA2);

void    LLA_to_ECEF(double lat_deg, double eastlon_deg, double alt_km, double *x_km, double *y_km, double *z_km);

void    ECEF_to_LLA(double x_km, double y_km, double z_km, double *lat_deg, double *eastlon_deg, double *alt_km);

void    ComputeHoughParameters( int nrows, double rowstart, double rowspeed,
	                            int ncols, double colstart, double colspeed,
	                            double *rho, double *phideg, double *deltad );


//#########################################################################################

//=========================================================================================
//                  3-Vector Arithmetic Functions
//=========================================================================================

void  UnitVector(double *a, double *b, double *c)
{
	*c = sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]);
	if (*c != 0) {
		b[0] = a[0] / *c;
		b[1] = a[1] / *c;
		b[2] = a[2] / *c;
	}
}

//.........................................................................................

double  DotProduct(double *a, double *b)
{
	double c = a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
	return(c);
}

//.........................................................................................

void  CrossProduct(double *a, double *b, double *c)
{
	c[0] = a[1] * b[2] - a[2] * b[1];
	c[1] = a[2] * b[0] - a[0] * b[2];
	c[2] = a[0] * b[1] - a[1] * b[0];
}

//.........................................................................................

void  ScaleVector(double a, double *b, double *c)
{
	c[0] = a * b[0];
	c[1] = a * b[1];
	c[2] = a * b[2];
}

//.........................................................................................

void  SumVector(double *a, double *b, double *c)
{
	c[0] = a[0] + b[0];
	c[1] = a[1] + b[1];
	c[2] = a[2] + b[2];
}

//.........................................................................................

void  DifferenceVector(double *a, double *b, double *c)
{
	c[0] = a[0] - b[0];
	c[1] = a[1] - b[1];
	c[2] = a[2] - b[2];
}

//.........................................................................................

void  ScaleAndSumVectors(double a, double *b, double c, double *d, double *e)
{
	e[0] = a * b[0] + c * d[0];
	e[1] = a * b[1] + c * d[1];
	e[2] = a * b[2] + c * d[2];
}


//=========================================================================================
//          Convert RA and DEC to Azimuth and Elevation - All angles in radians
//=========================================================================================

void     RADec_to_AzimElev( double  RA,        //... right ascension
	                        double  DEC,       //... declination
	                        double  latitude,  //... geodetic latitude
	                        double  LST,       //... local sidereal time
	                        double *Azim,      //... returns angle around east from due north
	                        double *Elev  )    //... returns angle above horizon
{
	double hourangle, sinelev, sinlat, coslat, pi;


	pi = 4.0 * atan(1.0);

	sinlat = sin(latitude);
	coslat = cos(latitude);

	hourangle = LST - RA;

	while (hourangle < -pi)  hourangle += 2.0*pi;
	while (hourangle > +pi)  hourangle -= 2.0*pi;

	*Azim = pi + atan2(sin(hourangle),
		cos(hourangle) * sinlat
		- tan(DEC) * coslat);

	while (*Azim <  0.0     )  *Azim += 2.0*pi;
	while (*Azim >= 2.0 * pi)  *Azim -= 2.0*pi;

	sinelev = sinlat * sin(DEC)
		+ coslat * cos(DEC) * cos(hourangle);

	if (sinelev > +1.0)  sinelev = +1.0;
	if (sinelev < -1.0)  sinelev = -1.0;

	*Elev = asin(sinelev);

}


//=========================================================================================
//           Convert Azimuth and Elevation to RA and DEC - All angles in radians
//=========================================================================================

void     AzimElev_to_RADec( double  azim,      //... measured around east from due north
	                        double  elev,      //... angle above the horizon
	                        double  latitude,  //... geodetic latitude
	                        double  LST,       //... local sidereal time
	                        double *RA,        //... returns right ascension
	                        double *DEC)       //... returns declination
{
	double hourangle, sinlat, coslat;

	// Note formulae signs assume azim measured +east of north

	sinlat = sin(latitude);
	coslat = cos(latitude);

	*DEC = asin(sinlat * sin(elev)
		+ coslat * cos(elev) * cos(azim));

	hourangle = atan2(-sin(azim),
		tan(elev)*coslat - cos(azim)*sinlat);

	*RA = LST - hourangle;

	while (*RA < 0.0              )  *RA += 2.0 * 3.14159265359;
	while (*RA > 2.0 * 3.141592654)  *RA -= 2.0 * 3.14159265359;

}

//=========================================================================================
//        Convert RA/Dec to equatorial cartesian coordinates - All angles in radians
//=========================================================================================

void  RADec2xyz(double RA, double DEC, double rmag, double *v)
{
	v[0] = rmag * cos(DEC) * cos(RA);
	v[1] = rmag * cos(DEC) * sin(RA);
	v[2] = rmag * sin(DEC);
}


//=========================================================================================
//       Convert equatorial cartesian coordinates to RA/Dec - All angles in radians
//=========================================================================================

void  xyz2RADec(double *v, double *RA, double *DEC, double *rmag)
{
	double u[3];

	UnitVector(v, u, rmag);

	*RA = atan2(u[1], u[0]);
	*DEC = asin(u[2]);

	if (*RA < 0.0)  *RA += 8.0 * atan(1.0);  //...add 2pi

}


//=========================================================================================
//      Convert RA and DEC to Standard "Gnomonic" Coordinates such that Xstd is parallel
//      to RA lines and Ystd is parallel to DEC lines. - All angles in radians
//=========================================================================================

void     RADec_to_Standard( double   RA,          //... right ascension
	                        double   DEC,         //... declination
	                        double   RAcenter,    //... RA of center
	                        double   DECcenter,   //... DEC of center
	                        double  *Xstandard,   //... returns X standard
	                        double  *Ystandard)   //... returns Y standard
{
	double q, RAdelta, cosine, pi;

	pi = 4.0 * atan(1.0);

	RAdelta = RA - RAcenter;

	cosine = cos(RAdelta);

	if (cosine != 0.0)  q = atan(tan(DEC) / cosine);
	else                q = pi / 2.0;

	cosine = cos(q - DECcenter);

	if (cosine != 0.0) {
		*Xstandard = -tan(RAdelta) * cos(q) / cosine;
		*Ystandard = +tan(q - DECcenter);
	}
	else {
		*Xstandard = 1.0e+30;
		*Ystandard = 1.0e+30;
	}

}

//=========================================================================================
//      Convert Standard "Gnomonic" Coordinates to RA and DEC such that Xstd is parallel 
//      to RA lines and Ystd is parallel to DEC lines. - All angles in radians
//=========================================================================================

void     Standard_to_RADec( double   Xstandard,     //... X standard coordinate
	                        double   Ystandard,     //... Y standard coordiante
	                        double   RAcenter,      //... right ascension of projection center
	                        double   DECcenter,     //... declination of projection center
	                        double  *RA,            //... returns right ascension
	                        double  *DEC)           //... returns declination
{
	double sindec, cosdec, pi;

	pi = 4.0 * atan(1.0);

	sindec = sin(DECcenter);
	cosdec = cos(DECcenter);

	*DEC = asin((sindec + Ystandard * cosdec) / sqrt(1.0 + Xstandard*Xstandard + Ystandard*Ystandard));

	*RA = RAcenter - atan2(Xstandard, cosdec - Ystandard * sindec);

	while (*RA < 0.0     )  *RA += 2.0 * pi;
	while (*RA > 2.0 * pi)  *RA -= 2.0 * pi;

}


//=========================================================================================
//      Convert a vector of star RA/Dec equatorial coordinates to aziumth west of south 
//      and zenith angle. All angles in radians.
//=========================================================================================

void  RADec_to_SAZZA( int     nstars,   //... number of equatorial coordinate pairs to convert
	                  double *RA,       //... vector of right ascensions
	                  double *DEC,      //... vector of declinations
	                  double  latitude, //... geodetic latitude
	                  double  LST,      //... local sidereal time
	                  double *SAZ,      //... azimuth measured around west of due south
	                  double *ZA)       //... zenith angle measured from directly overhead
{
	int     kstar;
	double  azim, elev, pi;


	pi = 4.0 * atan(1.0);

	for (kstar = 0; kstar < nstars; kstar++) {

		RADec_to_AzimElev(RA[kstar], DEC[kstar], latitude, LST, &azim, &elev);

		SAZ[kstar] = pi + azim;  //... want azimuth to be west of due south

		while (SAZ[kstar] <  0.0)  SAZ[kstar] += 2.0*pi;
		while (SAZ[kstar] >= 2.0 * pi)  SAZ[kstar] -= 2.0*pi;

		ZA[kstar] = pi / 2.0 - elev;

	}

}


//=========================================================================================
//      Convert a vector of aziumths west of south and zenith angles to equatorial RA
//      and DEC. All angles in radians.
//=========================================================================================

void  SAZZA_to_RADec( int     nstars,   //... number of equatorial coordinate pairs to convert
	                  double *SAZ,      //... azimuth measured around west of due south
	                  double *ZA,       //... zenith angle measured from directly overhead
	                  double  latitude, //... geodetic latitude
	                  double  LST,      //... local sidereal time
	                  double *RA,       //... vector of right ascensions
	                  double *DEC)      //... vector of declinations
{
	int     kstar;
	double  azim, elev, pi;


	pi = 4.0 * atan(1.0);

	for (kstar = 0; kstar < nstars; kstar++) {

		azim = SAZ[kstar] - pi;  //... want azimuth east of due north

		elev = pi / 2.0 - ZA[kstar];

		AzimElev_to_RADec(azim, elev, latitude, LST, &RA[kstar], &DEC[kstar]);

		while (RA[kstar] <  0.0)  RA[kstar] += 2.0*pi;
		while (RA[kstar] >= 2.0 * pi)  RA[kstar] -= 2.0*pi;

	}

}


//=========================================================================================
//          Convert south azimuth and zenith angle to Tangential "Gnomonic" coordinates
//          where Vstd is parallel to the local vertical viewing direction and Hstd
//          is parallel to the local horizontal. This differs from RADec_to_Standard
//          where Xstd is parallel to RA lines and Ystd is parallel to DEC lines.
//          All angles in radians.
//=========================================================================================

void    SAZZA_to_Tangential( double   SAZ,        //... aziumth measured west of due south
	                         double   ZA,         //... zenith angle
	                         double   SAZ_center, //... SAZ of reference center
	                         double   ZA_center,  //... ZA of reference center
	                         double  *Hstandard,  //... returns horizontal standard coordinate
	                         double  *Vstandard)  //... returns vertical standard coordinate
{
	double  pi;


	pi = 4.0 * atan(1.0);

	RADec_to_Standard(-SAZ, pi / 2.0 - ZA, -SAZ_center, pi / 2.0 - ZA_center, Hstandard, Vstandard);

}

//=========================================================================================
//       Convert Tangential "Gnomonic" coordinates Hstd and Vstd, which are parallel 
//       to the local horizontal and vertical viewing directions respectively, to 
//       +west of due south azimuth "SAZ and zenith angle "ZA". 
//=========================================================================================

void     Tangential_to_SAZZA( double   Hstandard,  //... horizontal standard coordinate
	                          double   Vstandard,  //... vertical standard coordinate
	                          double   SAZ_center, //... SAZ of reference center
	                          double   ZA_center,  //... ZA of reference center
	                          double  *SAZ,        //... returns aziumth measured west of due south
	                          double  *ZA)         //... returns zenith angle
{
	double pi, ZA_complement;

	pi = 4.0 * atan(1.0);

	Standard_to_RADec(Hstandard, Vstandard, -SAZ_center, pi / 2.0 - ZA_center, SAZ, &ZA_complement);

	if (*SAZ > 0.0)  *SAZ = 2.0 * pi - *SAZ;
	else               *SAZ *= -1.0;

	*ZA = pi / 2.0 - ZA_complement;

}


//=========================================================================================
//  Compute angular distance between a pair of RA/DEC coordinates - All angles in radians
//=========================================================================================

double  SphericalAngularDistance_RADec(double ra1, double dec1, double ra2, double dec2)
{
	double  cosangle, angle;


	cosangle = sin(dec1) * sin(dec2) + cos(dec1) * cos(dec2) * cos(ra1 - ra2);

	if (cosangle > +1.0) cosangle = +1.0;
	if (cosangle < -1.0) cosangle = -1.0;

	angle = acos(cosangle);

	return(angle);

}

//=========================================================================================
//  Compute angular distance between south azimuth and zenith angle coords - All radians
//=========================================================================================

double  SphericalAngularDistance_SAZZA(double SAZ1, double ZA1, double SAZ2, double ZA2)
{
	double  cosangle, angle;


	cosangle = cos(ZA1) * cos(ZA2) + sin(ZA1) * sin(ZA2) * cos(SAZ1 - SAZ2);

	if (cosangle > +1.0) cosangle = +1.0;
	if (cosangle < -1.0) cosangle = -1.0;

	angle = acos(cosangle);

	return(angle);

}



//=========================================================================================
//     Conversion from geodetic latitude, +east longitude, altitude above WGS84 to ECEF
//=========================================================================================

void  LLA_to_ECEF(double lat_deg, double eastlon_deg, double alt_km, double *x_km, double *y_km, double *z_km)
{
	double a, e, lat, lon, N;

	lat =     lat_deg / 57.295779513082323;
	lon = eastlon_deg / 57.295779513082323;  // +east

	a = 6378.137;   //... WGS84 constants
	e = 0.081819190842621;

	N = a / sqrt(1.0 - e*e * sin(lat)*sin(lat));

	*x_km = (N + alt_km) * cos(lat) * cos(lon);
	*y_km = (N + alt_km) * cos(lat) * sin(lon);
	*z_km = ((1 - e*e) * N + alt_km) * sin(lat);

}

//=========================================================================================
//    Conversion from ECEF to geodetic latitude, +east longitude, altitude above WGS84
//=========================================================================================

void  ECEF_to_LLA(double x_km, double y_km, double z_km, double *lat_deg, double *eastlon_deg, double *alt_km)
{
	double a, b, e, ep, N, p, theta, lat, lon, alt, x, y, z;

	x = x_km * 1000.0;
	y = y_km * 1000.0;
	z = z_km * 1000.0;

	a = 6378137;   //... WGS84 constants
	e = 0.081819190842621;

	b = sqrt(a*a * (1.0 - e*e));
	ep = sqrt((a*a - b*b) / (b*b));

	lon = atan2(y, x);

	p = sqrt(x*x + y*y);
	theta = atan2(z * a, p * b);

	lat = atan2(z + ep*ep*b*sin(theta)*sin(theta)*sin(theta), p - e*e*a*cos(theta)*cos(theta)*cos(theta));

	N = a / sqrt(1.0 - e*e * sin(lat)*sin(lat));

	alt = p / cos(lat) - N;

	if (fabs(x) < 1.0  &&  fabs(y) < 1.0)  alt = fabs(z) - b;

	*lat_deg     = lat * 57.295779513082323;  //... geodetic latitude
	*eastlon_deg = lon * 57.295779513082323;  //... +east
	*alt_km      = alt / 1000.0;              //... height above WGS84 earth

	//printf("%7.2lf %7.2lf %7.3lf \n", 57.296*lat, 57.296*atan(z/sqrt(x*x+y*y)), 57.296*lat-57.296*atan(z/sqrt(x*x+y*y)) );

}


//=========================================================================================
// Compute Hough parameters rho in pixels, phi angle in deg, and speed for interleaved
// given image dimensions, starting position, and velocity components (pixels/field).
//=========================================================================================

void   ComputeHoughParameters( int nrows, double rowstart, double rowspeed,
	                           int ncols, double colstart, double colspeed,
	                           double *rho, double *phideg, double *deltad)
{
	double  rowcen, colcen, phi, speed;


	rowcen = ((double)nrows - 1.0) / 2.0;
	colcen = ((double)ncols - 1.0) / 2.0;

	if (rowspeed == 0.0)  phi = 3.14159265359 / 2.0;
	else                  phi = atan(colspeed / rowspeed);

	*phideg = phi * 180.0 / 3.14159265359;

	*rho = (colstart - colcen) * cos(phi) + (rowcen - rowstart) * sin(phi);

	speed = sqrt(colspeed * colspeed + rowspeed * rowspeed);

	if (rowspeed <= 0.0)  *deltad = -2.0 * speed;
	else                  *deltad = +2.0 * speed;

}


//=========================================================================================
//             
//=========================================================================================
