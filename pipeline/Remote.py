#!/usr/bin/python3
"""

Functions for handling of remote sites

"""
from datetime import datetime
import cv2
from lib.DEFAULTS import *
import json
import os
from lib.PipeUtil import load_json_file, save_json_file, cfe
from lib.PipeAutoCal import autocal , solve_field, cal_all, draw_star_image, freecal_copy, apply_calib, index_failed, deep_calib, deep_cal_report, blind_solve_meteors, guess_cal, flatten_image, project_many, project_snaps, review_cals, star_db_mag, cal_report, review_all_cals, reverse_map, cal_index, fn_dir, eval_cal, minimize_fov, get_image_stars, solve_field, make_plate_image

CLOUD_ROOT = "/mnt/archive.allsky.tv/"
LOCAL_ROOT = "/mnt/ams2/meteor_archive/"


def load_remote_conf(station_id):
   station_data = None
   stations = load_json_file("../conf/stations.json")
   for data in stations:
      if station_id == data['id']:
         station_data = data

   local_cal_dir = LOCAL_ROOT + station_id + "/CAL/"
   cloud_cal_dir = CLOUD_ROOT + station_id + "/CAL/"
   lconf_file = local_cal_dir + "as6.json"
   cconf_file = cloud_cal_dir + "as6.json"
   if cfe(local_cal_dir, 1) == 0:
      os.makedirs(local_cal_dir)
   if cfe(lconf_file) == 1:
      print("Lconf found")
      json_conf = load_json_file(lconf_file)
      return(json_conf, station_data)
   elif cfe(cconf_file) == 1:
      print("cconf found")
      json_conf = load_json_file(cconf_file)
      save_json_file(lconf_file, json_conf)
      return(json_conf, station_data)
   else:
      print("Cloud conf not available.", cconf_file)
      remote_url = cconf_file.replace("/mnt/", "https://")
      cmd = "wget \"" + remote_url + "\" -O " + lconf_file 
      print(cmd)
      os.system(cmd)


   return(None, station_data)
   

def sync_configs():
   adirs = glob.glob("/mnt/ams2/archive.allsky.tv") 

def menu():
   out = """
      Functions:
         1) Copy / Update Remote Station Config Files
         2) Remote Calibrate
         3) Sync Back Updated Cal Files 

   """
   print(out)
   cmd = input("Select Function")
   print(cmd)
   if cmd == "2":
      remote_calibrate()
   if cmd == "3":
      sync_back_cals()



