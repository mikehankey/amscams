rm test
rm *.o
gcc -c -fpic HCAMS_Detection_Driver.c -fpic MTPcompression_Uchar.c; gcc HCAMS_Detection_Driver.o MTPcompression_Uchar.o -o cams_detect -lm
cp cams_detect ../RunFolder
