from lib.PipeAutoCal import update_center_radec, get_catalog_stars, XYtoRADec
import cv2
import numpy as np

def all_sky_image(filename, cal_params, json_conf,pxscale_div,size=5000):
   aw = size
   ah = size
   asimg = np.zeros((ah,aw,3),dtype=np.uint8)
   cal_params['imagew'] = aw
   cal_params['imageh'] = ah
   cal_params['center_az'] = 0
   cal_params['center_el'] = 90
   cal_params['position_angle'] = 0
   cal_params['pixscale'] = cal_params['pixscale'] * 1.5 * pxscale_div
   cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params = update_center_radec(filename,cal_params,json_conf)
   cat_stars = get_catalog_stars(cal_params)
   for cat_star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(new_cat_x,new_cat_y,file,cal_params,json_conf)
      new_cat_x = int(new_cat_x)
      new_cat_y = int(new_cat_y)
      if img_el > 0:
         foo = "bar"
         #cv2.circle(asimg,(new_cat_x,new_cat_y), 7, (128,128,128), 10)
         #text = str(int(img_az)) + " " + str(int(img_el))
         #cv2.putText(asimg, str(text),  (int(new_cat_x),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1)
      #else:
      #   print("SKIP:", img_az, img_el)
   return(asimg, cal_params)

if True:
   json_conf = load_json_file("../conf/as6.json")
   cal_params['imagew'] = 1920  
   cal_params['imageh'] = 1920
   cal_params['center_az'] = 0
   cal_params['center_el'] = 90
   cal_params['position_angle'] = 0
   cal_params['pixscale'] = cal_params['pixscale'] * 1.5 * pxscale_div
   cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)

   filename = "2021_09_23_04_00_00"
   
   asimg, cal_params = all_sky_image(filename, cal_params, json_conf,pxscale_div,size=5000):
   cv2.imwrite("/mnt/ams2/starmap.jpg", asimg)
