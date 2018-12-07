//#########################################################################################
//  Set of functions to write and read back H.264 compressed image sequences of 8-bit
//  gray levels using pipes. The function has an option for writing 12-bit input as 8-bit
//  by truncating the lowest 4 bits. The functions first convert to YUV420p for fast 
//  interface to the H.264 compression algorithm in libx264 (using crf level 17).
//
//  ---------------------------------------------------------------------------------------
//  Ver   Date        Author       Description
//  ----  ----------  -----------  ---------------------------------------------------------
//  1.00  2018-04-17  Gural        Original implementation
//  1.10  2018-06-23  Gural        Modified for direct YUV420 as well as 8-bit gray
//  1.20  2018-11-28  Gural        Added Linux functionality
//  1.21  2018-11-29  Gural        Added full pathnames for ffmpeg and ffprobe
//  1.22  2018-11-30  Gural        Added MP4 video snippet generation function
//
//#########################################################################################

//=========================================================================================
//========    Global structures to keep persistently between function calls        ========
//=========================================================================================

struct  FFMPEG_Global
{
	int             conversion_type;  // 0:  Gray12bits  <->  RGB  <->  YUV420P  <->  H.264
									  // 1:  Gray12bits            <->  YUV420P  <->  H.264
	                                  // 2:  Gray8bits             <->  YUV420P  <->  H.264
	int             nrows;
	int             ncols;
	int             npixels;
	int             nbytes;
	unsigned char  *array;
	FILE           *pipe;

};

struct FFMPEG_Global   Ginp,  Gout;



//=========================================================================================
//========   Function prototypes for reading and writing H.264 compressed files    ========
//=========================================================================================

void     Gray12bit_to_RGBpacked( unsigned short         *gray12bits,
	                             unsigned char          *rgb,
	                             int                     npixels  );

void     RGBpacked_to_Gray12bit( unsigned char          *rgb,
	                             unsigned short         *gray12bits,
	                             int                     npixels  );

void     Gray12bit_to_YUVpacked( unsigned short         *gray12bits,
	                             unsigned char          *yuv,
	                             int                     npixels  );

void     YUVpacked_to_Gray12bit( unsigned char          *yuv,
	                             unsigned short         *gray12bits,
	                             int                     npixels  );

void      Gray8bit_to_YUVpacked( unsigned char          *gray8bits,
	                             unsigned char          *yuv,
	                             int                     npixels  );

void      YUVpacked_to_Gray8bit( unsigned char          *yuv,
	                             unsigned char          *gray8bits,
	                             int                     npixels  );

//-----------------------------------------------------------------------------------------

void     Write_FFMPEG_Pipe_Open( char                   *FFMPEGpath,
	                             int                     conversion_type,
	                             char                   *filename,
	                             int                     nrows,
	                             int                     ncols,
	                             float                   framerate  );

void    Write_FFMPEG_Pipe_Image( unsigned char          *image_uchar, //...use either per conversion_type
	                             unsigned short         *image_ushort );

void    Write_FFMPEG_Pipe_Close( );

//-----------------------------------------------------------------------------------------

void      Read_FFMPEG_Pipe_Open( char                   *FFMPEGpath,
	                             char                   *FFPROBEpath,
	                             int                     conversion_type,
	                             char                   *filename,
	                             int                    *nrows,
	                             int                    *ncols,
	                             int                    *nframes,
                                 float                  *framerate  );

int      Read_FFMPEG_Pipe_Image( unsigned char          *image_uchar,  //...use either per conversion_type
	                             unsigned short         *image_ushort );

void    Read_FFMPEG_Pipe_Close( );

//-----------------------------------------------------------------------------------------

void          WriteVideoSnippet( char                   *FFMPEGpath,
	                             char                   *video_filename_inp,
	                             char                   *video_filename_out,
	                             double                  start_time_seconds,
	                             double                  duration_seconds );




//#########################################################################################

//=========================================================================================
//   Convert pixels from 12 bit gray to RGB 8-bit packed such that the highest 8 bits of  
//     each pixel (bits 5-12) are mapped to bits 1-8 of each 8-bit RGB color channel. The 
//     output is stored RGBRGBRGB...
//=========================================================================================

void     Gray12bit_to_RGBpacked( unsigned short         *gray12bits,
	                             unsigned char          *rgb,
	                             int                     npixels)
{
	int    kpixel, krgb;

	krgb = 0;

	for (kpixel = 0; kpixel < npixels; kpixel++) {
		rgb[krgb + 0] = (unsigned char)(gray12bits[kpixel] >> 4);
		rgb[krgb + 1] = (unsigned char)(gray12bits[kpixel] >> 4);
		rgb[krgb + 2] = (unsigned char)(gray12bits[kpixel] >> 4);
		krgb += 3;
	}

}


