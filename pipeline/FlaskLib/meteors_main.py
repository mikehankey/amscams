from flask import Flask, request
from FlaskLib.FlaskUtils import get_template, make_default_template
from FlaskLib.Pagination import get_pagination
import glob
from lib.PipeUtil import load_json_file, save_json_file, cfe, get_file_info
from lib.PipeAutoCal import fn_dir
import datetime 
from datetime import timedelta
from datetime import datetime as dt
import os

def filename_to_date(filename):
   fn, dir = fn_dir(filename)
   ddd = fn.split("_")
   if len(ddd) == 8:
      y,m,d,h,mm,s,ms,cam = ddd
   else:
      return("0000-00-00 00:00:00.0")
      print("BAD FILE:", ddd, len(ddd))
   start_time = y + "-" + m + "-" + d + " " + h + ":" + m + ":" + s + ".0"
   return(start_time)

def live_meteor_count(amsid, days, del_data):
   print("DAYS:", days)
   print("DEL:", str(del_data))
   md = "/mnt/ams2/meteors/"
   mc = []
   rc = []
   for day in days:
      mc,rc = day_count(md,amsid, day,mc,rc,del_data)
   return(mc,rc)

def get_meteors_in_range(station_id, start_date, end_date,del_data,filters=None):
   mi = []
   deleted = 0
   amsid = station_id

   hotspot_filter = 0
   nored = 0
   cam_filter = 0
   multi_filter = 0
   if filters is not None:
      if "multi" in filters:
         multi_filter = 1
      if "nored" in filters:
         nored = 1
      if "hotspot" in filters:
         hotspot_filter = 1
         print("HOTSPOT FILTER ON!")
      if "cam" in filters:
         print("CAM FILTER:", filters)
         xx,cam_id = filters.split(":")
         cam_filter = cam_id

   delete_log = "/mnt/ams2/SD/proc2/json/" + amsid + ".del"
   if cfe(delete_log) == 1:
      #os.system("./Process.py purge_meteors")
      deleted = 1


   start_dt = datetime.datetime.strptime(start_date + "_00_00_00", "%Y_%m_%d_%H_%M_%S") 
   end_dt = datetime.datetime.strptime(end_date + "_23_59_59", "%Y_%m_%d_%H_%M_%S") 
   # load AI and event files between the date range:
   delta = end_dt - start_dt 
   days = [start_dt + timedelta(days=i) for i in range(delta.days + 1)]
   for day in days:
      print("DAY:", day)

   if start_date == end_date:
      # get meteors from that days index file after building it on the fly!
      mif = "/mnt/ams2/meteors/" + start_date + "/" + start_date + "-" + station_id + ".meteors"
      if cfe(mif) == 1:
         mif_size, mif_old = get_file_info(mif)
      else:
         mif_old = 0
      if mif_old > 10:
         os.system("./Process.py mmi_day " + start_date)
      if cfe(mif) == 1:
         mi = load_json_file(mif)
      else:
         mi = []
 
      if hotspot_filter == 0 and nored == 0 and cam_filter == 0 and multi_filter == 0:
         print("NO FILTERS ON")
         return(mi)
      elif hotspot_filter == 1:
         filtered_index = []
         print("HOTSPOT FILTERS ON")
         for dd in mi:
            meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot, msm = dd 
            print("HOTSPOT", hotspot)
            if hotspot >= 4:
               filtered_index.append(dd)
      elif cam_filter != 0:
         filtered_index = []
         for dd in mi:
            meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot, msm  = dd 
            if cam_filter in meteor_file: 
               filtered_index.append(dd)
      elif multi_filter != 0:
         filtered_index = []
         for dd in mi:
            meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot, msm  = dd 
            if msm == 1:
               filtered_index.append(dd)


      filtered_index = sorted(filtered_index, key=lambda x: (x[6]), reverse=False)

      return(filtered_index)
   

   # check to see how many days in the range
   # if it is > 7 and use the month full index file (and have to del with bad sync.)
   # else use the main index file
   print(start_date, end_date)
   start_date = start_date.replace("-", "_")
   end_date = end_date.replace("-", "_")
   diff = end_dt - start_dt
   print("DIFF:", diff)
   days_in_range = int(diff.total_seconds() / 86300) 
   if days_in_range == 0:
      days_in_range = 1
   #if days_in_range <= 180:
   ai_dict = {}
   mso_dict = {}
   if True:
      for day_plus in range(0, days_in_range):
         this_date = start_dt + datetime.timedelta(days = day_plus)  
         this_day = this_date.strftime("%Y_%m_%d")
         #if deleted == 1:
         #   os.system("./Process.py mmi_day " + this_day)
         mif = "/mnt/ams2/meteors/" + this_day + "/" + this_day + "-" + station_id + ".meteors"
         ai_file = "/mnt/ams2/meteors/" + this_day + "/" + station_id + "_" + this_day + "_AI_DATA.info"
         events_file = "/mnt/ams2/meteors/" + this_day + "/" + station_id + "_" + this_day + "_EVENTS.info"
         ms_obs_file = "/mnt/ams2/meteors/" + this_day + "/" + this_day + "_MY_MS_OBS.info" 
         print("LOADING AI:", ai_file)
         if os.path.exists(ai_file) is True:
            temp = load_json_file(ai_file)
            for row in temp:
               ai_dict[row[1]] = row
         if os.path.exists(ms_obs_file) is True:
            temp = load_json_file(ms_obs_file)
            for row in temp:
               mso_dict[row] = {}
         print("This day:", this_day, mif)
         if cfe(mif) == 1:
            mit = load_json_file(mif)
            print("ADDING METEORS FOR DAY:", mif)
            for dd in mit:
               meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot, msm = dd 
               root_fn = meteor_file.split("/")[-1].replace(".json", "")
               print(root_fn)
               print(mso_dict)
               if nored == 1:
               #   meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot, msm = dd 
                  rf = meteor_file.replace(".json", "-reduced.json")
                  if cfe(rf) == 1:
                     reduced = 1
                  if reduced == 1:
                     print("NORED")
                     continue
               if hotspot_filter == 1:
               #   meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot, msm = dd 
                  print("HOSPOT VALUE", hotspot)
                  if hotspot <= 5:
                     continue
               if root_fn in mso_dict:
                  msm = 1
                  dd = [meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot, msm] 
               mi.append(dd)
         else:
            print("NO MIF:", mif)
   


   return(mi)
