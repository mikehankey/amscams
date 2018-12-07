
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



//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%                                                %%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%   Include Statements for C Library Functions   %%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%                                                %%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

#pragma warning(disable: 4996)  // disable warning on strcpy, fopen, ...

#include <stdio.h>         // fopen, fread, fwrite, fclose, getchar, printf 
#include <time.h>          // gmt, gmtime, tm_*
#include <math.h>          // intrinsic math functions: sqrt
#include <string.h> 
#include <stdlib.h> 

#ifdef _WIN32
   #include <windows.h>    // stuff in gettimeofday function
#else  // LINUX //
   #include <unistd.h>
#endif
                     
#include "MTPcompression_Uchar.h"


//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%                                                %%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%         MTP Compression Functions              %%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%                                                %%%%%%%%%%%%%%%%%%%%%%%%%%%%%
//%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


//#######################################################################################################
//                             MTPcompression_UChar_MemSetup
//
//  Compression structure initialization called a single time after program startup, once the 
//  image dimensions, number of frames per block, camera number, framerate in Hertz, and the
//  output destination folder for the compressed files are known. Recommend calling 
//  MTPcompression_UChar_NullPointers first (immediately after program startup), followed 
//  later by MTPcompression_UChar_MemSetup once the argument list parameters are all available.
//
//  The function allocates memory for all compression structure arrays and vectors. Call the
//  function MTPcompression_UChar_MemCleanup once ALL compression processing is completed, to  
//  free memory at the end of the program.
//
//#######################################################################################################


void     MTPcompression_UChar_MemSetup( long                        image_nrows,
                                        long                        image_ncols,
                                        long                        totalframes,
                                        long                        cameranumber,
										long                        ndecim,
										long                        interleave,
							            double                      framerateHz,
                                        char                       *camerafolder,
                                        struct MTP_UC_compressor   *imagecmp )
{
long  k, nrc, arand;


   //----- Make sure memory is released for this imagecmp structure and set version

   MTPcompression_UChar_MemCleanup( imagecmp );

   imagecmp->FFversion = -1;   // CAMS new FF file format designation for 8-bit


   //----- Set the output destination folder for Windows or Linux

   #ifdef _WIN32
      if( camerafolder == NULL ) strcpy( imagecmp->camerafolder, "./"         );
      else                       strcpy( imagecmp->camerafolder, camerafolder );
   #else //LINUX
      if( camerafolder == NULL ) strcpy( imagecmp->camerafolder, "."          );
      else                       strcpy( imagecmp->camerafolder, camerafolder );
   #endif


   //----- Check and save the number of frames for compressing the imagery block
   
   if( totalframes < 8  ||  totalframes > 256 )  {
       printf(" ERROR:  Totalframes must be between 8 and 256 in MTPcompression_UChar_MemSetup\n");
       #ifdef _WIN32    
	       Sleep(15000);
       #else            
	       sleep((unsigned int)(15));
       #endif
	   exit(1);
   }
   
   imagecmp->totalframes = totalframes;
 

   //----- Set the framerate, image dimensions, and camera number

   imagecmp->framerateHz  = framerateHz;

   imagecmp->nrows        = image_nrows;
   
   imagecmp->ncols        = image_ncols;
   
   imagecmp->cameranumber = cameranumber;

   imagecmp->ndecim       = ndecim;

   imagecmp->interleave   = interleave;


   //-----Allocate memory for all arrays and vectors

   nrc = (long)image_nrows * (long)image_ncols;
    
   imagecmp->maxpixel_ptr   = (unsigned char*)  malloc( nrc * sizeof(unsigned char)  );  
   imagecmp->maxframe_ptr   = (unsigned char*)  malloc( nrc * sizeof(unsigned char)  );  
   imagecmp->avepixel_ptr   = (unsigned char*)  malloc( nrc * sizeof(unsigned char)  );  
   imagecmp->stdpixel_ptr   = (unsigned char*)  malloc( nrc * sizeof(unsigned char)  );
      
   imagecmp->imgframe_ptr   = (unsigned char*)  malloc( nrc * sizeof(unsigned char)  );
   imagecmp->mpoffset_ptr   = (         long*)  malloc( nrc * sizeof(         long)  );
   imagecmp->mpcumcnt_ptr   = (         long*)  malloc( imagecmp->totalframes * sizeof( long )  );
   imagecmp->framecnt_ptr   = (         long*)  malloc( imagecmp->totalframes * sizeof( long )  );  
   
   imagecmp->randomN_ptr    = (unsigned short*)  malloc( 65536L * sizeof(unsigned short)  );
   imagecmp->squared_ptr    = (unsigned short*)  malloc(   256L * sizeof(unsigned short)  );
   imagecmp->squareroot_ptr = (unsigned char* )  malloc( 65536L * sizeof(unsigned char )  );
   imagecmp->gauss128_ptr   = (unsigned char* )  malloc( 65536L * sizeof(unsigned char )  );

   imagecmp->pixel_ptr      = (struct pixelinfo_UC*) malloc( nrc * sizeof( struct pixelinfo_UC ) );


   if( imagecmp->pixel_ptr          == NULL ||
	   imagecmp->maxpixel_ptr       == NULL ||
	   imagecmp->maxframe_ptr       == NULL ||
	   imagecmp->avepixel_ptr       == NULL ||
	   imagecmp->stdpixel_ptr       == NULL ||
	   imagecmp->imgframe_ptr       == NULL ||   
	   imagecmp->mpoffset_ptr       == NULL ||
	   imagecmp->framecnt_ptr       == NULL ||
	   imagecmp->mpcumcnt_ptr       == NULL ||
	   imagecmp->randomN_ptr        == NULL ||
	   imagecmp->squared_ptr        == NULL ||
	   imagecmp->squareroot_ptr     == NULL ||
	   imagecmp->gauss128_ptr       == NULL    )  {
       printf(" ERROR:  Memory not allocated in MTPcompression_UChar_MemSetup\n");
       #ifdef _WIN32    
	       Sleep(15000);
       #else            
	       sleep((unsigned int)(15));
       #endif
	   exit(1);
   }


   //----- Set the look-up-table (LUT) values for squared_ptr and square roots of integers

   for( k=0; k<256L;   k++ )  imagecmp->squared_ptr[k] = (unsigned short)( k * k );
   
   for( k=0; k<65536L; k++ )  imagecmp->squareroot_ptr[k] = (unsigned char) sqrt( (double)k );
   
   imagecmp->squareroot_ptr[0] = 1;  //... to avoid divide by zero when whitening


   //----- Set the random number selection to ensure repeated maxpixel value get maxframe numbers
   //        distributed evenly in time (frame number). Uses a very simple random number generator.

   arand = 1;
   
   for( k=0; k<65536L; k++ )  {  //... equivalent to (double)RAND_MAX / (double)rand()
   
        arand = ( arand * 32719L + 3L ) % 32749L;
   
        imagecmp->randomN_ptr[k] = (unsigned short)( 32749.0 / (double)(1 + arand) );

		imagecmp->gauss128_ptr[k] = (unsigned char) MTPcompression_UChar_Gauss3Sigma( 128.0 );
   }
   
   imagecmp->randcount = 0;


   //----- Set the startup file and path names to blank

   strcpy( imagecmp->FFpathname, " " );
   strcpy( imagecmp->FFfilename, " " );

   	
   //-------- Clear the entire memory contents of the per pixel work structure and maxpixel offsets

   memset( imagecmp->pixel_ptr, 0, image_nrows * image_ncols * sizeof( struct pixelinfo_UC ) );

   memset( imagecmp->mpoffset_ptr, 0, image_nrows * image_ncols * sizeof(unsigned long) );
   
}


//#######################################################################################################
//                              MTPcompression_UChar_Compress
//
//  Primary user function to compress an imagery block of "totalframes" images on-the-fly. 
//  The function is called once per image frame in temporally (frame number) increasing order. 
//  The compression works through a block of imagery of duration "totalframes" and then 
//  restarts on the next block of data. The start is triggered when the "framenumber" modulo
//  "totalframes" equals zero (Note that prior to the modulo zero call to this function,
//  one must call MTPcompression_UChar_Products to have the previous block's filename copied to 
//  the "WritFFpathname", and the previous block's compression products computed and copied off,  
//  at which point the products can be written out using MTPcompression_UChar_FileWrite or used
//  directly in processing while the next block of frames is compressed).
//  The sequence continues compressing a given block of imagery through "framenumber" modulo
//  "totalframes" equals totalframes-1. Then once the modulo cycles back to zero all the 
//  working arrays are reset. Having the separate function MTPcompression_UChar_Products
//  allows the user to hold off starting a new compression sequence until the computing of
//  a previous sequence is ensured to be completed (also to wait for the previus FF file to be
//  written and closed BEFORE the next compression call where modulo = 0). This provides 
//  totalframes worth of time to elapse to write the file plus any additional time if paused 
//  at the completion of the last block of data (AFTER the call when modulo = totalframes-1).
//
//         IMPORTANT NOTE: Do not start writing the latest complete block until 
//                         MTPcompression_UChar_Poducts is called. This same holds
//                         true for processing data from the last block of frames.
//
//  Note that the image_ptr array must be dimensioned exactly as the compression structure's
//  internal allocation of nrows x ncols in column preference order.
//
//  The compression keeps track of the NHIGHVAL highest values per pixel to remove them from
//  the mean and standard deviation calculation to minimize their contamination by meteors. It
//  employs an insertion sort technique for very fast sorting of short lists. The compression 
//  also checks for repeated instances of the maxpixel value of a given pixel and uses a 
//  randomization formula to evenly distribute those in time (frame number).
//
//#######################################################################################################


