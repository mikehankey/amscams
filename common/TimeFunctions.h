//#########################################################################################
//  A set of functions for various time related calculations
//
//  ---------------------------------------------------------------------------------------
//  Ver   Date        Author       Description
//  ----  ----------  -----------  ---------------------------------------------------------
//  1.00  2018-04-16  Gural        Original implementation
//
//#########################################################################################


//=========================================================================================
//========   Structure and function prototypes for pre-detection image processing  ========
//=========================================================================================

struct  DateAndTime
{
	int              year;
	int              month;
	int              day;
	int              hour;
	int              minute;
	int              second;
	int              msec;
};


//-----------------------------------------------------------------------------------------

void   GetCurrentUT_SecondsMicroseconds( time_t *seconds_jan1st1970, long *microseconds );

struct DateAndTime   GetUT_TimeofDay( );

int       GetLocal2UT_TimeDifference( );

void        FillDateAndTimeStructure( long year, long month, long day, long hour, long minute, long second, long msec, 
	                                  struct DateAndTime  *dt );

double             JulianDateAndTime( struct DateAndTime  *dt );

void            Calendar_DateAndTime( double jdt, struct DateAndTime *dt );

double      LocalSiderealTimeDegrees( double jdt, 
	                                  double site_wlongitude );  //... +west (radians)

double  SolarLongitudeDegrees_LowAccuracy( double jde );

void	                    Twilight( double  sun_elevation_deg,
	                                  double  jdt,
	                                  double  site_latitude,  //... geodetic (radians) 
	                                  double  site_longitude, //... +west (radians)
	                                  double *jdt_evening_twilight,
	                                  double *jdt_morning_twilight );

void            NearestLocalMidnight( double   jdt,
	                                  double  *jdt_midnight  );

void                NearestLocalNoon( double   jdt,
	                                  double  *jdt_noon  );

double	         SunElevationDegrees( double   jdt,            
	                                  double   site_latitude,   //... geodetic (radians) 
	                                  double   site_longitude); //... +west (radians)



//#########################################################################################


//=========================================================================================
//         Get the seconds and milliseconds of the current time for Windows and Unix
//=========================================================================================

#ifdef _WIN32 /*############## WINDOWS ############################*/

void     GetCurrentUT_SecondsMicroseconds(time_t *seconds_jan1st1970, long *microseconds)
{
	unsigned __int64    tmpres;
	FILETIME            ft;


	//======== Get time from onboard clock in universal time (UT)

    #if defined(_MSC_VER) || defined(_MSC_EXTENSIONS)
        #define DELTA_EPOCH_IN_MICROSECS  11644473600000000Ui64
    #else
        #define DELTA_EPOCH_IN_MICROSECS  11644473600000000ULL
    #endif


	//======== The GetSystemTimeAsFileTime returns the number of 100 nanosecond 
	//           intervals since Jan 1, 1601 in a structure. Copy the high bits to 
	//           the 64 bit tmpres, shift it left by 32 then OR in the low 32 bits.

	GetSystemTimeAsFileTime(&ft);

	tmpres = 0;
	tmpres |= ft.dwHighDateTime;
	tmpres <<= 32;
	tmpres |= ft.dwLowDateTime;


	//======== Convert to microseconds by dividing by 10

	tmpres /= 10;

	//======== The Unix epoch starts on Jan 1 1970.  Need to subtract the difference 
	//           in seconds from Jan 1 1601.

	tmpres -= DELTA_EPOCH_IN_MICROSECS;

	//======== Finally change microseconds to seconds and place in the seconds value. 
	//           The modulus picks up the microseconds.

	*seconds_jan1st1970 = (time_t)( (long)(tmpres / 1000000UL) );
	*microseconds       = (long)(tmpres % 1000000UL);

}

#else /*##################### LINUX ##############################*/

void     GetCurrentUT_SecondsMicroseconds( time_t *seconds, long *microseconds)
{
	struct timespec curtime = { 0 };


	//======== The clock_gettime returns 

	clock_gettime(CLOCK_REALTIME, &curtime);

	*seconds = curtime.tv_sec;

	*microseconds = round(curtime.tv_nsec / 1.0e9);

}


#endif /*#########################################################*/



//=========================================================================================
//         Get the Universal Date and Time from the PC system clock 
//=========================================================================================

struct DateAndTime      GetUT_TimeofDay()
{
long                microseconds;
time_t              seconds;
struct tm           gmt;
struct DateAndTime  ut;


    GetCurrentUT_SecondsMicroseconds(&seconds, &microseconds);

	gmt = *gmtime(&seconds);

