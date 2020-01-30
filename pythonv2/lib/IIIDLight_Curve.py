import cv2
import sys
import json
import statistics 
import numpy

from lib.MeteorReduce_Tools import get_stacks
 

def get_json_for_3Dlight_curve(frames,analysed_name):
   
   # First get min x,y and max x,y from the frames list
   # so we know where the meteor is on the stack
   x_vals=[]
   y_vals=[]
   z_vals=[] 

   # Get only the x and y
   all_x = []
   all_y = []
 

   for frame in frames:
      if('x' in frame): 
         all_x.append(frame['x'])
      if('y' in frame): 
         all_y.append(frame['y'])   
 
   min_pos_x = min(all_x)
   max_pos_x = max(all_x)
   min_pos_y = min(all_y)
   max_pos_y = max(all_y)
  
   # Get the stack
   hd_stack = get_stacks(analysed_name,0,True)
   if(hd_stack is not None):
      image = cv2.imread(hd_stack)

      if(min(min_pos_x,max_pos_x)>min(min_pos_y,max_pos_y)):

         # We get the pixel value for each x,y 
         for x in range(min_pos_x,max_pos_x):
            for y in range(min_pos_y,max_pos_y):
               z_vals.append(int(statistics.mean(image[y,x])))  # Average of the 3 VALUES
               #x_vals.append(int(x))
               #y_vals.append(int(y))

      else:

         # We get the pixel value for each x,y 
         for y in range(min_pos_y,max_pos_y):
            for x in range(min_pos_x,max_pos_x):
               z_vals.append(int(statistics.mean(image[y,x])))  # Average of the 3 VALUES
               #x_vals.append(int(x))
               #y_vals.append(int(y))
 

      print(z_vals)
      sys.exit(0)

      return  {
            'title':'3DLight Intensity',
            'title1': 'Intensity', 
            'z1_vals': z_vals 
      } 
   return None