void     MTPcompression_UChar_Compress( long                        framenumber,  // starts at zero and increments externally
                                        unsigned char              *image_ptr,    
                                        long                        image_nrows,
                                        long                        image_ncols,
                                        struct MTP_UC_compressor   *imagecmp )
{
long                  kthrow, kthcol, randcount, ksort;
unsigned char         datum, framemodulo;
unsigned char        *datum_ptr;
struct pixelinfo_UC  *pixel_ptr;


  //======== Test for valid dimensionality of incoming image frame

  if( image_nrows != imagecmp->nrows  ||  image_ncols != imagecmp->ncols )  {
  
       printf("Mismatch of number of rows or columns in call to MTPcompression_UChar_Compress \n");
       #ifdef _WIN32    
	       Sleep(15000);
       #else            
	       sleep((unsigned int)(15));
       #endif
	   exit(1);
  }
    
  
  //======== Set framemodulo to fall between 0 (first frame in the block) 
  //         and totalframes - 1 (last frame in the block)
    
  framemodulo = (unsigned char)( framenumber % imagecmp->totalframes );

  
  
  //======== First call for the next block sequence of images

  if( framemodulo == 0 )  {


      //-------- Build the new block's filename from the camera number, date/time, and framenumber
      
      MTPcompression_UChar_Filename( framenumber, imagecmp );


	  //-------- Assign the working pixelinfo_UC structure pointer.

	  pixel_ptr    = imagecmp->pixel_ptr;

	  datum_ptr    = image_ptr;

	   
      //-------- Initialize the intermediate products for the next block
	  //           given the first image frame.
    
      for( kthrow=0; kthrow<image_nrows; kthrow++ )  {          // Loop over image frame rows

          for( kthcol=0; kthcol<image_ncols; kthcol++ )  {     // Loop over image frame columns

 				//-------- Initialize the pixelinfo_UC contents for the new block's first frame

			    datum = *datum_ptr++;                           // Pull pixel value, increment to next pixel
       
				pixel_ptr->sumpixel = (unsigned short)datum;           // Temporal pixel sum
            
                pixel_ptr->ssqpixel = imagecmp->squared_ptr[ datum ];  // Temporal pixel-squared_ptr sum

 				pixel_ptr->highsort[0] = datum;                 // Set highest pixel value thus far

				for( ksort=1; ksort<NHIGHVAL; ksort++ )  pixel_ptr->highsort[ksort] = 0;

				pixel_ptr->maxframe = 0;                        // Maxpixel frame number is first frame = 0

                pixel_ptr->numequal = 1;                        // Set number of repeated highest pixel values

				pixel_ptr++;                                    // Increment the pixelinfo_UC structure pointer

           } //... end of column loop
       
      } //... end of row loop

  }

  
  //======== Second thru last call for the block sequence of images
  
  else  {
      
	  //-------- Compute running sums and check for new maxpixels and/or sort high pixel values

      randcount = imagecmp->randcount;  // Load the random counter for repeated highest pixel frame# selection
  
	  pixel_ptr = imagecmp->pixel_ptr;

	  datum_ptr = image_ptr;


      for( kthrow=0; kthrow<image_nrows; kthrow++ )  {        // Loop over image frame rows
      
           for( kthcol=0; kthcol<image_ncols; kthcol++ )  {   // Loop over image frame columns
       
			    //-------- Extract the pixel value and compute sums

			    datum = *datum_ptr++;                               // Pull pixel value, increment to next pixel 

                pixel_ptr->sumpixel += (unsigned short)datum;           // Temporal pixel sum
            
                pixel_ptr->ssqpixel += imagecmp->squared_ptr[ datum ];  // Temporal pixel-squared_ptr sum


			    //-------- Check if pixel is greater than smallest value in the sorted high-value list

			    if( datum >= pixel_ptr->highsort[NHIGHVAL-1] )  {

				    //...... Check if pixel greater than the current maxpixel

                    if( datum > pixel_ptr->highsort[0] )  {

						//- Slide all the insertion sorted values down
                    
 					    for( ksort=NHIGHVAL-1; ksort>0; ksort-- )  pixel_ptr->highsort[ksort] = pixel_ptr->highsort[ksort - 1];
					    
						pixel_ptr->highsort[0] = datum;
						pixel_ptr->maxframe    = framemodulo; 
						pixel_ptr->numequal    = 1;

                    } //... end of new maxpixel value


					//...... Check if pixel is equal to the current maxpixel

                    else if( datum == pixel_ptr->highsort[0] )  {  
                    
 						//- Slide all the insertion sorted values down

						for( ksort=NHIGHVAL-1; ksort>0; ksort-- )  pixel_ptr->highsort[ksort] = pixel_ptr->highsort[ksort - 1];
					    
						//- Set maxframe based on random draw to avoid biasing early frame #s

                        randcount = (randcount + 1) % 65536L;

                        pixel_ptr->numequal += 1;

                        if( pixel_ptr->numequal <= imagecmp->randomN_ptr[randcount] )  pixel_ptr->maxframe = framemodulo;                                          

                    }  //... end of repeated maxpixel value


					//...... Pixel value falls between sorted highest values so perform an insertion sort

					else if( datum > pixel_ptr->highsort[NHIGHVAL-1] )  {

					    for( ksort=NHIGHVAL-1; ksort>0; ksort-- )  {

						     if( datum <= pixel_ptr->highsort[ksort - 1] )  break;

						     pixel_ptr->highsort[ksort] = pixel_ptr->highsort[ksort - 1];

						}

					    pixel_ptr->highsort[ksort] = datum;

					}  //... end of between maxpixel and smallest value on high sorted list


                } //... end of IF test for pixel value must be greater than smallest pixel in high sorted list


				//-------- Increment the pixelinfo_UC structure pointer to work on next pixel

				pixel_ptr++;


           } //... end of column loop
       
      } //... end of row loop

      imagecmp->randcount = randcount;    // Save the latest random index prior to function exit

  
  } //... end of IF first or subsequent calls to compress function

 
}

//#######################################################################################################
//                              MTPcompression_UChar_Products
//
//  User function to perform the compression "product" generation after a complete block of 
//  "totalframes" has been passed through the function MTPcompression_UChar_Compress. The 
//  computation of the products for maxpixel, maxframe, avepixel, and stdpixel is performed
//  and the user can make "totalframes" follow-up calls to MTPcompression_UChar_Compress without
//  overwritting these products. The previous block's filename is copied to "WritFFpathname", 
//  the previous block's compression arrays are computed and can then be written out using 
//  MTPcompression_UChar_FileWrite or used directly in processing.
//
//  This function allows the user to hold off starting a new compression sequence until the 
//  writing of a previous sequence is ensured to be completed (that is wait for the last FF 
//  file to be written and closed BEFORE the next compression call where modulo = 0). This  
//  provides totalframes worth of time to elapse to write the file plus any additional time if  
//  paused at the completion of the last block of data (AFTER the call to the function
//  MTPcompression_UChar_Compress when modulo = totalframes-1).
//
//         IMPORTANT NOTE: Do not start writing the latest complete block until 
//                         MTPcompression_UChar_Products is called. The same holds 
//                         true for processing data from a previous block.
//
//#######################################################################################################


