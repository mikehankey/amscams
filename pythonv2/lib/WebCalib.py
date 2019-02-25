import datetime
import json
import numpy as np
import cv2
import cgi
import time
import glob
import os
from lib.FileIO import get_proc_days, get_day_stats, get_day_files , load_json_file, get_trims_for_file, get_days, save_json_file, cfe
from lib.VideoLib import get_masks, convert_filename_to_date_cam, find_hd_file_new, load_video_frames
from lib.ImageLib import mask_frame,stack_frames, adjustLevels, upscale_to_hd
from lib.CalibLib import radec_to_azel, clean_star_bg, get_catalog_stars, find_close_stars, XYtoRADec
from lib.UtilLib import check_running, calc_dist, angularSeparation

def check_solve_status(json_conf,form):
   hd_stack_file = form.getvalue("hd_stack_file")

   debug = "DEBUG: "
   if "-stacked.png" in hd_stack_file:
      # CASE 1
      debug = debug + "case=1;"
      solved_file = hd_stack_file.replace(".png", ".solved")
      grid_file = solved_file.replace(".solved", "-grid.png")
   
   #solved_file = grid_file

   #print(solved_file)
   running = check_running("solve-field")
   status = ""
   if running > 0:
      status = "running"
   elif running == 0 and cfe(solved_file) == 1:
      status = "success" 
   elif running == 0 and cfe(solved_file) == 0:
      status = "failed"
   #status = solved_file 
   debug = debug + " hd_stack_file=" + hd_stack_file + ";" + "solved_file=" + solved_file + ";" + "status=" + status
   
   if cfe(grid_file) == 1:
      tmp_img = cv2.imread(grid_file)
      tmp_img_tn = cv2.resize(tmp_img, (0,0),fx=.5, fy=.5)
      grid_file_half = grid_file.replace(".png", "-half.png")
      cv2.imwrite(grid_file_half, tmp_img_tn)
   else:
      grid_file_half = ""

   response = """
   {
      "status": """ + "\"" + status + "\"," + """ 
      "grid_file": """ + "\"" + grid_file_half + "\"," + """ 
      "solved_file": """ + "\"" + solved_file + "\"," + """ 
      "debug": """ + "\"" + debug + "\"" + """ 
   }
   """

   print(response)



def solve_field(json_conf, form):

   hd_stack_file = form.getvalue("hd_stack_file")
   fn,tdir = get_hd_filenames(hd_stack_file)
   plate_file = hd_stack_file.replace("-stacked.png", "-stacked.jpg")

   ff_plate_file = plate_file.replace("-stacked-an.png", "-stacked-4f.jpg")


   running = check_running("solve-field")
   status = ""
   if running > 0:
      status = "running"
   else:
      cmd = "cd /home/ams/amscams/pythonv2; ./plateSolve.py " + plate_file + " > /mnt/ams2/tmp/plt.txt 2>&1 &"
      #print(cmd)
      # exit()
      os.system(cmd)

   #plate_solve("/mnt/ams2/cal/tmp/" + new_fn, json_conf)
   status = "running" + ff_plate_file
   debug = "DEBUG: hd_stack_file" + hd_stack_file + "; cmd =" + cmd + "; status = " + status
   response = """
   {
      "status": """ + "\"" + status + "\"," + """ 
      "debug": """ + "\"" + debug + "\"" + """ 
   }
   """
   print(response)


def cnt_max_px(cnt_img):
   cnt_img = cv2.GaussianBlur(cnt_img, (7, 7), 0)
   min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)

   return(max_loc, min_val, max_val)

