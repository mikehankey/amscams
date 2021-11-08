from flask import Flask, request
from FlaskLib.FlaskUtils import get_template
from lib.PipeUtil import cfe, load_json_file, save_json_file
from lib.PipeAutoCal import fn_dir
import math
import time
import cv2
import os
import numpy as np
import glob

def pick_points_day(day, json_conf):
   print("PPD")
   xfiles = glob.glob("/mnt/ams2/meteors/" + day + "/*.json")
   print("/mnt/ams2/meteors/" + day + "/*.json")
   files = []
   for file in xfiles:
      print(file)
      if "reduced" not in file:
         files.append(file)
   out = ""
   for file in files:
      mf = file.split("/")[-1]
      print(file)
      mj = load_json_file(file)
      if "final_vid" in mj:
         vf = mj['final_vid']
      vf = vf.replace("/mnt/ams2", "")
      icf = vf.replace(".mp4", "_crop.jpg")
      mfile = json_conf['site']['ams_id'] + ":" + mf
      link = "/pick_points/" + mfile + "/" 
      href = "<a href=" + link + ">"
      out += href + "<img width=320 height=180 src='" + icf + "?123'></a>"
   return(out)

def pick_points(meteor_id, json_conf):

   points = []
   out = ""
   station_id, meteor_video = meteor_id.split(":")
   mf = meteor_video.replace(".mp4", ".json")
   year = mf[0:4] 
   date = mf[0:10]
   meteor_file = "/mnt/ams2/meteors/" + date + "/" + mf 
   red_file = meteor_file.replace(".json", "-reduced.json")
   if cfe(red_file) == 1:
      mjr = load_json_file(meteor_file)
   mj = load_json_file(meteor_file)
   if "final_vid" in mj:
      fvid = mj['final_vid']
      fv_fn = fvid.split("/")[-1]
      fv_fn = fv_fn.replace(".mp4", "")
      cache_dir = "/mnt/ams2/CACHE/" + year + "/" + fv_fn + "_crop/"
   if "final_vid" in mj:
      roi_big = mj['final_vid'].replace(".mp4", "_crop.jpg")
      crop_stack_file = mj['final_vid'].replace(".mp4", "_crop.jpg")
      stack_file = mj['final_vid'].replace(".mp4", "_stacked.jpg")
      vroi = roi_big.replace("/mnt/ams2", "")
   if "hd_red" in mj:
      if "hd_mfd" in mj['hd_red']:
         for key in mj['hd_red']['hd_mfd']:
            data = mj['hd_red']['hd_mfd'][key]
            points.append((data['hd_lx'], data['hd_ly']))
            print(data)
   else:
      print(mj)
   out += crop_stack_file + "<br>" 
   out += stack_file + "<br>" 
   out += "<img width=1280 height=720 src=" + vroi + ">"

   print("CACHE:", cache_dir)
   files = glob.glob(cache_dir + "*")


   out += """

      <script src="https://archive.allsky.tv/APPS/src/js/plugins/fabric.js?1613429206.2923284"></script>

      <canvas id="c" width=1920 height=1080 style="border:1px solid #ccc"></canvas>

      <script> 
      var crop_stack_file = "{:s}"
      var stack_file = "{:s}"
      var images = {:s}
      var points = {:s}
      ii = 0
   """.format(crop_stack_file, stack_file, str(files), str(points))

   out += """

      var canvas = new fabric.Canvas("c", {
         hoverCursor: 'pointer',
         selection: true,
         selectionBorderColor: 'green',
         backgroundColor: null
      });


      for (i in points) {
         var x = points[i][0]
         var y = points[i][1]
         console.log(x,y)
         canvas.add(new fabric.Line([x, y, x+100, y+100], {
            left: x,
            top: y,
            stroke: 'red'
         }));
      }


      function set_image() {
         imageUrl = images[ii]
         canvas.setBackgroundImage(imageUrl, canvas.renderAll.bind(canvas), {
         // Optionally add an opacity lvl to the image
         backgroundImageOpacity: 0.5,
         // should the image be resized to fit the container?
         backgroundImageStretch: false
         });
      }

      function next_img() {
         ii = ii + 1
         if (ii >= images.length) {
            ii = 0
         }
         imageUrl = images[ii]
         set_image()
         document.getElementById("frame_num").innerHTML=ii
      }
   
      function prev_img() {
         ii = ii - 1
         if (ii < 0) {
            ii = 0
         }
         imageUrl = images[ii]
         set_image()
         document.getElementById("frame_num").innerHTML=ii
      }


      set_image()

      </script>
      <span id="frame_num">#</span>
      <a href="javascript:prev_img()">Prev</a> - 
      <a href="javascript:next_img()">Next</a> - 

   """

   return(out)