void    MTPcompression_UChar_Products( struct MTP_UC_compressor   *imagecmp )
{
long               kthrow, kthcol, ksort, kvar, ssqpix;
double             avepix, varpix, N, N1;
unsigned short     sumpix;
unsigned char      datum;
unsigned char     *maxpixel_ptr;
unsigned char     *maxframe_ptr;
unsigned char     *avepixel_ptr;
unsigned char     *stdpixel_ptr;
struct pixelinfo_UC  *pixel_ptr;

 

	  //-------- Move the last block's full pathname to the write pathname buffer

	  strcpy( imagecmp->WritFFpathname, imagecmp->FFpathname );

	  strcpy( imagecmp->WritFFfilename, imagecmp->FFfilename );


	  //-------- Assign the previous block's data array output pointers to save content for writing
	  //           to the FF file as well as the working pixelinfo_UC structure pointer.

	  maxpixel_ptr = imagecmp->maxpixel_ptr; 
      maxframe_ptr = imagecmp->maxframe_ptr;
      avepixel_ptr = imagecmp->avepixel_ptr;
      stdpixel_ptr = imagecmp->stdpixel_ptr;

	  pixel_ptr    = imagecmp->pixel_ptr;


      //-------- Compute and copy out the last block's compressed products

	  N  = (double)( imagecmp->totalframes - NHIGHVAL     );
	  N1 = (double)( imagecmp->totalframes - NHIGHVAL - 1 );

	  if (N1 >= 1) {

		  for (kthrow = 0; kthrow < imagecmp->nrows; kthrow++) {          // Loop over image frame rows

			  for (kthcol = 0; kthcol < imagecmp->ncols; kthcol++) {     // Loop over image frame columns

				   //-------- Compute the previous block's temporal mean and standard deviation by
				   //           removing the sorted list of highest values for this pixel

				  sumpix = pixel_ptr->sumpixel;

				  ssqpix = pixel_ptr->ssqpixel;

				  for (ksort = 0; ksort < NHIGHVAL; ksort++) {

					  datum = pixel_ptr->highsort[ksort];

					  sumpix -= (unsigned short)datum;

					  ssqpix -= (long)imagecmp->squared_ptr[datum];

				  }

				  avepix = (double)sumpix / N;

				  varpix = ((double)ssqpix - avepix * (double)sumpix) / N1;

				  kvar = (long)varpix;


				  //-------- Copy the compressed content to the output arrays

				  *maxpixel_ptr++ = pixel_ptr->highsort[0];

				  *maxframe_ptr++ = pixel_ptr->maxframe;

				  *avepixel_ptr++ = (unsigned char)(avepix + 0.5);  //... round to nearest integer

				  *stdpixel_ptr++ = imagecmp->squareroot_ptr[kvar];


				  pixel_ptr++;                                    // Increment the pixelinfo_UC structure pointer

			  } //... end of column loop

		  } //... end of row loop

	  }



	  else {  //... N1 <= 0, just take straight average   @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

		  for (kthrow = 0; kthrow < imagecmp->nrows; kthrow++) {          // Loop over image frame rows

			  for (kthcol = 0; kthcol < imagecmp->ncols; kthcol++) {     // Loop over image frame columns

				  avepix = (double)pixel_ptr->sumpixel / (double)imagecmp->totalframes;

				  varpix = ((double)pixel_ptr->ssqpixel - avepix * (double)pixel_ptr->sumpixel) / ((double)imagecmp->totalframes - 1);

				  kvar = (long)varpix;


				  //-------- Copy the compressed content to the output arrays

				  *maxpixel_ptr++ = pixel_ptr->highsort[0];

				  *maxframe_ptr++ = pixel_ptr->maxframe;

				  *avepixel_ptr++ = (unsigned char)(avepix + 0.5);  //... round to nearest integer

				  *stdpixel_ptr++ = imagecmp->squareroot_ptr[kvar];


				  pixel_ptr++;                                    // Increment the pixelinfo_UC structure pointer

			  } //... end of column loop

		  } //... end of row loop

	  }

  
}


//#######################################################################################################
//                           MTPcompression_UChar_Filename
//
//  Constructs a FF filename with format \path\FF_######_YYYYMMDD_HHMMSS_MSC_FRAMENO.bin and 
//  places it in the compression structure "FFpathname" for full path name, and "FFfilename"
//  for only the FF filename itself. Time is based on PC system time at the time of this call.
//
//#######################################################################################################

void   MTPcompression_UChar_Filename( long framenumber,  struct MTP_UC_compressor *imagecmp )
{
long  utyear, utmonth, utday, uthour, utminute, utsecond, utmilliseconds;


   //====== Get time from onboard clock - preferably in universal time (UT)
   
   MTPcompression_UChar_DateTime( &utyear, &utmonth, &utday, &uthour, &utminute, &utsecond, &utmilliseconds );
 
            
   //====== Build filename

   sprintf( imagecmp->FFpathname, "%sFF_%06li_%04li%02li%02li_%02li%02li%02li_%03li_%07li.bin",
            imagecmp->camerafolder,
            imagecmp->cameranumber,
            utyear, utmonth, utday, uthour, utminute, utsecond, utmilliseconds,
            framenumber  );


   //====== Pull out FF name only just in case someone wants it after this call (legacy)

   strncpy( imagecmp->FFfilename, strrchr( imagecmp->FFpathname, 70 )-1, 41 );  // 41 characters from FF to .bin
  
   imagecmp->FFfilename[41] = '\0';  // Null terminate the string

}

//#######################################################################################################
//                           MTPcompression_UChar_FFpathname
//
//  Constructs a FF filename with format \path\FF_######_YYYYMMDD_HHMMSS_MSC_FRAMENO.bin and 
//  places it in "FFfilename". Time is based on user specified UT time arguments.
//
//#######################################################################################################

void   MTPcompression_UChar_FFpathname( long framenumber, long cameranumber,
	                                    long utyear, long utmonth,  long utday, 
									    long uthour, long utminute, long utsecond, long utmilliseconds,
										char *FFfolder,
										char *FFfilename,
										char *FFpathname )
{

            
   //====== Build filename

   sprintf( FFfilename, "FF_%06li_%04li%02li%02li_%02li%02li%02li_%03li_%07li.bin",
            cameranumber,
            utyear, utmonth, utday, uthour, utminute, utsecond, utmilliseconds,
            framenumber  );
  
   FFfilename[41] = '\0';  // Null terminate the string

   strcpy( FFpathname, FFfolder );

   strcat( FFpathname, FFfilename );

}


//#######################################################################################################
//                          MTPcompression_UChar_FilenameParse
//
//  Parses the FF pathname or filename to extract date, time, camera number, and starting framenumber.
//      It is backwards compatible with old FF file naming convention.
//#######################################################################################################

void   MTPcompression_UChar_FilenameParse( char *FFpathname, 
	                                       long *utyear, long *utmonth,  long *utday, 
										   long *uthour, long *utminute, long *utsecond, long *utmilliseconds, 
										   long *cameranumber, 
										   long *framenumber )
{
long   filename_length;
char  *F_ptr, *dot_ptr, FFsubstring[255];


   //--------- directory_pathname...\ FF_CAMERA_YYYYMMDD_HHMMSS_MSC_FRAMENO.bin
   //                            or       FFCAM_YYYYMMDD_HHMMSS_MSC_FRAMENO.bin

   dot_ptr = strrchr( FFpathname, 46 );  //... last occurance of . = ASCII 46 
   
   F_ptr   = strrchr( FFpathname, 70 );  //... last occurance of F = ASCII 70 

   filename_length = (long)dot_ptr - (long)F_ptr + 5L;

   if( filename_length != 37  &&  filename_length != 41 )  {
	   printf("ERROR ===> FF filename length %li not 37 or 41 in MTPcompression_UChar_FilenameParse\n", filename_length );
	   printf("           %s\n", FFpathname );
       #ifdef _WIN32    
	       Sleep(15000);
       #else            
	       sleep((unsigned int)(15));
       #endif
	   exit(1);
   }


   //-------- Extract the FF filename substring based on filename length
   
   strncpy( FFsubstring, F_ptr-1, filename_length );  // 37 or 41 characters from FF to .bin

   FFsubstring[filename_length] = '\0';  // Null terminate the string


   //-------- Parse the FF filename for its component values
   
   if( filename_length == 37 )  {  //... Old FF filename convention

	   sscanf( FFsubstring, "FF%3ld_%4ld%2ld%2ld_%2ld%2ld%2ld_%3ld_%7ld.bin", 
                             cameranumber,
                             utyear, utmonth, utday, 
                             uthour, utminute, utsecond, utmilliseconds,
                             framenumber );
   }
   else  {                         //... New FF filename convention

	   sscanf( FFsubstring, "FF_%6ld_%4ld%2ld%2ld_%2ld%2ld%2ld_%3ld_%7ld.bin", 
                             cameranumber,
                             utyear, utmonth, utday, 
                             uthour, utminute, utsecond, utmilliseconds,
                             framenumber );
   }

}


//#######################################################################################################
//                            MTPcompression_UChar_DateTime
//
//  Populates the date and time structure given the current value read off the system clock.
//#######################################################################################################