def remote_calibrate():
   r_station_num = input("Enter station id number AMSX:")
   #remote_ip = input("Enter remote http IP for direct host access or blank to use cloud drive data")
   r_station_id = "AMS" + r_station_num
   r_json_conf, station_data = load_remote_conf(r_station_id)
   R_CAL_DIR = LOCAL_ROOT + r_station_id + "/CAL/"

   # SYNC CAL INDEX FILES



   local_cal_files = []
   cam_num = 1
   ci_data = {}
   cam_nums = {}
   menu_cam_select = "Available cameras for " + r_station_id + "\n"
   year = "2020"
   for cam in r_json_conf['cameras']:
 
      cams_id = r_json_conf['cameras'][cam]['cams_id']
      cam_nums[cam] = cams_id
      if cams_id not in ci_data:
         ci_data[cams_id] = {}
         ci_data[cams_id]['cal_index'] = []
      ci_file = R_CAL_DIR + r_station_id + "_" + cams_id + "_CAL_INDEX.json"
      if station_data['remote_url'] != "":
         remote_url_base = "https://" + station_data['remote_url'] 
         remote_url = "https://" + station_data['remote_url'] + ci_file
         fn, dir = fn_dir(ci_file)
         fne = fn.split("-")
         fnr = fne[0]
         local_dir = R_CAL_DIR   
         local_file = local_dir + fnr
         if cfe(local_dir, 1) == 0:
            os.makedirs(local_dir)
         if cfe(local_file) == 0:
            cmd = "wget \"" + remote_url + "\" -O " + local_file
            os.system(cmd)
         local_cal_files.append(local_file)
         cij = load_json_file(local_file)
         ci_data[cams_id]['cal_index'] = cij 
    
         mcp_file = R_CAL_DIR + "AUTOCAL/" + year + "/solved/" + "multi_poly-" + r_station_id + "-" + cams_id + ".info"
         mfn, mdir = fn_dir(mcp_file)
         if cfe(mdir, 1) == 0:
            os.makedirs(mdir)
         if cfe(mcp_file) == 0:
            remote_mcp = remote_url_base + mcp_file
            cmd = "wget \"" + remote_mcp + "\" -O " + mcp_file
            print(cmd)
            os.system(cmd)

      menu_cam_select += "   " + str(cam.replace("cam", "")) + ") " + cams_id + "\n"

   print(menu_cam_select)
   selected = input("Select camera number (1-7): ")
   selected_cam = "cam" + str(selected)
   cams_id = cam_nums[selected_cam]
   print("You selected:", cam_nums[selected_cam])

   uci_data = cal_index(cams_id, r_json_conf, r_station_id)
   #print(cams_id, uci_data)
   if len(uci_data) > 0:
      ci_file = R_CAL_DIR + r_station_id + "_" + cams_id + "_CAL_INDEX.json"
      save_json_file(ci_file, uci_data)
      ci_data[cams_id]['cal_index'] = uci_data


   cc = 1 
   for data in ci_data[cams_id]['cal_index']:
      file, az, el, pos, px, ustars, cstars, res = data 
      fn, dir = fn_dir(file)
      elm = fn.split("-")
      rfn = elm[0]
      print(str(cc) + ")" , file, az, el, pos, px, ustars, cstars, res) 
      cc += 1

   #selected = input("Enter the cal file you want to work with, or enter ALL to do batch jobs on all cal files.")
   selected = "ALL"
   if selected == "ALL" or selected == "":
      work_on_all_files(r_station_id, r_json_conf, remote_url_base, cams_id, ci_data[cams_id]['cal_index'])
      exit()
   si = int(selected) - 1
   sdata = ci_data[cams_id]['cal_index'][si]
   print("YOU SELECTED:", sdata)


   cal_params_file, cal_image_file = sync_remote_calib(r_station_id, remote_url_base, sdata)

   cal_params = load_json_file(cal_params_file)
   oimage = cv2.imread(cal_image_file)

   mcp_file = R_CAL_DIR + "AUTOCAL/" + year + "/solved/" + "multi_poly-" + r_station_id + "-" + cams_id + ".info"
   if cfe(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      print("MCP:", mcp) 
      cal_params['x_poly'] = mcp['x_poly']
      cal_params['y_poly'] = mcp['y_poly']
      cal_params['y_poly_fwd'] = mcp['y_poly_fwd']
      cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
   else:
      print("NO MCP FILE:", mcp_file)

   cal_params , bad_stars, marked_img = eval_cal(cal_params_file, r_json_conf, cal_params, oimage) 

   #cal_params = minimize_fov(cal_params_file, cal_params, cal_params_file,oimage,r_json_conf )
   #guess_cal(cal_image_file, r_json_conf, cal_params)
   disp_img = cv2.resize(marked_img, (1280, 720))
   cv2.imshow('pepe', disp_img)
   cv2.waitKey(0)
  
   menu = """
      1) Minimize FOV
      2) Guess FOV
   """
   select = input(menu)
   if select == "1":
      cal_params = minimize_fov(cal_params_file, cal_params, cal_params_file,oimage,r_json_conf )
      save_json_file(cal_params_file, cal_params)
   if select == "2":
      cal_params = guess_cal(cal_image_file, r_json_conf, cal_params)
      save_json_file(cal_params_file, cal_params)

def sync_back_cals():

   r_station_num = input("Enter station id number AMSX:")
   #remote_ip = input("Enter remote http IP for direct host access or blank to use cloud drive data")
   r_station_id = "AMS" + r_station_num
   r_json_conf, station_data = load_remote_conf(r_station_id)

   l_ci_dir = LOCAL_ROOT + r_station_id + "/CAL/"
   c_ci_dir = CLOUD_ROOT + r_station_id + "/CAL/"

   ldir = LOCAL_ROOT + r_station_id + "/CAL/BEST/"
   cdir = CLOUD_ROOT + r_station_id + "/CAL/BEST/"


   cmd = "/usr/bin/rsync -av " + ldir + "*.json" + " " + cdir
   print(cmd)
   os.system(cmd)

   cmd = "/usr/bin/rsync -av " + l_ci_dir + "*.json" + " " + c_ci_dir
   print(cmd)
   os.system(cmd)

def work_on_all_files(r_station_id, r_json_conf, remote_url_base, cams_id, ci_data):
   imgs = []
   oimgs = []
   cps = []
   files = []
   cal_image_files = []
   mcp = load_mcp(r_station_id, cams_id)
   for sdata in ci_data:
      cal_params_file, cal_image_file = sync_remote_calib(r_station_id, remote_url_base, sdata)
      cal_params = load_json_file(cal_params_file)
      #guess_cal(cal_image_file, r_json_conf, cal_params)
      if mcp is not None:
         cal_params['x_poly'] = mcp['x_poly']
         cal_params['y_poly'] = mcp['y_poly']
         cal_params['y_poly_fwd'] = mcp['y_poly_fwd']
         cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      oimage = cv2.imread(cal_image_file)
      timage = oimage.copy()
      if "user_stars" in cal_params:
         if len(cal_params["user_stars"]) < 10:
            cal_params['user_stars'] = get_image_stars(cal_image_file, None, r_json_conf,0)
 
      cal_params , bad_stars, marked_img = eval_cal(cal_params_file, r_json_conf, cal_params, timage)

      cal_image_files.append(cal_image_file)
      imgs.append(marked_img)
      oimgs.append(timage)
      cps.append(cal_params)
      files.append(cal_params_file)
      #cal_params = minimize_fov(cal_params_file, cal_params, cal_params_file,oimage,r_json_conf )
   go = 1
   cc = 0
   while go == 1:
      if cc < len(imgs):
         disp_img = cv2.resize(imgs[cc], (1280, 720))
         cv2.imshow('pepe', disp_img)
         key = cv2.waitKey(0)
         if key == ord('p'):
            cc = cc - 1
            if cc <= 0:
               cc = 0
         if key == ord('n'):
            cc = cc + 1
         if key == ord('g'):
            ifile = files[cc].replace("-calparams.json", "-src.jpg")
            cal_params = guess_cal(ifile, r_json_conf, cps[cc])
            cps[cc] = cal_params
            imgs[cc] = marked_img 
            cal_params , bad_stars, marked_img = eval_cal(files[cc], r_json_conf, cal_params, oimgs[cc])
            save_json_file(cal_params_file, cal_params)
            #cc = cc + 1
         if key == ord('s'):
            temp_dir = "/mnt/ams2/temp/"
            cmd = "cp " + cal_image_files[cc] + " " + temp_dir
            cal_image_file = files[cc].replace("-calparams.json", "-src.jpg")
            fn, dir = fn_dir(cal_image_file)
            user_stars = get_image_stars(cal_image_file, None, r_json_conf,0)
            print("USER STARS:", len(user_stars))

            cps[cc]['user_stars'] = user_stars
            cal_params , bad_stars, marked_img = eval_cal(files[cc], r_json_conf, cps[cc], oimgs[cc])
            imgs[cc] = marked_img 
            #cv2.imwrite(cal_image_file, marked_img)
            save_json_file(files[cc], cal_params)

            plate_image, star_points = make_plate_image(oimgs[cc].copy(), user_stars)
            plate_file = cal_image_file.replace(".png", ".jpg")
            fn, dir = fn_dir(plate_file)
            plate_file = temp_dir + fn
            cv2.imwrite(plate_file, plate_image)
            print("WROTE:", plate_file)
            print("Solving...", plate_file)
            status, ps_cal_params, wcs_file = solve_field(plate_file , user_stars, r_json_conf)
            if status == 1:
               print("Plate success.")
               for key in ps_cal_params:
                  print(key, ps_cal_params[key])
               #save_json_file(files[cc], cal_params)
            else:
                print("Solved Failed.", plate_file)
                
         if key == ord('m'):
            cal_params = minimize_fov(files[cc], cps[cc], files[cc],oimgs[cc],r_json_conf )
            cal_params , bad_stars, marked_img = eval_cal(files[cc], r_json_conf, cal_params, oimgs[cc]) 
            cps[cc] = cal_params
            imgs[cc] = marked_img
            save_json_file(files[cc], cal_params)
      else:
         cc = 0
      


def load_mcp(r_station_id, cams_id):
   year = datetime.now().strftime("%Y")
   R_CAL_DIR = LOCAL_ROOT + r_station_id + "/CAL/"
   mcp_file = R_CAL_DIR + "AUTOCAL/" + year + "/solved/" + "multi_poly-" + r_station_id + "-" + cams_id + ".info"
   mcp = None
   if cfe(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
   else:
      print("NO MCP FILE:", mcp_file)
   return(mcp)
   

def sync_remote_calib(station_id, remote_url_base, sdata):      
   rfile = sdata[0]
   fn, dir = fn_dir(rfile)
   elm = fn.split("-") 
   cal_base = elm[0]
   ldir = LOCAL_ROOT + station_id + "/CAL/BEST/"
   if cfe(ldir, 1) == 0:
      os.makedirs(ldir)
   l_cp_file = ldir + cal_base + "-calparams.json"
   l_cp_img_file = ldir + cal_base + "-src.jpg"

   # get cal_params_json
   if cfe(l_cp_file) == 0:
      remote_url = remote_url_base + rfile
      cmd = "wget \"" + remote_url + "\" -O " + l_cp_file 
      os.system(cmd)

   # get source image 
   if cfe(l_cp_img_file) == 0:
      remote_url = remote_url_base + rfile
      remote_url = remote_url.replace("-calparams.json", "-src.jpg")
      cmd = "wget \"" + remote_url + "\" -O " + l_cp_img_file 
      os.system(cmd)
   return(l_cp_file, l_cp_img_file)
   
if __name__ == "__main__":
   menu()

