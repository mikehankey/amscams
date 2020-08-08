"""

Autocal functions

"""
import scipy.optimize
import math
import cv2
import numpy as np
from lib.PipeUtil import bound_cnt, cnt_max_px, cfe, load_json_file, save_json_file, convert_filename_to_date_cam, angularSeparation, calc_dist, date_to_jd, get_masks 
from lib.PipeImage import mask_frame, quick_video_stack
from lib.DEFAULTS import *
import os
import ephem
import lib.brightstardata as bsd
from datetime import datetime
import glob


from PIL import ImageFont, ImageDraw, Image, ImageChops

def apply_calib(meteor_file, json_conf):
   if "json" in meteor_file:
      hd_file = meteor_file.replace(".json", "-HD.mp4")

   if cfe(hd_file) == 1:
      print(hd_file)

   stack = quick_video_stack(hd_file) 
   stack = cv2.cvtColor(stack, cv2.COLOR_BGR2GRAY)
   stack_org = stack.copy()

   stars = get_image_stars(meteor_file, stack_org.copy(), json_conf, 1)
   cal_files= get_cal_files(meteor_file)

  
   best_cal_file, cp = get_best_cal(meteor_file, cal_files, stars, stack, json_conf)
   cp['user_stars'] = stars
   if best_cal_file == 0:

      
      print("No cal file found!")
      return(0)

   mj = load_json_file(meteor_file)
   cp['best_cal'] = best_cal_file
   print(cp)
   calib = cp_to_calib(cp, stack_org)   
   mj['calib'] = calib

   star_image = draw_star_image(None, stack, cp, 0) 

   save_json_file(meteor_file, mj)
   print(meteor_file)


def get_cnt_intensity(image, x, y, size):
   #cv2.rectangle(image, (x-10, y-10), (x+10, y+10), (200, 200, 200), 1)
   x1,y1,x2,y2= bound_cnt(x,y,1920,1080,size)
   cnt = image[y1:y2,x1:x2]

def cp_to_calib(cp, cal_image = None):
   calib = {}
   calib['device'] = {}
   if 'site_lat' in cp:
      calib['device']['lat'] = cp['site_lat']
      calib['device']['lng'] = cp['site_lng']
      calib['device']['alt'] = cp['site_alt']
   elif 'device_lat' in cp:
      calib['device']['lat'] = cp['device_lat']
      calib['device']['lng'] = cp['device_lng']
      calib['device']['alt'] = cp['device_alt']

   calib['device']['angle'] = cp['position_angle']
   calib['device']['scale_px'] = cp['pixscale']
   calib['device']['orig_file'] = cp['best_cal']
   calib['device']['total_res_px'] = cp['total_res_px']
   calib['device']['total_res_deg'] = cp['total_res_deg']
   calib['device']['poly'] = {}
   calib['device']['poly']['x'] = cp['x_poly'] 
   calib['device']['poly']['y'] = cp['y_poly'] 
   calib['device']['poly']['x_fwd'] = cp['x_poly_fwd'] 
   calib['device']['poly']['y_fwd'] = cp['y_poly_fwd'] 
   calib['device']['center'] = {}
   calib['device']['center']['az'] = cp['center_az']
   calib['device']['center']['el'] = cp['center_el']
   calib['device']['center']['ra'] = cp['ra_center']
   calib['device']['center']['dec'] = cp['dec_center']
   calib['stars'] = []
   calib['img_dim'] = [cp['imagew'],cp['imageh']]


   for data in cp['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = data
      star = {}
      star['name'] = dcname 
      star['mag'] = mag
      star['ra'] = ra
      star['dec'] = dec
      star['dist_px'] = cat_dist
      star['dist_px_fwd'] = match_dist
      star['intensity'] = star_int
      star['i_pos'] = [six,siy]
      star['cat_dist_pos'] = [new_x,new_y]
      star['cat_und_pos'] = [new_cat_x,new_cat_y]
      calib['stars'].append(star)


   
   return(calib)



def get_best_cal(meteor_file, cal_files, stars , cal_img, json_conf):

   cal_scores = []
   for data in cal_files:
      cf, td = data
      cp = load_json_file(cf)

      # change the CP center ra/dec to match the AZ,EL at the time of this meteor
      cp = update_center_radec(meteor_file,cp,json_conf)
      cp['user_stars'] = stars
       
      cat_stars = get_catalog_stars(cp)
      cp = pair_stars(cp, meteor_file, json_conf, cal_img)
      match_perc = len(cp['cat_image_stars']) / len(cp['user_stars'])
      if len(cp['user_stars']) <= 0:
         cat_score = 9999

      if len(cp['cat_image_stars']) > 0:
         # lower is better
         cat_score = (cp['total_res_px'] * cp['total_res_deg'] / len(cp['cat_image_stars'])) / match_perc
      else:
         cat_score = 9999
      print(cf, len(cp['user_stars']), len(cp['cat_image_stars']), match_perc, cp['total_res_px'], cp['total_res_deg'], cat_score)
      cal_scores.append((cf, cat_score,cp))
   cal_scores = sorted(cal_scores, key=lambda x: x[1], reverse=False)
   if len(cal_scores) > 0:
      cf,cs,cp = cal_scores[0]
      cp['user_stars'] = stars
      return(cf, cp)
   else:
      return(0)

def update_center_radec(archive_file,cal_params,json_conf):
   rah,dech = AzEltoRADec(cal_params['center_az'],cal_params['center_el'],archive_file,cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))
   cal_params['ra_center'] = ra_center
   cal_params['dec_center'] = dec_center

   return(cal_params)