def make_plate_from_points(json_conf, form):
   hd_stack_file = form.getvalue("hd_stack_file")
   #print(hd_stack_file)
   hd_stack_img = cv2.imread(hd_stack_file,0)
   #print(hd_stack_img)
   shp = hd_stack_img.shape
   ih,iw = shp[0],shp[1]
   sd = 0
   if iw < 1920:
      sd = 1
   
   hdm_x = 2.7272
   hdm_y = 1.875

  
   plate_img = np.zeros((ih,iw),dtype=np.uint8)
   hd_stack_file_an = hd_stack_file.replace(".png", "-an.png")
   half_stack_file_an = hd_stack_file.replace("-stacked.png", "-half-stack-an.png")
   #print(half_stack_file_an)
   pin = form.getvalue("points")
   points = []
   temps = pin.split("|")
   for temp in temps:
      if len(temp) > 0:
         (x,y) = temp.split(",")
         x,y = int(float(x)),int(float(y))
         x,y = int(x)+5,int(y)+5
         x,y = x*2,y*2
         points.append((x,y))
     
   plate_image_4f = np.zeros((ih,iw),dtype=np.uint8)


   hd_stack_img = cv2.imread(hd_stack_file,0);
   hd_stack_img_an = hd_stack_img.copy()
   star_points = []
   for x,y in points:
      x,y = int(x),int(y)
      #cv2.circle(hd_stack_img_an, (int(x),int(y)), 5, (128,128,128), 1)
      y1 = y - 15
      y2 = y + 15
      x1 = x - 15
      x2 = x + 15
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
      if ch > 0 and cw > 0:
         cnt_img = hd_stack_img[cy1:cy2,cx1:cx2]
         bgavg = np.mean(cnt_img)
         cnt_img = clean_star_bg(cnt_img, bgavg + 3)

      #cv2.rectangle(hd_stack_img_an, (x1,y1), (x2,y2), (90, 90, 90), 1)
         cv2.rectangle(hd_stack_img_an, (x+mx-5-15, y+my-5-15), (x+mx+5-15, y+my+5-15), (128, 128, 128), 1)
         cv2.rectangle(hd_stack_img_an, (x+mx-15-15, y+my-15-15), (x+mx+15-15, y+my+15-15), (128, 128, 128), 1)
         star_points.append([x+mx,y+my])
         if abs(cy1- (ih/2)) <= (ih/2)*.8 and abs(cx1- (iw/2)) <= (iw/2)*.8:
            plate_image_4f[cy1:cy2,cx1:cx2] = cnt_img 
            plate_img[cy1:cy2,cx1:cx2] = cnt_img
         else:
            plate_image_4f[cy1:cy2,cx1:cx2] = cnt_img 

   points_json = {}
   points_json['user_stars'] = star_points
   if sd == 1:
      temp_stars = []
      for x,y in star_points:
         x = x * hdm_x
         y = y * hdm_y
         temp.appen((x,y))
      points_json['user_stars'] = temp
      star_points = temp
   points_file = hd_stack_file.replace("-stacked.png", "-user-stars.json")
   save_json_file(points_file,points_json)


   #cv2.imwrite(hd_stack_file_an, hd_stack_img_an)
   ff_file = hd_stack_file_an.replace("-an.png", "-4f.jpg")
   cal_file = hd_stack_file_an.replace("-an.png", ".jpg")
   #print("FF:", ff_file)
   if iw != 1920 and ih != 1080:
      plate_img = cv2.resize(plate_img, (1920,1080))
      plate_image_4f = cv2.resize(plate_image_4f, (1920,1080))
      hd_stack_img_an = cv2.resize(hd_stack_img_an, (1920,1080))
   
   
   
   half_stack_img_an = cv2.resize(hd_stack_img_an, (0,0),fx=.5, fy=.5)
   half_stack_plate = cv2.resize(plate_img, (0,0),fx=.5, fy=.5)

   cv2.imwrite(cal_file, plate_img)
   cv2.imwrite(hd_stack_file_an, plate_img)
   cv2.imwrite(ff_file, plate_image_4f)
   #cv2.imwrite(half_stack_file_an, half_stack_img_an)
   cv2.imwrite(half_stack_file_an, half_stack_plate)


   response = """
   {
      "hd_stack_file_an": """ + "\"" + hd_stack_file_an + "\"," + """ 
      "half_stack_file_an": """ + "\"" + half_stack_file_an + "\"," + """
      "stars": """ + "" + str(star_points) + "" + """ 
   }
   """
   print(response)

