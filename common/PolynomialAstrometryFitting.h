
//########################################################################
//  Collection of calibration routines for wide field to narrow field of
//  view camera systems (NOT all-sky). Includes fitting capability and
//  forward/inverse transforms for various polynomial models including
//  linear, quadratic, cubic, quintic, and cubic with first order radial
//  terms. 
//
//  1 Linear        1, x, y
//  2 Quadratic     1, x, y, x^2, xy, y^2
//  3 Cubic         1, x, y, x^2, xy, y^2, x^3, x^2y, xy^2, y^3
//  5 Quintic       1, x, y, x^2, xy, y^2, x^3, x^2y, xy^2, y^3, x^5, x^4y, ... y^5
// 12 Cubic/Radial  1, x, y, x^2, xy, y^2, x^3, x^2y, xy^2, y^3, xr, yr
// 13 Cubic/Radial  1, x, y, x^2, xy, y^2, x^3, x^2y, xy^2, y^3, r, xr, yr
//
//  r = sqrt( x^2 + y^2 )  where x and y origin is the optical center
//
//  These calibration fit functions take a list of RA/Dec of stars with
//  associated row/col measured centroid positions off the focal plane
//  imagery of the same stars, and finds the coefficients for the
//  above listed models working in gnomonic space after conversion of 
//  the RA/Dec to standard (gnomic) coordinates. Thus the fit is actually
//  between standard and measured star centroids where the origin of the 
//  fitting functions is the center of the optical axis. Note the input 
//  centroid measurements are assumed based on an origin in the upper 
//  left corner of the image.
//#######################################################################



//#######################################################################
//                      Constants
//#######################################################################


#define  MAXCOEFS            30
#define  MAXCHARACTERS      256


//#######################################################################
//                      Structures
//#######################################################################


struct  polycal_starinfo
{
	double    RA_deg;
	double    DEC_deg;
	double    Xstd;
	double    Ystd;
	double    rowcentroid;
	double    colcentroid;
	double    oc_arcmin;
	double    vmag;
	double    bvmag;
	double    rmag;
	double    imag;
	double    smag;  //spectral response magnitude for catalog star field display
	double    logintensity;
	double    logvignette;
	double    logflux;
	long      intensity;
	long      rawintensity;
};


//======================================================================


struct  polycal_parameters
{
	//--------------------------------------- Star / centroid info
	int       ncalstars;
	struct    polycal_starinfo  *starinfo;

	//--------------------------------------- File info
	char      CALpathname[MAXCHARACTERS];
	char      CALnameonly[MAXCHARACTERS];

	//--------------------------------------- Site info
	int       cameranumber;  // CAMS 6 digit
	double    jdtcal;        // UT
	double    longitude_deg; // +West
	double    latitude_deg;  // Geodetic GPS
	double    height_km;     // Above WGS84

	//--------------------------------------- Camera specs
	double    framerate_Hz;
	double    midrow;
	double    midcol;

	//--------------------------------------- Fit coefficients
	int       fitorder;
	int       ncoefs;
	double    Xcoef[MAXCOEFS];  // 1  x  y  x^2  xy  y^2  x^3  x^2y  xy^2  y^3 ...
	double    Ycoef[MAXCOEFS];
	int       inverse_populated;
	double    Xinvcoef[MAXCOEFS];
	double    Yinvcoef[MAXCOEFS];

	//--------------------------------------- Astrometry products
	double    fovheight_deg;
	double    fovwidth_deg;
	double    arcminperpixel;
	double    plateroll_deg;
	double    cameratilt_deg;
	double    RAcenter_deg;
	double    DECcenter_deg;
	double    AZcenter_deg;
	double    ELcenter_deg;

	//--------------------------------------- Fit O-C performance
	double    oc_mean_arcmin;
	double    oc_sigma_arcmin;
	double    oc_rms_arcmin;

	//--------------------------------------- Photometry
	double    magicept;
	double    magslope;
	double    magiceptFlux;
	double    magslopeFlux;
	double    bvlimit;
	double    Vmaglimit;

	//---------------------------------------
};



//#######################################################################
//                      Function Prototypes
//#######################################################################

void  Polycal_FreeMemory( struct polycal_parameters *cal );

void  Polycal_AllocMemory( struct polycal_parameters *cal, int ncalstars );

long  Polycal_AstrometrySolver( int fitorder, struct polycal_parameters *cal );

void  Polycal_InversePolyCoefs( struct polycal_parameters *cal);

void  Polycal_rowcol2std( struct polycal_parameters  *cal,
	                      double   row,    //...actual row and column number
	                      double   col,
	                      double  *Xstd,
	                      double  *Ystd);

void  Polycal_std2rowcol( struct polycal_parameters  *cal,
	                      double   Xstd,
	                      double   Ystd,
	                      double  *row,   //...actual row and column number
	                      double  *col);

void  Polycal_ComputeOminusC( struct polycal_parameters *cal );

void  Polycal_SetUncalibrated( struct polycal_parameters *cal );

void  Polycal_ReadCALfile( char *filename, struct polycal_parameters *cal, struct camerasiteinfo *camsite);

void  Polycal_WriteCALfile( char *calfolder, struct polycal_parameters *cal, struct camerasiteinfo *camsite );


void  SVD_SquareMatrix( double *A, double *US, double *S2, double *V, int n, int maxn );

void  LMSviaSVD(double **Q, double *b, double *x, int nmeas, int ncoefs, int nrhs);




//#######################################################################
//              Free memory for starinfo structures
//#######################################################################

void  Polycal_FreeMemory( struct polycal_parameters *cal )
{
    free( cal->starinfo );

	cal->starinfo = NULL;
}


//#######################################################################
//  Allocate memory for starinfo structures given number of stars to use
//#######################################################################

void  Polycal_AllocMemory( struct polycal_parameters *cal, int ncalstars )
{
static int   firstcall = 1;


    if (firstcall == 1)  cal->starinfo = NULL;  //... 1st call to Polycal_AllocMemory

	firstcall = 0;


	if( cal->starinfo != NULL )  Polycal_FreeMemory( cal );

	cal->starinfo = (struct polycal_starinfo*) malloc( ncalstars * sizeof(struct polycal_starinfo) );

	if( cal->starinfo == NULL ) {
		printf(" Could not allocate space for %i stars in polycal_parameters structure\n", ncalstars);
	    Delay_msec(10000);
		exit(1);
	}

	cal->ncalstars = ncalstars;

}


//#######################################################################
//  Astrometric polynomial calibration fitting module for one of the 
//  following functional forms with "fitorder" listed to the left:
//
//  1 Linear         1, x, y
//  2 Quadratic      1, x, y, x^2, xy, y^2
//  3 Cubic          1, x, y, x^2, xy, y^2, x^3, x^2y, xy^2, y^3
//  5 Quintic        1, x, y, x^2, xy, y^2, x^3, x^2y, xy^2, y^3, x^5, x^4y, ... y^5
// 12 Cubic xryr     1, x, y, x^2, xy, y^2, x^3, x^2y, xy^2, y^3, xr, yr
// 13 Cubic Radial   1, x, y, x^2, xy, y^2, x^3, x^2y, xy^2, y^3, r, xr, yr
//
//
//  Uses a pseudo inverse via the singular value decomposition to handle
//  situations in which the solution is based on an ill-conditioned
//  scenario. That is, one or more coefficient terms are not actually
//  a contributor to the image warping. Note that the centroids 
//  measurements will get scaled internally in the function to have
//  values fall between -1 and +1 to avoid overflows during
//  computation, but note that all outputs have the scaling removed.
//
//  Requires the calibration structure be populated with the best guess
//  at the center RA/Dec (or a vector average is taken if the user sets
//  the center RA to 999.0), the actual row and column of the image center, 
//  the associated RA/Dec and row/col centroids for each of the ncalstars
//  AFTER the user has allocated the memory for the starinfo via call to
//  Polycal_AllocMemory and then filled in the starinfo structural
//  elements, the site's GPS coordinates, calibration Julian date/time,
//  the cameranumber, and the framerate. Note that row and column I/O 
//  are measured from the upper left corner of the image.
//
//  All the remaining polycal_parameters structural elements are filled
//  in after the fit EXCEPT for the CAL file full pathname as the user
//  must specify the folder later and build the pathname from the folder
//  and CALnameonly.
//
//
//  Inputs:  fitorder    (can be 1, 2, 3, 5, 12 or 13)
//           polycal_parameters structure pre-filled with:
//               RAcenter_deg   (user guess or set to 999.0 for auto)
//               DECcenter_deg
//               midrow         (#rows/2.0)
//               midcol         (#cols/2.0)
//               ncalstars
//               for kthstar = 0 to cal->ncalstars-1
//                   calstar[kthstar].RA_deg
//                   calstar[kthstar].DEC_deg
//                   calstar[kthstar].rowcentroid
//                   calstar[kthstar].colcentroid
//               framerate_Hz
//               cameranumber       (CAMS 6 digit)
//               latitude_deg       (geodetic latitude = GPS)
//               longitude_deg      (+west = GPS)
//               height_km          (above WGS84)
//               jdtcal             (Julian date/time UT)
//
//  Outputs: polycal_parameters structure post-filled with:
//               CALnameonly
//               fitorder
//               ncoefs
//               Xcoef[kcoef]
//               Ycoef[kcoef]
//               inverse_populated
//               Xinvcoef[kcoef]
//               Yinvcoef[kcoef]
////               xo
////               yo
////               RAoptical_deg
////               DECoptical_deg
//               RAcenter_deg
//               DECcenter_deg
//               AZcenter_deg        (+East of North)
//               ELcenter_deg
//               fovwidth_deg
//               fovheight_deg
//               cameratilt_deg      (w.r.t. horizon)
//               arcminperpixel
//               plateroll_deg       (w.r.t. standard)
//               oc_mean_arcmin
//               oc_sigma_arcmin
//               oc_rms_arcmin
//               starinfo.oc_arcmin[kthstar], kthstar = 0 to ncalstars-1
//
//#######################################################################

