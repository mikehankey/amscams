from lib.PipeAutoCal import update_center_radec, get_catalog_stars, XYtoRADec, AzEltoRADec
from lib.PipeUtil import load_json_file
import cv2
import numpy as np

def all_sky_image(filename, cal_params, json_conf,pxscale_div,size=5000):
   asimg = np.zeros((cal_params['imageh'],cal_params['imagew'],3),dtype=np.uint8)
   cal_params = update_center_radec(filename,cal_params,json_conf)
   cat_stars = get_catalog_stars(cal_params)
   for cat_star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(new_cat_x,new_cat_y,filename,cal_params,json_conf)
      new_cat_x = int(new_cat_x)
      new_cat_y = int(new_cat_y)
      if mag < 4 and img_el > 0:
         print(name, new_cat_x, new_cat_y, img_az, img_el)
         foo = "bar"
         cv2.circle(asimg,(new_cat_x,new_cat_y), 3, (128,128,128), 1)
         text = str(int(img_az)) + " " + str(int(img_el))
         cv2.putText(asimg, str(""),  (int(new_cat_x),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1)


   # AD GRID MARKS
   rah,dech = AzEltoRADec(cal_params['center_az'],cal_params['center_el'],archive_file,cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))
   cal_params['ra_center'] = ra_center
   cal_params['dec_center'] = dec_center
      #else:
      #   print("SKIP:", img_az, img_el)
   return(asimg, cal_params)

if True:
   json_conf = load_json_file("../conf/as6.json")
   cal_params = {}
   cal_params['imagew'] = 1920 
   cal_params['imageh'] = 1080 
   cal_params['center_az'] = 0
   cal_params['center_el'] = 90
   cal_params['position_angle'] = 0
   cal_params['pixscale'] = 680
   pxscale_div = 2
   cal_params['pixscale'] = cal_params['pixscale'] 
   cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)

   filename = "2021_09_23_04_00_00"
   
   asimg, cal_params = all_sky_image(filename, cal_params, json_conf,pxscale_div,size=3000)
   cv2.imwrite("/mnt/ams2/starmap.jpg", asimg)