def get_sd_filenames(sd_video_file):
   el = sd_video_file.split("/")
   fn = el[-1]
   tdir = sd_video_file.replace(fn, "")
   sd_img_dir = tdir + "images/"
   sd_stack = sd_img_dir + fn.replace(".mp4", "-stacked.png")
   return(sd_stack)

def get_hd_filenames(hd_video_file):
   el = hd_video_file.split("/")
   fn = el[-1]
   tdir = hd_video_file.replace(fn, "")
   return(fn,tdir)

def better_parse_file_date(input_file):
   el = input_file.split("/")
   fn = el[-1]
   ddd = fn.split("_")
   Y = ddd[0]
   M = ddd[1]
   D = ddd[2]
   H = ddd[3]
   MM = ddd[4]
   S = ddd[5]
   MS = ddd[6]
   CAM = ddd[7]
   extra = CAM.split("-")
   cam_id = extra[0]
   cam_id = cam_id.replace(".mp4", "")
   f_date_str = Y + "-" + M + "-" + D + " " + H + ":" + MM + ":" + S
   f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
   return(f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S)

def upscale_2HD(json_conf,form):
   hdm_x = 2.7272
   hdm_y = 1.875
   hd_stack_file = form.getvalue("hd_stack_file")
   half_stack_file = hd_stack_file.replace("-stacked.png", "-half-stack.png")
   points = form.getvalue("points")
   star_points = []
   temps = points.split("|")
   for temp in temps:
      if len(temp) > 0:
         (x,y) = temp.split(",")
         x,y = int(float(x)),int(float(y))
         x,y = int(x)+5,int(y)+5
         x,y = x,y
         star_points.append((x,y))
   points = star_points
   star_points = []

   for temp in points:
      if len(temp) > 0:
         (x,y) = temp
         x,y = int(float(x)),int(float(y))
         #x,y = int(x)+5,int(y)+5
         x,y = x*hdm_x,y*hdm_y
         star_points.append((x,y))

   user_stars = {}
   user_stars['user_stars'] = star_points

   stack_img = cv2.imread(half_stack_file,0)

   hd_image,plate_image,plate_image_4f,star_points = upscale_to_hd(stack_img, points)
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(hd_stack_file)
   base_dir = "/mnt/ams2/cal/freecal/" + Y + "_" + M + "_" + D + "_" + H + "_" + MM + "_" + S + "_" + "000" + "_" + cam_id
   base_file = Y + "_" + M + "_" + D + "_" + H + "_" + MM + "_" + S + "_" + "000" + "_" + cam_id
   if cfe(base_dir, 1) != 1:
      os.system("mkdir " + base_dir)
   stack_file = base_dir + "/" + base_file + "-stacked.png"
   orig_file = base_dir + "/" + base_file + "-orig.png"
   half_stack_file = base_dir + "/" + base_file + "-half-stack.png"
   plate_file = base_dir + "/" + base_file + ".jpg"
   plate_file_4f = base_dir + "/" + base_file + "-4f.jpg"

   user_star_file = stack_file.replace("-stacked.png", "-user-stars.json")
   save_json_file(user_star_file, user_stars)

   cv2.imwrite(plate_file, plate_image)
   cv2.imwrite(plate_file_4f, plate_image_4f)
   cv2.imwrite(stack_file, hd_image)
   half_stack_img = cv2.resize(hd_image, (960, 540))

   cv2.imwrite(half_stack_file, half_stack_img)
   status = "ok" 
   debug = ""
   response = """
   {
      "status": """ + "\"" + status + "\"," + """ 
      "hd_stack_file": """ + "\"" + stack_file + "\"," + """ 
      "debug": """ + "\"" + debug + "\"" + """ 
   }
   """
   print(response)

def choose_file(json_conf,form):
   input_file = form.getvalue("input_file")
   hd_file, hd_trim,time_diff_sec, dur = find_hd_file_new(input_file, 250, 10, 0)   
   if hd_file is None:
      sd_pic_stars(json_conf,form)
   else:
      print("<a href=webUI.py?cmd=free_cal&input_file=" + hd_file + "></a>HD File found. Stacking frames. Please wait... </a>") 
      print("<script>window.location.href='webUI.py?cmd=free_cal&input_file=" + hd_file + "';</script>")

