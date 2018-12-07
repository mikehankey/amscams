//#########################################################################################
//  Set of functions to read configuration run parameters for HCAMS processing
//
//  ---------------------------------------------------------------------------------------
//  Ver   Date        Author       Description
//  ----  ----------  -----------  ---------------------------------------------------------
//  1.00  2018-06-30  Gural        Original implementation
//
//#########################################################################################


//=========================================================================================
//                      HCAMS  structures definition  
//=========================================================================================

#define  READVERSION_HCAMS    102    // Current read version number consistent with below 

struct HCAMSparameters
{
	int        readversion;          // Read version number of configuration settings file
	char       FFMPEGpath[256];      // FFMPEG path
	char       FFPROBEpath[256];     // FFPROBE path

									 //---------------------------------- FOCAL PLANE parameters
	int        nrows;                // Row dimension of each frame
	int        ncols;                // Col dimension of each frame
	int        npixels;              // Number of pixels per frame

									 //---------------------------------- CAMS COMPRESSION Parameters
	int        max_nframes_compress; // Max number of frames for compression (typically 256)

									 //---------------------------------- CLUSTER PROCESSING Parameters
	int        maxclusters;          // Max number of clusters per frame
	int        blocksize;            // Cluster blocksize in pixels
	int        interleaved;          // Interleave 0-none, 1-even/odd, 2-odd/even
	int        ntuplet;              // Number of pixels for blob (neighbors + self)
	int        datatype;             // Imagery data type (see ClusterFunctions.h mnemonics)
	double     tiny_var;             // Smallest variance per pixel
	double     saturation;           // Saturation level per pixel
	double     sfactor;              // Sigma factor for cluster exceedance count
	double     SsqNdB_threshold;     // MF signal^2 to noise variance ratio (dB)

						             //---------------------------------- TRACKER PROCESSING Parameters
	int        maxtracks;            // Max number of active tracks
	int        maxhistory;           // Max number of measurements per meteor
	int        mfirm;                // N measurements for N of M FIRM track
	int        nfirm;                // M measurements for N of M FIRM track
	int        mdrop;                // K measurements for K of L DROPPED track
	int        ndrop;                // L measurements for K of L DROPPED track
	int        ndown;                // T measurements to declare TROUBLED track

									 //---------------------------------- POST-DETECTION PROCESSING Parameters
	int        nframesMin;           // Minimum number of frames in track
	double     framerateHz_override; // Override of frame rate in Hz (-1 use file metadata)
	double     anglerate_lowerlimit; // Lower angle rate limit (arcmin/sec)
	double     anglerate_upperlimit; // Upper angle rate limit (arcmin/sec)
	int        flag_varanglerate;    // Flag to allow variable angle rate across FOV
	double     linearity_threshold;  // Max deviation from striaght line (pixels)
	double     modelfit_threshold;   // Max deviation from even spacing (pixels)
	double     modelfit_percentage;  // Max RMSE error between model fit and velocity (%)
	double     astrometry_filetime;  // Time between astrometry files (minutes)


};




//=========================================================================================
//                  Read the HCAMS parameters configuration file  
//=========================================================================================

void     ReadConfigFile_HCAMSparameters( char                    *configPathname,
	                                     struct HCAMSparameters  *params)


{
	char  text[256];
	FILE *configFile;


	//======== Set the rows and columns to zero (need to be filled in later)

	params->nrows = 0;
	params->ncols = 0;


	//======== Read the parameter settings from a configuration file

	configFile = fopen(configPathname, "rt");

	if (configFile == NULL) {
		printf(" ===> ERROR: Could not find or open HCAMS config file %s\n", configPathname);
		Delay_msec(15000);
		exit(1);
	}
	else {
		fscanf(configFile, "%[^=]= %i", text, &params->readversion);

		if (params->readversion != READVERSION_HCAMS) {
			printf(" ===> ERROR: Config file %s\n"
				"       Version number %i is outdated, use version %i\n", configPathname, params->readversion, READVERSION_HCAMS);
			Delay_msec(15000);
			exit(2);
		}

		fscanf(configFile, "%[^\n]\n",   text);

		fscanf(configFile, "%[^=]= %s",  text, params->FFMPEGpath );
		fscanf(configFile, "%[^=]= %s",  text, params->FFPROBEpath);

		fscanf(configFile, "%[^\n]\n",   text);

		fscanf(configFile, "%[^=]= %i", text, &params->max_nframes_compress);

		fscanf(configFile, "%[^\n]\n",   text);

		fscanf(configFile, "%[^=]= %i",  text, &params->maxclusters);
		fscanf(configFile, "%[^=]= %i",  text, &params->blocksize);
		fscanf(configFile, "%[^=]= %i",  text, &params->interleaved);
		fscanf(configFile, "%[^=]= %i",  text, &params->ntuplet);
		fscanf(configFile, "%[^=]= %i",  text, &params->datatype);
		fscanf(configFile, "%[^=]= %lf", text, &params->tiny_var);
		fscanf(configFile, "%[^=]= %lf", text, &params->saturation);
		fscanf(configFile, "%[^=]= %lf", text, &params->sfactor);
		fscanf(configFile, "%[^=]= %lf", text, &params->SsqNdB_threshold);

		fscanf(configFile, "%[^\n]\n",    text);

		fscanf(configFile, "%[^=]= %i",  text, &params->maxtracks);
		fscanf(configFile, "%[^=]= %i",  text, &params->maxhistory);
		fscanf(configFile, "%[^=]= %i",  text, &params->mfirm);
		fscanf(configFile, "%[^=]= %i",  text, &params->nfirm);
		fscanf(configFile, "%[^=]= %i",  text, &params->mdrop);
		fscanf(configFile, "%[^=]= %i",  text, &params->ndrop);
		fscanf(configFile, "%[^=]= %i",  text, &params->ndown);

		fscanf(configFile, "%[^\n]\n",    text);

		fscanf(configFile, "%[^=]= %i",  text, &params->nframesMin);
		fscanf(configFile, "%[^=]= %lf", text, &params->framerateHz_override);
		fscanf(configFile, "%[^=]= %lf", text, &params->anglerate_lowerlimit);
		fscanf(configFile, "%[^=]= %lf", text, &params->anglerate_upperlimit);
		fscanf(configFile, "%[^=]= %i",  text, &params->flag_varanglerate);
		fscanf(configFile, "%[^=]= %lf", text, &params->linearity_threshold);
		fscanf(configFile, "%[^=]= %lf", text, &params->modelfit_threshold);
		fscanf(configFile, "%[^=]= %lf", text, &params->modelfit_percentage);
		fscanf(configFile, "%[^=]= %lf", text, &params->astrometry_filetime);

		fclose(configFile);
	}


}

//=========================================================================================
//          Set the dimensions for HCAMS parameters configuration structure  
//=========================================================================================

void     SetDimensions_HCAMSparameters(int nrows, int ncols, struct HCAMSparameters  *params)
{

	//======== Set the rows and columns

	params->nrows = nrows;
	params->ncols = ncols;
	params->npixels = nrows * ncols;

}

