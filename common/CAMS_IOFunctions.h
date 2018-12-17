//#########################################################################################
//  CAMS Input/Output Functionality for files of type FF, Detectinfo, Cal, MP4, Logs
//     in Windows and Linux (TBD) versions.
//
//  ---------------------------------------------------------------------------------------
//  Ver   Date        Author       Description
//  ----  ----------  -----------  ---------------------------------------------------------
//  1.00  2018-04-18  Gural        Original implementation
//
//#########################################################################################

#ifdef _WIN32
    #include <Shlobj.h>
#endif


#define  MAXSEGMENTS   128
#define  NLOGFILES       5

FILE    *FTPlogfile[NLOGFILES];
int      trackcount[NLOGFILES];


//=========================================================================================
//========   Structure and function prototypes for camera sites and event tracks   ========
//=========================================================================================

#include <string.h>
#include <sys/stat.h>
#include <sys/time.h>

struct  camerasiteinfo
{
	long               cameranumber;
	double             latitude;        // WGS84 geodetic latitude in radians
	double             longitude;       // WGS84 longitude in radians (+west)
	double             height_km;       // Height in km above WGS84 ellipsoid
	double             framerate_Hz;    // Camera frame rate in Hz
	double             deltat;          // Time offset in seconds
	char               station_name[256];
	char               station_ext[4];  // 2 or 3 letter station code

	char               cameradesc[128]; // Descriptive name of camera
	char               lensdesc[128];   // Description of lens
	double             focallength_mm;  // Lens focal length in mm
	double             focalratio;      // Lens focal ratio
	double             pixelpitchH_um;  // Sensor horizontal pixel pitch (microns)
	double             pixelpitchV_um;  // Sensor vertical pixel pitch (microns)
	double             specB;           // Sensor spectral reponses in B, V, R, I
	double             specV;           //   normalized such that their sum = 1
	double             specR;
	double             specI;
	double             vignette_coef;   // Lens vignetting in degrees/pixel
										//    such that cos^4(vig*R(pixels)*pi/180)
	double             gamma;           // Sensor gamma setting
};


struct  trackseqinfo
{
	char      proc_filename[256];
	char      cal_filename[256];
	long      cameranumber;
	long      meteornumber;
	long      nsegments;
	double    framerate;  //fps
	double    hnr;
	double    mle;
	double    bin;
	double    halfdeltad;
	double    houghrho;   //pixels
	double    houghphi;   //deg 
	double    framenumber[MAXSEGMENTS];
	double    colcentroid[MAXSEGMENTS];
	double    rowcentroid[MAXSEGMENTS];
	double    RA_deg[MAXSEGMENTS];
	double    DEC_deg[MAXSEGMENTS];
	double    AZ_deg[MAXSEGMENTS];   //...+east of north   
	double    EL_deg[MAXSEGMENTS];
	long      integratedcount[MAXSEGMENTS];

};


//-----------------------------------------------------------------------------------------

int  GenerateExtensionBasedFileListing(char *folder_pathname, char *extension, char *listing_pathname);

void        GetCAMSbaselineFolder( char *camsbaseline_folder );

void          ReadSiteInfo4Camera( long                        cameranumber,
	                               char                       *sitesfilename,
	                               struct camerasiteinfo      *camerasite );

FILE*          OpenSummaryLogFile( char                *detectionlog_pathname,
	                               char                *captured_folder,
	                               struct DateAndTime   ut,
	                               int                  daynight_integMode,
	                               double               version,
	                               double               jdt_start,
	                               double               jdt_stop,
	                               struct DateAndTime   folder_ut );


int             OpenFTPdetectinfo( int                  kthlogfile,
	                               char                *filename,
	                               char                *capturedfolder_pathname,
	                               char                *calibrationfolder_pathname,
	                               double               version) ;

void           WriteFTPdetectinfo( int                  kthlogfile,
	                               struct trackseqinfo *track );

void           CloseFTPdetectinfo( int                  kthlogfile);


void   GetFF_File(char* ff_file, long ff_file_dim);

void   GetFF_Folder(char* ff_folder, long ff_folder_dim);

void   GetFF_Folder_UsingLastFolder(char *ff_folder_last, char* ff_folder, long ff_folder_dim);

void   GetCAL_Folder(char* cal_folder, long cal_folder_dim);

void   GetMP4_File(char* mp4_pathanme);

void   GetMP4_Folder(char* mp4_folder);

void   GetFTPMeteorFilename(char* ftp_file, long ftp_file_dim);

void   GetMeteorLogPathname(char* ftp_file, long ftp_file_dim);

int    GetMostRecentFile(char *folder_pathname, char *file_firstpart, double jdtlast, char *latest_filename);


//#########################################################################################

//=========================================================================================
//    Get the directory listing of all the *.xxx files in the user
//    specified folder and pipe it to a text file "listing_pathname".
//    The extension xxx can be bin, vid, fits, mp4, ...
//=========================================================================================

