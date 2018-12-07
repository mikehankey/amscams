//####################################################################
//####################################################################
//#############                                          #############
//#############   OPERATING SYSTEM and I/O ROUTINES      #############
//#############                                          #############
//####################################################################
//####################################################################
//
//  Date         Version   Description
//  -----------  -------   -------------------------------------------
//  2010-Jul-05  1.1       Initially implemented for FFs by P. Gural
//  2016-Dec-07  2.0       Split out from MeteorProcessing
//
//####################################################################


//====================================================================
//        Include statements for C library functions
//====================================================================


#ifdef _WIN32 /*############## WINDOWS ############################*/

#include <windows.h>

#else /*##################### LINUX ##############################*/

#include <dirent.h>
#include <sys/stat.h>

extern unsigned int sleep(unsigned int __seconds);

#endif /*#########################################################*/



//====================================================================
//        Function prototypes
//====================================================================

//------------- Folder and file name retrieval function prototypes

void         SplitFilename( char* fullfilename, 
						    char* folder_pathname,
						    char* filename          );

void           EndsInSlash( char* folder_pathname   );

void            Delay_msec( int   milliseconds      );

long      GetFileSizeBytes( char* fullpathname      );


//====================================================================


//################################################################################
//               Some Linux only functions
//################################################################################

#ifdef _WIN32 
#else      /*######################### LINUX ###########################*/

int checkfile(const char *path)
{
	FILE *fp;

	fp = fopen(path, "r");
	if (fp == NULL) {
		/*perror("checkfile"); */
		return(-1);
	}
	else {
		fclose(fp);
	}
	return(0);
}

//................................................

int checkdir(const char *path)
{
	struct dirent *entry;
	DIR *dp;

	dp = opendir(path);
	if (dp == NULL) {
		/*perror("checkdir"); */
		return(-1);
	}
	//  else  {
	//      closedir(dp);
	//  }
	closedir(dp);
	return(0);
}

//..............................................

int check_args(int argc, char** argv)
{
	int i;

	if (argc != 4) {  /* argc should be 6 for correct execution */
		printf("usage: detect FF_input_Dir FF_Output_Dir Cal_Input_Dir");
		return(-1);
	}
	else {
		for (i = 1; i<4; i++) {
			/*printf("%s\n",argv[i]); */
			if (checkdir(argv[i]) == -1) {
				printf("%s Not Found\n", argv[i]);
				return(-1);
			}
		}
		return(0);
	}

}
#endif   /*##############################################################*/



//################################################################################
//               Split pathname for Windows and Linux
//################################################################################

void   SplitFilename(char* fullfilename, char* folder_pathname, char* filename)
{
	long   k;
	long   namelength;
	long   lastslash;
	int    slash;

	namelength = (long)strlen(fullfilename);

#ifdef _WIN32   
	slash = 92;
#else  //UNIX wants forward slashes     
	slash = 47;
#endif

	lastslash = (long)( strrchr(fullfilename, slash) - fullfilename );

	strcpy(folder_pathname, fullfilename);

	folder_pathname[lastslash + 0] = '\0';
	folder_pathname[lastslash + 1] = '\0';

	for (k = lastslash + 1; k<namelength; k++) filename[k - lastslash - 1] = fullfilename[k];

	filename[namelength - lastslash - 1] = '\0';
	filename[namelength - lastslash - 0] = '\0';


}

//################################################################################
//             Slash terminator for Windows and Linux
//################################################################################


void   EndsInSlash(char* folder_pathname)
{
	long   namelength;
	long   lastslash;
	int    slash;

	namelength = (long)strlen(folder_pathname);

#ifdef _WIN32   
	slash = 92;
#else  //UNIX wants forward slashes     
	slash = 47;
#endif

	lastslash = (long)( strrchr(folder_pathname, slash) - folder_pathname );

#ifdef _WIN32   
	if (lastslash + 1 != namelength)  strcat(folder_pathname, "\\");
#else  //UNIX wants a forward slash     
	if (lastslash + 1 != namelength)  strcat(folder_pathname, "/");
#endif

}

//################################################################################
//                Sleep functions for Windows and Linux
//################################################################################

void  Delay_msec(int milliseconds)
{

#ifdef _WIN32 /************* WINDOWS ******************************/

	Sleep(milliseconds);

#else /********************** LINUX *******************************/

	sleep((unsigned int)(milliseconds / 1000));

#endif /***********************************************************/

}

//################################################################################
//            Get file size in bytes for Windows and Linux
//################################################################################

long      GetFileSizeBytes(char* fullpathname)
{
long   nbytes;


#ifdef _WIN32 /************* WINDOWS ******************************/

	WIN32_FILE_ATTRIBUTE_DATA  fileInfo;

	if (GetFileAttributesExA( fullpathname, GetFileExInfoStandard, &fileInfo))  nbytes = (long)fileInfo.nFileSizeLow;
	else                                                                        nbytes = 0;

#else /********************** LINUX *******************************/

	struct stat statbuf;

	if (stat(fullpathname, &statbuf) == -1)  nbytes = 0;
	else                                     nbytes = (long)statbuf.st_size;

#endif /***********************************************************/


    return(nbytes);

}


//################################################################################