def day_count(md, amsid, day,mc,rc,del_data):
   jsons = glob.glob(md + day + "/*.json")
   for js in jsons:
      fn,dir = fn_dir(js)
      root = fn.replace(".json", "")
      print("ROOT:", root)
      if root not in del_data:
         if "reduced" in js:
            rc += 1 
         elif "reduced" not in js and "stars" not in js and "man" not in js and "star" not in js and "import" not in js and "archive" not in js:
            mc.append(js) 
         else:
            rc.append(js) 
      else:
         print("DEL FOUND:", js)
   return(mc,rc)

def meteors_by_day(amsid, in_data):
   json_conf = load_json_file("../conf/as6.json")
   mi_day_file  = "/mnt/ams2/meteors/" + amsid + "_mi_day.json"
   mi_day = load_json_file(mi_day_file)
   out = "<div>"
   last_day = None
   for day, stack_file, count in mi_day:
      if last_day is None:
         out += day + " - " + str(count) + " meteors<br>"
         out += "<div style='float:left'>"
         last_day = day
      if day != last_day:
         out += "</div><div style='clear:both'>"
         out += day + " " + str(count) + " meteors</div>"
         out += "<div style='float:left'>"
      vs = stack_file.replace("/mnt/ams2", "")
      vs = vs.replace(".jpg", "-tn.jpg")
      out += "<a href=/meteor/" + amsid + "/?start_day=" + day + "><img src=" +  vs + "></a>\n"
      last_day = day
   out += "</div></div>"
   return(out)