def sd_pic_stars(json_conf,form):
   print("<h1>Calibrate SD Image Step #1 - Pick Stars</h1>")
   input_file = form.getvalue("input_file")
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(input_file)
   base_dir = "/mnt/ams2/cal/freecal/" + Y + "_" + M + "_" + D + "_" + H + "_" + MM + "_" + S + "_" + "000" + "_" + cam_id
   base_file = Y + "_" + M + "_" + D + "_" + H + "_" + MM + "_" + S + "_" + "000" + "_" + cam_id
   if cfe(base_dir, 1) != 1:
      os.system("mkdir " + base_dir)
   stack_file = base_dir + "/" + base_file + "-stacked.png"
   half_stack_file = base_dir + "/" + base_file + "-half-stack.png"
   orig_file = base_dir + "/" + base_file + "-orig.png"

   if "mp4" in input_file:
      frames = load_video_frames(input_file, json_conf, 200)
      tmp_file, stack_img = stack_frames(frames, input_file, 1)
      half_stack_img = stack_img 
      shp = half_stack_img.shape
      sh,sw = shp[0], shp[1]
      stack_img = cv2.resize(stack_img, (sw*2, sh*2))
      #half_stack_file = input_file.replace(".mp4", "-half-stack.png") 
      #stack_file = input_file.replace(".mp4", "-stacked.png") 
      print(stack_file,half_stack_file)
      cv2.imwrite(stack_file, stack_img)
      cv2.imwrite(half_stack_file, half_stack_img)
   else:
      stack_file = input_file
      stack_img = cv2.imread(input_file)


   js_html = """

   <script>
      var my_image = '""" + half_stack_file + """'
      var hd_stack_file = '""" + stack_file + """'
      var stars = []
   </script>


   """.format(stack_file)
   canvas_html = """
      <p>An HD source file was not found for this time period. No worries, we can still calibrate from an SD image, but first we need to pick the stars so we can upscale the image. Select as many stars as possible from the image below and then click the "Upscale To HD" button.</p>
      <div style="float:left"><canvas id="c" width="960" height="540" style="border:2px solid #000000;"></canvas></div>
      <div style="float:left"><div style="position: relative; height: 50px; width: 50px" id="myresult" class="img-zoom-result"> </div></div>
      <div style="clear: both"></div>
   """

   canvas_html = canvas_html + """
      <div id=info_panel>Info: </div>
      <div id=star_panel>Stars: </div>
      <div id=action_buttons>
         <input type=button id="button1" value="Upscale To HD" onclick="javascript:upscale_HD('""" + stack_file + """')">
      </div>
      <div id=star_list>star_list: </div>
       <BR><BR>
   """
   print(stack_file)

   print(canvas_html)
   print(js_html)