void   MTPcompression_UChar_DateTime( long *utyear, long *utmonth,  long *utday, 
									  long *uthour, long *utminute, long *utsecond, long *utmilliseconds )
{
long       microseconds;
time_t     currtime;
struct tm  gmt;


   //======== Get time from onboard clock in universal time (UT)

#ifdef _WIN32  // WINDOWS //

   long  seconds_jan1st1970;

   MTPcompression_UChar_GetTimeofDay( &seconds_jan1st1970, &microseconds );

   currtime = (time_t)seconds_jan1st1970;

#else  // LINUX //

   struct timespec curtime = { 0 };

   clock_gettime(CLOCK_REALTIME, &curtime);

   currtime = (time_t)curtime.tv_sec;

   microseconds = round(curtime.tv_nsec / 1.0e9);

#endif // WINDOWS or LINUX //


   gmt = *gmtime( &currtime );
          
   *utyear         = gmt.tm_year + 1900;    
   *utmonth        = gmt.tm_mon  + 1;       
   *utday          = gmt.tm_mday;           
   *uthour         = gmt.tm_hour;
   *utminute       = gmt.tm_min;
   *utsecond       = gmt.tm_sec;
   *utmilliseconds = microseconds / 1000;
               
}


//#######################################################################################################
//                         MTPcompression_UChar_GetTimeofDay
//
//  Windows specific date and time retrieval from the system clock to millisecond accuracy.
//#######################################################################################################
 

#ifdef _WIN32

int  MTPcompression_UChar_GetTimeofDay( long *seconds_jan1st1970, long *microseconds )
{
#if defined(_MSC_VER) || defined(_MSC_EXTENSIONS)
  #define DELTA_EPOCH_IN_MICROSECS  11644473600000000Ui64
#else
  #define DELTA_EPOCH_IN_MICROSECS  11644473600000000ULL
#endif
 
  //======== Define a structure to receive the current Windows filetime

  FILETIME ft;

  //======== Initialize the present time to 0 and the timezone to UTC

  unsigned __int64 tmpres = 0;
 
  GetSystemTimeAsFileTime(&ft);
 
  //======== The GetSystemTimeAsFileTime returns the number of 100 nanosecond 
  //           intervals since Jan 1, 1601 in a structure. Copy the high bits to 
  //           the 64 bit tmpres, shift it left by 32 then or in the low 32 bits.
  
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

  *seconds_jan1st1970 = (long)(tmpres / 1000000UL);
  *microseconds       = (long)(tmpres % 1000000UL);

  return( 0 );

}

#endif  // WINDOWS //



//#######################################################################################################
//                           MTPcompression_UChar_FileWrite
//
//  Writes the UChar CAMS FF file format (version = -1) given the values contained in
//  maxpixel, maxframe, avepixel, and the stdpixel arrays. Note that the FF filename is
//  set at the START of any given block's compression processing and represents the time of 
//  the first frame collected in the block sequence, but the filename is not available in the
//  WritFFpathname string until AFTER MTPcompression_UChar_Products is called before the start of 
//  the NEXT block of data. The same holds true for the availability of the arrays listed above.
//
//  Note that the arrays to be written to the FF file during this write call will NOT get 
//  overwritten until a call to MTPcompression_UChar_Products again occurs. This allows the 
//  user to hold off compressing subsequent blocks until the write of the previous block is 
//  determined to be completed. One can set this up using signaling in a multi-threaded environment
//  without changing these functions.
//
//#######################################################################################################

void   MTPcompression_UChar_FileWrite( struct MTP_UC_compressor *imagecmp )
{
long   firstframe, cameranumber, framerate1000;
long   utyear, utmonth, utday, uthour, utminute, utsecond, utmilliseconds;
FILE  *WriteFile;


   //printf(" MTPcompression_UChar_FileWrite entered for %s\n", imagecmp->WritFFpathname );

   MTPcompression_UChar_FilenameParse( imagecmp->WritFFpathname, 
	                                   &utyear, &utmonth, &utday, 
									   &uthour, &utminute, &utsecond, &utmilliseconds, 
									   &cameranumber, &firstframe );

   framerate1000 = (long)( imagecmp->framerateHz * 1000.0 );

   //printf(" MTPcompression_UChar_FileWrite filename parsed\n" );

   //======== Write the entire FF file contents

   if( (WriteFile = fopen( imagecmp->WritFFpathname, "wb")) == NULL )  {
       printf(" Cannot open output file %s for writing \n", imagecmp->WritFFpathname );
       #ifdef _WIN32    
	       Sleep(15000);
       #else            
	       sleep((unsigned int)(15));
       #endif
	   exit(1);
   }

   //printf(" MTPcompression_UChar_FileWrite file opened for write\n" );

   fwrite( &imagecmp->FFversion,   sizeof(long), 1, WriteFile ); 
   fwrite( &imagecmp->nrows,       sizeof(long), 1, WriteFile ); 
   fwrite( &imagecmp->ncols,       sizeof(long), 1, WriteFile ); 
   fwrite( &imagecmp->totalframes, sizeof(long), 1, WriteFile ); 
   fwrite( &firstframe,            sizeof(long), 1, WriteFile ); 
   fwrite( &cameranumber,          sizeof(long), 1, WriteFile );
   fwrite( &imagecmp->ndecim,      sizeof(long), 1, WriteFile );
   fwrite( &imagecmp->interleave,  sizeof(long), 1, WriteFile );
   fwrite( &framerate1000,         sizeof(long), 1, WriteFile );

   //printf(" MTPcompression_UChar_FileWrite header written\n" );

   fwrite( imagecmp->maxpixel_ptr, sizeof(unsigned char), imagecmp->nrows*imagecmp->ncols, WriteFile ); 
   fwrite( imagecmp->maxframe_ptr, sizeof(unsigned char), imagecmp->nrows*imagecmp->ncols, WriteFile ); 
   fwrite( imagecmp->avepixel_ptr, sizeof(unsigned char), imagecmp->nrows*imagecmp->ncols, WriteFile ); 
   fwrite( imagecmp->stdpixel_ptr, sizeof(unsigned char), imagecmp->nrows*imagecmp->ncols, WriteFile ); 

   //printf(" MTPcompression_UChar_FileWrite arrays written\n" );

   fclose( WriteFile );

   //printf(" MTPcompression_UChar_FileWrite file closed\n" );

}

//#######################################################################################################
//                           MTPcompression_UChar_FileValidity
//
//  Reads any CAMS FF file format, reads through the file contents, and checks for valid 
//  ranges of parameters and data section sizes. Error codes on return:
//    0 = Normal FF file
//    1 = Cannot open file for reading
//    2 = Number of rows out of range
//    3 = Number of columns out of range
//    4 = Number of frames out of range
//    5 = First frame mismatch in filename
//    6 = Camera number mismatch in filename
//    7 = Decimation factor out of range
//    8 = Interleave incorrect
//    9 = Frame rate <0 or >1000 Hz
//   10 = FF file version not handled in MTPcompression_UChar_FileValidity
//   11 = Total file size incorrect
//#######################################################################################################