def get_cal_files(meteor_file):
   (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(meteor_file)
   pos_files = []
   cal_dirs = glob.glob("/mnt/ams2/cal/freecal/*" + cam + "*")
   for cd in cal_dirs:
      root_file = cd.split("/")[-1]
      if cfe(cd, 1) == 1:
         cpf = cd + "/" + root_file + "-stacked-calparams.json"
         if cfe(cpf) != 1:
            cpf = cd + "/" + root_file + "-calparams.json"
            if cfe(cpf) != 1:
               print("NO CAL FILE:", cpf)
               continue
      (c_datetime, ccam, c_date_str,cy,cm,cd, ch, cmm, cs) = convert_filename_to_date_cam(cpf)
      time_diff = f_datetime - c_datetime
      print(f_datetime, c_datetime, time_diff.total_seconds())
      pos_files.append((cpf, abs(time_diff.total_seconds())))




   pos_files = sorted(pos_files, key=lambda x: x[1], reverse=False)
   return(pos_files)
   

def solve_field(image_file, image_stars=[], json_conf={}):

   ifn = image_file.split("/")[-1]
   idir = image_file.replace(ifn, "")
   idir += "temp/"
   if cfe(idir, 1) == 0:
      os.makedirs(idir)

   plate_file = idir + ifn
   wcs_file = plate_file.replace(".jpg", ".wcs")
   grid_file = plate_file.replace(".jpg", "-grid.png")
   wcs_info_file = plate_file.replace(".jpg", "-wcsinfo.txt")
   solved_file = plate_file.replace(".jpg", ".solved")
   astrout = plate_file.replace(".jpg", "-astrout.txt")
   star_data_file = plate_file.replace(".jpg", "-stars.txt")

   if len(image_stars) < 10:
      return(0, {}, "")

   cmd = "mv " + image_file + " " + idir
   os.system(cmd)
   image_file = idir + ifn

   # solve field
   cmd = "/usr/local/astrometry/bin/solve-field " + plate_file + " --crpix-center --cpulimit=30 --verbose --no-delete-temp --overwrite --width=" + str(HD_W) + " --height=" + str(HD_H) + " -d 1-40 --scale-units dw --scale-low 50 --scale-high 90 -S " + solved_file + " >" + astrout
   astr = cmd
   if cfe(solved_file) == 0:
      os.system(cmd)

   if cfe(solved_file) == 1:
      print("SOLVED! Get WCS info.")
      # get WCS info
      cmd = "/usr/bin/jpegtopnm " + plate_file + "|/usr/local/astrometry/bin/plot-constellations -w " + wcs_file + " -o " + grid_file + " -i - -N -C -G 600 > /dev/null 2>&1 "
      print(cmd)
      os.system(cmd)

      cmd = "/usr/local/astrometry/bin/wcsinfo " + wcs_file + " > " + wcs_info_file
      print(cmd)
      os.system(cmd)

      os.system("grep Mike " + astrout + " >" +star_data_file + " 2>&1" )

      cal_params = save_cal_params(wcs_file,json_conf)
      cal_params = default_cal_params(cal_params, json_conf)
      cal_params['user_stars'] = image_stars

      return(1, cal_params, wcs_file) 
   else:
      print("Calibration failed!")
      print(astr) 
      return(0, {}, "")
   
def show_image(img, win, time=0):
   time = 300 
   #time = 0
   if img.shape[0] >= 1070:
      show_img = cv2.resize(img, (1280, 720))
   cv2.imshow(win, show_img)
   cv2.waitKey(time)  

def cal_all(json_conf):
   year = datetime.now().strftime("%Y")
   cal_dir = ARC_DIR + "CAL/AUTOCAL/" + year + "/*.png"
   files = glob.glob(cal_dir)
   for file in files:
      print(file)
      autocal(file, json_conf, 1)
      #exit()

def autocal(image_file, json_conf, show = 0):
   '''
      Open the image and find stars in it. 
      If there are not enough stars move the image to the 'bad' dir and end. 

      Make plate from found stars
      Send plate through plate solve 
      If the plate fails move the file to the 'failed' dir and end.

      If plate is a success save the calib info. 

      Figure out the poly lens stuff later or can do manually. This is mostly for screening good images from sense up folder.
  
   '''
   show = 0
   print("SHOW:", show)
   #exit()

   print(image_file)
   img = cv2.imread(image_file, 0)

   (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(image_file)
   cam = cam.replace(".png", "")
   masks = get_masks(cam, json_conf,1)
   star_img = img.copy()
   img = mask_frame(img, [], masks, 5)

   stars = get_image_stars(image_file, None, json_conf,0)

   print("TEST0", show)
   if show == 1:
      for star in stars:
         (x,y,sint) = star
         print(x,y,sint)
         #cv2.circle(star_img,(x,y), 10, (128,128,255), 1)
          
      show_image(star_img, 'pepe', 300)
   #exit()

   print("TEST1")

   plate_image, star_points = make_plate_image(img.copy(), stars )
   print("TEST2")



   plate_file = image_file.replace(".png", ".jpg")
   cv2.imwrite(plate_file, plate_image)
   print(plate_file)
   if show == 1:
      show_image(img, 'pepe', 300)
      show_image(plate_image, 'pepe', 300)
   status, cal_params,wcs_file = solve_field(plate_file, stars, json_conf)

   ifn = image_file.split("/")[-1]
   idir = image_file.replace(ifn, "")
   tdir = idir + "temp/"
   fdir = idir + "failed/"
   bdir = idir + "bad/"
   sdir = idir + "solved/"
   new_image_file = tdir + ifn
   if cfe(tdir, 1) == 0:
      os.makedirs(tdir)
   if cfe(fdir, 1) == 0:
      os.makedirs(fdir)
   if cfe(bdir, 1) == 0:
      os.makedirs(bdir)
   if cfe(sdir, 1) == 0:
      os.makedirs(sdir)
   os.system("cp " + image_file + " " + tdir)

   cal_params_file = wcs_file.replace(".wcs", "-calparams.json")
   if status == 1:
      print("Plate solve passed. Time for lens modeling!") 

      if show == 1:
         grid_file = wcs_file.replace(".wcs", "-grid.png")
         print("GRID:", grid_file)
         grid_image = cv2.imread(grid_file)
         show_image(grid_image, 'pepe', 90)


   else:
      print("Plate solve failed. Clean up the mess!") 
      # rm original file and temp files here
      cmd = "mv " + image_file + "* " + fdir
      os.system(cmd)
      return()

   # code below this point should only happen on the files that passed the plate solve. 

   cat_stars = get_catalog_stars(cal_params)
   cal_params = pair_stars(cal_params, cal_params_file, json_conf)
   #cal_params['cat_image_stars']  = remove_dupe_cat_stars(cal_params['cat_image_stars'])


   if show == 1:
      marked_img = make_fit_image(img, cal_params['cat_image_stars'])
      show_image(marked_img, 'pepe', 90)

   this_poly = np.zeros(shape=(4,), dtype=np.float64)
   cal_params['orig_pixscale'] = cal_params['pixscale']
   cal_params['orig_pos_ang'] = cal_params['position_angle']
   res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=( cal_params,image_file,img,json_conf, cal_params['cat_image_stars'],1,show), method='Nelder-Mead')

   #cal_params['cat_image_stars'], res_px,res_deg = cat_star_report(cal_params['cat_image_stars'], 4)
  # print("RES:", res_px)
   
   adj_az, adj_el, adj_pos, adj_px = res['x']
   cal_params['center_az'] += adj_az
   cal_params['center_el'] += adj_el
   cal_params['position_angle'] += adj_pos
   cal_params['pixscale'] += adj_px
   save_json_file(cal_params_file, cal_params)
   print("RIGID PARAMS FIT DONE.", cal_params_file)

   status, cal_params  = minimize_poly_params_fwd(cal_params_file, cal_params,json_conf)
   if status == 0:
      # ABORT!   
      print("Fit Process Faild! Clean up the mess!")
      # rm original file and temp files here
      cmd = "mv " + image_file + "* " + fdir
      os.system(cmd)
      return()


   cmd = "./AzElGrid.py az_grid " + cal_params_file + ">/tmp/mike.txt 2>&1"
   os.system(cmd)
   print(cmd)

   cat_stars = get_catalog_stars(cal_params)
   cal_params = pair_stars(cal_params, cal_params_file, json_conf)
   print("SAVING:", cal_params_file)
   save_json_file(cal_params_file, cal_params)
   
   draw_star_image(new_image_file, None, cal_params, 1) 

   freecal_copy(cal_params_file, json_conf)

   cpf = cal_params_file.split("/")[-1]
   pimf = cpf.replace("-calparams.json", ".jpg")
   imf = cpf.replace("-calparams.json", ".png")
   azf = cpf.replace("-calparams.json", "-azgrid.png")
   raf = cpf.replace("-calparams.json", "-grid.png")
   saf = cpf.replace("-calparams.json", "-stars.png")


   cmd = "mv " + idir + pimf + " " + sdir
   os.system(cmd)

   cmd = "mv " + tdir + cpf + " " + sdir
   os.system(cmd)

   cmd = "mv " + idir + imf + " " + sdir
   os.system(cmd)

   cmd = "mv " + tdir + pimf + " " + sdir
   os.system(cmd)

   cmd = "mv " + tdir + azf + " " + sdir
   os.system(cmd)

   cmd = "mv " + tdir + raf + " " + sdir
   os.system(cmd)

   cmd = "mv " + tdir + saf + " " + sdir
   print(cmd)
   os.system(cmd)


def cat_star_report(cat_image_stars, multi=2.5):
   #multi = 100
   c_dist = []
   m_dist = []
   for star in cat_image_stars:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      c_dist.append(cat_dist)
      m_dist.append(match_dist)
   med_c_dist = np.median(c_dist)
   med_m_dist = np.median(m_dist)
   if med_c_dist < 1:
      med_c_dist = 1 

   print("MED DIST:", med_c_dist, med_m_dist)
   clean_stars = [] 
   c_dist = []
   m_dist = []
   for star in cat_image_stars:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      if cat_dist > med_c_dist * multi:
         print("BAD", dcname, cat_dist, med_c_dist - cat_dist  )
      else:
         print(dcname, cat_dist, med_c_dist - cat_dist  )
         c_dist.append(cat_dist)
         m_dist.append(match_dist)
         clean_stars.append(star)
   return(clean_stars, np.median(c_dist), np.median(m_dist))
  
def make_fit_image(image, cat_image_stars) :
   marked_img = image.copy()
   for star in cat_image_stars:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star

      new_x = int(new_x)
      new_y = int(new_y)


      # catalog star enhanced position
      cv2.rectangle(marked_img, (new_x-10, new_y-10), (new_x+10, new_y+10), (200, 200, 200), 1)

      # catalog original star position
      cv2.rectangle(marked_img, (new_cat_x-15, new_cat_y-15), (new_cat_x+15, new_cat_y+15), (90, 90, 90), 1)

      # image star location position
      cv2.circle(marked_img,(six,siy), 10, (128,128,255), 1)

      # draw line from original star to enhanced star locations
      #cv2.line(marked_img, (new_cat_x,new_cat_y), (new_x,new_y), (255), 2)

      # draw line from enhanced star locations to image star location. This is the value we want to minimize! Less is better
      cv2.line(marked_img, (six,siy), (new_x,new_y), (255), 2)
   return(marked_img)


def get_image_stars(file=None,img=None,json_conf=None,show=0):
   stars = []
   if img is None:
      img = cv2.imread(file, 0)
   raw_img = img.copy()
   (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(file)
   cam = cam.replace(".png", "")
   masks = get_masks(cam, json_conf,1)
   img = mask_frame(img, [], masks, 5)


   avg = np.median(img) 
   best_thresh = avg + 20
   _, star_bg = cv2.threshold(img, best_thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(star_bg, None , iterations=4)

   if show == 1:
      show_image(thresh_obj, 'pepe', 0)

   res = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(res) == 3:
      (_, cnts, xx) = res
   else:
      (cnts ,xx) = res
   cc = 0
   for (i,c) in enumerate(cnts):

      

      x,y,w,h = cv2.boundingRect(cnts[i])
      bx = int(x + (w/2))
      by = int(y + (h/2))
      bx1,by1,bx2,by2= bound_cnt(bx,by,1920,1080,15)
      bg_cnt_img = raw_img[by1:by2,bx1:bx2]


      px_val = int(img[y,x])
      cnt_img = raw_img[y:y+h,x:x+w]
      cnt_img = cv2.GaussianBlur(cnt_img, (7, 7), 0)

      max_px, avg_px, px_diff,max_loc,star_int = eval_cnt(cnt_img.copy(), avg)
      max_int = np.sum(cnt_img)
      avg_int = np.median(bg_cnt_img) * cnt_img.shape[0] * cnt_img.shape[1]
#      star_int = max_int - avg_int 
      star_int = max_int 
      star_multi = max_int / avg_int
      print("STAR INT: ", star_int)

      name = "/mnt/ams2/tmp/cnt" + str(cc) + ".png"
      #star_test = test_star(cnt_img)
      x = x + int(w/2)
      y = y + int(h/2)
      #if px_diff > 10 and 500 < star_int < 20000 and w > 1 and h > 1 and w < 50 and h < 50:
      #if px_diff > 5 and 1.05 < star_multi < 50 and w > 1 and h > 1 and w < 50 and h < 50:
      #if px_diff > 5 and w > 1 and h > 1 and w < 50 and h < 50:
      if star_int > 300:
          stars.append((x,y,int(star_int)))
          #cv2.circle(img,(x,y), 5, (128,128,128), 1)
          print("STAR:", max_px, avg_px, max_int, avg_int, star_multi, star_int)
      else:
          #cv2.circle(img,(x,y), 5, (255,0,0), 1)
          print("BADSTAR:", max_px, avg_px, max_int, avg_int, star_multi, star_int)

      cc = cc + 1
   if show == 1:
      show_image(img, 'pepe', 0)
   temp = sorted(stars, key=lambda x: x[2], reverse=True)
   stars = temp[0:50]
   return(stars)


def eval_cnt(cnt_img, avg_px=5):
   cnt_img = cv2.GaussianBlur(cnt_img, (7, 7), 0)
   cnth,cntw = cnt_img.shape
   max_px = np.max(cnt_img)
   avg_px = np.mean(cnt_img)
   avg_int = (cnt_img[0,0] + cnt_img[-1,0] + cnt_img[0,-1] + cnt_img[-1,-1]) / 4
   avg_int = avg_int * cnt_img.shape[0] * cnt_img.shape[1]
   max_int = np.sum(cnt_img)

   px_diff = max_px - avg_px
   int_diff = max_int - avg_int

   star_int_multi = max_int / avg_int
   min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)
   mx, my = max_loc
   mx = mx - int(cnt_img.shape[1]/2)
   my = my - int(cnt_img.shape[0]/2) 
   return(max_px, avg_px,px_diff,(mx,my),int_diff)

def make_plate_image(image, file_stars): 
   ih, iw = image.shape
      

   plate_image = np.zeros((ih,iw),dtype=np.uint8)
   hd_stack_img = image
   hd_stack_img_an = hd_stack_img.copy()
   star_points = []
   print("TEST")
   for file_star in file_stars:
      (ix,iy,bp) = file_star
         
      x,y = int(ix),int(iy)
      #cv2.circle(hd_stack_img_an, (int(x),int(y)), 5, (128,128,128), 1)
      y1 = y - 15
      y2 = y + 15
      x1 = x - 15
      x2 = x + 15
      x1,y1,x2,y2= bound_cnt(x,y,iw,ih,15)
      cnt_img = hd_stack_img[y1:y2,x1:x2]
      ch,cw = cnt_img.shape
      max_pnt,max_val,min_val = cnt_max_px(cnt_img)
      mx,my = max_pnt
      mx = mx - 15
      my = my - 15
      cy1 = y + my - 15
      cy2 = y + my +15
      cx1 = x + mx -15
      cx2 = x + mx +15
      cx1,cy1,cx2,cy2= bound_cnt(x+mx,y+my,iw,ih)
      if ch > 0 and cw > 0:
         cnt_img = hd_stack_img[cy1:cy2,cx1:cx2]
         bgavg = np.mean(cnt_img)
         try:
            cnt_img = clean_star_bg(cnt_img, bgavg + 3)

            #cv2.rectangle(hd_stack_img_an, (x+mx-5-15, y+my-5-15), (x+mx+5-15, y+my+5-15), (128, 128, 128), 1)
            #cv2.rectangle(hd_stack_img_an, (x+mx-15-15, y+my-15-15), (x+mx+15-15, y+my+15-15), (128, 128, 128), 1)
            star_points.append([x+mx,y+my])
            plate_image[cy1:cy2,cx1:cx2] = cnt_img
         except:
            print("Failed star")

   points_json = {}
   points_json['user_stars'] = star_points

   return(plate_image,star_points)


def clean_star_bg(cnt_img, bg_avg):
   max_px = np.max(cnt_img)
   min_px = np.min(cnt_img)
   avg_px = np.mean(cnt_img)
   halfway = int((max_px - min_px) / 2)
   cnt_img.setflags(write=1)
   for x in range(0,cnt_img.shape[1]):
      for y in range(0,cnt_img.shape[0]):
         px_val = cnt_img[y,x]
         if px_val < bg_avg + halfway:
            #cnt_img[y,x] = random.randint(int(bg_avg - 3),int(avg_px))
            pxval = cnt_img[y,x]
            pxval = int(pxval) / 2
            cnt_img[y,x] = 0
   return(cnt_img)

def save_cal_params(wcs_file,json_conf):
   wcs_info_file = wcs_file.replace(".wcs", "-wcsinfo.txt")
   cal_params_file = wcs_file.replace(".wcs", "-calparams.json")
   fp =open(wcs_info_file, "r")
   cal_params_json = {}
   for line in fp:
      line = line.replace("\n", "")
      field, value = line.split(" ")
      if field == "imagew":
         cal_params_json['imagew'] = value
      if field == "imageh":
         cal_params_json['imageh'] = value
      if field == "pixscale":
         cal_params_json['pixscale'] = value
      if field == "orientation":
         cal_params_json['position_angle'] = float(value) + 180
      if field == "ra_center":
         cal_params_json['ra_center'] = value
      if field == "dec_center":
         cal_params_json['dec_center'] = value
      if field == "fieldw":
         cal_params_json['fieldw'] = value
      if field == "fieldh":
         cal_params_json['fieldh'] = value
      if field == "ramin":
         cal_params_json['ramin'] = value
      if field == "ramax":
         cal_params_json['ramax'] = value
      if field == "decmin":
         cal_params_json['decmin'] = value
      if field == "decmax":
         cal_params_json['decmax'] = value

   ra = cal_params_json['ra_center']
   dec = cal_params_json['dec_center']
   lat = json_conf['site']['device_lat']
   lon = json_conf['site']['device_lng']
   alt = json_conf['site']['device_alt']

   (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(wcs_file)
   new_date = y + "/" + m + "/" + d + " " + h + ":" + mm + ":" + s
   az, el = radec_to_azel(ra,dec, new_date,json_conf)

   cal_params_json['center_az'] = az
   cal_params_json['center_el'] = el
   #cal_params = default_cal_params(cal_params, json_conf)

 

   save_json_file(cal_params_file, cal_params_json)
   return(cal_params_json)

def radec_to_azel(ra,dec, caldate,json_conf, lat=None,lon=None,alt=None):

   if lat is None:
      lat = json_conf['site']['device_lat']
      lon = json_conf['site']['device_lng']
      alt = json_conf['site']['device_alt']

   body = ephem.FixedBody()
   #print ("BODY: ", ra, dec)
   body._epoch=ephem.J2000

   rah = RAdeg2HMS(ra)
   dech= Decdeg2DMS(dec)

   body._ra = rah
   body._dec = dech

   

   obs = ephem.Observer()
   obs.lat = ephem.degrees(lat)
   obs.lon = ephem.degrees(lon)
   obs.date = caldate
   obs.elevation=float(alt)
   body.compute(obs)
   az = str(body.az)
   el = str(body.alt)

   #print("RADEC_2_AZEL BODY RA:", body._ra)
   #print("RADEC_2_AZEL BODY DEC:", body._dec)
   #print("RADEC_2_AZEL OBS DATE:", obs.date)
   #print("RADEC_2_AZEL OBS LAT:", obs.lat)
   #print("RADEC_2_AZEL OBS LON:", obs.lon)
   #print("RADEC_2_AZEL OBS EL:", obs.elevation)
   #print("RADEC_2_AZEL AZH AZH:", az)
   #print("RADEC_2_AZEL ELH ELH:", el)
   
   (d,m,s) = az.split(":")
   dd = float(d) + float(m)/60 + float(s)/(60*60)
   az = dd

   (d,m,s) = el.split(":")
   dd = float(d) + float(m)/60 + float(s)/(60*60)
   el = dd

   return(az,el)

def HMS2deg(ra='', dec=''):
  RA, DEC, rs, ds = '', '', 1, 1
  if dec:
    D, M, S = [float(i) for i in dec.split()]
    if str(D)[0] == '-':
      ds, D = -1, abs(D)
    deg = D + (M/60) + (S/3600)
    DEC = '{0}'.format(deg*ds)
  
  if ra:
    H, M, S = [float(i) for i in ra.split()]
    if str(H)[0] == '-':
      rs, H = -1, abs(H)
    deg = (H*15) + (M/4) + (S/240)
    RA = '{0}'.format(deg*rs)
  
  if ra and dec:
    return (RA, DEC)
  else:
    return RA or DEC

def RAdeg2HMS( RAin ):
   RAin = float(RAin)
   if(RAin<0):
      sign = -1
      ra   = -RAin
   else:
      sign = 1
      ra   = RAin

   h = int( ra/15. )
   ra -= h*15.
   m = int( ra*4.)
   ra -= m/4.
   s = ra*240.

   if(sign == -1):
      out = '-%02d:%02d:%06.3f'%(h,m,s)
   else: out = '+%02d:%02d:%06.3f'%(h,m,s)

   return out

def Decdeg2DMS( Decin ):
   Decin = float(Decin)
   if(Decin<0):
      sign = -1
      dec  = -Decin
   else:
      sign = 1
      dec  = Decin

   d = int( dec )
   dec -= d
   dec *= 100.
   m = int( dec*3./5. )
   dec -= m*5./3.
   s = dec*180./5.

   if(sign == -1):
      out = '-%02d:%02d:%06.3f'%(d,m,s)
   else: out = '+%02d:%02d:%06.3f'%(d,m,s)

   return out

def pair_stars(cal_params, cal_params_file, json_conf, cal_img=None):

   if cal_img is None:
      img_file = cal_params_file.replace("-calparams.json", ".jpg")
      cal_img = cv2.imread(img_file, 0)
   ih, iw= cal_img.shape
   ra_center = cal_params['ra_center']
   dec_center = cal_params['dec_center']
   center_az = cal_params['center_az']
   center_el = cal_params['center_el']
   star_matches = []
   my_close_stars = []
   total_match_dist = 0
   total_cat_dist = 0
   total_matches = 0

   cat_stars = get_catalog_stars(cal_params)
   new_user_stars = []
   new_stars = []
   for star in cal_params['user_stars']:
      x,y,bp = star
      #cv2.rectangle(cal_img, (x-4, y-4), (x+ 4, y+ 4), (128, 128, 128), 1)
      y1 = y - 15
      y2 = y + 15
      x1 = x - 15
      x2 = x + 15
      if (x-10 > 0 and y-10 > 0) and (x+10 < iw-1 and y+10 < ih-1):
         cnt_img = cal_img[y1:y2,x1:x2]
         cnh,cnw = cnt_img.shape
         if cnh > 0 and cnw > 0:
            cv2.rectangle(cal_img, (x1, y1), (x2, y2), (0, 0, 0), 1)
            max_px, avg_px, px_diff,max_loc,star_int = eval_cnt(cnt_img)
            print("STAR INT:", star_int) 
            mx,my = max_loc
         else:
            continue
         # maybe bug here?
         pp_x = (x + int(max_loc[0]) )
         pp_y = (y + int(max_loc[1]) )
         #pp_x = (x + int(max_loc[0]) )
         #pp_y = (y + int(max_loc[1]) )
         #cv2.circle(cal_img,(pp_x,pp_y), 7, (128,128,128), 1)

         new_user_stars.append((pp_x,pp_y,star_int))

   cal_params['user_stars'] = new_user_stars   
   cal_params['stars'] = new_stars 


   for ix,iy,bp in cal_params['user_stars']:
      close_stars = find_close_stars((ix,iy), cat_stars)
      for name,mag,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist in close_stars:
         dcname = str(name.decode("utf-8"))
         dbname = dcname.encode("utf-8")
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(ix,iy,cal_params_file,cal_params,json_conf)
         match_dist = abs(angularSeparation(ra,dec,img_ra,img_dec))
         my_close_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp))
         total_match_dist = total_match_dist + match_dist
         total_cat_dist = total_cat_dist + cat_dist
         total_matches = total_matches + 1

         #cv2.rectangle(cal_img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
         #cv2.rectangle(cal_img, (six-2, siy-2), (six+ 2, siy+ 2), (255, 255, 255), 1)
         #cv2.circle(cal_img,(six,siy), 7, (128,128,128), 1)


   cal_params['cat_image_stars'] = my_close_stars
   cal_params['total_res_deg'] = total_match_dist / total_matches
   cal_params['total_res_px'] = total_cat_dist / total_matches
   cal_params['cal_params_file'] = cal_params_file

   fit_on = 0
   if fit_on == 1:
      os.system("./fitPairs.py " + cal_params_file)

   return(cal_params)

def get_catalog_stars(cal_params):
 
   mybsd = bsd.brightstardata()
   bright_stars = mybsd.bright_stars
   
   catalog_stars = []
   possible_stars = 0
   img_w = int(cal_params['imagew'])
   img_h = int(cal_params['imageh'])
   RA_center = float(cal_params['ra_center']) 
   dec_center = float(cal_params['dec_center']) 
   F_scale = 3600/float(cal_params['pixscale'])
   x_poly = cal_params['x_poly']
   y_poly = cal_params['y_poly']
   fov_w = img_w / F_scale
   fov_h = img_h / F_scale
   fov_radius = np.sqrt((fov_w/2)**2 + (fov_h/2)**2)

   pos_angle_ref = cal_params['position_angle'] 
   x_res = int(cal_params['imagew'])
   y_res = int(cal_params['imageh'])

   #print("USING CALP:", RA_center, dec_center, pos_angle_ref, cal_params['pixscale'], x_res, y_res)

   if img_w < 1920:
      center_x = int(x_res / 2)
      center_y = int(x_res / 2)

   bright_stars_sorted = sorted(bright_stars, key=lambda x: x[4], reverse=False)

   for bname, cname, ra, dec, mag in bright_stars_sorted:
      dcname = cname.decode("utf-8")
      dbname = bname.decode("utf-8")
      if dcname == "":
         name = bname
      else:
         name = cname

      ang_sep = angularSeparation(ra,dec,RA_center,dec_center)
      if ang_sep < fov_radius and float(mag) < 5.5:
         new_cat_x, new_cat_y = distort_xy(0,0,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale)

         possible_stars = possible_stars + 1
         catalog_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y))

   return(catalog_stars)

