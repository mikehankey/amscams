
//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%                                                                         %%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%       Unsigned Char Image Compression Functions for 1-Byte Data        %%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%                                                                         %%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%             Uses Maximum Temporal Pixel MTP compression                 %%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%                                                                         %%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//
//  MTPcompression_UChar is the 8-bit version of a compressed file generation, storage, and retrieval 
//    interface with contents of #rows, #cols, #frames/block, 1st_frame#, camera#, frame rate in Hz,
//    and arrays for maxpixel, frame#_of_maxpixel, mean_with_max_removed, stddev_with_max_removed. 
//    The mean and stddev are designed to exclude the NHIGHVAL highest temporal values per pixel to 
//    avoid contamination from bright meteors with long lasting trains on a given pixel. The file 
//    naming convention is FF_camera_yymmdd_hhmmss_msc_frameno.bin with content unsigned char imagery.
//
//  Date         Change Comment
//  ----------   ---------------------------------------------------------------------------------------
//  2016-08-07   Final implementation as evolved from MTPcompression_UShort
//
//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%



//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%                                                %%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%              Structure Definitions             %%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%                                                %%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

#define  NHIGHVAL  4  // Specifies the number of highest value pixels removed from mean and stddev calc

struct  pixelinfo_UC
{                   
	//------------- Pixel level work structure during capture/compression
    unsigned short  sumpixel;           // Temporal pixel sum 
    long            ssqpixel;           // Temporal pixel squared_ptr sum
	unsigned char   highsort[NHIGHVAL]; // Sorted high pixel values
	unsigned char   maxframe;           // Frame number of temporal maximum pixel 
    unsigned char   numequal;           // Number of equal maximum pixel values 
};

//======================================================================================================

struct  rowcolval_UC
{                   
	//------------- Pixel content info for maxpixel values of a specified frame number
    unsigned short  row;           // row index 
    unsigned short  col;           // col index 
	unsigned char   val;           // maxpixel minus mean value
};

//======================================================================================================

struct  MTP_UC_compressor
{                   
	//------------- Compressed image and file descriptive parameters
	long            FFversion;          // Version number of the FF file
    long            cameranumber;       // Integer camera designation 1 - 999
	long            firstframe;         // First frame number of this FF data block
    long            totalframes;        // Total frames in this compression sequence <= 256
    long            nrows;              // Number of rows in the image
    long            ncols;              // Number of columns in the image
	long            ndecim;             // Decimation factor
	long            interleave;         // Interleave: 0=progressive, 1=odd/even, 2=even/odd
	double          framerateHz;        // Frame rate in Hz
	char            camerafolder[256];  // Full pathname of the compressed data folder
    char            FFpathname[256];    // Full pathname of FF file
    char            FFfilename[256];    // File name only of FF file

	//------------- Information to hold for FF file write during next block capture/compress
	//              and after ingest from an FF data file. Includes compressed image array 
	//              components where in each array, the pixels are memory sequential
    char            WritFFpathname[256];// Output full pathname spec'd by 1st frame in sequence
    char            WritFFfilename[256];// Output FF filename only spec'd by 1st frame in sequence
	unsigned char  *maxpixel_ptr;       // Pointer to the temporal maximum pixel array
    unsigned char  *maxframe_ptr;       // Pointer to the frame number of the max pixel array
    unsigned char  *avepixel_ptr;       // Pointer to the temporal average pixel array
    unsigned char  *stdpixel_ptr;       // Pointer to the temporal standard deviation array

    //............. Work storage buffers at the pixel level for current block of imagery
	struct pixelinfo_UC  *pixel_ptr;       // Pointer to the pixelinfo_UC structure (nrows*ncols)
	                                       // Note the structure is sequential in memory and
	                                       //   thus any specific pixel attribute is not. For
	                                       //   example the maxframe value jumps by the
	                                       //   sizeof(pixelinfo_UC) to get to the next pixel.
	long                  Nrcval;          // Number of maxpixels in the rowcolmax structure
	struct rowcolval_UC  *rcval_ptr;       // Pointer to the rowcolmax structure (variable length)

	//------------- Pre-computed LUTs for efficient compression processing
	unsigned short *squared_ptr;        // Square of integer numbers from 0 to 255
	unsigned char  *squareroot_ptr;     // Square root resulting in values from 0 to 255
	unsigned char  *gauss128_ptr;       // Guassian 1 sigma noise scaled by 128
    unsigned short *randomN_ptr;        // Inverse of 65536 uniform random numbers between 0 and 1
    long            randcount;          // Position index in the random number vector

	//------------- Reconstructed image support arrays and scaler components
    unsigned char  *imgframe_ptr;       // Pointer to a reconstructed image frame
    long           *mpoffset_ptr;       // Pointer to the pointer offset into the maxpixel array
    long           *mpcumcnt_ptr;       // Pointer to the cumulative sum of the frame count
    long           *framecnt_ptr;       // Pointer to the frame counter histogram of maxpixel
    unsigned char   global_ave;         // Global median of the FOV mean
    unsigned char   global_std;         // Global median of the FOV standard deviation

};



