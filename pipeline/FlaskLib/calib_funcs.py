from lib.PipeUtil import load_json_file, save_json_file, cfe, bound_cnt
from lib.PipeAutoCal import get_image_stars, get_catalog_stars , pair_stars, eval_cnt, update_center_radec, fn_dir
from lib.PipeDetect import fireball, apply_frame_deletes
import os
import cv2
from FlaskLib.FlaskUtils import parse_jsid, make_default_template, get_template 
import glob
import time

def lens_model(amsid):
   lms = glob.glob("/mnt/ams2/cal/lens*")
   json_conf = load_json_file("../conf/as6.json")
   out = ""

   out += """   <div id="main_container" class="container-fluid h-100 mt-4 lg-l"> """
   
   template = make_default_template(amsid, "calib.html", json_conf)


   for lens in sorted(lms):
      vlens = lens.replace("/mnt/ams2", "")
      lfn,dir = fn_dir(vlens)
      lfn = lfn.replace("lens_model_", "")
      lfn = lfn.replace(".jpg", "")
      star_db = "/mnt/ams2/meteor_archive/" + amsid + "/CAL/AUTOCAL/2020/solved/star_db-" + amsid + "-" + lfn + ".info"
      mp_cal = "/mnt/ams2/meteor_archive/" + amsid + "/CAL/AUTOCAL/2020/solved/multi_poly-" + amsid +"-" + lfn + ".info"
      sdb = load_json_file(star_db)
      mp = load_json_file(mp_cal)
      x_fun = mp['x_fun']
      y_fun = mp['y_fun']
      x_fun_fwd = mp['x_fun_fwd']
      y_fun_fwd = mp['y_fun_fwd']
      pf = len(sdb['processed_files'])
      ts = len(sdb['autocal_stars'])
      out += "<div style='float: left' class='preview select-to norm'>"
      out += "<a href=" + vlens + "><img width=640 height=360 src=" + vlens + "></a><br>" 
      out += "<table>"
      out +=  "<tr><td>Camera</td><td>" + lfn + "</td></tr>"
      out += "<tr><td>Total Files / Total Stars</td><td>" + str(pf) + "/" + str(ts) + "</td></tr> "
      out += "<tr><td>Res Error in PX: </td><td>" + str(x_fun)[0:4] + "/" + str(y_fun)[0:4] + "</td></tr> " 
      out += "<tr><td>Fwd Res Error in Deg: </td><td>" + str(x_fun_fwd)[0:4] + "/" + str(y_fun_fwd)[0:4] + "</td></tr>"
      out += "</table></div>" 
   out += "</div>"

   template = template.replace("{MAIN_TABLE}", out)

   return(template)


def del_calfile(amsid, calfile):
   fn, dir= fn_dir(calfile)
   fn = fn.replace("-stacked.png", "") 
   cmd = "rm -rf /mnt/ams2/cal/freecal/" + fn 
   print("CMD", cmd)
   os.system(cmd)
   resp = {}
   resp['status'] = 1
   return(resp)


def edit_mask_points(mask_file, action, mask_points_str):
   mask_file_half = "/mnt/ams2/" + mask_file
   mask_file = mask_file_half.replace("half", "mask")
   flat_file = mask_file_half.replace("half", "flat")
   app_file = mask_file_half.replace("half", "applied")
   print("MASK FILE:", mask_file)
   mimg = cv2.imread(mask_file,0) 
   fimg = cv2.imread(flat_file,0) 
   oh, ow = mimg.shape[:2]
   print("mask:", mask_file)
   mimg = cv2.resize(mimg,(960,540))
   mp = mask_points_str.split(";")
   for mm in mp:
      print("mp:", mm)
      el = mm.split(",")
      if len(el) == 3:
         x,y,s = el
         x = int(x)
         y = int(y)
         s = int(s)
         s = int(s / 2)
         x1 = x - s 
         y1 = y - s 
         x2 = x + s 
         y2 = y + s 
         if x1 < 0:
            x1 = 0
         if y1 < 0:
            y1 = 0
         if x2 > 960:
            x2 = 960 
         if y2 > 540:
            y2 = 540
         if action == "add":
            print("ADD:", x1,y1,x2,y2)
            mimg[y1:y2,x1:x2] = 255
         if action == "del":
            print("DEL:", x1,y1,x2,y2)
            mimg[y1:y2,x1:x2] = 0

   print("SAVED:", mask_file)
   mimg = cv2.resize(mimg,(ow,oh))
   aimg = cv2.subtract(fimg, mimg)
   cv2.imwrite(mask_file, mimg)
   cv2.imwrite(app_file, aimg) 
   himg = cv2.resize(aimg,(960,540))
   cv2.imwrite(mask_file_half, himg) 
        