def free_cal(json_conf,form):
   input_file = form.getvalue("input_file")
   # if no input file is specified ask for one. 
   if input_file is None :
      print("enter the path and filename to the image or video you want to calibrate:")
      print("<form>")
      print("<input type=hidden name=cmd value=free_cal>")
      print("<input type=text size=50 name=input_file value=\"\">")
      print("<input type=submit value=\"Continue\">")
      print("</form>")
      return()

   # test the input file, stack if video, check size and re-size, make half-stack, copy to work dir

   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(input_file)
   base_dir = "/mnt/ams2/cal/freecal/" + Y + "_" + M + "_" + D + "_" + H + "_" + MM + "_" + S + "_" + "000" + "_" + cam_id
   base_file = Y + "_" + M + "_" + D + "_" + H + "_" + MM + "_" + S + "_" + "000" + "_" + cam_id
   if cfe(base_dir, 1) != 1:
      os.system("mkdir " + base_dir)

   #video or image
   if "mp4" in input_file:
      frames = load_video_frames(input_file, json_conf, 100)
      stack_file, stack_img = stack_frames(frames, input_file, 1)
      input_file = input_file.replace(".mp4", ".png") 
   else:
      stack_file = input_file
      stack_img = cv2.imread(input_file)

   sfs = stack_img.shape
   sh,sw = sfs[0],sfs[1]


   if sw != 1920:
      #print(input_file, sh,sw)
      #stack_img = adjustLevels(stack_img, 5,.98,255)
      half_stack_img = stack_img 
      stack_img = cv2.resize(stack_img, (sw*2, sh*2))
      sfs = stack_img.shape
      sh,sw = sfs[0],sfs[1]
   else:
      half_stack_img = cv2.resize(stack_img, (0,0),fx=.5, fy=.5)

   iw = int(sw/2)
   ih = int(sh/2)

   half_stack_file = base_dir + "/" + base_file + "-half-stack.png"
   stack_file = base_dir + "/" + base_file + "-stacked.png"


   cv2.imwrite(half_stack_file, half_stack_img)
   cv2.imwrite(stack_file, stack_img)


   user_stars_file = stack_file.replace("-stacked.png", "-user-stars.json")
   az_grid_file = stack_file.replace(".png", "-azgrid-half.png")
   az_grid_blend = stack_file.replace(".png", "-azgrid-half-blend.png")


   if cfe(user_stars_file) == 1:
      user_stars = load_json_file(user_stars_file)
      extra_js = """
         <script>
         """
      extra_js = extra_js + "var stars = ["

      c = 0
      for sx,sy in user_stars['user_stars']:
         if c > 0:
            extra_js = extra_js + ","
         extra_js=extra_js+ "[" + str(sx) + "," +str(sy) +"]" 
         c = c + 1
      extra_js = extra_js + "]"
      extra_js = extra_js + """
         </script>
   """
   else:
      extra_js = "<script>var stars = []</script>"

   js_html = """
   <script>
      var my_image = '""" + half_stack_file + """'
      var hd_stack_file = '""" + stack_file + """'
   </script>
   """.format(stack_file)
   canvas_html = """
      <div style="float:left"><canvas id="c" width="960" height="540" style="border:2px solid #000000;"></canvas></div>
      <div style="float:left"><div style="position: relative; height: 50px; width: 50px" id="myresult" class="img-zoom-result"> </div></div>
      <div style="clear: both"></div>
   """

   canvas_html = canvas_html + """
      <div id=info_panel>Info: </div>
      <div id=star_panel>Stars: </div>
      <div id=action_buttons>
         <input type=button id="button1" value="Show Image" onclick="javascript:show_image('""" + stack_file + """')">
         <input type=button id="button1" value="Make Plate" onclick="javascript:make_plate('""" + stack_file + """')">
         <input type=button id="button1" value="Solve Field" onclick="javascript:solve_field('""" + stack_file + """')">
         <input type=button id="button1" value="Show Catalog Stars" onclick="javascript:show_cat_stars('""" + stack_file + """')">
         <input type=button id="button1" value="Fit Field" onclick="javascript:fit_field('""" + stack_file + """')">
         <input type=button id="button1" value="AZ Grid" onclick="javascript:az_grid('""" + az_grid_blend + """')">
      </div>
      <div id=star_list>star_list: </div>
       <BR><BR>
   """
   print(stack_file)

   print(canvas_html)
   print(extra_js)
   print(js_html)
   #print("<script src=\"/js/freecal-canvas.js\"></script>")
   #print("<script src=\"/js/freecal-ajax.js\"></script>")



def default_cal_params(cal_params,json_conf):
   if 'fov_poly' not in cal_params:
      fov_poly = [0,0]
      cal_params['fov_poly'] = fov_poly
   if 'pos_poly' not in cal_params:
      pos_poly = [0]
      cal_params['pos_poly'] = pos_poly
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


