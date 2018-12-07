rm thumbcv
rm *.o
g++ -ggdb thumbcv.cpp lodepng.c -o thumbcv `pkg-config --cflags --libs opencv`

