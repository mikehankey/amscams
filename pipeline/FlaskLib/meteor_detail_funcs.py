from flask import Flask, request
from FlaskLib.FlaskUtils import get_template
from lib.PipeUtil import cfe, load_json_file, save_json_file
from lib.PipeAutoCal import fn_dir
import time


def detail_page(amsid, date, meteor_file):
   MEDIA_HOST = request.host_url.replace("5000", "80")
   MEDIA_HOST = ""
   METEOR_DIR = "/mnt/ams2/meteors/"
   METEOR_DIR += date + "/"
   METEOR_VDIR = METEOR_DIR.replace("/mnt/ams2", "")

   year,mon,day = date.split("_")
   base_name = meteor_file.replace(".mp4", "")
   json_conf = load_json_file("../conf/as6.json")
   obs_name = json_conf['site']['obs_name']
   CACHE_DIR = "/mnt/ams2/CACHE/" + year + "/" + mon + "/" + base_name + "/"
   CACHE_VDIR = CACHE_DIR.replace("/mnt/ams2", "")
   mjf = METEOR_DIR + meteor_file.replace(".mp4", ".json")
   mjvf = METEOR_VDIR + meteor_file.replace(".mp4", ".json")
   mjrf = METEOR_DIR + meteor_file.replace(".mp4", "-reduced.json")
   mjrvf = METEOR_VDIR + mjrf.replace("/mnt/ams2", "")
   if cfe(mjf) == 1:
      mj = load_json_file(mjf)
   else:
      return("meteor json not found.")

   sd_trim = meteor_file
   if "hd_trim" in mj:
      hd_trim,hdir  = fn_dir(mj['hd_trim'])
      hd_stack = hd_trim.replace(".mp4", "-stacked.jpg")
   else:
      hd_trim = None
      hd_stack = None

   sd_stack = sd_trim.replace(".mp4", "-stacked.jpg")
   half_stack = sd_stack.replace("stacked", "half-stack")
   az_grid = ""
   header = get_template("FlaskTemplates/header.html")
   header = header.replace("{OBS_NAME}", obs_name)
   header = header.replace("{AMSID}", amsid)
   footer = get_template("FlaskTemplates/footer.html")
   footer = footer.replace("{RAND}", str(time.time()))
   template = get_template("FlaskTemplates/meteor_detail.html")
   template = template.replace("{HEADER}", header)
   template = template.replace("{FOOTER}", footer)
   template = template.replace("{MEDIA_HOST}", MEDIA_HOST)
   template = template.replace("{HALF_STACK}", METEOR_VDIR + half_stack)
   template = template.replace("{HD_STACK}", METEOR_VDIR + hd_stack)
   template = template.replace("{SD_STACK}", METEOR_VDIR + sd_stack)
   template = template.replace("{HD_TRIM}", METEOR_VDIR + hd_trim)
   template = template.replace("{AZ_GRID}", METEOR_VDIR + az_grid)
   template = template.replace("{METEOR_JSON}", mjvf)
   template = template.replace("{SD_TRIM}", METEOR_VDIR + sd_trim)
   template = template.replace("{METEOR_REDUCED_JSON}", mjrvf)
   if cfe(mjrf) == 1:
      mjr = load_json_file(mjrf)
      frame_table_rows = frames_table(mjr, base_name, CACHE_VDIR)
      cal_params_js_var = "var cal_params = " + str(mjr['cal_params'])
      mfd_js_var = "var meteor_frame_data = " + str(mjr['meteor_frame_data'])
      crop_box_js_var = "var crop_box = " + str(mjr['crop_box'])
   else:
      cal_params_js_var = ""
      mfd_js_var = ""
      crop_box = ""
   template = template.replace("{CROP_BOX}", crop_box_js_var)
   template = template.replace("{CAL_PARAMS}", cal_params_js_var)
   template = template.replace("{METEOR_FRAME_DATA}", mfd_js_var)
   template = template.replace("{FRAME_TABLE_ROWS}", frame_table_rows)
   template = template.replace("{STAR_ROWS}", "")
   template = template.replace("{LIGHTCURVE_URL}", "")
   return(template)   

def frames_table(mjr, base_name, CACHE_VDIR):
   if True:
      # check for reduced data
      #dt, fn, x, y, w, h, oint, ra, dec, az, el
      #frames_table = "<table border=1><tr><td></td><td>Time</td><td>Frame</td><td>X</td><td>Y</td><td>W</td><td>H</td><td>Int</td><td>Ra</td><td>Dec</td><td>Az</td><td>El</td></tr>"
      frames_table = "\n"
      for mfd in mjr['meteor_frame_data']:
         dt, fn, x, y, w, h, oint, ra, dec, az, el = mfd
         date, dtime = dt.split(" ")
         fnid = "{:04d}".format(mfd[1])
         frame_url = CACHE_VDIR + base_name + "-frm" + fnid + ".jpg?r=" + str(time.time())
         frames_table += """<tr id='fr_{:d}' data-org-x='{:d}' data-org-y='{:d}'>""".format(mfd[1], mfd[2], mfd[3])
         frames_table += """<td><div class="st" hidden style="Background-color:#ff0000"></div></td>"""
         img_id = "img_" + str(mfd[1])
         frames_table += """<td><img id='""" + img_id + """' alt="Thumb #'""" + str(mfd[1]) + """'" src='""" +frame_url+ """' width="50" height="50" class="img-fluid smi select_meteor" style="border-color:#ff0000"></td>"""

         frames_table += """<td>{:d}</td><td>{:s} </td>""".format(int(fn), str(dtime))
         frames_table += "<td> {:0.2f} / {:0.2f}</td>".format(ra, dec)
         frames_table += "<td>{:s} / {:s}</td>".format(str(az)[0:5],str(el)[0:5])
         frames_table += """<td>{:s} / {:s}</td><td>{:s} / {:s}</td><td>{:s}</td>""".format(str(x), str(y), str(w), str(h), str(int(oint)))
         frames_table += """<td><a class="btn btn-danger btn-sm delete_frame"><i class="icon-delete"></i></a></td>"""
         frames_table += """<td class="position-relative"><a class="btn btn-success btn-sm select_meteor"><i class="icon-target"></i></a></td>"""
         frames_table += "<td></td><td></td><td></td></tr>\n"

        #table_tbody_html+= '<tr id="fr_'+frame_id+'" data-org-x="'+v[2]+'" data-org-y="'+v[3]+'">

        #<td><div class="st" hidden style="background-color:'+all_colors[i]+'"></div></td>'
        #<td><img alt="Thumb #'+frame_id+'" src='+thumb_path+'?c='+Math.random()+' width="50" height="50" class="img-fluid smi select_meteor" style="border-color:'+all_colors[i]+'"/></td>

        #table_tbody_html+=
        #table_tbody_html+= '<td>'+frame_id+'</td><td>'+_time[1]+'</td><td>'+v[7]+'&deg;/'+v[8]+'&deg;</td><td>'+v[9]+'&deg;/'+v[10]+'&deg;</td><td>'+ parseFloat(v[2])+'/'+parseFloat(v[3]) +'</td><td>'+ v[4]+'x'+v[5]+'</td>';
        #table_tbody_html+= '<td>'+v[6]+'</td>';

   return(frames_table)   
