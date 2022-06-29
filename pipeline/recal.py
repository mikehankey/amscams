"""

2022 - recalibration script -- fixes / updates calibration

import features / functions
   - get / validate image stars (no catalog)
   - blind solve
   - get catalog stars
   - pair stars (image stars with catalog stars)
   - create lens distorition model from one image
   - create lens distorition model from multiple images
   - apply lens correction model
   - refit / refine fov pointing values (ra/dec/pos/pix)

"""
from PIL import ImageFont, ImageDraw, Image, ImageChops
import time
import json
import numpy as np
import glob
import cv2
import os, sys
import requests
from photutils import CircularAperture, CircularAnnulus
from photutils.aperture import aperture_photometry
import scipy.optimize

import lib.brightstardata as bsd
from lib.PipeUtil import load_json_file, save_json_file,angularSeparation, calc_dist, convert_filename_to_date_cam 
from lib.PipeAutoCal import distort_xy, insert_calib, minimize_poly_multi_star, view_calib, cat_star_report , update_center_radec, XYtoRADec, draw_star_image
import sqlite3 
from lib.DEFAULTS import *
tries = 0


def make_grid_stars(merged_stars, mpc = None, factor = 2, gsize=50, limit=3):
   merged_stars = sorted(merged_stars, key=lambda x: x[-2], reverse=False)
   if mpc is None:
      print("FIRST TIME CAL!")
      gsize = 80
      factor = 2
      max_dist = 35
   else:
      print("MULTI-X CAL!", mpc['cal_version'])
      if mpc['cal_version'] < 3:
         gsize= 100
         factor = 2
         max_dist = 5
      else:
         gsize= 100
         factor = 1
         max_dist = 5

   all_res = [row[-2] for row in merged_stars]
   res1 = []
   res2 = []
   for star in merged_stars:
      (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star
      center_dist = calc_dist((six,siy), (1920/2, 1080/2))
      cat_dist = calc_dist((six,siy), (new_cat_x,new_cat_y))
      if center_dist < 800:
         res1.append(cat_dist)
      else:
         res2.append(cat_dist)

   med_res = np.mean(all_res) ** 2
   med_res1 = np.mean(res1) ** factor
   med_res2 = np.mean(res2) ** factor
   if med_res1 > max_dist:
      med_res1 = max_dist
   if med_res2 > max_dist:
      med_res2 = max_dist

   qual_stars = []
   grid = {}
   for w in range(0,1920):
      for h in range(0,1080):
         if (w == 0 and h == 0) or (w % gsize == 0 and h % gsize == 0):
            x1 = w
            x2 = w + gsize
            y1 = h
            y2 = h + gsize
            if x2 > 1920:
               x2 = 1920
            if y2 > 1080:
               y2 = 1080
            grid_key = str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2)

            if grid_key not in grid:
               grid[grid_key] = [] 

            for star in merged_stars:
               (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star
               cat_dist = calc_dist((six,siy), (new_cat_x,new_cat_y))
               res_limit = med_res
               if x1 <= six <= x2 and y1 <= siy <= y2 and cat_dist < res_limit:
                  print("CAT DIST/RES", cat_dist , res_limit)
                  print("FOUND:", grid_key, cat_dist, med_res )
                  grid[grid_key].append(star)
                  break

   print("med res1:", med_res1)
   print("med res2:", med_res2)
   print("MS:", len(merged_stars))
   print("QS:", len(qual_stars))
   for key in grid:
      print("FINAL GRID:", key, grid[key])
   return(grid)


def minimize_fov(cal_file, cal_params, image_file,img,json_conf,zero_poly=False):
   orig_cal = dict(cal_params)

   cal_params = update_center_radec(cal_file,cal_params,json_conf)

   all_res, inner_res, middle_res, outer_res = recalc_res(cal_params)
   cal_params['total_res_px'] = all_res

   az = np.float64(orig_cal['center_az'])
   el = np.float64(orig_cal['center_el'])
   pos = np.float64(orig_cal['position_angle'])
   pixscale = np.float64(orig_cal['pixscale'])
   x_poly = np.float64(orig_cal['x_poly'])
   y_poly = np.float64(orig_cal['y_poly'])


   this_poly = np.zeros(shape=(4,), dtype=np.float64)
   this_poly = [.0001,.0001,.0001,.0001]

   if zero_poly is True:
      cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)

      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      x_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
      y_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
   else:
      x_poly = cal_params['x_poly']
      y_poly = cal_params['y_poly']
      x_poly_fwd = cal_params['x_poly_fwd']
      y_poly_fwd = cal_params['y_poly_fwd']

   # MINIMIZE!
   print("CALPARAMS:", cal_params['x_poly'], cal_params['y_poly'])
   tries = 0

   orig_res = []
   orig_cat_image_stars = []

   # CALC RES
   for star in cal_params['cat_image_stars']:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      new_cat_x, new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)
      res_px = calc_dist((six,siy),(new_cat_x,new_cat_y))

      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_file,cal_params,json_conf)
      match_dist = angularSeparation(ra,dec,img_ra,img_dec)

      orig_res.append(res_px)
      orig_cat_image_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,res_px,bp)) 
   old_res = np.mean(orig_res)
   # END CALC RES
   print("ORIG RES:", old_res) 
   orig_info = [cal_params['center_az'], cal_params['center_el'], cal_params['ra_center'], cal_params['dec_center'], cal_params['position_angle'], cal_params['pixscale'], old_res ]
   print("ORIG INFO :", orig_info)

   res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=( az,el,pos,pixscale,x_poly, y_poly, x_poly_fwd, y_poly_fwd, image_file,img,json_conf, cal_params['cat_image_stars']), method='Nelder-Mead')
   print(res)

   if isinstance(cal_params['x_poly'], list) is not True:
      cal_params['x_poly'] = x_poly.tolist()
      cal_params['y_poly'] = x_poly.tolist()
      cal_params['x_poly_fwd'] = x_poly.tolist()
      cal_params['y_poly_fwd'] = x_poly.tolist()

   adj_az, adj_el, adj_pos, adj_px = res['x']

   print("ADJUSTMENTS:", adj_az, adj_el, adj_pos, adj_px )
   print("ORIG VALS:", az, el, pos, pixscale)
   new_az = az + (adj_az*az)
   new_el = el + (adj_el*el)
   new_position_angle = pos + (adj_pos*pos)
   new_pixscale = pixscale + (adj_px*pixscale)

   print("NEW VALS:", new_az, new_el, new_position_angle, new_pixscale)

   cal_params['center_az'] =  new_az
   cal_params['center_el'] =  new_el
   cal_params['position_angle'] =  new_position_angle
   cal_params['pixscale'] =  new_pixscale
   cal_params['total_res_px'] = res['fun']
   cal_params = update_center_radec(cal_file,cal_params,json_conf)
   print("ORIG:", orig_info)
   print("NEW INFO :", cal_params['center_az'], cal_params['center_el'], cal_params['ra_center'], cal_params['dec_center'], cal_params['position_angle'], cal_params['pixscale'], cal_params['total_res_px'] ) 
   return(cal_params)


def reduce_fov_pos(this_poly,az,el,pos,pixscale, x_poly, y_poly, x_poly_fwd, y_poly_fwd, cal_params_file, oimage, json_conf, cat_image_stars):
   cal_fn = cal_params_file
   global tries
   tries = tries + 1
   image = oimage.copy()
   image = cv2.resize(image, (1920,1080))

   new_az = az + (this_poly[0]*az)
   new_el = el + (this_poly[1]*el)
   new_position_angle = pos + (this_poly[2]*pos)
   new_pixscale = pixscale + (this_poly[3]*pixscale)

   #print("THIS POLY:", this_poly)
   #print("REDUCE VALS:", az,el,pos,pixscale)
   #print("NEW REDUCE VALS:", new_az,new_el,new_position_angle,new_pixscale)

   lat,lng,alt = json_conf['site']['device_lat'], json_conf['site']['device_lng'], json_conf['site']['device_alt']

   temp_cal_params = {}
   #temp_cal_params['ra_center'] = ra_center
   #temp_cal_params['dec_center'] = dec_center
   temp_cal_params['center_az'] = new_az
   temp_cal_params['center_el'] = new_el
   temp_cal_params['pixscale'] = new_pixscale
   temp_cal_params['position_angle'] = new_position_angle
   temp_cal_params['device_lat'] = json_conf['site']['device_lat']
   temp_cal_params['device_lng'] = json_conf['site']['device_lng']
   temp_cal_params['device_alt'] = json_conf['site']['device_alt']
   temp_cal_params['imagew'] = 1920
   temp_cal_params['imageh'] = 1080
   temp_cal_params['x_poly'] = x_poly
   temp_cal_params['y_poly'] = y_poly
   temp_cal_params['x_poly_fwd'] = x_poly_fwd 
   temp_cal_params['y_poly_fwd'] = y_poly_fwd
   temp_cal_params['cat_image_stars'] = cat_image_stars 
   temp_cal_params = update_center_radec(cal_fn,temp_cal_params,json_conf)

   #print("NEW REDUCE VALS:", new_az,new_el,new_position_angle,new_pixscale)

   all_res = []
   new_cat_image_stars = []
   for star in cat_image_stars:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      new_cat_x, new_cat_y = get_xy_for_ra_dec(temp_cal_params, ra, dec)
      res_px = calc_dist((six,siy),(new_cat_x,new_cat_y))

      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_fn,temp_cal_params,json_conf)
      match_dist = angularSeparation(ra,dec,img_ra,img_dec)

      all_res.append(res_px)
      new_cat_image_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,res_px,bp)) 
   mean_res = np.mean(all_res)
   temp_cal_params['cat_image_stars'] = new_cat_image_stars 
   temp_cal_params['total_res_px'] = mean_res
   if SHOW == 1:
      star_img = draw_star_image(image, new_cat_image_stars,temp_cal_params) 
      cv2.imshow('pepe', star_img)
      cv2.waitKey(30)
   print("CENTER FOV RES:", mean_res)
   return(mean_res)


def delete_cal_file(cal_fn, con, cur, json_conf):
   cal_dir = "/mnt/ams2/cal/freecal/" + cal_fn.replace("-stacked-calparams.json", "")
   if os.path.exists(cal_dir) is False:
      sql = "DELETE FROM calibration_files where cal_fn = ?"
      dvals = [cal_fn]
      cur.execute(sql, dvals)
      print(sql, dvals)
      sql = "DELETE FROM calfile_paired_stars where cal_fn = ?"
      dvals = [cal_fn]
      cur.execute(sql, dvals)
      con.commit()
      print(sql, dvals)


def start_calib(cal_fn, json_conf, calfiles_data, mcp=None):
   autocal_dir = "/mnt/ams2/cal/"
   station_id = json_conf['site']['ams_id']
   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)

   cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, None, mcp)
   #print("OK")
   #exit()

   if cal_img is False:
      print("FAILED")
      return(False)

   cal_img_fn = cal_fn.replace("-calparams.json", ".png")
   cal_image_file = cal_fn.replace("-calparams.json", ".png")
   cal_dir = cal_dir_from_file(cal_image_file)
   cal_json_file = get_cal_json_file(cal_dir)
   cal_json_fn = cal_json_file.split("/")[-1]
   if os.path.exists(cal_dir + cal_img_fn):
      clean_cal_img = cv2.imread(cal_dir + cal_img_fn)

   mask_file = "/mnt/ams2/meteor_archive/{}/CAL/MASKS/{}_mask.png".format(station_id, cam_id)
   if os.path.exists(mask_file) is True:
      mask = cv2.imread(mask_file)
      mask = cv2.resize(mask, (1920,1080))
   else:
      mask = np.zeros((1080,1920),dtype=np.uint8)
   clean_cal_img = cv2.subtract(clean_cal_img, mask)

   if mcp is None:
      mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
      if os.path.exists(mcp_file) == 1:
         mcp = load_json_file(mcp_file)

   if mcp is not None:
      cal_params['x_poly'] = mcp['x_poly']
      cal_params['y_poly'] = mcp['y_poly']
      cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      cal_params['y_poly_fwd'] = mcp['y_poly_fwd']

      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
      mcp['cal_version'] += 1
   else:
      mcp = None
      cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   

   
   return(station_id, cal_dir, cal_json_file, cal_image_file, cal_params, cal_img, clean_cal_img, mask_file, mcp)

def cal_status_report(cam_id, con, cur, json_conf): 
   station_id = json_conf['site']['ams_id']


   autocal_dir = "/mnt/ams2/cal/"
   # get all call files for this cam
   calfiles_data = load_cal_files(cam_id, con, cur)

   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
   else:
      mcp = None
   if mcp is None:
      print("Can't update until the MCP is made!")

   # get all paired stars by file 
   sql = """
      SELECT cal_fn, count(*) as ss, avg(res_px) as arp,  count(*) / avg(res_px) as score
        FROM calfile_paired_stars
       WHERE cal_fn like ?
         AND res_px is not NULL
       GROUP bY cal_fn
    ORDER BY score DESC
   """

   dvals = ["%" + cam_id + "%"]
   cur.execute(sql, dvals)
   rows = cur.fetchall()
   cal_fns = []

   calfile_paired_star_stats = {}
   stats_res = []
   stats_stars = []
   for row in rows:
      cal_fn, total_stars, avg_res , score = row
      calfile_paired_star_stats[cal_fn] = [cal_fn,total_stars,avg_res] 
      stats_res.append(avg_res)
      stats_stars.append(total_stars)

   avg_res = np.mean(stats_res)
   avg_stars = np.mean(stats_stars)
   # get all files from the cal-index / filesystem
   freecal_index = load_json_file("/mnt/ams2/cal/freecal_index.json") 
  
   need_to_load = {}
   for key in freecal_index:
      data = freecal_index[key]
      if data['cam_id'] == cam_id:
        cal_fn = key.split("/")[-1]
        if cal_fn not in calfiles_data:
           need_to_load[cal_fn] = {}
           need_to_load[cal_fn]['cal_dir'] = data['base_dir']
           need_to_load[cal_fn]['cal_fn'] = cal_fn
        if cal_fn not in calfile_paired_star_stats:
           need_to_load[cal_fn] = {}
           need_to_load[cal_fn]['cal_dir'] = data['base_dir']
           need_to_load[cal_fn]['cal_fn'] = cal_fn

   print("FILES TO LOAD", len(need_to_load.keys()))
   lc = 1 
   for cal_fn in need_to_load:
      #print(lc, need_to_load[cal_fn]['cal_dir'] + cal_fn)
      cal_dir = need_to_load[cal_fn]['cal_dir'] + "/"
      import_cal_file(cal_fn, cal_dir, mcp)
      lc += 1
      #exit()

   print("All files loaded...")

   os.system("clear")


   sql = """
      SELECT avg(res_px) as avg_res from calfile_paired_stars where cal_fn like ?
   """

   dvals = ["%" + cam_id + "%"]
   cur.execute(sql, dvals)
   rows = cur.fetchall()
   avg_res_2 = rows[0][0]


  
   from prettytable import PrettyTable as pt
   tb = pt()
   tb.field_names = ["Field", "Value"]

   tb.add_row(["Station ID", station_id])
   tb.add_row(["Camera ID", cam_id])
   tb.add_row(["Calfiles loaded in DB", len(calfiles_data.keys())])
   tb.add_row(["Calfiles with star data", len(calfile_paired_star_stats.keys())])
   tb.add_row(["Freecal source files", len(freecal_index.keys())])
   rr = str(round(avg_res,2)) + "/" + str(round(avg_res,2) )
   tb.add_row(["Average Res", rr])




   #print("IN DB:", len(calfiles_data.keys()) )
   #print("WITH STAR DATA:", len(calfile_paired_star_stats.keys()))
   #print("IN FOLDER :", len(freecal_index.keys()) )
   print(tb)

def import_cal_file(cal_fn, cal_dir, mcp):

   # load json, insert into main table, insert stars into pairs table
   
   cal_img_file = cal_dir + cal_fn.replace("-calparams.json", ".png")
   if os.path.exists(cal_img_file) is True:
      cal_img = cv2.imread(cal_img_file)
      if SHOW == 1:
         cv2.imshow('pepe', cal_img)
         cv2.waitKey(10)
   else:
      print("failed to import:", cal_img_file)
      return()
   if os.path.exists(cal_dir + cal_fn) is True:
      insert_calib(cal_dir + cal_fn , con, cur, json_conf)
      cal_params = load_json_file(cal_dir + cal_fn)
      cal_params_nlm = cal_params.copy()
      cal_params_nlm['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)

      for star in cal_params['cat_image_stars']:
         (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,res_px,bp) = star
         img_x = six
         img_y = siy
         print("import star! STAR:", dcname, mag, res_px)
         ra_key = str(ra) + "_" + str(dec)
         rx1 = int(new_cat_x - 20)
         rx2 = int(new_cat_x + 20)
         ry1 = int(new_cat_y - 20)
         ry2 = int(new_cat_y + 20)

         if rx1 <= 0 or ry1 <= 0 or rx2 >= 1920 or ry2 >= 1080:
            continue
         star_crop = cal_img[ry1:ry2,rx1:rx2]
         star_cat_info = [dcname,mag,ra,dec]
         star_obj = eval_star_crop(star_crop, cal_fn, rx1, ry1, rx2, ry2, star_cat_info)

         zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params_nlm,json_conf)
         zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, ra, dec)

         zp_res_px = calc_dist((img_x,img_y), (zp_cat_x,zp_cat_y))
         print(ra, dec, img_ra,img_dec)
         res_deg = angularSeparation(ra,dec,img_ra,img_dec)
         star_obj["cal_fn"] = cal_fn
         star_obj["name"]  = dcname
         star_obj["mag"] = mag
         star_obj["ra"]  = ra
         star_obj["dec"] = dec
         star_obj["new_cat_x"] = new_cat_x
         star_obj["new_cat_y"] = new_cat_y
         star_obj["zp_cat_x"]  = zp_cat_x
         star_obj["zp_cat_y"] = zp_cat_y
         star_obj["img_x"] = img_x
         star_obj["img_y"] = img_y
         star_obj["star_flux"] = star_obj['star_flux']
         star_obj["star_yn"]  = star_obj['star_yn']
         star_obj["star_pd"] = star_obj['pxd']
         star_obj["star_found"] = 1
         if mcp is None:
            star_obj["lens_model_version"] = 1
         else:
            star_obj["lens_model_version"] = mcp['cal_version']
         if new_cat_x == 0 or zp_cat_x == 0:
            continue
       
         try:
            slope = (img_y - new_cat_y) / (img_x - new_cat_x)
         except:
            continue
         try:
            zp_slope = (img_y - zp_cat_y) / (img_x - zp_cat_x)
         except:
            continue

         star_obj["slope"] = slope
         star_obj["zp_slope"] = zp_slope
         star_obj["res_px"] = res_px
         star_obj["zp_res_px"] = zp_res_px
         star_obj["res_deg"] = res_deg
         #print("INSERT NEW STAR!", star_obj)
         insert_paired_star(cal_fn, star_obj, con, cur, json_conf)
         
   else:
      print("failed to import :", cal_dir + cal_fn)
      return()