int  GenerateExtensionBasedFileListing(char *folder_pathname, char *extension, char *listing_pathname)
{

#ifdef _WIN32 /************* WINDOWS *******************************************/

	char    windows_system_command[512];

	sprintf(windows_system_command, "dir /b \"%s*.%s\" > \"%s\"", folder_pathname, extension, listing_pathname);

	system(windows_system_command);

	return(0);


#else /********************** LINUX *******************************************/

	struct dirent *entry;
	DIR           *directoryfolder;
	FILE          *filelisting;
	char           dot_extension[25];

        char          png_file[256];

	if ((filelisting = fopen(listing_pathname, "w")) == NULL) {
		fprintf(stdout, "ERROR ===> FITS file directory listing %s cannot be open for write\n\n", listing_pathname);
		fprintf(stderr, "ERROR ===> FITS file directory listing %s cannot be open for write\n\n", listing_pathname);
		return(1);
	}

	if ((directoryfolder = opendir(folder_pathname)) == NULL) {
		fprintf(stdout, "ERROR ===> FITS file folder %s cannot be opened\n\n", folder_pathname);
		fprintf(stderr, "ERROR ===> FITS file folder %s cannot be opened\n\n", folder_pathname);
		return(1);
	}

	sprintf(dot_extension, ".%s", extension);
        char mytoken[256];
        char trash[256];
        char ext[256];
        char myfile[256];

        int tdiff;
        tdiff = 0;
        struct DateAndTime file_date;
	char                    text[128];
	long   year, month, day, hour, minute, second, milliseconds, cam;
        time_t rawtime;
        struct tm * timeinfo;
        time(&rawtime);
        timeinfo = localtime(&rawtime);
        int file_time;
        int now; 
        now = (timeinfo->tm_mday * 24 * 60) +  (timeinfo->tm_hour * 60) + (timeinfo->tm_min);


	while (entry = readdir(directoryfolder)) {      //... listing of ".extension" files

                sprintf(myfile, "%s", entry->d_name);
                sscanf(myfile, "%[^.].%s", &mytoken, &ext);


		if (strstr(entry->d_name, dot_extension) != NULL)  { 

		     sscanf(myfile, "%4ld_%2ld_%2ld_%2ld_%2ld_%2ld_%3ld_%6d.%s", 
			&year, &month, &day, &hour, &minute, &second, &milliseconds,&cam,&text);
                     //printf("%li %li %li", day, hour, minute);  
                     file_time = (day * 24 * 60) +  (hour * 60) + (minute);
                     //printf ("TIMES: %d - %d", now, file_time);
                     tdiff = abs(now - file_time);
                     printf("TDIFF: %d\n", tdiff);

                     sprintf(png_file, "%s%s-stacked.png", folder_pathname, mytoken) ;
                     if (!access(png_file, F_OK)) {
                        printf("FOUND: %s,%s\n", png_file, myfile );
                     }
                     else {
                        printf("NOT FOUND: %s,%s\n", png_file, myfile );
                        if (tdiff > 3) {
                           fprintf(filelisting, "%s\n", entry->d_name);
                        }
                     }
                }

	}

	fclose(filelisting);

	closedir(directoryfolder);

	return(0);


#endif /************* End of WINDOWS or LINUX *********************************/

}



//#########################################################################################

//=========================================================================================
//    Get the CAMS baseline folder path by obtaining the executable location and use the
//      assumption that the executable is run out of the CAMS/RunFolder subfolder.
//=========================================================================================

void        GetCAMSbaselineFolder(char *camsbaseline_folder)
{
char   exe_fullname[256];
char   exe_pathname[256];
char   exe_executable[256];
char   exe_runfolder[256];


#ifdef _WIN32 /************* WINDOWS *******************************************/

	GetModuleFileName(0, exe_fullname, 256);    //  C:\...\CAMS\RunFolder\*.exe

#else /********************** LINUX *******************************************/

    ssize_t len = readlink("/proc/self/exe", exe_fullname, sizeof(exe_fullname));

    if (len == -1 || len == sizeof(exe_fullname))  len = 0;

    exe_fullname[len] = '\0';

#endif /************* End of WINDOWS or LINUX *********************************/


	//  exe_fullname  =  C:\...\CAMS\RunFolder\*.exe  (or forward slashes for Linux)

    SplitFilename(exe_fullname, exe_pathname, exe_executable);        //  C:\...\CAMS\RunFolder

	SplitFilename(exe_pathname, camsbaseline_folder, exe_runfolder);  //  C:\...\CAMS

	EndsInSlash(camsbaseline_folder);                                 //  C:\...\CAMS\

	if ((long)strlen(camsbaseline_folder) - (long)(strrchr(camsbaseline_folder, 'C') - camsbaseline_folder) != 5 ||
		(long)strlen(camsbaseline_folder) - (long)(strrchr(camsbaseline_folder, 'A') - camsbaseline_folder) != 4 ||
		(long)strlen(camsbaseline_folder) - (long)(strrchr(camsbaseline_folder, 'M') - camsbaseline_folder) != 3 ||
		(long)strlen(camsbaseline_folder) - (long)(strrchr(camsbaseline_folder, 'S') - camsbaseline_folder) != 2) {
		printf("CAMS baseline folder pathname appears to be incorrect\n");
		printf("   It should be ...\\...\\CAMS\\  on Windows\n");
		printf("   It should be ...//...//CAMS//  on Linux\n");
		printf("   Actually is %s \n", camsbaseline_folder);
		//Delay_msec(30000);
		//exit(1);
	}



}

//=========================================================================================
//         Read the site information for the specified camera from the sitesfilename
//=========================================================================================