//=========================================================================================
//   Unpack 8-bit RGB pixels into 12 bit gray by inverting the process in the function
//     Gray12bit_to_RGBpacked. An average of the RGB color space per pixel is used to
//     find the mean gray value and scaled up by a 4 bit shift.
//=========================================================================================

void     RGBpacked_to_Gray12bit( unsigned char          *rgb,
	                             unsigned short         *gray12bits,
	                             int                     npixels)
{
	int    kpixel, krgb;

	krgb = 0;

	for (kpixel = 0; kpixel < npixels; kpixel++) {
		gray12bits[kpixel] = ( (((unsigned short)rgb[krgb + 0]) << 4)
			                 + (((unsigned short)rgb[krgb + 1]) << 4)
			                 + (((unsigned short)rgb[krgb + 2]) << 4) ) / 3;
		krgb += 3;
	}

}


//=========================================================================================
//   Convert pixels from 12 bit gray to YUV420p packed such that the highest 8 bits of  
//     each gray pixel (bits 5-12) is mapped to the luminance and the two chrominance
//     images (2x2 decimated) are both 128 filled.
//=========================================================================================

void     Gray12bit_to_YUVpacked( unsigned short         *gray12bits,
	                             unsigned char          *yuv,
	                             int                     npixels)
{
	int    kpixel;

	memset( yuv, 128, 3 * npixels/ 2 );

	for (kpixel = 0; kpixel < npixels; kpixel++) {
		yuv[kpixel] = (unsigned char)(gray12bits[kpixel] >> 4);
	}

}

//=========================================================================================
//   Unpack 8-bit YUV420p luminance values into 12 bit gray by inverting the process in 
//     Gray12bit_to_YUVpacked.
//=========================================================================================

void     YUVpacked_to_Gray12bit( unsigned char          *yuv,
	                             unsigned short         *gray12bits,
	                             int                     npixels)
{
	int    kpixel;

	for (kpixel = 0; kpixel < npixels; kpixel++) {
		gray12bits[kpixel] = ((unsigned short)yuv[kpixel]) << 4;
	}

}


//=========================================================================================
//   Convert pixels from 8 bit gray to YUV420p packed such that the 8 bits of  
//     each gray pixel is mapped to the luminance and the two chrominance
//     images (2x2 decimated) are both 128 filled.
//=========================================================================================

void      Gray8bit_to_YUVpacked( unsigned char          *gray8bits,
	                             unsigned char          *yuv,
	                             int                     npixels)
{

	memset( yuv, 128, 3 * npixels/ 2 );

	memcpy( yuv, gray8bits, npixels );

}


//=========================================================================================
//   Unpack 8-bit YUV420p luminance values into 12 bit gray by inverting the process in 
//     Gray12bit_to_YUVpacked.
//=========================================================================================

void      YUVpacked_to_Gray8bit( unsigned char          *yuv,
	                             unsigned char          *gray8bits,
	                             int                     npixels)
{

    memcpy( gray8bits, yuv, npixels );

}


//=========================================================================================
//  Use FFMPEG with a pipe to send sequences of 12-bit gray scale images to a H.264 
//  compressed MPEG4 file. Converts to a special RGB packed format followed by
//  FFMPEG conversion to YUV420P for H.264 compatibility.
//=========================================================================================

void     Write_FFMPEG_Pipe_Open( char                   *FFMPEGpath,
	                             int                     conversion_type,
	                             char                   *filename,
	                             int                     nrows,
	                             int                     ncols,
	                             float                   framerate )
{
char  cmd[256];


    Gout.conversion_type = conversion_type;

	//======== Open the FFMPEG pipe assuming RGB input and H.264 YUV420p output.
	//         Windows expects the full path *\ffmpeg.exe with exe extension
	//         Linux does not use the .exe extension

	if (Gout.conversion_type == 0)  sprintf(cmd, "%s -loglevel warning -y -f rawvideo -pixel_format rgb24   -s %ix%i -r %i -i - -crf 17 -an -vcodec libx264 -pix_fmt yuv420p %s\n", FFMPEGpath, ncols, nrows, (int)(framerate + 0.5f), filename);
	if (Gout.conversion_type == 1)  sprintf(cmd, "%s -loglevel warning -y -f rawvideo -pixel_format yuv420p -s %ix%i -r %i -i - -crf 17 -an -vcodec libx264 -pix_fmt yuv420p %s\n", FFMPEGpath, ncols, nrows, (int)(framerate + 0.5f), filename);
	if (Gout.conversion_type == 2)  sprintf(cmd, "%s -loglevel warning -y -f rawvideo -pixel_format yuv420p -s %ix%i -r %i -i - -crf 17 -an -vcodec libx264 -pix_fmt yuv420p %s\n", FFMPEGpath, ncols, nrows, (int)(framerate + 0.5f), filename);

    #ifdef _WIN32 
        Gout.pipe = _popen(cmd, "wb");
    #else  /* LINUX */
	    Gout.pipe = popen(cmd, "w");
    #endif

    if (Gout.pipe == NULL)  {
		printf(" FFMPEG pipe not opened in Write_FFMPEG_Pipe_Open\n");
		Delay_msec(20000);
		exit(1);
    }


	Gout.nrows   = nrows;
	Gout.ncols   = ncols;
	Gout.npixels = nrows * ncols;

	if (Gout.conversion_type == 0)  Gout.nbytes = 3 * Gout.npixels;
	if (Gout.conversion_type == 1)  Gout.nbytes = 3 * Gout.npixels / 2;
	if (Gout.conversion_type == 2)  Gout.nbytes = 3 * Gout.npixels / 2;

	//... allocate memory for writes

	Gout.array = (unsigned char*)malloc(Gout.nbytes * sizeof(unsigned char));

	  

}