def batch_review(cam_id, con, cur, json_conf, limit=100):
   autocal_dir = "/mnt/ams2/cal/"
   calfiles_data = load_cal_files(cam_id, con, cur)

   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
   else:
      mcp = None



   #for cal_fn in calfiles_data:
   #   catalog_image(cal_fn, con, cur, json_conf)
   sql = """
      SELECT cal_fn, count(*) as ss, avg(res_px) as arp,  count(*) + (count(*) / avg(res_px)) as score
        FROM calfile_paired_stars
       WHERE cal_fn like ?
         AND res_px is not NULL
       GROUP bY cal_fn
    ORDER BY score DESC
    LIMIT {}
   """.format(limit)

   dvals = ["%" + cam_id + "%"]
   cur.execute(sql, dvals)
   rows = cur.fetchall()
   cal_fns = []
   for row in rows:
      cal_fn, total_stars, avg_res,score = row
      if cal_fn not in calfiles_data:
         continue
      if avg_res is None:
         print("ERROR", cal_fn, avg_res)
         exit()
         continue
      print("REVIEW", cal_fn, total_stars, avg_res)
      #catalog_image(cal_fn, con, cur, json_conf, True)




      # -- RECENTER -- #
      cal_image_file = cal_fn.replace("-calparams.json", ".png")
      cal_dir = cal_dir_from_file(cal_image_file)
      cal_json_file = get_cal_json_file(cal_dir)
      cal_json_fn = cal_json_file.split("/")[-1]
      oimg = cv2.imread(cal_dir + cal_image_file)
      cal_params = load_json_file(cal_json_file)
      if mcp is not None:
         cal_params['x_poly'] = mcp['x_poly']
         cal_params['y_poly'] = mcp['y_poly']
         cal_params['y_poly_fwd'] = mcp['y_poly_fwd']
         cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      

      cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
      cal_params['short_bright_stars'] = short_bright_stars
      stars,cat_stars = get_paired_stars(cal_fn, cal_params, con, cur)
      # Need to modes here?

      star_img = draw_star_image(oimg, cal_params['cat_image_stars'],cal_params) 
      if SHOW == 1:
         cv2.imshow('pepe', star_img)
         cv2.waitKey(30)

      new_cal_params = minimize_fov(cal_fn, cal_params, cal_image_file,oimg,json_conf)


      print("NEW:", new_cal_params['total_res_px'], "OLD:", cal_params['total_res_px'])
      if new_cal_params['total_res_px'] <= cal_params['total_res_px']:
         print("NEW IS BETTER SAVE!", cal_json_file)
         update_calibration_file(cal_fn, cal_params, con,cur,json_conf,mcp)
         up_stars, cat_image_stars = update_paired_stars(cal_fn, cal_params, stars, con, cur, json_conf)
         save_json_file(cal_json_file, new_cal_params)
      else:
         print("OLD IS BETTER")

      # OLD WAY
      #new_cal_params, cat_stars = recenter_fov(cal_fn, cal_params, oimg.copy(), stars, json_conf)

      print("AFTER CENTER NEW/OLD",  cal_params['total_res_px'], new_cal_params['total_res_px'])

      # -- END RECENTER -- #
      if cal_fn in calfiles_data:
         cal_fns.append(cal_fn)
      #exit()

   return(cal_fns)

def catalog_image(cal_fn, con, cur, json_conf,mcp=None, add_more=False,del_more=False ):
   fine_tune = False
   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)

   cv2.namedWindow("pepe")
   cv2.resizeWindow("pepe", 1920, 1080)

   calfiles_data = load_cal_files(cam_id , con, cur )

   resp = start_calib(cal_fn, json_conf, calfiles_data, mcp)
   if resp is False:
      print(resp)
      print("start Calib failed!")
      return(False)
   else:
      (station_id, cal_dir, cal_json_file, cal_img_file, cal_params, cal_img, clean_cal_img, mask_file,mcp) = resp


   if fine_tune is True:
      if cal_params['total_res_px'] > 20:
         tuner = 10
      elif 10 < cal_params['total_res_px'] <= 20:
         tuner = 100
      else:
         tuner = 1000
      if len(cal_params['cat_image_stars']) is None:
         print("BAD CAL: NO CAT IMAGE STARS!")
         print(cal_dir + cal_fn)
         exit()
      if len(cal_params['cat_image_stars']) >80:
         add_more = False

      print("TUNE:", len(cal_params['cat_image_stars']), cal_params['total_res_px'], tuner)
      new_cal_params, report_txt, show_img = cal_params_report(cal_fn, cal_params, json_conf, clean_cal_img.copy(), 30, mcp)

      # AUTO TWEEK THE CAL!

      best_res_px = new_cal_params['total_res_px']
      best_res_deg = new_cal_params['total_res_deg']
      best_az = 9999
      best_el = 9999
      best_ra = 9999
      best_dec = 9999
      best_pos = 9999
      best_pxs = 9999

      if len(cal_params['cat_image_stars']) > 60 and cal_params['total_res_px'] > 10:
         cal_params, del_stars = delete_bad_stars (cal_fn, cal_params, con,cur,json_conf)
   
      if cal_params['cat_image_stars'] == 0:
         print(cal_params)
         print("NO STARS FAIL")
         exit()

      for i in range(-10,10):
         v = i / tuner
         nc = cal_params.copy()
         nc['center_az'] = nc['center_az'] + v
         nc = update_center_radec(cal_fn,nc,json_conf)
         nc, report_txt, show_img = cal_params_report(cal_fn, nc, json_conf, clean_cal_img.copy(), 30, mcp)
         if nc['total_res_px'] < best_res_px:
            best_res_px = nc['total_res_px']
            best_res_deg = nc['total_res_deg']
            best_az = nc['center_az']
            best_ra = nc['ra_center']
            best_dec = nc['dec_center']
            print("BEST!", best_az, best_ra)
         print("CAT IMAGE RES PX/RES DEG", nc['total_res_px'], nc['total_res_deg'])

      if best_az != 9999:
         print("UPDATE BETTER CAL")
         cal_params = nc.copy()
         cal_params['center_az'] = best_az
         cal_params['ra_center'] = best_ra
         cal_params['dec_center'] = best_dec
         cal_params['total_res_px'] = best_res_px 
         cal_params['total_res_deg'] = best_res_deg 

      cal_params, report_txt, show_img = cal_params_report(cal_fn, cal_params, json_conf, clean_cal_img.copy(), 30, mcp)
      best_res_px = cal_params['total_res_px']


      for i in range(-10,10):
         v = i / tuner
         nc = cal_params.copy()
         nc['center_el'] = nc['center_el'] + v
         nc = update_center_radec(cal_fn,nc,json_conf)
         nc, report_txt, show_img = cal_params_report(cal_fn, nc, json_conf, clean_cal_img.copy(), 30, mcp)
         if nc['total_res_px'] < best_res_px:
            best_res_px = nc['total_res_px']
            best_el = nc['center_el']
            best_ra = nc['ra_center']
            best_dec = nc['dec_center']
            print("BEST!", best_el, best_ra)
         #print("RES", nc['total_res_px'], nc['total_res_deg'])

      if best_el != 9999:
         print("UPDATE BETTER CAL")
         cal_params = nc.copy()
         cal_params['center_el'] = best_el
         cal_params['ra_center'] = best_ra
         cal_params['dec_center'] = best_dec
         cal_params['total_res_px'] = best_res_px 
         cal_params['total_res_deg'] = best_res_deg 


      cal_params, report_txt, show_img = cal_params_report(cal_fn, cal_params, json_conf, clean_cal_img.copy(), 30, mcp)
      best_res_px = cal_params['total_res_px']

      for i in range(-10,10):
         v = i / tuner
         nc = cal_params.copy()
      
         nc['position_angle'] = nc['position_angle'] + v
         nc = update_center_radec(cal_fn,nc,json_conf)
         nc, report_txt, show_img = cal_params_report(cal_fn, nc, json_conf, clean_cal_img.copy(), 30, mcp)
         if nc['total_res_px'] < best_res_px:
            best_res_px = nc['total_res_px']
            best_pos = nc['position_angle']
            best_ra = nc['ra_center']
            best_dec = nc['dec_center']
            print("BEST!", best_pos, best_ra, best_dec)
         #print("RES", nc['total_res_px'], nc['total_res_deg'])

      if best_pos != 9999:
         print("UPDATE BETTER CAL")
         cal_params = nc.copy()
         cal_params['position_angle'] = best_pos
         cal_params['ra_center'] = best_ra
         cal_params['dec_center'] = best_dec
         cal_params['total_res_px'] = best_res_px 
         cal_params['total_res_deg'] = best_res_deg 

      cal_params, report_txt, show_img = cal_params_report(cal_fn, cal_params, json_conf, clean_cal_img.copy(), 30, mcp)
      best_res_px = cal_params['total_res_px']
      print("LAST BEST:", best_res_px)

      for i in range(-10,10):
         v = i / tuner
         nc = cal_params.copy()
         nc['pixscale'] = nc['pixscale'] + v
         nc = update_center_radec(cal_fn,nc,json_conf)
         nc, report_txt, show_img = cal_params_report(cal_fn, nc, json_conf, clean_cal_img.copy(),30,mcp)
         if nc['total_res_px'] < best_res_px:
            best_res_px = nc['total_res_px']
            best_pxs = nc['pixscale']
            best_ra = nc['ra_center']
            best_dec = nc['dec_center']
            print("BEST!", best_pxs, best_ra, best_dec)
         #print("RES", nc['total_res_px'], nc['total_res_deg'])

      if best_pxs != 9999:
         print("UPDATE BETTER CAL")
         cal_params['pixscale'] = best_pxs
         cal_params['total_res_px'] = best_res_px 
         cal_params['total_res_deg'] = best_res_deg 

      print("DONE")
      cal_params = update_center_radec(cal_fn,cal_params,json_conf)
      # final before delete
      cal_params, report_txt, show_img = cal_params_report(cal_fn, cal_params, json_conf, clean_cal_img.copy(), 30, mcp)
      best_res_px = cal_params['total_res_px']

   # DELETE BAD STARS
   if delete_more is True:
      cal_params, del_stars = delete_bad_stars (cal_fn, cal_params, con,cur,json_conf)

   # final after delete
   cal_params, report_txt, show_img = cal_params_report(cal_fn, cal_params, json_conf, clean_cal_img.copy(), 30, mcp)
   if SHOW == 1:
      cv2.imshow('pepe', show_img)
      cv2.waitKey(30)

   print("BEFORE UPDATE RES:", cal_fn, cal_params['total_res_px'], cal_params['total_res_deg'])
   cal_params = update_center_radec(cal_fn,cal_params,json_conf)
   update_calibration_file(cal_fn, cal_params, con,cur,json_conf,mcp)

   save_json_file(cal_dir + cal_fn, cal_params)


   print("AFTER UPDATE RES:", cal_dir + cal_fn, cal_params['total_res_px'], cal_params['total_res_deg'])

   if add_more is False:
      print("WE HAVE ENOUGH STARS!")
      input("WAIT")
      return()
   ### ADD MORE STARS IF WE CAN ###
   ### GET MORE STARS IF WE CAN ###
   cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
   blend_img = cv2.addWeighted(show_img, .5, cat_image, .5,0)
   cat_show_img = show_img.copy()

   last_best_res = cal_params['total_res_px'] + 2

   cal_params_nlm = cal_params.copy()
   cal_params_nlm['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   all_res, inner_res, middle_res, outer_res = recalc_res(cal_params)


   used = {}
   new_stars = []
   for star in cal_params['cat_image_stars']: 
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      # ONLY TRY TO ADD EDGE STARS! 
      


      ra_key = str(ra) + "_" + str(dec)
      used[ra_key] = {}


   print("LAST BEST RES:", inner_res, middle_res, outer_res)
   rejected = 0
   for star in cat_stars[0:200]:
      if rejected > 20:
         print("NO MORE STARS CAN BE ADDED!")
         continue
      (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star 
      ra_key = str(ra) + "_" + str(dec)
      rx1 = int(new_cat_x - 20)
      rx2 = int(new_cat_x + 20)
      ry1 = int(new_cat_y - 20)
      ry2 = int(new_cat_y + 20)

      if (new_cat_x < 300 or new_cat_x > 1620) and (new_cat_y < 200 or new_cat_y > 880):
         print("EDGE")
      else:
         continue

      if rx1 <= 0 or ry1 <= 0 or rx2 >= 1920 or ry2 >= 1080:
         continue
      if ra_key in used:
         cv2.rectangle(cat_show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (0, 255, 0), 2)
      else:
         star_crop = clean_cal_img[ry1:ry2,rx1:rx2]
         star_obj = eval_star_crop(star_crop, cal_fn, rx1, ry1, rx2, ry2)
         if star_obj['valid_star'] is True:
            star_obj['cx'] = star_obj['cx'] + rx1
            star_obj['cy'] = star_obj['cy'] + ry1
            cv2.rectangle(cat_show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (128, 200, 128), 1)
            star_yn = star_obj['star_yn'] 
            img_x= star_obj['cx'] 
            img_y = star_obj['cy'] 
            bp = star_obj['star_flux']
            star_flux = star_obj['star_flux']

            res_px = calc_dist((star_obj['cx'],star_obj['cy']),(new_cat_x,new_cat_y))
            print("RE PXS/ LAST BEST RES:", res_px, last_best_res)

            center_dist = calc_dist((960,540),(img_x,img_y))
            if center_dist < 400: 
               act_res = inner_res ** 2
            elif 400 <= center_dist < 600: 
               act_res = middle_res  ** 2
            else:

               act_res = (outer_res ** 2) + outer_res

            if res_px <= act_res :
               print("ADD NEW INCLUDE:", act_res, res_px)

               new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params,json_conf)
               match_dist = angularSeparation(ra,dec,img_ra,img_dec)
               res_deg = match_dist
               cal_params['cat_image_stars'].append((name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,bp)) 
               print("ADD NEW STAR!", res_px)

               zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params_nlm,json_conf)
               zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, ra, dec)

               zp_res_px = res_px
               slope = (img_y - new_cat_y) / (img_x - new_cat_x)
               zp_slope = (img_y - zp_cat_y) / (img_x - zp_cat_x)


               new_stars.append((cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, res_deg, slope, zp_slope, star_obj['pxd']))

               cv2.rectangle(cat_show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (0,255, 0), 1)
               cv2.line(cat_show_img, (int(new_cat_x),int(new_cat_y)), (int(star_obj['cx']),int(star_obj['cy'])), (255,255,255), 2)
               cv2.putText(cat_show_img, str(round(res_px,1)) + "px",  (int(new_cat_x + 5),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,255,0), 1)
               #cv2.imshow("CROP", star_crop)
               #cv2.imshow('pepe', cat_show_img)
               #cv2.waitKey(0)
            else:
               # NOT VALID PER EVAL
               print("FAILED EVAL!", star_obj)
               print("REJECT:", act_res, res_px)
               cv2.putText(cat_show_img, str(round(res_px,1)) + "px",  (int(new_cat_x + 5),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,128), 1)
               cv2.rectangle(cat_show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (0,0, 255), 1)
         else:

            print("REJECT: not valid" )
            for key in star_obj:
               print(key, star_obj[key])

            cv2.putText(cat_show_img, "X",  (int(rx1),int(ry1)), cv2.FONT_HERSHEY_SIMPLEX, .5, (0,0,255), 2)
            rejected += 1
            continue
            #cv2.putText(cat_show_img, str(round(res_px,1)) + "px",  (int(new_cat_x + 5),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
            cv2.rectangle(cat_show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (64,64, 128), 1)
         if SHOW == 1:
            cv2.imshow('pepe', cat_show_img)
            cv2.waitKey(10)


   update_calibration_file(cal_fn, cal_params, con,cur,json_conf,mcp)


   save_json_file(cal_dir + cal_fn, cal_params)

   if SHOW == 1:      
      cv2.imshow('pepe', blend_img)
      cv2.waitKey(100)

      cv2.imshow('pepe', cat_show_img)
      cv2.waitKey(30)



   # INSERT NEW STARS!
   for star in new_stars:
      (cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, res_deg, slope, zp_slope,star_pd) = star

      zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params_nlm,json_conf)
      zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, ra, dec)

      zp_res_px = calc_dist((img_x,img_y), (zp_cat_x,zp_cat_y))
      star_obj["cal_fn"] = cal_fn
      star_obj["name"]  = name
      star_obj["mag"] = mag
      star_obj["ra"]  = ra 
      star_obj["dec"] = dec
      star_obj["new_cat_x"] = new_cat_x 
      star_obj["new_cat_y"] = new_cat_y 
      star_obj["zp_cat_x"]  = zp_cat_x 
      star_obj["zp_cat_y"] = zp_cat_y 
      star_obj["img_x"] = img_x 
      star_obj["img_y"] = img_y 
      star_obj["star_flux"] = star_flux 
      star_obj["star_yn"]  = star_yn 
      star_obj["star_pd"] = star_pd 
      star_obj["star_found"] = 1 
      if mcp is None:
         star_obj["lens_model_version"] = 1
      else:
         star_obj["lens_model_version"] = mcp['cal_version']
      star_obj["slope"] = slope
      star_obj["zp_slope"] = zp_slope
      star_obj["res_px"] = res_px
      star_obj["zp_res_px"] = zp_res_px
      star_obj["res_deg"] = res_deg
      #print("INSERT NEW STAR!", star_obj)
      insert_paired_star(cal_fn, star_obj, con, cur, json_conf )


def recalc_res(cal_params):
   all_res = []
   inner_res = []
   middle_res = []
   outer_res = []
   for star in cal_params['cat_image_stars']:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      center_dist = calc_dist((960,540),(six,siy))
      all_res.append(res_px)
      if center_dist < 400:
         inner_res.append(res_px)
      elif 400 <= center_dist < 800:
         middle_res.append(res_px)
      else:
         outer_res.append(res_px)
   if len(all_res) > 3:
      all_res_mean = np.mean(all_res)
   else:
      all_res_mean = 5

   if len(inner_res) > 3:
      inner_res_mean = np.mean(inner_res)
   else:
      inner_res_mean = 5

   if len(middle_res) > 3:
      middle_res_mean = np.mean(middle_res)
   else:
      middle_res_mean = 15

   if len(outer_res) > 3:
      outer_res_mean = np.mean(outer_res)
   else:
      outer_res_mean = 36 

   if inner_res_mean < 5:
      inner_res_mean = 5 

   return(all_res_mean, inner_res_mean, middle_res_mean, outer_res_mean)

