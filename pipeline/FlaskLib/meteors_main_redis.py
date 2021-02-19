#!/usr/bin/python3

import os
# functions for loading data in and out of reddis
from FlaskLib.FlaskUtils import make_default_template
import json
import datetime
from lib.PipeUtil import load_json_file,save_json_file, cfe, convert_filename_to_date_cam
from lib.PipeDetect import get_trim_num
from lib.PipeAutoCal import fn_dir
import redis

import boto3
import socket
import subprocess
from boto3.dynamodb.conditions import Key
from lib.PipeUtil import get_file_info
import sys

def meteors_main_redis(amsid, req,json_conf):
   start_day = req['start_day'] 
   end_day = req['end_day']
   meteor_per_page = req['meteor_per_page'] 
   p = req['p'] 
   page = p
   sort_by = req['sort_by'] 
   filter = req['filter'] 


   if p is None:
      p = 0
      page = 0
   if meteor_per_page is None:
      meteor_per_page = 50 

   filters = {}
   if req['filter'] is not None:
      temp = req['filter'].split(";")

      for row in temp:
         if ":" in row :
            key,val = row.split(":")
            filters[key] = val

   if start_day is not None and end_day is None:
      dwild = start_day 
   else:
      dwild = "" 


   r = redis.Redis(decode_responses=True)

   # SCAN!
   meteors = []
   meteor_days = {}
   if True:
      result = []
      count =10
      pattern = ""
      keys = r.scan_iter(match="OB:" + dwild + "*" )
      add = 0
      for key in keys:
         add = 1
         data = r.get(key)
         key = key.replace("OB:", "")
         jdata = json.loads(data)
         jdata['sd'] = key

         if "multi" in filters:
            if "ms" not in jdata: 
               add = 0
            if "ms" in jdata:
               if jdata['ms'] != int(filters['multi']):
                  add = 0
         if "final" in filters:
            if "fv" not in jdata: 
               add = 0
            if "fv" in jdata:
               if len(jdata['fv']) == 0:
                  add = 0

         if start_day is not None and end_day is not None:
            end_day = start_day
            start_dt = datetime.datetime.strptime(start_day, "%Y_%m_%d")
            end_dt = datetime.datetime.strptime(end_day, "%Y_%m_%d")
            mday = jdata['tme'][0:10]
            if mday not in meteor_days:
               meteor_days[mday] = 0
            else:
               meteor_days[mday] += 1
            if "." in jdata['tme']:
               event_datetime = datetime.datetime.strptime(jdata['tme'], "%Y-%m-%d %H:%M:%S.%f")
            else:
               event_datetime = datetime.datetime.strptime(jdata['tme'], "%Y-%m-%d %H:%M:%S")
            if start_dt <= event_datetime <= end_dt:
               good = 1
            else:
               add = 0


         if add == 1:
            meteors.append(jdata)

   #for mday in sorted(meteor_days.keys(), reverse=True):
   #   out += mday + " " + str(meteor_days[mday]) + "\n"
   out = ""

   total_meteors = len(meteors)
   si = 0
   ei = total_meteors

   #meteors = sorted(meteors, reverse=True)
   meteors = sorted(meteors, key=lambda x: x['tme'], reverse=True)
   for data in meteors[si:ei]:
      show = 1
      if show == 1:
         rf = data['sd'].replace(".mp4", "")
         day = rf[0:10]
         root = "/mnt/ams2/meteors/" + day + "/" + rf
         stack_tn = root + "-stacked-tn.jpg"
         if cfe(stack_tn) == 1:
            vtn = stack_tn.replace("/mnt/ams2", "")
         #   out += "<img src='" + vtn + "'>"
         #out += str(data) + "\n"

         ht_class= ""
         jsid = rf
         meteor_detail_link = "/meteor/" + amsid + "/" + day + "/" + data['sd'] + "/" 
         vothumb = vtn.replace("-tn.jpg", "-obj-tn.jpg")
         vthumb = vtn
         (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(data['sd'])
         show_datetime_cam = data['tme'] + " " + sd_cam
         if "av" in data:
            show_datetime_cam += "<br> Vel:" + str(data['av'])[0:4]
         if "dur" in data:
            show_datetime_cam += " Dur:" + str(data['dur'])[0:4]
         vvid_link  = ""

         if data['rd'] == 1:
            ht_class = "reduced"
         else:
            ht_class = "norm"
         if "ms" in data:
            if data['ms'] == 1:
               ht_class = "multi"

   

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


   if start_day is not None and end_day is None:
      end_day = start_day


   #def page_header (filter_display = None, meteor_per_page=50, total_meteors="", start_day="", end_day="", si=0, ei=0, page=1):
   print ("TEST:", "", 50, total_meteors, start_day, end_day, si, ei, page)
   page_top = page_header ("", 50, total_meteors, start_day, end_day, si, ei, page)
   out = page_top + out + "</div>"


   template = make_default_template(amsid, "meteors_main.html", json_conf)
   template = template.replace("{MAIN_TABLE}", out)

   return(template)

def page_header (filter_display = None, meteor_per_page=50, total_meteors="", start_day="", end_day="", si=0, ei=0, page=1):
   if filter_display is None:
      filter_display = ""
   # header area
   out = """
      <div class='h1_holder  d-flex justify-content-between'>
         <h1><span class='h'><span id='meteor_count'>""" + str(total_meteors)+ """</span> meteors</span> captured between 
         <input value='""" + start_day + """' type="text" data-display-format="YYYY/MM/DD" data-action="reload" data-url-param="start_day" data-send-format="YYYY_MM_DD" class="datepicker form-control"> and
         <input value='""" + end_day + """' type="text" data-display-format="YYYY/MM/DD" data-action="reload" data-url-param="end_day" data-send-format="YYYY_MM_DD" class="datepicker form-control"> 
         showing meteors  """ + str(si) + "-" + str(ei) 
   if filter_display is not None:
      out += filter_display 
   out += """
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

   return(out)