def default_cal_params(cal_params,json_conf):
   
   if 'lat' not in cal_params:
      cal_params['site_lat'] = json_conf['site']['device_lat']
      cal_params['device_lat'] = json_conf['site']['device_lat']
   if 'lon ' not in cal_params:
      cal_params['site_lng'] = json_conf['site']['device_lng']
      cal_params['device_lng'] = json_conf['site']['device_lng']
   if 'alt ' not in cal_params:
      cal_params['site_alt'] = json_conf['site']['device_alt']
      cal_params['device_alt'] = json_conf['site']['device_alt']

   if 'x_poly' not in cal_params:
      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly'] = x_poly.tolist()
   if 'y_poly' not in cal_params:
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly'] = x_poly.tolist()
   if 'x_poly_fwd' not in cal_params:
      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly_fwd'] = x_poly.tolist()
   if 'y_poly_fwd' not in cal_params:
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly_fwd'] = x_poly.tolist()

   return(cal_params)


def distort_xy(sx,sy,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale=1):

   ra_star = ra
   dec_star = dec

   #F_scale = F_scale/10
   w_pix = 50*F_scale/3600
   #F_scale = 158 * 2
   #F_scale = 155
   #F_scale = 3600/16
   #F_scale = 3600/F_scale
   #F_scale = 1

   # Gnomonization of star coordinates to image coordinates
   ra1 = math.radians(float(RA_center))
   dec1 = math.radians(float(dec_center))
   ra2 = math.radians(float(ra_star))
   dec2 = math.radians(float(dec_star))
   ad = math.acos(math.sin(dec1)*math.sin(dec2) + math.cos(dec1)*math.cos(dec2)*math.cos(ra2 - ra1))
   radius = math.degrees(ad)
   
   try:
      sinA = math.cos(dec2)*math.sin(ra2 - ra1)/math.sin(ad)
      cosA = (math.sin(dec2) - math.sin(dec1)*math.cos(ad))/(math.cos(dec1)*math.sin(ad))
   except:
      sinA = 0
      cosA = 0
   theta = -math.degrees(math.atan2(sinA, cosA))
   theta = theta + pos_angle_ref - 90.0
   #theta = theta + pos_angle_ref - 90 + (1000*x_poly[12]) + (1000*y_poly[12])
   #theta = theta + pos_angle_ref - 90



   dist = np.degrees(math.acos(math.sin(dec1)*math.sin(dec2) + math.cos(dec1)*math.cos(dec2)*math.cos(ra1 - ra2)))

   # Calculate the image coordinates (scale the F_scale from CIF resolution)
   X1 = radius*math.cos(math.radians(theta))*F_scale
   Y1 = radius*math.sin(math.radians(theta))*F_scale
   # Calculate distortion in X direction
   dX = (x_poly[0]
      + x_poly[1]*X1
      + x_poly[2]*Y1
      + x_poly[3]*X1**2
      + x_poly[4]*X1*Y1
      + x_poly[5]*Y1**2
      + x_poly[6]*X1**3
      + x_poly[7]*X1**2*Y1
      + x_poly[8]*X1*Y1**2
      + x_poly[9]*Y1**3
      + x_poly[10]*X1*math.sqrt(X1**2 + Y1**2)
      + x_poly[11]*Y1*math.sqrt(X1**2 + Y1**2))

   # Add the distortion correction and calculate X image coordinates
   #x_array[i] = (X1 - dX)*x_res/384.0 + x_res/2.0
   new_x = X1 - dX + x_res/2.0

   # Calculate distortion in Y direction
   dY = (y_poly[0]
      + y_poly[1]*X1
      + y_poly[2]*Y1
      + y_poly[3]*X1**2
      + y_poly[4]*X1*Y1
      + y_poly[5]*Y1**2
      + y_poly[6]*X1**3
      + y_poly[7]*X1**2*Y1
      + y_poly[8]*X1*Y1**2
      + y_poly[9]*Y1**3
      + y_poly[10]*Y1*math.sqrt(X1**2 + Y1**2)
      + y_poly[11]*X1*math.sqrt(X1**2 + Y1**2))

   # Add the distortion correction and calculate Y image coordinates
   #y_array[i] = (Y1 - dY)*y_res/288.0 + y_res/2.0
   new_y = Y1 - dY + y_res/2.0
   #print("DENIS RA:", X1, Y1, sx, sy, F_scale, w_pix, dist)
   #print("DENIS:", X1, Y1, dX, dY, sx, sy, F_scale, w_pix, dist)
   #print("THETA:",theta)
   #print("DENIS:", sx,sy,new_x,new_y, sx-new_x, sy-new_y)
   return(new_x,new_y)