def edit_mask(amsid, cam):
   json_conf = load_json_file("../conf/as6.json")
   out = amsid + "_" + cam
   mask_file = "/mnt/ams2/meteor_archive/" + amsid + "/CAL/MASKS/" + cam + "_applied.png"
   mask_file_half = "/mnt/ams2/meteor_archive/" + amsid + "/CAL/MASKS/" + cam + "_half.png"
   vmask = "/meteor_archive/" + amsid + "/CAL/MASKS/" + cam + "_half.png"
   if cfe(mask_file_half) == 0:
      img = cv2.imread(mask_file)
      img2 = cv2.resize(img,(960,540))
      cv2.imwrite(mask_file_half, img2)
   
   template = make_default_template(amsid, "edit_mask.html", json_conf)
   template = template.replace("{MAIN_TABLE}", out)
   template = template.replace("{MASK_FILE}", vmask)
   return(template)

def show_masks(amsid):
   json_conf = load_json_file("../conf/as6.json")
   mask_dir = "/mnt/ams2/meteor_archive/" + amsid + "/CAL/MASKS/"
   masks = glob.glob(mask_dir + "*mask.png")
   out = ""
   #out = """
   #   <div id="main_container" class="container-fluid d-flex h-100 mt-4 position-relative">
   #"""
   rand = str(time.time())
   for mask in sorted(masks):
      mask = mask.replace("/mnt/ams2", "")
      fn,dir = fn_dir(mask)
      cam = fn.replace("_mask.png", "")
      applied = mask.replace("mask", "applied")
      elink = "<a href='/edit_mask/" + amsid + "/" + cam + "/'>"
      out += "<div style='float:left; padding: 10px'>" + elink + "<img width=640 height=360 src=" + mask + "?" + rand + "><br><caption>" + cam + "</caption></a><br></div>\n"
      out += "<div style='float:left; padding: 10px'>" + elink + "<img width=640 height=360 src=" + applied + "?" + rand + "><br><caption>" + cam + "</caption></a><br></div>\n"
      out += "<div style='clear:both'></div>"
   #out += "</div>"
   template = make_default_template(amsid, "calib.html", json_conf)
   template = template.replace("{MAIN_TABLE}", out)
   return(template)

