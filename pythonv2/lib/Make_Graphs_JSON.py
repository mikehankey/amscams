import sys
import os
import json
import numpy as np
import cv2
import statistics 
import requests 
import glob

from lib.FileIO import cfe, save_json_file
from lib.VIDEO_VARS import HD_W, HD_H
from lib.MeteorReduce_Tools import get_cache_path, does_cache_exist


DEFAULT_IFRAME = "<iframe width='100%' height='517' style='margin:.5rem auto' frameborder='false' src='{CONTENT}'></iframe>"
DEFAULT_PATH_TO_GRAPH = "/pycgi/plot.html?"


# Basic X,Y Plot with regression (actually a "trending line")
def make_xy_point_plot(frames,analysed_name):

   xs = []
   ys = []
 
   for frame in frames:
      xs.append(frame['x']) 
      ys.append(frame['y']) 
 
   if(len(xs)>1):

      trend_x, trend_y = poly_fit_points(xs,ys) 
      
      # trend_x, trend_y = get_fit_line(xs,ys)
    
      tx1 = []
      ty1 = []

      for i in range(0,len(trend_x)):
         tx1.append(int(trend_x[i]))
         ty1.append(int(trend_y[i]))

      return create_iframe_to_graph(
         analysed_name,
         {'title':'XY Points and Trendline',
          'x1_vals': str(xs),
          'y1_vals':str(ys),
          'x2_vals': str(tx1),
          'y2_vals':str(ty1),
          'y1_reverse':'1',
          'title1': 'Meteor pos.',
          'title2': 'Fit val',
          's_ratio1':'1'},
          'xy')
   return ''


# Build the iFrame 
# Create the corresponding JSON file for the Graph
# and create the iframe with file=this json
def create_iframe_to_graph(analysed_name,data,name,clear_cache=False):

   link = DEFAULT_PATH_TO_GRAPH  
 
   # Suprise: we need data to display
   if 'x1_vals' in data and 'y1_vals' in data :
      # Here we test <=2 because the list are passed as string 
      # and an empty list = [] => 2 chararcters
      if len(data['x1_vals'])<=2: 
         return ""
      if len(data['y1_vals'])<=2:
         return ""
   
   # CREATE or RETRIEVE TMP JSON FILE UNDER /GRAPH (see REDUCE_VARS)  
   json_graph = does_cache_exist(analysed_name,'graphs',name+'.json')
   
   if(len(json_graph)==0 or clear_cache is True or (clear_cache is True)):
      # We need to create the JSON
      path_to_json = get_cache_path(analysed_name,"graphs")+name+'.json'
      save_json_file(path_to_json,json.dumps(data))
    
   else:
      # We return them 
      path_to_json = glob.glob(get_cache_path(analysed_name,"graphs")+name+'.json') 



   print("PATH TO GRAPH JSON :<br>")
   print(path_to_json)
   sys.exit(0)

 
   
   #sys.exit(0)
 

   #if('title' in data):
   #   link += "&title=" + data['title'].replace(" ","_")
   #if('x_title' in data):
   #   link += "&x_title=" + data['x_title']
   #if('y_title' in data):
   #   link += "&y_title=" + data['y_title']
   #if('x1_vals' in data):
   #   link += "&x1_vals=" + data['x1_vals']
   #if('y1_vals' in data):
   #   link += "&y1_vals=" + data['y1_vals']
   #if('z1_vals' in data):
   #   link += "&z1_vals=" + data['z1_vals']
   #if('x2_vals' in data):
   #   link += "&x2_vals=" + data['x2_vals']
   #if('y2_vals' in data):
   #   link += "&y2_vals=" + data['y2_vals']   
   #if('y1_reverse' in data):
   #   link += "&y1_reverse=" + data['y1_reverse']   
   #if('title1' in data):
   #   link += "&title1=" + data['title1'].replace(" ","_")   
   #if('s_ratio1' in data):
   #   link += "&s_ratio1=" + data['s_ratio1']
   #if('linetype1' in data):
   #    link += "&linetype1=" + data['linetype1']   
   #if('lineshape1' in data):
   #    link += "&lineshape1=" + data['lineshape1']   
   #if('linetype2' in data):
   #    link += "&linetype2=" + data['linetype2']     
  
   #link = link.replace("[", "").replace("]", "").replace(" ", "").replace("\"", "").replace("\'", "")

   #return DEFAULT_IFRAME.replace('{CONTENT}', link) 

   return ''