void  ReadSiteInfo4Camera(long cameranumber, char *sitesfilename, struct camerasiteinfo *camerasite)
{
	long   camnum, camerafound;
	double latitude_deg, longitude_deg, height_km, framerate_Hz;
	double focallength_mm, focalratio, pixelpitchH_um, pixelpitchV_um;
	double specB, specV, specR, specI, vignette_coef, gamma;
	char   camerafilename[256];
	char   camerapathname[256];
	char   calfolder[256];
	char   text[256];
	char   cameradesc[128];
	char   lensdesc[128];
	char   stationcode[4];
	FILE  *sitesfile;
	FILE  *camfile;


	//------------------ open the camera sites data file

	if ((sitesfile = fopen(sitesfilename, "r")) == NULL) {
		printf(        " Cannot open the %s file for reading \n", sitesfilename);
		fprintf(stderr," Cannot open the %s file for reading \n", sitesfilename);
		Delay_msec(10000);
		exit(1);
	}

	SplitFilename(sitesfilename, calfolder, text);


	//------------------ Skip past header lines

	fscanf(sitesfile, "%[^\n]\n", text);
	fscanf(sitesfile, "%[^\n]\n", text);


	//------------------ Read through all the cameras to get the desired (camera) site info

	camerasite->framerate_Hz = 0.0;

	camerafound = 0;


	while (feof(sitesfile) == 0) {

		camnum = -1;  //...reset to check if no further lines read and exit

					  //................ Read data from the site info file

		fscanf(sitesfile, "%ld %lf %lf %lf %s %3s %[^\n]\n",
			&camnum,
			&latitude_deg,
			&longitude_deg,  //+west
			&height_km,
			camerafilename,
			stationcode,
			text);

		//................ Check for the right camera number

		if (camnum == -1)  break;

		if (camnum != cameranumber)  continue;

		camerafound = 1;

		//................ Save the camera parameters

		camerasite->cameranumber = cameranumber;

		camerasite->latitude  = latitude_deg  * 3.14159265359 / 180.0;
		camerasite->longitude = longitude_deg * 3.14159265359 / 180.0;  //+west
		camerasite->height_km = height_km;

		strcpy(camerasite->station_ext,  stationcode);
		strcpy(camerasite->station_name, text);


		//................ Now read in the camera system parameters

		strcpy(camerapathname, calfolder);

		EndsInSlash(camerapathname);

		strcat(camerapathname, camerafilename);

		if ((camfile = fopen(camerapathname, "r")) == NULL) {
			printf(" Cannot open the camera file %s for reading \n", camerafilename);
			Delay_msec(5000);
			exit(1);
		}

		fscanf(camfile, "%[^=]= %[^\n]\n", text, cameradesc);
		fscanf(camfile, "%[^=]= %[^\n]\n", text, lensdesc);
		fscanf(camfile, "%[^=]= %lf", text, &framerate_Hz);
		fscanf(camfile, "%[^=]= %lf", text, &focallength_mm);
		fscanf(camfile, "%[^=]= %lf", text, &focalratio);
		fscanf(camfile, "%[^=]= %lf", text, &pixelpitchH_um);
		fscanf(camfile, "%[^=]= %lf", text, &pixelpitchV_um);
		fscanf(camfile, "%[^=]= %lf", text, &specB);
		fscanf(camfile, "%[^=]= %lf", text, &specV);
		fscanf(camfile, "%[^=]= %lf", text, &specR);
		fscanf(camfile, "%[^=]= %lf", text, &specI);
		fscanf(camfile, "%[^=]= %lf", text, &vignette_coef);
		fscanf(camfile, "%[^=]= %lf", text, &gamma);

		fclose(camfile);


		strcpy(camerasite->cameradesc, cameradesc);
		strcpy(camerasite->lensdesc, lensdesc);

		camerasite->framerate_Hz   = framerate_Hz;
		camerasite->focallength_mm = focallength_mm;
		camerasite->focalratio     = focalratio;
		camerasite->pixelpitchH_um = pixelpitchH_um;
		camerasite->pixelpitchV_um = pixelpitchV_um;
		camerasite->specB          = specB / (specB + specV + specR + specI);
		camerasite->specV          = specV / (specB + specV + specR + specI);
		camerasite->specR          = specR / (specB + specV + specR + specI);
		camerasite->specI          = specI / (specB + specV + specR + specI);
		camerasite->vignette_coef  = vignette_coef;
		camerasite->gamma          = gamma;

		break;

	}

	fclose(sitesfile);


	//------ Did we find a camera in the sites list ?  NO --> framerate = 0

	if (camerafound == 0) {
		printf(        " Cannot find camera %li in the %s file\n", cameranumber, sitesfilename);
		fprintf(stderr," Cannot find camera %li in the %s file\n", cameranumber, sitesfilename);
		Delay_msec(10000);
		exit(2);
	}


}

//=========================================================================================
//        Open and write the header of a detection summary log file
//=========================================================================================

FILE*      OpenSummaryLogFile( char                *detectionlog_pathname, 
	                           char                *captured_folder, 
	                           struct DateAndTime   ut, 
	                           int                  daynight_integMode, 
	                           double               version,
	                           double               jdt_start,
	                           double               jdt_stop,
	                           struct DateAndTime   folder_ut )
{
struct  DateAndTime    dt;
FILE   *detectionlog;


	if ( (detectionlog = fopen(detectionlog_pathname, "wt")) == NULL) {
		printf("ERROR: Could not open detection log file %s\n", detectionlog_pathname);
		Delay_msec(10000);
		exit(1);
	}

	fprintf(detectionlog, "Detection version %f\n", version);

	if (daynight_integMode == 0)  fprintf(detectionlog, "     This is a NIGHT collection\n");
	else                          fprintf(detectionlog, "     This is a DAYLIGHT collection\n");

	fprintf(detectionlog, "     Captured imagery to %s\n", captured_folder);

	fprintf(detectionlog, "Capture started %02d/%02d/%04d %02d:%02d:%02d\n",
		ut.month, ut.day, ut.year,
		ut.hour, ut.minute, ut.second);


	fprintf(detectionlog, "-----------------------------------------------------------------------\n");


	if (daynight_integMode == 0) {  //... NIGHT
		Calendar_DateAndTime(jdt_stop, &dt);
		printf("\nNIGHT collection until morning twilight %02d/%02d/%04d  %02d:%02d:%02d UT\n", dt.month, dt.day, dt.year, dt.hour, dt.minute, dt.second);
		fprintf(detectionlog, "\nNIGHT collection until morning twilight %02d/%02d/%04d  %02d:%02d:%02d UT\n", dt.month, dt.day, dt.year, dt.hour, dt.minute, dt.second);
		printf("\nDuration = %6.2f hours\n", 24.0 * (jdt_stop - jdt_start));
		fprintf(detectionlog, "\nDuration = %6.2f hours\n", 24.0 * (jdt_stop - jdt_start));
		printf("\nLocal Midnight is  %02d/%02d/%04d  %02d:%02d:%02d UT\n\n", folder_ut.month, folder_ut.day, folder_ut.year, folder_ut.hour, folder_ut.minute, folder_ut.second);
		fprintf(detectionlog, "\nLocal Midnight is  %02d/%02d/%04d  %02d:%02d:%02d UT\n\n", folder_ut.month, folder_ut.day, folder_ut.year, folder_ut.hour, folder_ut.minute, folder_ut.second);
	}
	else {
		Calendar_DateAndTime(jdt_stop, &dt);
		printf("\nDAYLIGHT collection until evening twilight %02d/%02d/%04d  %02d:%02d:%02d UT\n", dt.month, dt.day, dt.year, dt.hour, dt.minute, dt.second);
		fprintf(detectionlog, "\nDAYLIGHT collection until evening twilight %02d/%02d/%04d  %02d:%02d:%02d UT\n", dt.month, dt.day, dt.year, dt.hour, dt.minute, dt.second);
		printf("\nDuration = %6.2f hours\n", 24.0 * (jdt_stop - jdt_start));
		fprintf(detectionlog, "\nDuration = %6.2f hours\n", 24.0 * (jdt_stop - jdt_start));
		printf("\nLocal Noon is  %02d/%02d/%04d  %02d:%02d:%02d UT\n\n", folder_ut.month, folder_ut.day, folder_ut.year, folder_ut.hour, folder_ut.minute, folder_ut.second);
		fprintf(detectionlog, "\nLocal Noon is  %02d/%02d/%04d  %02d:%02d:%02d UT\n\n", folder_ut.month, folder_ut.day, folder_ut.year, folder_ut.hour, folder_ut.minute, folder_ut.second);
	}