long    Polycal_AstrometrySolver( int fitorder, struct polycal_parameters *cal )
{
int     kiteration, jthstar, kthstar, kr;
double  x, y, r, Xstd, Ystd, pi, deg2rad;
double  RAcenter, DECcenter, RA, DEC, RA1, DEC1, RA2, DEC2, LST_deg;
double  deltaAZ_deg, deltaEL_deg, ten_pixels_rad;
double  fovwidth_rad, fovheight_rad, azim_rad, elev_rad;
double  vectorsum[3], vec[3];

double  **Q;
double   *XYstd;
double   *XYcoef;

struct    DateAndTime   ut;



       pi = 4.0 * atan(1.0);

	   deg2rad = pi / 180.0;

 
	   //--------------------- Build the CAL filename (CAMS convention)

	   Calendar_DateAndTime( cal->jdtcal, &ut );

	   sprintf( cal->CALnameonly, "CAL_%06d_%04d%02d%02d_%02d%02d%02d_%03d.txt",
		   cal->cameranumber, ut.year, ut.month, ut.day, ut.hour, ut.minute, ut.second, ut.msec); 
	   
		   
	   //-------------- Determine the number of fit coefs to be used

	   cal->fitorder = fitorder;

	   if      (cal->fitorder ==  1)  cal->ncoefs = 3;
	   else if (cal->fitorder ==  2)  cal->ncoefs = 6;
	   else if (cal->fitorder ==  3)  cal->ncoefs = 10;
	   else if (cal->fitorder ==  5)  cal->ncoefs = 16;
	   else if (cal->fitorder == 12)  cal->ncoefs = 12;
	   else if (cal->fitorder == 13)  cal->ncoefs = 13;
	   else {
		   printf(" fitorder %i not implemented in PolynomialAstrometricCalibration\n", cal->fitorder);
		   Delay_msec(10000);
		   exit(1);
	   }


	   if (2*cal->ncoefs-2 > MAXCOEFS) {
		   printf(" fitorder %i requires increasing MAXCOEFS in CalibrationFunctions.h to %i\n", cal->fitorder, 2*cal->ncoefs-2);
		   Delay_msec(10000);
		   exit(1);
	   }

	   
      //-------------- Test for minimum number of stars to do transform fit

       if( cal->ncalstars < 2*cal->ncoefs-2 ) {
	       printf(" PolynomialAstrometricCalibration requires minimum of %i stars - only %i provided\n", 
			        2*cal->ncoefs-2, cal->ncalstars );
		   return(1);
	   }


	   //-------------- Allocate memory for the 1D and 2D arrays

	   XYstd  = (double*)malloc(2*cal->ncalstars * sizeof(double));
	   XYcoef = (double*)malloc((2*cal->ncoefs-2)  * sizeof(double));

	   Q      = (double**)allocate_2d_array(2*cal->ncalstars, 2*cal->ncoefs-2, sizeof(double));


	   //--------------- Initial guess for the image center in equatorial coords RA/DEC

	   if (cal->RAcenter_deg == 999.0) {

		   vectorsum[0] = 0.0;
		   vectorsum[1] = 0.0;
		   vectorsum[2] = 0.0;

		   for (kthstar = 0; kthstar < cal->ncalstars; kthstar++) {

			   RADec2xyz( cal->starinfo[kthstar].RA_deg  * deg2rad,
				          cal->starinfo[kthstar].DEC_deg * deg2rad,
				          1.0, vec );

			   vectorsum[0] += vec[0];
			   vectorsum[1] += vec[1];
			   vectorsum[2] += vec[2];

		   }

		   xyz2RADec(vectorsum, &RAcenter, &DECcenter, &vec[0]);
	   }

	   else {

		   RAcenter  = cal->RAcenter_deg  * deg2rad;
		   DECcenter = cal->DECcenter_deg * deg2rad;

	   }


	   //--------------- Initialize the optical axis offset from the image center

	   cal->Xcoef[0] = 0.0;
	   cal->Ycoef[0] = 0.0;


       //--------------- Iterate the solution to find the image center's RA,DEC 
       
       for( kiteration=0; kiteration<10; kiteration++ )  {


            //.......... Convert each star's RA,DEC into standard coordinates
            //
            //           NOTE: Only valid if star's distance from center < 90 deg

            for( kthstar=0; kthstar<cal->ncalstars; kthstar++ )  {
            
                 RADec_to_Standard( cal->starinfo[kthstar].RA_deg  * deg2rad, 
                                    cal->starinfo[kthstar].DEC_deg * deg2rad,
                                    RAcenter,
                                    DECcenter,
						            &cal->starinfo[kthstar].Xstd,
						            &cal->starinfo[kthstar].Ystd  );

				 jthstar = kthstar + cal->ncalstars;

				 XYstd[kthstar] = cal->starinfo[kthstar].Xstd;
				 XYstd[jthstar] = cal->starinfo[kthstar].Ystd;
			}

            
            //........... Fill the Q matrix of measurements
            
            for( kthstar=0; kthstar<cal->ncalstars; kthstar++ )  {

                 x = cal->starinfo[kthstar].colcentroid - ( cal->midcol + cal->Xcoef[0] );
                 y = ( cal->midrow + cal->Ycoef[0] ) - cal->starinfo[kthstar].rowcentroid;

				 jthstar = kthstar + cal->ncalstars;

				 if( cal->fitorder >= 1 )  {  //... Linear terms
					 Q[kthstar][0] = x;
					 Q[kthstar][1] = y;
					 Q[kthstar][2] = 1.0;

					 Q[jthstar][0] = y;
					 Q[jthstar][1] =-x;
					 Q[jthstar][2] = 0.0;
				 }
				 if( cal->fitorder >= 2 )  {  //... Quadratic terms
				     Q[kthstar][3] = x*x;
				     Q[kthstar][4] = x*y;
				     Q[kthstar][5] = y*y;

					 Q[jthstar][3] = 0.0;
					 Q[jthstar][4] = 0.0;
					 Q[jthstar][5] = 0.0;
				 }
				 if (cal->fitorder >= 3) {  //... Cubic terms
					 Q[kthstar][6] = x*x*x;
					 Q[kthstar][7] = x*x*y;
					 Q[kthstar][8] = x*y*y;
					 Q[kthstar][9] = y*y*y;

					 Q[jthstar][6] = 0.0;
					 Q[jthstar][7] = 0.0;
					 Q[jthstar][8] = 0.0;
					 Q[jthstar][9] = 0.0;
				 }
				 if (cal->fitorder == 12) {  //... Radial terms
					 r = sqrt(x*x + y*y);
					 Q[kthstar][10] = x*r;
					 Q[kthstar][11] = y*r;
					 Q[kthstar][12] = 0.0;
					 Q[kthstar][13] = 0.0;
					 Q[kthstar][14] = 0.0;
					 Q[kthstar][15] = 0.0;
					 Q[kthstar][16] = 0.0;
					 Q[kthstar][17] = 0.0;
					 Q[kthstar][18] = 0.0;
					 Q[kthstar][19] = 0.0;
					 Q[kthstar][20] = 0.0;
					 Q[kthstar][21] = 0.0;

					 Q[jthstar][10] = 0.0;
					 Q[jthstar][11] = 0.0;
					 Q[jthstar][12] = 1.0;
					 Q[jthstar][13] = x*x;
					 Q[jthstar][14] = x*y;
					 Q[jthstar][15] = y*y;
					 Q[jthstar][16] = x*x*x;
					 Q[jthstar][17] = x*x*y;
					 Q[jthstar][18] = x*y*y;
					 Q[jthstar][19] = y*y*y;
					 Q[jthstar][20] = x*r;
					 Q[jthstar][21] = y*r;
				 }
				 if (cal->fitorder == 13) {  //... Radial terms
					 r = sqrt(x*x + y*y);
					 Q[kthstar][10] = r;
					 Q[kthstar][11] = x*r;
					 Q[kthstar][12] = y*r;
					 Q[kthstar][13] = 0.0;
					 Q[kthstar][14] = 0.0;
					 Q[kthstar][15] = 0.0;
					 Q[kthstar][16] = 0.0;
					 Q[kthstar][17] = 0.0;
					 Q[kthstar][18] = 0.0;
					 Q[kthstar][19] = 0.0;
					 Q[kthstar][20] = 0.0;
					 Q[kthstar][21] = 0.0;
					 Q[kthstar][22] = 0.0;
					 Q[kthstar][23] = 0.0;

					 Q[jthstar][10] = 0.0;
					 Q[jthstar][11] = 0.0;
					 Q[jthstar][12] = 0.0;
					 Q[jthstar][13] = 1.0;
					 Q[jthstar][14] = x*x;
					 Q[jthstar][15] = x*y;
					 Q[jthstar][16] = y*y;
					 Q[jthstar][17] = x*x*x;
					 Q[jthstar][18] = x*x*y;
					 Q[jthstar][19] = x*y*y;
					 Q[jthstar][20] = y*y*y;
					 Q[jthstar][21] = r;
					 Q[jthstar][22] = x*r;
					 Q[jthstar][23] = y*r;
				 }

			}


			//............ LMS solve for coefs

			LMSviaSVD( Q, XYstd, XYcoef, 2 * cal->ncalstars, 2 * cal->ncoefs - 2, 1 );


			//............ Copy out coefs to cal structure

			for (kr = 3; kr < cal->ncoefs; kr++)  cal->Xcoef[kr] = XYcoef[kr];

			for (kr = 3; kr < cal->ncoefs; kr++)  cal->Ycoef[kr] = XYcoef[kr + cal->ncoefs - 2];

			cal->Xcoef[0] = XYcoef[2];
			cal->Xcoef[1] = XYcoef[0];
			cal->Xcoef[2] = XYcoef[1];

			cal->Ycoef[0] = XYcoef[cal->ncoefs];
			cal->Ycoef[1] =-XYcoef[1];
			cal->Ycoef[2] = XYcoef[0];



/*
			//............ If cubic-radial, find an improved xo, yo (BRUTE FORCE METHOD)

			if (cal->fitorder == 12  ||  cal->fitorder == 13)  {

				//~~~~~~ Loop over finer xo, yo test resolutions

				xo = cal->xo;
				yo = cal->yo;

				deltao = 1.0;   //... Start at 1 pixel and go to 1/128

				for( kresloop=0; kresloop<8; kresloop++ )  {

					continue_searching_at_this_resolution = 1;

					while(continue_searching_at_this_resolution == 1 )  {

						ocbest = 1.0e+30;

						for (kdrow = -1; kdrow <= +1; kdrow++ ) {
						for (kdcol = -1; kdcol <= +1; kdcol++) {

							 cal->xo = xo + (double)kdcol * deltao;
							 cal->yo = yo + (double)kdrow * deltao;

							 Polycal_ComputeOminusC( cal );

							 if( cal->oc_mean_arcmin < ocbest )  {
								 xobest = cal->xo;
								 yobest = cal->yo;
								 ocbest = cal->oc_mean_arcmin;
							 }

						}
					    } //... end of double loop to search 3x3 grid

						if( xo == xobest  &&  yo == yobest )  continue_searching_at_this_resolution = 0;
						else  {
							xo = xobest;
							yo = yobest;							
							continue_searching_at_this_resolution = 1;
						}

					} //... end of while search at given resolution

					deltao /= 2.0;

				} //... end of eight finer resolutions loop


				//~~~~~~ Save the optical axis offsets

		        cal->xo = xo;
		        cal->yo = yo;

			}  //... end of if cubic-radial then iteration on xo, yo 
*/

			cal->RAcenter_deg  = RAcenter  / deg2rad;
			cal->DECcenter_deg = DECcenter / deg2rad;

			Polycal_ComputeOminusC(cal);

                                    
            //............ Now get the RA, DEC of the image center

			Polycal_rowcol2std(cal, cal->midrow, cal->midcol, &Xstd, &Ystd);

	        Standard_to_RADec( Xstd, Ystd, RAcenter, DECcenter, &RA, &DEC );

			RAcenter  = RA;
			DECcenter = DEC;

			if (kiteration % 100 >= 0) {

				printf("Image Center  %lf  %lf    %lf  %lf    %lf\n", cal->Xcoef[0], cal->Ycoef[0], RAcenter/deg2rad, DECcenter/deg2rad, cal->oc_mean_arcmin);
				/*
				printf("1    %lf   %lf\n", cal->Xcoef[0] * 1.0, cal->Ycoef[0] * 1.0);
				printf("x    %lf   %lf\n", cal->Xcoef[1] * 640.0, cal->Ycoef[1] * 640.0);
				printf("y    %lf   %lf\n", cal->Xcoef[2] * 640.0, cal->Ycoef[2] * 640.0);
				printf("xx   %lf   %lf\n", cal->Xcoef[3] * 640.0 * 640.0, cal->Ycoef[3] * 640.0 * 640.0);
				printf("xy   %lf   %lf\n", cal->Xcoef[4] * 640.0 * 640.0, cal->Ycoef[4] * 640.0 * 640.0);
				printf("yy   %lf   %lf\n", cal->Xcoef[5] * 640.0 * 640.0, cal->Ycoef[5] * 640.0 * 640.0);
				printf("xxx  %lf   %lf\n", cal->Xcoef[6] * 640.0 * 640.0 * 640.0, cal->Ycoef[6] * 640.0 * 640.0 * 640.0);
				printf("xxy  %lf   %lf\n", cal->Xcoef[7] * 640.0 * 640.0 * 640.0, cal->Ycoef[7] * 640.0 * 640.0 * 640.0);
				printf("xyy  %lf   %lf\n", cal->Xcoef[8] * 640.0 * 640.0 * 640.0, cal->Ycoef[8] * 640.0 * 640.0 * 640.0);
				printf("yyy  %lf   %lf\n", cal->Xcoef[9] * 640.0 * 640.0 * 640.0, cal->Ycoef[9] * 640.0 * 640.0 * 640.0);
				printf("r    %lf   %lf\n", cal->Xcoef[10] * 640.0, cal->Ycoef[10] * 640.0);
				printf("xr   %lf   %lf\n", cal->Xcoef[11] * 640.0 * 640.0, cal->Ycoef[11] * 640.0 * 640.0);
				printf("yr   %lf   %lf\n", cal->Xcoef[12] * 640.0 * 640.0, cal->Ycoef[12] * 640.0 * 640.0);
                */
			}


       } //... end of refinement iteration loop for RA/Dec of the center


	   cal->RAcenter_deg  = RAcenter  / deg2rad;
	   cal->DECcenter_deg = DECcenter / deg2rad;


	   //----------------------- Solve for the inverse coefficients (std -> row/col)

	   Polycal_InversePolyCoefs( cal );
       

	   //----------------------- Determine FOV width

	   Polycal_rowcol2std( cal, cal->midrow, 0.5, &Xstd, &Ystd );

       Standard_to_RADec( Xstd, Ystd, RAcenter, DECcenter, &RA1, &DEC1 );

	   Polycal_rowcol2std( cal, cal->midrow, 2.0*cal->midcol-0.5, &Xstd, &Ystd );

       Standard_to_RADec( Xstd, Ystd, RAcenter, DECcenter, &RA2, &DEC2 );

                                                                                     
	   fovwidth_rad = SphericalAngularDistance_RADec( RA1, DEC1, RA2, DEC2 );

	   cal->fovwidth_deg = fovwidth_rad / deg2rad;


       //.......................... Determine FOV height

	   Polycal_rowcol2std( cal, 0.5, cal->midcol, &Xstd, &Ystd );

       Standard_to_RADec( Xstd, Ystd, RAcenter, DECcenter, &RA1, &DEC1 );

                                           
	   Polycal_rowcol2std( cal, 2.0*cal->midrow - 0.5, cal->midcol, &Xstd, &Ystd );

       Standard_to_RADec( Xstd, Ystd, RAcenter, DECcenter, &RA2, &DEC2 );

                                                                                     
	   fovheight_rad = SphericalAngularDistance_RADec( RA1, DEC1, RA2, DEC2 );

 	   cal->fovheight_deg = fovheight_rad / deg2rad;


	   //----------------------- Determine the azimuth and elevation (altitude) of center

	   LST_deg = LocalSiderealTimeDegrees( cal->jdtcal, cal->longitude_deg * deg2rad );

	   RADec_to_AzimElev( RAcenter, DECcenter,
                          cal->latitude_deg * deg2rad, 
                          LST_deg * deg2rad,
					      &azim_rad, &elev_rad  );

       cal->AZcenter_deg = azim_rad / deg2rad;
	   cal->ELcenter_deg = elev_rad / deg2rad;
       

	   //----------------------- Camera tilt wrt to horizon, pixel res, roll wrt std

	   Polycal_rowcol2std(cal, cal->midrow, cal->midcol + 10.0, &Xstd, &Ystd);

	   Standard_to_RADec(Xstd, Ystd, RAcenter, DECcenter, &RA, &DEC);

	   RADec_to_AzimElev( RA, DEC,
                          cal->latitude_deg * deg2rad, 
                          LST_deg * deg2rad,
					      &azim_rad, &elev_rad  );

	   deltaEL_deg = elev_rad / deg2rad - cal->ELcenter_deg;

	   deltaAZ_deg = azim_rad / deg2rad - cal->AZcenter_deg;

	   if( deltaAZ_deg < 0.0 )  deltaAZ_deg += 360.0;
	                                                                               
       cal->cameratilt_deg = atan2( deltaEL_deg, deltaAZ_deg ) / deg2rad;

     
 	   ten_pixels_rad = SphericalAngularDistance_RADec( RAcenter, DECcenter, RA, DEC );

	   cal->arcminperpixel = (ten_pixels_rad / deg2rad) * 60.0 / 10.0;


	   Polycal_rowcol2std(cal, cal->midrow, cal->midcol + 10.0, &Xstd, &Ystd);

	   cal->plateroll_deg = atan2( -Ystd, Xstd ) / deg2rad;


	   //------------------------- Calculate the observed minus calculated

	   Polycal_ComputeOminusC( cal );


	   //--------------------- Free meeory and return

	   free(Q);
	   free(XYstd);
	   free(XYcoef);


       return(0);
       
} 


