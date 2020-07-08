import lib.brightstardata as bsd
import cv2
from lib.CalibLib import distort_xy_new, find_image_stars, distort_xy_new, XYtoRADec, radec_to_azel, get_catalog_stars,AzEltoRADec , HMS2deg, get_active_cal_file, RAdeg2HMS, clean_star_bg, define_crop_box
from lib.UtilLib import calc_dist
show = 0

def get_image_stars(file,img=None, show=0):
   stars = []
   if img is None:
      img = cv2.imread(file, 0)
   avg = np.mean(img)
   best_thresh = avg + 12
   _, star_bg = cv2.threshold(img, best_thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(star_bg, None , iterations=4)
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   cc = 0
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      px_val = int(img[y,x])
      cnt_img = img[y:y+h,x:x+w]
      cnt_img = cv2.GaussianBlur(cnt_img, (7, 7), 0)
      max_px, avg_px, px_diff,max_loc = eval_cnt(cnt_img.copy())
      name = "/mnt/ams2/tmp/cnt" + str(cc) + ".png"
      #star_test = test_star(cnt_img)
      x = x + int(w/2)
      y = y + int(h/2)
      if px_diff > 5 and w > 1 and h > 1 and w < 50 and h < 50:
          stars.append((x,y,int(max_px)))
          cv2.circle(img,(x,y), 5, (128,128,128), 1)

      cc = cc + 1
   #if show == 1:
   #   cv2.imshow('pepe', img)
   #   cv2.waitKey(1)

   temp = sorted(stars, key=lambda x: x[2], reverse=True)
   stars = temp[0:50]
   return(stars)


def reduce_fov_pos(this_poly, in_cal_params, cal_params_file, oimage, json_conf, cat_image_stars, min_run = 1, show=1):
   paired_stars = []
   for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,intensity, px_dist,cp_file in cat_image_stars:
      paired_stars.append(( name,mag,ra,dec,0,0,px_dist,new_cat_x,new_cat_y,0,0,new_cat_x,new_cat_y,ix,iy,px_dist))

   image = oimage.copy()
   image = cv2.resize(image, (1920,1080))
   # cal_params_file should be 'image' filename
   org_az = in_cal_params['center_az']
   org_el = in_cal_params['center_el']
   org_pixscale = in_cal_params['orig_pixscale']
   org_pos_angle = in_cal_params['orig_pos_ang']
   new_az = in_cal_params['center_az'] + this_poly[0]
   new_el = in_cal_params['center_el'] + this_poly[1]
   position_angle = float(in_cal_params['position_angle']) + this_poly[2]
   pixscale = float(in_cal_params['orig_pixscale']) + this_poly[3]

   rah,dech = AzEltoRADec(new_az,new_el,cal_params_file,in_cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))

   in_cal_params['position_angle'] = position_angle
   in_cal_params['ra_center'] = ra_center
   in_cal_params['dec_center'] = dec_center
   in_cal_params['pixscale'] = pixscale
   in_cal_params['device_lat'] = json_conf['site']['device_lat']
   in_cal_params['device_lng'] = json_conf['site']['device_lng']
   in_cal_params['device_alt'] = json_conf['site']['device_alt']



   for data in paired_stars:
      iname,mag,o_ra,o_dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist  = data
      old_cat_x = int(old_cat_x)
      old_cat_y = int(old_cat_y)
      cv2.rectangle(image, (old_cat_x-5, old_cat_y-5), (old_cat_x + 5, old_cat_y + 5), (255), 1)
      cv2.line(image, (six,siy), (old_cat_x,old_cat_y), (255), 1)
      cv2.circle(image,(six,siy), 10, (255), 1)

   fov_poly = 0
   pos_poly = 0
   x_poly = in_cal_params['x_poly']
   y_poly = in_cal_params['y_poly']
   cat_stars = get_catalog_stars(fov_poly, pos_poly, in_cal_params,"x",x_poly,y_poly,min=0)
   new_res = []
   new_paired_stars = []
   used = {}
   org_star_count = len(paired_stars)
   for cat_star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
      dname = name.decode("utf-8")
      for data in paired_stars:
         iname,mag,o_ra,o_dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist  = data
