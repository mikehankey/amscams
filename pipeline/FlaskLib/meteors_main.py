from flask import Flask, request
from FlaskLib.FlaskUtils import get_template, make_default_template
from FlaskLib.Pagination import get_pagination
import glob
from lib.PipeUtil import load_json_file, save_json_file, cfe
from lib.PipeAutoCal import fn_dir
import datetime 


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
   if cfe(mif) == 1:
      mid = load_json_file(mif)
   else:
      out = "no index!"
      return(out)

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
      filter = in_data['filters']
   if in_data['sort_by'] is None:
      sort_by = "date"
   else:
      sort_by = in_data['sorted_by']

   if in_data['start_date'] is None and in_data['end_date'] is not None:
      in_data['start_date'] = in_data['end_date']

   if in_data['start_date'] is None and in_data['end_date'] is None:
      # do entire index with pagination
      #/mnt/ams2/meteors/AMS1-meteors.info
      sorted_meteors = sorted(mid, key=lambda x: (x[0]), reverse=False)
      total_meteors = len(mid)
      ed = mid[0][2]
      sd = mid[-1][2]
      tmeteors = mid

   elif in_data['start_date'] is not None and in_data['end_date'] is None:
      # do just 1 day
      sd = in_data['start_date'] + " 00:00:00"
      ed = in_data['start_date'] + " 23:59:59"
      for data in mid:
         if len(data) == 6:
            meteor, reduced, start_time, dur, ang_vel, ang_dist = data
            if in_data['start_date'] in meteor:
               tmeteors.append(data)
         else:
            print("BAD:", data)
            exit()

      total_meteors = len(tmeteors)
 

   elif in_data['start_date'] is not None and in_data['end_date'] is not None:
      #do a range of dates
      sd = in_data['start_date'] + " 00:00:00"
      ed = in_data['end_date'] + " 23:59:59"

      start_dt = datetime.datetime.strptime(sd, "%Y_%m_%d %H:%M:%S")
      end_dt = datetime.datetime.strptime(ed, "%Y_%m_%d %H:%M:%S")
      #out += "range of dates", + in_data['start_date'], in_data['end_date']
      for data in mid:
         meteor, reduced, start_time, dur, ang_vel, ang_dist = data
         stime = start_time.split(".")[0]
         meteor_dt = datetime.datetime.strptime(stime, "%Y-%m-%d %H:%M:%S")
         if start_dt <= meteor_dt <= end_dt:


            tmeteors.append(data)
      total_meteors = len(tmeteors)




   si = (page - 1) * meteor_per_page
   ei = page * meteor_per_page
   if ei >= len(tmeteors):
      ei = len(tmeteors)
   print("SI:", si, ei)
   #if sort_by == "date":
   sorted_meteors = sorted(tmeteors, key=lambda x: (x[0]), reverse=True)
   these_meteors = sorted_meteors[si:ei]
   print("THESE:", len(sorted_meteors), si, ei)
  
   start_day, start_time = sd.split(" ")
   start_day = start_day.replace("_", "/")
   end_day, end_time = ed.split(" ")
   end_day = end_day.replace("_", "/")
   # header area
   out += """
      <div class='h1_holder  d-flex justify-content-between'>
         <h1><span class='h'><span id='meteor_count'>""" + str(total_meteors)+ """</span> meteors</span> captured between 
         <input value='""" + start_day + """' type="text" data-display-format="YYYY/MM/DD" data-action="reload" data-url-param="start_date" data-send-format="YYYY_MM_DD" class="datepicker form-control"> and
         <input value='""" + end_day + """' type="text" data-display-format="YYYY/MM/DD" data-action="reload" data-url-param="end_date" data-send-format="YYYY_MM_DD" class="datepicker form-control"> 

         </h1>
         <div class='d-flex'>
            <div class='mr-2'><select name='rpp' id='rpp' data-rel='meteor_per_page' class='btn btn-primary'><option value="20">20 / page</option><option value="40">40 / page</option><option selected value="60">60 / page</option><option value="80">80 / page</option><option value="100">100 / page</option><option value="150">150 / page</option><option value="200">200 / page</option><option value="500">500 / page</option><option value="1000">1000 / page</option><option value="10000">10000 / page</option></select></div>
            <div class='btn-group mr-3'><button id='show_gal' class='btn btn-primary act'><i class='icon-list'></i></button></div>
            <div class='page_h'>Page  1/2</div>
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
      print("MF:", meteor_file) 
      if cfe(meteor_file) == 0:
         continue
      stime = start_time.split(".")[0]
      fn,dir = fn_dir(meteor_file)
      dfn = fn.replace(".json", "") 
      print("DEL?:", dfn)
      if dfn in del_data:

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


   pagination = get_pagination(page, len(tmeteors), "/meteors/" + amsid + "/?meteor_per_page=" + str(meteor_per_page) + "&start_day=" + start_day + "&end_day=" + end_day, meteor_per_page )
   out += "<div class='page_h'>Page  " + format(page) + "/" +  format(pagination[2]) + "</div></div>"
   out += pagination[0]
   out += "</div>"


   template = make_default_template(amsid, "meteors_main.html", json_conf)
   template = template.replace("{MAIN_TABLE}", out)
   out = """

      <div class='h1_holder d-flex justify-content-between'>
         <h1>Review Stacks by Day<input value='2020/11/28' type='text' data-display-format='YYYY/MM/DD'  data-action='reload' data-url-param='limit_day' data-send-format='YYYY_MM_DD' class='datepicker form-control'></h1>
         <div class='page_h'>Page  1/10</div></div>
         <div id='main_container' class='container-fluid h-100 mt-4 lg-l'>
   """



   return(template)