def trash_page (amsid, in_data) :
   start_day = in_data['start_day']
   if "rebuild" in in_data:
      print("REBUILD METEOR INDEX")
      os.system("./Process.py purge_meteors ")
      os.system("./Process.py mmi_day " + start_day)
      msg = "Meteor Index for " + start_day + " was rebuilt." 
   else:
      msg = ""
   date = start_day
   json_conf = load_json_file("../conf/as6.json")
   trash_dir = "/mnt/ams2/trash/" + start_day + "/" 
   print(trash_dir + "*.json") 
   trash_files = []
   trash_json = glob.glob(trash_dir + "*.json")
   for tj in trash_json:
      if "reduced" not in tj:
         trash_files.append(tj)
   template = make_default_template(amsid, "meteors_main.html", json_conf)

   rebuild_link = "<a href=/trash/" + amsid + "/?start_day=" + start_day + "&rebuild=1>Rebuild Meteor Index After Restoring Files</a><br>" + msg + "<br>"

   out = rebuild_link + """
   
      <div id='main_container' class='container-fluid h-100 mt-4 lg-l'>
      <div class='gallery gal-resize reg row text-center text-lg-left'>
      <div class='list-onl'>
      <div class='filter-header d-flex flex-row-reverse '>
      <button id="sel-all" title="Select All" class="btn btn-primary ml-3"><i class="icon-checkbox-checked"></i></button>
      <button id="restore-all" class="restore-all btn "><i class="icon-restore"></i> Restore <span class="sel-ctn">All</span> Selected</button>
     </div>
     </div>
   """
   print("TRASH:", trash_files)
   for trash in trash_files: 
      fn, dir = fn_dir(trash)
      jsid = fn.replace(".json", "")
      ht_class = "norm"
      meteor_detail_link = "#"
      vothumb = "/trash/" + date + "/" + jsid + "-stacked-tn.jpg" 
      #vothumb = vthumb.replace("-tn.jpg", "-obj-tn.jpg")
      vvid_link = "/trash/" + date + "/" + jsid + ".mp4" 
      vthumb = "/trash/" + date + "/" + jsid + "-stacked-tn.jpg" 
      show_datetime_cam = """
       Classify<BR>
       <div style="display: None">
       Clouds/Moon - Plane - Car Lights - Bird
       Satellite - Rocket - Aurora - Lightening
       Trees - 
       </div>
      """
      out += """
         <div id='""" + jsid + """' class='preview select-to """ + ht_class + """'>
            <a class='mtt' href='""" + meteor_detail_link + """' data-obj='""" + vothumb + """' title='Go to Info Page'>
               <img alt='""" + "ALT" + """' class='img-fluid ns lz' src='""" + vthumb + """'>
               <span>""" + show_datetime_cam + """</span>
            </a>

            <div class='list-onl'>
               <span>""" + show_datetime_cam + """</span>
            </div>
            <div class="list-onl sel-box">
               <div class="custom-control big custom-checkbox">
                  <input type="checkbox" class="custom-control-input" id='chec_""" + jsid + """' name='chec_""" + jsid + """'>
                  <label class="custom-control-label" for='chec_""" + jsid + """'></label>
               </div>
            </div>

            <div class='btn-toolbar'>
               <div class='btn-group'>
                  <a style='color:#ffffff' class='vid_link_gal col btn btn-primary btn-sm' title='Play Video' href='/dist/video_player.html?video=""" + vvid_link + """&vid_id=""" + jsid + """'>
                  <!--<i class='icon-play'>-->Play</i></a>
                  <a style='color:#ffffff' class='restore_meteor_gallery col btn btn-sm' title='Restore Detection' href="javascript:restore_meteor('""" + jsid + """')">Restore Meteor<i class='icon-restore'></i></a>
               </div>
            </div>
         </div>
      """




   template = template.replace("{MAIN_TABLE}", out)
   template = template.replace("{RAND}", "v3.0000")
   return(template)

def confirm_non_meteors(all_ids,json_conf):
   confirm_file = "/mnt/ams2/non_meteors/non_meteors_confirm.json"
   if os.path.exists(confirm_file) is False:
      conf_data = {}
   else:
      conf_data = load_json_file(confirm_file)
   ids = all_ids.split(",")[:-1]
   out = ""
   for fn in ids:
      out += fn + "<br>"
      conf_data[fn] = {}
   
   save_json_file(confirm_file,conf_data)
   return(out)