def find_close_stars(star_point, catalog_stars,dt=25):

   scx,scy = star_point
   scx,scy = int(scx), int(scy)

   center_dist = calc_dist((scx,scy),(960,540))
   if center_dist > 500:
      dt = 55
   if center_dist > 700:
      dt = 65
   if center_dist > 800:
      dt = 75
   if center_dist > 900:
      dt = 150


   matches = []
   #print("IMAGE STAR:", scx,scy)
   for name,mag,ra,dec,cat_x,cat_y in catalog_stars:
      cat_x, cat_y = int(cat_x), int(cat_y)
      if cat_x - dt < scx < cat_x + dt and cat_y -dt < scy < cat_y + dt:
         #print("\t{:s} at {:d},{:d} is CLOSE to image star {:d},{:d} ".format(name,cat_x,cat_y,scx,scy))
         cat_star_dist= calc_dist((cat_x,cat_y),(scx,scy))
         matches.append((name,mag,ra,dec,cat_x,cat_y,scx,scy,cat_star_dist))


   if len(matches) > 1:
      matches_sorted = sorted(matches, key=lambda x: x[8], reverse=False)
      # check angle back to center from cat star and then angle from cat star to img star and pick the one with the closest match for the star...
      #for match in matches_sorted:
      #print("MULTI MATCH:", scx,scy, matches)
     
      matches = matches_sorted
   #print("<HR>")

   return(matches[0:1])


