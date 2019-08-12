#!/usr/bin/python3 
#import collections
#from collections import deque
from PIL import Image, ImageChops
#from queue import Queue
#import multiprocessing
#import datetime
import cv2
import numpy as np
#import iproc 
import time
#import ephem
import sys
#import os

def view(file, show):

    out_file = file.replace(".mp4", ".jpg")
    #print (file)
    #print (out_file)
    img_matrix = [] 
    count = 0
    print ("FILE:", file)
    cap = cv2.VideoCapture(file)
    time.sleep(2)
    frame = None 
    last_frame = None 
    image_acc = None 
    nc = 0
    while (frame is None):
        _ , frame = cap.read()
        print("Frame is none.")
        nc = nc + 1
        if nc > 20:
           print ("Can't read the file", file)
           exit()
    stack_frame = np.array(frame,dtype=np.float32)
    im = np.array(frame,dtype=np.float32)
    final_image = Image.fromarray(frame)
    median_array = []
    #cv2.namedWindow('pepe')
    med_on = 0
    while True:
        _ , frame = cap.read()
        nice_frame = frame
        if frame is None:
            print (str(count) + " frames processed.")
            break
        else:

            frame_img = Image.fromarray(frame)
            final_image=ImageChops.lighter(final_image,frame_img)

            #median_image = np.median(np.array(median_array), axis=0)
            #median = np.uint8(median_image)

            save_image = Image.fromarray(nice_frame)
            el = file.split("/")
            temp = el[-1]
            temp2 = str(1000+count) + "-" + temp.replace(".mp4", ".jpg")
            save_file = file.replace(temp, temp2)


            count += 1  
    print (out_file)
    final_image.save(out_file, "JPEG")

    #im /= count  * .15

    #final_image = Image.fromarray(np.uint8(im.clip(0,255)))
    #final_image.save('all_averaged2.jpg', 'JPEG')

    #image_stack = np.dstack(tuple(img_matrix)) 
    #median_array = np.median(image_stack, axis=2)
    #cv2.imwrite("test.jpg", median_array)
    #med_out = Image.fromarray(np.uint8(median_array))
    #med_out.save('all_medout.jpg', 'JPEG')

view(sys.argv[1], "a")