	ut.year   = gmt.tm_year + 1900;
	ut.month  = gmt.tm_mon + 1;
	ut.day    = gmt.tm_mday;
	ut.hour   = gmt.tm_hour;
	ut.minute = gmt.tm_min;
	ut.second = gmt.tm_sec;
	ut.msec   = microseconds / 1000;

	return(ut);

}


//=========================================================================================
//         Get the number of hours difference between local time and GMT 
//=========================================================================================

int       GetLocal2UT_TimeDifference()
{
	long                microseconds;
	double              jdt_GMT, jdt_localtime, hour_shift;
	time_t              seconds;
	struct tm           gmt;
	struct tm           localt;
	struct DateAndTime  ut;


	GetCurrentUT_SecondsMicroseconds(&seconds, &microseconds);

	//======== Get GMT and convert to julian date/time

	gmt = *gmtime(&seconds);

	ut.year   = gmt.tm_year + 1900;
	ut.month  = gmt.tm_mon + 1;
	ut.day    = gmt.tm_mday;
	ut.hour   = gmt.tm_hour;
	ut.minute = gmt.tm_min;
	ut.second = gmt.tm_sec;
	ut.msec   = microseconds / 1000;

	jdt_GMT = JulianDateAndTime(&ut);


	//======== Get local time and convert to julian date/time

	localt = *localtime(&seconds);

	ut.year   = localt.tm_year + 1900;
	ut.month  = localt.tm_mon + 1;
	ut.day    = localt.tm_mday;
	ut.hour   = localt.tm_hour;
	ut.minute = localt.tm_min;
	ut.second = localt.tm_sec;
	ut.msec   = microseconds / 1000;

	jdt_localtime = JulianDateAndTime(&ut);


	//======== Difference Julian dates and convert to nearest hour shift

	hour_shift = ( jdt_localtime - jdt_GMT ) * 24.0;

	if (hour_shift > 0.0)  return((int)(hour_shift + 0.5));
	else                   return((int)(hour_shift - 0.5));

}


//=========================================================================================
//             Fill date and time structure from integer components
//=========================================================================================

void      FillDateAndTimeStructure( long year, long month, long day, long hour, long minute, long second, long msec,
	                                struct DateAndTime  *dt)
{

	dt->year = year;
	dt->month = month;
	dt->day = day;
	dt->hour = hour;
	dt->minute = minute;
	dt->second = second;
	dt->msec = msec;

}


//=========================================================================================
//              Convert Calendar Date and Time to Julian Date
//=========================================================================================

double  JulianDateAndTime( struct DateAndTime  *dt )
{
	int     year, month, aterm, bterm, jdate;
	double  jdt;


	//.................. compute julian date terms

	if ((dt->month == 1) || (dt->month == 2)) {
		year  = dt->year  - 1;
		month = dt->month + 12;
	}
	else {
		year  = dt->year;
		month = dt->month;
	}

	aterm = (int)(year / 100);
	bterm = 2 - aterm + (int)(aterm / 4);

	//.................. julian day at 12hr UT

	jdate = (int)( 365.25 * (double)(year + 4716))
		  + (int)(30.6001 * (double)(month + 1))
		  + dt->day + bterm - 1524;

	//................... add on the actual UT

	jdt = (double)jdate - 0.5
		+ (double)dt->hour   / (24.0)
		+ (double)dt->minute / (24.0 * 60.0)
		+ (double)dt->second / (24.0 * 60.0 * 60.0)
		+ (double)dt->msec   / (24.0 * 60.0 * 60.0 * 1000.0);

	return(jdt);
}

//=========================================================================================
//               Convert Julian Date to Calendar Date and Time
//=========================================================================================

void  Calendar_DateAndTime( double jdt, struct DateAndTime *dt )
{
	int        jyear, jmonth, jday, jhour, jminute, jsecond, jmsec;
	int        aterm, bterm, cterm, dterm, eterm, alpha, intpart;
	double     fracpart;

	//.................. JD integer and fractional part

	intpart = (int)(jdt + 0.5);
	fracpart = (jdt + 0.5) - (double)intpart;

	alpha = (int)(((double)intpart - 1867216.25) / 36524.25);
	aterm = intpart + 1 + alpha - (alpha / 4);
	bterm = aterm + 1524;
	cterm = (int)(((double)bterm - 122.1) / 365.25);
	dterm = (int)(365.25 * (double)cterm);
	eterm = (int)(((double)bterm - (double)dterm) / 30.6001);

	//................... date calculation

	jday = bterm - dterm - (int)(30.6001 * (double)eterm);

	if (eterm < 14)  jmonth = (int)eterm - 1;
	else             jmonth = (int)eterm - 13;

	if (jmonth > 2)  jyear  = (int)cterm - 4716;
	else             jyear  = (int)cterm - 4715;


	//................... time calculation

	fracpart += 0.0001 / (24.0 * 60.0 * 60.0); // Add 0.1 msec for rounding
	fracpart *= 24.0;
	jhour     = (int)fracpart;
	fracpart -= (double)jhour;
	fracpart *= 60.0;
	jminute   = (int)fracpart;
	fracpart -= (double)jminute;
	fracpart *= 60.0;
	jsecond   = (int)fracpart;
	fracpart -= (double)jsecond;
	fracpart *= 1000.0;
	jmsec     = (int)fracpart;


	//................... put into output date/time structure

	dt->year   = jyear;
	dt->month  = jmonth;
	dt->day    = jday;
	dt->hour   = jhour;
	dt->minute = jminute;
	dt->second = jsecond;
	dt->msec   = jmsec;

}