//#######################################################################
//  Obtain the inverse transform coefficients to go from standard to
//    focal plane row and column, based on the forward transform
//    polynomial calibration coefs.
//#######################################################################

void   Polycal_InversePolyCoefs(struct polycal_parameters *cal)
{
	int     kmeas, k, rowindex, colindex, ncoefs;
	double  col, row, Xstd, Ystd, Rstd;

#define   NHALF   25
#define   NSIDE   (2*NHALF+1)
#define   NSQ     (NSIDE*NSIDE)

	double    *xy;
	double    *XYinv;
	double   **Q;



	if      (cal->fitorder ==  1)  ncoefs = 3;
	else if (cal->fitorder ==  2)  ncoefs = 6;
	else if (cal->fitorder ==  3)  ncoefs = 10;
	else if (cal->fitorder ==  5)  ncoefs = 16;
	else if (cal->fitorder == 12)  ncoefs = 12;
	else if (cal->fitorder == 13)  ncoefs = 13;
	else {
		printf(" fitorder %i not implemented in Polycal_InversePolyCoefs\n", cal->fitorder);
		Delay_msec(10000);
		exit(1);
	}


	if (ncoefs > MAXCOEFS) {
		printf(" fitorder %i requires increasing MAXCOEFS in PolynomialAstrometryFitting to %i\n", cal->fitorder, ncoefs);
		Delay_msec(10000);
		exit(1);
	}

	//------------- Allocate memory for 1D and 2D arrays

	xy    = (double*)malloc( 2 * NSQ * sizeof(double));
	XYinv = (double*)malloc( 2 * ncoefs * sizeof(double));

	Q     = (double**)allocate_2d_array(NSQ, ncoefs, sizeof(double));


	//........... Fill the Q matrix of NSIDE * NSIDE measurements
	//            1  X  Y  X^2  XY  Y^2  X^3  X^2Y  XY^2  Y^3  ...

	kmeas = 0;

	for (colindex = 0; colindex<NSIDE; colindex++) {
		for (rowindex = 0; rowindex<NSIDE; rowindex++) {

			col = cal->midcol * (double)colindex / (double)NHALF;
			row = cal->midrow * (double)rowindex / (double)NHALF;

			xy[kmeas]       = col - ( cal->midcol + cal->Xcoef[0] );
			xy[kmeas + NSQ] = ( cal->midrow + cal->Ycoef[0] ) - row;

			Polycal_rowcol2std(cal, row, col, &Xstd, &Ystd);

			if (cal->fitorder >= 1) {
				Q[kmeas][0] = 1.0;
				Q[kmeas][1] = Xstd;
				Q[kmeas][2] = Ystd;
			}
			if (cal->fitorder >= 2) {
				Q[kmeas][3] = Xstd*Xstd;
				Q[kmeas][4] = Xstd*Ystd;
				Q[kmeas][5] = Ystd*Ystd;
			}
			if (cal->fitorder >= 3) {
				Q[kmeas][6] = Xstd*Xstd*Xstd;
				Q[kmeas][7] = Xstd*Xstd*Ystd;
				Q[kmeas][8] = Xstd*Ystd*Ystd;
				Q[kmeas][9] = Ystd*Ystd*Ystd;
			}
			if (cal->fitorder == 5) {
				Q[kmeas][10] = Xstd*Xstd*Xstd*Xstd*Xstd;
				Q[kmeas][11] = Xstd*Xstd*Xstd*Xstd*Ystd;
				Q[kmeas][12] = Xstd*Xstd*Xstd*Ystd*Ystd;
				Q[kmeas][13] = Xstd*Xstd*Ystd*Ystd*Ystd;
				Q[kmeas][14] = Xstd*Ystd*Ystd*Ystd*Ystd;
				Q[kmeas][15] = Ystd*Ystd*Ystd*Ystd*Ystd;
			}
			if (cal->fitorder == 12) {
				Rstd = sqrt(Xstd*Xstd + Ystd*Ystd);
				Q[kmeas][10] = Xstd*Rstd;
				Q[kmeas][11] = Ystd*Rstd;
			}
			if (cal->fitorder == 13) {
				Rstd = sqrt(Xstd*Xstd + Ystd*Ystd);
				Q[kmeas][10] = Rstd;
				Q[kmeas][11] = Xstd*Rstd;
				Q[kmeas][12] = Ystd*Rstd;
			}

			kmeas++;
		}
	}


	//............ Solve for inverse coefs

	LMSviaSVD(Q, xy, XYinv, NSQ, ncoefs, 2);


	for (k = 0; k<ncoefs; k++) {
		cal->Xinvcoef[k] = XYinv[k];
		cal->Yinvcoef[k] = XYinv[k + ncoefs];
	}


	cal->inverse_populated = 1;


	//-------- Free the memory

	free(xy);
	free(XYinv);
	free(Q);

}