int    MTPcompression_UChar_FileValidity( char *FFpathname )
{
long   FFversion, nrows, ncols, totalframes, framerate1000, nbytes, nbits, ndecim, interleave;
long   firstframe, firstframe2, cameranumber, cameranumber2, nread;
long   utyear, utmonth, utday, uthour, utminute, utsecond, utmilliseconds;
FILE  *ReadFile;



   //======== Open the FF file for reading as a binary file

   if( (ReadFile = fopen( FFpathname, "rb")) == NULL )  {
       return(1);
   }
      
   MTPcompression_UChar_FilenameParse( FFpathname, 
	                                   &utyear, &utmonth, &utday, 
									   &uthour, &utminute, &utsecond, &utmilliseconds, 
									   &cameranumber2, &firstframe2 );


   //======== Read the first integer in file and determine version

   nread = fread( &FFversion, sizeof(long), 1, ReadFile );

       if( nread != 1 )  {
	       printf("ERROR ===> Could not read version number header line\n" );
	       printf("           %s\n", FFpathname );
	       return(10);
       }

       if( FFversion < -1 )  {
	       printf("ERROR ===> FF file version number %li not implemented in MTPcompression_UChar_FileValidity\n", FFversion );
	       printf("           %s\n", FFpathname );
	       return(10);
       }


   //======== Check the header entries for all CAMS formats

   nread = 1;

   if( FFversion > 0 )  nrows = FFversion;
   else                 nread = fread( &nrows, sizeof(long), 1, ReadFile );

       if( nread != 1 )  {
	       printf("ERROR ===> Could not read number of rows line\n" );
	       printf("           %s\n", FFpathname );
	       return(2);
       }

	   if( nrows <= 0  ||  nrows >= 32768L )  {
	       printf("ERROR ===> Number of rows %li outside valid range [0,32768] in MTPcompression_UChar_FileValidity\n", nrows );
	       printf("           %s\n", FFpathname );
		   fclose( ReadFile );
		   return(2);
	   }

   //--------

   nread = fread( &ncols, sizeof(long), 1, ReadFile ); 

       if( nread != 1 )  {
	       printf("ERROR ===> Could not read number of cols line\n" );
	       printf("           %s\n", FFpathname );
	       return(3);
       }

       if( ncols <= 0  ||  ncols >= 32768L )  {
	       printf("ERROR ===> Number of cols %li outside valid range [0,32768] in MTPcompression_UChar_FileValidity\n", ncols );
	       printf("           %s\n", FFpathname );
		   fclose( ReadFile );
		   return(3);
	   }

   //--------

   nread = fread( &totalframes, sizeof(long), 1, ReadFile );

       if( nread != 1 )  {
	       printf("ERROR ===> Could not read number of frames line\n" );
	       printf("           %s\n", FFpathname );
	       return(4);
       }

       if( FFversion > 0 )  {
	       nbits = totalframes;
	       totalframes = 1;
	       while( nbits > 0 )  {
		       totalframes *= 2;
		       nbits--;
	       }
       }

       if( totalframes < 8  ||  totalframes > 65535 )  {
	       printf("ERROR ===> Number of frames %li outside valid range [8,256] in MTPcompression_UChar_FileValidity\n", totalframes );
	       printf("           %s\n", FFpathname );
		   fclose( ReadFile );
		   return(4);
	   }

   //--------

   nread = fread( &firstframe, sizeof(long), 1, ReadFile );

       if( nread != 1 )  {
	       printf("ERROR ===> Could not read first frame line\n" );
	       printf("           %s\n", FFpathname );
	       return(5);
       }

	   if( firstframe != firstframe2 )  {
		   printf("WARNING ===> First frame# %li in header does not match filename %li MTPcompression_UChar_FileValidity\n", firstframe, firstframe2 );
	       printf("             %s\n", FFpathname );
		   //fclose( ReadFile );
		   //return(5);
	   }

   //--------

   nread = fread( &cameranumber, sizeof(long), 1, ReadFile );

        if( nread != 1 )  {
	       printf("ERROR ===> Could not read camera number line\n" );
	       printf("           %s\n", FFpathname );
	       return(6);
       }

       if( cameranumber != cameranumber2 )  {
		   printf("ERROR ===> Camera# %li in header does not match filename %li MTPcompression_UChar_FileValidity\n", cameranumber, cameranumber2 );
	       printf("           %s\n", FFpathname );
		   fclose( ReadFile );
		   return(6);
	   }

   //--------

   nread = 1;

   if( FFversion > 0 )  ndecim = 1;
   else                 nread = fread( &ndecim, sizeof(long), 1, ReadFile );
   
        if( nread != 1 )  {
	       printf("ERROR ===> Could not read decimation line\n" );
	       printf("           %s\n", FFpathname );
	       return(7);
       }

	   if( ndecim < 1  ||  ndecim > 128 )  {
		   printf("ERROR ===> Decimation factor %li outside valid range [1,128] MTPcompression_UChar_FileValidity\n", ndecim );
	       printf("           %s\n", FFpathname );
		   fclose( ReadFile );
		   return(7);
	   }

   //--------

   nread = 1;

   if( FFversion > 0 )  interleave = 1;
   else                 nread = fread( &interleave, sizeof(long), 1, ReadFile );
   
        if( nread != 1 )  {
	       printf("ERROR ===> Could not read interleave line\n" );
	       printf("           %s\n", FFpathname );
	       return(8);
       }

       if( interleave < 0  ||  interleave > 2 )  {
		   printf("ERROR ===> Interleave flag %li outside valid range [0,2] MTPcompression_UChar_FileValidity\n", interleave );
	       printf("           %s\n", FFpathname );
		   fclose( ReadFile );
		   return(8);
	   }

   //--------

   nread = 1;

   if( FFversion > 0 )  framerate1000 = 0;
   else                 nread = fread( &framerate1000, sizeof(long), 1, ReadFile );

        if( nread != 1 )  {
	       printf("ERROR ===> Could not read frame rate line\n" );
	       printf("           %s\n", FFpathname );
	       return(9);
       }

	   if( framerate1000 < 0  ||  framerate1000 > 10000000 )  {  // <=10000 Hz
	       printf("ERROR ===> Frame rate %lf outside valid range [0,10000] in MTPcompression_UChar_FileValidity\n", (double)framerate1000/1000.0 );
	       printf("           %s\n", FFpathname );
		   fclose( ReadFile );
		   return(9);
	   }
           

   //-------- test on size of the file = header + data block

   fseek( ReadFile, 0, SEEK_END );

   if( FFversion > 0 )  nbytes = 20L + 4L * nrows * ncols;   // old FF file
   else                 nbytes = 36L + 4L * nrows * ncols;   // new FF file

	   if( nbytes != ftell( ReadFile ) )  {
	       printf("ERROR ===> Number of bytes %li not correct in MTPcompression_UChar_FileValidity\n", nbytes );
	       printf("           %s\n", FFpathname );
		   fclose( ReadFile );
		   return(11);
	   }
	   
   //--------

   fclose( ReadFile );

   return(0);

}


//#######################################################################################################
//                             MTPcompression_UChar_FileRead
//
//  Reads any CAMS FF file format, allocates memory to and fills in the "imagecmp" structure.
//  Note that this MTPcompression_UChar_FileRead function calls the MTPcompression_UChar_MemSetup function
//  and the user must call MTPcompression_UChar_MemCleanup when done with "imagecmp" (special note that
//  the function MTPcompression_UChar_MemSetup does do a MTPcompression_UChar_MemCleanup call on entry in the
//  event the user forgot to make the memory cleanup call - it tests the structure pointer
//  for a NULL value - see beginning of MTPcompression_UChar_MemSetup). Thus the user need
//  only bother to clean up memory at the end of the program.
//
//  This reader also computes the global mean, standard deviation and fills out the pointer 
//  offsets needed for fast reconstruction of image frames. The reader populates the maxpixel,
//  maxframe, avepixel, stdpixel arrays as well as all the associated header info such as image 
//  dimensions, totalframes, frame rate, ...
//
//#######################################################################################################