def cal_file(amsid, calib_file):
   json_conf = load_json_file("../conf/as6.json")
   
   caldir = "/mnt/ams2/cal/freecal/" + calib_file + "/"
   caldir = caldir.replace("-stacked.png", "")
   caldir = caldir.replace(".png", "")

   cps = glob.glob(caldir + "*cal*.json")
   print ("GLOB:", caldir + "*cal*.json")
   hss = glob.glob(caldir + "*half-stack.png")
   azs = glob.glob(caldir + "*az*half*")
   sfs = glob.glob(caldir + "*stacked.png")
   if len(cps) == 0 :
      cdd = caldir.replace(".png/", "")
      template = "Problem: no calparams file exists in this dir. " + caldir
      cmd = "rm -rf " + cdd
      #os.system(cmd)
      return(template + cmd)
   if len(cps) > 1 :
      template = "Problem: more than one cal file in this dir, please delete one." + caldir
      return(template)
   if len(hss) == 0 :
      if len(sfs) >= 1:
          for x in range(0, len(sfs)):
             if "az" not in sfs: 
                stack_img = cv2.imread(sfs[x], 0)
                hsimg  = cv2.resize(stack_img,(960,540))
                hss = []
                hsf = sfs[x].replace("-stacked.png", "-half-stack.png")
                hss.append(hsf)
                cv2.imwrite(hsf, hsimg)
      else:
         template = "Problem: no half-stack file exists and we could not make one." + caldir
         return(template)
   if len(hss) > 1 :
      template = "Problem: more than one half-stack file exists." + caldir
      return(template)
 
   cp = load_json_file(cps[0])
   hs = hss[0]
   st = hs.replace("half-stack", "stacked")
   if len(azs) == 0 :
      #template = "Problem: no azgrid file exists in this dir. " + caldir
      os.system("./AzElGrid.py az_grid " + cps[0] + " > /dev/null")
      print("./AzElGrid.py az_grid " + cps[0] + " > /dev/null")
      azs = glob.glob(caldir + "*az*half*")

   star_rows = ""
   for star in cp['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
      star_rows += "<tr><td>{:s}</td><td>{:s} </td><td> {:s} / {:s}</td><td>{:s}</td><td>{:s}</td><!-- <td>{:s}</td> --></tr>".format(dcname, str(mag), str(ra)[0:5], str(dec)[0:5], str(match_dist)[0:5], str(cat_dist)[0:5], str(bp))



   template = make_default_template(amsid, "calib.html", json_conf)
   template = template.replace("</html>", "<script src='/src/js/mikes/freecal-ajax.js'></script></html>")


   cd_template = get_template("FlaskTemplates/calfile_detail.html")
   hs = hs.replace("/mnt/ams2", "")
   st = hs.replace("/mnt/ams2", "")
   azs[0] = hs.replace("/mnt/ams", "")
   cal_time = calib_file[0:20]
   if "total_res_px" not in cp:
      cp['total_res_px']  = 999
   if "total_res_deg" not in cp:
      cp['total_res_deg']  = 999

   cd_template = cd_template.replace("{AMSID}", str(amsid))
   cd_template = cd_template.replace("{CALFILE}", str(calib_file))
   cd_template = cd_template.replace("{CAL_PARAMS}", str(cp))
   cd_template = cd_template.replace("{RA_CENTER}", str(cp['ra_center'])[0:5])
   cd_template = cd_template.replace("{DEC_CENTER}", str(cp['dec_center'])[0:5])
   cd_template = cd_template.replace("{CENTER_AZ}", str(cp['center_az'])[0:5])
   cd_template = cd_template.replace("{CENTER_EL}", str(cp['center_el'])[0:5])
   cd_template = cd_template.replace("{POSITION_ANGLE}", str(cp['position_angle'])[0:5])
   cd_template = cd_template.replace("{PIXSCALE}", str(cp['pixscale'])[0:5])
   cd_template = cd_template.replace("{TOTAL_STARS}", str(len(cp['user_stars'])))
   cd_template = cd_template.replace("{RES_PX}", str(cp['total_res_px'])[0:5])
   cd_template = cd_template.replace("{RES_DEG}", str(cp['total_res_deg'])[0:5])
   cd_template = cd_template.replace("{CAL_TIME}", cal_time)
   cd_template = cd_template.replace("{HALF_STACK}", hs)
   cd_template = cd_template.replace("{STACK_FILE}", st)
   cd_template = cd_template.replace("{AZ_GRID}", azs[0])
   cd_template = cd_template.replace("{USER_STARS}", "")
   print("AZS:", azs[0])
   template = template.replace("{MAIN_TABLE}", cd_template)
   template = template.replace("{STAR_ROWS}", star_rows)

   return(template)

def calib_main(amsid,in_data):
   if in_data['cam_id_filter'] is not None:
      cam_id_filter = in_data['cam_id_filter']
   else: 
      cam_id_filter = None
   json_conf = load_json_file("../conf/as6.json")
   template = make_default_template(amsid, "calib.html", json_conf)

   
   selector = "<select onChange='window.location.href=\"/calib/" + amsid + "/?cam_id_filter=\" + this.value '> name=cam_id_filter>"
   for cam in json_conf['cameras']:
      cams_id = json_conf['cameras'][cam]['cams_id']
      if cam_id_filter == cams_id:
         selector += "<option selected>" + cams_id + "</option>"
      else:
         selector += "<option >" + cams_id + "</option>"
   selector += "</select>"
   #out =selector
   out = cal_history(amsid, cam_id_filter, selector) 

   

   template = template.replace("{MAIN_TABLE}", out)

   return(template)


def cal_history(amsid, cam_id_filter=None, selector=None):
   #cam_id_filter = form.getvalue("cam_id")
   out = ""
   out += "<h1>Past Calibrations</h1>"
   out += "<center> Limit calibrations to camera " + selector + "</center>"


   freecal_index = "/mnt/ams2/cal/freecal_index.json"
   if cfe(freecal_index) == 1:
      ci = load_json_file("/mnt/ams2/cal/freecal_index.json")
   else:
      out += "No calibrations have been completed yet."
      exit()

   cia = []
   for cf in sorted(ci, reverse=True):
      if "cam_id" in ci[cf]:
         cia.append(ci[cf])
   #cia = sorted(cia, key=lambda x: x['cam_id'], -x['cal_image_file'], reverse=False)
   cia = sorted(cia, key=lambda x: x['cam_id'] )


   out += "<table class='table table-dark table-striped table-hover td-al-m m-auto table-fit'>"
   out += "<thead><tr><th>&nbsp;</th><th>Date</th><th>Cam ID</th><th>Stars</th><th>Center AZ/EL</th><th>Pos Angle</th><th>Pixscale</th><th>Res Px</th><th>Res Deg</th><th>Preview</th></tr></thead>"
   out += "<tbody>"

   #for cf in sorted(ci, reverse=True):
   for cf in cia:
      cal_image_file = None
      if "cam_id" not in cf:
         out += cf
         continue
      #hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cf)
      if "cal_date" not in cf:
          cf['cal_date'] = "9999"
      if 'cal_image_file' in cf:
         cal_image_file = cf['cal_image_file']
         ci_fn, ci_dir = fn_dir(cf['cal_image_file'])
         link = "/calfile/" + amsid + "/" + ci_fn + "/" 
      else:
         link = ""
      if "total_res_deg" not in cf:
         cf['total_res_deg'] = 99
      if cf['total_res_deg'] > .5:
         color = "lv1"; #style='color: #ff0000'"
      elif .4 < cf['total_res_deg'] <= .5:
         color = "lv2"; #"style='color: #FF4500'"
      elif .3 < cf['total_res_deg'] <= .4:
         color = "lv3"; #"style='color: #FFFF00'"
      elif .2 < cf['total_res_deg'] <= .3:
         color = "lv4"; #"style='color: #00FF00'"
      elif .1 < cf['total_res_deg'] <= .2:
         color = "lv5"; #"style='color: #00ffff'"
      elif 0 < cf['total_res_deg'] <= .1:
         color = "lv8"; #"style='color: #0000ff'"
      elif cf['total_res_deg'] == 0:
         color = "lv7"; #"style='color: #ffffff'"
      else:
         color = "lv7"
      if cam_id_filter is None:
         show_row = 1
      elif cf['cam_id'] == cam_id_filter:
         show_row = 1
      else:
         show_row = 0

      if show_row == 1:
         if cal_image_file is not None:
            cal_thumb = cal_image_file.replace(".png", "-tn.jpg")
            if cfe(cal_thumb) == 0:
               img = cv2.imread(cal_image_file)
               try:
                  tn = cv2.resize(img,(320,180))
                  cv2.imwrite(cal_thumb, tn)
               except:
                  print("PROBLEM WITH :", cal_image_file)
            vcal = cal_thumb.replace("/mnt/ams2", "")
            cal_img_thumb = "<img src=" + vcal + " width=320 height=180>"
         else:
            cal_img_thumb = ""
         out += "<tr class='" + color + "'><td><div class='st'></div></td><td><a class='btn btn-primary' href='{:s}'>{:s}</a></td><td><b>{:s}</b></td><td>{:s}</td><td>{:s}/{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td></tr>".format( link, str(cf['cal_date']), \
            str(cf['cam_id']), str(cf['total_stars']), str(cf['center_az'])[0:5], str(cf['center_el'])[0:5], str(cf['position_angle'])[0:5], \
            str(cf['pixscale'])[0:5], str(cf['total_res_px'])[0:5], str(cf['total_res_deg'])[0:5],cal_img_thumb )

   out += "</tbody></table></div>"

   return(out)