def non_meteors_main (amsid, in_data,json_conf) :
   out = """
   <script>
         $(function() {
            $('.restore_meteor').click(function() {
               restore_meteor($(this).attr('data-meteor'))
            })
         })
   </script>
   """
   out += """
      <div id='main_container' class='container-fluid h-100 mt-4 lg-l'>
      <div class='gallery gal-resize reg row text-center text-lg-left'>
      <div class='list-onl'>
      <div class='filter-header d-flex flex-row-reverse '>
      <button id="sel-all" title="Select All" class="btn btn-primary ml-3"><i class="icon-checkbox-checked"></i></button>
      <button id="del-all" class="del-all btn btn-danger"><i class="icon-delete"></i> Delete <span class="sel-ctn">All</span> Selected</button>
     </div>
     </div>
   """

   non_meteors = []
   nm_data_file = "/mnt/ams2/non_meteors/non_meteors.txt"
   confirm_file = "/mnt/ams2/non_meteors/non_meteors_confirm.json"
   if os.path.exists(confirm_file) is False:
      conf_data = {}
   else:
      conf_data = load_json_file(confirm_file)

   fp = open(nm_data_file)
   for line in fp:
      line = line.replace("\n", "")
      non_meteors.append(line)

   all_files_str = ""
   c = 0
   for nmf in sorted(non_meteors, reverse=True):
      fn = nmf.split("/")[-1]
      if fn in conf_data:
         continue
      if c > 100:
         break
      imgf = nmf.replace(".json", "-stacked-tn.jpg")

      all_files_str += fn + ","
      if os.path.exists(imgf):
         img_url = imgf.replace("/mnt/ams2", "")
         cell = meteor_cell(fn.replace(".json", ""), img_url)
         out += cell
         #out += "<img src=" + img_url + ">\n"
      c+= 1
   #print(out)
   out += "</div></div>"
   out += """
   <div style='width: 100%; border: 1px #000000 solid; text-align: center;'>
   <form method=post action="/confirm_non_meteors/" style='display: inline-block;'>
      <input type=hidden name="all_ids" value="{}">
      <input type=submit name="submit" value="Confirm All As Non Meteor">
   </form>
   <div>
   """.format(all_files_str)
   template = make_default_template(amsid, "meteors_main.html", json_conf)
   template = template.replace("{MAIN_TABLE}", out)
   return(template)

def non_meteors_main_old (amsid, in_data) :
   date = in_data['date']
   ai_file = "/mnt/ams2/meteors/" + in_data['date'] + "/" + amsid + "_" + in_data['date'] + "_" + "AI_DATA.info"
   out = ""
   if os.path.exists(ai_file) is True:
      ai_data = load_json_file(ai_file)
      for row in ai_data:
         decision, root_fn, hd_vid, roi, meteor_yn, fireball_yn, mc_class, mc_class_conf = row
         if decision == "ACCEPT":
            continue
         out += str(row) + "<br>"
         jsid = root_fn
         vvid_link = "/non_meteors/" + date + "/" + jsid + ".mp4" 
         meteor_detail_link = "#"
         ht_class = ""
         vothumbs = ""
         show_datetime_cam = ""
         vthumb = "/non_meteors/" + in_data['date'] + "/" + root_fn + "-stacked-tn.jpg"
         vothumb = "/non_meteors/" + in_data['date'] + "/" + root_fn + "-stacked-tn.jpg"
         out += """
            <div id='""" + jsid + """' class='preview select-to """ + ht_class + """'>
               <a class='mtt' href='""" + meteor_detail_link + """' data-obj='""" + vothumb + """' title='Go to Info Page'>
                  <img alt='""" + show_datetime_cam + """' class='img-fluid ns lz' src='""" + vthumb + """'>
                  <span>""" + show_datetime_cam + """</span>
               </a>

               <div class='list-onl'>
                  <span>""" + show_datetime_cam + """</span>
               </div>
               <div class="list-onl sel-box">
                  <div class="custom-control big custom-checkbox">
                     <input type="checkbox" class="custom-control-input" id='chec_""" + jsid + """' name='chec_""" + jsid + """'>
                     <label class="custom-control-label" for='chec_""" + jsid + """'></label>
                  </div>
               </div>

               <div class='btn-toolbar'>
                  <div class='btn-group'>
                     <a class='vid_link_gal col btn btn-primary btn-sm' title='Play Video' href='/dist/video_player.html?video=""" + vvid_link + """&vid_id=""" + jsid + """'>
                     <i class='icon-play'></i></a>
                     <a class='delete_meteor_gallery col btn btn-danger btn-sm' title='Delete Detection' data-meteor='""" + jsid + """'><i class='icon-delete'></i></a>
                  </div>
               </div>
            </div>
         """


   else:
      out += "no ai data: " + ai_file
   return(out)