#dname == iname:
         if (ra == o_ra and dec == o_dec) or (iname == dname and iname != ''):
            pdist = calc_dist((six,siy),(new_cat_x,new_cat_y))
            if pdist <= 50:
               new_res.append(pdist)
               used_key = str(six) + "." + str(siy)
               if used_key not in used:
                  new_paired_stars.append((iname,mag,ra,dec,new_cat_x,new_cat_y,six,siy,pdist))

                  used[used_key] = 1
                  new_cat_x,new_cat_y = int(new_cat_x), int(new_cat_y)
                  cv2.rectangle(image, (new_cat_x-5, new_cat_y-5), (new_cat_x + 5, new_cat_y + 5), (255), 1)
                  cv2.line(image, (six,siy), (new_cat_x,new_cat_y), (255), 1)
                  cv2.circle(image,(six,siy), 10, (255), 1)

   paired_stars = new_paired_stars
   tres  =0
   for iname,mag,ra,dec,new_cat_x,new_cat_y,six,siy,pdist in new_paired_stars:
      tres = tres + pdist

   orig_star_count = len(in_cal_params['cat_image_stars'])

   if len(paired_stars) > 0:
      avg_res = tres / len(paired_stars)
   else:
      avg_res = 9999999
      res = 9999999

   if orig_star_count > len(paired_stars):
      pen = orig_star_count - len(paired_stars)
   else:
      pen = 0

   avg_res = avg_res + (pen * 10)
   show_res = avg_res - (pen*10)
   desc = "RES: " + str(show_res) + " " + str(len(new_paired_stars)) + " " + str(orig_star_count) + " PEN:" + str(pen)
   cv2.putText(image, desc,  (10,50), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   desc2 = "CENTER AZ/EL/POS" + str(new_az) + " " + str(new_el) + " " + str(in_cal_params['position_angle'])
   cv2.putText(image, desc2,  (10,80), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)

   desc2 = "PX SCALE:" + str(in_cal_params['pixscale'])
   cv2.putText(image, desc2,  (10,110), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)

   if show == 1:
      show_img = cv2.resize(image, (960,540))
      if "cam_id" in in_cal_params:
         cv2.imshow(cam_id, show_img)
      else:
         cv2.imshow('pepe', show_img)
      if min_run == 1:
         cv2.waitKey(10)
      else:
         cv2.waitKey(10)
   in_cal_params['position_angle'] = org_pos_angle
   if min_run == 1:
      return(avg_res)
   else:
      return(show_res)



def flex_get_image_stars_from_catalog(file,json_conf,cal_params_file, masks = [], cal_params = None, show = 0):
   # NOT USED!
   img = cv2.imread(file,0)
   img = cv2.resize(img, (1920,1080))
   img = mask_frame(img, [], masks)
   if cal_params is None:
      cal_params = load_json_file(cal_params_file)
   if "lat" in cal_params:
      lat = cal_params['lat']
      lon = cal_params['lon']
      alt = cal_params['alt']
   else:
      lat = json_conf['site']['device_lat']
      lon = json_conf['site']['device_lng']
      alt = json_conf['site']['device_alt']

   ra_center = cal_params['ra_center']
   dec_center = cal_params['dec_center']
   center_az = cal_params['center_az']
   center_el = cal_params['center_el']
   rah,dech = AzEltoRADec(center_az,center_el,file,cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")

   #rahh = RAdeg2HMS(rah)
   ra_center,dec_center = HMS2deg(str(rah),str(dech))


   cal_params['ra_center'] = ra_center
   cal_params['dec_center'] = dec_center

   fov_poly = 0
   pos_poly = 0
   x_poly = cal_params['x_poly']
   y_poly = cal_params['y_poly']
   cat_stars = get_catalog_stars(fov_poly, pos_poly, cal_params,"x",x_poly,y_poly,min=0)
   #cat_stars = cat_stars[0:50]

   cat_image_stars = []
   for cat_star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
      name = name.decode("utf-8")
      new_cat_x = int(new_cat_x)
      new_cat_y = int(new_cat_y)
      ix,iy = find_img_point_from_cat_star(new_cat_x,new_cat_y,img)
      if ix != 0 and iy != 0:
         px_dist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
         if px_dist < 10:
            cat_image_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file))


   # compute std dev distance
   tot_res = 0
   close_stars = []
   dist_list = []
   for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file in cat_image_stars:
      px_dist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
      dist_list.append(px_dist)
   std_dev_dist = np.std(dist_list)
   desc = "STD DEV DIST:" + str(std_dev_dist)
   tot_res = 0
   close_stars = []

   cv2.putText(img, desc ,  (300,300), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)

   tot_res = 0
   for pstar in cat_image_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file) = pstar
      if px_dist <= std_dev_dist:
         cv2.rectangle(img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
         cv2.line(img, (ix,iy), (new_cat_x,new_cat_y), (255), 2)
         cv2.circle(img,(ix,iy), 5, (128,128,128), 1)
         tot_res = tot_res + px_dist
         close_stars.append(pstar)

   if len(close_stars) > 0:
      avg_res = tot_res / len(close_stars)
   else:
      avg_res = 9999
   desc = "AVG RES:" + str(avg_res)
   cv2.putText(img, desc ,  (400,400), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
   #cv2.rectangle(img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)

   return(close_stars,img)



def flex_get_cat_stars(file, cal_params_file, json_conf, cal_params = None):
   good_cat_stars = []
   if cal_params == None:
      print("CAL PARAMS ARE NONE!")
      exit()
      cal_params = load_json_file(cal_params_file)

   if "lat" in cal_params:
      lat = cal_params['lat']
      lon = cal_params['lon']
      alt = cal_params['alt']
   else:
      lat = json_conf['site']['device_lat']
      lon = json_conf['site']['device_lng']
      alt = json_conf['site']['device_alt']
   ra_center = cal_params['ra_center']
   dec_center = cal_params['dec_center']
   center_az = cal_params['center_az']
   center_el = cal_params['center_el']
   rah,dech = AzEltoRADec(center_az,center_el,file,cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")

   ra_center,dec_center = HMS2deg(str(rah),str(dech))

   cal_params['ra_center'] = ra_center
   cal_params['dec_center'] = dec_center
   fov_poly = 0
   pos_poly = 0
   x_poly = cal_params['x_poly']
   y_poly = cal_params['y_poly']

   cat_stars = get_catalog_stars(fov_poly, pos_poly, cal_params,"x",x_poly,y_poly,min=0)
   for (name,mag,ra,dec,new_cat_x,new_cat_y) in cat_stars:
      #name = name.encode('utf-8')
      name = str(name.decode('utf-8'))

      good_cat_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y)) 

   return(good_cat_stars)