//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%                                                %%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%        Function Prototype Declarations         %%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%                                                %%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

int      MTPcompression_UChar_GetTimeofDay( long *seconds_jan1st1970,            //millisecond accuracy date/time (Windows)
								            long *microseconds            );


void         MTPcompression_UChar_MemSetup( long                        image_nrows,    //allocate memory and set parameters
                                            long                        image_ncols,
                                            long                        nframes,
                                            long                        cameranumber,
											long                        ndecim,
											long                        interleave,
								            double                      framerateHz,
                                            char                       *camerafolder,
                                            struct MTP_UC_compressor   *imagecmp );
                              
                     
void         MTPcompression_UChar_Compress( long                        framenumber,     //compress newest frame into sequence
                                            unsigned char              *image_ptr,
                                            long                        image_nrows,
                                            long                        image_ncols,
                                            struct MTP_UC_compressor   *imagecmp );

void         MTPcompression_UChar_Products( struct MTP_UC_compressor   *imagecmp );      //post block's last frame compression product generation

                                                            
void         MTPcompression_UChar_Filename( long                        framenumber,     //generate FF filename from current PC date/time, frm#
                                            struct MTP_UC_compressor   *imagecmp );

void       MTPcompression_UChar_FFpathname( long framenumber,  
	                                        long cameranumber,                           //generate FF filename from cam#, specified date/time, frm#
	                                        long utyear, long utmonth,  long utday,      
									        long uthour, long utminute, long utsecond, long utmilliseconds,
											char                       *FFfolder,
											char                       *FFfilename,
											char                       *FFpathname );
                              
void    MTPcompression_UChar_FilenameParse( char                       *FFpathname,      //extract date/time, cam#, frm# from pathname or filename
                                            long                       *year,
                                            long                       *month,
                                            long                       *day,
                                            long                       *hour,
                                            long                       *minute,
                                            long                       *second,
                                            long                       *milliseconds,
							                long                       *cameranumber, 
								            long                       *framenumber );
                              
void         MTPcompression_UChar_DateTime( long                       *year,
                                            long                       *month,
                                            long                       *day,
                                            long                       *hour,
                                            long                       *minute,
                                            long                       *second,
                                            long                       *milliseconds );  //get the UT date and time to the millisecond

void        MTPcompression_UChar_FileWrite( struct MTP_UC_compressor   *imagecmp );      //max,frame#,mean,stddev,aftermax to file
                             
int      MTPcompression_UChar_FileValidity( char                       *FFpathname );    //checks validity of file parameters

void         MTPcompression_UChar_FileRead( char                       *FFpathname,      //read max,frame#,mean,stddev from file
                                            struct MTP_UC_compressor   *imagecmp );      //   and populate imagecmp structure

void       MTPcompression_UChar_PrepBuild( struct MTP_UC_compressor   *imagecmp );      //finds pointer offsets to maxpixel per frame#

void        MTPcompression_UChar_RowColVal( long                        fileframenumber, //fills rowcolval_UC structure for user frame number
                                            struct MTP_UC_compressor   *imagecmp );
                                                   
void       MTPcompression_UChar_FrameBuild( long                        fileframenumber, //build imgframe from the mean and fill-in
								            struct MTP_UC_compressor   *imagecmp );      //   with the frame number requested
                              
void       MTPcompression_UChar_GlobalMean( struct MTP_UC_compressor   *imagecmp );      //find the global median of the mean image
                              
void      MTPcompression_UChar_GlobalSigma( struct MTP_UC_compressor   *imagecmp );      //find the global median of sigma (std dev)
                              
                              
void          MTPcompression_UChar_Flatten( short                      *flattened_ptr,   //flattened = 128*(prebuilt_imgframe-mean)/sigma
                                            struct MTP_UC_compressor   *imagecmp );
                              
void     MTPcompression_UChar_BuildFlatten( short                      *flattened_ptr,   //flattened = 128*(build_imgframe-mean)/sigma
                                            long                        fileframenumber,
                                            struct MTP_UC_compressor   *imagecmp );

void     MTPcompression_UChar_NoiseFlatten( short                      *flattened_ptr,   //flattened = 128*gauss_random_draw
                                            long                        fileframenumber,
                                            struct MTP_UC_compressor   *imagecmp );

void      MTPcompression_UChar_MeanRemoval( short                      *demean_ptr, 
                                            struct MTP_UC_compressor   *imagecmp );
                              
                              
void       MTPcompression_UChar_MemCleanup( struct MTP_UC_compressor   *imagecmp );      //free all allocated memory

void     MTPcompression_UChar_NullPointers( struct MTP_UC_compressor   *imagecmp );      //NULL all pointers

double    MTPcompression_UChar_Gauss3Sigma( double                      sigma    );      //Normal distributed limit to 3 sigma