def delete_bad_stars (cal_fn, cal_params, con,cur,json_conf, factor =2):
   new_stars = []
   del_stars = []



   all_res, inner_res, middle_res, outer_res = recalc_res(cal_params)
   print(all_res, inner_res, middle_res, outer_res)
   mean_all_res = all_res
   if np.isnan(outer_res) :
      outer_res = 35
   print("ALL RES:", all_res)
   print("INNER RES:", inner_res)
   print("MIDDLE RES:", middle_res)
   print("OUTER RES:", outer_res)

   if sum(cal_params['x_poly'] ) == 0:
      first_time_cal = True
   else:
      first_time_cal = False 
   print("FIRST TIME CAL?:", first_time_cal)

   if all_res > 10:
      factor = 2 
   else:
      factor = 2 

   if first_time_cal is True:
      factor = 4 


   for star in cal_params['cat_image_stars']:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      center_dist = calc_dist((960,540),(six,siy))
      if center_dist < 400:
         dist_limit =  inner_res ** factor 
         if dist_limit > 6:
            dist_limit = 6 
      elif 400 <= center_dist < 800:
         dist_limit =  middle_res ** factor
         if dist_limit > 10:
            dist_limit = 10
      else:
         dist_limit =  outer_res ** factor
         if dist_limit > 20:
            dist_limit = 20

      if star[-2] < dist_limit :
         print("KEEP", dist_limit, star[-2])
         new_stars.append(star)
      else:
         print("DELETE", dist_limit, star[-2])
         del_stars.append(star)
         sql = """DELETE FROM calfile_paired_stars 
                   WHERE ra = ?
                     AND dec = ?
                  AND cal_fn = ?
         """
         dvals = [ra, dec, cal_fn]
         cur.execute(sql, dvals)
   con.commit()
   cal_params['cat_image_stars'] = new_stars
   return(cal_params, del_stars)
 

def create_star_catalog_table(con, cur):
   #   (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
   sql = """
         DROP TABLE IF EXISTS "calfile_catalog_stars";
         CREATE TABLE IF NOT EXISTS "calfile_catalog_stars" (
            cal_fn text,
            name text,
            mag real,
            ra real,
            dec real,
            new_cat_x real,
            new_cat_y real,
            zp_cat_x real,
            zp_cat_y real,
            img_x real,
            img_y real,
            star_flux real,
            star_yn real,
            star_pd integer,
            star_found integer DEFAULT 0,
            lens_model_version integer,
            PRIMARY KEY(cal_fn,ra,dec)
         )

   """

def get_xy_for_ra_dec(cal_params, ra, dec):
   # pass in cal_params and ra, dec 
   # get back x,y!

   MAG_LIMIT = 8
   img_w = 1920
   img_h = 1080
   # setup astrometry and lens model variables
   catalog_stars = []
   cal_params['imagew'] = img_w
   cal_params['imageh'] = img_h 
   RA_center = float(cal_params['ra_center'])
   dec_center = float(cal_params['dec_center'])
   F_scale = 3600/float(cal_params['pixscale'])
   if "x_poly" in cal_params:
      x_poly = cal_params['x_poly']
      y_poly = cal_params['y_poly']
      x_poly_fwd = cal_params['x_poly_fwd']
      y_poly_fwd = cal_params['y_poly_fwd']
   else:
      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      x_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
      y_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)

   zp_x_poly = np.zeros(shape=(15,), dtype=np.float64)
   zp_y_poly = np.zeros(shape=(15,), dtype=np.float64)

   fov_w = img_w / F_scale
   fov_h = img_h / F_scale
   fov_radius = np.sqrt((fov_w/2)**2 + (fov_h/2)**2)

   pos_angle_ref = cal_params['position_angle']
   x_res = int(cal_params['imagew'])
   y_res = int(cal_params['imageh'])

   center_x = int(x_res / 2)
   center_y = int(y_res / 2)
   new_cat_x, new_cat_y = distort_xy(0,0,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale)

   return(new_cat_x, new_cat_y)

def get_catalog_stars(cal_params):

   mybsd = bsd.brightstardata()
   bright_stars = mybsd.bright_stars
   #if "short_bright_stars" not in cal_params :
   #   mybsd = bsd.brightstardata()
   #   bright_stars = mybsd.bright_stars
   #else:
   #   bright_stars = cal_params['short_bright_stars']
   cat_image = np.zeros((1080,1920,3),dtype=np.uint8)

   MAG_LIMIT = 8
   img_w = 1920
   img_h = 1080
   # setup astrometry and lens model variables
   catalog_stars = []
   cal_params['imagew'] = img_w
   cal_params['imageh'] = img_h 
   RA_center = float(cal_params['ra_center'])
   dec_center = float(cal_params['dec_center'])
   F_scale = 3600/float(cal_params['pixscale'])
   if "x_poly" in cal_params:
      x_poly = cal_params['x_poly']
      y_poly = cal_params['y_poly']
      x_poly_fwd = cal_params['x_poly_fwd']
      y_poly_fwd = cal_params['y_poly_fwd']
   else:
      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      x_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
      y_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)

   zp_x_poly = np.zeros(shape=(15,), dtype=np.float64)
   zp_y_poly = np.zeros(shape=(15,), dtype=np.float64)

   fov_w = img_w / F_scale
   fov_h = img_h / F_scale
   fov_radius = np.sqrt((fov_w/2)**2 + (fov_h/2)**2)

   pos_angle_ref = cal_params['position_angle']
   x_res = int(cal_params['imagew'])
   y_res = int(cal_params['imageh'])

   center_x = int(x_res / 2)
   center_y = int(y_res / 2)

   bright_stars_sorted = sorted(bright_stars, key=lambda x: x[4], reverse=False)

   sbs = []
   for data in bright_stars_sorted:
      bname, cname, ra, dec, mag = data
      name = bname
      if mag > MAG_LIMIT:
         continue

      # decode name when needed
      if isinstance(name, str) is True:
         name = name
      else:
         name = name.decode("utf-8")

      # calc ang_sep of star's ra/dec from fov center ra/dec
      ang_sep = angularSeparation(ra,dec,RA_center,dec_center)
      if ang_sep < fov_radius and float(mag) <= MAG_LIMIT:
         sbs.append((name, name, ra, dec, mag))

         # get the star position with no distortion
         zp_cat_x, zp_cat_y = distort_xy(0,0,ra,dec,RA_center, dec_center, zp_x_poly, zp_y_poly, x_res, y_res, pos_angle_ref,F_scale)
         new_cat_x, new_cat_y = distort_xy(0,0,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale)

         catalog_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y))
         if mag <= 5.5:
            cv2.line(cat_image, (int(new_cat_x),int(new_cat_y)), (int(zp_cat_x),int(zp_cat_y)), (255,255,255), 2)
            if new_cat_x < 300:
               rx1 = new_cat_x - 10
               rx2 = new_cat_x + 40
               ry1 = new_cat_y - 10 
               ry2 = new_cat_y + 40
            elif new_cat_x > 1620:
               rx1 = new_cat_x - 40
               rx2 = new_cat_x + 10
               ry1 = new_cat_y - 40 
               ry2 = new_cat_y + 10
            else:
               rx1 = new_cat_x - 25
               rx2 = new_cat_x + 25
               ry1 = new_cat_y - 25
               ry2 = new_cat_y + 25
            cv2.rectangle(cat_image, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (255, 255, 255), 2)

   if len(catalog_stars) == 0:
      print("NO CATALOG STARS!?")

   catalog_stars = sorted(catalog_stars, key=lambda x: x[1], reverse=False)
   return(catalog_stars, sbs, cat_image)

def ai_check_star(img, img_file):

   # SHOULD CHACHE THESE!! 
   # AND LEARN FROM THEM 
   if os.path.exists(img_file) is False:
      temp_file = "/mnt/ams2/tempstar.jpg"
      cv2.imwrite(temp_file, img)
   else:
      temp_file = img_file

   url = "http://localhost:5000/AI/STAR_YN/?file={}".format(temp_file)
   if True:
      response = requests.get(url)
      content = response.content.decode()
      resp = json.loads(content)
   return(resp['star_yn'])

def do_photo(image, position, radius,r_in=10, r_out=12):
   aperture_area = np.pi * radius**2
   annulus_area = np.pi * (r_out**2 - r_in**2)
   # pass in BW crop image centered around the star
   
   aperture = CircularAperture(position,r=radius)
   bkg_aperture = CircularAnnulus(position,r_in=r_in,r_out=r_out)



   phot = aperture_photometry(image, aperture)
   bkg = aperture_photometry(image, bkg_aperture)

   #print("PH", phot['aperture_sum'][0])
   #print("BK", bkg['aperture_sum'][0])

   
   bkg_mean = bkg['aperture_sum'][0] / annulus_area
   bkg_sum = bkg_mean * aperture_area

   #print("AP AREA:", aperture_area)
   #print("AN AREA:", annulus_area)
   #print("BKG MEAN:", bkg_mean)
   #print("BKG SUM:", bkg_sum)

   flux_bkgsub = phot['aperture_sum'][0] - bkg_sum
   return(flux_bkgsub)

def get_contours_in_image(frame ):
   ih, iw = frame.shape[:2]

   cont = []
   if len(frame.shape) > 2:
      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
   cnt_res = cv2.findContours(frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      if (w >= 1 or h >= 1) and (w < 10 and h < 10):
         cont.append((x,y,w,h))

   #if len(cont) == 0:
   #   cv2.imshow('cnt', frame)

   return(cont)

def cal_dir_from_file(cal_file):
   freecal_dir = "/mnt/ams2/cal/freecal/" 
   #2022_05_18_06_32_03_000_010001-stacked-fit.jpg
   if "trim" not in cal_file:
      cal_root_fn = cal_file.split("-")[0]
   else:
      print("CAL FILE:", cal_file)
      cal_root_fn = cal_file 
   
   cal_dir = freecal_dir + cal_root_fn + "/"
   if os.path.isdir(cal_dir):
      return(cal_dir)
   else:
      return(False)

def get_cal_json_file(cal_dir):
   if cal_dir is False:
      return()
   files = glob.glob(cal_dir + "*calparams.json")
   #print("(get_cal_json_file) CAL DIR", files)
   if len(files) == 1:
      return(files[0])
   else:
      return(False)

def make_star_roi(x,y,size):
   x1 = int(x - (size/2))
   x2 = int(x + (size/2))
   y1 = int(y - (size/2))
   y2 = int(y + (size/2))
   status = True
   if True:
      if x1 <= 0:
         x1 = 0
         x2 = size
         status = False 
      if x2 >= 1920:
         x1 = 1920 - size 
         x2 = 1920
         status = False 
      if y1 <= 0:
         y1 = 0
         y2 = size
         status = False 
      if y2 >= 1080:
         y1 = 1080 - size 
         y2 = 1080 
         status = False 
      return(status, x1,y1,x2,y2)


def batch_apply(cam_id, con,cur, json_conf):
   # apply the latest MCP Poly to each cal file and then recenter them
   autocal_dir = "/mnt/ams2/cal/"
   station_id = json_conf['site']['ams_id']
   cv2.namedWindow("pepe")
   cv2.resizeWindow("pepe", 1920, 1080)

   calfiles_data = load_cal_files(cam_id, con, cur)

   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
   else:
      mcp = None
   if mcp is None:
      print("Can't update until the MCP is made!")

   cff = 0
   for cf in calfiles_data:
      apply_calib (cf, calfiles_data, json_conf, mcp)


def apply_calib (cal_file, calfiles_data, json_conf, mcp):
      (station_id, camera_id, cal_fn, cal_ts, az, el, ra, dec, position_angle,\
         pixel_scale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
         y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) = calfiles_data[cal_file]
      cal_params = cal_data_to_cal_params(cal_fn, calfiles_data[cal_file],json_conf)

      print("--------------")
      print("STARTING VALS", cal_fn)
      print("--------------")
      show_calparams(cal_params)      

      print("VIEW CAL APPLY:", cal_fn)
      cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf,None,None,mcp)
      if SHOW == 1:
         cv2.imshow('pepe', cal_img)
         cv2.resizeWindow("pepe", 1920, 1080)

      cv2.waitKey(30)
      if mcp is not None:
         cal_params['x_poly'] = mcp['x_poly']
         cal_params['y_poly'] = mcp['y_poly']
         cal_params['y_poly_fwd'] = mcp['y_poly_fwd']
         cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      else:
         cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)

      #if cal_version < mcp['cal_version']:
      #   print(cal_fn, "needs update!", cal_version, mcp['cal_version'])

      cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
      cal_params['short_bright_stars'] = short_bright_stars
      cal_params['no_match_stars'] = [] 
      cal_image_file = cal_fn.replace("-calparams.json", ".png")
      cal_dir = cal_dir_from_file(cal_image_file)
      cal_json_file = get_cal_json_file(cal_dir)
      cal_json_fn = cal_json_file.split("/")[-1]
      oimg = cv2.imread(cal_dir + cal_image_file)
      cal_params_json = load_json_file(cal_json_file)

      stars,cat_stars = get_paired_stars(cal_fn, cal_params, con, cur)
      # Need to modes here?
      cal_params, cat_stars = recenter_fov(cal_fn, cal_params, oimg.copy(), stars, json_conf)
      print("--------------")
      print("AFTER RECENTER", cal_fn)
      print("--------------")
      print("RA/DEC:", cal_params['ra_center'], cal_params['dec_center'])
      

      update_calibration_file(cal_fn, cal_params, con,cur,json_conf,mcp)
      print(cal_json_file)
      save_json_file(cal_json_file, cal_params)

      show_calparams(cal_params)      

      stars,cat_stars = get_paired_stars(cal_fn, cal_params, con, cur)
      up_stars, cat_image_stars = update_paired_stars(cal_fn, cal_params, stars, con, cur, json_conf)

      save_json_file(cal_json_file, cal_params)

      print("VIEW CAL 33:", cal_fn)
      cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, None, cal_params, mcp)

      print("--------------")
      print("AFTER VIEW CAL", cal_fn)
      print("--------------")
      show_calparams(cal_params)      

      if SHOW == 1:
         cv2.imshow("pepe", cal_img)
         cv2.waitKey(30)
      #view_calib(cal_fn,json_conf, cal_params,oimg, 1)

def show_calparams(cal_params):
   for key in cal_params:
      if "star" in key:
         print("CP", key, len(cal_params[key]))
      elif "poly" in cal_params:
         print("CP", key, cal_params[key][0])
      else:
         print("CP", key, cal_params[key])

def update_calfiles(cam_id, con,cur, json_conf):
   autocal_dir = "/mnt/ams2/cal/"
   station_id = json_conf['site']['ams_id']

   calfiles_data = load_cal_files(cam_id, con, cur)

   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
   else:
      mcp = None
   if mcp is None:
      print("Can't update until the MCP is made!")
   cff = 0
   for cf in calfiles_data:
      (station_id, camera_id, cal_fn, cal_ts, az, el, ra, dec, position_angle,\
         pixel_scale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
         y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) = calfiles_data[cf]
      if cal_version < mcp['cal_version']:
         print(cal_fn, "needs update!", cal_version, mcp['cal_version'])

         manual_tweek_calib(cal_fn, con, cur, json_conf)

         #redo_calfile(cal_fn, con, cur, json_conf)
         cv2.waitKey(30)
         print("ENDED HERE")
         #repair_calfile_stars(cal_fn, con, cur, json_conf, mcp)
      else:
         print(cal_fn, "is ok!", cal_version, mcp['cal_version'])
      cff += 1
      if cff > 10:
         print("EXIT", cff)
         exit()


def recenter_fov(cal_fn, cal_params, cal_img, stars, json_conf):
   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)
   # make sure we are using the latest MCP!
   autocal_dir = "/mnt/ams2/cal/"
   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      cal_params['x_poly'] = mcp['x_poly']
      cal_params['y_poly'] = mcp['y_poly']
      cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      cal_params['y_poly_fwd'] = mcp['y_poly_fwd']
   else:
      mcp = None


   if False: 
      cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)

   print("XPOLY0:", cal_params['x_poly'][0])

   this_poly = np.zeros(shape=(4,), dtype=np.float64)
   this_poly = [.001,.001,.001,.001]
   
   start_cp = dict(cal_params)
   start_res = cal_params['total_res_px']

   center_stars = []
   center_user_stars = []
   for star in cal_params['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
      if 100 <= six <= 1820 and 100 <= siy <= 980:
         center_stars.append(star)
         center_user_stars.append((six,siy,bp))

   #                                            def reduce_fov_pos(this_poly,az,el,pos,pixscale, x_poly, y_poly, cal_params_file, oimage, json_conf, cat_image_stars):
   res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=( cal_params['center_az'],cal_params['center_el'],cal_params['position_angle'],cal_params['pixscale'],cal_params['x_poly'], cal_params['y_poly'], cal_params['x_poly_fwd'], cal_params['y_poly_fwd'],cal_fn,cal_img,json_conf, center_stars), method='Nelder-Mead')
   print("RES FROM MINIMIZE:", res)

   adj_az, adj_el, adj_pos, adj_px = res['x']

   #nc = minimize_fov(cal_fn, cal_params, cal_fn,oimg,json_conf )
   nc = cal_params.copy()
   if type(nc['x_poly']) is not list:
      nc['x_poly'] = nc['x_poly'].tolist()
      nc['y_poly'] = nc['y_poly'].tolist()
      nc['y_poly_fwd'] = nc['y_poly_fwd'].tolist()
      nc['x_poly_fwd'] = nc['x_poly_fwd'].tolist()

   nc['center_az'] = cal_params['center_az'] + (adj_az*cal_params['center_az'] )
   nc['center_el'] = cal_params['center_el'] + (adj_az*cal_params['center_el'] )
   nc['position_angle'] = cal_params['position_angle'] + (adj_az*cal_params['position_angle'] )
   nc['pixscale'] = cal_params['pixscale'] + (adj_az*cal_params['pixscale'] )
   nc['total_res_px'] = res['fun']

   #XXXX BUG!!!!
   nc = update_center_radec(cal_fn,nc,json_conf)
   print("""
      FINAL!
      AZ/EL {} {}
      RA/DEC {} {}
      POS {}
      PIX {}
      RES {}
   """.format(nc['center_az'], nc['center_el'], nc['ra_center'], nc['dec_center'], nc['position_angle'], nc['pixscale'] , nc['total_res_px']))

   cat_stars, short_bright_stars, cat_image = get_catalog_stars(nc)

   #nc['short_bright_stars'] = short_bright_stars

   end_res = nc['total_res_px']
   if end_res > start_res:
      # IGNORE THE RUN!
      nc = start_cp 

   cat_stars, short_bright_stars, cat_image = get_catalog_stars(nc)

   up_stars, cat_image_stars = update_paired_stars(cal_fn, nc, stars, con, cur, json_conf)
   nc['cat_image_stars'] = cat_image_stars
   for star in cat_image_stars:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      print(dcname, mag, res_px)

   # save the json file here too.
   print("END RECENTER", nc['ra_center'], nc['dec_center'])

   return(nc, cat_stars)