def AzEltoRADec(az,el,cal_file,cal_params,json_conf):
   azr = np.radians(az)
   elr = np.radians(el)
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cal_file)
   #hd_datetime = hd_y + "/" + hd_m + "/" + hd_d + " " + hd_h + ":" + hd_M + ":" + hd_s
   if "device_lat" in cal_params:
      device_lat = cal_params['device_lat']
      device_lng = cal_params['device_lng']
      device_alt = cal_params['device_alt']
   else:
      device_lat = json_conf['site']['device_lat']
      device_lng = json_conf['site']['device_lng']
      device_alt = json_conf['site']['device_alt']

   obs = ephem.Observer()


   obs.lat = str(device_lat)
   obs.lon = str(device_lng)
   obs.elevation = float(device_alt)
   obs.date = hd_datetime 
   #print("AZ/RA DEBUG: ", device_lat, device_lng, device_alt, hd_datetime, az, el)
   #print("AZ2RA DATETIME:", hd_datetime)
   #print("AZ2RA LAT:", obs.lat)
   #print("AZ2RA LON:", obs.lon)
   #print("AZ2RA ELV:", obs.elevation)
   #print("AZ2RA DATE:", obs.date)
   #print("AZ2RA AZ,EL:", az,el)
   #print("AZ2RA RAD AZ,EL:", azr,elr)

   ra,dec = obs.radec_of(azr,elr)
   
   #print("AZ2RA RA,DEC:", ra,dec)

   return(ra,dec)


def XYtoRADec(img_x,img_y,cal_file,cal_params,json_conf):
   #print("CAL FILE IS : ", cal_file)
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cal_file)
   F_scale = 3600/float(cal_params['pixscale'])
   #F_scale = 24

   total_min = (int(hd_h) * 60) + int(hd_M)
   day_frac = total_min / 1440 
   hd_d = int(hd_d) + day_frac
   jd = date_to_jd(int(hd_y),int(hd_m),float(hd_d))

   lat = float(json_conf['site']['device_lat'])
   lon = float(json_conf['site']['device_lng'])

   # Calculate the reference hour angle
   T = (jd - 2451545.0)/36525.0
   Ho = (280.46061837 + 360.98564736629*(jd - 2451545.0) + 0.000387933*T**2 \
      - (T**3)/38710000.0)%360

   x_poly_fwd = cal_params['x_poly_fwd']
   y_poly_fwd = cal_params['y_poly_fwd']
   
   dec_d = float(cal_params['dec_center']) 
   RA_d = float(cal_params['ra_center']) 

   dec_d = dec_d + (x_poly_fwd[13] * 100)
   dec_d = dec_d + (y_poly_fwd[13] * 100)

   RA_d = RA_d + (x_poly_fwd[14] * 100)
   RA_d = RA_d + (y_poly_fwd[14] * 100)

   pos_angle_ref = float(cal_params['position_angle']) + (1000*x_poly_fwd[12]) + (1000*y_poly_fwd[12])

   # Convert declination to radians
   dec_rad = math.radians(dec_d)

   # Precalculate some parameters
   sl = math.sin(math.radians(lat))
   cl = math.cos(math.radians(lat))


   x_det = img_x - int(cal_params['imagew'])/2
   y_det = img_y - int(cal_params['imageh'])/2

   dx = (x_poly_fwd[0]
      + x_poly_fwd[1]*x_det
      + x_poly_fwd[2]*y_det
      + x_poly_fwd[3]*x_det**2
      + x_poly_fwd[4]*x_det*y_det
      + x_poly_fwd[5]*y_det**2
      + x_poly_fwd[6]*x_det**3
      + x_poly_fwd[7]*x_det**2*y_det
      + x_poly_fwd[8]*x_det*y_det**2
      + x_poly_fwd[9]*y_det**3
      + x_poly_fwd[10]*x_det*math.sqrt(x_det**2 + y_det**2)
      + x_poly_fwd[11]*y_det*math.sqrt(x_det**2 + y_det**2))

   # Add the distortion correction
   x_pix = x_det + dx 

   #print("ORIG X:", img_x)
   #print("X DET:", x_det)
   #print("DX :", dx)
   #print("NEWX :", x_pix)

   dy = (y_poly_fwd[0]
      + y_poly_fwd[1]*x_det
      + y_poly_fwd[2]*y_det
      + y_poly_fwd[3]*x_det**2
      + y_poly_fwd[4]*x_det*y_det
      + y_poly_fwd[5]*y_det**2
      + y_poly_fwd[6]*x_det**3
      + y_poly_fwd[7]*x_det**2*y_det
      + y_poly_fwd[8]*x_det*y_det**2
      + y_poly_fwd[9]*y_det**3
      + y_poly_fwd[10]*y_det*math.sqrt(x_det**2 + y_det**2)
      + y_poly_fwd[11]*x_det*math.sqrt(x_det**2 + y_det**2))

   # Add the distortion correction
   y_pix = y_det + dy 

   x_pix = x_pix / F_scale
   y_pix = y_pix / F_scale

   ### Convert gnomonic X, Y to alt, az ###

   # Caulucate the needed parameters
   radius = math.radians(math.sqrt(x_pix**2 + y_pix**2))
   theta = math.radians((90 - pos_angle_ref + math.degrees(math.atan2(y_pix, x_pix)))%360)

   sin_t = math.sin(dec_rad)*math.cos(radius) + math.cos(dec_rad)*math.sin(radius)*math.cos(theta)
   Dec0det = math.atan2(sin_t, math.sqrt(1 - sin_t**2))

   sin_t = math.sin(theta)*math.sin(radius)/math.cos(Dec0det)
   cos_t = (math.cos(radius) - math.sin(Dec0det)*math.sin(dec_rad))/(math.cos(Dec0det)*math.cos(dec_rad))
   RA0det = (RA_d - math.degrees(math.atan2(sin_t, cos_t)))%360

   h = math.radians(Ho + lon - RA0det)
   sh = math.sin(h)
   sd = math.sin(Dec0det)
   ch = math.cos(h)
   cd = math.cos(Dec0det)

   x = -ch*cd*sl + sd*cl
   y = -sh*cd
   z = ch*cd*cl + sd*sl

   r = math.sqrt(x**2 + y**2)

   # Calculate azimuth and altitude
   azimuth = math.degrees(math.atan2(y, x))%360
   altitude = math.degrees(math.atan2(z, r))



   ### Convert alt, az to RA, Dec ###

   # Never allow the altitude to be exactly 90 deg due to numerical issues
   if altitude == 90:
      altitude = 89.9999

   # Convert altitude and azimuth to radians
   az_rad = math.radians(azimuth)
   alt_rad = math.radians(altitude)

   saz = math.sin(az_rad)
   salt = math.sin(alt_rad)
   caz = math.cos(az_rad)
   calt = math.cos(alt_rad)

   x = -saz*calt
   y = -caz*sl*calt + salt*cl
   HA = math.degrees(math.atan2(x, y))

   # Calculate the hour angle
   T = (jd - 2451545.0)/36525.0
   hour_angle = (280.46061837 + 360.98564736629*(jd - 2451545.0) + 0.000387933*T**2 - T**3/38710000.0)%360

   RA = (hour_angle + lon - HA)%360
   dec = math.degrees(math.asin(sl*salt + cl*calt*caz))

   ### ###




   return(x_pix+img_x,y_pix+img_y,RA,dec,azimuth,altitude)