def make_obs_object(mj,mse, nsinfo):
   obs = {}
   for i in range(0, len(mse['stations'])):
      station = mse['stations'][i] 
      file = mse['files'][i] 
      fn, dir = fn_dir(file)
      
      if station not in obs:
         obs[station] = {}
      if fn not in obs[station]:
         print("STATION:", station)
         
         obs[station][fn] = {}
         if station in nsinfo:
            obs[station][fn]['loc'] = nsinfo[station]['loc']
         else:
            obs[station][fn]['loc'] = [0,0,0]
         obs[station][fn]['times'] = []
         obs[station][fn]['fns'] = []
         obs[station][fn]['xs'] = []
         obs[station][fn]['ys'] = []
         obs[station][fn]['azs'] = []
         obs[station][fn]['els'] = []
         obs[station][fn]['ras'] = []
         obs[station][fn]['decs'] = []
         obs[station][fn]['ints'] = []
    
      if "mfds" in mse:
         mfd = mse['mfds'][i]
      else:
         mfd = {}
      if "meteor_frame_data" in mfd:
         for mc in range(0, len(mfd['meteor_frame_data'])):
            data = mfd['meteor_frame_data'][mc]
            dt, fnum, x, y, w, h, oint, ra, dec, az, el = data
            obs[station][fn]['times'].append(dt)
            obs[station][fn]['fns'].append(fnum)
            obs[station][fn]['xs'].append(x)
            obs[station][fn]['ys'].append(y)
            obs[station][fn]['ints'].append(oint)
            obs[station][fn]['ras'].append(ra)
            obs[station][fn]['decs'].append(dec)
            obs[station][fn]['azs'].append(az)
            obs[station][fn]['els'].append(el)
            print("DATA:", fn, data)

   for station in obs:
       for file in obs[station]:
         print(station, file, obs[station][file])

   return(obs) 