//#######################################################################
//  Transform from focal plane row and column coordinates to standard 
//     (gnomic) coordinates following CAMS convention with the origin
//     in the upper left corner and row increases downwards and
//     column increases to the right.
//#######################################################################

void  Polycal_rowcol2std( struct polycal_parameters  *cal,
	                      double   row,    //...actual row and column number
	                      double   col,
	                      double  *Xstd,
	                      double  *Ystd)
{
	double x, y, r;


	//-------- Test if fitorder implemented

	if ( cal->fitorder < 1 || cal->fitorder == 4 || (cal->fitorder >= 6 && cal->fitorder <= 11) || cal->fitorder >= 14 ) {
		printf(" fitorder %i not implemented in Polycal_rowcol2std\n", cal->fitorder);
		Delay_msec(10000);
		exit(1);
	}



	//-------- Compute transform from row/col to standard

	x = col - ( cal->midcol + cal->Xcoef[0] );
	y = ( cal->midrow + cal->Ycoef[0] ) - row;

	*Xstd = 0.0;
	*Ystd = 0.0;


	if (cal->fitorder >= 1) {  //---- add in first order coefs

		*Xstd += cal->Xcoef[0]
			+ cal->Xcoef[1] * x
			+ cal->Xcoef[2] * y;
		*Ystd += cal->Ycoef[0]
			+ cal->Ycoef[1] * x
			+ cal->Ycoef[2] * y;
	}


	if (cal->fitorder >= 2) {  //---- add in second order coefs

		*Xstd += cal->Xcoef[3] * x * x
			+ cal->Xcoef[4] * x * y
			+ cal->Xcoef[5] * y * y;
		*Ystd += cal->Ycoef[3] * x * x
			+ cal->Ycoef[4] * x * y
			+ cal->Ycoef[5] * y * y;
	}


	if (cal->fitorder >= 3) {  //---- add in third order coefs

		*Xstd += cal->Xcoef[6] * x * x * x
			+ cal->Xcoef[7] * x * x * y
			+ cal->Xcoef[8] * x * y * y
			+ cal->Xcoef[9] * y * y * y;

		*Ystd += cal->Ycoef[6] * x * x * x
			+ cal->Ycoef[7] * x * x * y
			+ cal->Ycoef[8] * x * y * y
			+ cal->Ycoef[9] * y * y * y;
	}


	if (cal->fitorder == 5) {  //---- add in fifth order coefs

		*Xstd += cal->Xcoef[10] * x * x * x * x * x
			  +  cal->Xcoef[11] * x * x * x * x * y
			  +  cal->Xcoef[12] * x * x * x * y * y
			  +  cal->Xcoef[13] * x * x * y * y * y
		      +  cal->Xcoef[14] * x * y * y * y * y
			  +  cal->Xcoef[15] * y * y * y * y * y;

		*Ystd += cal->Ycoef[10] * x * x * x * x * x
		  	  +  cal->Ycoef[11] * x * x * x * x * y
			  +  cal->Ycoef[12] * x * x * x * y * y
			  +  cal->Ycoef[13] * x * x * y * y * y
		      +  cal->Ycoef[14] * x * y * y * y * y
			  +  cal->Ycoef[15] * y * y * y * y * y;
	}


	if (cal->fitorder == 12) {  //---- radial coefs

		r = sqrt(x*x + y*y);

		*Xstd += cal->Xcoef[10] * x * r
			+ cal->Xcoef[11] * y * r;

		*Ystd += cal->Ycoef[10] * x * r
			+ cal->Ycoef[11] * y * r;
	}


	if (cal->fitorder == 13) {  //---- radial coefs

		r = sqrt( x*x + y*y );

		*Xstd += cal->Xcoef[10] * r
			+ cal->Xcoef[11] * x * r
			+ cal->Xcoef[12] * y * r;

		*Ystd += cal->Ycoef[10] * r
			+ cal->Ycoef[11] * x * r
			+ cal->Ycoef[12] * y * r;
	}


}


//#######################################################################
//  Transform from standard (gnomic) coordinates to row and column
//     position in the focal plane following CAMS convention of the
//     origin in the upper left corner and row increases downwards and
//     column increases to the right.
//#######################################################################