	fprintf(detectionlog, "-----------------------------------------------------------------------\n");


	return(detectionlog);

}


//=========================================================================================
//    Open the detectinfo file to prep for writing sequences of detected meteor tracks.
//    Multiple files could be opened using the kthlogfile index to distiquish them.
//=========================================================================================

int   OpenFTPdetectinfo(int kthlogfile, char *filename, char *capturedfolder_pathname, char *calibrationfolder_pathname, double version)
{
int      totalmeteors;
time_t   processedtime;


	if (kthlogfile < 0 || kthlogfile > NLOGFILES - 1) {
		printf(        " OpenFTPdetectinfo %s log file %i out of range [0,%i] \n", filename, kthlogfile, NLOGFILES - 1);
		fprintf(stderr," OpenFTPdetectinfo %s log file %i out of range [0,%i] \n", filename, kthlogfile, NLOGFILES - 1);
		Delay_msec(10000);
		exit(61);
	}


	if (capturedfolder_pathname == NULL  &&  calibrationfolder_pathname == NULL) {  //...open, read counts, goto EOF

		if ((FTPlogfile[kthlogfile] = fopen(filename, "r+")) == NULL) {
			printf(        " Cannot open FTPdetectinfo file %s for read/write \n", filename);
			fprintf(stderr," Cannot open FTPdetectinfo file %s for read/write \n", filename);
			Delay_msec(10000);
			exit(62);
		}

		fscanf(FTPlogfile[kthlogfile], "Meteor Count = %d", &totalmeteors);

		fseek(FTPlogfile[kthlogfile], 0L, SEEK_END);  //... position to the end of the file
	}

	else {  //...open new file and write header info

		if ((FTPlogfile[kthlogfile] = fopen(filename, "wt")) == NULL) {
			printf(        " Cannot open FTPdetectinfo file %s for writing \n", filename);
			fprintf(stderr," Cannot open FTPdetectinfo file %s for writing \n", filename);
			Delay_msec(10000);
			exit(63);
		}

		processedtime = time(NULL);

		fprintf(FTPlogfile[kthlogfile], "Meteor Count = 000000\n");
		fprintf(FTPlogfile[kthlogfile], "-----------------------------------------------------\n");
		fprintf(FTPlogfile[kthlogfile], "Processed with software version %3.1lf on %s", version, ctime(&processedtime));
		fprintf(FTPlogfile[kthlogfile], "-----------------------------------------------------\n");
		fprintf(FTPlogfile[kthlogfile], "Imagery folder = %s\n", capturedfolder_pathname);
		fprintf(FTPlogfile[kthlogfile], "CAL folder = %s\n", calibrationfolder_pathname);
		fprintf(FTPlogfile[kthlogfile], "-----------------------------------------------------\n");
		fprintf(FTPlogfile[kthlogfile], "Imagery file processed\n");
		fprintf(FTPlogfile[kthlogfile], "CAL file processed\n");
		fprintf(FTPlogfile[kthlogfile], "Cam# Meteor# #Segments fps hnr mle bin Pix/fm Rho Phi\n");
		fprintf(FTPlogfile[kthlogfile], "Per segment:  Frame# Col Row RA Dec Azim Elev Inten\n");

		trackcount[kthlogfile] = 0;

		totalmeteors = 0L;

	}

	return(totalmeteors);



}


//=========================================================================================
//             Write a single event track to a detectinfo file
//=========================================================================================

void  WriteFTPdetectinfo(int kthlogfile, struct trackseqinfo *track)
{
long   ks;


	if (kthlogfile < 0 || kthlogfile > NLOGFILES - 1) {
		printf(" WriteFTPdetectinfo log file %i out of range [0,%i] \n", kthlogfile, NLOGFILES - 1);
		Delay_msec(10000);
		exit(61);
	}


	fprintf(FTPlogfile[kthlogfile], "-------------------------------------------------------\n");
	fprintf(FTPlogfile[kthlogfile], "%-s\n%-s\n%06li %04li %04li %07.2lf %05.1lf %05.1lf %05.1lf %05.1lf %06.1lf %06.1lf\n",
		track->proc_filename,
		track->cal_filename,
		track->cameranumber,
		track->meteornumber,
		track->nsegments,
		track->framerate,
		track->hnr,
		track->mle,
		track->bin,
		track->halfdeltad,
		track->houghrho,
		track->houghphi);


	for (ks = 0; ks<track->nsegments; ks++) {

		fprintf(FTPlogfile[kthlogfile], "%06.1lf %07.2lf %07.2lf %06.2lf %06.2lf %06.2lf %06.2lf %06li\n",
			track->framenumber[ks],
			track->colcentroid[ks],
			track->rowcentroid[ks],
			track->RA_deg[ks],
			track->DEC_deg[ks],
			track->AZ_deg[ks],
			track->EL_deg[ks],
			track->integratedcount[ks]);

	}

	trackcount[kthlogfile]++;

}

//=========================================================================================
//             Write a single event track to a detectinfo file
//=========================================================================================