void   MTPcompression_UChar_FileRead( char *FFpathname, struct MTP_UC_compressor *imagecmp )
{
long   nrows, ncols, totalframes, FFversion, framerate1000, ndecim, interleave, k, nbits;
long   firstframe, cameranumber, framenumberdummy, filename_length;
long   utyear, utmonth, utday, uthour, utminute, utsecond, utmilliseconds;
double framerateHz;
char  *F_ptr, *dot_ptr, camerafolder[256];
FILE  *ReadFile;


   //======== Open the FF file for reading as a binary file

   if( (ReadFile = fopen( FFpathname, "rb")) == NULL )  {
       printf("ERROR ===> Cannot open input file %s for reading \n", FFpathname );
       #ifdef _WIN32    
	       Sleep(15000);
       #else            
	       sleep((unsigned int)(15));
       #endif
	   exit(1);
   }


   //======== Read the header information according to the CAMS file format specified

   fread( &FFversion,     sizeof(long), 1, ReadFile );

   if( FFversion != -1  &&  FFversion < 0 )  {
	   printf(" FFversion = %li header read NOT implemented in MTPcompression_UChar_FileRead\n", FFversion );
       #ifdef _WIN32    
	       Sleep(15000);
       #else            
	       sleep((unsigned int)(15));
       #endif
	   exit(1);
   }

   if( FFversion > 0 )  {  //... original CAMS format
	   nrows = FFversion;
	   fread( &ncols,         sizeof(long), 1, ReadFile );
	   fread( &nbits,   sizeof(long), 1, ReadFile );
       fread( &firstframe,    sizeof(long), 1, ReadFile );
       fread( &cameranumber,  sizeof(long), 1, ReadFile );

	   ndecim        = 1;
	   interleave    = 1;
       framerate1000 = 29970;
	   totalframes   = 1;
       for( k=0; k<nbits; k++ )  totalframes *= 2;
   }


   if( FFversion == -1 )  {  //... ver 2.0 unsigned char CAMS format
       fread( &nrows,         sizeof(long), 1, ReadFile ); 
       fread( &ncols,         sizeof(long), 1, ReadFile );
       fread( &totalframes,   sizeof(long), 1, ReadFile );
       fread( &firstframe,    sizeof(long), 1, ReadFile );
       fread( &cameranumber,  sizeof(long), 1, ReadFile );
	   fread( &ndecim,        sizeof(long), 1, ReadFile );
       fread( &interleave,    sizeof(long), 1, ReadFile );
       fread( &framerate1000, sizeof(long), 1, ReadFile );
  }


   //..... Fill in and check parameters

   framerateHz = (double)framerate1000 / 1000.0;

 
   //======== Overwrite the cameranumber with the value in the FF filename (rather than the header)
      
   MTPcompression_UChar_FilenameParse( FFpathname, 
	                                   &utyear, &utmonth, &utday, 
									   &uthour, &utminute, &utsecond, &utmilliseconds, 
									   &cameranumber, &framenumberdummy );


   //======== Get the folder pathname, filename, and full pathname

   dot_ptr = strrchr( FFpathname, 46 );  //... last occurance of . = ASCII 46 
   
   F_ptr   = strrchr( FFpathname, 70 );  //... last occurance of F = ASCII 70 

   filename_length = (long)dot_ptr - (long)F_ptr + 5L;

   
   strncpy( camerafolder, FFpathname, F_ptr-FFpathname-1 );
  
   camerafolder[F_ptr-FFpathname-1] = '\0';   // Null terminate the string

   
   strncpy( imagecmp->FFfilename, F_ptr-1, filename_length );  // 37 or 41 characters from FF to .bin

   imagecmp->FFfilename[filename_length] = '\0';  // Null terminate the string


   strcpy( imagecmp->FFpathname, FFpathname );


   //======== Set up the compression structure memory BEFORE reading data block arrays
   //           and move scalers into "imagecmp" structure
   
   MTPcompression_UChar_MemSetup( nrows, ncols, totalframes, cameranumber, ndecim, interleave, framerateHz, camerafolder, imagecmp );
   
   imagecmp->firstframe = firstframe;


   //======== Read the array information according to the CAMS file format specified

   fread( imagecmp->maxpixel_ptr, sizeof(unsigned char), nrows*ncols, ReadFile ); 
   fread( imagecmp->maxframe_ptr, sizeof(unsigned char), nrows*ncols, ReadFile ); 
   fread( imagecmp->avepixel_ptr, sizeof(unsigned char), nrows*ncols, ReadFile ); 
   fread( imagecmp->stdpixel_ptr, sizeof(unsigned char), nrows*ncols, ReadFile );                      


   //======== Close the FF file

   fclose( ReadFile );


   //======== Compute the global mean, sigma and populate the pointer offsets 
   //           of the maxpixel values specific to each frame number.

   MTPcompression_UChar_GlobalMean( imagecmp );          

   MTPcompression_UChar_GlobalSigma( imagecmp );          

   MTPcompression_UChar_PrepBuild( imagecmp );

}


//#######################################################################################################
//                           MTPcompression_UChar_PrepBuild
//
//  Populates the pointer offsets of the maxpixel values specific to a given frame number.
//  This preps the build functions for faster frame-by-frame image reconstruction from the 
//  FF file compressed data contents. 
//      mpfrmcnt = number of times a given maxframe number appears in the image block
//      mpcumcnt = specific frame# starting index in the maxpixel pointer offset array
//      mpoffset = rcindex pointer offset into the maxpixel array
//  This function is always called by MTPcompression_UChar_FileRead.
//
//#######################################################################################################

void   MTPcompression_UChar_PrepBuild( struct MTP_UC_compressor *imagecmp )
{
long            k, kf, rcindex;
unsigned char  *maxframe_ptr;


   //------ Compute the histogram of frame numbers in the maxframe array

   for( k=0; k<imagecmp->totalframes; k++ )  imagecmp->framecnt_ptr[k] = 0;


   maxframe_ptr = imagecmp->maxframe_ptr;

   for( rcindex=0; rcindex<imagecmp->nrows*imagecmp->ncols; rcindex++ )  {

	   k = (long)*maxframe_ptr++;

       imagecmp->framecnt_ptr[k] += 1;  //...increment the frame count for this frame number
   }


   //------ Compute the histogram's cumulative count

   imagecmp->mpcumcnt_ptr[0] = 0;

   for( k=1; k<imagecmp->totalframes; k++ )  imagecmp->mpcumcnt_ptr[k] = imagecmp->mpcumcnt_ptr[k-1] 
	                                                                   + imagecmp->framecnt_ptr[k-1];


   //------ Determine the pointer offsets for each specific frame number and group them
																	   
   for( k=0; k<imagecmp->totalframes; k++ )  imagecmp->framecnt_ptr[k] = 0;


   maxframe_ptr = imagecmp->maxframe_ptr;

   for( rcindex=0; rcindex<imagecmp->nrows*imagecmp->ncols; rcindex++ )  {

	   k = (long)*maxframe_ptr++;

	   kf = imagecmp->mpcumcnt_ptr[k] + imagecmp->framecnt_ptr[k];

       imagecmp->mpoffset_ptr[kf] = rcindex;

	   imagecmp->framecnt_ptr[k] += 1; //... this will eventually restore frame count

   }


}

//#######################################################################################################
//                          MTPcompression_UChar_RowColVal
//
//  Fills a rowcolval_UC structure with the maxpixel minus mean values associated with a user   
//  specified frame number. Assumes MTPcompression_UChar_PrepBuild has been called, typically
//  done on an FF file read. Upon each MTPcompression_UChar_RowColVal call, the rowcolval_UC
//  structure's pointer is checked for a NULL value. If not NULL, then the program cleans up
//  memory and reallocates a replacement rowcolval_UC structure. The function returns the number 
//  of maxpixels for the given frame number as "Nrcval" in the imagecmp structure as well as
//  the pointer to the rowcolval_UC structure containing row, col, and maxpixel-mean value.
//
//  For a program to later retrieve the row, col, or max-mean value respectively use:
//       imagecmp->rcval_ptr[k]->row
//       imagecmp->rcval_ptr[k]->col
//       imagecmp->rcval_ptr[k]->val       for k=0 to imagecmp->Nrcmax-1
//
//#######################################################################################################

void   MTPcompression_UChar_RowColVal( long fileframenumber, struct MTP_UC_compressor *imagecmp )
{
long            kf, kflo, kfhi, rcindex;
unsigned char  *maxpixel_ptr;
unsigned char  *avepixel_ptr;

struct  rowcolval_UC  *rcval_ptr;


     //------ Free memory rowcolmax structure if its pointer is not NULL, to ensure that
     //         the last call's memory allocation is freed.

     if( imagecmp->rcval_ptr != NULL )  free( imagecmp->rcval_ptr );


	 //------ Check for valid frame number

	 imagecmp->Nrcval = 0;

	 if( fileframenumber <  0                     )  return;
     if( fileframenumber >= imagecmp->totalframes )  return;


     //------ Determine the number of maxpixels to extract

     kflo = imagecmp->mpcumcnt_ptr[fileframenumber];

     if( fileframenumber < imagecmp->totalframes - 1 )  kfhi = (long)imagecmp->mpcumcnt_ptr[fileframenumber+1];
     else                                               kfhi = imagecmp->nrows * imagecmp->ncols;

     imagecmp->Nrcval = kfhi - kflo;


     //------ Allocate memory based on number of maxpixels for this frame number

     imagecmp->rcval_ptr = (struct rowcolval_UC*) malloc( imagecmp->Nrcval * sizeof(struct rowcolval_UC) );

     if( imagecmp->rcval_ptr == NULL )  {
         printf(" ERROR:  Memory not allocated in MTPcompression_UChar_RowColVal\n");
         #ifdef _WIN32    
	         Sleep(15000);
         #else            
	         sleep((unsigned int)(15));
         #endif
	     exit(1);
     }


	  //------ Extract only those pixel locations where the "fileframenumber" matches the 
	  //         maxframe number. The pixel locations are given by pointer offsets previously
	  //         calculated in the function MTPcompression_UChar_PrepBuild.

	  maxpixel_ptr = imagecmp->maxpixel_ptr;
	  avepixel_ptr = imagecmp->avepixel_ptr;
	  rcval_ptr    = imagecmp->rcval_ptr;

      for( kf=kflo; kf<kfhi; kf++ )  {

           rcindex = imagecmp->mpoffset_ptr[kf];

           rcval_ptr->row = (unsigned short)( rcindex / imagecmp->ncols );
           rcval_ptr->col = (unsigned short)( rcindex % imagecmp->ncols );
           rcval_ptr->val = maxpixel_ptr[rcindex] - avepixel_ptr[rcindex];

		   rcval_ptr++;
      }


}


//#######################################################################################################
//                            MTPcompression_UChar_FrameBuild
//
//  Reconstructs a full image frame given a specific frame number desired. The frame consists
//  of the mean pixel image overwritten with maxpixel values only where the maxframe matches 
//  the "fileframenumber". Call MTPcompression_UChar_PrepBuild once BEFORE 
//  MTPcompression_UChar_FrameBuild is used but note that if the function 
//  MTPcompression_UChar_FileRead was called to obtain the compressed data block, then
//  the function MTPcompression_UChar_PrepBuild has already been called. Final output
//  image is placed in imagecmp->imgframe_ptr.
//
//#######################################################################################################