void  Polycal_std2rowcol( struct polycal_parameters  *cal,
	                      double   Xstd,
	                      double   Ystd,
	                      double  *row,   //...actual row and column number
	                      double  *col)
{
	double x, y, Rstd;


	//-------- Test if fitorder implemented

	if ( cal->fitorder < 1 || cal->fitorder == 4 || (cal->fitorder >= 6 && cal->fitorder <= 11) || cal->fitorder >= 14 ) {
		printf(" fitorder %i not implemented in Polycal_std2rowcol\n", cal->fitorder);
		Delay_msec(10000);
		exit(1);
	}


	//-------- Compute the inverse coefs if not done already

	if (cal->inverse_populated != 1)  Polycal_InversePolyCoefs( cal );


	//-------- Compute the row/col given a position's standard coords

	x = 0.0;
	y = 0.0;


	if (cal->fitorder >= 1) {  //---- add in first order coefs

		x += cal->Xinvcoef[0]
			+ cal->Xinvcoef[1] * Xstd
			+ cal->Xinvcoef[2] * Ystd;
		y += cal->Yinvcoef[0]
			+ cal->Yinvcoef[1] * Xstd
			+ cal->Yinvcoef[2] * Ystd;
	}


	if (cal->fitorder >= 2) {  //---- add in second order coefs

		x += cal->Xinvcoef[3] * Xstd * Xstd
			+ cal->Xinvcoef[4] * Xstd * Ystd
			+ cal->Xinvcoef[5] * Ystd * Ystd;
		y += cal->Yinvcoef[3] * Xstd * Xstd
			+ cal->Yinvcoef[4] * Xstd * Ystd
			+ cal->Yinvcoef[5] * Ystd * Ystd;
	}


	if (cal->fitorder >= 3) {  //---- add in third order coefs

		x += cal->Xinvcoef[6] * Xstd * Xstd * Xstd
			+ cal->Xinvcoef[7] * Xstd * Xstd * Ystd
			+ cal->Xinvcoef[8] * Xstd * Ystd * Ystd
			+ cal->Xinvcoef[9] * Ystd * Ystd * Ystd;

		y += cal->Yinvcoef[6] * Xstd * Xstd * Xstd
			+ cal->Yinvcoef[7] * Xstd * Xstd * Ystd
			+ cal->Yinvcoef[8] * Xstd * Ystd * Ystd
			+ cal->Yinvcoef[9] * Ystd * Ystd * Ystd;
	}


	if (cal->fitorder == 5) {  //---- add in fifth order coefs

		x +=  cal->Xinvcoef[10] * Xstd * Xstd * Xstd * Xstd * Xstd
			+ cal->Xinvcoef[11] * Xstd * Xstd * Xstd * Xstd * Ystd
			+ cal->Xinvcoef[12] * Xstd * Xstd * Xstd * Ystd * Ystd
			+ cal->Xinvcoef[13] * Xstd * Xstd * Ystd * Ystd * Ystd
			+ cal->Xinvcoef[14] * Xstd * Ystd * Ystd * Ystd * Ystd
			+ cal->Xinvcoef[15] * Ystd * Ystd * Ystd * Ystd * Ystd;

		y +=  cal->Yinvcoef[10] * Xstd * Xstd * Xstd * Xstd * Xstd
		    + cal->Yinvcoef[11] * Xstd * Xstd * Xstd * Xstd * Ystd
			+ cal->Yinvcoef[12] * Xstd * Xstd * Xstd * Ystd * Ystd
			+ cal->Yinvcoef[13] * Xstd * Xstd * Ystd * Ystd * Ystd
			+ cal->Yinvcoef[14] * Xstd * Ystd * Ystd * Ystd * Ystd
			+ cal->Yinvcoef[15] * Ystd * Ystd * Ystd * Ystd * Ystd;
	}


	if (cal->fitorder == 12) {  //---- add in radial coefs

		Rstd = sqrt(Xstd * Xstd + Ystd * Ystd);

		x += cal->Xinvcoef[10] * Xstd * Rstd
			+ cal->Xinvcoef[11] * Ystd * Rstd;
		y += cal->Yinvcoef[10] * Xstd * Rstd
			+ cal->Yinvcoef[11] * Ystd * Rstd;
	}


	if (cal->fitorder == 13) {  //---- add in radial coefs

		Rstd = sqrt(Xstd * Xstd + Ystd * Ystd);

		x += cal->Xinvcoef[10] * Rstd
			+ cal->Xinvcoef[11] * Xstd * Rstd
			+ cal->Xinvcoef[12] * Ystd * Rstd;
		y += cal->Yinvcoef[10] * Rstd
			+ cal->Yinvcoef[11] * Xstd * Rstd
			+ cal->Yinvcoef[12] * Ystd * Rstd;
	}


	//======== Convert to row and column

	*col = x + ( cal->midcol + cal->Xcoef[0] );
	*row = ( cal->midrow + cal->Ycoef[0] ) - y;


}


//#######################################################################
//  Compute the observed minus catalog (O-C) residual mean, sigma, RMS
//#######################################################################

void   Polycal_ComputeOminusC( struct polycal_parameters *cal )
{
int     kthstar;
double  pi, deg2rad, RAcenter, DECcenter, RA, DEC, Xstd, Ystd;
double  oc_rad, oc_rad_sum, oc_rad_ssq, oc_mean, oc_sigma, oc_rms;


       //-------- Set image center in radians

       pi = 4.0 * atan(1.0);

	   deg2rad = pi / 180.0;

       RAcenter  = cal->RAcenter_deg  * deg2rad;
	   DECcenter = cal->DECcenter_deg * deg2rad;


	   //-------- Compute running sums of O-C

	   oc_rad_sum = 0.0;
	   oc_rad_ssq = 0.0;
	  
	   for( kthstar=0; kthstar<cal->ncalstars; kthstar++ )  {

		    //... find the observed minus calculated position

			Polycal_rowcol2std(  cal, 
				                 cal->starinfo[kthstar].rowcentroid, 
				                 cal->starinfo[kthstar].colcentroid, 
							     &Xstd, &Ystd );

            Standard_to_RADec( Xstd, Ystd, RAcenter, DECcenter, &RA, &DEC );

		    oc_rad = SphericalAngularDistance_RADec( RA, DEC, 
				                               cal->starinfo[kthstar].RA_deg  * deg2rad, 
									           cal->starinfo[kthstar].DEC_deg * deg2rad );

		    oc_rad_sum += oc_rad;
		    oc_rad_ssq += oc_rad * oc_rad;

			cal->starinfo[kthstar].oc_arcmin = oc_rad * 60.0 / deg2rad;
       } 

	   oc_mean  = oc_rad_sum / (double)cal->ncalstars;
	   oc_sigma = sqrt( (oc_rad_ssq - (double)cal->ncalstars * oc_mean * oc_mean) / (double)(cal->ncalstars-1) );
	   oc_rms   = sqrt( oc_rad_ssq / (double)cal->ncalstars );
                        
       cal->oc_mean_arcmin  = oc_mean  * 60.0 / deg2rad;
       cal->oc_sigma_arcmin = oc_sigma * 60.0 / deg2rad;
       cal->oc_rms_arcmin   = oc_rms   * 60.0 / deg2rad;

}


//#######################################################################
//  Set the calibration structure to uncalibrated settings if no
//     astrometric solution available
//#######################################################################

void  Polycal_SetUncalibrated( struct polycal_parameters *cal )
{
	struct DateAndTime  ut;


	strcpy(cal->CALnameonly, "UNCALIBRATED.txt");

	ut.year   = 2000;
	ut.month  = 1;
	ut.day    = 1;
	ut.hour   = 0;
	ut.minute = 0;
	ut.second = 0;
	ut.msec   = 0;

	cal->jdtcal        = JulianDateAndTime( &ut );
	cal->framerate_Hz  = 30.0;
	cal->RAcenter_deg  = 0.0;
	cal->DECcenter_deg = 90.0;    //90 deg ensures Moon never in FOV
	cal->longitude_deg = 0.0;
	cal->latitude_deg  = 0.0;
	cal->height_km     = 0.0;
	cal->midrow        = 1.0;
	cal->midcol        = 1.0;

	cal->arcminperpixel = 3.0;

	cal->fitorder = 1;
	cal->Xcoef[0] = 0.0;
	cal->Xcoef[1] = 0.0;
	cal->Xcoef[2] = 0.0;
	cal->Ycoef[0] = 0.0;
	cal->Ycoef[1] = 0.0;
	cal->Ycoef[2] = 0.0;

}



//#######################################################################
//   Read the standard CAMS calibration file depending on fit order and
//     place content into the calibration structure.
//#######################################################################