def recenter_cal_file(cal_fn, con, cur, json_conf, mcp):

      cal_image_file = cal_fn.replace("-calparams.json", ".png")
      cal_dir = cal_dir_from_file(cal_image_file)
      cal_json_file = get_cal_json_file(cal_dir)
      cal_json_fn = cal_json_file.split("/")[-1]
      oimg = cv2.imread(cal_dir + cal_image_file)

      # APPLY LATEST MODEL AND RECENTER THE FOV
      # THEN SAVE THE CALP FILE AND UPDATE THE DB

      if os.path.exists(cal_json_file) is True:

         cal_params = load_json_file(cal_json_file)
         cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
         cal_params['short_bright_stars'] = short_bright_stars

         view_calib(cal_fn,json_conf, cal_params,oimg, show = 0)
         this_poly = np.zeros(shape=(4,), dtype=np.float64)
         this_poly = [0,0,0,0]



         res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=( cal_params['center_az'],cal_params['center_el'],cal_params['position_angle'],cal_params['pixscale'],cal_params['x_poly'], cal_params['y_poly'], cal_image_file,oimg,json_conf, cal_params['cat_image_stars'],cal_params['user_stars'],1,SHOW,None,cal_params['short_bright_stars']), method='Nelder-Mead')
         print("RES FROM MINIMIZE:", res)

         adj_az, adj_el, adj_pos, adj_px = res['x']

         #nc = minimize_fov(cal_fn, cal_params, cal_fn,oimg,json_conf )
         nc = cal_params.copy()

         nc['center_az'] = cal_params['center_az'] + (adj_az*cal_params['center_az'] )
         nc['center_el'] = cal_params['center_el'] + (adj_az*cal_params['center_el'] )
         nc['position_angle'] = cal_params['position_angle'] + (adj_az*cal_params['position_angle'] )
         nc['pixscale'] = cal_params['pixscale'] + (adj_az*cal_params['pixscale'] )
         nc = update_center_radec(cal_file,nc,json_conf)
         cat_stars, short_bright_stars, cat_image = get_catalog_stars(nc)
         nc['short_bright_stars'] = short_bright_stars

         print("BEFORE:")
         print("CAZ", cal_params['center_az'])
         print("CEL", cal_params['center_el'])
         print("POS", cal_params['position_angle'])
         print("PIX", cal_params['pixscale'])
         print("RES", cal_params['total_res_px'])

         print("AFTER:")

         nc['total_res_px'] = res_px
         nc['total_res_deg'] = res_deg

         print("CAZ", nc['center_az'])
         print("CEL", nc['center_el'])
         print("POS", nc['position_angle'])
         print("PIX", nc['pixscale'])
         print("RES", nc['total_res_px'])
         up_cat_image_stars = []
         for star in cal_params['cat_image_stars']:
            dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
            sql = """
                   SELECT new_cat_x, new_cat_y 
                     FROM calfile_catalog_stars 
                    WHERE cal_fn = ? 
                      AND ra = ? 
                      AND dec = ?
            """
            svals = [cal_fn, ra, dec]
            cur.execute(sql, svals)
            rows = cur.fetchall()
            #print("NEW:", rows[0])
            up_cat_x, up_cat_y = rows[0]
            res_px = calc_dist((six,siy), (up_cat_x,up_cat_y))

            #print("OLD STAR:", dcname, new_cat_x, new_cat_y, cat_dist)
            #print("NEW STAR:", dcname, up_cat_x, up_cat_y, res_px)
            if res_px < 20:
               up_cat_image_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) )

         nc['cat_image_stars'] = up_cat_image_stars
         temp_stars, total_res_px,total_res_deg = cat_star_report(nc['cat_image_stars'], 4)
         nc['total_res_px'] = total_res_px
         nc['total_res_deg'] = total_res_deg

         #print("OLD RES:", cal_params['total_res_px'] )
         #print("NEW RES:", nc['total_res_px'] )
         # only save if new is better than old
         if cal_params['total_res_px'] > total_res_px:
            cal_params = nc
            save_json_file(cal_json_file, cal_params)
            update_calfile(cal_fn, con, cur, json_conf, mcp)
            print("SAVED NEW BETTER")
         else:
            print("OLD BETTER")

         view_calib(cal_fn,json_conf, nc,oimg, show = 1)
         print("DONE")
         exit()

def redo_calfile(cal_fn, con, cur, json_conf):
   cal_image_file = cal_fn.replace("-calparams.json", ".png")
   cal_dir = cal_dir_from_file(cal_image_file)
   cal_img = cv2.imread(cal_dir + cal_image_file)
   cal_json_file = get_cal_json_file(cal_dir)
   cal_json_fn = cal_json_file.split("/")[-1]

   sql = """
      DELETE FROM calfile_catalog_stars 
            WHERE cal_fn = ?
   """
   ivals = [cal_fn]
   cur.execute(sql, ivals)
   con.commit()

   sql = """
      DELETE FROM calibration_files 
            WHERE cal_fn = ?
   """
   ivals = [cal_fn]
   cur.execute(sql, ivals)
   con.commit()

   sql = """
      DELETE FROM calfile_paired_stars 
            WHERE cal_fn = ?
   """
   ivals = [cal_fn]
   cur.execute(sql, ivals)
   con.commit()

   if os.path.exists(cal_dir + cal_image_file):
      get_image_stars(cal_dir + cal_image_file, con, cur, json_conf)
   else:
      print("NO IMAGE", cal_dir + cal_image_file)






def repair_calfile_stars(cal_fn, con, cur, json_conf, mcp):
   # RE-PAIR STARS WITH LATESTS VALUES FROM DB OR JSON
   # AND MAKE SURE BOTH MATCH BY THE END!
   # COULD ALSO CALL THIS APPLY CAL 

   # LOAD THE FILES
   cal_image_file = cal_fn.replace("-calparams.json", ".png")
   cal_dir = cal_dir_from_file(cal_image_file)
   cal_img = cv2.imread(cal_dir + cal_image_file)
   cal_json_file = get_cal_json_file(cal_dir)
   cal_json_fn = cal_json_file.split("/")[-1]

   cal_params = load_json_file(cal_json_file)
   # RELOAD THE CATALOG STARS BASED ON JSON CAL PARAMS FILE (REFITS OR REMODEL UPDATES SHOULD HAVE ALREADY HAPPENED BEFORE THIS!")
   cat_stars, short_bright_stars = reload_calfile_catalog_stars(cal_fn, cal_params)


   
   # GET PAIRED STARS FROM THE DB
   # THIS IS WHAT WE HAVE CURRENTLY
   # LETS RE-PAIR EACH ONE TO GET THE BEST MATCH / VALUES
   stars,cat_stars = get_paired_stars(cal_fn, cal_params, con, cur)
   for star in stars:
      (cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope) = star
      key = str(ra)[0:5] + "_" + str(dec)[0:5]
      print("ORIG:", cal_fn, name, mag, star_yn, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px)
      #cv2.line(cal_img, (int(new_cat_x),int(new_cat_y)), (int(zp_cat_x),int(zp_cat_y)), (255,255,255), 2)

      if res_px is not None:
         res_px = calc_dist((img_x,img_y), (new_cat_x,new_cat_y))
         if 0 < res_px <= 1:
            color = [0,255,0]
         elif 1 < res_px <= 3:
            color = [255,0,0]
         elif res_px > 3:
            color = [0,0,255]
         else:
            color = [255,255,255]

      if img_x is not None:
         cv2.circle(cal_img, (int(img_x),int(img_y)), 3, (0,69,255),1)
      if new_cat_x is not None:
         cv2.circle(cal_img, (int(new_cat_x),int(new_cat_y)), 5, color,1)
      if zp_cat_x is not None:
         cv2.circle(cal_img, (int(zp_cat_x),int(zp_cat_y)), 3, (128,128,128),1)
      if zp_cat_x is not None:
         cv2.line(cal_img, (int(zp_cat_x),int(zp_cat_y)), (int(img_x),int(img_y)), (128,128,128), 2)
      if new_cat_x is not None:
         cv2.line(cal_img, (int(new_cat_x),int(new_cat_y)), (int(img_x),int(img_y)), color, 1)

      # get close stars from the latest refreshed catalog db 
      star_obj = {}
      star_obj['cal_fn'] = cal_fn
      star_obj['x'] = img_x
      star_obj['y'] = img_y
      star_obj['star_flux'] = star_flux
      close_stars = find_close_stars(star_obj)

      if len(close_stars) > 0:
         for cs in close_stars:
            (cs_cal_fn, cs_name, cs_mag, cs_ra, cs_dec, cs_new_cat_x, cs_new_cat_y, cs_zp_cat_x, cs_zp_cat_y, \
               cs_ximg_x, cs_ximg_y, cs_star_flux, cs_star_yn, cs_star_pd, cs_star_found, cs_lens_model_version, \
               cs_slope, cs_zp_slope, cs_dist, cs_zp_dist) = cs
            cv2.line(cal_img, (int(cs_new_cat_x),int(cs_new_cat_y)), (int(img_x),int(img_y)), [255,255,255], 3)
      else:
         cv2.putText(cal_img, "X",  (int(img_x),int(img_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)

   print("DONE REDO")
   if SHOW == 1:
      cv2.imshow('pepe', cal_img)
      cv2.waitKey(30)
   #get_image_stars(cal_dir + cal_image_file, con, cur, json_conf, True)
   #view_calfile(cal_fn, con,cur,json_conf)
   #exit()

def cal_data_to_cal_params(cal_fn, cal_data,json_conf, mcp):
   (station_id, camera_id, cal_fn, cal_ts, az, el, ra, dec, position_angle,\
      pixel_scale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
      y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) = cal_data

   x_poly = json.loads(x_poly)
   y_poly = json.loads(y_poly)
   x_poly_fwd = json.loads(x_poly_fwd)
   y_poly_fwd = json.loads(y_poly_fwd)
      
   if mcp is not None:
      x_poly = mcp['x_poly']
      y_poly = mcp['y_poly']
      x_poly_fwd = mcp['x_poly_fwd']
      y_poly_fwd = mcp['y_poly_fwd']

   
   cal_params = {}
   cal_params['station_id'] = station_id
   cal_params['camera_id'] = camera_id
   cal_params['cal_fn'] = cal_fn
   cal_params['img_w'] = 1920
   cal_params['img_h'] = 1080 
   cal_params['cal_ts'] = cal_ts
   cal_params['center_az'] = az
   cal_params['center_el'] = el
   cal_params['ra_center'] = ra
   cal_params['dec_center'] = dec
   cal_params['position_angle'] = position_angle
   cal_params['pixscale'] = pixel_scale
   cal_params['total_res_px'] = res_px
   cal_params['total_res_deg'] = res_deg 
   cal_params['x_poly'] = x_poly 
   cal_params['y_poly'] = y_poly 
   cal_params['x_poly_fwd'] = x_poly_fwd 
   cal_params['y_poly_fwd'] = y_poly_fwd 
   cal_params['cal_version'] = y_poly_fwd 
   cal_params['last_update'] = last_update


   cal_params['user_stars'] = []
   cal_params['cat_image_stars'] = []

   stars,cat_stars = get_paired_stars(cal_fn, cal_params, con, cur)
   for star in stars:
      (x_cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope) = star
      if ra is not None:
         cal_params['cat_image_stars'].append((name,mag,ra,dec,ra,dec,res_px,zp_cat_x,zp_cat_y,az,el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux))
      cal_params['user_stars'].append((img_x,img_y,star_flux))

   #print("CAL PARAMS 1:", cal_fn, cal_params['ra_center'], cal_params['dec_center'])
   #print("AZ EL :", cal_fn, cal_params['center_az'], cal_params['center_el'])
   #cal_params = update_center_radec(cal_fn,cal_params,json_conf)
   #print("CAL PARAMS 2:", cal_fn, cal_params['ra_center'], cal_params['dec_center'])
   return(cal_params)

def make_help_img(cal_img):
   x1 = int((1920 / 2) - 400)
   x2 = int((1920 / 2) + 400)
   y1 = int((1080/ 2) - 400)
   y2 = int((1080/ 2) + 400)
   temp_img = cal_img.copy()
   bgimg = temp_img[y1:y2, x1:x2]
   help_image = np.zeros((800,800,3),dtype=np.uint8) 
   blend_img = cv2.addWeighted(bgimg, .5, help_image, .5,0)
   cv2.putText(blend_img, "ALLSKYOS - CALIBRATION TOOL",  (100,30), cv2.FONT_HERSHEY_SIMPLEX, .9, (128,128,128), 2)
   cv2.putText(blend_img, "[ESC] = Quit",  (120,100), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[F1]  = Display/Hide this help message",  (120,140), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[A]   = -Azimuth ",  (120,180), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[S]   = -Elevation",  (120,220), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[D]   = +Elevation",  (120,260), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[F]   = +Azimuth ",  (120,300), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[Q]   = -Pixel Scale",  (120,340), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[W]   = -Position Angle",  (120,380), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[E]   = +Position Angle",  (120,420), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[R]   = +Pixel Scale",  (120,460), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[C]   = Center FOV",  (120,500), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[P]   = Re-Fit",  (120,540), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[0]   = Set Interval to 1.0",  (120,580), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[1]   = Set Interval to 0.1",  (120,620), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[2]   = Set Interval to 0.01",  (120,660), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[3]   = Set Interval to 0.001",  (120,700), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)

   temp_img[y1:y2,x1:x2] = blend_img

   cv2.rectangle(temp_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 2)
   return(temp_img)

def show_message(cal_img, message, px, py):
   val = 255
   for i in range(0, 10):
      val = val - (i * 10)
      temp_img = cal_img.copy()
      color = [val,val,val]
      cv2.putText(temp_img, message,  (px,py), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
      if SHOW == 1:
         cv2.resizeWindow("TWEEK CAL", 1920, 1080)
         cv2.imshow("TWEEK CAL", temp_img)
         cv2.waitKey(30)



def cat_view(cal_fn, con, cur, json_conf, mcp=None):
   print("CAT VIEW")
   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)
   cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, None, None, mcp)

   cal_img_fn = cal_fn.replace("-calparams.json", ".png")
   cal_image_file = cal_fn.replace("-calparams.json", ".png")
   cal_dir = cal_dir_from_file(cal_image_file)
   cal_json_file = get_cal_json_file(cal_dir)
   cal_json_fn = cal_json_file.split("/")[-1]

   if os.path.exists(cal_dir + cal_img_fn):
      clean_cal_img = cv2.imread(cal_dir + cal_img_fn)

   cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
   if SHOW == 1:
      cv2.imshow('pepe', cat_image)
      cv2.waitKey(30)
   for star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
      print(name,mag,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y)

   

def manual_tweek_calib(cal_fn, con, cur, json_conf,mcp):
   help_on = False

   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)
   cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, None, None, mcp)
   help_img = make_help_img(cal_img) 
   interval = .1

   cal_img_fn = cal_fn.replace("-calparams.json", ".png")
   cal_image_file = cal_fn.replace("-calparams.json", ".png")
   cal_dir = cal_dir_from_file(cal_image_file)
   cal_json_file = get_cal_json_file(cal_dir)
   cal_json_fn = cal_json_file.split("/")[-1]
   if os.path.exists(cal_dir + cal_img_fn):
      clean_cal_img = cv2.imread(cal_dir + cal_img_fn)

   cv2.namedWindow("TWEEK CAL")
   cv2.resizeWindow("TWEEK CAL", 1920, 1080)

   cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
   cal_params['short_bright_stars'] = short_bright_stars
   stars,cat_image_stars = get_paired_stars(cal_fn, cal_parasm, con, cur)
   cal_params['cat_image_stars'] = cat_image_stars

   cat_on = False

   while True:
      if help_on is True and SHOW == 1:
         cv2.imshow("TWEEK CAL", help_img)
      elif SHOW == 1:
         cv2.imshow("TWEEK CAL", cal_img)
      key = cv2.waitKey(30)
      print("KEY:", key)
      if key == 27:
         return()
      if key == 104 or key == 190:
         if help_on is False:
            help_on = True
            help_img = make_help_img(cal_img) 
            cv2.imshow('TWEEK CAL', help_img) 
         else:
            cv2.imshow('TWEEK CAL', cal_img) 
            help_on = False
      if key == 102:
         cal_params['center_az'] += interval
         cal_img, cal_params = view_calfile(cal_fn, con, cur, json_conf, cal_params,mcp)
         show_message(cal_img, "AZ + " + str(interval),900,500 )
      if key == 97:
         cal_params['center_az'] -= interval
         cal_img, cal_params = view_calfile(cal_fn, con, cur, json_conf, cal_paramsm,mcp)
         show_message(cal_img, "AZ - " + str(interval),900,500 )
      if key == 115:
         cal_params['center_el'] -= interval
         cal_img, cal_params = view_calfile(cal_fn, con, cur, json_conf, cal_params,mcp)
         show_message(cal_img, "EL - " + str(interval),900,500 )
      if key == 100:
         cal_params['center_el'] += interval
         cal_img, cal_params = view_calfile(cal_fn, con, cur, json_conf, cal_params,mcp)
         show_message(cal_img, "EL + " + str(interval),900,500 )
      if key == 119:
         cal_params['position_angle'] -= interval
         cal_img, cal_params = view_calfile(cal_fn, con, cur, json_conf, cal_params,mcp)
         show_message(cal_img, "PA - " + str(interval),900,500 )
      if key == 101:
         cal_params['position_angle'] += interval
         cal_img, cal_params = view_calfile(cal_fn, con, cur, json_conf, cal_params,mcp)
         show_message(cal_img, "PA + " + str(interval),900,500 )
      if key == 113:
         cal_params['pixscale'] -= interval
         cal_img, cal_params = view_calfile(cal_fn, con, cur, json_conf, cal_params,mcp)
         show_message(cal_img, "PX - " + str(interval),900,500 )
      if key == 114:
         cal_params['pixscale'] += interval
         show_message(cal_img, "PX + " + str(interval),900,500 )

      if key == 99 or key == 191:
         show_message(cal_img, "Recenter FOV Fit" + str(interval),900,500 )
         cal_params, cat_stars = recenter_fov(cal_fn, cal_params, clean_cal_img.copy(), stars, json_conf)
         cal_params['short_bright_stars'] = short_bright_stars
         cal_img, cal_params = view_calfile(cal_fn, con, cur, json_conf, cal_params)


      if key == 112 or key == 192:
         show_message(cal_img, "Recenter Poly Vars" + str(interval),900,500 )
      if key == 193:
         if cat_on is True:
            cv2.imshow('TWEEK CAL', cal_img) 
            cat_on = False
         else:
            cv2.imshow('TWEEK CAL', catalog_image) 
            cat_on = True 





      if key == 48 :
         interval = 1
         show_message(cal_img, "Set interval to " + str(interval),900,500 )
      if key == 49 :
         interval = .1
         show_message(cal_img, "Set interval to " + str(interval),900,500 )
      if key == 50 :
         interval = .01
         show_message(cal_img, "Set interval to " + str(interval),900,500 )
      if key == 51 :
         interval = .001
         show_message(cal_img, "Set interval to " + str(interval),900,500 )

      cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
      up_stars, cat_image_stars = update_paired_stars(cal_fn, cal_params, stars, con, cur, json_conf)
      cal_params['cat_image_stars'] = cat_image_stars
      #for xxx in up_stars:
      #   print("UPSTAR:", xxx)

      cal_params['short_bright_stars'] = short_bright_stars
      cal_img, cal_params = view_calfile(cal_fn, con, cur, json_conf, cal_params)


      blend_img = cv2.addWeighted(cal_img, .6, catalog_image, .4,0)
      cal_img= blend_img

      #cv2.imshow("TWEEK CAL", blend_img)
      help_img = make_help_img(cal_img) 