def make_ms_html(amsid, meteor_file, mj):
   mse = mj['multi_station_event']


   print("MSE:", mse)

   if "event_file" in mse:
      if "http:" in mse['event_file']:
         mse['event_file'] = mse['event_file'].replace("http:", "https:")
      ms_html = "<iframe width=100% height=800 src=" + mse['event_file'] + "></iframe>"
      print(ms_html)
      return(ms_html)

   failed = 0
   if "solve_status" in mse:
      solve_status = mse['solve_status']
      if "FAILED" in mse['solve_status']:
         failed = 1
   else:
      solve_status = "NOT SOLVED"

   #ms_html = "<table width=100%>"
   #ms_html += "<tr><td>Station</td><td>Start Datetime</td><td>File</td></tr>"
   if cfe("../conf/network_station_info.json") == 0:
      os.system("./Process.py get_network_info")
   if cfe("../conf/network_station_info.json"):
      nsinfo = load_json_file("../conf/network_station_info.json")
   else:
      nsinfo = {}

   obs = make_obs_object(mj,mse, nsinfo)

   station_pts = ""

   if failed == 1:
      note = "This event failed."
   else:
      note = ""

  

   note = solve_status
   ms_html = ""
   if solve_status == "SUCCESS":
      event_day = mse['event_day']
      y,m,d = event_day.split("_")
      event_dir = "/mnt/archive.allsky.tv/EVENTS/" + y + "/" + m + "/" + d + "/" + mse['event_id'] + "/"
      event_url = event_dir.replace("/mnt/", "https://")
      event_link = event_url + "index.html"
      mse['event_link'] = event_link
      event_href = "<a target=_blank href=" + event_link + ">Event " + mse['event_id'] + " Solved</a>" 
      ms_html += """
         <div class='h1_holder  d-flex justify-content-between'>
            <h1><span class='h'>""" + event_href + """</span> </h1>
         </div>
      """
   else:
      ms_html += """
         <div class='h1_holder  d-flex justify-content-between'>
            <h1><span class='h'>""" + str(solve_status) + """</span> </h1>
         </div>
      """


   ms_html += """
      <div class='h1_holder  d-flex justify-content-between'>
         <h1><span class='h'>Captures</span> </h1>
      </div>
   """

   ms_html += """
      <div id='main_container' class='container-fluid h-100 mt-4 lg-l'>
      <div class='gallery gal-resize reg row text-center text-lg-left'>

   """
   active_stations = {}
   for i in range(0, len(mse['stations'])):
      file,dir = fn_dir(mse['files'][i])
      file = file.replace(".json", "")
      tstation = mse['stations'][i]
      active_stations[tstation] = 1
      if "mfds" in mse:
         mfd = mse['mfds'][i]
      else:
         mfd = {}
      if "meteor_frame_data" not in mfd:
         meteor_frame_data = None
      else:
         meteor_frame_data = mfd['meteor_frame_data']
      year = file[0:4]
      day = file[0:10]
      if tstation != amsid:
         local_dir = "/mnt/ams2/meteor_archive/" + tstation + "/METEORS/" + year + "/" + day + "/" 
         cloud_dir = "/mnt/archive.allsky.tv/" + tstation + "/METEORS/" + year + "/" + day + "/" 
         cloud_url = "https://archive.allsky.tv/" + tstation + "/METEORS/" + year + "/" + day + "/" 
         if cfe(local_dir,1) == 0:
            os.makedirs(local_dir)
      else:
         cloud_dir = "/mnt/archive.allsky.tv/" + tstation + "/METEORS/" + year + "/" + day + "/" 
         cloud_url = "https://archive.allsky.tv/" + tstation + "/METEORS/" + year + "/" + day + "/" 
      cloud_prev = cloud_dir + tstation + "_" + file + "-prev.jpg"
      cloud_prev_url = cloud_url + tstation + "_" + file + "-prev.jpg?xx"
      if ".mp4" in cloud_prev:
         cloud_prev = cloud_prev.replace(".mp4", "")
         cloud_prev_url = cloud_prev_url.replace(".mp4", "")
         
      prev_img = "<img src=" + cloud_prev_url + ">"      
      #ms_html += "<tr><td>" + mse['stations'][i] + "</td><td>" + mse['start_datetime'][i] + "</td><td>" + prev_img + "<br>" + file + "</td></tr>"
      ht_class = "norm"
      jsid = ""
      meteor_detail_link = ""
      vothumb = cloud_prev_url
      vthumb = cloud_prev_url 
      show_datetime_cam = mse['start_datetime'][i]
      #ms_html += "<div>" + mse['stations'][i] + " " +  mse['start_datetime'][i] +  prev_img + "<br>" + file 
      if meteor_frame_data is not None:
         fmfd = meteor_frame_data[0]
         lmfd = meteor_frame_data[-1]
         (dt, fn, x, y, w, h, oint, ra, dec, az, el) = fmfd
         first_az_el = str(az)[0:5] + " / " + str(el)[0:5]
         (dt, fn, x, y, w, h, oint, ra, dec, az, el) = lmfd 
         last_az_el = str(az)[0:5] + " / " + str(el)[0:5]
         az_desc = " First: " + first_az_el + "<br>Last : " + last_az_el + ""
         #ms_html += "<tr><td colspan=4>" + str(meteor_frame_data) + "</td></tr>"
      else:
         az_desc = "AZ/EL Pending"
         #ms_html += "<tr><td colspan=4>Meteor Not Reduced Yet.</td></tr>"
         #ms_html += "Meteor Not Reduced Yet."
      show_datetime_cam += "<br>" + az_desc
      ms_html += """
         
         <div id='""" + jsid + """' class='preview select-to """ + ht_class + """'>
            <a class='mtt' href='""" + meteor_detail_link + """' data-obj='""" + vothumb + """' title='Go to Info Page'>
               <img alt='""" + show_datetime_cam + """' class='img-fluid ns lz' src='""" + vthumb + """'>
               <span>""" + tstation + " " + show_datetime_cam + """</span>
            </a>


      """
      ms_html += "</div>"


   ms_html += "</div>"

   if solve_status == "SUCCESS":
      ms_html += """
         <div class='h1_holder  d-flex justify-content-between'>
            <h1><span class='h'>Solution</span> </h1>
         </div>
      """
      ms_html += solve_report(mse)


   ms_html += "</div>"
   return(ms_html)

   all_lats = []
   all_lons = []

   for station in active_stations:
      if station_pts != "":
         station_pts += ";"
      loc = nsinfo[station]['loc']
      station_pts += str(loc[0]) + "," + str(loc[1]) + "," + station
      all_lats.append(float(loc[0]))
      all_lons.append(float(loc[1]))
   fn,dir = fn_dir(meteor_file)
   date = fn[0:10]
   fn = fn.replace(".mp4", "-map.jpg?" + str(time.time()))
   station_map = "/meteor/" + date + "/" + fn
   kml_file = station_map.replace("-map.jpg", ".kml")
   print("MAP:", station_map)
   ms_html += "</div></div>"
   #if cfe(station_map) == 1:

   center_lat = np.mean(all_lats)
   center_lon = np.mean(all_lons)

   if True:
      ms_html += """
         <div class='h1_holder  d-flex justify-content-between'>
            <h1><span class='h'>Map</span> </h1>
         </div>
   """
      #ms_html += "<img src=" + station_map+ "><br>"
      ms_html += "<iframe src=\"https://archive.allsky.tv/dist/maps/index.html?mf=" + kml_file + "&lat=" + str(center_lat) + "&lon=" + str(center_lon) + "\" width=800 height=440></iframe><br><a href=" + kml_file + ">KML</a>"
   ms_html += """
            <div class="tab-content box " >

                <div class="tab-pane fade show active pr-3" id="sol-tab" role="tabpanel" aria-labelledby="reduc-tab-l">

                <table class="table table-dark table-striped table-hover td-al-m mb-2 pr-5" >
                <thead>
                <tr>
                </th><th>Solution</th><th>Start Time</th><th>Start Lat</th><th>Start Lon</th><th>Start Alt</th><th>End Lat</th><th>End Lon</th><th>End Alt</th>
                <th>Distance</th><th>Duration</th><th>Velocity</th>
                </tr>
                </thead>

   """
   if "solutions" in mj:
      
      for sdata in mj['solutions']:
         if len(sdata) == 2:
            (skey,sol) = sdata
            slon,slat,salt,elon,elat,ealt,dist,dur,vel = sol
         else:
            skey, slon,slat,salt,elon,elat,ealt,dist,dur,vel = sdata
         #saz,sel,salt,eaz,eel,ealt,dist,dur,vel = sol
         ms_html += "<tr><td>" + skey + "</td><td>TIME</td><td>" + str(slat)[0:5] + "</td><td>" + str(slon)[0:5] + "</td><td>" + str(salt/1000)[0:5] + "</td><td>" + str(elat)[0:5] + "</td><td>" + str(elon)[0:5] + "</td><td>" + str(ealt/1000)[0:5] + "</td><td>" + str(dist)[0:5] + "</td><td>" + str(dur)[0:5] + "</td><td>" + str(vel)[0:5] + "</td></tr>"
   ms_html += "</table></div></div>"
   return(ms_html)

