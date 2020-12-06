from lib.PipeUtil import load_json_file, save_json_file, cfe, bound_cnt
from lib.PipeAutoCal import get_image_stars, get_catalog_stars , pair_stars, eval_cnt, update_center_radec, fn_dir
from lib.PipeDetect import fireball, apply_frame_deletes
import os
import cv2
from FlaskLib.FlaskUtils import parse_jsid, make_default_template, get_template 
import glob

def show_masks(amsid):
   json_conf = load_json_file("../conf/as6.json")
   mask_dir = "/mnt/ams2/meteor_archive/" + amsid + "/CAL/MASKS/"
   masks = glob.glob(mask_dir + "*mask.png")
   out = ""
   #out = """
   #   <div id="main_container" class="container-fluid d-flex h-100 mt-4 position-relative">
   #"""

   for mask in sorted(masks):
      mask = mask.replace("/mnt/ams2", "")
      fn,dir = fn_dir(mask)
      cam = fn.replace("_mask.png", "")
      out += "<div style='float:left; padding: 10px'><img width=640 height=360 src=" + mask + "><br><caption>" + cam + "</caption><br></div>\n"
   #out += "</div>"
   template = make_default_template(amsid, "calib.html", json_conf)
   template = template.replace("{MAIN_TABLE}", out)
   return(template)

def cal_file(amsid, calib_file):
   json_conf = load_json_file("../conf/as6.json")
   
   caldir = "/mnt/ams2/cal/freecal/" + calib_file + "/"
   caldir = caldir.replace("-stacked.png", "")

   cps = glob.glob(caldir + "*cal*.json")
   hss = glob.glob(caldir + "*half-stack.png")
   azs = glob.glob(caldir + "*az*half*")
   sfs = glob.glob(caldir + "*stacked.png")
   if len(cps) == 0 :
      template = "Problem: no calparams file exists in this dir. " + caldir
      return(template)
   if len(cps) > 1 :
      template = "Problem: more than one cal file in this dir, please delete one." + caldir
      return(template)
   if len(hss) == 0 :
      if cfe(sfs[0]) == 1:
          stack_img = cv2.imread(sfs[0], 0)
          hsimg  = cv2.resize(stack_img,(960,540))
          hss = []
          hsf = sfs[0].replace("-stacked.png", "-half-stack.png")
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
      azs = glob.glob(caldir + "*az*half*")

   template = make_default_template(amsid, "calib.html", json_conf)
   template = template.replace("</html>", "<script src='/src/js/mikes/freecal-ajax.js'></script></html>")


   cd_template = get_template("FlaskTemplates/calfile_detail.html")
   hs = hs.replace("/mnt/ams2", "")
   st = hs.replace("/mnt/ams2", "")
   azs[0] = hs.replace("/mnt/ams", "")
   cal_time = calib_file[0:20]

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

   return(template)

def calib_main(amsid):
   json_conf = load_json_file("../conf/as6.json")
   template = make_default_template(amsid, "calib.html", json_conf)
   out = cal_history(amsid) 

   template = template.replace("{MAIN_TABLE}", out)

   return(template)


def cal_history(amsid, cam_id_filter=None):
   #cam_id_filter = form.getvalue("cam_id")
   out = ""
   out += "<h1>Past Calibrations</h1>"
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
   out += "<thead><tr><th>&nbsp;</th><th>Date</th><th>Cam ID</th><th>Stars</th><th>Center AZ/EL</th><th>Pos Angle</th><th>Pixscale</th><th>Res Px</th><th>Res Deg</th></tr></thead>"
   out += "<tbody>"

   #for cf in sorted(ci, reverse=True):
   for cf in cia:
      if "cam_id" not in cf:
         out += cf
         continue
      #hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cf)
      if "cal_date" not in cf:
          cf['cal_date'] = "9999"
      if 'cal_image_file' in cf:
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
      elif cam_id == cam_id_filter:
         show_row = 1
      else:
         show_row = 0

      if show_row == 1:
         out += "<tr class='" + color + "'><td><div class='st'></div></td><td><a class='btn btn-primary' href='{:s}'>{:s}</a></td><td><b>{:s}</b></td><td>{:s}</td><td>{:s}/{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td></tr>".format( link, str(cf['cal_date']), \
            str(cf['cam_id']), str(cf['total_stars']), str(cf['center_az'])[0:5], str(cf['center_el'])[0:5], str(cf['position_angle'])[0:5], \
            str(cf['pixscale'])[0:5], str(cf['total_res_px'])[0:5], str(cf['total_res_deg'])[0:5] )

   out += "</tbody></table></div>"

   return(out)
