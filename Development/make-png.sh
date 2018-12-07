 gcc -c -fpic lodepng.c -fpic HCAMS_Thumbnails_Driver.c ; gcc lodepng.o HCAMS_Thumbnails_Driver.o -o cams_thumbnail -lm