void  CloseFTPdetectinfo(int kthlogfile)
{

	if (kthlogfile < 0 || kthlogfile > NLOGFILES - 1) {
		printf(        " CloseFTPdetectinfo log file %i out of range [0,%i] \n", kthlogfile, NLOGFILES - 1);
		fprintf(stderr," CloseFTPdetectinfo log file %i out of range [0,%i] \n", kthlogfile, NLOGFILES - 1);
		Delay_msec(10000);
		exit(64);
	}

	//======== Overwrite the first line of the file to indicate meteor count
	//         where trackcount is a global updated within the previous functions

	fseek(FTPlogfile[kthlogfile], 0L, SEEK_SET);  //...reset to beginning of file

	fprintf(FTPlogfile[kthlogfile], "Meteor Count = %06i\n", trackcount[kthlogfile]);

	fclose(FTPlogfile[kthlogfile]);

}


//=========================================================================================
//           User dialog to get an FF file name
//=========================================================================================

#ifdef _WIN32 /*############## WINDOWS ############################*/

void   GetFF_File(char* ff_file, long ff_file_dim)
{
	char   ffstring[256], *X_ptr;
	HWND   consolehandle;


	SetConsoleTitle("Console Window");
	Sleep(40);
	consolehandle = FindWindow(NULL, "Console Window");


	//------------- Windows dialog to get the FF file name to be reprocessed

	OPENFILENAME ofn;
	char szFileName[MAX_PATH] = "";

	sprintf(ffstring, "FF Files (FF*.bin)XFF*.binXAll Files (*.*)X*.*XX");
	//...replace six X's with NULL strings
	X_ptr = strrchr(ffstring, 'X');   ffstring[(long)(X_ptr - ffstring)] = '\0';
	X_ptr = strrchr(ffstring, 'X');   ffstring[(long)(X_ptr - ffstring)] = '\0';
	X_ptr = strrchr(ffstring, 'X');   ffstring[(long)(X_ptr - ffstring)] = '\0';
	X_ptr = strrchr(ffstring, 'X');   ffstring[(long)(X_ptr - ffstring)] = '\0';
	X_ptr = strrchr(ffstring, 'X');   ffstring[(long)(X_ptr - ffstring)] = '\0';


	ZeroMemory(&ofn, sizeof(ofn));
	ofn.lStructSize = sizeof(ofn);
	ofn.hwndOwner = consolehandle;
	ofn.lpstrTitle = "Navigate to and select the FF File ";
	ofn.lpstrFilter = ffstring;
	ofn.lpstrFile = szFileName;
	ofn.lpstrFile[0] = '\0';
	ofn.nMaxFile = MAX_PATH;
	ofn.Flags = OFN_EXPLORER | OFN_FILEMUSTEXIST | OFN_HIDEREADONLY | OFN_NOCHANGEDIR;
	ofn.lpstrInitialDir = '\0';

	if (GetOpenFileName(&ofn)) {
		strcpy(ff_file, szFileName);
	}
	else {
		ff_file = '\0';
		printf(" ERROR getting FF filename \n");
	}

	//============ Get only the folder name portion

	//long   namelength;   
	//long   lastbackslash;
	//int    backslash;

	//namelength = strlen( ff_file );

	//backslash = 92;

	//lastbackslash = strrchr( ff_file, backslash ) - ff_file;

	//ff_file[lastbackslash] = '\0';


}

#else /*##################### LINUX ##############################*/

void   GetFF_File(char* ff_file, long ff_file_dim)
{
	printf("TBD - GetFF_File not implemented for Linux\n");
	Delay_msec(15000);
	exit(1);
}

#endif /*#########################################################*/


//=========================================================================================
//           User dialog to get an FF file folder
//=========================================================================================

#ifdef _WIN32 /*############## WINDOWS ############################*/

void   GetFF_Folder(char* ff_folder, long ff_folder_dim)
{
	HWND   consolehandle;


	SetConsoleTitle("Console Window");
	Sleep(40);
	consolehandle = FindWindow(NULL, "Console Window");


	//------------- Windows dialog to get the FF folder name to be reprocessed

	BROWSEINFO  binfo;
	ZeroMemory(&binfo, sizeof(binfo));
	TCHAR szDisplayName[MAX_PATH];
	szDisplayName[0] = '\0';

	binfo.hwndOwner = consolehandle;
	binfo.lpszTitle = "Navigate to and select the FF Folder";
	binfo.pszDisplayName = szDisplayName;
	binfo.lpfn = '\0';
	binfo.ulFlags = BIF_RETURNONLYFSDIRS;
	binfo.pidlRoot = '\0';  //specifies the folder to start the search
	binfo.lParam = '\0';
	binfo.iImage = 0;

	LPITEMIDLIST   pidl;
	TCHAR szPathName[MAX_PATH];

	if ((pidl = SHBrowseForFolder(&binfo)) != NULL) {
		SHGetPathFromIDList(pidl, szPathName); //get full path name
		strcpy(ff_folder, szPathName);
	}
	else {
		strcpy(ff_folder, "CANCEL");
		printf("\n Did not get a FF files folder pathname from user \n");
	}


}

#else /*##################### LINUX ##############################*/

void   GetFF_Folder(char* ff_folder, long ff_folder_dim)
{
	printf("TBD - GetFF_Folder not implemented for Linux\n");
	Delay_msec(15000);
	exit(1);
}

#endif /*#########################################################*/


//=========================================================================================
//   User dialog to get an FF file folder given a previous folder location to speed up
//     the user's navigation through folders.
//=========================================================================================


#ifdef _WIN32 /*############## WINDOWS ############################*/

void   GetFF_Folder_UsingLastFolder(char *ff_folder_last, char* ff_folder, long ff_folder_dim)
{
	HWND   consolehandle;


	SetConsoleTitle("Console Window");
	Sleep(40);
	consolehandle = FindWindow(NULL, "Console Window");


	//------------- Windows dialog to get the FF folder name to be reprocessed

	BROWSEINFO  binfo;
	ZeroMemory(&binfo, sizeof(binfo));
	TCHAR szDisplayName[MAX_PATH];
	szDisplayName[0] = '\0';

	binfo.hwndOwner = consolehandle;
	binfo.lpszTitle = "Navigate to and select the FF Folder";
	binfo.pszDisplayName = szDisplayName;
	binfo.lpfn = '\0';
	binfo.ulFlags = BIF_RETURNONLYFSDIRS;
	binfo.pidlRoot = '\0';  //not NULL path limits search to folder specified (and subfolders), cannot go up 
	binfo.lParam = '\0';
	binfo.iImage = 0;

	LPITEMIDLIST   pidl;
	TCHAR szPathName[MAX_PATH];

	if ((pidl = SHBrowseForFolder(&binfo)) != NULL) {
		SHGetPathFromIDList(pidl, szPathName); //get full path name
		strcpy(ff_folder, szPathName);
	}
	else {
		strcpy(ff_folder, "CANCEL");
		printf("\n Did not get a FF files folder pathname from user \n");
	}


}