def view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data= None, cp = None,mcp=None):
   print("start view calfile")
   if cal_fn in calfiles_data:
      cal_data = calfiles_data[cal_fn]
   else:
      print("PROBLEM cal_fn is not in the cal data!?", cam_id, cal_fn)
      #print("CALFILES", calfiles_data)
      #exit()
      return(False, False)

   if cp is None:
      cal_params = cal_data_to_cal_params(cal_fn, cal_data,json_conf, mcp)
   else:
      cal_params = cp.copy()

   cal_img_fn = cal_fn.replace("-calparams.json", ".png")
   cal_image_file = cal_fn.replace("-calparams.json", ".png")
   cal_dir = cal_dir_from_file(cal_image_file)
   cal_json_file = get_cal_json_file(cal_dir)
   cal_json_fn = cal_json_file.split("/")[-1]
   if os.path.exists(cal_dir + cal_img_fn):
      cal_img = cv2.imread(cal_dir + cal_img_fn)

   
   cal_params = update_center_radec(cal_fn,cal_params,json_conf)
   stars, cat_image_stars = get_paired_stars(cal_fn, cal_params, con, cur)
   cal_params['cat_image_stars'] = cat_image_stars

   rez = []

   for star in stars:
      (cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope) = star
      if ra is not None:
         res_px = calc_dist((img_x,img_y), (new_cat_x,new_cat_y))
         zp_res_px = calc_dist((img_x,img_y), (zp_cat_x,zp_cat_y))
         rez.append(res_px)
      else:
         res_px = None
      if res_px is not None:
         if 0 < res_px <= 1:
            color = [0,255,0]
         elif 1 < res_px <= 3:
            color = [255,0,0]
         elif res_px > 3:
            color = [0,0,255]
         else:
            color = [255,255,255]
      else:
         # There is no match for this star
         cv2.putText(cal_img, "X",  (int(img_x + 5),int(img_y )), cv2.FONT_HERSHEY_SIMPLEX, .5, (0,0,128), 2)

      if img_x is not None:
         cv2.circle(cal_img, (int(img_x),int(img_y)), 3, (0,69,255),1)
      if new_cat_x is not None:
         cv2.circle(cal_img, (int(new_cat_x),int(new_cat_y)), 5, color,1)
      if zp_cat_x is not None:
         cv2.circle(cal_img, (int(zp_cat_x),int(zp_cat_y)), 3, (128,128,128),1)
      if zp_cat_x is not None:
         cv2.line(cal_img, (int(zp_cat_x),int(zp_cat_y)), (int(img_x),int(img_y)), (128,128,128), 2)
      if new_cat_x is not None:
         cv2.line(cal_img, (int(new_cat_x),int(new_cat_y)), (int(img_x),int(img_y)), color, 1)

   mean_res = np.mean(rez)
   cal_params['total_res_px'] = mean_res 
   desc = json_conf['site']['ams_id'] + " " + cal_fn.replace("-calparams.json", "")
   desc = desc.replace("-stacked", "")
   desc += " | "

   desc += "AZ {:.4f} | ".format(cal_params['center_az'])
   desc += "EL {:.4f} | ".format(cal_params['center_el'])
   desc += "RA {:.4f} | ".format(float(cal_params['ra_center']))
   desc += "DEC {:.4f} | ".format(float(cal_params['dec_center']))
   desc += "POS {:.4f} | ".format(cal_params['position_angle'])
   desc += "PIX {:.4f} | ".format(cal_params['pixscale'])
   desc += "RES {:.3f} | ".format(mean_res)
   cv2.putText(cal_img, desc,  (250,15), cv2.FONT_HERSHEY_SIMPLEX, .6, (128,128,128), 1)

   # todo add total_res_deg...
   return(cal_img, cal_params)

def update_paired_stars(cal_fn, cal_params, stars, con, cur, json_conf):
   # this will update existing paired stars with latest cat x,y based on provided cal_params


      # get stars from the cal_params 

   up_stars = []
   up_cat_image_stars = []
   #print("CALP", cal_params['center_az'], cal_params['center_el'], cal_params['ra_center'], cal_params['dec_center'] )
   for star in stars:
      (cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope) = star

      n_new_cat_x,n_new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)


      if new_cat_x is None:
         continue
      if n_new_cat_x is not None:
         n_res_px = calc_dist((img_x,img_y), (n_new_cat_x,n_new_cat_y))
      else:
         n_res_px = 0

      #print("OLD {} {}".format(new_cat_x, new_cat_y))
      #print("NEW {} {}".format(n_new_cat_x, n_new_cat_y))
      #print("___")

      up_stars.append((cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope)) 
      sql = """
         UPDATE calfile_paired_stars 
            SET new_cat_x = ?, 
                new_cat_y = ?, 
                res_px = ? 
          WHERE cal_fn = ? 
            AND img_x = ? 
            AND img_y = ?
      """
      uvals = [n_new_cat_x, n_new_cat_y, n_res_px, cal_fn, img_x, img_y]
      cur.execute(sql, uvals)
      #print(sql)
      #print(uvals)
      # temp holder / fix later

      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params,json_conf)

      img_ra = img_ra 
      img_dec = img_dec 
      img_az = img_az 
      img_el = img_el 
      match_dist = zp_res_px
      cat_dist = res_px 
      if ra is not None:
         up_cat_image_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux)) 
   con.commit()

   return(up_stars, up_cat_image_stars)

def update_calibration_file(cal_fn, cal_params, con,cur,json_conf,mcp):
   ts = time.time()

   if type(cal_params['x_poly']) is not list:
      cal_params['x_poly'] = cal_params['x_poly'].tolist()
      cal_params['y_poly'] = cal_params['y_poly'].tolist()
      cal_params['y_poly_fwd'] = cal_params['y_poly_fwd'].tolist()
      cal_params['x_poly_fwd'] = cal_params['x_poly_fwd'].tolist()

   if mcp is None:
      cv = 1
   else:
      cv = mcp['cal_version']

   uvals = [ts, cal_params['center_az'], cal_params['center_el'], cal_params['ra_center'], cal_params['dec_center'], \
            cal_params['position_angle'], cal_params['pixscale'], json.dumps(cal_params['x_poly']), json.dumps(cal_params['y_poly']), \
            json.dumps(cal_params['x_poly_fwd']), json.dumps(cal_params['y_poly_fwd']), cal_params['total_res_px'], cal_params['total_res_deg'], \
            cv, ts, cal_fn]
   sql = """
      UPDATE calibration_files 
         SET 
                 cal_ts = ?,
                     az = ?,
                     el = ?,
                     ra = ?,
                    dec = ?,
         position_angle = ?,
            pixel_scale = ?,
                 x_poly = ?,
                 y_poly = ?,
             x_poly_fwd = ?,
             y_poly_fwd = ?,
                 res_px = ?,
                res_deg = ?,
            cal_version = ?,
            last_update = ?
       WHERE cal_fn = ? 
   """
   cur.execute(sql, uvals)
   con.commit()

def update_calfile(cal_fn, con, cur, json_conf, mcp):

   cal_root = cal_fn.split("-")[0]
   cal_dir = "/mnt/ams2/cal/freecal/" + cal_root + "/"  
   cal_img_fn = cal_fn.replace("-calparams.json", ".png")
   if os.path.exists(cal_dir + cal_img_fn):
      cal_img = cv2.imread(cal_dir + cal_img_fn)
   if os.path.exists(cal_dir + cal_fn) is True:
      cal_params = load_json_file(cal_dir + cal_fn)
   else:   
      print(cal_dir + cal_fn + " NOT FOUND.")
      exit()

   cal_params['x_poly'] = mcp['x_poly']
   cal_params['y_poly'] = mcp['y_poly']
   cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
   cal_params['y_poly_fwd'] = mcp['y_poly_fwd']

   save_json_file(cal_dir + cal_fn, cal_params)

   sql = """UPDATE calibration_files SET az = ?, el = ?, ra = ?, dec = ?, position_angle = ?, pixel_scale = ?, x_poly = ?, y_poly = ?, x_poly_fwd = ?, y_poly_fwd = ?
            WHERE cal_fn = ?
   """

   uvals = [cal_params['center_az'], cal_params['center_el'], cal_params['ra_center'], cal_params['dec_center'], cal_params['position_angle'], cal_params['pixscale'], json.dumps(mcp['x_poly']), json.dumps(mcp['y_poly']), json.dumps(mcp['x_poly_fwd']), json.dumps(mcp['y_poly_fwd']), cal_fn ]
   #print(sql)
   #print(uvals)
   cur.execute(sql, uvals)

   sql = """
      SELECT station_id, camera_id, cal_fn, cal_ts, az, el, ra, dec, position_angle, pixel_scale, 
             zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, y_poly, x_poly_fwd, y_poly_fwd, 
             res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update
        FROM calibration_files WHERE cal_fn = ?
   """
   svals = [cal_fn]
   cur.execute(sql, svals)
   rows = cur.fetchall()
   #print(rows[0])


   # UPDATE THE CATALOG
   cat_stars, short_bright_stars,calibration_image = get_catalog_stars(cal_params)
   for star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
      desc = name + " " + str(mag)
      #cv2.putText(zp_star_chart_img, desc,  (zp_cat_x,zp_cat_y), cv2.FONT_HERSHEY_SIMPLEX, .4, (128,128,128), 1)
      cv2.line(cal_img, (int(new_cat_x),int(new_cat_y)), (int(zp_cat_x),int(zp_cat_y)), (255,255,255), 2)
      sql = """
               INSERT OR REPLACE INTO calfile_catalog_stars (
                      cal_fn,
                      name,
                      mag,
                      ra,
                      dec,
                      new_cat_x,
                      new_cat_y,
                      zp_cat_x,
                      zp_cat_y
               )
               VALUES (?,?,?,?,?,?,?,?,?)
      """
      ivals = [cal_fn, name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y]
      try:
         cur.execute(sql, ivals)
      except:
         print("Must be done already")
   con.commit()
   cv2.imshow("calview", cal_img)
   cv2.waitKey(60)

   # GET THE CURRENT STARS, UPDATE THE PAIRS BASED ON NEWLY LOADED CAT STAR POSITIONS
   sql = """
      SELECT cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope
        FROM calfile_paired_stars
       WHERE cal_fn = ?
   """
   svals = [cal_fn]
   #print(sql)
   #print(svals)
   cur.execute(sql, svals )

   # PAIR STARS AREA HERE..
   rows = cur.fetchall()
   all_good_stars = []
   for row in rows:
      cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope = row

      if new_cat_x is not None and new_cat_y is not None and img_x is not None and img_y is not None:
         res_px = calc_dist((img_x,img_y), (new_cat_x,new_cat_y))
      else:
         res_px = None

      #print(name, new_cat_x, new_cat_y, img_x, img_y, res_px)
      star_obj = {}
      star_obj['x'] = img_x
      star_obj['y'] = img_y
      star_obj['star_flux'] = star_flux
      star_obj['cal_fn'] = cal_fn 
      close_stars = find_close_stars(star_obj)

      pp = 1
      for cs in close_stars:
         (cal_fn, name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, \
            ximg_x, ximg_y, star_flux, star_yn, star_pd, star_found, lens_model_version, \
            slope, zp_slope, dist, zp_dist) = cs
         #if new_cat_x is None or new_cat_y is None or img_x is None or img_y is None:
         #   continue
         res_px = calc_dist((img_x,img_y), (new_cat_x,new_cat_y))
         zp_dist = calc_dist((img_x,img_y), (zp_cat_x,zp_cat_y))
         slope = (img_y - new_cat_y) / (img_x - new_cat_x)
         zp_slope = (img_y - zp_cat_y) / (img_x - zp_cat_x)

         #print("   CLOSE:", name, mag, new_cat_x, new_cat_y, img_x, img_y, res_px)

         if pp == 1:
            # UPDATE THE calfile_paired_stars table
            sql = """
               UPDATE calfile_paired_stars SET name = ?, 
                                               mag = ?,
                                               ra = ?,
                                               dec = ?,
                                               new_cat_x = ?,
                                               new_cat_y = ?,
                                               zp_cat_x = ?,
                                               zp_cat_y = ?,
                                               slope = ?,
                                               zp_slope = ?,
                                               res_px = ?,
                                               zp_res_px = ?
                                         WHERE cal_fn = ?
                                           AND img_x = ?
                                           AND img_y = ?
            """
            uvals = [name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, slope, zp_slope, res_px, zp_dist, cal_fn, img_x, img_y]
            cur.execute(sql, uvals)
            #print(sql)
            #print(uvals)
         pp += 1


def reload_calfile_catalog_stars(cal_fn, cal_params):

   sql = """
      DELETE FROM calfile_catalog_stars 
            WHERE cal_fn = ?
   """
   ivals = [cal_fn]
   cur.execute(sql, ivals)
   con.commit()

   cat_stars, short_bright_stars = get_catalog_stars(cal_params)
   for star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
      sql = """
               INSERT OR REPLACE INTO calfile_catalog_stars (
                      cal_fn,
                      name,
                      mag,
                      ra,
                      dec,
                      new_cat_x,
                      new_cat_y,
                      zp_cat_x,
                      zp_cat_y
               )
               VALUES (?,?,?,?,?,?,?,?,?)
      """
      ivals = [cal_fn, name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y]
      try:
         cur.execute(sql, ivals)
      except:
         print("Must be done already")
   con.commit()
   return(cat_stars, short_bright_stars)


def get_paired_stars(cal_fn, cal_params, con, cur):
   sql = """
      SELECT cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope
        FROM calfile_paired_stars
       WHERE cal_fn = ?
   """
   svals = [cal_fn]
   #print(sql)
   #print(svals)
   cur.execute(sql, svals )
   up_cat_image_stars = []
   # PAIR STARS AREA HERE..
   rows = cur.fetchall()
   stars = []
   for row in rows:
      cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope = row
      stars.append((cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope))

      # temp holder / fix later
      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params,json_conf)

      img_ra = img_ra
      img_dec = img_dec
      img_az = img_az
      img_el = img_el 
      if ra is not None and img_ra is not None:
         match_dist = angularSeparation(ra,dec,img_ra,img_dec)
      else:
         match_dist = 999


      cat_dist = res_px 
      if ra is not None:
         up_cat_image_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,zp_cat_x,zp_cat_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux)) 

   return(stars, up_cat_image_stars)