void  Polycal_ReadCALfile(char *filename, struct polycal_parameters *cal, struct camerasiteinfo *camsite)
{
	FILE  *calibfile;
	char   text[128];
	long   kthstar, kdummy;
	fpos_t file_position;

	struct DateAndTime  ut;


	//------------- open calibration file

	if ((calibfile = fopen(filename, "r")) == NULL) {
		printf(" Cannot open calibration file %s for reading \n", filename);
		Delay_msec(10000);
		exit(1);
	}


	//------------- read some header info

	strcpy(cal->CALpathname, filename);

	if (strstr(filename, "CAL_") == NULL) {  // 30 characters from CAL to .txt      	  
		strncpy(cal->CALnameonly, strrchr(filename, 67), 30);
		cal->CALnameonly[30] = '\0';
	}

	else {                                   // 34 characters from CAL to .txt     	  
		strncpy(cal->CALnameonly, strrchr(filename, 67), 34);
		cal->CALnameonly[34] = '\0';
	}

	fscanf(calibfile, "%[^=]= %d", text, &cal->cameranumber);
	fscanf(calibfile, "%[^=]= %2d/%2d/%4d", text, &ut.month, &ut.day, &ut.year);
	fscanf(calibfile, "%[^=]= %2d:%2d:%2d.%3d", text, &ut.hour, &ut.minute, &ut.second, &ut.msec);
	cal->jdtcal = JulianDateAndTime(&ut);
	fscanf(calibfile, "%[^=]= %lf", text, &cal->longitude_deg); // +west
	fscanf(calibfile, "%[^=]= %lf", text, &cal->latitude_deg);  // geodetic
	fscanf(calibfile, "%[^=]= %lf", text, &cal->height_km);     // above WGS84
	fscanf(calibfile, "%[^=]= %lf x %lf", text, &cal->fovheight_deg, &cal->fovwidth_deg);
	fscanf(calibfile, "%[^=]= %lf", text, &cal->arcminperpixel);
	fscanf(calibfile, "%[^=]= %lf", text, &cal->plateroll_deg);
	fscanf(calibfile, "%[^=]= %lf", text, &cal->cameratilt_deg);
	fscanf(calibfile, "%[^=]= %lf", text, &cal->framerate_Hz);
	fscanf(calibfile, "%[^=]= %lf", text, &cal->RAcenter_deg);
	fscanf(calibfile, "%[^=]= %lf", text, &cal->DECcenter_deg);
	fscanf(calibfile, "%[^=]= %lf", text, &cal->AZcenter_deg);
	fscanf(calibfile, "%[^=]= %lf", text, &cal->ELcenter_deg);
	fscanf(calibfile, "%[^=]= %lf", text, &cal->midcol);
	fscanf(calibfile, "%[^=]= %lf", text, &cal->midrow);
	fscanf(calibfile, "%[^=]= %2d\n", text, &cal->fitorder);


	//-------------- read the camera specs

	camsite->latitude     = cal->latitude_deg  / 57.29577951;  // radians in WGS84 (geodetic latitude)
	camsite->longitude    = cal->longitude_deg / 57.29577951;  // radians +west
	camsite->height_km    = cal->height_km;                    // km in WGS84
	camsite->framerate_Hz = cal->framerate_Hz;                 // Hz
	camsite->cameranumber = cal->cameranumber;

	strcpy(camsite->station_name, "XX"); //not in header - see camerasites.txt file
	strcpy(camsite->station_ext, "XX");  //not in header - see camerasites.txt file

	fscanf(calibfile, "%[^=]= %[^\n]\n", text, camsite->cameradesc);
	fscanf(calibfile, "%[^=]= %[^\n]\n", text, camsite->lensdesc);
	fscanf(calibfile, "%[^=]= %lf", text, &camsite->focallength_mm);
	fscanf(calibfile, "%[^=]= %lf", text, &camsite->focalratio);
	fscanf(calibfile, "%[^=]= %lf", text, &camsite->pixelpitchH_um);
	fscanf(calibfile, "%[^=]= %lf", text, &camsite->pixelpitchV_um);
	fscanf(calibfile, "%[^=]= %lf", text, &camsite->specB);
	fscanf(calibfile, "%[^=]= %lf", text, &camsite->specV);
	fscanf(calibfile, "%[^=]= %lf", text, &camsite->specR);
	fscanf(calibfile, "%[^=]= %lf", text, &camsite->specI);
	fscanf(calibfile, "%[^=]= %lf", text, &camsite->vignette_coef);
	fscanf(calibfile, "%[^=]= %lf\n", text, &camsite->gamma);


	//-------------- read the calibration coefficients

	fscanf(calibfile, "%[^\n]\n", text);
	fscanf(calibfile, "%[^\n]\n", text);
	fscanf(calibfile, "%[^\n]\n", text);
	fscanf(calibfile, "%[^\n]\n", text);
	fscanf(calibfile, "%[^\n]\n", text);

	if (cal->fitorder >= 1) {
		fscanf(calibfile, " 1   %le%le", &cal->Xcoef[0], &cal->Ycoef[0]);
		fscanf(calibfile, " x   %le%le", &cal->Xcoef[1], &cal->Ycoef[1]);
		fscanf(calibfile, " y   %le%le", &cal->Xcoef[2], &cal->Ycoef[2]);
	}

	if (cal->fitorder >= 2) {
		fscanf(calibfile, " xx  %le%le", &cal->Xcoef[3], &cal->Ycoef[3]);
		fscanf(calibfile, " xy  %le%le", &cal->Xcoef[4], &cal->Ycoef[4]);
		fscanf(calibfile, " yy  %le%le", &cal->Xcoef[5], &cal->Ycoef[5]);
	}

	if (cal->fitorder >= 3) {
		fscanf(calibfile, " xxx %le%le", &cal->Xcoef[6], &cal->Ycoef[6]);
		fscanf(calibfile, " xxy %le%le", &cal->Xcoef[7], &cal->Ycoef[7]);
		fscanf(calibfile, " xyy %le%le", &cal->Xcoef[8], &cal->Ycoef[8]);
		fscanf(calibfile, " yyy %le%le", &cal->Xcoef[9], &cal->Ycoef[9]);
	}

	if (cal->fitorder == 5) {
		fscanf(calibfile, "x5   %le%le", &cal->Xcoef[10], &cal->Ycoef[10]);
		fscanf(calibfile, "x4y  %le%le", &cal->Xcoef[11], &cal->Ycoef[11]);
		fscanf(calibfile, "x3y2 %le%le", &cal->Xcoef[12], &cal->Ycoef[12]);
		fscanf(calibfile, "x2y3 %le%le", &cal->Xcoef[13], &cal->Ycoef[13]);
		fscanf(calibfile, "xy4  %le%le", &cal->Xcoef[14], &cal->Ycoef[14]);
		fscanf(calibfile, "y5   %le%le", &cal->Xcoef[15], &cal->Ycoef[15]);
	}

	if (cal->fitorder == 12) {
		fscanf(calibfile, " xr  %le%le", &cal->Xcoef[11], &cal->Ycoef[11]);
		fscanf(calibfile, " yr  %le%le", &cal->Xcoef[12], &cal->Ycoef[12]);
	}

	if (cal->fitorder == 13) {
		fscanf(calibfile, " r   %le%le", &cal->Xcoef[10], &cal->Ycoef[10]);
		fscanf(calibfile, " xr  %le%le", &cal->Xcoef[11], &cal->Ycoef[11]);
		fscanf(calibfile, " yr  %le%le", &cal->Xcoef[12], &cal->Ycoef[12]);
	}

	if ( cal->fitorder < 1 || (cal->fitorder >= 4 && cal->fitorder <= 11) || cal->fitorder >= 14 ) {
		printf(" fitorder %i is not implemented in ReadCALfile\n", cal->fitorder);
		Delay_msec(10000);
		exit(1);
	}


	//-------------- read the O-C values

	fscanf(calibfile, "%[^\n]\n\n", text);
	fscanf(calibfile, "%[^=]= %lf +-%lf arcmin\n\n", text, &cal->oc_mean_arcmin, &cal->oc_sigma_arcmin);


	//-------------- read the calibration star info

	fscanf(calibfile, "%[^\n]\n", text);
	fscanf(calibfile, "%[^=]= %lf", text, &cal->magicept);
	fscanf(calibfile, "%[^=]= %lf", text, &cal->magslope);
	fscanf(calibfile, "%[^\n]\n", text);
	fscanf(calibfile, "%[^\n]\n", text);
	fscanf(calibfile, "%[^=]= %lf", text, &cal->magiceptFlux);
	fscanf(calibfile, "%[^=]= %lf", text, &cal->magslopeFlux);
	fscanf(calibfile, "%[^\n]\n", text);
	fscanf(calibfile, "%[^\n]\n", text);
	fscanf(calibfile, "%[^\n]\n", text);
	fscanf(calibfile, "%[^\n]\n", text);


	fgetpos(calibfile, &file_position);

	kthstar = 0;

	while (feof(calibfile) == 0) {

		fscanf(calibfile, "%[^\n]\n", text );

		kthstar++;

	}

	cal->ncalstars = kthstar;

	////printf("Number cal stars %i\n", cal->ncalstars);


	Polycal_AllocMemory( cal, cal->ncalstars);


	fsetpos(calibfile, &file_position);

	kthstar = 0;

	while (feof(calibfile) == 0) {

		fscanf(calibfile, "%li%lf%lf%lf%lf%lf%lf%lf%lf%lf%lf%lf%lf",
			&kdummy,
			&cal->starinfo[kthstar].RA_deg,
			&cal->starinfo[kthstar].DEC_deg,
			&cal->starinfo[kthstar].rowcentroid,
			&cal->starinfo[kthstar].colcentroid,
			&cal->starinfo[kthstar].vmag,
			&cal->starinfo[kthstar].bvmag,
			&cal->starinfo[kthstar].rmag,
			&cal->starinfo[kthstar].imag,
			&cal->starinfo[kthstar].logintensity,
			&cal->starinfo[kthstar].logvignette,
			&cal->starinfo[kthstar].logflux,
			&cal->starinfo[kthstar].oc_arcmin);

		kthstar++;

		if (kthstar >= cal->ncalstars)  break;

	}

	cal->ncalstars = kthstar;

	fclose(calibfile);


	Polycal_InversePolyCoefs( cal );


}


//#######################################################################
//   Write the standard CAMS calibration file depending on fit order
//     using content from the calibration structure.
//#######################################################################