def meteors_main (amsid, in_data) :
   print("meteors_main")
   json_conf = load_json_file("../conf/as6.json")
   delete_log = "/mnt/ams2/SD/proc2/json/" + amsid + ".del"
   if cfe(delete_log) == 1:
      try:
         del_data = load_json_file(delete_log)
      except:
         del_data = {}
   else:
      del_data = {}

   mif = "/mnt/ams2/meteors/" + amsid + "-meteors.info"
   out = ""
   tmeteors = []

   # get meteor array for date range supplied
   if in_data['end_day'] is None and in_data['start_day'] is not None:
      in_data['end_day'] = in_data['start_day']
   if in_data['end_day'] is None:
      in_data['end_day'] = dt.now().strftime("%Y_%m_%d")
   if in_data['start_day'] is None:
      in_data['start_day'] = dt.now().strftime("%Y_%m_%d")
   print("get_meteors_in_range")
   if in_data['ai_list'] is None:
      tmeteors = get_meteors_in_range(amsid, in_data['start_day'], in_data['end_day'],del_data, in_data['filter'])
   else:
      temp_meteors = load_json_file("/mnt/ams2/datasets/" + amsid + "_AI_METEOR_INDEX.json")
      tmeteors = []
      for data in temp_meteors:
         meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot,msm,mlabel,hlabel = data 
         if "ams2" not in meteor_file:
            station_id = meteor_file.split("/")[0]
            meteor_file = meteor_file.replace(station_id + "_", "")
            meteor_file = "/mnt/ams2/meteors/" + meteor_file[0:10] + "/" + meteor_file
         if in_data['ai_list'] in mlabel or in_data['ai_list'] in hlabel:
            tmeteors.append((meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot,msm,mlabel,hlabel))


      
   print("done get_meteors_in_range", len(tmeteors))

   if in_data['p'] is None:
      page = 1
   else:
      page = int(in_data['p'])
   if in_data['meteor_per_page'] is None:
      meteor_per_page = 100
   else:
      meteor_per_page = int(in_data['meteor_per_page'])
   if in_data['filter'] is None:
      filter = []
   else:
      filter = in_data['filter']
   if in_data['sort_by'] is None:
      sort_by = "date"
   else:
      sort_by = in_data['sorted_by']

   si = ((page - 1) * meteor_per_page)
   ei = page * meteor_per_page
   if ei >= len(tmeteors):
      ei = len(tmeteors)
   #out += ("SI/EI:" + str(si) + " " + str(ei))
   sorted_meteors = sorted(tmeteors, key=lambda x: (x[0]), reverse=True)
   these_meteors = sorted_meteors[si:ei]

   start_day = in_data['start_day']  
   end_day = in_data['end_day']  

   total_meteors = len(sorted_meteors)
   filter_display = ""
   msc = 0   
   ai_data = {}
   for meteor in these_meteors:
      if len(meteor) == 8:
         meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot,msm = meteor 
         print("METEOR:", msm)
         if msm == 1:
            msc += 1
      if len(meteor) == 10:
         meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot,msm,mlabel,hlabel = meteor 
   if msc > 0:
       link = "<a href='/meteor/" + amsid + "/?start_day=" + start_day + "&filter=multi'>"
       filter_display += "<span style='margin: 25px'>" + link + str(msc) + " multi-station meteors detected</a></span>"


   # header area
   out += """
      <div class='h1_holder  d-flex justify-content-between'>
         <h1><span class='h'><span id='meteor_count'>""" + str(total_meteors)+ """</span> meteors</span> captured between 
         <input value='""" + start_day + """' type="text" data-display-format="YYYY/MM/DD" data-action="reload" data-url-param="start_day" data-send-format="YYYY_MM_DD" class="datepicker form-control"> and
         <input value='""" + end_day + """' type="text" data-display-format="YYYY/MM/DD" data-action="reload" data-url-param="end_day" data-send-format="YYYY_MM_DD" class="datepicker form-control"> 
         showing meteors  """ + str(si) + "-" + str(ei) + """

""" + filter_display + """

         </h1>
         <div class='d-flex'>
            <div class='mr-2'><select name='rpp' id='rpp' data-rel='meteor_per_page' class='btn btn-primary'>"""
   opts = [25,50,100,250,500,1000]
   for i in opts:
      if i == meteor_per_page:
         out += "<option value='" + str(i) + "' selected>" + str(i) + " / page</option>"
      else:
         out += "<option value='" + str(i) + "'>" + str(i) + " / page</option>"

   out  += """</select></div>
            <div class='btn-group mr-3'><button id='show_gal' class='btn btn-primary act'><i class='icon-list'></i></button></div>
            <div class='page_h'>Page  """ + str(page) + """</div>
         </div>
      </div>
      <div id='main_container' class='container-fluid h-100 mt-4 lg-l'>
      <div class='gallery gal-resize reg row text-center text-lg-left'>
      <div class='list-onl'>
      <div class='filter-header d-flex flex-row-reverse '>
      <button id="sel-all" title="Select All" class="btn btn-primary ml-3"><i class="icon-checkbox-checked"></i></button>
      <button id="del-all" class="del-all btn btn-danger"><i class="icon-delete"></i> Delete <span class="sel-ctn">All</span> Selected</button>
     </div>
     </div>

   """
   #out += str(total_meteors) + " meteors between " + sd + " and " + ed

       
      

   for meteor in these_meteors:
      if len(meteor) == 6:
         meteor_file, reduced, start_time, dur, ang_vel, ang_dist = meteor 
         hotspot = 0
      elif len(meteor) == 7:
         meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot = meteor 
      elif len(meteor) == 8:
         meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot,msm = meteor 
      elif len(meteor) == 10:
         meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot,msm,mlabel,hlabel = meteor 
         print("BEF", meteor_file)
         if "ams2" not in meteor_file:
            station_id = meteor_file.split("/")[0]
            meteor_file = meteor_file.replace(station_id + "_", "")
            meteor_file = "/mnt/ams2/meteors/" + meteor_file[0:10] + "/" + meteor_file
         print("AFT", meteor_file)
      red_file = meteor_file.replace(".json", "-reduced.json")
      if cfe(red_file) == 1:
         reduced = 1
      if cfe(meteor_file) == 0:
         continue

      stime = start_time.split(".")[0]
      fn,dir = fn_dir(meteor_file)
      dfn = fn.replace(".json", "") 
      if dfn in del_data:
         print("ALREADY DELETED:", dfn)

         continue
      el = fn.split("_")
      camd = el[7]
      cel = camd.split("-")
      cam = cel[0]
      show_datetime_cam = stime + " - " + cam
      if reduced == 1:
         show_datetime_cam += "<BR>Ang Vel: " + str(ang_vel)[0:4] + " Duration: " + str(dur) 
   
      meteor_dt = datetime.datetime.strptime(stime, "%Y-%m-%d %H:%M:%S")
      mdate, mtime = stime.split(" ")
      mdate = mdate.replace("-", "_")
      jsf = meteor[0]
      vid = meteor[0].replace(".json", ".mp4")
      thumb = meteor[0].replace(".json", "-stacked-tn.jpg")
      thumb_png = meteor[0].replace(".json", "-stacked-tn.png")
      # convert thumb to jpg if it doesn't exist
      if cfe(thumb) == 0 and cfe(thumb_png) == 1:
         cmd = "convert " + thumb_png + " " + thumb + " >/dev/null"
         os.system(cmd)
     
      vthumb = thumb.replace("/mnt/ams2", "")
      vothumb = vthumb.replace("-tn.jpg", "-obj-tn.jpg")
      if cfe("/mnt/ams2/" + vothumb) == 0:
         vothumb = vothumb.replace(".jpg", ".png")

      fn, vdir = fn_dir(vthumb)   
      div_id = fn.replace("-stacked-tn.jpg", "")
      vvid_link = vid.replace("/mnt/ams2", "")
     
      jsid = div_id.replace("_", "")
      vfn = fn.replace("-stacked-tn.jpg", ".mp4")
      meteor_detail_link = "/meteor/" + amsid + "/" + mdate + "/" + vfn + "/"
      if reduced == 1:
         ht_class = "reduced"
      else:
         ht_class = "norm"
      if msm == 1:
         ht_class = "multi"
      print("MSM:", msm)
      # Per meteor cell / div
      out += """
         <div id='""" + jsid + """' class='preview select-to """ + ht_class + """'>
            <a class='mtt' href='""" + meteor_detail_link + """' data-obj='""" + vothumb + """' title='Go to Info Page'>
               <img alt='""" + show_datetime_cam + """' class='img-fluid ns lz' src='""" + vthumb + """'>
               <span>""" + show_datetime_cam + """</span>
            </a>

            <div class='list-onl'>
               <span>""" + show_datetime_cam + """</span>
            </div>
            <div class="list-onl sel-box">
               <div class="custom-control big custom-checkbox">
                  <input type="checkbox" class="custom-control-input" id='chec_""" + jsid + """' name='chec_""" + jsid + """'>
                  <label class="custom-control-label" for='chec_""" + jsid + """'></label>
               </div>
            </div>

            <div class='btn-toolbar'>
               <div class='btn-group'>
                  <a class='vid_link_gal col btn btn-primary btn-sm' title='Play Video' href='/dist/video_player.html?video=""" + vvid_link + """&vid_id=""" + jsid + """'>
                  <i class='icon-play'></i></a>
                  <a class='delete_meteor_gallery col btn btn-danger btn-sm' title='Delete Detection' data-meteor='""" + jsid + """'><i class='icon-delete'></i></a>
               </div>
            </div>
         </div>
      """

   if "/" in start_day:
      start_day = start_day.replace("/", "_")
      end_day = end_day.replace("/", "_")
   pagination = get_pagination(page, len(sorted_meteors), "/meteor/" + amsid + "/?meteor_per_page=" + str(meteor_per_page) + "&start_day=" + start_day + "&end_day=" + end_day, meteor_per_page )
   out += "</div><!--main container!--> <div class='page_h'><!--Page  " + format(page) + "/" +  format(pagination[2]) + "--></div></div> <!-- ADD EXTRA FOR ENDING MAIN PROPERLY. --> <div>"
   out += pagination[0]


   template = make_default_template(amsid, "meteors_main.html", json_conf)
   template = template.replace("{MAIN_TABLE}", out)



   return(template)