def get_image_stars(cal_image_file, con, cur, json_conf,force=False):

   print("CAL IMAGE_FILE", cal_image_file)

   if "/" in cal_image_file:
      cal_image_file = cal_image_file.split("/")[-1]

   """
      input : image file to extract stars from
     output : x,y,intensity of each point that 'passes' the star tests
   """

   cal_fn = cal_image_file.split("-")[0]


   zp_star_chart_img = np.zeros((1080,1920,3),dtype=np.uint8)
   star_chart_img = np.zeros((1080,1920,3),dtype=np.uint8)

   image_stars = []
   cv2.namedWindow("calview")
   cv2.resizeWindow("calview", 1920, 1080)
   # setup values
   cal_dir = cal_dir_from_file(cal_image_file)
   if cal_dir is False:
      print("Corrupted files or not named right.")
      return()


   cal_json_file = get_cal_json_file(cal_dir)
   cal_json_fn = cal_json_file.split("/")[-1]

   print("CAL FN:", cal_fn)
   print("CAL DIR:", cal_dir)
   print("CAL JSON", cal_json_file)
   print("CAL IMAGE", cal_dir + cal_image_file)

   resp = check_calibration_file(cal_json_fn, con, cur)
   if resp is True and force is False:
      print("SKIP DONE!")
      return() 
   if resp is False:
      insert_calib(cal_json_file, con, cur, json_conf)
      con.commit()
   print(cal_json_file)

   print("R", resp)

   # load the image
   if os.path.exists(cal_dir + cal_image_file) is True:
      cal_img = cv2.imread(cal_dir + cal_image_file)
      cal_img_orig = cal_img.copy()
   else:
      print("No image_file!")
      return(False) 


   if os.path.exists(cal_json_file) is True:
      cal_params = load_json_file(cal_json_file)
   else:
      return(False) 

   cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
   for star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
      desc = name + " " + str(mag)
      #cv2.putText(zp_star_chart_img, desc,  (zp_cat_x,zp_cat_y), cv2.FONT_HERSHEY_SIMPLEX, .4, (128,128,128), 1)
      cv2.line(zp_star_chart_img, (int(new_cat_x),int(new_cat_y)), (int(zp_cat_x),int(zp_cat_y)), (255,255,255), 2)
      sql = """
               INSERT INTO calfile_catalog_stars (
                      cal_fn,
                      name,
                      mag,
                      ra,
                      dec,
                      new_cat_x,
                      new_cat_y,
                      zp_cat_x,
                      zp_cat_y 
               ) 
               VALUES (?,?,?,?,?,?,?,?,?)
      """
      ivals = [cal_json_fn, name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y]
      try:
         cur.execute(sql, ivals)
      except:
         print("Must be done already")
   con.commit()
   cv2.imshow("calview", zp_star_chart_img)
   cv2.waitKey(30)

   gray_orig = cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)
   gray_img  = cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)
   show_img = cal_img.copy()
   cv2.imshow("calview", show_img)
   cv2.waitKey(30)

   # check top 100 brightest points in the image
   for i in range(0,200):
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_img)
      resp = make_star_roi(mx,my,32)
      sbx = mx
      sby = my
      status,x1,y1,x2,y2 = resp
      valid = False
      if status is True:
         crop_img = gray_orig[y1:y2,x1:x2]
         avg_val = np.mean(crop_img)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_img)
         pxd = max_val - avg_val 

         _, crop_thresh = cv2.threshold(crop_img, max_val * .85, 255, cv2.THRESH_BINARY)
         cv2.imshow('crop_thresh', crop_thresh)
    
         cnts = get_contours_in_image(crop_thresh)


         if pxd > 20 and len(cnts) == 1:
            valid = True

         if len(cnts) == 1:
            x,y,w,h = cnts[0]
            cx = x + (w/2)
            cy = y + (h/2)
            if w > h:
               radius = w
            else:
               radius = h
            try:
               star_flux = do_photo(crop_img, (cx,cy), radius)
            except:
               star_flux = 0
            if star_flux > 0:
               star_yn = ai_check_star(crop_img)
            else:
               star_yn = 0 
               valid = False
         else:
            valid = False


         if valid is True:

            print("FLUX / YN:", star_flux, star_yn)

            print("GOOD", cnts)
            star_obj = {}
            star_obj['cal_fn'] = cal_json_fn 
            star_obj['x'] = x1 + (x) + (w/2)
            star_obj['y'] = y1 + (y) + (h/2)
            star_obj['star_flux'] = star_flux
            star_obj['star_yn'] = star_yn
            star_obj['star_radius'] = radius
            image_stars.append(star_obj)
            desc = str(int(star_flux)) + " " + str(int(star_yn)) 
            if star_yn > 90:
               cv2.putText(show_img, desc,  (x1,y1), cv2.FONT_HERSHEY_SIMPLEX, .4, (128,128,128), 1)
               cv2.rectangle(show_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1)
            else:
               cv2.putText(show_img, desc,  (x1,y1), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,0), 1)
               cv2.rectangle(show_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 0, 0), 1)


            # Do an insert here into calfile_paired_stars table
            sql = """
               INSERT INTO calfile_paired_stars (
                           cal_fn, 
                           img_x, 
                           img_y, 
                           star_flux, 
                           star_yn, 
                           star_pd)
                    VALUES (?,?,?,?,?,?)
            """
            ivals = [cal_json_fn, star_obj['x'], star_obj['y'], star_flux, star_yn, pxd]
            print(sql)
            print(ivals)
            try:
               cur.execute(sql, ivals)
            except:
               print("Must be done already")


      gray_img[y1:y2,x1:x2] = 0
      cv2.imshow("calview", show_img)
      cv2.waitKey(10)

   cv2.waitKey(30)

   print("NOW LETS PAIR THE STARS!")
   for star_obj in image_stars:
      
      cal_fn = star_obj['cal_fn']
      x = star_obj['x']
      y = star_obj['y']
      star_flux = star_obj['star_flux']
      close_stars = find_close_stars(star_obj)

      pp = 1
      if len(close_stars) == 0:
         cv2.putText(show_img, "X",  (int(x + 5),int(y + 5)), cv2.FONT_HERSHEY_SIMPLEX, .5, (0,0,128), 2)
         continue

      for pstar in close_stars:
         (cal_fn, name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, \
         img_x, img_y, cat_star_flux, star_yn, star_pd, star_found, lens_model_version, \
         slope, zp_slope, dist, zp_dist) = pstar

         print("POSSIBLE STAR:", zp_cat_x, zp_cat_y)
        
         desc = str(int(mag))
         cv2.putText(show_img, desc,  (int(zp_cat_x+20),int(zp_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .5, (128,128,128), 2)
         cv2.line(show_img, (int(zp_cat_x),int(zp_cat_y)), (int(x),int(y)), (128,128,128), 2)
         if pp == 1:
            # UPDATE THE calfile_paired_stars table
            res_px = calc_dist((x,y), (new_cat_x,new_cat_y))
            sql = """
               UPDATE calfile_paired_stars SET name = ?, 
                                               mag = ?,
                                               ra = ?,
                                               dec = ?,
                                               new_cat_x = ?,
                                               new_cat_y = ?,
                                               zp_cat_x = ?,
                                               zp_cat_y = ?,
                                               slope = ?,
                                               zp_slope = ?,
                                               res_px = ?,
                                               zp_res_px = ?
                                         WHERE cal_fn = ?
                                           AND img_x = ?
                                           AND img_y = ?
            """
            uvals = [name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, slope, zp_slope, res_px, zp_dist, cal_json_fn, x, y]
            cur.execute(sql, uvals)
            #print(sql)
            #print(uvals)
            #cv2.line(cal_img_orig, (int(new_cat_x),int(new_cat_y)), (int(zp_cat_x),int(zp_cat_y)), (255,255,255), 2)



            #cv2.line(show_img, (int(new_cat_x),int(new_cat_y)), (int(x),int(y)), (0,128,0), 1)
            cv2.line(show_img, (int(new_cat_x),int(new_cat_y)), (int(x),int(y)), (203,192,255), 1)

         # extra close stars that are not choosen
         #else:
         #   if img_x is not None:
         #      cv2.putText(show_img, "X",  (int(img_x),int(img_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
         #   cv2.line(show_img, (int(new_cat_x),int(new_cat_y)), (int(x),int(y)), (203,192,255), 1)
         cv2.imshow("calview", show_img)
         cv2.waitKey(30)
         pp += 1



      print("IMG STAR:", star_obj['x'], star_obj['y'])
   cv2.waitKey(30)
   con.commit()


#   calib_info = get_calibration_file()

def insert_paired_star(cal_fn, star_obj, con, cur, json_conf):
   # Do an insert here into calfile_paired_stars table
   sql = """
               INSERT OR REPLACE INTO calfile_paired_stars (
                           cal_fn,
                           name,
                           mag,
                           ra,
                           dec,
                           new_cat_x,
                           new_cat_y,
                           zp_cat_x,
                           zp_cat_y,
                           img_x,
                           img_y,
                           star_flux,
                           star_yn,
                           star_pd,
                           star_found,
                           lens_model_version,
                           slope,
                           zp_slope,
                           res_px,
                           zp_res_px,
                           res_deg
                           )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
   """

   ivals = [star_obj["cal_fn"], star_obj["name"], star_obj["mag"], star_obj["ra"], star_obj["dec"], star_obj["new_cat_x"], star_obj["new_cat_y"], star_obj["zp_cat_x"], star_obj["zp_cat_y"], star_obj["img_x"], star_obj["img_y"], star_obj["star_flux"], star_obj["star_yn"], star_obj["star_pd"], 1, star_obj["lens_model_version"], star_obj["slope"], star_obj["zp_slope"], star_obj["res_px"], star_obj["zp_res_px"], star_obj["res_deg"]]

   #print(sql)
   #print(ivals)
   try:
      cur.execute(sql, ivals)
      con.commit()
   except:
      print("record already exists.")

def check_calibration_file(cal_fn, con, cur):
   sql = "SELECT cal_fn FROM calibration_files where cal_fn = ?"
   uvals = [cal_fn]
   cur.execute(sql, uvals)
   #print(sql, cal_fn)
   rows = cur.fetchall()
   #print(rows)
   if len(rows) > 0:
      return(True)
   else:
      return(False)


def find_stars_with_catalog(cal_fn, con, cur, json_conf,mcp=None):
   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)
   font = ImageFont.truetype("/usr/share/fonts/truetype/DejaVuSans.ttf", 20, encoding="unic" )
   print("VIEW CAL:", cal_fn)
   cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf,None, None, mcp )

   if cal_img is False:
      print("FAILED FIND")
      return()
   help_img = make_help_img(cal_img)
   interval = .1

   cal_img_fn = cal_fn.replace("-calparams.json", ".png")
   cal_image_file = cal_fn.replace("-calparams.json", ".png")
   cal_dir = cal_dir_from_file(cal_image_file)
   cal_json_file = get_cal_json_file(cal_dir)
   cal_json_fn = cal_json_file.split("/")[-1]
   if os.path.exists(cal_dir + cal_img_fn):
      clean_cal_img = cv2.imread(cal_dir + cal_img_fn)

   mask_file = "/mnt/ams2/meteor_archive/{}/CAL/MASKS/{}_mask.png".format(station_id, cam_id)
   print("MASK:", mask_file)
   if os.path.exists(mask_file) is True:
      mask = cv2.imread(mask_file)
      #mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
      mask = cv2.resize(mask, (1920,1080))
   else:
      mask = np.zeros((1080,1920),dtype=np.uint8)
   print(mask.shape)
   print(clean_cal_img.shape)
   clean_cal_img = cv2.subtract(clean_cal_img, mask)

   cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)

   good_stars = []
   star_objs = []
   for star in cat_stars[0:100]:
      name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y = star
      mcx1 = int(new_cat_x - 25)
      mcx2 = int(new_cat_x + 25)
      mcy1 = int(new_cat_y - 25)
      mcy2 = int(new_cat_y + 25)
      if mcx1 < 0 or mcx2 > 1920 or mcy1 < 0 or mcy2 > 1080:
         continue
      crop_img = clean_cal_img[mcy1:mcy2,mcx1:mcx2]
      # 10x bigger
      show_img = clean_cal_img.copy()
      cv2.rectangle(show_img, (int(mcx1), int(mcy1)), (int(mcx2) , int(mcy2) ), (255, 255, 255), 1)
      crop_img_big = cv2.resize(crop_img, (500,500))
      star_obj = eval_star_crop(crop_img, cal_fn, mcx1, mcx2, mcy1, mcy2)
      #print(resp)


      show_image_pil = Image.fromarray(show_img)
      show_image_draw = ImageDraw.Draw(show_image_pil)

      crop_image_pil = Image.fromarray(crop_img_big)
      crop_image_draw = ImageDraw.Draw(crop_image_pil)
    
      crop_text = "Star: {} Mag: {} X/Y {}/{}".format(name, mag , str(int(new_cat_x)), str(int(new_cat_y)))
      crop_text2 = "YN: {} Flux: {}".format(str(int(star_obj['star_yn'])) + "%", str(int(star_obj['star_flux'])))
    
      crop_image_draw.text((20, 10), str(crop_text), font = font, fill="white")
      crop_image_draw.text((20, 475), str(crop_text2), font = font, fill="white")

      crop_img_big = cv2.cvtColor(np.asarray(crop_image_pil), cv2.COLOR_RGB2BGR)

      if len(star_obj['cnts']) == 1:
         cx1 = star_obj['cnts'][0][0] * 10
         cy1 = star_obj['cnts'][0][1] * 10
         cx2 = cx1 + (star_obj['cnts'][0][2] * 10)
         cy2 = cy1 + (star_obj['cnts'][0][3] * 10)

         ccx = int((cx1 + cx2) / 2)
         ccy = int((cy1 + cy2) / 2)

         six = mcx1 + (ccx/10)
         siy = mcy1 + (ccy/10)

         print("************* CROP:", cx1,cy1, cx2, cy2)
         cv2.rectangle(crop_img_big, (int(cx1), int(cy1)), (int(cx2) , int(cy2) ), (0, 0, 255), 2)
         print("CCX:", ccx, ccy)
         cv2.circle(crop_img_big, (int(ccx),int(ccy )), star_obj['radius']* 10, (0,69,255),1)

         cv2.line(crop_img_big, (int(250),int(0)), (int(250),int(500)), (255,255,255), 1)
         cv2.line(crop_img_big, (int(0),int(250)), (int(500),int(250)), (255,255,255), 1)

         cv2.line(crop_img_big, (int(250),int(250)), (ccx,ccy), (255,255,255), 1)

      if star_obj['valid_star'] is False:
         cv2.rectangle(crop_img_big, (int(0), int(0)), (int(499) , int(499) ), (0, 0, 255), 2)
      else:
         cv2.rectangle(crop_img_big, (int(0), int(0)), (int(499) , int(499) ), (0, 255, 0), 2)
         # GOOD STAR
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_fn,cal_params,json_conf)

         match_dist = angularSeparation(ra,dec,img_ra,img_dec)
         cat_dist = calc_dist((six,siy),(new_cat_x,new_cat_y))
         center_dist = calc_dist((960,540),(new_cat_x,new_cat_y))
         good_stars.append(( name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_obj['star_flux'] ))
         star_obj['star_name'] = name
         star_obj['mag'] = mag 
         star_obj['ra'] = ra
         star_obj['dec'] = dec
         star_obj['img_ra'] = img_ra
         star_obj['img_dec'] = img_dec
         star_obj['img_az'] = img_az
         star_obj['img_el'] = img_el
         star_obj['proj_x'] = new_x
         star_obj['proj_y'] = new_y
         star_obj['cat_x'] = new_cat_x
         star_obj['cat_y'] = new_cat_y
         star_obj['img_x'] = six 
         star_obj['img_y'] = siy 
         star_obj['center_dist'] = int(center_dist)
         star_obj['total_res_deg'] = match_dist
         star_obj['total_res_px'] = cat_dist 
         #star_obj['grid_square'] = grid_square 
         #star_obj['quad'] = quad
         star_objs.append(star_obj)



      cv2.imshow('pepe', crop_img_big)
      cv2.imshow('pepe_main', show_img)
      cv2.waitKey(30)

   show_img = clean_cal_img.copy()

   print("MAG TABLE!")
   star_objs = sorted(star_objs, key=lambda x: x['mag'], reverse=False)
   for so in  star_objs:
      if so['star_name'] == "":
         name = "---"
      else:
         name = so['star_name']
      #print("STAR:", name, so['mag'], so['star_flux'], so['center_dist'], round(so['total_res_deg'],2), round(so['total_res_px'],2), so['star_yn'] )

   star_obj_report(star_objs)
   #print("DIST TABLE!")
   #for star in good_stars:
   #   name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_flux = star
   #   center_dist = int(calc_dist((960,540),(new_cat_x,new_cat_y)))
   #   print("STAR:", name, center_dist, match_dist, cat_dist)


   cv2.imshow('pepe_main', show_img)
   cv2.waitKey(30)


def cal_params_report(cal_fn, cal_params,json_conf, show_img, waitVal=30, mcp=None):
   from prettytable import PrettyTable as pt   

   cal_params_nlm = cal_params.copy()
   cal_params_nlm['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   
   tb = pt()
   tb.field_names = ["Star","Magnitude", "Flux", "RA", "Dec", "Cat X", "Cat Y", "Img X", "Img Y", "Res PX", "Res Deg"]
   #print("CAL PARAMS FOR {}".format(cal_fn))
   res_pxs = []
   res_degs = []
   zp_res_pxs = []
   zp_res_degs = []
   new_cat_image_stars = []
   center_res_pxs = []

   for star in cal_params['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
      new_cat_x, new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)

      # with the best lens model 
      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_fn,cal_params,json_conf)

      # with NO lens model 
      zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(six,siy,cal_fn,cal_params_nlm,json_conf)
      zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, ra, dec)

      cat_dist = calc_dist((six,siy),(new_cat_x,new_cat_y))
      match_dist = angularSeparation(ra,dec,img_ra,img_dec)

      zp_cat_dist = calc_dist((six,siy),(zp_x,zp_y))
      zp_match_dist = angularSeparation(ra,dec,zp_img_ra,zp_img_dec)


      res_pxs.append(cat_dist)
      res_degs.append(match_dist)

      zp_res_pxs.append(zp_cat_dist)
      zp_res_degs.append(zp_match_dist)
      center_dist = calc_dist((six,siy),(1920/2,1080/2))

      if center_dist < 600:
         center_res_pxs.append(cat_dist)


      # image star point (yellow)
      cv2.circle(show_img, (int(six),int(siy)), 3, ( 0, 234, 255),1)

      # Projected image star point 
      cv2.putText(show_img, "+",  (int(new_x-5),int(new_y+4)), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
      cv2.circle(show_img, (int(new_x),int(new_y)), 3, (255,69,255),1)

      # corrected catalog star point using lens model
      cv2.rectangle(show_img, (int(new_cat_x - 7), int(new_cat_y-7)), (int(new_cat_x+7) , int(new_cat_y+7) ), (255, 255, 255), 1)

      # zero poly catalog star point ( no lens model)
      cv2.rectangle(show_img, (int(zp_cat_x - 5), int(zp_cat_y-5)), (int(zp_cat_x+5) , int(zp_cat_y+5) ), (0, 0, 255), 1)

      tb.add_row([dcname, round(mag,2), int(bp), round(ra,2), round(dec,2), round(new_cat_x,2), round(new_cat_y,2), round(six,2), round(siy,2), round(cat_dist,2), round(match_dist,2)])
      new_cat_image_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp ))

   cv2.circle(show_img, (int(1920/2),int(1080/2)), 400, (128,128,128),1)
   cv2.circle(show_img, (int(1920/2),int(1080/2)), 800, (128,128,128),1)

   mean_center_res = np.mean(center_res_pxs)
   cal_params['mean_center_res'] = mean_center_res
   #print(tb)
   report_txt = str(tb)
   tb = pt()
   tb.field_names = ["Cal Paramater","Value"]
   # CENTER ??
   cal_params['total_res_px'] = mean_center_res
   #cal_params['total_res_px'] = np.mean(res_pxs)
   cal_params['total_res_deg'] = np.mean(res_degs)
   tb.add_row(["Center RA", cal_params['ra_center']] )
   tb.add_row(["Center Dec", cal_params['dec_center']])
   tb.add_row(["Center Az", cal_params['center_az']])
   tb.add_row(["Center El", cal_params['center_el']])
   tb.add_row(["Pixel Scale", cal_params['pixscale']])
   tb.add_row(["Residuals (Px)", cal_params['total_res_px']])
   tb.add_row(["Residuals (Deg)", cal_params['total_res_deg']])
   tb.add_row(["Residuals (Cnt PX)", cal_params['mean_center_res']])
   #print(tb)
   report_txt += str(tb)
   desc = "Stars: {} Res PX: {} Res Deg: {}".format(len(cal_params['cat_image_stars']), round(cal_params['total_res_px'],3), round(cal_params['total_res_deg'],3))
   cv2.putText(show_img, desc,  (int(10),int(1060)), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)

   cal_params['cat_image_stars'] = new_cat_image_stars
   cv2.imshow('pepe', show_img)
   cv2.waitKey(waitVal)

   return(cal_params, report_txt, show_img)


