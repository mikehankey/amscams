import sys
import numpy as np


DEFAULT_IFRAME = "<iframe width='100%' height='517' style='margin:.5rem auto' frameborder='false' src='{CONTENT}'></iframe>"
DEFAULT_PATH_TO_GRAPH = "/pycgi/graph.html?"


# Build the iFrame (proper URL) for a given graph
def create_iframe_to_graph(data):
   link = DEFAULT_PATH_TO_GRAPH + '?w=7'  # w=7 for the next &
   
   if('title' in data):
      link += "&title=" + data['title'].replace(" ","_")
   if('x_title' in data):
      link += "&x_title=" + data['x_title']
   if('y_title' in data):
      link += "&y_title=" + data['y_title']
   if('x1_vals' in data):
      link += "&x1_vals=" + data['x1_vals']
   if('y1_vals' in data):
      link += "&y1_vals=" + data['y1_vals']
   if('x2_vals' in data):
      link += "&x2_vals=" + data['x2_vals']
   if('y2_vals' in data):
      link += "&y2_vals=" + data['y2_vals']   
   if('y1_reverse' in data):
      link += "&y1_reverse=" + data['y1_reverse']   
   if('title1' in data):
      link += "&title1=" + data['title1'].replace(" ","_")   
   if('s_ratio1' in data):
      link += "&s_ratio1=" + data['s_ratio1']
   
   
   link = link.replace("[", "").replace("]", "").replace(" ", "")

   return DEFAULT_IFRAME.replace('{CONTENT}', link) 


# Curve Light
def make_light_curve(frames):
   lc_cnt = []
   lc_ff = []
   lc_count = []
   
   if(len(frames)>1):
      for frame in frames:
         if "intensity" in frame and "intensity_ff" in frame :
            lc_count.append(frame['x'])
            lc_cnt.append(frame['intensity']) 
            lc_ff.append(frame['intensity_ff']) 
 
      return create_iframe_to_graph(
            {'title':'Blob Light Curve',
            'title1': 'Blob Int.',
            'x1_vals': str(lc_count),
            'y1_vals': str(lc_cnt),
            'y2_vals': str(lc_ff) 
            })
   return ''



# Basic X,Y Plot with regression (?)
def make_xy_point_plot(frames):

   xs = []
   ys = []
 
   for frame in frames:
      xs.append(frame['x']) 
      ys.append(frame['y']) 
 
   if(len(xs)>1):
      trend_x, trend_y = poly_fit_points(xs,ys)
   
      tx1 = []
      ty1 = []

      for i in range(0,len(trend_x)):
         tx1.append(int(trend_x[i]))
         ty1.append(int(trend_y[i]))

      return create_iframe_to_graph(
         {'title':'XY Points and Line Fit',
          'x1_vals': str(xs),
          'y1_vals':str(ys),
          'x2_vals': str(tx1),
          'y2_vals':str(ty1),
          'y1_reverse':'1',
          'title1': 'Meteor pos.',
          'title2': 'Fit val',
          's_ratio1':'1'})
   return ''



# Compute the fit line of a set of data
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







# Create 3 different plots when possible
# 1- X,Y position 
# 2- Light Curves
def make_basic_plots(meteor_json_file):
   plots = ''
   if 'frames' in meteor_json_file:   
      if len(meteor_json_file['frames']) > 0:  
         # Main x,y plot + Curve Light
         plots = make_xy_point_plot(meteor_json_file['frames'])+ " " + make_light_curve(meteor_json_file['frames'])
   
   return plots