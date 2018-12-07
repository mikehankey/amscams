



#include "lodepng.h"
#include <stdlib.h>


int main() {

	unsigned int  k, width, height;

	unsigned char  *uchar_image;
	unsigned char  *uread_image;

  
	//-------------------------------

	width  = 240;  //...<255
	height = 260;

	uchar_image = (unsigned char*)malloc(width*height * sizeof(unsigned char));
	uread_image = (unsigned char*)malloc(width*height * sizeof(unsigned char));

	//----- create a ramp image

    for(k=0; k<width*height; k++ )  uchar_image[k] = k % width;

	//----- write the ramp image

	lodepng_encode_file("ramp1.png", uchar_image, width, height, LCT_GREY, 8 );

	//----- read back the image

    lodepng_decode_file(&uread_image, &width, &height, "ramp1.png", LCT_GREY, 8);

	//----- reverse color on the image

	for (k = 0; k<width*height; k++)  uread_image[k] = 255 - uread_image[k];

	//----- write the negative ramp image

	lodepng_encode_file("ramp2.png", uread_image, width, height, LCT_GREY, 8);

	
	free(uread_image);
	free(uchar_image);


	return 0;
}