void   MTPcompression_UChar_FrameBuild( long fileframenumber, struct MTP_UC_compressor *imagecmp )
{
long            kf, kflo, kfhi, rcindex;
unsigned char  *maxpixel_ptr;
unsigned char  *imgframe_ptr;


      //------ First fill with the mean image and check for out of bounds frame number request

	  memcpy( imagecmp->imgframe_ptr, imagecmp->avepixel_ptr, sizeof(unsigned char) * imagecmp->nrows * imagecmp->ncols ); 

      if( fileframenumber <  0                     )  return;
      if( fileframenumber >= imagecmp->totalframes )  return;


	  //------ Determine the range of maxpixels that need to get mapped onto the image frame

	  kflo = (long)imagecmp->mpcumcnt_ptr[fileframenumber];

	  if( fileframenumber < imagecmp->totalframes - 1 )  kfhi = (long)imagecmp->mpcumcnt_ptr[fileframenumber+1];
	  else                                               kfhi = imagecmp->nrows * imagecmp->ncols;


	  //------ Overwrite those pixel locations with maxpixel values where the "fileframenumber" 
	  //         matches the maxframe number. The pixel locations are given by pointer offsets 
	  //         previously calculated in the function MTPcompression_UChar_PrepBuild.

	  maxpixel_ptr = imagecmp->maxpixel_ptr;
      imgframe_ptr = imagecmp->imgframe_ptr;

      for( kf=kflo; kf<kfhi; kf++ )  {

           rcindex = imagecmp->mpoffset_ptr[kf];

           imgframe_ptr[rcindex] = maxpixel_ptr[rcindex];
      }
           
}


//#######################################################################################################
//                       MTPcompression_UChar_GlobalMean
//
//  Assigns the median of the block mean to imagecmp->global_ave via gray level histogram
//#######################################################################################################

void   MTPcompression_UChar_GlobalMean( struct MTP_UC_compressor *imagecmp )
{
long            *kount, kgray, kpixel, ksum, khalf;
unsigned char  *avepixel_ptr;


      //------ Allocate memory for histogram

      kount = (long*) malloc( 256L * sizeof(long) );
      
	  if( kount == NULL )  {
         printf(" ERROR:  Memory not allocated in MTPcompression_UChar_GlobalMean\n");
         #ifdef _WIN32    
	         Sleep(15000);
         #else            
	         sleep((unsigned int)(15));
         #endif
	     exit(1);
      }


      //------ Build histogram of mean values across image block

      for( kgray=0; kgray<256L; kgray++ )  kount[kgray] = 0;

      avepixel_ptr = imagecmp->avepixel_ptr;
      
      for( kpixel=0; kpixel<imagecmp->nrows * imagecmp->ncols; kpixel++ )  {
  
           kgray = (long)*avepixel_ptr++;
                
           kount[kgray] += 1;           
      }
    
     
      //------ Find the median which equals the middle value in the cumulative histogram

	  khalf = imagecmp->nrows * imagecmp->ncols / 2;
      
      ksum = 0;
      
      for( kgray=0; kgray<256L; kgray++ )  {

           ksum += kount[kgray];
           
           if( ksum > khalf )  break;
      }  

      imagecmp->global_ave = (unsigned char)kgray;
          
	  free( kount );

}


//#######################################################################################################
//                        MTPcompression_UChar_GlobalSigma
//
//  Assigns the median of the block standard deviation to imagecmp->global_std via histogram
//#######################################################################################################

void   MTPcompression_UChar_GlobalSigma( struct MTP_UC_compressor *imagecmp )
{
long           *kount, kgray, kpixel, ksum, khalf;
unsigned char  *stdpixel_ptr;
 

      //------ Allocate memory for histogram

      kount = (long*) malloc( 256L * sizeof(long) );
      
	  if( kount == NULL )  {
         printf(" ERROR:  Memory not allocated in MTPcompression_UChar_GlobalSigma\n");
         #ifdef _WIN32    
	         Sleep(15000);
         #else            
	         sleep((unsigned int)(15));
         #endif
	     exit(1);
      }


	  //------ Build histogram of sigma values across image block      
      
      for( kgray=0; kgray<256L; kgray++ )  kount[kgray] = 0;

      stdpixel_ptr = imagecmp->stdpixel_ptr;
  
      for( kpixel=0; kpixel<imagecmp->nrows * imagecmp->ncols; kpixel++ )  {
  
           kgray = (long)*stdpixel_ptr++;
                
           kount[kgray] += 1;           
      }

      
      //------ Find the median of sigma = middle value in the cumulative histogram
      
	  khalf = imagecmp->nrows * imagecmp->ncols / 2;
      
      ksum = 0;
      
      for( kgray=0; kgray<256L; kgray++ )  {

           ksum += kount[kgray];
           
           if( ksum > khalf )  break;
      }  
      
      imagecmp->global_std = (unsigned char)kgray;

	  free( kount );

}


//#######################################################################################################
//                            MTPcompression_UChar_Flatten
//
//  Flat fielding of previously built "imgframe" comprised of mean removal, division by the 
//  standard deviation, and scaling up by 128. The sign preserving output uses the short
//  data type. Either a 0 or 1 is added to the entire frame on each call to toggle a small
//  noise contribution.
//
//  Call MTPcompression_UChar_FrameBuild before calling this function to populate the
//  array imagecmp->imgframe_ptr.
//
//#######################################################################################################

void   MTPcompression_UChar_Flatten( short *flattened_ptr, struct MTP_UC_compressor *imagecmp )
{ 
long            unitybias, rcindex;
unsigned char  *imgframe_ptr;
unsigned char  *avepixel_ptr;
unsigned char  *stdpixel_ptr;


      //------ Set pointers to the image frame, mean, and standard deviation

      imgframe_ptr = imagecmp->imgframe_ptr;
      avepixel_ptr = imagecmp->avepixel_ptr;
      stdpixel_ptr = imagecmp->stdpixel_ptr;
      
      
      //------ Add either zero or one to this image for well behaved noise filter
            
      imagecmp->randcount = (imagecmp->randcount + 1) % 65536L;
      
      unitybias = (short)( imagecmp->randomN_ptr[imagecmp->randcount] % 2 );
      
      
      //------ Mean remove and flat field each pixel = 128 * ( pixel - mean ) / sigma
        
      for( rcindex=0; rcindex<imagecmp->nrows*imagecmp->ncols; rcindex++ )  {
  
		  flattened_ptr[rcindex] = (short)( unitybias + ( labs( (long)(imgframe_ptr[rcindex] - avepixel_ptr[rcindex]) ) << 7 ) / (long)stdpixel_ptr[rcindex] );
                           
      }
      
}

//#######################################################################################################
//                              MTPcompression_UChar_BuildFlatten
//
//  Flat field image processing by first reconstructing the image frame and then performing  
//  mean removal, division by the standard deviation, and scaling up by 128. The sign  
//  preserving output is of the short data type. Either a 0 or 1 is added to the entire frame 
//  on each call to toggle a small noise contribution. Call MTPcompression_UChar_PrepBuild once before
//  MTPcompression_UChar_FrameBuild is used. Note that if the function MTPcompression_UChar_FileRead was called
//  to get the compressed data block, then the function MTPcompression_UChar_PrepBuild has already been
//  called. Currently only puts in the maxpixel values (no aftermax values).
//
//#######################################################################################################

void   MTPcompression_UChar_BuildFlatten( short *flattened_ptr, long fileframenumber, struct MTP_UC_compressor *imagecmp )
{
long            rcindex, kf, kflo, kfhi;
unsigned char  *maxpixel_ptr;
unsigned char  *avepixel_ptr;
unsigned char  *stdpixel_ptr;
short           unitybias;


      //------ Add either zero or one to this image for well behaved noise filter
            
      imagecmp->randcount = (imagecmp->randcount + 1) % 65536L;
      
      unitybias = (short)( imagecmp->randomN_ptr[imagecmp->randcount] % 2 );

	  for( rcindex=0; rcindex<imagecmp->nrows*imagecmp->ncols; rcindex++ )  flattened_ptr[rcindex] = unitybias;

      
      //------ Check if frame number is out of bounds

      if( fileframenumber <  0                     ) return;
      if( fileframenumber >= imagecmp->totalframes ) return;


	  //------ Determine the range of maxpixels that need to get mapped onto the image frame

	  kflo = imagecmp->mpcumcnt_ptr[fileframenumber];

	  if( fileframenumber < imagecmp->totalframes - 1 )  kfhi = (long)imagecmp->mpcumcnt_ptr[fileframenumber+1];
	  else                                               kfhi = imagecmp->nrows * imagecmp->ncols;


	  //------ Set pointers to the image frame, mean, and standard deviation

	  maxpixel_ptr = imagecmp->maxpixel_ptr;
	  avepixel_ptr = imagecmp->avepixel_ptr;
	  stdpixel_ptr = imagecmp->stdpixel_ptr;


      //..... Flat field each pixel = 128 * ( pixel - mean ) / sigma 
	  //        only for the specified frame number (otherwise set to unitybias)
        
      for( kf=kflo; kf<kfhi; kf++ )  {

           rcindex = imagecmp->mpoffset_ptr[kf];

           flattened_ptr[rcindex] += (short)( ( labs( (long)(maxpixel_ptr[rcindex] - avepixel_ptr[rcindex]) ) << 7 ) / (long)stdpixel_ptr[rcindex] );
      }
      
}