def meteor_cell(root_fn, thumb_url):
   jsid = root_fn #.replace("_", "")
   datecam = ""
   click_link = "#"
   video_url = thumb_url.replace("-stacked-tn.jpg", ".mp4")
   met_html = """
         <div id='{:s}' class='preview select-to norm'>
            <a class='mtt' href='{:s}' data-obj='{:s}' title='Go to Info Page'>
               <img alt='{:s}' class='img-fluid ns lz' src='{:s}'>
               <span>{:s}</span>
            </a>

            <div class='list-onl'>
               <span>{:s}<span>
            </div>
            <div class="list-onl sel-box">
               <div class="custom-control big custom-checkbox">
                  <input type="checkbox" class="custom-control-input" id='chec_{:s}' name='chec_{:s}'>
                  <label class="custom-control-label" for='chec_{:s}'></label>
               </div>
            </div>

            <div class='btn-toolbar'>
               <div class='btn-group'>
                  <a class='vid_link_gal col btn btn-primary btn-sm' title='Play Video' href='/dist/video_player.html?video={:s}'>
                  <i class='icon-play'></i></a>
                  <a class='restore_meteor col btn btn-danger btn-sm' title='Restore Meteor' data-meteor='{:s}'>
                  <i class="fas fa-meteor"></i>
</a>

               </div>
            </div>
         </div>

   """.format(jsid, click_link, thumb_url, datecam, thumb_url, datecam, datecam, jsid,jsid,jsid, video_url,jsid)
   return(met_html)