void  Polycal_WriteCALfile( char *calfolder, struct polycal_parameters *cal, struct camerasiteinfo *camsite )
{
long  kthstar;
char  calpathname[256];
FILE  *calibfile;        

struct DateAndTime  ut;

                           
      //------------- open calibration output file

      strcpy( calpathname, calfolder );

	  EndsInSlash( calpathname );

	  strcat( calpathname, cal->CALnameonly );
      
      strcpy( cal->CALpathname, calpathname );

     
      if( (calibfile= fopen( calpathname, "w")) == NULL )  {
           printf(" Cannot open calibration file %s for writing \n", calpathname );
		   Delay_msec(10000);
           exit(1);
      }


      //------------- write some header info

	  Calendar_DateAndTime(cal->jdtcal, &ut);
      
      fprintf(calibfile," Camera number            = %i\n", cal->cameranumber );
      fprintf(calibfile," Calibration date         = %02i/%02i/%04i\n", ut.month, ut.day, ut.year );
	  fprintf(calibfile," Calibration time (UT)    = %02i:%02i:%02i.%03i\n", ut.hour, ut.minute, ut.second, ut.msec );
      fprintf(calibfile," Longitude +west (deg)    = %10.5lf\n", camsite->longitude * 57.29577951 );
      fprintf(calibfile," Latitude +north (deg)    = %10.5lf\n", camsite->latitude  * 57.29577951 );
      fprintf(calibfile," Height above WGS84 (km)  = %10.5lf\n", camsite->height_km );
      fprintf(calibfile," FOV dimension hxw (deg)  = %6.1f x %6.1f\n", 
                                                     (float)cal->fovheight_deg,
                                                     (float)cal->fovwidth_deg );                              
      fprintf(calibfile," Plate scale (arcmin/pix) = %8.3f\n", (float)cal->arcminperpixel ); 
      fprintf(calibfile," Plate roll wrt Std (deg) = %8.3f\n", (float)cal->plateroll_deg  );
      fprintf(calibfile," Cam tilt wrt Horiz (deg) = %8.3f\n", (float)cal->cameratilt_deg );
      fprintf(calibfile," Frame rate (Hz)          = %8.3f\n", (float)cal->framerate_Hz   ); 
      fprintf(calibfile," Cal center RA (deg)      = %8.3f\n", (float)cal->RAcenter_deg   );
      fprintf(calibfile," Cal center Dec (deg)     = %8.3f\n", (float)cal->DECcenter_deg  );
      fprintf(calibfile," Cal center Azim (deg)    = %8.3f\n", (float)cal->AZcenter_deg   );
      fprintf(calibfile," Cal center Elev (deg)    = %8.3f\n", (float)cal->ELcenter_deg   );
      fprintf(calibfile," Cal center col (colcen)  = %8.3f\n", (float)cal->midcol         );
      fprintf(calibfile," Cal center row (rowcen)  = %8.3f\n", (float)cal->midrow         );
	  fprintf(calibfile," Cal fit order            = %02i\n\n",  (int)cal->fitorder       );

      fprintf(calibfile," Camera description       = %s\n",           camsite->cameradesc      );
      fprintf(calibfile," Lens description         = %s\n",           camsite->lensdesc        );
      fprintf(calibfile," Focal length (mm)        = %8.3f\n", (float)camsite->focallength_mm  );
      fprintf(calibfile," Focal ratio              = %8.3f\n", (float)camsite->focalratio      );
      fprintf(calibfile," Pixel pitch H (um)       = %8.3f\n", (float)camsite->pixelpitchH_um  );
      fprintf(calibfile," Pixel pitch V (um)       = %8.3f\n", (float)camsite->pixelpitchV_um  );
      fprintf(calibfile," Spectral response B      = %8.3f\n", (float)camsite->specB  );
      fprintf(calibfile," Spectral response V      = %8.3f\n", (float)camsite->specV  );
      fprintf(calibfile," Spectral response R      = %8.3f\n", (float)camsite->specR  );
      fprintf(calibfile," Spectral response I      = %8.3f\n", (float)camsite->specI  );
      fprintf(calibfile," Vignetting coef(deg/pix) = %8.3f\n", (float)camsite->vignette_coef  );
      fprintf(calibfile," Gamma                    = %8.3f\n\n", (float)camsite->gamma        );


	  //-------------- write the calibration cubic fit coefficients

	  fprintf(calibfile," Xstd, Ystd = Polyxy2Standard( col, row, colcen, rowcen, Xcoef, Ycoef )\n");
	  fprintf(calibfile," x = col - colcen\n");
	  fprintf(calibfile," y = rowcen - row\n\n");
	  fprintf(calibfile," Term       Xcoef            Ycoef     \n");
	  fprintf(calibfile," ----  ---------------  ---------------\n");  

      
	  if( cal->fitorder >= 1 )  {
	      fprintf(calibfile," 1    %15.6e  %15.6e \n", cal->Xcoef[0], cal->Ycoef[0] );
	      fprintf(calibfile," x    %15.6e  %15.6e \n", cal->Xcoef[1], cal->Ycoef[1] );
	      fprintf(calibfile," y    %15.6e  %15.6e \n", cal->Xcoef[2], cal->Ycoef[2] );
	  }

	  if( cal->fitorder >= 2 )  {
		  fprintf(calibfile," xx   %15.6e  %15.6e \n", cal->Xcoef[3], cal->Ycoef[3] );
	      fprintf(calibfile," xy   %15.6e  %15.6e \n", cal->Xcoef[4], cal->Ycoef[4] );
	      fprintf(calibfile," yy   %15.6e  %15.6e \n", cal->Xcoef[5], cal->Ycoef[5] );
	  }

	  if (cal->fitorder >= 3) {
		  fprintf(calibfile, " xxx  %15.6e  %15.6e \n", cal->Xcoef[6], cal->Ycoef[6]);
		  fprintf(calibfile, " xxy  %15.6e  %15.6e \n", cal->Xcoef[7], cal->Ycoef[7]);
		  fprintf(calibfile, " xyy  %15.6e  %15.6e \n", cal->Xcoef[8], cal->Ycoef[8]);
		  fprintf(calibfile, " yyy  %15.6e  %15.6e \n", cal->Xcoef[9], cal->Ycoef[9]);
	  }

	  if (cal->fitorder == 5) {
		  fprintf(calibfile, "x5    %15.6e  %15.6e \n", cal->Xcoef[10], cal->Ycoef[10]);
		  fprintf(calibfile, "x4y   %15.6e  %15.6e \n", cal->Xcoef[11], cal->Ycoef[11]);
		  fprintf(calibfile, "x3y2  %15.6e  %15.6e \n", cal->Xcoef[12], cal->Ycoef[12]);
		  fprintf(calibfile, "x2y3  %15.6e  %15.6e \n", cal->Xcoef[13], cal->Ycoef[13]);
		  fprintf(calibfile, "xy4   %15.6e  %15.6e \n", cal->Xcoef[14], cal->Ycoef[14]);
		  fprintf(calibfile, "y5    %15.6e  %15.6e \n", cal->Xcoef[15], cal->Ycoef[15]);
	  }

	  if (cal->fitorder == 12) {
		  fprintf(calibfile, " xr   %15.6e  %15.6e \n", cal->Xcoef[11], cal->Ycoef[11]);
		  fprintf(calibfile, " yr   %15.6e  %15.6e \n", cal->Xcoef[12], cal->Ycoef[12]);
	  }

	  if (cal->fitorder == 13) {
		  fprintf(calibfile, " r    %15.6e  %15.6e \n", cal->Xcoef[10], cal->Ycoef[10]);
		  fprintf(calibfile, " xr   %15.6e  %15.6e \n", cal->Xcoef[11], cal->Ycoef[11]);
		  fprintf(calibfile, " yr   %15.6e  %15.6e \n", cal->Xcoef[12], cal->Ycoef[12]);
	  }

	  fprintf(calibfile," ----  ---------------  ---------------\n");
      fprintf(calibfile,"\n Mean O-C = %7.3f +- %7.3f arcmin\n\n", cal->oc_mean_arcmin, cal->oc_sigma_arcmin  );
 
      //-------------- write the calibration star info
      
      fprintf(calibfile," Magnitude = A + B (logI-logVig)   fit mV vs. -2.5 (logI-logVig),   B-V < %5.2f, mV < %5.2f\n", (float)cal->bvlimit, (float)cal->Vmaglimit );
      fprintf(calibfile,"         A = %7.2lf \n",   cal->magicept );
      fprintf(calibfile,"         B = %7.2lf \n\n", cal->magslope );
                                                
      fprintf(calibfile," Magnitude = -2.5 ( C + D (logI-logVig) )   fit logFlux vs. Gamma (logI-logVig), mV < %5.2f\n", (float)cal->Vmaglimit );
      fprintf(calibfile,"         C = %7.2lf \n",   cal->magiceptFlux );
      fprintf(calibfile,"         D = %7.2lf \n\n", cal->magslopeFlux );

	  fprintf(calibfile," logVig = log( cos( Vignetting_coef * Rpixels * pi/180 )^4 )\n\n\n" );


	  //-------------- write the calibration star spctral class used
      
      fprintf(calibfile," Star    RA (deg)  DEC (deg)    row      col       V      B-V      R      IR    logInt  logVig  logFlux  O-C arcmin \n");
      fprintf(calibfile," ----   ---------  ---------  -------  -------  ------  ------  ------  ------  ------  ------  -------  ---------- \n");
      
	  for( kthstar=0; kthstar<cal->ncalstars; kthstar++ )  {

           fprintf(calibfile,"  %3li   %9.5f  %9.5f  %7.2f  %7.2f  %6.2f  %6.2f  %6.2f  %6.2f  %6.3f  %6.3f  %7.3f  %7.3f\n",
                   kthstar+1L,
                   cal->starinfo[kthstar].RA_deg,
                   cal->starinfo[kthstar].DEC_deg,
                   cal->starinfo[kthstar].rowcentroid,
                   cal->starinfo[kthstar].colcentroid,
                   cal->starinfo[kthstar].vmag,
                   cal->starinfo[kthstar].bvmag,
                   cal->starinfo[kthstar].rmag,
                   cal->starinfo[kthstar].imag,
                   cal->starinfo[kthstar].logintensity,
                   cal->starinfo[kthstar].logvignette,
                   cal->starinfo[kthstar].logflux,
				   cal->starinfo[kthstar].oc_arcmin  );
      } 
                        
      fclose( calibfile );


}