def solve_report(mse):
   out = ""
   out += """<iframe width=100% height=800 src='""" + mse['event_link'] + """'></iframe>"""
   return(out)


def detail_page(amsid, date, meteor_file):
   remote = 1
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
   print("MJF IS:", mjf)
   mjvf = METEOR_VDIR + meteor_file.replace(".mp4", ".json")
   if "mp4" in meteor_file:
      mjrf = METEOR_DIR + meteor_file.replace(".mp4", "-reduced.json")
   else:
      mjrf = METEOR_DIR + meteor_file.replace(".json", "-reduced.json")
   mjrvf = METEOR_VDIR + mjrf.replace("/mnt/ams2", "")
   if cfe(mjf) == 1:
      mj = load_json_file(mjf)
   else:
      return("meteor json not found.")

   sd_trim = meteor_file
   if "hd_trim" in mj:
      print(mj['hd_trim'])
      if mj['hd_trim'] is not None and mj['hd_trim'] != 0:
         hd_trim,hdir  = fn_dir(mj['hd_trim'])
         hd_stack = hd_trim.replace(".mp4", "-stacked.jpg")
      else:
         hd_trim = None
         hd_stack = None
   else:
      hd_trim = None
      hd_stack = None
   if "multi_station_event" in mj:
      otherobs = """
                <li class="nav-item">
                    <a class="nav-link" id="multi-tab-l" data-toggle="tab" href="#multi-tab" role="tab" aria-controls="multi" aria-selected="false"><span id="str_cnt"></span>Event Solution</a>
                </li>
      """
      ms_html = str(mj['multi_station_event'])
      ms_html = make_ms_html(amsid, meteor_file, mj)
   else:
      otherobs = ""
      ms_html = ""


   sd_stack = sd_trim.replace(".mp4", "-stacked.jpg")
   half_stack = sd_stack.replace("stacked", "half-stack")
   if cfe(METEOR_DIR + half_stack) == 0:
      if cfe(METEOR_DIR + sd_stack) == 1:
         simg = cv2.imread(METEOR_DIR + sd_stack)
         simg  = cv2.resize(simg,(1920,1080))
         simg  = cv2.resize(simg,(960,540))
         cv2.imwrite(METEOR_DIR + half_stack,  simg)
         print("SAVED HALF", METEOR_DIR + half_stack, simg.shape)
         print("HALF SOURCE " + METEOR_DIR + sd_stack)
      else:
         print("NO SD ", sd_stack)
 
   az_grid = ""
   if remote == 1:
      header = get_template("FlaskTemplates/header-remote.html")
      footer = get_template("FlaskTemplates/footer-remote.html")
   else:
      header = get_template("FlaskTemplates/header.html")
      footer = get_template("FlaskTemplates/footer.html")
   nav = get_template("FlaskTemplates/nav.html")
   template = get_template("FlaskTemplates/meteor_detail.html")

   #footer = footer.replace("{RAND}", str(time.time()))
   if "location" in json_conf:
      template = template.replace("{LOCATION}", json_conf['site']['location'])
   else:
      template = template.replace("{LOCATION}", "")
   template = template.replace("{HEADER}", header)
   template = template.replace("{FOOTER}", footer)
   template = template.replace("{NAV}", nav)
   template = template.replace("{OBS_NAME}", obs_name)
   template = template.replace("{AMSID}", amsid)
   template = template.replace("{MEDIA_HOST}", MEDIA_HOST)
   template = template.replace("{HALF_STACK}", METEOR_VDIR + half_stack)
   template = template.replace("<!--OTHEROBS-->", otherobs)
   template = template.replace("{%MULTI_STATION_DATA%}", ms_html)
   if hd_stack is None or hd_stack == 0:
      template = template.replace("{HD_STACK}", "#")
   else:
      template = template.replace("{HD_STACK}", METEOR_VDIR + hd_stack)
   template = template.replace("{SD_STACK}", METEOR_VDIR + sd_stack)
   if hd_trim is None or hd_trim == 0:
      template = template.replace("{HD_TRIM}", "#")
   else:
      template = template.replace("{HD_TRIM}", METEOR_VDIR + hd_trim)
   template = template.replace("{AZ_GRID}", METEOR_VDIR + az_grid)
   template = template.replace("{JSON_CONF}", mjvf)
   template = template.replace("{METEOR_JSON}", mjvf)
   template = template.replace("{SD_TRIM}", METEOR_VDIR + sd_trim)
   template = template.replace("{METEOR_REDUCED_JSON}", mjrvf)

   if "best_meteor" not in mj: 
      template = template.replace("{START_TIME}", "-")
      template = template.replace("{DURATION}", "-")
      template = template.replace("{MAX_INTENSE}", "-")
      template = template.replace("{START_AZ}", "-")
      template = template.replace("{START_EL}", "-")
      template = template.replace("{END_EL}", "-")
      template = template.replace("{END_AZ}", "-")
      template = template.replace("{START_RA}", "-")
      template = template.replace("{END_RA}", "-")
      template = template.replace("{ANG_VEL}", "-")
      template = template.replace("{ANG_SEP}", "-")
      template = template.replace("{RA}", str("-"))
      template = template.replace("{DEC}", str("-"))
      template = template.replace("{AZ}", str("-"))
      template = template.replace("{EL}", str("-"))
      template = template.replace("{POSITION_ANGLE}", str("-"))
      template = template.replace("{PIXSCALE}", str("-"))
      template = template.replace("{IMG_STARS}", str("-"))
      template = template.replace("{CAT_STARS}", str("-"))
      template = template.replace("{RES_PX}", str("-"))
      template = template.replace("{RES_DEG}", str("-"))


   else:
      dur = len(mj['best_meteor']['ofns']) / 25 
      if "azs" in mj['best_meteor']:
         template = template.replace("{START_TIME}", mj['best_meteor']['dt'][0])
         template = template.replace("{DURATION}", str(dur)[0:4])
         template = template.replace("{MAX_INTENSE}", str(max(mj['best_meteor']['oint'])))

         template = template.replace("{START_AZ}", str(mj['best_meteor']['azs'][0])[0:5])
         template = template.replace("{END_AZ}", str(mj['best_meteor']['azs'][-1])[0:5])
         template = template.replace("{START_RA}", str(mj['best_meteor']['ras'][0])[0:5])
         template = template.replace("{END_RA}", str(mj['best_meteor']['ras'][-1])[0:5])
         template = template.replace("{START_DEC}", str(mj['best_meteor']['decs'][0])[0:5])
         template = template.replace("{END_DEC}", str(mj['best_meteor']['decs'][-1])[0:5])
         template = template.replace("{START_EL}", str(mj['best_meteor']['els'][0])[0:5])
         template = template.replace("{END_EL}", str(mj['best_meteor']['els'][-1])[0:5])
         template = template.replace("{ANG_VEL}", str(mj['best_meteor']['report']['ang_vel'])[0:5])
         template = template.replace("{ANG_SEP}", str(mj['best_meteor']['report']['ang_dist'])[0:5])

      if "cp" in mj['best_meteor']:
         cp = mj['best_meteor']['cp']
         mj['cp'] = cp
         del(mj['best_meteor']['cp'])

      if "cp" in mj:
         cp = mj['cp']
         if cp is not None:
            print(cp)
            template = template.replace("{RA}", str(cp['ra_center'])[0:5])
            template = template.replace("{DEC}", str(cp['dec_center'])[0:5])
            template = template.replace("{AZ}", str(cp['center_az'])[0:5])
            template = template.replace("{EL}", str(cp['center_el'])[0:5])
            template = template.replace("{POSITION_ANGLE}", str(cp['position_angle'])[0:5])
            template = template.replace("{PIXSCALE}", str(cp['pixscale'])[0:5])
            template = template.replace("{IMG_STARS}", str(len(cp['user_stars'])))
            if "cat_image_stars" in cp:
               template = template.replace("{CAT_STARS}", str(len(cp['cat_image_stars'])))
            else:
               template = template.replace("{CAT_STARS}", "")

            if "total_res_px" in cp:
               if math.isnan(cp['total_res_px']) is True:
                  cp['total_res_px'] = 99
               template = template.replace("{RES_PX}", str(cp['total_res_px'])[0:5])
               if "total_res_deg" in cp:
                  template = template.replace("{RES_DEG}", str(cp['total_res_deg'])[0:5])
               else:
                  template = template.replace("{RES_DEG}", "")
      else:

         template = template.replace("{RES_PX}", "99")
         template = template.replace("{RES_DEG}", "99")
         cp['total_res_px'] = 99
         cp['total_res_deg'] = 99

   #if "total_res_px" not in cp:
   #   cp['total_res_px'] = 99
   #   cp['total_res_deg'] = 99

   if cfe("/mnt/ams2" + CACHE_VDIR, 1) == 0:
      if "mp4" in meteor_file:
         vid = meteor_file.replace(".json", ".mp4")
      else:
         vid = meteor_file.replace(".json", ".mp4")
      cmd = "./Process.py roi_mfd " + METEOR_DIR + vid
      print(cmd)
      os.system(cmd)
   print("CACHE:", CACHE_VDIR) 

   cal_params_js_var = "var cal_params = []"
   if cfe(mjrf) == 1:
      mjr = load_json_file(mjrf)
      print("LOADING REDUCE FILE:", mjrf)
      if "cal_params" in mjr:
         if mjr['cal_params'] is not None:
            if "total_res_px" not in mjr['cal_params']:
               mjr['cal_params']['total_res_px'] = 99
               mjr['cal_params']['total_res_deg'] = 99
               mjr['cal_params']['cat_image_stars'] = []
            elif mjr['cal_params']['total_res_px'] == "":
               mjr['cal_params']['total_res_px'] = 99
               mjr['cal_params']['total_res_deg'] = 99

            else:
               cal_params_js_var = "var cal_params = []"

         else:
            cal_params_js_var = "var cal_params = []"

      else:
         mjr['cal_params'] = mj['cp']


         if np.isnan(mjr['cal_params']['total_res_px']) or mjr['cal_params']['total_res_px'] is None or len(mjr['cal_params']['cat_image_stars']) == 0:
            mjr['cal_params']['total_res_px'] = 9999
            mjr['cal_params']['total_res_deg'] = 9999


      frame_table_rows = frames_table(mjr, base_name, CACHE_VDIR)
      if mjr is not None:
         if mjr['cal_params'] is not None:
            cal_params_js_var = "var cal_params = " + str(mjr['cal_params'])
      mfd_js_var = "var meteor_frame_data = " + str(mjr['meteor_frame_data'])
      crop_box_js_var = "var crop_box = " + str(mjr['crop_box'])
   else:
      cal_params_js_var = ""
      mfd_js_var = ""
      crop_box = ""
      crop_box_js_var = ""
      frame_table_rows = ""

   lc_html = light_curve_url(METEOR_DIR + sd_trim , mj)
  
   fn, vdir = fn_dir(meteor_file)
   div_id = fn.replace(".mp4", "")
   jsid = div_id.replace("_", "")

   template = template.replace("{JSID}", jsid)
   template = template.replace("{CROP_BOX}", crop_box_js_var)
   template = template.replace("{CAL_PARAMS}", cal_params_js_var)
   template = template.replace("{METEOR_FRAME_DATA}", mfd_js_var)
   template = template.replace("{FRAME_TABLE_ROWS}", frame_table_rows)
   template = template.replace("{STAR_ROWS}", "")
   template = template.replace("{LIGHTCURVE_URL}", lc_html)
   ts = time.time()
   template = template.replace("{RAND}", str(ts))
   return(template)   