def AzEltoRADec(az,el,cal_file,cal_params,json_conf):
   azr = np.radians(az)
   elr = np.radians(el)
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cal_file)
   #hd_datetime = hd_y + "/" + hd_m + "/" + hd_d + " " + hd_h + ":" + hd_M + ":" + hd_s
   if "device_lat" in cal_params:
      device_lat = cal_params['device_lat']
      device_lng = cal_params['device_lng']
      device_alt = cal_params['device_alt']
   else:
      device_lat = json_conf['site']['device_lat']
      device_lng = json_conf['site']['device_lng']
      device_alt = json_conf['site']['device_alt']

   obs = ephem.Observer()


   obs.lat = str(device_lat)
   obs.lon = str(device_lng)
   obs.elevation = float(device_alt)
   obs.date = hd_datetime 
   #print("AZ/RA DEBUG: ", device_lat, device_lng, device_alt, hd_datetime, az, el)
   #print("AZ2RA DATETIME:", hd_datetime)
   #print("AZ2RA LAT:", obs.lat)
   #print("AZ2RA LON:", obs.lon)
   #print("AZ2RA ELV:", obs.elevation)
   #print("AZ2RA DATE:", obs.date)
   #print("AZ2RA AZ,EL:", az,el)
   #print("AZ2RA RAD AZ,EL:", azr,elr)

   ra,dec = obs.radec_of(azr,elr)
   
   #print("AZ2RA RA,DEC:", ra,dec)

   return(ra,dec)


def XYtoRADec(img_x,img_y,cal_file,cal_params,json_conf):
   #print("CAL FILE IS : ", cal_file)
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cal_file)
   F_scale = 3600/float(cal_params['pixscale'])
   #F_scale = 24

   total_min = (int(hd_h) * 60) + int(hd_M)
   day_frac = total_min / 1440 
   hd_d = int(hd_d) + day_frac
   jd = date_to_jd(int(hd_y),int(hd_m),float(hd_d))

   lat = float(json_conf['site']['device_lat'])
   lon = float(json_conf['site']['device_lng'])

   # Calculate the reference hour angle
   T = (jd - 2451545.0)/36525.0
   Ho = (280.46061837 + 360.98564736629*(jd - 2451545.0) + 0.000387933*T**2 \
      - (T**3)/38710000.0)%360

   x_poly_fwd = cal_params['x_poly_fwd']
   y_poly_fwd = cal_params['y_poly_fwd']
   
   dec_d = float(cal_params['dec_center']) 
   RA_d = float(cal_params['ra_center']) 

   dec_d = dec_d + (x_poly_fwd[13] * 100)
   dec_d = dec_d + (y_poly_fwd[13] * 100)

   RA_d = RA_d + (x_poly_fwd[14] * 100)
   RA_d = RA_d + (y_poly_fwd[14] * 100)

   pos_angle_ref = float(cal_params['position_angle']) + (1000*x_poly_fwd[12]) + (1000*y_poly_fwd[12])

   # Convert declination to radians
   dec_rad = math.radians(dec_d)

   # Precalculate some parameters
   sl = math.sin(math.radians(lat))
   cl = math.cos(math.radians(lat))


   x_det = img_x - int(cal_params['imagew'])/2
   y_det = img_y - int(cal_params['imageh'])/2

   dx = (x_poly_fwd[0]
      + x_poly_fwd[1]*x_det
      + x_poly_fwd[2]*y_det
      + x_poly_fwd[3]*x_det**2
      + x_poly_fwd[4]*x_det*y_det
      + x_poly_fwd[5]*y_det**2
      + x_poly_fwd[6]*x_det**3
      + x_poly_fwd[7]*x_det**2*y_det
      + x_poly_fwd[8]*x_det*y_det**2
      + x_poly_fwd[9]*y_det**3
      + x_poly_fwd[10]*x_det*math.sqrt(x_det**2 + y_det**2)
      + x_poly_fwd[11]*y_det*math.sqrt(x_det**2 + y_det**2))

   # Add the distortion correction
   x_pix = x_det + dx 

   #print("ORIG X:", img_x)
   #print("X DET:", x_det)
   #print("DX :", dx)
   #print("NEWX :", x_pix)

   dy = (y_poly_fwd[0]
      + y_poly_fwd[1]*x_det
      + y_poly_fwd[2]*y_det
      + y_poly_fwd[3]*x_det**2
      + y_poly_fwd[4]*x_det*y_det
      + y_poly_fwd[5]*y_det**2
      + y_poly_fwd[6]*x_det**3
      + y_poly_fwd[7]*x_det**2*y_det
      + y_poly_fwd[8]*x_det*y_det**2
      + y_poly_fwd[9]*y_det**3
      + y_poly_fwd[10]*y_det*math.sqrt(x_det**2 + y_det**2)
      + y_poly_fwd[11]*x_det*math.sqrt(x_det**2 + y_det**2))

   # Add the distortion correction
   y_pix = y_det + dy 

   x_pix = x_pix / F_scale
   y_pix = y_pix / F_scale

   ### Convert gnomonic X, Y to alt, az ###

   # Caulucate the needed parameters
   radius = math.radians(math.sqrt(x_pix**2 + y_pix**2))
   theta = math.radians((90 - pos_angle_ref + math.degrees(math.atan2(y_pix, x_pix)))%360)

   sin_t = math.sin(dec_rad)*math.cos(radius) + math.cos(dec_rad)*math.sin(radius)*math.cos(theta)
   Dec0det = math.atan2(sin_t, math.sqrt(1 - sin_t**2))

   sin_t = math.sin(theta)*math.sin(radius)/math.cos(Dec0det)
   cos_t = (math.cos(radius) - math.sin(Dec0det)*math.sin(dec_rad))/(math.cos(Dec0det)*math.cos(dec_rad))
   RA0det = (RA_d - math.degrees(math.atan2(sin_t, cos_t)))%360

   h = math.radians(Ho + lon - RA0det)
   sh = math.sin(h)
   sd = math.sin(Dec0det)
   ch = math.cos(h)
   cd = math.cos(Dec0det)

   x = -ch*cd*sl + sd*cl
   y = -sh*cd
   z = ch*cd*cl + sd*sl

   r = math.sqrt(x**2 + y**2)

   # Calculate azimuth and altitude
   azimuth = math.degrees(math.atan2(y, x))%360
   altitude = math.degrees(math.atan2(z, r))



   ### Convert alt, az to RA, Dec ###

   # Never allow the altitude to be exactly 90 deg due to numerical issues
   if altitude == 90:
      altitude = 89.9999

   # Convert altitude and azimuth to radians
   az_rad = math.radians(azimuth)
   alt_rad = math.radians(altitude)

   saz = math.sin(az_rad)
   salt = math.sin(alt_rad)
   caz = math.cos(az_rad)
   calt = math.cos(alt_rad)

   x = -saz*calt
   y = -caz*sl*calt + salt*cl
   HA = math.degrees(math.atan2(x, y))

   # Calculate the hour angle
   T = (jd - 2451545.0)/36525.0
   hour_angle = (280.46061837 + 360.98564736629*(jd - 2451545.0) + 0.000387933*T**2 - T**3/38710000.0)%360

   RA = (hour_angle + lon - HA)%360
   dec = math.degrees(math.asin(sl*salt + cl*calt*caz))

   ### ###




   return(x_pix+img_x,y_pix+img_y,RA,dec,azimuth,altitude)