def star_obj_report(star_objs):
   #pip install prettytable
   from prettytable import PrettyTable as pt   
   tb = pt()
   tb.field_names = ["Star","Magnitude","Flux","Cen Dist", "Res Deg", "Res PX", "AI YN", "CRR"]

   star_objs = sorted(star_objs, key=lambda x: x['mag'], reverse=False)
   for so in  star_objs:
      if so['star_name'] == "":
         so['star_name'] = "---"
      center_res_ratio = round(so['total_res_px'] / so['center_dist'] , 2)
      tb.add_row([so['star_name'], so['mag'], round(so['star_flux'],2), so['center_dist'], round(so['total_res_deg'],3), round(so['total_res_px'],3), so['star_yn'], center_res_ratio])
   print(tb)


def eval_star_crop(crop_img, cal_fn, x1, y1,x2,y2, star_cat_info=None ):
   learn_dir = "/mnt/ams2/datasets/cal_stars/"
   if os.path.exists(learn_dir) is False:
      os.makedirs(learn_dir)
   roi_end = "_" + str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2)
   star_key= cal_fn.replace("-stacked-calparams.json", roi_end)

   star_img_file = learn_dir + star_key + ".jpg"
   star_data_file = learn_dir + star_key + ".json"
   if os.path.exists(star_data_file) is True:
      #print("STAR KEY:", star_key)
      #print("STAR img:", star_img_file)
      #print("STAR data:", star_data_file)
      #print("FOUND!")
      try:
         return(load_json_file(star_data_file))
      except:
         print("error")    
   #else:
   #   print("STAR data NOT FOUND!:", star_data_file)

   cv2.imwrite(star_img_file,crop_img)

   radius = 0
   star_flux = 0
   valid_star = True 
   gray_img  = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
   gray_orig = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
   show_img = crop_img.copy()
   cx = 0
   cy = 0

   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_img)
   avg_val = np.mean(crop_img)
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_img)
   pxd = max_val - avg_val

   #thresh_val = avg_val + (pxd / 2)
   thresh_val = max_val * .9
   if pxd < 20:
      thresh_val = max_val - 3 
   if pxd < 15:
      thresh_val = max_val - 2 

   _, crop_thresh = cv2.threshold(crop_img, thresh_val, 255, cv2.THRESH_BINARY)

   cnts = get_contours_in_image(crop_thresh)

   if len(cnts) == 1:
      x,y,w,h = cnts[0]
      cx = x + (w/2)
      cy = y + (h/2)
      if w > h:
         radius = int(w / 2)
      else:
         radius = int(h / 2)
      try:
         star_flux = do_photo(gray_img, (cx,cy), radius)
      except:
         star_flux = 0
   #else:
   #   cv2.imshow('thresh', crop_thresh)

   if star_flux > 0:
      star_yn = ai_check_star(crop_img, star_img_file)
   else:
      star_yn = 0
      valid = False

   if pxd > 8 and (len(cnts) == 1 or star_yn > 50):
      valid = True
   else:
      valid = False

   # return : cnts, star_flux, pxd, star_yn, radius
   star_obj = {}
   star_obj['cnts'] = cnts
   star_obj['star_flux'] = round(star_flux,2)
   star_obj['pxd'] = int(pxd)
   star_obj['brightest_point'] = [mx,my]
   star_obj['brightest_val'] = int(max_val)
   star_obj['bg_avg'] = int(avg_val)
   star_obj['star_yn'] = int(star_yn)
   star_obj['radius'] = radius
   star_obj['valid_star'] = valid
   star_obj['thresh_val'] = thresh_val
   star_obj['cx'] = cx 
   star_obj['cy'] = cy
   if star_cat_info is not None:
      name, mag, ra,dec = star_cat_info
      star_obj['name'] = name
      star_obj['mag'] = mag 
      star_obj['ra'] = ra
      star_obj['dec'] = dec

   #for key in star_obj:
   #   print(key, star_obj[key])

   #star_obj['crop_thresh'] = crop_thresh

   save_json_file(star_data_file, star_obj)
   print("SAVED:", star_data_file)
   return ( star_obj)

def find_close_stars(star_obj):
   cal_fn = star_obj['cal_fn']
   x = star_obj['x']
   y = star_obj['y']
   star_flux = star_obj['star_flux']
   sql = """
      SELECT cal_fn, name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, 
             img_x, img_y, star_flux, star_yn, star_pd, star_found, lens_model_version 
        FROM calfile_catalog_stars
       WHERE cal_fn = ?
         AND (new_cat_x > ? and new_cat_x < ?)
         AND (new_cat_y > ? and new_cat_y < ?)
   """

   center_dist = calc_dist((x,y),(1920/2,1080/2))
   if center_dist < 800:
      x1 = x - 50
      x2 = x + 50
      y1 = y - 50
      y2 = y + 50
   else:
      x1 = x - 75 
      x2 = x + 75
      y1 = y - 75
      y2 = y + 75

   # Adjust search box based on where the img star is
   # right side image, cat must be greater than source!
   if x > 1620:
      x1 = x 
      x2 = x1 + 50 
   # left side image, cat must be greater than source!
   if x < 300:
      x2 = x 
      x1 = x2 - 50 

   ivals = [cal_fn, x1, x2, y1, y2]
   cur.execute(sql, ivals)
   rows = cur.fetchall()
   stars = []
   for row in rows:
      cal_fn, name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, \
         img_x, img_y, cat_star_flux, star_yn, star_pd, star_found, lens_model_version  = row

      slope = (y - new_cat_y) / (x - new_cat_x)
      zp_slope = (y - zp_cat_y) / (x - zp_cat_x)
      dist = calc_dist((x,y),(new_cat_x,new_cat_y))
      zp_dist = calc_dist((x,y),(zp_cat_x,zp_cat_y))


      valid = True

      if center_dist > 600:
         if x < 600 and y < 400: # top left corner
            if new_cat_x > x:
               valid = False
            if new_cat_y > y:
               valid = False
         if x < 600 and y > 1080 - 400: # bottom left corner
            if new_cat_x > x:
               valid = False
            if new_cat_y < y:
               valid = False
         if x > 1920 - 600 and y < 400: # top right corner
            if new_cat_x < x:
               valid = False
            if new_cat_y > y:
               valid = False
         if x > 1920 - 600 and y > 1080- 400: # bottom right corner
            if new_cat_x < x:
               valid = False
            if new_cat_y < y:
               valid = False
         
         # y_dist should not be more than x_dist on edge
         y_dist = abs(new_cat_y - y)
         x_dist = abs(new_cat_x - x)
         if y_dist > x_dist:
            valid = False

      if star_flux is None:
         valid = False
      elif star_flux > 1000 and mag >= 4:
         valid = False
      if center_dist < 600:
         if zp_dist > 25:
            valid = False 

      if valid is True:
         stars.append(( cal_fn, name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, \
            img_x, img_y, star_flux, star_yn, star_pd, star_found, lens_model_version, \
            slope, zp_slope, dist, zp_dist))

   stars = sorted(stars, key=lambda x: x[-2], reverse=False)

   return(stars)

#def cal_main(cal_file):
#   print("Menu")

   # GET IMAGE STARS IS DONE. 

   # GET CATALOG STARS


def get_best_cal_files(cam_id, con, cur, json_conf, limit=10):
   sql = """
      SELECT cal_fn, count(*) AS ss, avg(res_px) as rs 
        FROM calfile_paired_stars 
       WHERE cal_fn like ?
         AND res_px IS NOT NULL
    GROUP BY cal_fn 
    ORDER BY ss desc, rs
    LIMIT ? 
   """
   dvals = ["%" + cam_id + "%", limit]
   cur.execute(sql, dvals)
   rows = cur.fetchall()
   best = []
   best_dict = {}
   for row in rows:
      x_cal_fn, total_stars, avg_res = row
      best.append((x_cal_fn, total_stars, avg_res))
      best_dict[x_cal_fn] = [x_cal_fn,total_stars,avg_res]
   return(best, best_dict)