//#######################################################################
/*
* Perform a singular value decomposition A = USV' of a nxn square matrix.
*
*    SVD_SquareMatrix( &A[0][0], &US[0][0], &S2[0], &V[0][0], n, maxn );
*
* This routine has been adapted with permission from a Pascal implementation
* (c) 1988 J. C. Nash, "Compact numerical methods for computers", Hilger 1990.
* The A, US and V matrices must all be dimensioned to the same column dimension
* of maxn and minimal row dimension of n. The matrix to be decomposed is 
* assumed contained in the first n rows of A. On return, the "US" matrix
* contains the product U times the diagonal singular vector S, while the "V"  
* matrix contains V (not V' = V transpose). The "S2" vector returns a vector 
* containing the square of the singular values S^2. Note that U and V are
* unitary matrices.
*
* To obtain the Penrose pseudo-inverse  A^-1 = V S2^-1 US'     ' = transpose
*
* To solve A x = b;
*
*      x = V S2^-1 US' b   using only significant S2(k) singular values
*
*  (c) Copyright 1996 by Carl Edward Rasmussen. */
//#######################################################################

//#include <stdio.h>
//#include <math.h>

void SVD_SquareMatrix(double *A, double *US, double *S2, double *V, int n, int maxn)
{
	int     i, j, k, EstColRank = n, RotCount = n;
	int     SweepCount = 0, slimit = (n<120) ? 30 : n / 4;
	double  eps = 1e-15, e2 = 10.0*n*eps*eps, tol = 0.1*eps;
	double  vt, p, x0, y0, q, r, c0, s0, d1, d2;

	for (i = 0; i<n; i++) {
		for (j = 0; j<n; j++)  *(US + i*maxn + j) = *(A + i*maxn + j);
	}

	for (i = 0; i<n; i++) {
		for (j = 0; j<n; j++)  *(V + i*maxn + j) = 0.0;  
		*(V + i*maxn + i) = 1.0;
	}

	while (RotCount != 0 && SweepCount++ <= slimit) {

		RotCount = EstColRank*(EstColRank - 1) / 2;

		for (j = 0; j<EstColRank - 1; j++)

			for (k = j + 1; k<EstColRank; k++) {
				p = 0.0;
				q = 0.0;
				r = 0.0;
				for (i = 0; i<n; i++) {
					x0 = *(US + i*maxn + j);
					y0 = *(US + i*maxn + k);
					p += x0*y0;
					q += x0*x0;
					r += y0*y0;
				}
				S2[j] = q; 
				S2[k] = r;

				if (q >= r) {
					if (q <= e2*S2[0] || fabs(p) <= tol*q)
						RotCount--;
					else {
						p /= q;
						r = 1.0 - r / q;
						vt = sqrt(4.0*p*p + r*r);
						c0 = sqrt(0.5*(1.0 + r / vt));
						s0 = p / (vt*c0);
						for (i = 0; i<n; i++) {
							d1 = *(US + i*maxn + j);
							d2 = *(US + i*maxn + k);
							*(US + i*maxn + j) = +d1*c0 + d2*s0;
							*(US + i*maxn + k) = -d1*s0 + d2*c0;
						}
						for (i = 0; i<n; i++) {
							d1 = *(V + i*maxn + j);
							d2 = *(V + i*maxn + k);
							*(V + i*maxn + j) = +d1*c0 + d2*s0;
							*(V + i*maxn + k) = -d1*s0 + d2*c0;
						}
					}
				}

				else {
					p /= r;
					q = q / r - 1.0;
					vt = sqrt(4.0*p*p + q*q);
					s0 = sqrt(0.5*(1.0 - q / vt));
					if (p<0.0) s0 = -s0;
					c0 = p / (vt*s0);
					for (i = 0; i<n; i++) {
						d1 = *(US + i*maxn + j);
						d2 = *(US + i*maxn + k);
						*(US + i*maxn + j) = +d1*c0 + d2*s0;
						*(US + i*maxn + k) = -d1*s0 + d2*c0;
					}
					for (i = 0; i<n; i++) {
						d1 = *(V + i*maxn + j);
						d2 = *(V + i*maxn + k);
						*(V + i*maxn + j) = +d1*c0 + d2*s0;
						*(V + i*maxn + k) = -d1*s0 + d2*c0;
					}

				} //... end if (q >= r) else

			} //... end k loop

		while (EstColRank>2 && S2[EstColRank - 1] <= S2[0] * tol + tol*tol) EstColRank--;

	} //... end of RotCount and SweepCount while loop

	if (SweepCount > slimit)
		printf("Warning: Reached maximum number of sweeps (%i) in SVD routine...\n", slimit);

}

//################################################################################
/*
*   Solve the overdetermined least mean squares equation  Q x = b  by performing
*   a singular value decomposition as follows:
*  
*         x  =  (Qt Q)^-1 Qt b  =  V S^-2 USt Qt b
*
*  such that  Qt Q = U S Vt  and t = transpose
*
*  Q is a 2D matrix of dimensions nmeas x ncoef
*  b is a input vector of length nmeas * nrhs (stacked for "nrhs" right hand sides)
*  x is a solution vector of length ncoef * nrhs (stacked for "nrhs" solutions)
*  nmeas = number of measurments >= ncoefs
*  ncoefs = number of coefficients to solve for in an LMS sense
*  nrhs = number of right hand sides
*
*  Pete Gural   19-Aug-2018   */
//================================================================================

void  LMSviaSVD( double **Q, double *b, double *x, int nmeas, int ncoefs, int nrhs )
{
	int       kmeas, jcoef, kcoef, krhs, jstart, kstart;
	double    sum, cmax;

	double  **QtQ;
	double  **US;
	double  **V;

	double   *Qtb;
	double   *Ssq;      // squared singular values
	double   *SsqinvUSQtb;
	double   *scale;


    //======== Test dimensions

	if (nmeas < ncoefs) {
		printf("ERROR in LMSviaSVD where #meas = %i < #coef = %i\n", nmeas, ncoefs);
		Delay_msec(15000);
		exit(1);
	}

	//======== Allocate working memory

	QtQ = (double**)allocate_2d_array(ncoefs, ncoefs, sizeof(double));
	US  = (double**)allocate_2d_array(ncoefs, ncoefs, sizeof(double));
	V   = (double**)allocate_2d_array(ncoefs, ncoefs, sizeof(double));

	Qtb         = (double*)malloc(ncoefs * sizeof(double));
	Ssq         = (double*)malloc(ncoefs * sizeof(double));
	SsqinvUSQtb = (double*)malloc(ncoefs * sizeof(double));
	scale       = (double*)malloc(ncoefs * sizeof(double));


	//======== Compute the scaling factors to scale columns of Q

	for (kcoef = 0; kcoef < ncoefs; kcoef++) {

		cmax = 0.0;

		for (kmeas = 0; kmeas < nmeas; kmeas++) {
			if (fabs(Q[kmeas][kcoef]) > cmax)  cmax = fabs(Q[kmeas][kcoef]);
		}

		if (cmax == 0.0)  cmax = 1.0;

		scale[kcoef] = 1.0 / cmax;

	}


	//======== Compute Q-transpose * Q

	for (jcoef = 0; jcoef<ncoefs; jcoef++) {

		for (kcoef = 0; kcoef<ncoefs; kcoef++) {

			sum = 0.0;

			for (kmeas = 0; kmeas<nmeas; kmeas++)  sum += Q[kmeas][jcoef] * Q[kmeas][kcoef];

			QtQ[jcoef][kcoef] = sum * scale[jcoef] * scale[kcoef];

		}
	}


	//======== Compute SVD of Q-transpose * Q = USV'

	SVD_SquareMatrix( &QtQ[0][0], &US[0][0], &Ssq[0], &V[0][0], ncoefs, ncoefs );


	//======== Solve each right hand side

	for (krhs = 0; krhs < nrhs; krhs++) {

		kstart = krhs * nmeas;


		//-------- Compute Q-transpose * b

		for (kcoef = 0; kcoef < ncoefs; kcoef++) {

			sum = 0.0;

			for (kmeas = 0; kmeas < nmeas; kmeas++)  sum += Q[kmeas][kcoef] * b[kstart + kmeas];

			Qtb[kcoef] = sum * scale[kcoef];

		}


		//-------- Compute  US' * (Qt * b) and check for singular values

		for (kcoef = 0; kcoef < ncoefs; kcoef++) {

			sum = 0.0;

			for (jcoef = 0; jcoef < ncoefs; jcoef++)  sum += US[jcoef][kcoef] * Qtb[jcoef];

			if (Ssq[kcoef] > 0.0)  SsqinvUSQtb[kcoef] = sum / Ssq[kcoef];
			else                   SsqinvUSQtb[kcoef] = 0.0;
		}


		//-------- Obtain solution = V * S^-2 * USt * (Qt * b)

		for (jcoef = 0; jcoef < ncoefs; jcoef++) {

			jstart = krhs * ncoefs;

			sum = 0.0;

			for (kcoef = 0; kcoef < ncoefs; kcoef++)  sum += V[jcoef][kcoef] * SsqinvUSQtb[kcoef];

			x[jstart + jcoef] = sum * scale[jcoef];

		}


	} //... end of right hand side solution loop


    //======== Free work memory

	free(QtQ);
	free(US);
	free(V);

	free(Qtb);
	free(Ssq);
	free(SsqinvUSQtb);
	free(scale);

}