#else /*##################### LINUX ##############################*/

void    GetFF_Folder_UsingLastFolder(char *ff_folder_last, char* ff_folder, long ff_folder_dim)
{
	printf("TBD - GetFF_Folder_UsingLastFolder not implemented for Linux\n");
	Delay_msec(15000);
	exit(1);
}

#endif /*#########################################################*/



//=========================================================================================
//           User dialog to navigate to and get the CAL file folder
//=========================================================================================

#ifdef _WIN32 /*############## WINDOWS ############################*/

void   GetCAL_Folder(char* cal_folder, long cal_folder_dim)
{
	HWND   consolehandle;


	SetConsoleTitle("Console Window");
	Sleep(40);
	consolehandle = FindWindow(NULL, "Console Window");


	//------------- Windows dialog to get the Cal folder name

	BROWSEINFO  binfo;
	ZeroMemory(&binfo, sizeof(binfo));
	TCHAR szDisplayName[MAX_PATH];
	szDisplayName[0] = '\0';

	binfo.hwndOwner = consolehandle;
	binfo.lpszTitle = "Navigate to the Calibration files folder";
	binfo.pszDisplayName = szDisplayName;
	binfo.lpfn = '\0';
	binfo.ulFlags = BIF_RETURNONLYFSDIRS;
	binfo.pidlRoot = '\0';
	binfo.lParam = '\0';
	binfo.iImage = 0;

	LPITEMIDLIST   pidl;
	TCHAR szPathName[MAX_PATH];

	if ((pidl = SHBrowseForFolder(&binfo)) != NULL) {
		SHGetPathFromIDList(pidl, szPathName); //get full path name
		strcpy(cal_folder, szPathName);
	}
	else {
		cal_folder = '\0';
		printf(" ERROR getting CAL files folder pathname \n");
	}

}

#else /*##################### LINUX ##############################*/

void   GetCAL_Folder(char* cal_folder, long cal_folder_dim)
{
	printf("TBD - GetCAL_Folder not implemented for Linux\n");
	Delay_msec(15000);
	exit(1);
}

#endif /*#########################################################*/



//=========================================================================================
//           User dialog to navigate to and get an MP4 file full pathname
//=========================================================================================

#ifdef _WIN32 /*############## WINDOWS ############################*/

void   GetMP4_File(char* mp4_pathname)
{
	char   ffstring[256], *X_ptr;
	HWND   consolehandle;


	SetConsoleTitle("Console Window");
	Sleep(40);
	consolehandle = FindWindow(NULL, "Console Window");


	//------------- Windows dialog to get the MP4 file name to be reprocessed

	OPENFILENAME ofn;
	char szFileName[MAX_PATH] = "";

	sprintf(ffstring, "MP4 Files (*.mp4)X*.mp4XAll Files (*.*)X*.*XX");
	//...replace five X's with NULL strings
	X_ptr = strrchr(ffstring, 'X');   ffstring[(long)(X_ptr - ffstring)] = '\0';
	X_ptr = strrchr(ffstring, 'X');   ffstring[(long)(X_ptr - ffstring)] = '\0';
	X_ptr = strrchr(ffstring, 'X');   ffstring[(long)(X_ptr - ffstring)] = '\0';
	X_ptr = strrchr(ffstring, 'X');   ffstring[(long)(X_ptr - ffstring)] = '\0';
	X_ptr = strrchr(ffstring, 'X');   ffstring[(long)(X_ptr - ffstring)] = '\0';


	ZeroMemory(&ofn, sizeof(ofn));
	ofn.lStructSize = sizeof(ofn);
	ofn.hwndOwner = consolehandle;
	ofn.lpstrTitle = "Navigate to the MP4 File for Calibration";
	ofn.lpstrFilter = ffstring;
	ofn.lpstrFile = szFileName;
	ofn.lpstrFile[0] = '\0';
	ofn.nMaxFile = MAX_PATH;
	ofn.Flags = OFN_EXPLORER | OFN_FILEMUSTEXIST | OFN_HIDEREADONLY | OFN_NOCHANGEDIR;
	ofn.lpstrInitialDir = '\0';

	if (GetOpenFileName(&ofn)) {
		strcpy(mp4_pathname, szFileName);
	}
	else {
		mp4_pathname = '\0';
		printf(" ERROR getting mp4 pathname \n");
	}

}

#else /*##################### LINUX ##############################*/

void   GetMP4_File(char* mp4_pathname)
{
	printf("TBD - GetMP4_File not implemented for Linux\n");
	Delay_msec(15000);
	exit(1);
}


#endif /*#########################################################*/



//=========================================================================================
//           User dialog to navigate to and get an MP4 folder patname
//=========================================================================================

#ifdef _WIN32 /*############## WINDOWS ############################*/

void   GetMP4_Folder(char* mp4_folder)
{
	HWND   consolehandle;


	SetConsoleTitle("Console Window");
	Sleep(40);
	consolehandle = FindWindow(NULL, "Console Window");


	//------------- Windows dialog to get the MP4 folder name

	BROWSEINFO  binfo;
	ZeroMemory(&binfo, sizeof(binfo));
	TCHAR szDisplayName[MAX_PATH];
	szDisplayName[0] = '\0';

	binfo.hwndOwner = consolehandle;
	binfo.lpszTitle = "Navigate to the MP4 files folder to process";
	binfo.pszDisplayName = szDisplayName;
	binfo.lpfn = '\0';
	binfo.ulFlags = BIF_RETURNONLYFSDIRS;
	binfo.pidlRoot = '\0';
	binfo.lParam = '\0';
	binfo.iImage = 0;

	LPITEMIDLIST   pidl;
	TCHAR szPathName[MAX_PATH];

	if ((pidl = SHBrowseForFolder(&binfo)) != NULL) {
		SHGetPathFromIDList(pidl, szPathName); //get full path name
		strcpy(mp4_folder, szPathName);
	}
	else {
		mp4_folder = '\0';
		printf(" ERROR getting the MP4 files folder pathname \n");
	}

}