def reduce_fov_pos(this_poly, in_cal_params, cal_params_file, oimage, json_conf, paired_stars, min_run = 1, show=0):
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
   #pixscale = float(in_cal_params['pixscale']) + this_poly[3]


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
      if len(data) == 16:
         iname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist  = data
      if len(data) == 17:
         iname,mag,o_ra,o_dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist,star_int  = data


      #cv2.rectangle(image, (old_cat_x-5, old_cat_y-5), (old_cat_x + 5, old_cat_y + 5), (255), 1)
      #cv2.line(image, (six,siy), (old_cat_x,old_cat_y), (255), 1)
      #cv2.circle(image,(six,siy), 10, (255), 1)

   fov_poly = 0
   pos_poly = 0
   x_poly = in_cal_params['x_poly']
   y_poly = in_cal_params['y_poly']
   #print(in_cal_params['ra_center'], in_cal_params['dec_center'], in_cal_params['center_az'], in_cal_params['center_el'], in_cal_params['position_angle'], in_cal_params['pixscale'], this_poly)
   cat_stars = get_catalog_stars(in_cal_params)
   new_res = []
   new_paired_stars = []
   used = {}
   org_star_count = len(paired_stars)
   for cat_star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
      dname = name.decode("utf-8")
      for data in paired_stars:
         if len(data) == 16:
            iname,mag,o_ra,o_dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist  = data
         if len(data) == 17:
#dname == iname:
            iname,mag,o_ra,o_dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist,star_int  = data
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


   print("AVG RES:", avg_res, len(paired_stars), "/", org_star_count, new_az, new_el, ra_center, dec_center, position_angle)
   if show == 1:
      show_img = cv2.resize(image, (960,540))
      if "cam_id" in in_cal_params:
         cv2.imshow(cam_id, show_img)
      else:
         cv2.imshow('pepe', show_img)
      if min_run == 1:
         cv2.waitKey(1) 
      else:
         cv2.waitKey(1) 
   in_cal_params['position_angle'] = org_pos_angle
   if min_run == 1:
      return(avg_res)
   else:
      return(show_res)


def minimize_poly_params_fwd(cal_params_file, cal_params,json_conf,show=0):
   global tries
   tries = 0 
   #cv2.namedWindow('pepe')
   
   fit_img_file = cal_params_file.replace("-calparams.json", ".png")
   if cfe(fit_img_file) == 1:
      fit_img = cv2.imread(fit_img_file)
   else:
      fit_img = np.zeros((1080,1920),dtype=np.uint8)

   #if show == 1:
   #   cv2.namedWindow('pepe')
   x_poly_fwd = cal_params['x_poly_fwd'] 
   y_poly_fwd = cal_params['y_poly_fwd'] 
   x_poly = cal_params['x_poly'] 
   y_poly = cal_params['y_poly'] 

   close_stars = cal_params['cat_image_stars']
   # do x poly fwd

   x_poly_fwd = np.zeros(shape=(15,),dtype=np.float64)
   y_poly_fwd = np.zeros(shape=(15,),dtype=np.float64)
   x_poly = np.zeros(shape=(15,),dtype=np.float64)
   y_poly = np.zeros(shape=(15,),dtype=np.float64)



   # do x poly 
   field = 'x_poly'
   res = scipy.optimize.minimize(reduce_fit, x_poly, args=(field,cal_params,cal_params_file,fit_img,json_conf), method='Nelder-Mead')
   x_poly = res['x']
   x_fun = res['fun']
   cal_params['x_poly'] = x_poly.tolist()
   cal_params['x_fun'] = x_fun


   (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(cal_params_file)
   cal_params['cal_date'] = f_date_str

   cal_params['cat_image_stars'], res_px,res_deg = cat_star_report(cal_params['cat_image_stars'], 4)
   cal_params['total_res_px'] = res_px
   cal_params['total_res_deg'] = res_deg
   cal_params['cal_params_file'] = cal_params_file


   if res_px > 20:
      print("Something is bad here. Abort!")
      return(0, cal_params)
   #exit()
   # do y poly 
   field = 'y_poly'
   res = scipy.optimize.minimize(reduce_fit, y_poly, args=(field,cal_params,cal_params_file,fit_img,json_conf), method='Nelder-Mead')
   y_poly = res['x']
   y_fun = res['fun']
   cal_params['y_poly'] = y_poly.tolist()
   cal_params['y_fun'] = y_fun

   cal_params['cat_image_stars'], res_px,res_deg = cat_star_report(cal_params['cat_image_stars'], 2.5)

   # do x poly fwd
   field = 'x_poly_fwd'
   res = scipy.optimize.minimize(reduce_fit, x_poly_fwd, args=(field,cal_params,cal_params_file,fit_img,json_conf), method='Nelder-Mead')
   x_poly_fwd = res['x']
   x_fun_fwd = res['fun']
   cal_params['x_poly_fwd'] = x_poly_fwd.tolist()
   cal_params['x_fun_fwd'] = x_fun_fwd

   # do y poly fwd
   field = 'y_poly_fwd'
   res = scipy.optimize.minimize(reduce_fit, y_poly_fwd, args=(field,cal_params,cal_params_file,fit_img,json_conf), method='Nelder-Mead')
   y_poly_fwd = res['x']
   y_fun_fwd = res['fun']
   cal_params['y_poly_fwd'] = y_poly_fwd.tolist()
   cal_params['y_fun_fwd'] = y_fun_fwd


   print("BEFORE REPORT:", len( cal_params['cat_image_stars']))
   cal_params['cat_image_stars'], res_px,res_deg = cat_star_report(cal_params['cat_image_stars'], 2.5)
   print("AFTER REPORT:", len( cal_params['cat_image_stars']))


   print("POLY PARAMS")
   print("X_POLY", x_poly)
   print("Y_POLY", y_poly)
   print("X_POLY_FWD", x_poly_fwd)
   print("Y_POLY_FWD", y_poly_fwd)
   print("X_POLY FUN", x_fun)
   print("Y_POLY FUN", y_fun)
   print("X_POLY FWD FUN", x_fun_fwd)
   print("Y_POLY FWD FUN", y_fun_fwd)


   # FINAL RES & STARS UPDATE
   cal_params['cat_image_stars'], res_px,res_deg = cat_star_report(cal_params['cat_image_stars'], 4)
   cal_params['total_res_px'] = res_px
   cal_params['total_res_deg'] = res_deg


   #img_x = 960
   #img_y = 540
   #new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_params_file,cal_params,json_conf)
   #cal_params['center_az'] = img_az
   #cal_params['center_el'] = img_el
   save_json_file(cal_params_file, cal_params)
   return(1, cal_params)

def reduce_fit(this_poly,field, cal_params, cal_params_file, fit_img, json_conf, show=0):
   global tries
   pos_poly = 0 
   fov_poly = 0
   fit_img = np.zeros((1080,1920),dtype=np.uint8)
   fit_img = cv2.cvtColor(fit_img, cv2.COLOR_GRAY2RGB)
   this_fit_img = fit_img.copy()
   if field == 'x_poly':
      x_poly_fwd = cal_params['x_poly_fwd']
      y_poly_fwd = cal_params['y_poly_fwd']
      x_poly = this_poly
      cal_params['x_poly'] = x_poly
      y_poly = cal_params['y_poly']

   if field == 'y_poly':
      x_poly_fwd = cal_params['x_poly_fwd']
      y_poly_fwd = cal_params['y_poly_fwd']
      y_poly = this_poly
      cal_params['y_poly'] = y_poly
      x_poly = cal_params['x_poly']

   if field == 'x_poly_fwd':
      x_poly = cal_params['x_poly']
      y_poly = cal_params['y_poly']
      x_poly_fwd = this_poly
      cal_params['x_poly_fwd'] = x_poly_fwd
      y_poly_fwd = cal_params['y_poly_fwd']

   if field == 'y_poly_fwd':
      x_poly = cal_params['x_poly']
      y_poly = cal_params['y_poly']
      y_poly_fwd = this_poly
      cal_params['y_poly_fwd'] = y_poly_fwd
      x_poly_fwd = cal_params['x_poly_fwd']

   # loop over each pair of img/cat star and re-compute distortion with passed 'this poly', calc error distance and return avg distance for all pairs set
   total_res = 0
   total_res_fwd = 0
   ra_center = float(cal_params['ra_center'])
   dec_center = float(cal_params['dec_center'])

   for star in (cal_params['cat_image_stars']):
      if len(star) == 16:
         (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,px_dist ) = star
      if len(star) == 17:
         (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, px_dist, img_res ) = star
 
      if field == 'x_poly' or field == 'y_poly':
         new_cat_x, new_cat_y = distort_xy(0,0,ra,dec,float(cal_params['ra_center']), float(cal_params['dec_center']), x_poly, y_poly, float(cal_params['imagew']), float(cal_params['imageh']), float(cal_params['position_angle']),3600/float(cal_params['pixscale']))
         img_res = abs(calc_dist((six,siy),(new_cat_x,new_cat_y)))

         if img_res < 1:
            color = (255,0,0)
         elif 1 < img_res < 2:
            color = (0,255,0)
         elif 3 < img_res < 4:
            color = (255,255,0)
         elif 5 < img_res < 6:
            color = (0,165,255)
         else :
            color = (0,0,255)

         cv2.line(this_fit_img, (six,siy), (int(new_cat_x),int(new_cat_y)), color, 2)
      else:
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_params_file,cal_params,json_conf)
         new_cat_x, new_cat_y = distort_xy(0,0,img_ra,img_dec,float(cal_params['ra_center']), float(cal_params['dec_center']), x_poly, y_poly, float(cal_params['imagew']), float(cal_params['imageh']), float(cal_params['position_angle']),3600/float(cal_params['pixscale']))
         img_res = abs(angularSeparation(ra,dec,img_ra,img_dec))
         if img_res < .1:
            color = (255,0,0)
         elif .1 < img_res < .2:
            color = (0,255,0)
         elif .2 < img_res < .3:
            color = (255,255,0)
         elif .4 < img_res < .5:
            color = (0,165,255)
         else:
            color = (0,0,255)
         cv2.line(this_fit_img, (six,siy), (int(new_cat_x),int(new_cat_y)), color, 2)
         #img_res = abs(calc_dist((six,siy),(new_x,new_y)))

      #cv2.rectangle(this_fit_img, (int(new_x)-2, int(new_y)-2), (int(new_x) + 2, int(new_y) + 2), (128, 128, 128), 1)
      cv2.rectangle(this_fit_img, (int(new_cat_x)-2, int(new_cat_y)-2), (int(new_cat_x) + 2, int(new_cat_y) + 2), (128, 128, 128), 1)
      #cv2.rectangle(this_fit_img, (six-4, siy-4), (six+4, siy+4), (128, 128, 128), 1)
      cv2.circle(this_fit_img, (six,siy), 5, (128,128,128), 1)

      total_res = total_res + img_res
   #tries = tries + 1

   tries = 0
   total_stars = len(cal_params['cat_image_stars'])
   avg_res = total_res/total_stars

   movie =0
   show_img = cv2.resize(this_fit_img, (0,0),fx=.5, fy=.5)
   cn = str(tries)
   cnp = cn.zfill(10)
   desc = field + " res: " + str(img_res) 
   cv2.putText(this_fit_img, desc, (int(50), int(50)),cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 1)
   if movie == 1:
      if (field == 'xpoly' or field == 'ypoly'): 
         if img_res > 5:
            if tries % 1 == 0:
               cv2.imwrite("/mnt/ams2/fitmovies/fr" + str(cnp) + ".png", this_fit_img)
         else:
            if tries % 5 == 0:
               cv2.imwrite("/mnt/ams2/fitmovies/fr" + str(cnp) + ".png", this_fit_img)
      else: 
         if img_res > .3:
            if tries % 1 == 0:
               cv2.imwrite("/mnt/ams2/fitmovies/fr" + str(cnp) + ".png", this_fit_img)
         elif .08 < img_res < .3 :
            if tries % 5 == 0:
               cv2.imwrite("/mnt/ams2/fitmovies/fr" + str(cnp) + ".png", this_fit_img)
         else: 
            if tries % 1 == 0:
               cv2.imwrite("/mnt/ams2/fitmovies/fr" + str(cnp) + ".png", this_fit_img)
   if show == 1:
      cv2.imshow('pepe', show_img)
      cv2.waitKey(1)


   #print("Total Residual Error:", total_res )
   print("Avg Residual Error:", field, avg_res )
 
   return(avg_res)

