from flask import Flask, request
from FlaskLib.FlaskUtils import get_template, make_default_template
from FlaskLib.Pagination import get_pagination
import glob
from lib.PipeUtil import load_json_file, save_json_file, cfe
from lib.PipeAutoCal import fn_dir
import datetime 
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

   nored = 0
   if filters is not None:
      if "nored" in filters:
         nored = 1

   delete_log = "/mnt/ams2/SD/proc2/json/" + amsid + ".del"
   if cfe(delete_log) == 1:
      os.system("./Process.py purge_meteors")
      deleted = 1


   start_dt = datetime.datetime.strptime(start_date + "_00_00_00", "%Y_%m_%d_%H_%M_%S") 
   end_dt = datetime.datetime.strptime(end_date + "_23_59_59", "%Y_%m_%d_%H_%M_%S") 

   if start_date == end_date:
      # get meteors from that days index file after building it on the fly!
      os.system("./Process.py mmi_day " + start_date)
      mif = "/mnt/ams2/meteors/" + start_date + "/" + start_date + "-" + station_id + ".meteors"
      if cfe(mif) == 1:
         mi = load_json_file(mif)
      else:
         mi = []
      return(mi)

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
   if True:
      for day_plus in range(0, days_in_range):
         this_date = start_dt + datetime.timedelta(days = day_plus)  
         this_day = this_date.strftime("%Y_%m_%d")
         #if deleted == 1:
         #   os.system("./Process.py mmi_day " + this_day)
         mif = "/mnt/ams2/meteors/" + this_day + "/" + this_day + "-" + station_id + ".meteors"
         print("This day:", this_day, mif)
         if cfe(mif) == 1:
            mit = load_json_file(mif)
            print("ADDING METEORS FOR DAY:", mif)
            for dd in mit:
               if nored == 1:
                  meteor_file, reduced, start_time, dur, ang_vel, ang_dist = dd 
                  rf = meteor_file.replace(".json", "-reduced.json")
                  if cfe(rf) == 1:
                     reduced = 1
                  if reduced == 1:
                     print("NORED")
                     continue
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

def meteors_main (amsid, in_data) :

   json_conf = load_json_file("../conf/as6.json")
   delete_log = "/mnt/ams2/SD/proc2/json/" + amsid + ".del"
   if cfe(delete_log) == 1:
      del_data = load_json_file(delete_log)
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
   tmeteors = get_meteors_in_range(amsid, in_data['start_day'], in_data['end_day'],del_data, in_data['filter'])


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

   # header area
   out += """
      <div class='h1_holder  d-flex justify-content-between'>
         <h1><span class='h'><span id='meteor_count'>""" + str(total_meteors)+ """</span> meteors</span> captured between 
         <input value='""" + start_day + """' type="text" data-display-format="YYYY/MM/DD" data-action="reload" data-url-param="start_day" data-send-format="YYYY_MM_DD" class="datepicker form-control"> and
         <input value='""" + end_day + """' type="text" data-display-format="YYYY/MM/DD" data-action="reload" data-url-param="end_day" data-send-format="YYYY_MM_DD" class="datepicker form-control"> 
         showing meteors  """ + str(si) + "-" + str(ei) + """
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

      meteor_file, reduced, start_time, dur, ang_vel, ang_dist = meteor 
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
      fn, vdir = fn_dir(vthumb)   
      div_id = fn.replace("-stacked-tn.jpg", "")
      vvid_link = vid.replace("/mnt/ams2", "")
     
      jsid = div_id.replace("_", "")
      vfn = fn.replace("-stacked-tn.jpg", ".mp4")
      meteor_detail_link = "/meteors/" + amsid + "/" + mdate + "/" + vfn + "/"
      if reduced == 1:
         ht_class = "reduced"
      else:
         ht_class = "norm"
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
   pagination = get_pagination(page, len(sorted_meteors), "/meteors/" + amsid + "/?meteor_per_page=" + str(meteor_per_page) + "&start_day=" + start_day + "&end_day=" + end_day, meteor_per_page )
   out += "</div><!--main container!--> <div class='page_h'><!--Page  " + format(page) + "/" +  format(pagination[2]) + "--></div></div> <!-- ADD EXTRA FOR ENDING MAIN PROPERLY. --> <div>"
   out += pagination[0]


   template = make_default_template(amsid, "meteors_main.html", json_conf)
   template = template.replace("{MAIN_TABLE}", out)



   return(template)