#else /*##################### LINUX ##############################*/

void   GetMP4_Folder(char* mp4_folder)
{

	strcpy(mp4_folder, "../Collected");

	printf(" WARNING: Function GetMP4_Folder in CAMS_IOfunctions.h\n");
	printf("   is not fully implemented for LINUX - hardcoded to ../Collected\n");
	printf("   This should be a dialog navigation to the folder by the user\n");

}

#endif /*#########################################################*/



//=========================================================================================
//           User dialog to navigate to and get a Detectinfo file full pathname
//=========================================================================================


#ifdef _WIN32 /*############## WINDOWS ############################*/

void   GetFTPMeteorFilename(char* ftp_file, long ftp_file_dim)
{
	char   ffstring[256], *X_ptr;
	HWND   consolehandle;


	SetConsoleTitle("Console Window");
	Sleep(40);
	consolehandle = FindWindow(NULL, "Console Window");


	//------------- Windows dialog to get the FF file name to be reprocessed

	OPENFILENAME ofn;
	char szFileName[MAX_PATH] = "";

	sprintf(ffstring, "FTP Detection Files (FTPdetectinfo*.txt)XFTPdetectinfo*.txtXAll Files (*.*)X*.*X");
	//...replace four X's with NULL strings
	X_ptr = strrchr(ffstring, 'X');   ffstring[(long)(X_ptr - ffstring)] = '\0';
	X_ptr = strrchr(ffstring, 'X');   ffstring[(long)(X_ptr - ffstring)] = '\0';
	X_ptr = strrchr(ffstring, 'X');   ffstring[(long)(X_ptr - ffstring)] = '\0';
	X_ptr = strrchr(ffstring, 'X');   ffstring[(long)(X_ptr - ffstring)] = '\0';

	ZeroMemory(&ofn, sizeof(ofn));
	ofn.lStructSize = sizeof(ofn);
	ofn.hwndOwner = consolehandle;
	ofn.lpstrTitle = "Navigate to and select the FTPdetectinfo file to process";
	ofn.lpstrFilter = ffstring;
	ofn.lpstrFile = szFileName;
	ofn.lpstrFile[0] = '\0';
	ofn.nMaxFile = MAX_PATH;
	ofn.Flags = OFN_EXPLORER | OFN_FILEMUSTEXIST | OFN_HIDEREADONLY | OFN_NOCHANGEDIR;
	ofn.lpstrInitialDir = '\0';

	if (GetOpenFileName(&ofn)) {
		strcpy(ftp_file, szFileName);
	}
	else {
		strcpy(ftp_file, "CANCEL");
		printf("\n Did not get a FTPdetectinfo pathname from user \n");
	}

}

#else /*##################### LINUX ##############################*/

void   GetFTPMeteorFilename(char* ftp_file, long ftp_file_dim)
{
	printf("TBD - GetFTPMeteorFilename not implemented for Linux\n");
	Delay_msec(15000);
	exit(1);
}

#endif /*#########################################################*/


//=========================================================================================
//       User dialog to navigate to and get an SummaryMeteorLog file full pathname
//=========================================================================================

void   GetMeteorLogPathname(char* ftp_file, long ftp_file_dim)
{

#ifdef _WIN32 /*############## WINDOWS ############################*/

	char   ffstring[256], *X_ptr;
	HWND   consolehandle;


	SetConsoleTitle("Console Window");
	Sleep(40);
	consolehandle = FindWindow(NULL, "Console Window");


	//------------- Windows dialog to get the FF file name to be reprocessed

	OPENFILENAME ofn;
	char szFileName[MAX_PATH] = "";

	sprintf(ffstring, "Meteor Log Files (SummaryMeteorLog*.txt)XSummaryMeteorLog*.txtXAll Files (*.*)X*.*X");
	//...replace four X's with NULL strings
	X_ptr = strrchr(ffstring, 'X');   ffstring[(long)(X_ptr - ffstring)] = '\0';
	X_ptr = strrchr(ffstring, 'X');   ffstring[(long)(X_ptr - ffstring)] = '\0';
	X_ptr = strrchr(ffstring, 'X');   ffstring[(long)(X_ptr - ffstring)] = '\0';
	X_ptr = strrchr(ffstring, 'X');   ffstring[(long)(X_ptr - ffstring)] = '\0';

	ZeroMemory(&ofn, sizeof(ofn));
	ofn.lStructSize = sizeof(ofn);
	ofn.hwndOwner = consolehandle;
	ofn.lpstrTitle = "Navigate & select the SummaryMeteorLog.txt file to process (in gefdat)";
	ofn.lpstrFilter = ffstring;
	ofn.lpstrFile = szFileName;
	ofn.lpstrFile[0] = '\0';
	ofn.nMaxFile = MAX_PATH;
	ofn.Flags = OFN_EXPLORER | OFN_FILEMUSTEXIST | OFN_HIDEREADONLY | OFN_NOCHANGEDIR;
	ofn.lpstrInitialDir = '\0';

	if (GetOpenFileName(&ofn)) {
		strcpy(ftp_file, szFileName);
	}
	else {
		ftp_file = '\0';
		printf(" ERROR getting SummaryMeteorLog.txt filename \n");
	}

#else /*###################### LINUX ########################*/

	printf("Function GetMeteorLogPathname in FTP_meteorProcessing\n");
	printf("  is not implemented for LINUX\n");
	exit(1);

#endif /*#########################################################*/

}

//=========================================================================================
//   User dialog to get the most recent CAL or FOV file in the specified folder_pathname
//     that has a date stamp no later than jdtlast. Returns the CAL filename.
//=========================================================================================