def draw_star_image(image_file= None, image = None, cal_params=None, write=1) :
   if cal_params == None:
      cpfile = image_file.replace(".png", "-calparams.json")
      cal_params = load_json_file(cpfile)
   print("image:", image_file)
   if write == 1:
      star_file = image_file.replace(".png", "-stars.png")
   if image_file is not None: 
      img = Image.open(image_file)
   else:
      img = Image.fromarray(image)
   draw = ImageDraw.Draw(img)
   font = ImageFont.truetype(VIDEO_FONT, VIDEO_FONT_SMALL_SIZE) 

   c_dist = []
   m_dist = []
   if len(cal_params['cat_image_stars']) == 0:
      print("CAT IMAGE STARS 0!")
      exit()
   for star in cal_params['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      c_dist.append(cat_dist)
      m_dist.append(match_dist)
   med_c_dist = np.median(c_dist)
   med_m_dist = np.median(m_dist)

   for star in cal_params['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      print(dcname, match_dist - med_m_dist, cat_dist - med_c_dist)
      if cat_dist - med_c_dist < 20:
         draw.ellipse((six-5, siy-5, six+5, siy+5), outline ='blue')
         draw.rectangle([(new_cat_x-5,new_cat_y-5),(new_cat_x+5),(new_cat_y+5)], outline ="red") 
         draw.rectangle([(new_x-5,new_y-5),(new_x+5),(new_y+5)], outline ="green") 

         draw.text((six, siy), dcname, font=font)
   if write == 1:
      img.save(star_file)
      return(img)
   else:
      return(img)

def freecal_copy(cal_params_file, json_conf):
   cal_params = load_json_file(cal_params_file)
   user_stars = []
   for x,y,cp in cal_params['user_stars']:
      user_stars.append((x,y))
   
   cpf = cal_params_file.split("/")[-1]
   cprf = cpf.replace("-calparams.json", "")
   cpd = cal_params_file.replace(cpf, "")
   fc_dir = "/mnt/ams2/cal/freecal/" + cprf + "/" 
   if cfe(fc_dir, 1) == 0:
      os.makedirs(fc_dir)
   cmd = "cp " + cpd + cpf + " " + fc_dir + cprf + "-stacked-calparams.json"
   os.system(cmd)
   print(cmd)
   js = {}
   js['user_stars'] = user_stars


   save_json_file(fc_dir + cprf + "-user-stars.json", js)
   print("SAVED:", fc_dir + cprf + "-user-stars.json")

   cmd = "cp " + cpd + cprf + "-azgrid.png" + " " + fc_dir + cprf + "-azgrid.png"
   os.system(cmd)
   print(cmd)

   cmd = "cp " + cpd + cprf + ".png" + " " + fc_dir + cprf + "-stacked.png"
   os.system(cmd)
   print(cmd)

   img = cv2.imread(fc_dir + cprf + ".png")
   azimg = cv2.imread(fc_dir + cprf + "-azgrid.png")
   azhalf = cv2.resize(azimg, (960, 540))
   imghalf = cv2.resize(azimg, (960, 540))

   imgaz_blend = cv2.addWeighted(imghalf, 0.5, azhalf, 0.5, 0.0)

   cv2.imwrite(fc_dir + cprf + "-stacked-azgrid-half.png", azhalf)
   cv2.imwrite(fc_dir + cprf + "-stacked-azgrid-half-blend.png", imgaz_blend)
   cv2.imwrite(cpd + cprf + "-blend.png", imgaz_blend)


def remove_dupe_cat_stars(paired_stars):
   iused = {}
   cused = {}
   new_paired_stars = []
   for data in paired_stars:
      if len(data) == 16:
         iname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist  = data
      if len(data) == 17:
         iname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist,bp  = data
      if len(data) == 10:
         name,mag,ra,dec,new_cat_x,new_cat_y,six,siy,px_dist,cp_file = data
      used_key = str(six) + "." + str(siy)
      c_used_key = str(ra) + "." + str(dec)
      if used_key not in iused and c_used_key not in cused:
         new_paired_stars.append(data)
         iused[used_key] = 1
         cused[c_used_key] = 1
   return(new_paired_stars)

def AzEltoRADec(az,el,cal_file,cal_params,json_conf):
   azr = np.radians(az)
   elr = np.radians(el)
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cal_file)
   #hd_datetime = hd_y + "/" + hd_m + "/" + hd_d + " " + hd_h + ":" + hd_M + ":" + hd_s
   if "device_lat" in cal_params:
      device_lat = cal_params['device_lat']
      device_lng = cal_params['device_lng']
      device_alt = cal_params['device_alt']
   else:
      device_lat = json_conf['site']['device_lat']
      device_lng = json_conf['site']['device_lng']
      device_alt = json_conf['site']['device_alt']

   obs = ephem.Observer()


   obs.lat = str(device_lat)
   obs.lon = str(device_lng)
   obs.elevation = float(device_alt)
   obs.date = hd_datetime 
   #print("AZ/RA DEBUG: ", device_lat, device_lng, device_alt, hd_datetime, az, el)
   #print("AZ2RA DATETIME:", hd_datetime)
   #print("AZ2RA LAT:", obs.lat)
   #print("AZ2RA LON:", obs.lon)
   #print("AZ2RA ELV:", obs.elevation)
   #print("AZ2RA DATE:", obs.date)
   #print("AZ2RA AZ,EL:", az,el)
   #print("AZ2RA RAD AZ,EL:", azr,elr)

   ra,dec = obs.radec_of(azr,elr)
   
   #print("AZ2RA RA,DEC:", ra,dec)

   return(ra,dec)