# Curve Light
def make_light_curve(frames):
   lc_cnt = []
   lc_ff = []
   lc_count = []
   
   if(len(frames)>1):
      for frame in frames:
         if "intensity" in frame and "intensity_ff" in frame:
             if frame['intensity']!= '?' and frame['intensity']!= '9999':
               lc_count.append(frame['dt'][14:]) # Get Min & Sec from dt
               lc_cnt.append(frame['intensity']) 
               lc_ff.append(frame['intensity_ff']) 
 
      return create_iframe_to_graph({
           'title':'Light Intensity',
           'title1': 'Intensity',
           'x1_vals':  lc_count,
           'y1_vals':  lc_cnt, 
           'linetype1': 'lines+markers',
           'lineshape1': 'spline'
            })
   return ''






# Get "trendingline"
def get_fit_line(poly_x, poly_y):
  return np.unique(poly_x), np.poly1d(np.polyfit(poly_x, poly_y, 1))(np.unique(poly_x))
 
# Compute the fit line of a set of data (MIKE VERSION)
def poly_fit_points(poly_x,poly_y, z = None):
   if z is None:
      if len(poly_x) >= 3:
         try:
            z = np.polyfit(poly_x,poly_y,1)
            f = np.poly1d(z)
         except:
            return 0
      else:
         return 0

      trendpoly = np.poly1d(z)
      new_ys = trendpoly(poly_x)

   return(poly_x, new_ys)
 

# Create 2 different plots when possible
# 1- X,Y position 
# 2- Light Curves
def make_basic_plots(meteor_json_file, analysed_name):
   plots = ''
   if 'frames' in meteor_json_file:   
      if len(meteor_json_file['frames']) > 0:  
         # Main x,y plot + Curve Light
         plots = make_xy_point_plot(meteor_json_file['frames'],analysed_name)+ " " + make_light_curve(meteor_json_file['frames'],analysed_name)
   
   return plots


# Create 3D Light Curve Graph
def make3D_light_curve(meteor_json_file,hd_stack):
 
   xvals = []
   yvals = []
   zvals = []


   for x in range(0, HD_W):
      xvals.append(x)
   
   for y in range(0, HD_H):
      yvals.append(y)

   for z in range(0, 255):
      zvals.append(0)

   image = cv2.imread(hd_stack)

   for f in meteor_json_file['frames']:   
      try:
         #xvals.append(f['x'])
         #yvals.append(f['y'])
         zvals.append(statistics.mean(image[int(f['y']),int(f['x'])]))  # Average of the 3 VALUES
      except:
         partial = True
   
   if len(xvals)>0 and len(yvals)>0 and len(zvals)>0:
      return create_iframe_to_graph({
         'title':'3D Light Topography',
         'x1_vals': str(xvals),
         'y1_vals':str(yvals),
         'z1_vals':str(zvals) 
      })
   else:
      return ''



   #partial = False 
   #if 'frames' in meteor_json_file:   
   #   if len(meteor_json_file['frames']) > 0:  
#
   #      image = cv2.imread(hd_stack)
#      for f in meteor_json_file['frames']:   
   #         try:
   #            xvals.append(f['x'])
   #            yvals.append(f['y'])
   #            zvals.append(statistics.mean(image[int(f['y']),int(f['x'])]))  # Average of the 3 colors
    #        except:
    #           partial = True
 