//=========================================================================================
//           Compute Solar Longitude in Degrees from Julian Emphemeris Time
//
//                From Meeus pg 151-152 low accuracy to 0.01 deg (36")
//=========================================================================================

double  SolarLongitudeDegrees_LowAccuracy(double jde)
{
	double  sunlongitude, tim, meanlongitude, meananomaly, corrlongitude;
	struct DateAndTime  dt;


	Calendar_DateAndTime(jde, &dt);

	tim = (jde - 2451545.0) / 36525.0;


	meanlongitude = 280.46645
		          + 36000.76983 * tim
		          + 0.0003032   * tim * tim;

	while (meanlongitude >= 360.0)  meanlongitude -= 360.0;
	while (meanlongitude <    0.0)  meanlongitude += 360.0;


	meananomaly = (357.52910
		        + 35999.05030 * tim
		        - 0.0001559   * tim * tim
		        - 0.00000048  * tim * tim * tim);

	while (meananomaly >= 360.0)  meananomaly -= 360.0;
	while (meananomaly <    0.0)  meananomaly += 360.0;

	meananomaly *= (4.0 * atan(1.0)) / 180.0;  //...pi/180


	corrlongitude = (1.914600 - 0.004817*tim - 0.000014*tim*tim)
		* sin(meananomaly)
		+ (0.019993 - 0.000101*tim)
		* sin(meananomaly * 2.0)
		+ (0.000290)
		* sin(meananomaly * 3.0);


	sunlongitude = meanlongitude
		+ corrlongitude
		- 0.01397 * (double)(dt.year - 2000);

	while (sunlongitude >= 360.0)  sunlongitude -= 360.0;
	while (sunlongitude <    0.0)  sunlongitude += 360.0;


	return(sunlongitude);
}


//=========================================================================================
//         Local Sidereal Time from Julian Date and Site Longitude (+west)
//=========================================================================================

double  LocalSiderealTimeDegrees(double jdt, double site_wlongitude )
{
	double  tim, stg, localstdeg;  //... longitude assumed +west in radians

	//.................. sidereal time at Greenwich

	tim = (jdt - 2451545.0) / 36525.0;

	stg = 280.46061837
		+ 360.98564736629 * (jdt - 2451545.0)
		+ tim * tim * 0.000387933
		- tim * tim * tim / 38710000.0;

	//.................. local sidereal time

	localstdeg = stg - site_wlongitude * 180.0 / 3.141592654;

	//.................. set value between 0 and 360 degrees

	while (localstdeg >= +360.0)  localstdeg -= 360.0;
	while (localstdeg <     0.0)  localstdeg += 360.0;

	return(localstdeg);
}

//=========================================================================================
//          Obtain the Julian Date of Twilight defined by Sun Elevation Angle
//=========================================================================================