//#######################################################################################################
//                              MTPcompression_UChar_NoiseFlatten
//
//  Flat fielded 1 sigma gaussian noise image scaled up by 128. The sign preserving output is of the 
//  short data type. Either a 0 or 1 is added to the entire frame on each call to toggle a small noise 
//  contribution.  Currently only puts in the maxpixel values (no aftermax values). Used for feeding
//  noise-like imagery to the MeteorScan program.
//
//..... Fill specific image pixels with random gaussian noise such that 
//           |mean + gauss(std) - mean| * 128 / std  =  |gauss(1)| * 128 = |gauss(128)|
//
//#######################################################################################################

void   MTPcompression_UChar_NoiseFlatten( short *flattened_ptr, long fileframenumber, struct MTP_UC_compressor *imagecmp )
{
long            rcindex, kf, kflo, kfhi;
unsigned char  *maxpixel_ptr;
unsigned char  *avepixel_ptr;
unsigned char  *stdpixel_ptr;
short           unitybias;


      //------ Add either zero or one to this image for well behaved noise filter
            
      imagecmp->randcount = (imagecmp->randcount + 1) % 65536L;
      
      unitybias = (short)( imagecmp->randomN_ptr[imagecmp->randcount] % 2 );

	  for( rcindex=0; rcindex<imagecmp->nrows*imagecmp->ncols; rcindex++ )  flattened_ptr[rcindex] = unitybias;

      
      //------ Check if frame number is out of bounds

      if( fileframenumber <  0                     ) return;
      if( fileframenumber >= imagecmp->totalframes ) return;


	  //------ Determine the range of maxpixels that need to get mapped onto the image frame

	  kflo = imagecmp->mpcumcnt_ptr[fileframenumber];

	  if( fileframenumber < imagecmp->totalframes - 1 )  kfhi = (long)imagecmp->mpcumcnt_ptr[fileframenumber+1];
	  else                                               kfhi = imagecmp->nrows * imagecmp->ncols;


	  //------ Set pointers to the image frame, mean, and standard deviation

	  maxpixel_ptr = imagecmp->maxpixel_ptr;
	  avepixel_ptr = imagecmp->avepixel_ptr;
	  stdpixel_ptr = imagecmp->stdpixel_ptr;


      //..... Flat field each pixel = 128 * gaussian draw 
	  //        only for the specified frame number (otherwise set to unitybias)
        
      for( kf=kflo; kf<kfhi; kf++ )  {

           rcindex = imagecmp->mpoffset_ptr[kf];

		   imagecmp->randcount = (imagecmp->randcount + fileframenumber) % 65536L;

           flattened_ptr[rcindex] += (short)imagecmp->gauss128_ptr[imagecmp->randcount];
      }
      
}


//#######################################################################################################
//                                 MTPcompression_UChar_MeanRemoval
//
//  Remove the mean from the image frame array and preserve the sign using a short on output.
//       demean = imgframe - avepixel
//#######################################################################################################

void   MTPcompression_UChar_MeanRemoval( short *demean_ptr, struct MTP_UC_compressor *imagecmp )
{
long            kthrow, kthcol;
unsigned char  *imgframe_ptr;
unsigned char  *avepixel_ptr;


      //------ Set pointers to the image frame and mean

      imgframe_ptr = imagecmp->imgframe_ptr;
      avepixel_ptr = imagecmp->avepixel_ptr;
            
      
      //------ Remove mean for each pixel
        
      for( kthrow=0; kthrow<imagecmp->nrows; kthrow++ )  {
  
           for( kthcol=0; kthcol<imagecmp->ncols; kthcol++ )  {
                           
                *demean_ptr++ = (short)( (long)*imgframe_ptr++ - (long)*avepixel_ptr++ );
                                                 
           }
      }
      
}



//#######################################################################################################
//                      MTPcompression_UChar_MemCleanup
//
//  Frees all allocated memory of the compression structure specified
//#######################################################################################################

void   MTPcompression_UChar_MemCleanup( struct MTP_UC_compressor *imagecmp )
{

   if( imagecmp->maxpixel_ptr   != NULL )  free( imagecmp->maxpixel_ptr   );
   if( imagecmp->maxframe_ptr   != NULL )  free( imagecmp->maxframe_ptr   );
   if( imagecmp->avepixel_ptr   != NULL )  free( imagecmp->avepixel_ptr   );
   if( imagecmp->stdpixel_ptr   != NULL )  free( imagecmp->stdpixel_ptr   );
   if( imagecmp->imgframe_ptr   != NULL )  free( imagecmp->imgframe_ptr   );

   if( imagecmp->pixel_ptr      != NULL )  free( imagecmp->pixel_ptr      );
   if( imagecmp->rcval_ptr      != NULL )  free( imagecmp->rcval_ptr      );

   if( imagecmp->mpoffset_ptr   != NULL )  free( imagecmp->mpoffset_ptr   );
   if( imagecmp->mpcumcnt_ptr   != NULL )  free( imagecmp->mpcumcnt_ptr   );
   if( imagecmp->framecnt_ptr   != NULL )  free( imagecmp->framecnt_ptr   );

   if( imagecmp->randomN_ptr    != NULL )  free( imagecmp->randomN_ptr    );
   if( imagecmp->squared_ptr    != NULL )  free( imagecmp->squared_ptr    );
   if( imagecmp->squareroot_ptr != NULL )  free( imagecmp->squareroot_ptr );
   if( imagecmp->gauss128_ptr   != NULL )  free( imagecmp->gauss128_ptr   );

   MTPcompression_UChar_NullPointers( imagecmp );
   

}


//#######################################################################################################
//                                MTPcompression_UChar_NullPointers
//
//  Ensures all array and vector data pointers are set to NULL. Recommend calling this at
//  program startup to clear all the compressor structure's pointers
//#######################################################################################################

void   MTPcompression_UChar_NullPointers( struct MTP_UC_compressor *imagecmp )
{

   imagecmp->maxpixel_ptr   = NULL;
   imagecmp->maxframe_ptr   = NULL;
   imagecmp->avepixel_ptr   = NULL;
   imagecmp->stdpixel_ptr   = NULL;
   imagecmp->imgframe_ptr   = NULL;
   imagecmp->pixel_ptr      = NULL;
   imagecmp->rcval_ptr      = NULL;
   imagecmp->mpoffset_ptr   = NULL;
   imagecmp->mpcumcnt_ptr   = NULL;
   imagecmp->framecnt_ptr   = NULL;
   imagecmp->randomN_ptr    = NULL;
   imagecmp->squared_ptr    = NULL;
   imagecmp->squareroot_ptr = NULL;
   imagecmp->gauss128_ptr   = NULL;
    
} 

//#######################################################################################################

double  MTPcompression_UChar_Gauss3Sigma( double sigma )  //normally distributed limited to +-3sigma
{
static short   gausscall = 0;
static double  rangauss1st, rangauss2nd;
double         ran1, ran2, v1, v2, fac, vsq;


     if( gausscall == 0 )  {
		 do {

             do {
                  ran1 = (double)rand() / (double)RAND_MAX;
                  ran2 = (double)rand() / (double)RAND_MAX;
                  v1   = 2.0 * ran1 - 1.0;
                  v2   = 2.0 * ran2 - 1.0;
                  vsq  = v1*v1 + v2*v2;
             }
             while( vsq >= 1.0 );
         
             fac = sqrt( -2.0*log(vsq)/vsq );
         
             rangauss1st = v1 * fac;
             rangauss2nd = v2 * fac;
		 }
		 while( rangauss1st > 3.0 || rangauss2nd > 3.0 );

         gausscall = 1;
         return( sigma * rangauss1st );
     }
     else {
         gausscall = 0;
         return( sigma * rangauss2nd );
     }
     
}

//#######################################################################################################