def characterize_best(cam_id, con, cur, json_conf,limit=800, cal_fns=None):
   #(f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)
   # best 
   calfiles_data  = load_cal_files(cam_id, con,cur)

   autocal_dir = "/mnt/ams2/cal/"
   mcp_file = autocal_dir + "multi_poly-" + json_conf['site']['ams_id'] + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
      mcp['cal_version'] += 1
   else:
      mcp = None


   station_id = json_conf['site']['ams_id']
   all_cal_files, best_dict = get_best_cal_files(cam_id, con, cur, json_conf)

   sql = """
      SELECT cal_fn, count(*) AS ss, avg(res_px) as rs 
        FROM calfile_paired_stars 
       WHERE cal_fn like ?
         AND res_px IS NOT NULL
    GROUP BY cal_fn 
    ORDER BY ss desc, rs
    LIMIT {}
   """.format(limit)
   dvals = ["%" + cam_id + "%"]
   #print(sql)
   #print(dvals)
   cur.execute(sql, dvals)
   rows = cur.fetchall()

   for row in rows:
      print(row)
   if len(rows) == 0:
      print("FAILED no rows")
      exit()

   print("CHAR ROWS:", len(rows))
   updated_stars = []
   updated_stars_zp = []
   res_0 = []
   res_200 = []
   res_400 = []
   res_600 = []
   res_800 = []
   res_900 = []
   res_1000 = []
   
   #for cal_fn in best_dict:
   #if cal_fns is not None:
   #   rows = cal_fns
   for row in rows:
      #print("ROW:", row)
      if row[2] is None:
         continue
      cal_fn = row[0]

      resp = start_calib(cal_fn, json_conf, calfiles_data, mcp)

      if resp is not False:
         (station_id, cal_dir, cal_json_file, cal_img_file, cal_params, cal_img, clean_cal_img, mask_file,mcp) = resp
      else:
         print("STAR CALIB FAILED:", cal_fn)
         continue 


      stars,cat_stars = get_paired_stars(cal_fn, cal_params, con, cur)

      cal_params_nlm = cal_params.copy()
      cal_params_nlm['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)


      for star in cat_stars:
         (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = star
         new_cat_x, new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params,json_conf)

         zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, ra, dec)
         zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params_nlm,json_conf)

         match_dist = angularSeparation(ra,dec,img_ra,img_dec)
         res_px = calc_dist((img_x,img_y),(new_cat_x,new_cat_y))

         zp_match_dist = angularSeparation(ra,dec,img_ra,img_dec)
         zp_res_px = calc_dist((img_x,img_y),(zp_cat_x,zp_cat_y))

         zp_center_dist = calc_dist((1920/2,1080/2),(zp_cat_x,zp_cat_y))
         if zp_center_dist < 200:
            res_0.append(zp_res_px)
         if 200 <= zp_center_dist < 400:
            res_200.append(zp_res_px)
         if 400 <= zp_center_dist < 600:
            res_400.append(zp_res_px)
         if 600 <= zp_center_dist < 800:
            res_600.append(zp_res_px)
         if 800 <= zp_center_dist < 900:
            res_800.append(zp_res_px)
         if 900 <= zp_center_dist < 1000:
            res_900.append(zp_res_px)
         if zp_center_dist >= 1000:
            res_1000.append(zp_res_px)

         updated_stars.append((cal_fn,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux))
         updated_stars_zp.append((cal_fn,dcname,mag,ra,dec,zp_img_ra,zp_img_dec,zp_match_dist,zp_x,zp_y,zp_img_az,zp_img_el,zp_cat_x,zp_cat_y,img_x,img_y,zp_res_px,star_flux))


         #print("NEW/ZP:", new_cat_x, zp_cat_x, new_cat_y, zp_cat_y)
         #print("ZP CENTER/RES:", zp_center_dist, zp_res_px)

      #plot_star_chart(clean_cal_img, updated_stars, updated_stars_zp)

   print("RES ZONES:")
   print("0-200", np.median(res_0))
   print("200-400", np.median(res_200))
   print("400-600", np.median(res_400))
   print("600-800", np.median(res_600))
   print("800-900", np.median(res_800))
   print("900-1000", np.median(res_900))
   print("1000+", np.median(res_1000))

   try:
      base_image = clean_cal_img.copy()
   except:
      base_image = np.zeros((1080,1920,3),dtype=np.uint8)

   if False:
      cv2.circle(base_image, (int(1920/2),int(1080/2)), 200, (128,128,128),1)
      cv2.circle(base_image, (int(1920/2),int(1080/2)), 400, (128,128,128),1)
      cv2.circle(base_image, (int(1920/2),int(1080/2)), 600, (128,128,128),1)
      cv2.circle(base_image, (int(1920/2),int(1080/2)), 800, (128,128,128),1)
      cv2.circle(base_image, (int(1920/2),int(1080/2)), 900, (128,128,128),1)
      cv2.circle(base_image, (int(1920/2),int(1080/2)), 1000, (128,128,128),1)

      cv2.putText(base_image, str(int(np.median(res_0))),  (960,540), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
      cv2.putText(base_image, str(int(np.median(res_200))),  (720,400), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
      cv2.putText(base_image, str(int(np.median(res_400))),  (550,300), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
      cv2.putText(base_image, str(int(np.median(res_600))),  (350,195), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
      cv2.putText(base_image, str(int(np.median(res_800))),  (200,115), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
      cv2.putText(base_image, str(int(np.median(res_900))),  (125,60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
      cv2.putText(base_image, str(int(np.median(res_1000))),  (55,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)

      cv2.line(base_image, (int(0),int(0)), (int(1920/2),int(1080/2)), [255,255,255], 1)
   best_stars = []

   ic = 0
   for star in updated_stars_zp:
      (cal_fn,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,zp_cat_x,zp_cat_y,img_x,img_y,res_px,star_flux) = star
      if True:
         zp_center_dist = calc_dist((1920/2,1080/2),(zp_cat_x,zp_cat_y))
         if zp_center_dist < 200:
            limit = np.median(res_0)
         if 200 <= zp_center_dist < 400:
            limit = np.median(res_200)
         if 400 <= zp_center_dist < 600:
            limit = np.median(res_400)
         if 600 <= zp_center_dist < 800:
            limit = np.median(res_600)
         if 800 <= zp_center_dist < 900:
            limit = np.median(res_800)
         if 900 <= zp_center_dist < 1000:
            limit = np.median(res_900)
         if zp_center_dist >= 1000:
            limit = np.median(res_1000)

      fact = res_px / limit
      print("F:", res_px, limit, fact)
      if .75 <= fact <= 1.25:
      #if True:
         #cv2.putText(base_image, str(int(res_px)),  (int(new_x),int(new_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,255,0), 1)
         cv2.line(base_image, (int(zp_cat_x),int(zp_cat_y)), (int(img_x),int(img_y)), (0,255,0), 2)
         (cal_fn,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = updated_stars[ic]
         best_stars.append((cal_fn,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,zp_cat_x,zp_cat_y,img_x,img_y,res_px,star_flux)) 
      #else:
      #   cv2.putText(base_image, str(int(res_px)),  (int(new_x),int(new_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
      ic += 1

   if SHOW == 1:
      cv2.imshow('pepe', base_image)
      cv2.waitKey(00)


   print("CAM ID:", cam_id)

   merged_stars = []
   rez = [row[-2] for row in best_stars] 
   med_rez = np.median(rez)

   for star in best_stars:

      (cal_fn, name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,zp_cat_x,zp_cat_y,img_x,img_y,res_px,star_flux) = star
      #if cal_fn not in best_dict:
         #print("MISSING CAL FN!", cal_fn)
      #   continue

      if cal_fn in calfiles_data:
         #(cal_fn_ex, center_az,center_el, ra_center,dec_center, position_angle, pixscale) = calfiles_data[cal_fn]
         (station_id, camera_id, cal_fn, cal_ts, center_az, center_el, ra_center, dec_center, position_angle,\
            pixscale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
            y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) = calfiles_data[cal_fn]


      #match_dist = zp_res_px

      match_dist = 9999
      if res_px < med_rez: 
         print("KEEP", res_px, med_rez)
         merged_stars.append((cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,center_az,center_el,new_cat_x,new_cat_y,img_x,img_y,zp_res_px,star_flux))
      else:
         print("SKIP", res_px, med_rez)

   grid_stars = make_grid_stars(merged_stars, mpc = None, factor = 2, gsize=50, limit=10)


   save_json_file("/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json", merged_stars)
   print("SAVED STARS FOR MODEL! /mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json", len(merged_stars), "stars")


def plot_star_chart(base_image, cat_stars, zp_cat_stars):
   for star in zp_cat_stars:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = star

      cv2.circle(base_image, (int(img_x),int(img_y)), 4, (135,247,252),1) # yellow

      cv2.circle(base_image, (int(new_x),int(new_y)), 4, (0,0,200),1)
      #cv2.circle(base_image, (int(new_cat_x),int(new_cat_y)), 4, (0,255,255),1)

      x1 = new_cat_x - 4 
      x2 = new_cat_x + 4 
      y1 = new_cat_y - 4 
      y2 = new_cat_y + 4 
      cv2.rectangle(base_image, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 0, 200), 1)


   for star in cat_stars:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = star
      cv2.circle(base_image, (int(new_x),int(new_y)), 3, (0,68,255),1)
      #cv2.circle(base_image, (int(new_cat_x),int(new_cat_y)), 3, (0,0,255),1)

      x1 = new_cat_x - 5
      x2 = new_cat_x + 5
      y1 = new_cat_y - 5
      y2 = new_cat_y + 5
      cv2.rectangle(base_image, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1)


   cv2.circle(base_image, (int(1920/2),int(1080/2)), 200, (128,128,128),1)
   cv2.circle(base_image, (int(1920/2),int(1080/2)), 400, (128,128,128),1)
   cv2.circle(base_image, (int(1920/2),int(1080/2)), 600, (128,128,128),1)
   cv2.circle(base_image, (int(1920/2),int(1080/2)), 800, (128,128,128),1)
   cv2.circle(base_image, (int(1920/2),int(1080/2)), 1000, (128,128,128),1)

   if SHOW == 1:
      cv2.imshow('pepe', base_image)
      cv2.waitKey(30)


def characterize_fov(cam_id, con, cur, json_conf):

   best_cal_files, best_dict = get_best_cal_files(cam_id, con, cur, json_conf, 400)

   station_id = json_conf['site']['ams_id']
   import matplotlib.pyplot as plt
   grid_img = np.zeros((1080,1920,3),dtype=np.uint8)
   # flux / mag
   sql = """
      SELECT cal_fn, star_flux, mag 
        FROM calfile_paired_stars
       WHERE star_flux is not NULL
         AND star_yn >= 99
         and cal_fn like ?
   """
   mag_db = {}
   med_flux_db = {}

   cur.execute(sql, [ "%" + cam_id + "%"])
   rows = cur.fetchall()
   xs = []
   ys = []
   for row in rows:
      cal_fn, flx, mag = row
      if mag is None:
         continue
      if mag not in mag_db:
         mag_db[mag] = []
      mag_db[mag].append(flx)

   for mag in sorted(mag_db):
      med_flux = np.median(mag_db[mag])
      mean_flux = np.mean(mag_db[mag])
      med_flux_db[mag] = med_flux
      num_samples = len(mag_db[mag])
      #print(mag, num_samples, mean_flux, med_flux)
      xs.append(mag)
      ys.append(mean_flux)

   plt.plot(xs,ys)
   plt.show()

   # determine the avg, min, max zp_dist and zp_slope for each grid in the image!
   grid_size = 100
   grid_data = {}
   for y in range(0,1080) :
      if y == 0 or y % 100 == 0:
         for x in range(0,1920):
            if x == 0 or x % 100 == 0:
               x1 = x
               y1 = y
               x2 = x + grid_size
               y2 = y + grid_size


               sql = """
                  SELECT cal_fn, zp_res_px, zp_slope 
                    FROM calfile_paired_stars 
                   WHERE img_x > ? and img_x < ? 
                     AND img_y > ? and img_y < ?
                     AND zp_res_px is NOT NULL
                     AND cal_fn like ?
               """
               uvals = [x1,x2,y1,y2, "%" + cam_id + "%" ]
               cur.execute(sql, uvals)
               rows = cur.fetchall()
               dist_vals = []
               slope_vals = []
               for row in rows:
                  cal_fn = row[0] 
                  if cal_fn not in best_dict:
                     continue

                  dist_val = row[1] 
                  slope_val = row[2] 
                  dist_vals.append(dist_val)
                  slope_vals.append(slope_val)

               if len(dist_vals) > 2:
                  med_d_val = np.median(dist_vals)
                  mean_d_val = np.mean(dist_vals)
               else:
                  med_d_val = None
                  mean_d_val = None
               if len(slope_vals) > 2:
                  med_s_val = np.median(slope_vals)
                  mean_s_val = np.mean(slope_vals)
               else:
                  med_s_val = None
                  mean_s_val = None

               med_dist = med_d_val
               if mean_s_val is None:
                  cv2.rectangle(grid_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1)
               elif mean_s_val < 0: 
                  cv2.rectangle(grid_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 255, 0), 1)
               else:
                  cv2.rectangle(grid_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 0, 255), 1)

               if med_dist is not None:
                  desc = str(int(med_dist)) + " " + str(med_s_val)[0:4]
               else:
                  desc = str(len(rows))
               cv2.putText(grid_img, desc,  (x1+15,y1+15), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
               #cv2.imshow("pepper", grid_img)
               #cv2.waitKey(30)

               grid_key = str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2)
               grid_data[grid_key] = [x1,y1,x2,y2,med_d_val, med_s_val]
               #print(x1,y1,x2,y2,med_d_val, med_s_val)


   sql = """
      SELECT cal_fn, name, mag, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, zp_res_px, zp_slope
        FROM calfile_paired_stars
       WHERE star_flux is not NULL
         AND new_cat_x is not NULL
         AND star_yn >= 99
         AND cal_fn like ?
   """

   cur.execute(sql, ["%" + cam_id + "%"])
   rows = cur.fetchall()
   all_good_stars = []
   for row in rows:
      cal_fn, name, mag, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, zp_res_px, zp_slope = row
      med_flux = med_flux_db[mag]
      if cal_fn not in best_dict:
         continue

      flux_diff = star_flux / med_flux

      grid_key = get_grid_key(grid_data, img_x, img_y, zp_res_px, zp_slope)
      [x1,y1,x2,y2,med_d_val, med_s_val] = grid_data[grid_key] 
      if med_d_val is None or zp_res_px is None:
         continue
      dist_diff = zp_res_px /  med_d_val
      scope_diff = zp_slope /  med_s_val
      dist = str(dist_diff)[0:4] + " " + str(scope_diff)[0:4]
      cv2.putText(grid_img, desc,  (x1+15,y1+25), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
      print("GRID KEY", grid_key, dist_diff, scope_diff , flux_diff) 

      cval = 128
      if .75 <= dist_diff <= 1.75:
         cval = cval + (cval/2)
      else:
         cval = cval - (cval /2)
      if .75 <= scope_diff <= 1.75:
         cval = cval + (cval/2)
      else:
         cval = cval - (cval /2)
      if .75 <= flux_diff <= 1.75:
         cval = cval + (cval/2)
      else:
         cval = cval - (cval /2)
      if cval > 245:
         cval = 250
         all_good_stars.append((cal_fn, name, mag, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, zp_res_px, zp_slope)) 

      if cval < 0:
         cval = 64 

      if cval > 128:
         color = [0,cval, 0]
      else:
         color = [cval,cval, cval]


      cv2.line(grid_img, (int(zp_cat_x),int(zp_cat_y)), (int(img_x),int(img_y)), color, 2)

      #cv2.imshow("pepper", grid_img)
      #cv2.waitKey(30)
      sql = """UPDATE calfile_paired_stars set star_found = 1 where cal_fn = ? and img_x = ? and img_y = ?"""
      uvals = [cal_fn, img_x, img_y]
      cur.execute(sql, uvals )
      
   if SHOW == 1:
      cv2.imshow("pepper", grid_img)
      cv2.waitKey(90)
   cv2.imwrite("/mnt/ams2/cal/plots/" + station_id + "_" + cam_id + "_ALL_GOOD_STARS.jpg", grid_img)
   print("saved all stars image /mnt/ams2/cal/plots/" + station_id + "_" + cam_id + "_ALL_GOOD_STARS.jpg")
   save_json_file("/mnt/ams2/cal/" + station_id + "_" + cam_id + "_ALL_GOOD_STARS.json", all_good_stars)
   print("saved", "/mnt/ams2/cal/" + station_id + "_" + cam_id + "_ALL_GOOD_STARS.json")
   con.commit()
   # plot all stars?

   #(cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star

   calfiles_data  = load_cal_files(cam_id, con,cur)
   merged_stars = []
   for star in all_good_stars:

      (cal_fn, name, mag, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, zp_res_px, zp_slope) = star
      if cal_fn not in best_dict:
         continue

      if cal_fn in calfiles_data:
         #(cal_fn_ex, center_az,center_el, ra_center,dec_center, position_angle, pixscale) = calfiles_data[cal_fn]
         (station_id, camera_id, cal_fn, cal_ts, center_az, center_el, ra_center, dec_center, position_angle,\
            pixscale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
            y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) = calfiles_data[cal_fn] 


      #match_dist = zp_res_px

      match_dist = 9999
      merged_stars.append((cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,center_az,center_el,new_cat_x,new_cat_y,img_x,img_y,zp_res_px,star_flux)) 
   save_json_file("/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json", merged_stars)
 
def load_cal_files(cam_id, con, cur, single=False):
   sql = """
      SELECT station_id,
             camera_id,
             cal_fn,
             cal_ts,
             az,
             el,
             ra,
             dec,
             position_angle,
             pixel_scale,
             zp_az,
             zp_el,
             zp_ra,
             zp_dec,
             zp_position_angle,
             zp_pixel_scale,
             x_poly,
             y_poly,
             x_poly_fwd,
             y_poly_fwd,
             res_px,
             res_deg,
             ai_weather,
             ai_weather_conf,
             cal_version,
             last_update
        FROM calibration_files
   """
   if single is False:
      sql += """
         WHERE cal_fn like ?
      """
      uvals = ["%" + cam_id + "%"]
   else:
      sql += """
         WHERE cal_fn = ?
      """
      uvals = [ cam_id  ]
   #print(sql)
   #print(uvals)
   cur.execute(sql, uvals )

   rows = cur.fetchall()
   calfiles_data = {}
   #print(rows)
   #print("NO CAL FILES DATA FOUND!?")

   for row in rows:
      failed = False
      (station_id, camera_id, cal_fn, cal_ts, az, el, ra, dec, position_angle,\
         pixel_scale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
         y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) = row

      cal_dir = cal_dir_from_file(cal_fn)
      if cal_dir is False:
         print("FAILED load_cal_files ", cal_dir , cal_fn)
         failed = True 
      elif os.path.exists(cal_dir + cal_fn) is False: 
         print("FAILED load_cal_files", cal_dir + cal_fn)
         failed = True 

      if failed is True:
         print("DELETE", cal_fn)
         delete_cal_file(cal_fn, con, cur, json_conf)
         continue

      calfiles_data[cal_fn] = (station_id, camera_id, cal_fn, cal_ts, az, el, ra, dec, position_angle,\
         pixel_scale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
         y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) 
     # row
   print("GOOD")
   return(calfiles_data)       
   



def get_grid_key(grid_data, img_x, img_y, zp_res_px, zp_slope):
   for gkey in grid_data:
      [x1,y1,x2,y2,med_d_val, med_s_val] = grid_data[gkey] 
      if x1 <= img_x <= x2 and y1 <= img_y <= y2:
         return(gkey)
      
def batch_calib(cam_id, con, cur, json_conf):
   free_cal_dir = "/mnt/ams2/cal/freecal/"
   cal_dirs = glob.glob(free_cal_dir + "*" + cam_id + "*")
   for ccd in sorted(cal_dirs, reverse=True):
      cal_fn = ccd.split("/")[-1]
      cal_img_file = ccd + "/" + cal_fn + "-stacked.png"
      cal_json_file = cal_img_file.replace(".png", "-calparams.json")
      cal_json_fn = cal_json_file.split("/")[-1]
      if os.path.exists(cal_img_file):
         print("JSON:", cal_json_fn)
         loaded = check_calibration_file(cal_json_fn, con, cur)
         if loaded is False:
            get_image_stars(cal_img_file, con, cur, json_conf)
         else:
            print("Already loaded")

def lens_model(cam_id, con, cur, json_conf):
   station_id = json_conf['site']['ams_id']

   mask_file = "/mnt/ams2/meteor_archive/{}/CAL/MASKS/{}_mask.png".format(station_id, cam_id)
   print("MASK:", mask_file)
   if os.path.exists(mask_file) is True:
      mask = cv2.imread(mask_file)
      mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
      mask = cv2.resize(mask, (1920,1080))
   else:
      mask = np.zeros((1080,1920),dtype=np.uint8)

   autocal_dir = "/mnt/ams2/cal/"
   station_id = json_conf['site']['ams_id']
   print("LENS MODEL")

   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
      mcp['cal_version'] += 1
   else:
      mcp = None

   #if "cal_version" not in cal_params:
   #   cal_params['cal_version'] = mcp['cal_version'] 


   merged_stars = load_json_file("/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json")
   # 

   status, cal_params,merged_stars = minimize_poly_multi_star(merged_stars, json_conf,0,0,cam_id,None,mcp,SHOW)

   if cal_params == 0:
      print("LENS MODEL MAKE FAILED")
      exit()

   if "cal_version" not in cal_params and mcp is None:
      cal_params['cal_version'] = 1 
   else:
      cal_params['cal_version'] =  mcp['cal_version']

   save_json_file(mcp_file, cal_params)
   print("SAVED:", mcp_file)

   # save the new merged stars!
   new_merged_stars = []

   rez = [row[-2] for row in merged_stars] 
   med_rez = np.mean(rez) 
   for star in merged_stars:
      (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,center_az,center_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = star
      cal_params['center_az'] = center_az
      cal_params['center_el'] = center_el
      cal_params['ra_center'] = ra_center
      cal_params['dec_center'] = dec_center
      cal_params['position_angle'] = position_angle 
      cal_params['pixscale'] = pixscale 
      #nc = update_center_radec(cal_fn,cal_params,json_conf)
      new_cat_x,new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)
      res_px = calc_dist((img_x,img_y),(new_cat_x,new_cat_y))
      if res_px <= med_rez:
         print("KEEP", res_px, med_rez)
         new_merged_stars.append((cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,center_az,center_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux))
      else:
         print("SKIP", res_px, med_rez)
   save_json_file("/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json", new_merged_stars)

   rez = [row[-2] for row in new_merged_stars] 
   mean_rez = np.mean(rez) 
   print("NEW STARS:", len(new_merged_stars))
   print("NEW REZ:", mean_rez)


def wizard(cam_id, con, cur, json_conf):

   
   # review / apply the current lens model 
   # and calibration on the best 10 files

   cal_fns = batch_review(cam_id, con, cur, json_conf, 100)

   # characterize the current lens model 
   # and define best merge star values

   print(cam_id, cal_fns)
   characterize_best(cam_id, con, cur, json_conf, 100, cal_fns)

   # run lens model with current stars
   lens_model(cam_id, con, cur, json_conf)

   # run lens model a second time
   lens_model(cam_id, con, cur, json_conf)

   # now remove the previous model
   autocal_dir = "/mnt/ams2/cal/"
   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   os.system("rm " + mcp_file)

   # now remake it with the stars left over from the last run
   lens_model(cam_id, con, cur, json_conf)

   # run lens model a second time
   lens_model(cam_id, con, cur, json_conf)

   # now the lens model should be made within around to less than 1PX res. 
   # if it is less than 2px that is fine as each indiviual capture will
   # be specifically fined tuned. Remember the goal here is to make a generic model
   # that can be applied to any file at any time. Not to neccessarily get the minimize possible res

   # lens_model_final_report()
   lens_model_report(cam_id, con, cur, json_conf)



def lens_model_report(cam_id, con, cur, json_conf):
   print("LENS MODEL REPORT FOR ", cam_id)
   print("--------------------- ")

def prune(cam_id, con, cur, json_conf):
   #print("Prune calfiles for cam_id")
   freecal_dir = "/mnt/ams2/cal/freecal/"
   extracal_dir = "/mnt/ams2/cal/extracal/"
   if os.path.exists(extracal_dir) is False:
      os.path.exists(extracal_dir)
   temp = os.listdir(freecal_dir)
   cal_files = []
   for xx in temp:
      if cam_id in xx:
         cal_files.append(xx)

   freecal_index = load_json_file("/mnt/ams2/cal/freecal_index.json") 
   month_dict = {}
   pruned = 0
   for cal_file in freecal_index:
      if cam_id not in cal_file:
         continue
      cal_fn = cal_file.split("/")[-1]
      day = cal_fn[0:10]
      month = cal_fn[0:7]
      if month not in month_dict:
         month_dict[month] = {}
         month_dict[month]['files'] = []
      data = freecal_index[cal_file]
      month_dict[month]['files'].append([cal_file, data])

   mc = 0
   for month in sorted(month_dict, reverse=True):
      if mc < 3:
         print("Skip most recent months!")
         mc += 1
         continue
      over_files = len(month_dict[month]['files']) - 15
      print(month, len(month_dict[month]['files']), "over", over_files )
      just_data = []
      for cal_file, data in month_dict[month]['files'] :
         just_data.append(data)
      if over_files <= 1:
         print("THIS MONTH IS GOOD", month)
         continue
      just_data = sorted(just_data, key=lambda x: x['total_stars'] / x['total_res_px'], reverse=True)

      for data in just_data[0:over_files]:
         if os.path.isdir(data['base_dir']) is True:
            cmd = "mv " + data['base_dir'] + " " + extracal_dir
            print(cmd)
            os.system(cmd)
            print(data['base_dir'], data['total_stars'], data['total_res_px'])
            pruned += 1
         else:
            print("DONE ALREADY!", data['base_dir'], data['total_stars'], data['total_res_px'])

      mc += 1
      
   print("Before prune total files:", len(cal_files))
   print("Suggest pruning:", pruned)
   print("After prune total files:", len(cal_files) - pruned)


if __name__ == "__main__":
   json_conf = load_json_file("../conf/as6.json")
   station_id = json_conf['site']['ams_id']
   db_file = station_id + "_CALIB.db" 
   #con = sqlite3.connect(":memory:")

   if os.path.exists(db_file) is False:
      cmd = "cat CALDB.sql |sqlite3 " + db_file
      print(cmd)
      os.system(cmd)
   else:
      print("CAL DB EXISTS ALREADY")

   con = sqlite3.connect(db_file)
   cur = con.cursor()

   cmd = sys.argv[1]
   cal_file = sys.argv[2]

   # batch = batch load cal files in DB / v2 structure
   # gis = process 1 file for first time
   # cal_main = main menu
   # char = recharacterize camera -- pre-req for lens_model 
   # lens_model = make multi-file lens model from best stars
   # update_calfiles = update all files with latest poly vals, re-center and re-pick/calc stars and res
   # view = view a file
   # man_tweek = tweek a file

   # cron process/es shoudl be: {
   #   batch
   #   char
   #   lens_model
   #   update
   # }
   # do this 3-5x and it should be good?!
   # 


   if cmd == "best" :
      cam_id = sys.argv[2]
      characterize_best(cam_id, con, cur, json_conf)

   if cmd == "batch" :
      # IMPORT FOR THE FIRST TIME
      # WORKS BUT OLD AND SLOW
      # USE status to get started and wiz to perfect!

      cam_id = sys.argv[2]
      batch_calib(cam_id, con, cur, json_conf)
   if cmd == "get_image_stars" or cmd == "gis":
      get_image_stars(cal_file, con, cur, json_conf)
   if cmd == "cal_main" :
      cal_main(cal_file)
   if cmd == "char" :
      cam_id = sys.argv[2]
      characterize_fov(cam_id, con, cur, json_conf)
   if cmd == "lens_model" :
      cam_id = sys.argv[2]
      lens_model(cam_id, con, cur, json_conf)
   if cmd == "update" :
      cam_id = sys.argv[2]
      update_calfiles(cam_id, con, cur, json_conf)
   if cmd == "view" :
      view_calfile(cal_file, con, cur, json_conf)
   if cmd == "man_tweek" :
      manual_tweek_calib(cal_file, con, cur, json_conf)
   if cmd == "wizard" :
      wizard(cam_id, con, cur, json_conf)
   if cmd == "batch_apply" :
      cam_id = sys.argv[2]
      batch_apply(cam_id, con, cur, json_conf)
   if cmd == "cat_view" :
      cal_fn = sys.argv[2]
      cat_view(cal_fn, con, cur, json_conf)
   if cmd == "find_stars_cat" :
      cal_fn = sys.argv[2]
      find_stars_with_catalog(cal_fn, con, cur, json_conf)
   if cmd == "cat_image" :
      cal_fn = sys.argv[2]
      catalog_image(cal_fn, con, cur, json_conf)

   if cmd == "batch_review" :
      cam_id = sys.argv[2]
      batch_review(cam_id, con, cur, json_conf)
   if cmd == "wiz" :
      cam_id = sys.argv[2]
      wizard(cam_id, con, cur, json_conf)

   if cmd == "status" :
      cam_id = sys.argv[2]
      cal_status_report(cam_id, con, cur, json_conf)
   if cmd == "prune" :
      cam_id = sys.argv[2]
      prune(cam_id, con, cur, json_conf)