int     GetMostRecentFile(char *folder_pathname, char *file_firstpart, double jdtlast, char *latest_filename)
{
	double jdtcal, jdtdiff;
	char          system_command[512];
	char            fullfilename[512];
	char                    text[128];
	long   year, month, day, hour, minute, second, milliseconds, cam;

	struct  DateAndTime  dt;



	//--------- Loop over the list of calibration filenames for this camera 

#ifdef _WIN32 /*############## WINDOWS ############################*/

	strcpy(system_command, folder_pathname);

	strcat(system_command, file_firstpart);

	strcat(system_command, "*.txt");

	HANDLE                     hfindFile;
	WIN32_FIND_DATA            findFileStruct;

	hfindFile = FindFirstFile(system_command, &findFileStruct);

	if (hfindFile == INVALID_HANDLE_VALUE) {
		//printf(" FindFirstFile: Invalid handle returned searching for %s files\n", file_firstpart );
		//printf(" No %s* file found with valid time\n", file_firstpart );
		return(2);
	}

	strcpy(fullfilename, findFileStruct.cFileName);

	if (strstr(fullfilename, "CAL_") != NULL) {  //... new CAL filename format
		sscanf(fullfilename, "%[^_]_%6ld_%4ld%2ld%2ld_%2ld%2ld%2ld_%3ld.txt", text,
			&cam, &year, &month, &day, &hour, &minute, &second, &milliseconds);
	}
	else {                                          //... old filename format
		sscanf(fullfilename, "%[^_]_%4ld%2ld%2ld_%2ld%2ld%2ld_%3ld.txt", text,
			&year, &month, &day, &hour, &minute, &second, &milliseconds);
	}

	FillDateAndTimeStructure(year, month, day, hour, minute, second, milliseconds, &dt);

	jdtcal = JulianDateAndTime(&dt);

	strcpy(latest_filename, findFileStruct.cFileName);

	jdtdiff = jdtlast - jdtcal;


	//---------- Pick the closest cal file in time no later than the last
	//             meteor event in case the system has been moved 

	while (FindNextFile(hfindFile, &findFileStruct)) {

		strcpy(fullfilename, findFileStruct.cFileName);

		//.... parse the calibration filename for date and time
		//     *_YYYYMMDD_HHMMSS_SSS.txt

		if (strstr(fullfilename, "CAL_") != NULL) {  //... new CAL filename format
			sscanf(fullfilename, "%[^_]_%6ld_%4ld%2ld%2ld_%2ld%2ld%2ld_%3ld.txt", text,
				&cam, &year, &month, &day, &hour, &minute, &second, &milliseconds);
		}
		else {                                          //... old filename format
			sscanf(fullfilename, "%[^_]_%4ld%2ld%2ld_%2ld%2ld%2ld_%3ld.txt", text,
				&year, &month, &day, &hour, &minute, &second, &milliseconds);
		}

		FillDateAndTimeStructure(year, month, day, hour, minute, second, milliseconds, &dt);

		jdtcal = JulianDateAndTime(&dt);



		if ((fabs(jdtlast - jdtcal) <= fabs(jdtdiff)) &&
			(jdtcal <= jdtlast)) {

			strcpy(latest_filename, findFileStruct.cFileName);

			jdtdiff = jdtlast - jdtcal;
		}

	}

	FindClose(hfindFile);


#else /*##################### LINUX ##############################*/

	int     icnt;
	struct  dirent *entry;
	DIR    *dp;

	icnt = 0;
	dp = opendir(folder_pathname);
	if (dp != NULL) {
		while (entry = readdir(dp))
		{
			strcpy(fullfilename, entry->d_name);

			/* Only process *.txt files */

			if ((strstr(fullfilename, file_firstpart) != NULL) && (strstr(fullfilename, ".txt") != NULL))
			{

				//.... parse the calibration filename for date and time
				//     *_YYYYMMDD_HHMMSS_SSS.txt

				if (strstr(fullfilename, "CAL_") != NULL) {  //... new CAL filename format
					sscanf(fullfilename, "%[^_]_%6ld_%4ld%2ld%2ld_%2ld%2ld%2ld_%3ld.txt", text,
						&cam, &year, &month, &day, &hour, &minute, &second, &milliseconds);
				}
				else {                                          //... old filename format
					sscanf(fullfilename, "%[^_]_%4ld%2ld%2ld_%2ld%2ld%2ld_%3ld.txt", text,
						&year, &month, &day, &hour, &minute, &second, &milliseconds);
				}

				FillDateAndTimeStructure(year, month, day, hour, minute, second, milliseconds, &dt);

				jdtcal = JulianDateAndTime(&dt);

				if (icnt == 0) {
					strcpy(latest_filename, fullfilename);
					jdtdiff = jdtlast - jdtcal;
				}
				else {
					if ((fabs(jdtlast - jdtcal) <= fabs(jdtdiff)) &&
						(jdtcal <= jdtlast)) {

						strcpy(latest_filename, fullfilename);
						jdtdiff = jdtlast - jdtcal;
					}
				}
				icnt += 1;
			}
		}
	}
	else {
		printf(" No Cal file found in %s  \n", folder_pathname);
	}
	closedir(dp);

#endif /*#########################################################*/


	//--------- Ensure we have a null character at the end of the filename string
	//             Old Cal file convention is 30 characters  CAL###_YYYYMMDD_HHMMSS_MSC.txt 
	//             New Cal file convention is 34 characters  CAL_######_YYYYMMDD_HHMMSS_MSC.txt 
	//             FOV file convention is 30 characters  FOVpercent_YYYYMMDD_HHMMSS.txt 


	if (strstr(file_firstpart, "CAL") == NULL)  latest_filename[30] = '\0';  //FOV
	else {
		if (strstr(file_firstpart, "CAL_") == NULL)  latest_filename[30] = '\0';  //CAL###_
		else                                            latest_filename[34] = '\0';  //CAL_######_
	}

	if (strstr(file_firstpart, "CAL") != NULL)   printf(" Latest cal filename is %s \n", latest_filename);
	else                                         printf(" Latest fov filename is %s \n", latest_filename);


	return(0);

}


//=========================================================================================
//          
//=========================================================================================



//=========================================================================================
//          
//=========================================================================================



//=========================================================================================
//          
//=========================================================================================