//----------------------------------------------------------------------------------------

void     Write_FFMPEG_Pipe_Image( unsigned char          *image_uchar, //...use either per conversion_type
	                              unsigned short         *image_ushort )
{

	//======== Do not perform write if pipe is not opened yet

	if (Gout.pipe == NULL)  return;


	//======== Convert gray scale image to intermediate format

	if (Gout.conversion_type == 0)  Gray12bit_to_RGBpacked(image_ushort, Gout.array, Gout.npixels);
	if (Gout.conversion_type == 1)  Gray12bit_to_YUVpacked(image_ushort, Gout.array, Gout.npixels);
	if (Gout.conversion_type == 2)   Gray8bit_to_YUVpacked(image_uchar,  Gout.array, Gout.npixels);


	//======== Write each packed image to the pipe. FFMPEG will convert to YUV420P, encode it for
	//           H.264 compression using libx264, and write compressed packets to the file.

	fwrite(Gout.array, 1, Gout.nbytes, Gout.pipe);


}

//----------------------------------------------------------------------------------------

void     Write_FFMPEG_Pipe_Close( )
{

	//======== Do not close pipe if pipe is not opened yet

	if (Gout.pipe == NULL)  return;


	//======== After last image written to the pipe, flush and close the pipe/file.

	fflush(Gout.pipe);

    #ifdef _WIN32 
	    _pclose(Gout.pipe);
    #else  /* LINUX */
	    pclose(Gout.pipe);
    #endif

	Gout.pipe = NULL;

	free( Gout.array );


}


//=========================================================================================
//  Use FFMPEG with a pipe to to obtain 12 or 8 bit gray scale images from a H.264 
//  compressed MPEG4 file. Converts from the YUV420P format mapped back to gray from
//  the luminance. May have intermediate RGB product for conversion type 0.
//=========================================================================================

