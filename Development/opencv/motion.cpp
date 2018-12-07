/*
* To compile: g++ opencv_test2.cpp -o opencv_test2 $(pkg-config --cflags --libs opencv)
*/
#include <opencv2/opencv.hpp>
#include <opencv2/tracking.hpp>
#include <opencv2/core/ocl.hpp>
#include <unistd.h>

using namespace cv;
using namespace std;
 
int main(int argc, char **argv) {

    printf("%s", argv[1]);
    Mat frame, gray, frameDelta, thresh, firstFrame;
    vector<vector<Point> > cnts;
    VideoCapture camera(argv[1]); //open camera
    
    //set the video size to 512x288 to process faster
    //camera.set(3, 512);
    //camera.set(4, 288);

    sleep(3);
    camera.read(frame);

    //convert to grayscale and set the first frame
    cvtColor(frame, firstFrame, COLOR_BGR2GRAY);
    GaussianBlur(firstFrame, firstFrame, Size(21, 21), 0);

    while(camera.read(frame)) {

        //convert to grayscale
        cvtColor(frame, gray, COLOR_BGR2GRAY);
        GaussianBlur(gray, gray, Size(21, 21), 0);

        //compute difference between first frame and current frame
        absdiff(firstFrame, gray, frameDelta);
        threshold(frameDelta, thresh, 25, 255, THRESH_BINARY);
        
        dilate(thresh, thresh, Mat(), Point(-1,-1), 2);
        findContours(thresh, cnts, RETR_EXTERNAL, CHAIN_APPROX_SIMPLE);

        for(int i = 0; i< cnts.size(); i++) {
            if(contourArea(cnts[i]) < 500) {
                continue;
            }
            printf("Motion Detected.");
            //putText(frame, "Motion Detected", Point(10, 20), FONT_HERSHEY_SIMPLEX, 0.75, Scalar(0,0,255),2);
        }
   /* 
        imshow("Camera", firstFrame);
        
        if(waitKey(1) == 27){
            //exit if ESC is pressed
            break;
        }
*/
    
    }

    return 0;
}