def show_cat_stars(json_conf,form):
   hd_stack_file = form.getvalue("hd_stack_file")
   cal_params_file = hd_stack_file.replace(".png", "-calparams.json")
   user_star_file = hd_stack_file.replace("-stacked.png", "-user-stars.json")
   cal_params = load_json_file(cal_params_file)
   user_stars = load_json_file(user_star_file)
   cal_params = default_cal_params(cal_params,json_conf)

   cat_stars = get_catalog_stars(cal_params['fov_poly'], cal_params['pos_poly'], cal_params,"x",cal_params['x_poly'],cal_params['y_poly'],min=0)
   my_cat_stars = []
   my_close_stars = []


   for name,mag,ra,dec,new_cat_x,new_cat_y in cat_stars :
      dcname = str(name.decode("utf-8"))
      dbname = dcname.encode("utf-8")
      my_cat_stars.append((dcname,mag,ra,dec,new_cat_x,new_cat_y))
   cal_params['cat_stars'] = my_cat_stars
   cal_params['user_stars'] = user_stars['user_stars']
   for ix,iy in user_stars['user_stars']:
   #   print(ix,iy)
      close_stars = find_close_stars((ix,iy), cat_stars) 
      for name,mag,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist in close_stars:
         dcname = str(name.decode("utf-8"))
         dbname = dcname.encode("utf-8")
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(ix,iy,cal_params_file,cal_params,json_conf)
         match_dist = abs(angularSeparation(ra,dec,img_ra,img_dec))
         my_close_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist))


      #print(close_stars,"<BR>")
   #   print(close_stars, "<BR>")

   cal_params['close_stars'] = my_close_stars
   #out = str(cal_params)
   #out = out.replace("'", "\"")
   #out = out.replace("(b", "(")
   save_json_file(cal_params_file, cal_params) 
   print(json.dumps(cal_params))

