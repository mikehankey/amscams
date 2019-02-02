rm thumb
rm *.o
g++ -ggdb thumb.cpp lodepng.c -o thumb 
#`pkg-config --cflags --libs opencv`
cp thumb ../RunFolder