void	Twilight( double  sun_elevation_deg,
	              double  jdt,
	              double  site_latitude,  //... geodetic (radians) 
	              double  site_longitude, //... +west (radians)
	              double *jdt_evening_twilight,
	              double *jdt_morning_twilight)
{
double  jdt_noon, jdtshift, sunlong, LST, hourangle, d2r, rah, dec, transit, obliquity;
struct DateAndTime  dt;


	d2r = 3.141592654 / 180.0;

	Calendar_DateAndTime(jdt, &dt);

	dt.hour   = 0;  //... Get sun's position for Greenwich noon
	dt.minute = 0;
	dt.second = 0;
	dt.msec   = 0;

	jdt_noon = JulianDateAndTime( &dt );  //... JDT in Greenwich at 0:00 UT

	sunlong = d2r * SolarLongitudeDegrees_LowAccuracy(jdt_noon + 32.184 / 86400.0); // ignoring leap seconds

	LST = d2r * LocalSiderealTimeDegrees(jdt_noon, 0.0);  //...LST at Greenwich longitude = 0 radians


	//----- Get the sun's RA and Dec

	obliquity = 23.439 * d2r;

	rah = atan2(cos(obliquity) * sin(sunlong), cos(sunlong));

	dec = asin(sin(obliquity) * sin(sunlong));


	//----- compute the hour angle for the sun xxx degrees below horizon
	//         that will define the start of collection

	hourangle = acos((sin(sun_elevation_deg * d2r) - sin(site_latitude) * sin(dec))
		      / (cos(site_latitude) * cos(dec)));

	transit = rah + site_longitude - LST;  //... Noon transit for the local site


	jdtshift = (transit + hourangle) / d2r / 360.0;

	while (jdtshift < 0.0)  jdtshift += 1.0;
	while (jdtshift > 1.0)  jdtshift -= 1.0;

	*jdt_evening_twilight = jdt_noon + jdtshift;

	while (*jdt_evening_twilight - jdt < -1.0) *jdt_evening_twilight += 1.0;
	while (*jdt_evening_twilight - jdt > +1.0) *jdt_evening_twilight -= 1.0;


	jdtshift = (transit - hourangle) / d2r / 360.0;

	while (jdtshift < 0.0)  jdtshift += 1.0;
	while (jdtshift > 1.0)  jdtshift -= 1.0;

	*jdt_morning_twilight = jdt_noon + jdtshift;

	while (*jdt_morning_twilight - jdt < -1.0) *jdt_morning_twilight += 1.0;
	while (*jdt_morning_twilight - jdt > +1.0) *jdt_morning_twilight -= 1.0;

}


//=========================================================================================
//          Compute the Closest Local Midnight near the given Julian Date
//=========================================================================================

void   NearestLocalMidnight(double jdt,  double *jdt_midnight)  //... jdt in UT

{
	int     delta_hour;
	long    kjdt;
	double  jdt_greenwich_midnight, jdt_local_midnight;



	delta_hour = GetLocal2UT_TimeDifference();

	//======== Midnight on the zero meridian minus the hour offset

	jdt_greenwich_midnight = (double)((int)jdt) + 0.5;

	jdt_local_midnight = jdt_greenwich_midnight - delta_hour / 24.0;


	//----- round to nearest hour

	kjdt = (long)(jdt_local_midnight * 24.0 + 0.5);

	*jdt_midnight = (double)kjdt / 24.0;

	while (*jdt_midnight - jdt > +0.5)  *jdt_midnight -= 1.0;
	while (*jdt_midnight - jdt < -0.5)  *jdt_midnight += 1.0;

}

//=========================================================================================
//          Compute the Closest Local Noon near the given Julian Date
//=========================================================================================

void   NearestLocalNoon(double jdt,  double *jdt_noon)  //... jdt in UT

{
	int     delta_hour;
	long    kjdt;
	double  jdt_greenwich_noon, jdt_local_noon;



	delta_hour = GetLocal2UT_TimeDifference();

	//======== Noon on the zero meridian minus the hour offset

	jdt_greenwich_noon = (double)((int)jdt);

	jdt_local_noon = jdt_greenwich_noon - delta_hour / 24.0;


	//----- round to nearest hour

	kjdt = (long)(jdt_local_noon * 24.0 + 0.5);

	*jdt_noon = (double)kjdt / 24.0;

	while (*jdt_noon - jdt > +0.5)  *jdt_noon -= 1.0;
	while (*jdt_noon - jdt < -0.5)  *jdt_noon += 1.0;
}

//=========================================================================================
//     Compute the Sun's Elevation Angle (+above, -below)) the Horizon in degrees
//=========================================================================================


double	SunElevationDegrees( double  jdt,
	                         double  site_latitude,   //... geodetic (radians) 
	                         double  site_longitude ) //... +west (radians)
{
double  sunlong, LST, d2r, ra, dec, obliquity, elev_deg;


	d2r = 3.141592654 / 180.0;


	//----- Get the site's local sidereal time and sun's longitude, RA and Dec

	LST = d2r * LocalSiderealTimeDegrees(jdt, site_longitude);

	sunlong = d2r * SolarLongitudeDegrees_LowAccuracy(jdt + 32.184 / 86400.0); // ignoring leap seconds

	obliquity = 23.439 * d2r;

	ra  = atan2(cos(obliquity) * sin(sunlong), cos(sunlong));

	dec = asin(sin(obliquity) * sin(sunlong));


	//----- compute the sun's elevation angle

	elev_deg = asin(sin(site_latitude) * sin(dec)
		          + cos(site_latitude) * cos(dec) * cos(LST - ra)) / d2r;

	return(elev_deg);

}

	