def frames_table(mjr, base_name, CACHE_VDIR):

   if True:
      # check for reduced data
      #dt, fn, x, y, w, h, oint, ra, dec, az, el
      #frames_table = "<table border=1><tr><td></td><td>Time</td><td>Frame</td><td>X</td><td>Y</td><td>W</td><td>H</td><td>Int</td><td>Ra</td><td>Dec</td><td>Az</td><td>El</td></tr>"
      frames_table = "\n"
      for mfd in mjr['meteor_frame_data']:
         dt, fn, x, y, w, h, oint, ra, dec, az, el = mfd
         print(dt)
         if " " in dt:
            date, dtime = dt.split(" ")
         else:
            print("DATE TIME FIELD IS MAL FORMATTED!", dt)
            elm = dt.split("_")
            print("ELM:", elm)
            y,m,d,h,mm,s = elm
            date = y+ "-" + m + "-" + d 
            dtime = h + "-" + mm + "-" + s 
            dt = date + " " + dtime

         fnid = "{:04d}".format(mfd[1])
         frame_url = CACHE_VDIR + base_name + "-frm" + fnid + ".jpg?r=" + str(time.time())
         frames_table += """<tr id='fr_{:d}' data-org-x='{:d}' data-org-y='{:d}'>""".format(mfd[1], int(mfd[2]), int(mfd[3]))
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

def light_curve_url(sd_video_file, mj):
   light_curve_file = sd_video_file.replace('.mp4','-lightcurve.jpg')
   if(cfe(light_curve_file) == 1):
      lc_url = '<a class="d-block nop text-center img-link-n" href="'+light_curve_file+'"><img  src="'+light_curve_file+'" class="mt-2 img-fluid"></a>'
   else:
      if "best_meteor" in mj:
         lc_url = graph_light_curve(mj)
      else:
         lc_url = ""
         #lc_url = "<div class='alert error mt-4'><iframe scolling=no src=" + light_curve_url  + " width=100% height=640></iframe></div>"
   return(lc_url)

def graph_light_curve(mj):
   x1_vals = ""
   y1_vals = ""
   for i in range(0, len(mj['best_meteor']['ofns'])):
      if x1_vals != "":
         x1_vals += ","
         y1_vals += ","
      x1_vals += str(mj['best_meteor']['ofns'][i])
      y1_vals += str(mj['best_meteor']['oint'][i])
   gurl = "/dist/plot.html?"
   gurl += "title=Meteor_Light_Curve&xat=Intensity&yat=Frame&x1_vals=" + x1_vals + "&y1_vals=" + y1_vals
   return(gurl)

