import sys

def poly_fit_points(poly_x,poly_y, z = None):
   if z is None:
      if len(poly_x) >= 3:
         try:
            z = np.polyfit(poly_x,poly_y,1)
            f = np.poly1d(z)
         except:
            return(0)

      else:
         return(0)

      trendpoly = np.poly1d(z)
      new_ys = trendpoly(poly_x)

   return(poly_x, new_ys)

def make_lc_plot(frames):
   lc_cnt = []
   lc_ff = []
   lc_count = []
   
   for frame in frames:
      if "intensity" in frame and "intensity_ff" in frame :
         lc_count.append(frame['fn'])
         lc_cnt.append(frame['intensity']) 
         lc_ff.append(frame['intensity_ff']) 
   link = "/pycgi/graph.html?xat=frame&yat=intensity&plot_title=Blob_Light_Curve&x1=" + str(lc_count) + "&y1=" + str(lc_cnt) 
   link = link.replace("[", "")
   link = link.replace("]", "")
   link = link.replace(" ", "")
   iframe = "<iframe width=100% height=538 src=" + link + "></iframe>" 
   return(iframe)



def make_xy_point_plot(frames):
   xs = []
   ys = []

   print(frames)
   sys.exit(0)
   for frame in frames:
      xs.append(frame['x']) 
      ys.append(frame['y']) 

   #print(link)
   trend_x, trend_y = poly_fit_points(xs,ys)
   tx1 = []
   ty1 = []
   for i in range(0,len(trend_x)):
      tx1.append(int(trend_x[i]))
      ty1.append(int(trend_y[i]))

   link = "/pycgi/graph.html?xat=X&yat=Y&t1d=Point&t2d=Fit&ry=1&plot_title=XY_Points_and_Line_Fit&x1=" + str(xs) + "&y1=" + str(ys) + "&tx1=" + str(tx1) + "&ty1=" + str(ty1)
   link = link.replace("[", "")
   link = link.replace("]", "")
   link = link.replace(" ", "")
   iframe = "<iframe width='100%' height='538' src=" + link + "></iframe>" 
   return(iframe)


def make_basic_plot(meteor_json_file):
   plots = ''
   if 'frames' in meteor_json_file:  
      print("FRAMES<br/>")
      if len(meteor_json_file['frames']) > 0:
         print("SEVERAL FRAMES<br/>")
         xy_point_plot = make_xy_point_plot(meteor_json_file['frames'])
         cnt_light_curve = make_lc_plot(meteor_json_file['frames'])
         plots = xy_point_plot + "<P>" + cnt_light_curve
   
   return plots