def calibrate_pic(json_conf,form):
   hdm_x = 2.7272
   hdm_y = 1.875
   sd_video_file = form.getvalue("sd_video_file")
   hd_file = None
   override = form.getvalue("override") 


   if override is not None:
      if "mp4" in override:
         sd_video_file = override
         print("OVERRIDE VIDEO", sd_video_file)
         override = None

   if sd_video_file is None and override is None:
      print("enter the path and filename to the image or video you want to calibrate:")
      print("<form>")
      print("<input type=hidden name=cmd value=calibrate_pic>")
      print("<input type=text size=50 name=override value=\"\">")
      print("<input type=submit value=\"Continue\">")
      print("</form>")
      return()


   if override is None or override == "":
      print("looking for HD file.")
      sd_stack_file = get_sd_filenames(sd_video_file)
      stack_img = cv2.imread(sd_stack_file,0)
      ih,iw = stack_img.shape
      hd_file, hd_trim,time_diff_sec, dur = find_hd_file_new(sd_video_file, 250, 10, 0)   
      print(hd_file, hd_trim)
   if hd_file is None and override is None:
      print("NO HD FILE FOUND. Using SD image instead.")
      # no HD file exists..
 
      hd_stack_img = cv2.resize(stack_img, (1920,1080))
      half_stack_img = cv2.resize(hd_stack_img, (0,0),fx=.5, fy=.5)
      sd_stack_file = sd_stack_file.replace("_000_", "_007_")
      half_stack_file = sd_stack_file.replace("-stacked.png", "half-stack.png")
      hd_stack_file = sd_stack_file.replace("-stacked.png", "-stacked.png")
      override = hd_stack_file 
      cv2.imwrite(half_stack_file, half_stack_img)
      cv2.imwrite(hd_stack_file, hd_stack_img)

   if override is None or override == "":
      #print(hd_file,"<BR>")
      hd_stack_file = hd_file.replace(".mp4", "-stacked.png")
      half_stack_file = hd_file.replace(".mp4", "-half-stack.png")
      if cfe(hd_stack_file) == 0: 
         frames = load_video_frames(hd_file, json_conf, 20)
         hd_stack_file, hd_stack_img = stack_frames(frames, hd_file)
         half_stack_img = cv2.resize(hd_stack_img, (0,0),fx=.5, fy=.5)
         cv2.imwrite(half_stack_file, half_stack_img)
         ih,iw = half_stack_img.shape
         #print("HD FILE Exists :", half_stack_file) 
      else:
         half_stack_img = cv2.imread(half_stack_file,0)
         ih,iw = half_stack_img.shape

   if override is not None:
      sd_stack_file = override
      stack_img = cv2.imread(sd_stack_file,0)

      hd_stack_img = cv2.resize(stack_img, (1920,1080))
      half_stack_img = cv2.resize(hd_stack_img, (0,0),fx=.5, fy=.5)
      sd_stack_file = sd_stack_file.replace("_000_", "_007_")
      if "stacked" in sd_stack_file:
         half_stack_file = sd_stack_file.replace("-stacked.png", "-half-stack.png")
         hd_stack_file = sd_stack_file.replace("-stacked.png", "-stacked.png")
      if "jpg" in sd_stack_file:
         half_stack_file = sd_stack_file.replace(".jpg", "half-stack.jpg")
         hd_stack_file = sd_stack_file 
      override = hd_stack_file 
      print("HALF:", half_stack_file)
      cv2.imwrite(half_stack_file, half_stack_img)
      cv2.imwrite(hd_stack_file, hd_stack_img)

      print(hd_stack_file)
      #hd_stack_img = cv2.imread(hd_stack_file, 0)



      #half_stack_file = hd_stack_file.replace("-stacked.png", "-half-stack.png")
      #half_stack_img = cv2.resize(hd_stack_img, (0,0),fx=.5, fy=.5)
      #cv2.imwrite(half_stack_file, half_stack_img)



      ih,iw = half_stack_img.shape

   canvas_js = """
      <script>

      var hd_stack_file = '""" + hd_stack_file + """'
      var waiting = false

      function sleep (time) {
         return new Promise((resolve) => setTimeout(resolve, time));
      }

      function solve_field(hd_stack_file) {
         check_solve_status(1)
      }

      function send_ajax_solve() { 
         ajax_url = "/pycgi/webUI.py?cmd=solve_field&hd_stack_file=" + hd_stack_file 
         alert(ajax_url)
         $.get(ajax_url, function(data) {
            $(".result").html(data);
            var json_resp = $.parseJSON(data);
            alert(json_resp['debug'])
            sleep(5000).then(() => {
               alert("time to wake up!")
               check_solve_status(0)
            });
         });
      }

      function check_solve_status(then_run) {
         ajax_url = "/pycgi/webUI.py?cmd=check_solve_status&hd_stack_file=" + hd_stack_file 
         alert(ajax_url)
         waiting = true
         $.get(ajax_url, function(data) {
            $(".result").html(data);
            var json_resp = $.parseJSON(data);
            waiting = false
            alert(json_resp['debug']) 
            if (json_resp['status'] == 'failed' && then_run == 1) {
               send_ajax_solve()
            }
            if (json_resp['status'] == 'running' && then_run == 0) {
               alert("still running")
            }
            if (json_resp['status'] == 'success' && then_run == 0) {
               alert("solved")
            }
            if (json_resp['status'] == 'success' && then_run == 1) {
               grid_img = json_resp['grid_file']
               canvas.setBackgroundImage(grid_img, canvas.renderAll.bind(canvas));
               alert("GRID IMAGE:" + grid_img)
               alert(json_resp['debug'])
            }
            if (json_resp['status'] == 'failed' && then_run == 0) {
               alert(json_resp['solved_file'])
               alert("failed")
            }
         });
      }

      function make_plate(img_url) {
         var point_str = ""
         for (i in user_stars) {
            point_str = point_str + user_stars[i].toString()  + "|"
         }

         var point_str = ""
         var objects = canvas.getObjects('circle')
         for (let i in objects) {
            x = objects[i].left
            y = objects[i].top
            point_str = point_str + x.toString() + "," + y.toString() + "|"
         }

         ajax_url = "/pycgi/webUI.py?cmd=make_plate_from_points&hd_stack_file=" + hd_stack_file + "&points=" + point_str 
         alert(ajax_url)
 
         $.get(ajax_url, function(data) {
            $(".result").html(data);
            var json_resp = $.parseJSON(data);
            alert(json_resp['half_stack_file_an']) 
            var new_img = json_resp['half_stack_file_an'] + "?r=" + Math.random().toString()
            var stars = json_resp['stars'];

            for (let s in stars) {
              
              cx = stars[s][0] - 11 
              cy = stars[s][1] - 11

              var circle = new fabric.Circle({
                 radius: 5, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(100,200,200,.5)', left: cx/2, top: cy/2,
                 selectable: false
              });
              canvas.add(circle);

            }            

            alert(stars)
            canvas.setBackgroundImage(new_img, canvas.renderAll.bind(canvas));
            // remove existing objects & replace with pin pointed stars
            for (let i in objects) {
               canvas.remove(objects[i]);
            }


            //alert(json_resp.error)
            //alert(data)
         });


      }


      var canvas = new fabric.Canvas('c', {
         hoverCursor: 'default', 
         selection: true 
      });
      var my_image = " """ + half_stack_file + """"
      var user_stars = []

      canvas.setBackgroundImage(my_image, canvas.renderAll.bind(canvas));

      canvas.on('mouse:move', function(e) {
         var pointer = canvas.getPointer(event.e);
         x_val = pointer.x | 0;
         y_val = pointer.y | 0;
         cx = 2
         cy = 2
         document.getElementById('info_panel').innerHTML = x_val.toString() + " , " + y_val.toString()
         myresult = document.getElementById('myresult')
         myresult.style.backgroundImage = "url('" + hd_stack_file + "')";
         myresult.style.backgroundPosition = "-" + ((x_val*cx)-75) + "px -" + ((y_val * cy)-75)  + "px" 
      });

      canvas.on('mouse:down', function(e) {
         var pointer = canvas.getPointer(event.e);
         x_val = pointer.x | 0;
         y_val = pointer.y | 0;
         user_stars.push([x_val,y_val])

         var circle = new fabric.Circle({
            radius: 5, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(100,200,200,.5)', left: x_val-5, top: y_val-5,
            selectable: false
         });

         var objFound = false
         var clickPoint = new fabric.Point(x_val,y_val);

         //canvas.forEachObject(function (obj) {
         var objects = canvas.getObjects('circle')
         for (let i in objects) {
            if (!objFound && objects[i].containsPoint(clickPoint)) {
               objFound = true
               canvas.remove(objects[i]);
            }
         }
         if (objFound == false) {
            canvas.add(circle);
         }


         document.getElementById('info_panel').innerHTML = "star added"
         document.getElementById('star_panel').innerHTML = "Total Stars: " + user_stars.length;
      });

      </script>
   """


   canvas_html = """
      <div style="float:left"><canvas id="c" width="{:d}" height="{:d} style="border:2px solid #000000;"></canvas></div><div style="float:left"><div style="position: relative; height: 150px; width: 150px" id="myresult" class="img-zoom-result"> </div></div><div style="clear: both"></div>
   """.format(iw,ih)

   canvas_html = canvas_html + """ 
      <div id=info_panel>Info: </div>
      <div id=star_panel>Stars: </div>
      <div id=action_buttons>
         <input type=button id="button1" value="Make Plate" onclick="javascript:make_plate('""" + hd_stack_file + """')"> 
         <input type=button id="button1" value="Find Stars"> 
         <input type=button id="button1" value="Solve Field" onclick="javascript:solve_field('""" + hd_stack_file + """')"> 
         <input type=button id="button1" value="Fit Field" onclick="javascript:fit_field('""" + hd_stack_file + """')"> 
      </div>
       <BR><BR>
   """

   print(canvas_html)
   print(canvas_js)

def div_table_vars():

   start_table = """
      <div class="divTable" style="border: 1px solid #000;" >
      <div class="divTableBody">
   """
   start_row = """
      <div class="divTableRow">
   """
   start_cell = """
      <div class="divTableCell">
   """
   end_table = "</div></div>"
   end_row = "</div>"
   end_cell= "</div>"
   return(start_table, start_row, start_cell, end_table, end_row, end_cell)