void     Read_FFMPEG_Pipe_Open( char                   *FFMPEGpath,
	                            char                   *FFPROBEpath,
	                            int                     conversion_type,
	                            char                   *filename,
	                            int                    *nrows,
	                            int                    *ncols,
	                            int                    *nframes,
	                            float                  *framerate )
{
int    num, den;
char   cmd[256];
FILE  *paramfile;


    Ginp.conversion_type = conversion_type;

    //======== Make sure the input pipe is free

    if (Ginp.pipe != NULL) {
		printf(        "ERROR: Trying to open a new FFMPEG read pipe before previous one is closed\n");
		fprintf(stderr,"ERROR: Trying to open a new FFMPEG read pipe before previous one is closed\n");
		Delay_msec(10000);
		exit(1);
	}

    
    //======== Get some parameters from the MPEG4 file using FFPROBE
	//         Windows expects the full path *\ffprobe.exe with exe extension
	//         Linux expects the full path but does not use the .exe extension


    sprintf(cmd, "%s -v error -select_streams v:0 -show_entries stream=width,height,avg_frame_rate,nb_frames -of default=noprint_wrappers=1 %s > MPEGfileinfo.txt\n", FFPROBEpath, filename);

    system(cmd);

	paramfile = fopen("MPEGfileinfo.txt", "rt");

	fscanf(paramfile, "width=%i\n",  ncols);
	fscanf(paramfile, "height=%i\n", nrows);
	fscanf(paramfile, "avg_frame_rate=%i/%i\n", &num, &den);
	fscanf(paramfile, "nb_frames=%i\n", nframes);

	*framerate = (float)num / (float)den;

	fclose(paramfile);


	//======== Open the FFMPEG pipe assuming RGB input and H.264 YUV420p output.
	//         Windows expects the full path *\ffmpeg.exe with exe extension
	//         Linux expects the full path but does not use the .exe extension

	if (Ginp.conversion_type == 0)  sprintf(cmd, "%s -loglevel fatal -i %s -f image2pipe -vcodec rawvideo -pix_fmt rgb24 -flags +global_header  -\n", FFMPEGpath, filename);
	if (Ginp.conversion_type == 1)  sprintf(cmd, "%s -loglevel fatal -i %s -f image2pipe -vcodec rawvideo -pix_fmt yuv420p -flags +global_header -\n", FFMPEGpath, filename);
	if (Ginp.conversion_type == 2)  sprintf(cmd, "%s -loglevel fatal -i %s -f image2pipe -vcodec rawvideo -pix_fmt yuv420p -flags +global_header -\n", FFMPEGpath, filename);
      printf("MIKE : %s", cmd);

    // NOTE: For some reason loglevel must be fatal (rather than warning) or error message
	//        pops up when _pclose is called

    #ifdef _WIN32 
	    Ginp.pipe = _popen(cmd, "rb");
    #else  /* LINUX */
	    Ginp.pipe = popen(cmd, "r");
    #endif
	
    if (Ginp.pipe == NULL)  {
		printf(" FFMPEG pipe not opened in Read_FFMPEG_Pipe_Open\n");
		Delay_msec(20000);
		exit(1);
    }

	Ginp.nrows   = *nrows;
	Ginp.ncols   = *ncols;
	Ginp.npixels = *nrows * *ncols;

	if (Ginp.conversion_type == 0)  Ginp.nbytes = 3 * Ginp.npixels;
	if (Ginp.conversion_type == 1)  Ginp.nbytes = 3 * Ginp.npixels / 2;
	if (Ginp.conversion_type == 2)  Ginp.nbytes = 3 * Ginp.npixels / 2;

	//... allocate memory for writes

	Ginp.array = (unsigned char*)malloc(Ginp.nbytes * sizeof(unsigned char));;


}


//----------------------------------------------------------------------------------------

int     Read_FFMPEG_Pipe_Image( unsigned char          *image_uchar, //...use either per conversion_type
	                            unsigned short         *image_ushort )
{
int  nbytes_read;


	//======== Do not perform read if pipe is not opened yet

	if (Ginp.pipe == NULL)  return(1);  //... No pipe opened


	//======== Read each RGB image from the pipe. FFMPEG will convert to YUV420P, encode it for
	//           H.264 compression using libx264, and write compressed packets to the file.

	nbytes_read = (int) fread(Ginp.array, 1, Ginp.nbytes, Ginp.pipe);

	if (nbytes_read != Ginp.nbytes) {  //... Check proper number of bytes read

		Read_FFMPEG_Pipe_Close();

		return(2);  //... EOF

	}


	//======== Convert custom RGB or YUV packed format to a gray scale 12 or 8  bit image

	if (Ginp.conversion_type == 0)  RGBpacked_to_Gray12bit(Ginp.array, image_ushort, Ginp.npixels);
	if (Ginp.conversion_type == 1)  YUVpacked_to_Gray12bit(Ginp.array, image_ushort, Ginp.npixels);
	if (Ginp.conversion_type == 2)  YUVpacked_to_Gray8bit (Ginp.array, image_uchar,  Ginp.npixels);

	return(0);  //... Normal return of gray image

}

//----------------------------------------------------------------------------------------

void     Read_FFMPEG_Pipe_Close()
{

	//======== Do not close pipe if pipe is not opened yet

	if (Ginp.pipe == NULL)  return;


	//======== After last image written to the pipe, flush and close the pipe/file.

	fflush(Ginp.pipe);

    #ifdef _WIN32 
	    _pclose(Ginp.pipe);
    #else  /* LINUX */
	    pclose(Ginp.pipe);
    #endif
	
	Ginp.pipe = NULL;

	free( Ginp.array );

}


//=========================================================================================
//  Use FFMPEG to create an extracted subset video file from a larger video file of the 
//  same file type and compression codec. User specifies the start time for the first 
//  frame to extract and the duration, both in seconds.
//=========================================================================================

void     WriteVideoSnippet( char      *FFMPEGpath,
	                        char      *video_filename_inp,
	                        char      *video_filename_out,
	                        double     start_time_seconds,
	                        double     duration_seconds  )
{
char  cmd[256];


	sprintf(cmd, "%s -flags +global_header -loglevel warning -i %s -y -ss %.3lf -t %.3lf -c copy %s\n", 
		         FFMPEGpath, video_filename_inp, start_time_seconds, duration_seconds, video_filename_out);

	system(cmd);

}
