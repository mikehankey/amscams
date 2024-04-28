import glob


from  lib.insert_meteor_json import insert_meteor_json
import math
import simplejson as json
import sqlite3
import cv2
import os
from lib.PipeAutoCal import fn_dir
from FlaskLib.Pagination import get_pagination
from flask import Flask, request
from FlaskLib.FlaskUtils import get_template, make_default_template
import time
import glob
from lib.PipeUtil import load_json_file, save_json_file, cfe, bound_cnt_new, calc_dist

from lib.PipeAutoCal import fn_dir

TEST = """
      /*
      */
"""

def move_ai_sample(new_label, sample_id):
   print("MOVE SAMPLE")
   resp = {}
   resp['msg'] = "ok" 
   return(resp)

def export_samples(station_id, options, json_conf):
   # /mnt/ams2/AI/DATASETS/EXPORT/MULTI_CLASS/ground/AMS1_ground_index.json
   #header = html_page_header(station_id)
   #js_code = js_learn_funcs(station_id)

   datasets = ai_datasets()
   if "ipp" in options:
      print("IPP:", options['ipp'])
      ipp = int(options['ipp'])
   else:
      ipp = 100
   if "p" in options:
      start = int(ipp) * int(options['p'])
      end = start + int(ipp)
      current_page = options['p']
   else:
      start = 0
      end = ipp
      current_page = 0
   print("SE", start, end)
   sample_vdir = "/AI/DATASETS/EXPORT/" 
   template = make_default_template(station_id, "live.html", json_conf)
   css = """
   <style>
      .show_hider {
         opacity: 0;
         color: #FFFFFF;
         font-size: 10px;
      }
      .show_hider:hover {
         opacity: 1;
         color: #FFFFFF;
         font-size: 10px;
      }
      .ai_sample {
         float: left;
      }
   </style>

   """
   out = css + """
   <h1>Image Classification Data Sets</h1><ul>\n
   """
   ai_export_dir = "/mnt/ams2/AI/DATASETS/EXPORT/"
   if os.path.exists(ai_export_dir) is False:
      return("The AI has not exported any data yet. " + ai_export_dir + " does not exist")
   if "d" not in options:
      export_files = os.listdir(ai_export_dir)
      for sdir in export_files :
         if sdir == "scan_stack_rois":
            continue
         ekey = sdir.replace(station_id + "_", "")
         if ekey in datasets:
            desc = datasets[ekey]['desc']
         else:
            desc = ""
         if os.path.isdir(ai_export_dir + sdir):
            out += "<li><a href=?d={:s}>{:s}</a> - {:s}</li>\n".format(sdir, sdir, desc)
      pdir = None
   else:
      pdir = options['d']
      export_files = os.listdir(ai_export_dir + options['d'])
      samples = "<div class=container-lg>"
      for sdir in export_files[start:end] :
         if os.path.isdir(ai_export_dir + options['d'] + "/" + sdir):
             url = pdir + "/" + sdir 
             out += "<li><a href=?d={:s}>{:s}</a></li>\n".format(url , url )
         else:
            print("NO ", sdir)
            if "jpg" in sdir :
               surl = sample_vdir + pdir + "/" + sdir
               samples += sample_thumb(surl)
      #pages = page_links(len(export_files), start, end)
      base_url = "/AI/MAIN/EXPORT/SAMPLES/{:s}/?d={:s}&ipp={:s}&p=".format(station_id, pdir , str(ipp))
      pages_list, pages = make_page_links(base_url, current_page, len(export_files), ipp)

      #print("pages:", pages)
      #samples += pages 

   #AMS1_FAILED_METEORS   AMS1_FIREBALL_METEORS  AUTO_MC  MULTI_CLASS  scan_stack_rois
   #AMS1_FAILED_METEORS2  .gz     METEORS  NON_METEORS
   out += "</ul>"
   out += "<div>"
   if pdir is not None:
      pdir_desc = pdir.split("/")[-1]
      sub_nav_header = "<h2>" + str(len(export_files)) + " " + pdir_desc +  " files </h2>"
   else:
      pdir_desc = ""
      sub_nav_header = ""
  
   out += sub_nav_header 
   if pdir is not None:
      out += samples
   out += "</div>"
   out += "<div style='clear: both'></div>"
   if pdir is not None:
      out += pages
   out += ui_javascript()
   template = template.replace("{MAIN_TABLE}", out)
   return(template)

def ai_datasets():
   # dict containing the exported datasets or primary dirs and what they mean
   datasets = {
      "METEORS": {
         "desc": "All items in this folder should be verified and real meteors."
      },
      "AUTO_MC": {
         "desc": "Mult-class items that have been automatically determined. Should be reviewed."
      },
      "FIREBALL_METEORS": {
         "desc": "Only samples of real fireball meteors should be in this folder."
      },
      "FAILED_METEORS": {
         "desc": "These items failed the meteor test but were later human approved as meteors. All items should be meteors."
      },
      "MULTI_CLASS": {
         "desc": "These items should be multi-class items that have been human verified already, using the AI confirmation tool."
      },
      "FAILED_METEORS2": {
         "desc": "These meteors passed the YN test but failed the multi-class meteor test. Lower confidence meteors but also good training samples."
      }
   }

   return(datasets)

def page_links(total, start, end):
   ipp = end - start
   print("INFO:", total, start, end, ipp)
   pages = ""
   total_pages = int(round(total / ipp, 0))
   for i in range (0, total_pages):
      pages += str(i) + " - "
   return(pages)

def make_sample_buttons(sample):
   labels = ['aurora', 'bird', 'bug', 'car', 'cloud', 'ground', 'moon', 'meteor', 'meteor_fireball', 'non_meteor', 'plane', 'rain', 'satellite', 'snow', 'star', 'unsure', 'ufo']
   icons = ['fa-solid fa-sun-dust', 'fas-5x fas fa-crow', 'fas fa-bug', 'fas fa-car', 'fas fa-cloud', 'fas fa-tree', 'fas fa-moon', 'fa-solid fa-star-shooting', 'fa-solid fa-meteor', 'fas fa-ban', 'fas fa-plane', 'fas fa-cloud-rain', 'fas fa-satellite', 'fas fa-snowflake', 'fas fa-star', 'fas fa-question-circle', 'fa-duotone fa-alien']

   t_buttons = "<div>"
   for i in range(0,len(labels)):
      t_buttons += """
         <a style="float: left; width:40px; height:40px" onclick="move_ai_sample('{:s}', '{:s}')" class="col btn btn-secondary btn-sm" title="{:s}" data-meteor="{:s}"><i class="{:s}"></i></a>
      """.format(labels[i], sample, labels[i], sample, icons[i])
   t_buttons += "</div>"
   t_buttons += "<div>"
   t_buttons += """<a style="float: left; width:40px; height:40px" onclick="show_sample_info('{:s}', '{:s}')" class="col btn btn-secondary btn-sm" title="{:s}" data-meteor="{:s}"><i class="{:s}"></i></a>""".format("info", sample, "info", sample, "fa-solid fa-circle-info")
   t_buttons += "</div>"

   return(t_buttons)

def sample_thumb(sample):
   sample_id = sample.split("/")[-1].replace(".", "_")
   t_buttons = make_sample_buttons(sample)
   #buttons = "xxx"
   img = """
      <div id={:s} style="background-size: cover; width: 200px; height: 200px; background-image: url({:s})" class="ai_sample">
      <div class="show_hider"> 
      {:s}
      </div>
      </div>
   """.format(sample_id, sample, t_buttons)
   return(img)

def timelapse_main(station_id, date,cam_num,json_conf):

   main_header = html_page_header(station_id)
   cam_id = json_conf['cameras']['cam' + str(cam_num)]['cams_id']
      
  #<script src="https://code.jquery.com/jquery-1.11.3.min.js"></script>
   tl_header = main_header + """
  <title>Time Lapse</title>
  <script type='text/javascript' src='/src/js/functions/mTimeLapse.js'></script>
  <style>
    * {
      margin:0px;
      padding:0px;
      font-family:sans-serif;
    }

    body {
      text-align: center;
    }

    input {
      background-color: slategray;
      padding:4px 12px;
      margin:4px;
      width:100px;
      color: rgb(250,252,255);
      border:0px;
    }

    input:hover {
      cursor: pointer;
      color:white;
    }

    #frames {
      width:100%;
    }

    #frame_front,
    #frame_back {
      position: absolute;
      top:10px;
      left:10px;
      width:95%;
    }

    #controls {
      opacity: .05;
      width:100%;
      position: fixed;
      bottom: 30px;
      left:10px;
      color:slategray;
      margin:10px auto;
    }

    #controls:hover {
      opacity: .8;
      width:100%;
      position: fixed;
      bottom: 30px;
      left:10px;
      color:slategray;
      margin:10px auto;
    }


    #data_stamp {
      font-family: monospace;
    }

    #mTimeLapse {
      display: none;
    }
  </style>
</head>
<body>
  <div >
   """
   tl_div1 = tl_div(date,cam_id)
   divs = tl_div1 
   divs += """
      </div>
      </body>
      </html>

   """
   final_out= tl_header + divs 
   return(final_out)

def tl_div(date,cam_id):
   out = """ <div id="mTimeLapse"> """
   files = sorted(glob.glob("/mnt/ams2/latest/" + date + "/" + "*" + cam_id + "*"))
   for filename in files:
      if "mark" in filename:
         continue
      desc = filename.split("/")[-1].replace(".jpg", "")   + "<br>&nbsp;<br>"
      desc = desc.replace("-marked", "")
      out += '''<img src="''' + filename.replace("/mnt/ams2", "") + '''" data-stamp="''' + desc  + '''">\n'''

   out += """  </div>
   """
   return(out)

def batch_update_labels(station_id, label_data):
   update_data = {}
   for row in label_data:
      rel = row.split("_")
      cmd = rel[0]
      new_class = rel[1]
      t_station_id = rel[2]
      year = rel[3]
      month = rel[4]
      dom = rel[5]
      date = year + "_" + month + "_" + dom 
      fn = row.replace("reclass_" + new_class + "_", "")
      if "-ROI.jpg" not in fn:
         fn += "-ROI.jpg"
      if date not in update_data:
         update_data[date] = {}
      update_data[date][fn] = new_class
   for date in update_data:
      ai_data_file = "/mnt/ams2/meteors/" + date + "/" + station_id + "_" + date + "_AI_SCAN.info"
      ai_data = load_json_file(ai_data_file)

      for fn in update_data[date]:
         print("UPDATE ", fn, " TO ", update_data[date][fn])
         if fn in ai_data:
            print("FOUND ", fn)
            ai_data[fn]['human_label'] = update_data[date][fn]
         else:
            print("NOT FOUND ", fn)
      save_json_file(ai_data_file, ai_data)
   return("OK")

def learn_main(station_id):

   machine_data_file = "/mnt/ams2/datasets/" + station_id + "_ML_DATA.json"
   human_data_file = "/mnt/ams2/datasets/" + station_id + "_human_data.json"
   ai_summary_file = "/mnt/ams2/datasets/" + station_id + "_AI_SUMMARY.json"
   obs_ids_file = "/mnt/ams2/meteors/" + station_id + "_OBS_IDS.json"
   if os.path.exists(machine_data_file) is False:
      machine_data = {}
   else:
      machine_data = load_json_file(machine_data_file)
   if os.path.exists(human_data_file) is False:
      human_data = {}
   else:
      human_data = load_json_file(human_data_file)
   if os.path.exists(obs_ids_file) is False:
      obs_ids = {}
   else:
      obs_ids = load_json_file(human_data_file)
   if os.path.exists(ai_summary_file) is False:
      ai_sum = {}
   else:
      ai_sum = load_json_file(ai_summary_file)
   out = ""
   for key in ai_sum:
      #img = "<img src="/datasets/meteor_yn/"
      out += key + " " + str(ai_sum[key]) +  "<br>\n"
   print(ai_summary_file)
   print("MD:", len(machine_data)) 
   print("HD:", len(human_data)) 
   print("OBS IDS:", len(obs_ids)) 

   return(out)


def html_page_header(station_id):

   header = """
<!doctype html>
<html lang="en">
        <head>

                <style>
                        @import url("https://cdn.jsdelivr.net/npm/bootstrap-icons@1.4.1/font/bootstrap-icons.css");
                        @import url("https://cdn.datatables.net/1.10.25/css/jquery.dataTables.min.css");

.show_hider {
   opacity: 0;
   color: #FFFFFF;
   font-size: 10px;
}
.show_hider:hover {
   opacity: 1;
   color: #FFFFFF;
   font-size: 10px;
}

.navbar-fixed-top, .navbar-fixed-bottom {
    /*position: fixed;*/
    right: 0;
    left: 0;
    z-index: 1030;
    margin-bottom: 0;
}
                </style>
                <noscript><meta http-equiv="refresh" content="0; url=/no-js.html" /></noscript>
    

      <!-- Required meta tags -->
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>AllSky.com </title>
               <script src="https://cdn.plot.ly/plotly-2.2.0.min.js"></script>
      <script src="https://kit.fontawesome.com/f3f9f77a06.js" crossorigin="anonymous"></script>
      <!--<script src="https://kit.fontawesome.com/25faff154f.js" crossorigin="anonymous"></script>-->
      <!-- Bootstrap CSS -->
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-eOJMYsd53ii+scO/bJGFsiCZc+5NDVN2yr8+0RDqr0Ql0h+rP48ckxlpbzKgwra6" crossorigin="anonymous">
      <link rel="alternate" type="application/rss+xml" title="RSS 2.0" href="https://www.datatables.net/rss.xml">
      <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/js/bootstrap.bundle.min.js" integrity="sha384-JEW9xMcG8R+pH31jmWH6WWP0WintQrMb4s7ZOdauHnUtxwoG2vI5DkLtS3qm9Ekf" crossorigin="anonymous"></script>
      <script type="text/javascript" language="javascript" src="https://cdn.datatables.net/1.10.24/js/jquery.dataTables.min.js"></script>

      <script>

      all_classes = ['meteor', 'cloud', 'bolt', 'cloud-moon', 'cloud-rain',  'tree', 'planes', 'car-side', 'satellite', 'crow', 'bug','chess-board','question']
      labels = ['meteor', 'clouds', 'lightening', 'moon', 'rain', 'tree', 'planes', 'cars', 'satellite', 'BIRDS', 'fireflies','noise','notsure']
      </script>
   """
   return(header)

def learning_review_day(station_id, review_date):
   header = """
<!doctype html>
<html lang="en">
        <head>

                <style>
                        @import url("https://cdn.jsdelivr.net/npm/bootstrap-icons@1.4.1/font/bootstrap-icons.css");
                        @import url("https://cdn.datatables.net/1.10.25/css/jquery.dataTables.min.css");
                </style>
                <noscript><meta http-equiv="refresh" content="0; url=/no-js.html" /></noscript>


      <!-- Required meta tags -->
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>AllSky.com </title>
               <script src="https://cdn.plot.ly/plotly-2.2.0.min.js"></script>

      <!--<script src="https://kit.fontawesome.com/25faff154f.js" crossorigin="anonymous"></script>-->
      <script src="https://kit.fontawesome.com/f3f9f77a06.js" crossorigin="anonymous"></script>
      <!-- Bootstrap CSS -->
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-eOJMYsd53ii+scO/bJGFsiCZc+5NDVN2yr8+0RDqr0Ql0h+rP48ckxlpbzKgwra6" crossorigin="anonymous">
      <link rel="alternate" type="application/rss+xml" title="RSS 2.0" href="https://www.datatables.net/rss.xml">
      <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/js/bootstrap.bundle.min.js" integrity="sha384-JEW9xMcG8R+pH31jmWH6WWP0WintQrMb4s7ZOdauHnUtxwoG2vI5DkLtS3qm9Ekf" crossorigin="anonymous"></script>
      <script type="text/javascript" language="javascript" src="https://cdn.datatables.net/1.10.24/js/jquery.dataTables.min.js"></script>

      <script>

      all_classes = ['meteor', 'cloud', 'bolt', 'cloud-moon', 'cloud-rain',  'tree', 'planes', 'car-side', 'satellite', 'crow', 'bug','chess-board','question']
      labels = ['meteor', 'clouds', 'lightening', 'moon', 'rain', 'tree', 'planes', 'cars', 'satellite', 'BIRDS', 'fireflies','noise','notsure']



      function click_mark_all_as(icon_type) {
         $(".gal_img" ).each(function( index ) {
           resource_id = this.id
           for (var i in all_classes) {
              var tdiv_id = "#reclass_" + labels[i] + "_" + resource_id
              console.log("RESET:", i, tdiv_id)
              $(tdiv_id).attr('style', 'color: #cdcdcd !important; padding: 2px; ');
              if ($(tdiv_id).hasClass('selected')) {
                 console.log("REMOVE SELECTED:", tdiv_id)
                 $(tdiv_id).toggleClass('selected')
              }
           }

           var tdiv_id = "#" + icon_type + "_" + resource_id
           if (icon_type == "reclass_meteor") {
              $(tdiv_id).toggleClass('selected')
              $(tdiv_id).attr('style', 'color: lime !important;padding: 2px');
           }
           else {
              $(tdiv_id).toggleClass('selected')
              $(tdiv_id).attr('style', 'color: red !important;padding: 2px');
           }

            console.log( index + ": " + this.id );
            
         });
      }


   // call : javascript:SwapDivsWithClick('div_id1','crop_img', 'vid_url',play_vid)
   function callAPI(api_url, method, data, callback,error_callback) {
                if (method == "GET") {
                        $.ajax({
                         url: api_url,
                         type: method,
                         dataType: "json",
                         crossDomain: true,
                         contentType: "application/json",

                         success: function(response){
                            callback(response)
                         },
                        error: function(response){
                             error_callback(response)
                         },
                        })
                }
                if (method == "POST") {
                        data = JSON.stringify(data)
                        $.ajax({
                         url: api_url,
                         type: method,
                         data: data,
                         dataType: "json",
                         crossDomain: true,
                         contentType: "application/json",

                         success: function(response){
                            callback(response)
                         },
                         error: function(response){
                             error_callback(response)
                         },
                        })
                }
        }

      function click_save_tags(station_id) {
         data = []

         $(".selected" ).each(function( index ) {
            data.push(this.id)
         });
         console.log(data)
         api_url = "/LEARNING/" + station_id + "/BATCH_UPDATE/" 
         method = "POST"
         api_data = {}
         api_data['label_data'] = data
         callAPI(api_url, method, api_data, callbackBatchUpdate,error_callback)
      }

   function callbackBatchUpdate(resp) {
   }
   function error_callback(resp) {
      console.log("ERROR" + resp)
   }

      function click_icon(icon_type, resource_id) {
           for (var i in labels) {
              var tdiv_id = "#reclass_" + labels[i] + "_" + resource_id
              console.log("RESET:", i, tdiv_id)
              $(tdiv_id).attr('style', 'color: #cdcdcd !important; padding: 2px; ');
              if ($(tdiv_id).hasClass('selected')) {
                 console.log("REMOVE SELECTED:", tdiv_id)
                 $(tdiv_id).toggleClass('selected')
              }
           }
           // set the icon for the
           var div_id = "#" + icon_type + "_" + resource_id
           console.log(i, tdiv_id)
           if (icon_type == "reclass_meteor") {
              $(div_id).toggleClass('selected')
              $(div_id).attr('style', 'color: lime !important;padding: 2px');
           }
           else {
              $(div_id).toggleClass('selected')
              $(div_id).attr('style', 'color: red !important;padding: 2px');
           }
           // write the detection to the jobs/local edits storage list
      }
      </script>

   """
   ai_file = "/mnt/ams2/meteors/" + review_date + "/" + station_id + "_" + review_date + "_AI_SCAN.info"
   msvdir = "/METEOR_SCAN/" + review_date + "/"
   if os.path.exists(ai_file) is True:
      ai_data = load_json_file(ai_file)
   else:
      ai_data = {}
   out_nm = ""
   out = ""

   day_labels = labels_for_day(station_id, review_date, ai_data)

   for fn in ai_data:
      resource_id = fn.replace("-ROI.jpg", "")
      img = "<img class='gal_img' id='" + resource_id + "' width=180 height=180 src=" + msvdir + fn + ">"
      main_class = "notsure"
      pclass1 = "notsure"
      print("AI", ai_data[fn])
      if "classes" in ai_data[fn]:
         if "mc_class" in ai_data[fn]['classes']:
            mc_class = ai_data[fn]['classes']['mc_class']
            main_class = mc_class.split("_")[0]
            desc = main_class 
            print("MC FOUND!", mc_class)
         if "meteor" not in main_class:
            if ai_data[fn]['classes']['meteor_yn'] is True or ai_data[fn]['classes']['meteor_fireball_yn'] is True:
               main_class = "meteor"   
      else:
         print("MC NOT FOUND!")
         desc = "not scanned"
         main_class = "not_scanned"
      if "human_label" in ai_data[fn]:
         main_class = ai_data[fn]['human_label']
         print("HUMAN LABEL FOUND!")
      desc = main_class + "<br>" + buttons
      if "meteor" in main_class:
         out += "<div style='margin: 5px; float: left'>" + img + "<br>" + desc + "</div>\n"
      else:
         out_nm += "<div style='margin: 5px; float: left'>" + img + "<br>" + desc + "</div>\n"
   final_out = header 
   review_button = """
      <button onclick="javascript: click_save_tags('""" + station_id + """')">Save Tags</button>
   """

   mark_all_button = """
      <button onclick="javascript: click_mark_all_as('reclass_meteor')">Mark All As Meteor</button>
   """

   final_out += review_button + mark_all_button + day_labels
   final_out += "<h1>Non-Meteor Detections?</h1>\n"
   final_out += "<p>The AI has a classified the following detections as NON-meteors. These detections will not be included in the archives unless they are part of a multi-station event OR human confirmed. </p>\n" + out_nm
   final_out += "<div style='clear: both'></div>"
   final_out += "<p> &nbsp; </p><h1>Meteor AI Confirmed Detections</h1>\n"
   final_out += "<p>The AI has classified the following detections as meteors. These detects will be archived as meteors. Please remove non-meteor detections that are mis-classified. </p>\n" + out


   return(final_out)

def labels_for_day (station_id, date, ai_data ):
   cats = {}
   for fn in ai_data:
      resource_id = fn.replace("-ROI.jpg", "")
      if "predict_top3" in ai_data[fn]:
         top3 = ai_data[fn]['predict_top3'] 
         pclass1 = top3[0][0]
         el = pclass1.split("_")
         if len(el) > 0: 
            main_class = pclass1.split("_")[0]
      else:
         main_class = "not_scanned"
      if main_class not in cats:
         cats[main_class] = 1
      else:
         cats[main_class] += 1

   html_nav = ""
   for cat in cats:
      html_nav += "<a href=/LEARNING/" + station_id + "/review?date=" + date + "&main_cat=" + cat + ">" + cat + " (" + str(cats[cat]) + ")</a> - "
   return(html_nav) 


def make_buttons(roi_file=None, selected=None):
   print("BUTTON SELECTED:", selected)
   icons = ['meteor', 'cloud', 'bolt', 'cloud-moon', 'cloud-rain',  'tree', 'plane', 'car-side', 'satellite', 'crow', 'bug','chess-board','question']
   labels = ['meteor', 'clouds', 'lightening', 'cloud-moon', 'rain', 'tree', 'planes', 'cars', 'satellite', 'BIRDS', 'fireflies','noise','notsure']
   color = "#000000"
   resource_id = roi_file.replace("-ROI.jpg", "")
   buttons = "<table width=180><tr><td>"
   for i in range(0,len(icons)):
      icon = icons[i]
      label = labels[i]
      if selected == label and selected == "meteor":
         color = "lime" 
         extra_class = "selected"
      elif selected == label :
         color = "#ff0000" 
         extra_class = "selected"
         print("SL", selected, label, color)
      else:
         print("NOT SL", selected, label, color)
         extra_class = "not_selected"
         color = "#cdcdcd" 
      buttons += """
         <a href="javascript:click_icon('reclass_{:s}', '{:s}')"><i style="padding: 2px; color: {:s}" class="fas fa-{:s} icon-link {:s}" title="{:s}" id="reclass_{:s}_{:s}"></i></a> 
      """.format(label, resource_id , color, icon, extra_class, label, label, resource_id)
   buttons += "</td></tr></table>"
   return(buttons)

def recrop_roi_confirm(station_id, root_file, roi):
   db_file = station_id + "_ALLSKY.db"
   con = sqlite3.connect(db_file)
   cur = con.cursor()

   # save the status in the DB
   # mv the ROITEMP file to the REAL ROI FILE
   # That's it!
   sql = """UPDATE meteors 
               SET human_roi = ?,
                   roi = ?,
                   reprocess = 1
             WHERE sd_vid = ?
         """
   task = (roi,roi,root_file + ".mp4")
   cur.execute(sql, task)
   print(sql,task)
   con.commit()

   # move the temp file to the real file. 

   ms_file1 = "/mnt/ams2/METEOR_SCAN/" + root_file[0:10] + "/" + station_id + "_" + root_file + "-ROITEMP.jpg"
   ms_file2 = "/mnt/ams2/METEOR_SCAN/" + root_file[0:10] + "/" + station_id + "_" + root_file + "-ROI.jpg"
   cmd = "mv " + ms_file1 + " " + ms_file2 
   print("MOVING", cmd)
   os.system(cmd)

   resp = {}
   resp['msg'] = "OK"
   return(resp) 
   

def recrop_roi(station_id, stack_fn, div_id, click_x, click_y,size,margin=.2):
   rand = str(time.time())
   div_id = div_id.replace("#", "")
   out= {}
   out['station_id'] = station_id
   out['click_x'] = click_x
   out['click_y'] = click_y
   out['div_id'] = "#" + div_id
   roi_url = "/METEOR_SCAN/" + div_id[0:10] + "/" + div_id + "-ROI.jpg"
   vs_dir = "/METEOR_SCAN/" + div_id[0:10] + "/" 
   msdir = "/mnt/ams2/METEOR_SCAN/" + div_id[0:10] + "/" 
   mdir = "/mnt/ams2/meteors/" + div_id[0:10] + "/" 
   if os.path.exists(msdir) is False:
      os.makedirs(msdir)
   stack_file = mdir + div_id + "-stacked.jpg"
   stack_img = cv2.imread(stack_file)
   print("Stack file:", stack_file)
   #stack_img = cv2.resize(stack_img, (640,360))
   stack_img = cv2.resize(stack_img, (1920,1080))

   # convert click x to 1080p from 360p (3x)
   hd_click_x = int(int(float(click_x))*3)
   hd_click_y = int(int(float(click_y))*3)
   size = int(size)
   x1 = int(hd_click_x) - int(size/2)
   y1 = int(hd_click_y) - int(size/2)
   x2 = int(hd_click_x) + int(size/2)
   y2 = int(hd_click_y) + int(size/2)
   if x1 < 0:
      x1 = 0
      x2 = size
   if y1 < 0:
      y1 = 0
      y2 = size
   if x1 >= 1920:
      print("X1 out of bounds!!!", x1,size)
      x1 = 1919 - size 
      x2 = 1919
   if y1 >= 1080:
      print("Y1 out of bounds!!!",y1,size)
      y1 = 1080 - size 
      y2 = 1079 

   roi = [x1,y1,x2,y2]
   print("X1Y1:", x1,y1,x2,y2)
   roi_img = stack_img[y1:y2,x1:x2]
   print("SIZE:", roi_img.shape)
   roi_v_temp_file = vs_dir + station_id + "_" + div_id + "-ROITEMP.jpg"
   roi_temp_file = msdir + station_id + "_" + div_id + "-ROITEMP.jpg"
   print("SAVING:", roi_temp_file)
   cv2.imwrite(roi_temp_file, roi_img)

   out['roi_url'] = roi_url
   out['stack_fn'] = stack_fn
   out['size'] = size  
   big_size = int(size) + 50
   small_size = int(size) - 50
   out['margin'] = margin

   # bigger / smaller func:  recrop_roi(station_id, stack_fn, div_id, click_x, click_y,size=150,margin=.2)
   out['html'] = """
      <img width=150 height=150 src='"""  + roi_v_temp_file + """?""" + rand + """'><br>
      <a href="javascript:confirmROI('""" + station_id + """','""" + div_id + """','""" + str(roi) + """')">Keep</a> - 
      <a href="javascript:recrop_roi('""" + station_id + """','""" + stack_fn + """','""" + div_id + """','""" + str(click_x) + """','""" + str(click_y) + """','""" + str(int(big_size)) + """','""" + str(margin) + """')">Bigger</a> - 
      <a href="javascript:recrop_roi('""" + station_id + """','""" + stack_fn + """','""" + div_id + """','""" + str(click_x) + """','""" + str(click_y) + """','""" + str(int(small_size)) + """','""" + str(margin) + """')">Smaller</a> 
   """ 
   out['msg'] = "recropped"
   return(out)

def recrop_roi_old(station_id, stack_fn, div_id, click_x, click_y,size=150,margin=.2):

   from Classes.ASAI import AllSkyAI
   # remake the ROI based on the filename and center click x,y
   stack_file = "/mnt/ams2/meteors/" + stack_fn[0:10] + "/" + stack_fn
   roi_file = "/mnt/ams2/METEOR_SCAN/" + stack_fn[0:10] + "/" + station_id + "_" + stack_fn.replace("-stacked.jpg", "-ROI.jpg")
   roi_url = "/METEOR_SCAN/" + stack_fn[0:10] + "/" + station_id + "_" + stack_fn.replace("-stacked.jpg", "-ROI.jpg?" + str(click_x))
   print("STATION_ID", station_id)
   ASAI = AllSkyAI()
   (img, img_gray, img_thresh, img_dilate, avg_val, max_val, thresh_val) = ASAI.ai_open_image(stack_file)
   img_dilate = cv2.resize(img_dilate,(1920,1080))
   cnts = ASAI.get_contours(img_dilate)

   stack_img = cv2.resize(img, (640,360))
   hd_stack_img = cv2.resize(img, (1920,1080))

   hdm_x = 1920 / 640 
   hdm_y = 1080 / 360
   click_x = int(click_x*hdm_x)
   click_y = int(click_y*hdm_y)

   cdist = 9999
   for x,y,w,h in cnts:
      cx = x + (w/2)
      cy = y + (h/2)
      dist = calc_dist((click_x, click_y),(cx,cy))
      print("CNT:", click_x, click_y, cx,cy, cdist, dist)
      cv2.rectangle(img_dilate, (x,y), (x+w, y+h) , (255, 255, 255), 1)
      if dist < cdist:
         cdist = dist
         best_cnt = [x,y,w,h] 
   
   x,y,w,h = best_cnt   
   cv2.rectangle(img_dilate, (x,y), (x+w, y+h) , (0, 255, 255), 1)
   cv2.imwrite("/mnt/ams2/test33.jpg", img_dilate)

   if w > h:
      size = int(w )
   else:
      size = int(h )
   cx = x + (w/2)
   cy = y + (h/2)
   size = int(size * .8)
   if size < 150:
      size = 150
   x1 = int(cx - int(size / 2))
   x2 = int(cx + int(size / 2))
   y1 = int(cy - int(size / 2))
   y2 = int(cy + int(size / 2))
   print(x1,y1,x2,y2)
   x1, y1, x2, y2 = bound_cnt_new(x1,y1,x2,y2,hd_stack_img,.25)
   print(x1,y1,x2,y2)
   print("W:", x2 - x1)
   print("H:", y2 - y1)
   roi_img = hd_stack_img[y1:y2,x1:x2]
   print("SAVING:", roi_file)
   cv2.imwrite(roi_file, roi_img)
   resp = {}
   resp['msg'] = "OK"
   resp['div_id'] = div_id 
   resp['roi_url'] = roi_url 
   print(x1,y1,x2,y2)





   return(resp)

def learn_footer(url, items, cur_page, ipp):
   nav = """
      <nav class="mt-3"><ul class="pagination justify-content-center">
   """
   total_items = len(items)
   pages = int(total_images / ipp)
   for i in range(1,pages):

      nav += """<li class='page-item active'><a class='page-link' href='""" + url + str(i) + """'>""" + i + """</a></li> """

   nav += """</li></ul></nav>"""

   return(nav)
#<li class='page-item'><a class='page-link' href='/meteor/AMS1/?meteor_per_page=100&start_day=2021_11_07&end_day=2021_11_07&p=2'>2</a></li><li class='page-item'><a class='page-link' href='/meteor/AMS1/?meteor_per_page=100&start_day=2021_11_07&end_day=2021_11_07&p=2'>Next &raquo;</a></li></ul></nav> 


def learning_meteors_tag(label, req, station_id = None):
   print(label)
   roi_file = req['learning_file']
   if station_id is None:
      json_conf = load_json_file("../conf/as6.json")
      station_id = json_conf['site']['ams_id']

   db_file = station_id + "_ALLSKY.db"
   con = sqlite3.connect(db_file)
   cur = con.cursor()

   sql = """ UPDATE meteors
             SET human_confirmed = ?,
                 meteor_yn = ?,
                 meteor_yn_conf = ?
             WHERE sd_vid = ? """
   print(sql)
   print(roi_file)

   if label == "METEOR": 
      task = [1,1,99,roi_file + ".mp4"]
   else:
      task = [-1,0,0,roi_file + ".mp4"]

   #cur = con.cursor()
   cur.execute(sql, task)
   con.commit()
   resp = {}
   resp['msg'] = "OK"

   return(resp)

def js_learn_funcs(station_id):

   #vid_html = vid_html + " - <a href=javascript:SwapDivLearnDetail('" + div1 + "','" + learn_img + "','" + crop_vid + "',2)>Full</a>"

   JS_SWAP_DIV_WITH_CLICK = """

   $(document).ready(function() {
    $("img").on("click", function(event) {
        //var id = $(this).data("id");
        //var x = event.pageX - this.offsetLeft;
        //var y = event.pageY - this.offsetTop;

    });
   });

   // ROI FUNCS
   function confirmROI(station_id, root_file, roi) {
      api_data = {}
      api_data['cmd'] = "confirm_roi"
      api_data['station_id'] = station_id
      api_data['root_file'] = root_file 
      api_data['roi'] = roi
      api_url = "/LEARNING/" + station_id + "/RECROP_CONFIRM/"
      console.log("CONFIRM ROI:", api_data)
      method = "POST"

      callAPI(api_url, method, api_data, callbackROI,error_callback)


   }
   function recrop_roi(station_id, stack_fn, div_id, click_x, click_y,size,margin) {

         var x = click_x
         var y = click_y
         var id = $(this).data("id");
         $(div_id).html(cur_html)
         //div_id = "#" + id
         api_data = {}
         api_data['cmd'] = "recrop_roi"
         api_data['station_id'] = station_id
         api_data['stack_fn'] = stack_fn 
         api_data['click_x'] = x
         api_data['click_y'] = y
         api_data['div_id'] = div_id
         api_data['size'] = size
         api_data['margin'] = margin
         console.log("API DATA", api_data)
         api_url = "/LEARNING/" + station_id + "/RECROP/"
         method = "POST"
         callAPI(api_url, method, api_data, callbackROI,error_callback)

         //$(div_id).css("width", "320px");
         //$(div_id).css("height", "180px");
         //$(div_id).css("background-size", "320px 180px");
      }


   function make_trash_icons(roi_file, size, color) {
      trash_icons = `
        <a href="javascript:click_icon('reclass_meteor', '` + roi_file + `')">
            <i style="padding: 5px; color: ` + color + `; font-size: ` + size + `px;"
               class="fas fa-meteor" title="confirm meteor" id="reclass_meteor_roi_file"></i>
        </a>
        <a href="javascript:click_icon('reclass_trash', '` + roi_file + `')">
            <i style="padding: 5px; color: ` + color + `; font-size: ` + size + `px;"
               class="bi bi-trash" title="non-meteor" id='reclass_trash_` + roi_file + `'></i>
        </a>
        <a href="javascript:click_icon('expand', '` + roi_file + `')">
            <i style="padding: 5px; color: ` + color + `; font-size: ` + size + `px;"
               class="bi bi-arrows-fullscreen" title="expand" id='expand_` + roi_file + `'></i>
        </a>
      `
   return (trash_icons)
   }

   function swap_html(div_id, new_html, width, height) {
         $(div_id).html(new_html)
         $(div_id).css("width", width);
         $(div_id).css("height", height);
         $(div_id).css("background-size", width + " " + height);
         //$(div_id).css("background-image", "url(" + img_url + ")");
         // reset the cap div
         cap_div_id = div_id + "_caption"
         $(cap_div_id).html("")

   }


   function click_icon(cmd, roi_file) {
      root_file = roi_file
      if (roi_file.includes("-RX_") == true) {
         el = roi_file.split("-RX_")
         div_id = "#" + roi_file.replace(".jpg", "")
         root_file = el[0]
 
      } else {
         div_id = "#" + roi_file.replace("-ROI.jpg", "")
         div_id = div_id.replace(/-/g, "")
         div_id = div_id.replace(/_/g, "")
      }
      div_id = "#" + roi_file
      if (cmd == "reclass_meteor" || cmd == "reclass_trash") {

           var tdiv_id = "#reclass_meteor_" + roi_file.replace(".jpg", "")
           var odiv_id = "#reclass_trash_" + roi_file.replace(".jpg", "")
           if (cmd == "reclass_meteor") {
              //$(tdiv_id).toggleClass('selected')
              $(tdiv_id).attr('style', 'font-size: 20px; color: lime !important;padding: 5px');
              $(odiv_id).attr('style', 'font-size: 20px; color: white !important;padding: 5px');
           }
           if (cmd == "reclass_trash") {
              //$(odiv_id).toggleClass('selected')
              $(odiv_id).attr('style', 'font-size: 20px; color: red !important;padding: 2px');
              $(tdiv_id).attr('style', 'font-size: 20px; color: white !important;padding: 2px');
           }

         if (cmd == "reclass_meteor") {
            ReLabel(div_id,roi_file,"METEOR",5)
         } else {
            ReLabel(div_id,roi_file,"NON_METEOR",5)
         }
      }
      if (cmd == "play") {
         cur_html = $(div_id).html()
         video_file = root_file + ".mp4"
         date = video_file.substr(0,10)
         video_url = "/meteors/" + date + "/" + video_file


         vid_html = "<div style='opacity: .8; width=704; height=576; border: 3px #ffffff solid;'><video id='player' width=700 height=572 controls autoplay loop><source src='"+ video_url + "'></video></div>"
         close_html = `<div><a href="javascript:swap_html(div_id, cur_html, '320px', '180px' )">close</a><br></div>`
         cap_div_id = "#" + root_file + "_caption"
         $(cap_div_id).html(close_html)

         $(div_id).css("width", "704px");
         $(div_id).css("height", "576px");
         $(div_id).css("background-size", "704px 576px");
         //$(div_id).css("background-image", "url(" + stack_url + ")");
         // DIV SWAP  
         $(div_id).html(vid_html)

      }

      if (cmd == "expand") {
         cur_html = $(div_id).html()
         if (root_file != "") {
            roi_file = root_file + "-ROI.jpg"
         }
    
         if (roi_file.includes("AMS_") == true) { 
            el = roi_file.split("_")
            station_id = el[0]
            stack_fn = roi_file.replace(station_id + "_", "")
         } 
         else {
            stack_fn = roi_file
            station_id = '"""  + station_id + """'
         }

         if (roi_file.includes("ROI.jpg")) {
            stack_fn = roi_file.replace("-ROI.jpg", "-stacked.jpg")
         }
         else {
            stack_fn = roi_file + "-stacked.jpg"
         } 
         date = stack_fn.substr(0,10)
         stack_url = "/meteors/" + date + "/" + stack_fn

         $(div_id).css("width", "640px");
         $(div_id).css("height", "360px");
         $(div_id).css("background-size", "640px 360px");
         $(div_id).css("background-image", "url(" + stack_url + ")");
         //ismap
         //new_html = `<a href="#` + stack_fn + `"></a><img data-id="` + stack_fn + `" class="ximg" width=640 height=360 src="` + stack_url + `" ismap></a>`
         //new_html = `<a href="javascript:swap_html(div_id, cur_html, '320px', '180px' )">
         new_html = ` <a href="javascript:void(0)">
              <img ismap data-id="` + root_file + `" class="ximg" width=640 height=360 src="` + stack_url + `" ></a>`
         // DIV SWAP  
         $(div_id).html(new_html)
      }
      $(".ximg").on("click", function(event) {
         var x = event.pageX - this.offsetLeft;
         var y = event.pageY - this.offsetTop;
         console.log("THIS", this)
         console.log("event", event)
         var id = $(this).data("id"); 
         $(div_id).html(cur_html)
         div_id = "#" + id 
         api_data = {}
         api_data['cmd'] = "recrop_roi"
         api_data['stack_fn'] = id
         api_data['click_x'] = x
         api_data['click_y'] = y
         api_data['div_id'] = div_id
         api_data['size'] = 150
         console.log(api_data)
         api_url = "/LEARNING/" + station_id + "/RECROP/" 
         method = "POST"
         callAPI(api_url, method, api_data, callbackROI,error_callback)

         //$(div_id).css("width", "320px");
         //$(div_id).css("height", "180px");
         //$(div_id).css("background-size", "320px 180px");

      })
    
      /*
      $("img").on("click", function(event) {
        var id = $(this).data("id");
        var x = event.pageX - this.offsetLeft;
        var y = event.pageY - this.offsetTop;
        //api_data = "stack_fn=" + id + "click_x=" + x + "&click_y=" + y 
        api_data = {}
        api_data['cmd'] = "recrop_roi"
        api_data['stack_fn'] = id
        api_data['click_x'] = x
        api_data['click_y'] = y
        api_data['div_id'] = div_id
        console.log(api_data)
        //api_url = "/LEARNING/" + station_id + "/RECROP/" 
        method = "POST"
        //callAPI(api_url, method, api_data, callbackROI,error_callback)

      });
      */

   }

   // call : javascript:SwapDivsWithClick('div_id1','crop_img', 'vid_url',play_vid)
   function callAPI(api_url, method, data, callback,error_callback) {
                if (method == "GET") {
                        $.ajax({
                         url: api_url,
                         type: method,
                         dataType: "json",
                         crossDomain: true,
                         contentType: "application/json",

                         success: function(response){
                            callback(response)   
                         }, 
                        error: function(response){
                             error_callback(response)   
                         }, 
                        })
                }
                if (method == "POST") {
                        data = JSON.stringify(data)
                        $.ajax({
                         url: api_url,
                         type: method,
                         data: data,
                         dataType: "json",
                         crossDomain: true,
                         contentType: "application/json",

                         success: function(response){
                            callback(response)   
                         }, 
                         error: function(response){
                             error_callback(response)   
                         }, 
                        })
                }
        }

   function callbackBatchUpdate(resp) {
   }

   function callbackROI(resp) {
      console.log("CB DIV ID " + resp['div_id'])

      //controls = make_trash_icons(roi_file,"#FFFFFF","20") 
      div_id = resp['div_id']
      $(div_id).css("width", "180px");
      $(div_id).css("height", "180px");
      $(div_id).css("background-size", "180px 180px");
      $(div_id).css("background-image", "url(" + resp['roi_url'] + ")");
      //new_html = controls
       //`<a href="#` + stack_fn + `"><img data-id="` + stack_fn + `" class="ximg" width=150 height=150 src="` + stack_url + `" ismap></a>`


      $(div_id).html(resp['html'])


      console.log(resp)
   }

 
   function callback(resp) {
      console.log(resp)
   }
   function error_callback(resp) {
      console.log("ERROR" + resp)
   }

   function ReLabel(div1, learn_img, label ,play_vid) {
      api_url = "/LEARNING/TAG/" + label + "?learning_file=" + learn_img
      data = {}
      method = "GET"
      callAPI(api_url, method, data, callback,error_callback)
   }
   function SwapDivLearnDetail(div1,learn_img, orig_meteor,play_vid)
   {
    
      js_link = "<a href=\\"javascript:SwapDivLearnDetail('" + div1 + "','" + learn_img + "','" + orig_meteor + "', 1)\\"> "
      orig_html = js_link + "<img width=150 height=150 src=" + learn_img + "></a>"
      d1 = document.getElementById(div1);
      if (play_vid == 1) {
         //vid_html = "<video width=160 height=90 controls autoplay loop><source src='"+ crop_vid + "'></video>"
         vid_html = "Relabel As<br>"
         vid_html = vid_html + "<a href=javascript:ReLabel('" + div1 + "','" + learn_img + "','" + "NONMETEORS" + "',2)>Non Meteor</a><br>"
         vid_html = vid_html + "<a href=javascript:ReLabel('" + div1 + "','" + learn_img + "','" + "METEORS" + "',2)>Meteor</a><br>"
         vid_html = vid_html + "<a href=/goto/meteor/" + orig_meteor + ">Details</a><br>"
         vid_html = vid_html + "<br><a href=javascript:SwapDivLearnDetail('" + div1 + "','" + learn_img + "','" + orig_meteor + "',0)>Close</a><br>"
         d1.innerHTML = vid_html
      
         //vid.play()
      }
      if (play_vid == 0) {
         div_item = document.getElementById(div1)
         div_item.innerHTML = orig_html 
      }
      if (play_vid == 2) {
         //full_vid = crop_vid.replace("CROPS", "VIDS")
         //full_vid = full_vid.replace("-crop-360p", "")
         //vid_html = "<video width=640 height=360 controls autoplay loop><source src='"+ full_vid + "'></video>"
         vid_html = "<br><a href=javascript:SwapDivLearnDetail('" + div1 + "','" + learn_img + "','" + orig_meteor + "',0)>Close</a>"
         //vid_html = vid_html + " - <a href=javascript:SwapDivLearnDetail('" + div1 + "','" + crop_img + "','" + crop_vid + "',2)>Full</a>"
         div_item = document.getElementById(div1)
         div_item.innerHTML = vid_html
      }

   }
   """

   return(JS_SWAP_DIV_WITH_CLICK)


def meteor_ai_scan(in_data, json_conf):

   rand = str(time.time())
   machine_data = load_json_file("/mnt/ams2/datasets/machine_data_meteors.json")
   human_data = load_json_file("/mnt/ams2/datasets/human_data.json")

   ams_id = in_data['ams_id']
   station_id = ams_id
   all_meteors = load_json_file("/mnt/ams2/meteors/" + ams_id + "_OBS_IDS.json")

   page = in_data['p']
   uc_label = in_data['label']
   label = in_data['label'].lower()
   items_per_page = in_data['ipp']
   template = make_default_template(ams_id, "live.html", json_conf)
   print("IPP:", items_per_page)
   out = ""

   js_code = js_learn_funcs(station_id)
   out += "<script>" + js_code + "</script>"

   if page is None:
      page = 1
   else:
      page = int(page)
   if items_per_page is None:
      items_per_page = 1000
   else:
      items_per_page = int(items_per_page) 
   si = (page-1) * items_per_page
   ei = si + items_per_page
   all_files = []
   #for lfile in sorted(machine_data, reverse=True):
   for lfile,ltime in all_meteors :
      rfile = lfile.replace(".json", "-ROI.jpg")
      if rfile in machine_data:
         tlabel, tscore = machine_data[rfile]
      else:
         tlabel = "UNKNOWN"
         tscore = 98
      roi_file = lfile.split("/")[-1].replace(".json", "-ROI.jpg")
      print("CHECK HUMAN:", roi_file)
      if roi_file in human_data:
         tlabel = human_data[roi_file]    
         print("HUMAN DATA FOUND!", roi_file, human_data[roi_file])


      if (label == "NONMETEORS" or label == "nonmeteors") and "NON" in tlabel:
         all_files.append((roi_file, tlabel, tscore))
      if (label == "METEORS" or label == "meteors") and "NON" not in tlabel and "UNKNOWN" not in tlabel:
         all_files.append((roi_file, tlabel, tscore))
      if (label == "UNKNOWN" or label == "unknown") and "UNKOWN" in tlabel:
         all_files.append((roi_file, tlabel, tscore))


   out += str(len(all_files)) + " AI items classified as " + label
   out += "<div>"
   for row in sorted(all_files, key=lambda x: (x[2]), reverse=True)[si:ei]:
      lfile, tlabel, tscore = row
      crop_img = "/METEOR_SCAN/" + lfile[5:15] + "/" + lfile.replace(".json", "-ROI.jpg")
      controls = ""


      controls = make_trash_icon(lfile,"#ffffff","20",selected) 
      div_id = lfile.replace("-ROI.jpg", "")
      div_id = div_id.replace("-", "")
      div_id = div_id.replace("_", "")
      out += """
             <div id='""" + div_id + """' class="meteor_gallery" style="background-color: #000000; background-image: url('""" + crop_img + """?""" + rand + """'); background-repeat: no-repeat; background-size: 180px; width: 180px; height: 180px; border: 1px #000000 solid; float: left; color: #fcfcfc; margin:5px "> """ + controls + """ </div>
      """
   out += "</div>"

   pagination = get_pagination(page, len(all_files), "/LEARNING/" + ams_id + "/AI_SCAN/" + uc_label + "?ipp=" + str(items_per_page) , items_per_page)
   out += "<div style='clear: both'></div>" 
   out += pagination[0]
    
   template = template.replace("{MAIN_TABLE}", out)
   return(template)

def search_form(in_data):
   print("IN:", in_data)
   station_id = in_data['station_id']
   datestr = in_data['datestr']
   human_conf = in_data['human_confirmed']
   ipp = in_data['ipp']
   mtype = in_data['label']


   if in_data['sort'] == "score_asc":
      sort_by = "score"
      order_by = "score ASC"
      sort_opt = "<option value=date >Date</option>"
      sort_opt += "<option value=score_asc selected>Score ASC</option>"
      sort_opt += "<option value=score_desc >Score DESC</option>"
   elif in_data['sort'] == "score_desc":
      sort_by = "score"
      order_by = "score DESC"
      sort_opt = "<option value=date >Date</option>"
      sort_opt += "<option value=score_asc >Score ASC</option>"
      sort_opt += "<option value=score_desc selected >Score DESC</option>"
   else:
      sort_by = "date"
      order_by = "MS.roi_fn"
      sort_opt = "<option value=date selected>Date</option>"
      sort_opt += "<option value=score_asc >Score ASC</option>"
      sort_opt += "<option value=score_desc >Score DESC</option>"

   if in_data['ipp'] is None:
      in_data['ipp'] = "100"

   limit = int(in_data['ipp'])
   limits = [25,100,250,500,1000]
   per_page_opt = ""
   for ll in limits:
      if int(ll) == int(limit):
         per_page_opt += "<option selected value='" + str(ll) + "'>" + str(ll) + "</option>"
      else:
         per_page_opt += "<option value='" + str(ll) + "'>" + str(ll) + "</option>"

   if in_data['p'] is None:
      offset = 0
      page_num = 0
   else:
      page_num = in_data['p']
      offset = int(in_data['p']) * int(in_data['ipp'])

   if in_data['label'] == "METEOR" or in_data['label'] == 'meteor':
      type_opt = "<option value=meteor selected>Meteors</option>"
      type_opt += "<option value=non_meteor >Non Meteors</option>"
   else:
      type_opt = "<option value=meteor >Meteors</option>"
      type_opt += "<option value=non_meteor selected>Non Meteors</option>"

   if "human_confirmed" not in in_data: 
      in_data['human_confirmed'] = "all"

   if in_data['human_confirmed'] == "confirmed" :
      human_opt = "<option value=all>All</option>"
      human_opt += "<option value=non_confirmed>Not Confirmed</option>"
      human_opt += "<option value=confirmed selected>Confirmed</option>"
   elif in_data['human_confirmed'] == "non_confirmed":
      human_opt = "<option value=all >All</option>"
      human_opt += "<option value=non_confirmed selected>Not Confirmed</option>"
      human_opt += "<option value=confirmed>Confirmed</option>"
   else:
      human_opt = "<option value=all selected>All</option>"
      human_opt += "<option value=non_confirmed>Not Confirmed</option>"
      human_opt += "<option value=confirmed>Confirmed</option>"

   script = """
    <script>
       function go(station_id) {
           select_type = document.getElementById('meteor_yn')
           var mtype = select_type.options[select_type.selectedIndex].value

           datestr = document.getElementById('datestr').value

           select_order_by = document.getElementById('order_by')

           var order_by = select_order_by.options[select_order_by.selectedIndex].value

           select_human = document.getElementById('human_confirmed')
           var human_conf = select_human.options[select_human.selectedIndex].value

           select_ipp = document.getElementById('ipp')
           var ipp = select_ipp.options[select_ipp.selectedIndex].value


           new_url = "/LEARNING/" + station_id + "/" + mtype.toUpperCase() + "?datestr=" + datestr + "&sort=" + order_by + "&human_confirmed=" + human_conf + "&ipp=" + ipp
           window.location.href = new_url


       }
    </script>
   """
   if datestr is None:
      datestr = ""
   print("STATION ID IS:", station_id, per_page_opt, datestr)
   form = """
    <div class='container'>
    <form name=search id='search' action="#" METHOD="GET">
    Show <select id=meteor_yn name="meteor_yn">""" + type_opt + """ </select>
    Date <input id=datestr type="date_str" value='""" + datestr + """' size=12>
    Order By <select id='order_by' name="order_by">""" + sort_opt + """ </select> """

   form += """ Confirmed <select id='human_confirmed' name="human_confirmed"> + """ + human_opt + """
    </select> """
   form += """ Items Per Page <select id='ipp' name="ipp">""" + per_page_opt + """ </select>"""

   form += """
    <button onclick="javascript: go('""" + station_id + """'); return false;">Go</button>
    </form>
    </div>

   """ 
   if order_by is None:
      order_by = "date"
   if human_conf is None:
      human_conf = "all"

   base_url = "/LEARNING/" + station_id + "/" + mtype.upper() + "?datestr=" + datestr + "&sort=" + order_by + "&human_confirmed=" + human_conf + "&ipp=" + str(ipp) + "&p="

   final = script + form
   return(final, base_url)

def weather_header(ams_id, in_data):
   header = """
   <div class='nav'>
   ALLSKY : Learning : Weather 
   </div> 
   """
   return(header)

def learning_weather(station_id, in_data):
   header = html_page_header(station_id)
   js_code = js_learn_funcs(station_id)
   wheader = weather_header(station_id, in_data)

   db_file = station_id + "_WEATHER.db"
   con = sqlite3.connect(db_file)
   cur = con.cursor()

   out = header 
   out += "<script>" + js_code + "</script>"
   out += wheader

   if  in_data['label'] == "main":
      out += """
         <h2>Learning Samples</h2>
         <ul>
         <li><a href=/LEARNING/""" + station_id + "/WEATHER/WC" + """>Weather Condition Samples</a>
         <li><a href=/LEARNING/""" + station_id + "/WEATHER/CT" + """>Cloud Type Samples</a>
         <li><a href=/LEARNING/""" + station_id + "/WEATHER/SW" + """>Severe Weather Samples</a>
         </ul>
      """

   if in_data['label'] == "WC":
      counts = sample_counts("WC", station_id, con, cur)
      out += """
         <h2>Weather Condition Samples</h2>
         <ul>
      """
      for row in counts:
         ss, lab, cc = row
         tag = lab

         out += "<li><a href=/LEARNING/" + station_id + "/WEATHER/" + tag + ">" + tag + "</a> " +  str(cc) + "</li>"
   elif "DAWN" in in_data['label'] or "DUSK" in in_data['label'] or "DAY" in in_data['label'] or "NIGHT" in in_data['label']:
      el = in_data['label'].split("_")
      sun_status = el[0]
      ai_weather_condition = in_data['label'] #.replace(sun_status + "_", "")
      data = select_samples(sun_status, ai_weather_condition, con, cur)
      for row in data:
         img_fn = row[0]
         el = img_fn.split("_")
         st_id = el[0]
         cam_id = el[1]
         year = el[2]
         mon = el[3]
         day = el[4]
         hour = el[5]
         mintemp = el[6]
         minute, picid = mintemp.split("-")
         img_file = "/mnt/ams2/datasets/weather/" + ai_weather_condition + "/" + img_fn
         img_url = img_file.replace("/mnt/ams2", "")
         out += "<div style='float: left'><img src=" + img_url + "></div>"

   return(out) 

def select_samples(sun_status, ai_weather_condition, con, cur):
   if True:
      sql = """
         SELECT filename ,
                WC.sun_status, 
                WS.ai_sky_condition  
           FROM ml_weather_samples WS 
     INNER JOIN weather_conditions WC 
             ON WC.local_datetime_key = WS.local_datetime_key 
          WHERE WS.ai_sky_condition = ?
       ORDER BY filename DESC 
      """

      
      sel_vals = [ai_weather_condition]
      print(sql)
      print(sel_vals)
      cur.execute(sql, sel_vals)
      rows = cur.fetchall()
      my_data = []
      print("LEN:", len(rows))
      for row in rows:
         print(row)
         my_data.append(row)
      return(my_data)      


def sample_counts(sample_type, station_id, con, cur):
   # TOTALS QUERY
   resp = []
   if sample_type == "WC":

      sql = """
         SELECT count(*), 
                WC.sun_status, 
                WS.ai_sky_condition  
           FROM ml_weather_samples WS 
     INNER JOIN weather_conditions WC 
             ON WC.local_datetime_key = WS.local_datetime_key 
       GROUP BY sun_status, ai_sky_condition
      """
      print(sql)
      cur.execute(sql)
      rows = cur.fetchall()
      for row in rows:
  
         rcount = row[0]
         sun_status = row[1]
         sky_condition = row[2]
         resp.append((sun_status, sky_condition, rcount))
   return(resp)

def learning_db_dataset(ams_id, in_data):
   db_file = ams_id + "_ALLSKY.db"
   con = sqlite3.connect(db_file)
   cur = con.cursor()
   station_id = ams_id

   search_form_html,base_url = search_form(in_data)
   header = html_page_header(ams_id)
   js_code = js_learn_funcs(station_id)
   header += "<script>" + js_code + "</script>"
   header += search_form_html

   if in_data['ipp'] is None:
      ipp = 100
   else:
      ipp = int(in_data['ipp'])
   limit = ipp
   if in_data['p'] is None:
      p = 0
   else:
      p = int(in_data['p'])
   
   # SORTING
   if in_data['sort'] == 'date':
      order_by = "root_fn DESC"
   elif in_data['sort'] == 'score_desc':
      order_by = "meteor_yn_conf DESC"
   elif in_data['sort'] == 'score_asc':
      order_by = "meteor_yn_conf asc"
   else:
      order_by = "root_fn DESC"
  
   # LIMIT / PAGE
   offset = p * ipp 
   where_clause = ""
   print("IN", in_data)
   sql_terms = []
   if in_data['datestr'] is not None:
      where_clause = "sd_vid like ? "
      sql_terms.append(in_data['datestr'] + "%")
   else:
      where_clause = "sd_vid like ? "
      sql_terms.append("20%")

   if in_data['label'] == "METEOR":
      where_clause += " AND meteor_yn = 1 "
   elif in_data['label'] == "NON_METEOR":
      where_clause += " AND meteor_yn = 0 "
   else:
      meteor_yn = 0
      where_clause += " AND (1 = 1) "

   if in_data['human_confirmed'] == "confirmed":
      if in_data['label'] == "METEOR":
         where_clause += " AND human_confirmed = 1 "
      elif in_data['label'] == "NON_METEOR":
         where_clause += " AND human_confirmed = -1 "

   if in_data['human_confirmed'] == "non_confirmed":
      where_clause += " AND human_confirmed = '0'"

   # TOTALS QUERY
   sql = """
         SELECT count(*)
            FROM meteors 
           WHERE """ + where_clause 
   cur.execute(sql, sql_terms)
   rows = cur.fetchall()
   total_count = rows[0][0]

   # ROWS QUERY
   sql = """
         SELECT root_fn, meteor_yn, ai_resp, human_confirmed, reduced, duration, ang_velocity, meteor_yn_conf
            FROM meteors 
           WHERE """ + where_clause + """
           ORDER BY """ + order_by + """ LIMIT """ + str(limit) + """ OFFSET """ + str(offset)

   cur.execute(sql, sql_terms)
   print(sql)
   rows = cur.fetchall()
   out = header
   cc = 0

   page_links, page_links_html = make_page_links(base_url, p, total_count, ipp)
   
   out += "<div class='container'>" + str(total_count) + " records matching search critera. Show " + str(ipp) + " items per page.</div>"
   out += "<div class='container clearfix'>" + page_links_html + "</div>"
   out += "<div class='container-fluid justify-content-center'>"
   for row in rows:
      out += meteor_image(cc, ams_id, row[0], row[1], row[2], row[3], row[4], row[5], row[6] )
      cc += 1
   out += "</div>"
   return(out)
 
def make_page_links(base_url, current_item, total_items, items_per_page):
   #pagination
   print("LINKS: ", current_item, total_items, items_per_page)
   total_pages = math.ceil(total_items / items_per_page)
   links = []
   html = "\n<div class=container><nav aria-label='Pages'><ul class='pagination'>\n"
   for c in range (0, total_pages ):
      show_c = str(c + 1)
      if c == int(current_item):
         active = "active"
      else:
         active = ""
      link = "<li class='page-item " + active + "'><a class='page-link' href=" + base_url + str(c) + ">" + show_c + "</a></li> \n"
      links.append(link)
      #html += "<a href=" + base_url + str(c) + ">" + show_c + "</a> "
      html += link
      if c > 2 and (c - 1) % 30 == 0:
         html += "</ul><ul class='pagination'>"
   html += "</ul>"
   html += "</nav></div>"
   return(links, html)

def meteor_image(count, station_id, root_fn, final_meteor_yn, ai_resp, human_confirmed, reduced, duration, ang_vel):
   rand = str(time.time())
   meteor_dir = "/mnt/ams2/meteors/" + root_fn[0:10] + "/"
   stack_file = meteor_dir + root_fn + "-stacked-tn.jpg"
   meteor_scan_dir = "/mnt/ams2/METEOR_SCAN/" + root_fn[0:10] + "/"
   roi_file = meteor_scan_dir + station_id + "_" + root_fn + "-ROI.jpg"
   roi_html = " NO ROI FILE? " + roi_file
   if os.path.exists(roi_file) is True:
      roi_img_url = roi_file.replace("/mnt/ams2", "") + "?" + rand
      roi_img_width="180"
      roi_img_height="180"
      roi_html = """<img width=120 height=120 style="border: 2px solid #ffffff" src=""" + roi_img_url + """>"""
   else:
      roi_html = ""
   if True:
      stack_url = stack_file.replace("/mnt/ams2", "")
      img_width="320"
      img_height="180"

   main_class = ""
   if human_confirmed == 1:
      selected = "meteor"
   elif human_confirmed == -1:
      selected = "trash"
   else:
      selected = None
 
 
   buttons = make_trash_icon(root_fn,"#ffffff","20",selected) 

   date_str = root_fn[0:19]
   ai_text = ""

   if reduced == 1:
      border_color = "gold"
   else:
      border_color = "yellow"

   if final_meteor_yn == 0:
      border_color = "red"

   if ai_resp is not None:
      ai_resp = json.loads(ai_resp)
      print(ai_resp)
      #if ai_resp["final_meteor_yn"] == 1:
      #   ai_text += "Meteor Final: " + str(ai_resp['final_meteor_yn_conf'])[0:4] + "<br>"
      ai_text += "MC: " + ai_resp['mc_class'] + " " + str(ai_resp['mc_class_conf'])[0:4] + "<br>"
   else:
      ai_text = ""
   ai_text += "Dur: " + str(duration)[0:4] + "<br>"
   ai_text += "Ang Vel: " + str(ang_vel)[0:4] + "<br>"

   roi_div = "<div><div style='float: left'>" + roi_html + "</div><div style='float:left'>" + ai_text + "</div></div><div style='clear: both'></div>"
   

   html = """
      <div style='float: left'>
      <div id="{:s}" style=" 
        background-image: url('{:s}'); 
        background-repeat: no-repeat; 
        background-size: {:s}px; 
        width: {:s}px; height: {:s}px; 
        border: 3px {:s} solid; 
        margin:5px "> 
        <div class="show_hider">
           
           {:s} {:s} {:s} <br>
           {:s}
        </div>
      </div> 
      <div id="{:s}_caption">&nbsp;</div>
      </div>
   """.format(root_fn, stack_url, img_width, img_width, img_height, border_color, buttons, date_str, str(count), roi_div, root_fn)
   return(html)
 
def learning_samples_db_dataset(ams_id, in_data):
   # SHOW METEORS & NON METEORS FROM THE LIVE METEOR ARCHIVE.
   # SQL REPORT FROM ML_SAMPLES TABLE
   header = html_page_header(ams_id)
   rand = str(time.time())
   label = "meteor"
   order_by = "MS.roi_fn"


   if in_data['label'] == "METEORS" or in_data['label'] == 'METEOR':
      label = "meteor"
   else:
      label = "non_meteor"

   high_conf = 0
   low_conf = 0
   if in_data['conf'] == "high" and label == 'meteor':
      print("High conf meteors") 
      high_conf = 1

   elif in_data['conf'] == "high" and label == 'non_meteor':
      print("High conf non meteors") 
      high_conf = 1
   elif in_data['conf'] == "low" and label == 'meteor':
      print("low conf meteors") 
      low_conf = 1



   if in_data['sort'] == "score_asc":
      sort_by = "score"
      order_by = "score ASC"
      sort_opt = "<option value=date >Date</option>"
      sort_opt += "<option value=score_asc selected>Score ASC</option>"
      sort_opt += "<option value=score_desc >Score DESC</option>"
   elif in_data['sort'] == "score_desc":
      sort_by = "score"
      order_by = "score DESC"
      sort_opt = "<option value=date >Date</option>"
      sort_opt += "<option value=score_asc >Score ASC</option>"
      sort_opt += "<option value=score_desc selected >Score DESC</option>"
   else:
      sort_by = "date"
      order_by = "MS.roi_fn"
      sort_opt = "<option value=date selected>Date</option>"
      sort_opt += "<option value=score_asc >Score ASC</option>"
      sort_opt += "<option value=score_desc >Score DESC</option>"

   print(str(in_data) + "<BR>")
   station_id = ams_id
   db_file = ams_id + "_ALLSKY.db"
   con = sqlite3.connect(db_file)
   if in_data['ipp'] is None:
      in_data['ipp'] = 100

   limit = int(in_data['ipp'])

   limits = [25,100,250,500,1000]
   per_page_opt = ""
   for ll in limits:
      if int(ll) == int(limit):
         per_page_opt += "<option selected value='" + str(ll) + "'>" + str(ll) + "</option>"
      else:
         per_page_opt += "<option value='" + str(ll) + "'>" + str(ll) + "</option>"

   if in_data['p'] is None:
      offset = 0
      page_num = 0
   else:
      page_num = in_data['p']
      offset = int(in_data['p']) * int(in_data['ipp'])
      
   cur = con.cursor()
   if label == "meteor":
      if high_conf == 1:
         plus_where = " WHERE ((MS.meteor_yn = 1 OR MS.fireball_yn = 1 or MS.human_confirmed == 1) AND MS.multi_class LIKE '%meteor%' or MS.human_confirmed == 1"
      elif low_conf == 1:
         plus_where = " WHERE ((MS.meteor_yn = 1 OR MS.fireball_yn = 1 or MS.human_confirmed == 1) AND (MS.meteor_yn_conf < 50 and MS.fireball_yn_conf < 50)) OR (MS.meteor_yn = 1 OR MS.fireball_yn = 1) AND MS.multi_class NOT LIKE '%meteor%'  "
         print("PLUS WHERE!")
      else:
         plus_where = " WHERE MS.meteor_yn = 1 OR MS.fireball_yn = 1 OR MS.multi_class LIKE '%meteor%' "
   else:
      plus_where = " WHERE MS.meteor_yn = 0 AND MS.fireball_yn = 0 AND MS.multi_class NOT LIKE '%meteor%' "

   #order_by = "M.root_fn "
   #order_by = "MS.meteor_yn_conf "
   #cur.execute("""
   #      SELECT M.root_fn, M.roi, MS.roi_fn, MS.meteor_yn, MS.meteor_yn_conf, MS.multi_class, MS.multi_class_conf, M.human_confirmed
   #         FROM meteors as M LEFT JOIN ml_samples as MS ON M.root_fn = MS.root_fn
   #         """ + plus_where + """
   #         ORDER BY """ + order_by + """ DESC LIMIT """ + str(limit) + """ OFFSET """ + str(offset)
   #   )

   cur.execute("""
         SELECT MS.root_fn, MS.roi_fn, MS.meteor_yn, MS.meteor_yn_conf, MS.multi_class, MS.multi_class_conf, MS.human_confirmed
            FROM ml_samples MS
            """ + plus_where 
      )
   rows = cur.fetchall()
   total_rows = len(rows)

   start_row = int(limit) * int(page_num)
   end_row = int(start_row) + int(limit)
   #row_desc = "page num " +  str(page_num) + " offset:" + str(offset) + "<br>"
   row_desc = "showing " + str(start_row) + " to " + str(end_row)

   cur.execute("""
         SELECT MS.root_fn, MS.roi_fn, MS.meteor_yn, MS.meteor_yn_conf, MS.fireball_yn, MS.fireball_yn_conf, MS.multi_class, MS.multi_class_conf, MS.human_confirmed,
            (MS.meteor_yn_conf + MS.fireball_yn_conf + MS.multi_class_conf) AS score

            FROM ml_samples MS
            """ + plus_where + """
            ORDER BY """ + order_by + """ LIMIT """ + str(limit) + """ OFFSET """ + str(offset)
      )
   rows = cur.fetchall()
   out = header

   js_code = js_learn_funcs()
   out += "<script>" + js_code + "</script>"

   #out +=str( in_data)

   #out += str(in_data)
   if label == "meteor":
      type_opt = "<option value=meteor selected>Meteors</option>"
      type_opt += "<option value=non_meteor >Non Meteors</option>"
   else:
      type_opt = "<option value=meteor >Meteors</option>"
      type_opt += "<option value=non_meteor selected>Non Meteors</option>"


   out += """
    <script>
       function go2(station_id) {
           select_type = document.getElementById('meteor_yn')
           var mtype = select_type.options[select_type.selectedIndex].value

           datestr = document.getElementById('datestr').value

           select_order_by = document.getElementById('order_by')

           var order_by = select_order_by.options[select_order_by.selectedIndex].value
           select_human = document.getElementById('human_confirmed')
           var human_conf = select_human.options[select_human.selectedIndex].value
           
           select_ipp = document.getElementById('ipp')
           var ipp = select_ipp.options[select_ipp.selectedIndex].value


           new_url = "/LEARNING/" + station_id + "/" + mtype.toUpperCase() + "?datestr=" + datestr + "&sort=" + order_by + "&human_confirmed=" + human_conf + "&ipp=" + ipp
           window.location.href = new_url
           

       }
    </script>
    <div class='container'>
    <form name=search id='search'>
    Show <select id=meteor_yn name="meteor_yn">""" + type_opt + """ </select>
    Date Str <input id=datestr type="date_str" value="">
    Order By <select id='order_by' name="order_by">""" + sort_opt + """ </select>
    Confirmed <select id='human_confirmed' name="human_confirmed">
       <option value=all>Show All</option>
       uoption value=confirmed>Confirmed Only</option>
       <option value=non_confirmed>Non Confirmed </option>
</select>
    Items Per Page <select id='ipp' name="ipp">""" + per_page_opt + """ </select>
    <button onclick="javascript: go('""" + station_id + """'); return false;">Go</button>
    </form>
    </div>
    <div class='container'> """ + str(total_rows) + """ """ + label + """ rows found matching criteria <br> """ + row_desc + """ </div>
   """

   root_img_dir = "/mnt/ams2/datasets/meteor_yn/"
   out += "ROWS:" + str(len(rows))
   out += " <div class='container'>"
   for row in rows:
      print("ROW:", row)
      root_fn = row[0]
      roi_fn = row[1]
      #roi = row[1]
      meteor_yn = row[2]
      meteor_yn_conf = row[3]
      meteor_fireball_yn = row[4]
      meteor_fireball_yn_conf = row[5]
      multi_class = row[6]
      multi_class_conf = row[7]
      if meteor_yn is False or meteor_yn == 0:
         meteor_yn_text = "Non Meteor"
      else:
         meteor_yn_text = "Meteor"
      if meteor_fireball_yn is False or meteor_fireball_yn == 0:
         meteor_fireball_yn_text = "Non Fireball"
      else:
         meteor_fireball_yn_text = "Fireball"
      if roi_fn is not None:
         print(station_id, roi_fn, root_img_dir)
         img_file = find_img_loc(station_id + "_" + roi_fn, root_img_dir)  
         if img_file is None:
            print("NO IMG FILE:", img_file)
         div_id = roi_fn.replace(".jpg", "")
         if img_file is not None:
            
            buttons = make_trash_icon(roi_fn,"#ffffff","20") 
            controls = "<div class='show_hider'>"
            controls += buttons
            controls += str(root_fn)[0:10] + "<br>"
            controls += str(meteor_yn_text) + " " + str(meteor_yn_conf)[0:4] + "<br>"
            controls += str(meteor_fireball_yn_text) + " " + str(meteor_fireball_yn_conf)[0:4] + "<br>"
            controls += str(multi_class) + " " + str(multi_class_conf)[0:4] + "<br>"
            controls += "</div>"
            print(img_file, meteor_yn, meteor_yn_conf, roi_fn)
            img_uri = img_file.replace("/mnt/ams2", "")
            #out += "<img src=" + img_uri + ">"
            out += """ <div id='""" + div_id + """' class="meteor_gallery" style="background-color: #000000; background-image: url('""" + img_uri + """?""" + rand + """'); background-repeat: no-repeat; background-size: 180px; width: 180px; height: 180px; border: 1px #000000 solid; float: left; color: #fcfcfc; margin:5px "> """ + controls + """ </div> """


         else:
            print("NO IMG:", img_file)
      else:
         print("NO ROI FILE.")

   out += " </div>"

   return(out)

def find_img_loc(img_name,root_dir):
   img_f = root_dir + "meteor/" + img_name
   print(img_f)
   if os.path.exists(img_f) is True:
      return(img_f)
   img_f = root_dir + "non_meteor/" + img_name
   print(img_f)

def learning_meteors_dataset(amsid, in_data):

   rand = str(time.time())
   json_conf = load_json_file("../conf/as6.json")
   machine_data_file = "/mnt/ams2/datasets/machine_data_meteors.json"
   if os.path.exists(machine_data_file) is True:
      machine_data = load_json_file(machine_data_file)
   else:
      machine_data = {}

   template = make_default_template(amsid, "live.html", json_conf)
   page = in_data['p']
   uc_label = in_data['label']
   label = in_data['label'].lower()
   sort_by = in_data['sort']
   filter_station = in_data['filter_station']
   filter_date = in_data['filter_date']
   items_per_page = in_data['ipp']
   print("IPP:", items_per_page)
   if page is None:
      page = 1
   else:
      page = int(page)
   if items_per_page is None:
      items_per_page = 1000
   else:
      items_per_page = int(items_per_page) 
   si = (page-1) * items_per_page
   ei = si + items_per_page
 
   
   
   files = []
   T_DIR = "/mnt/ams2/datasets/images/repo/" + label + "/"
   #V_DIR = "/mnt/ams2/datasets/images/validation/" + label + "/"
   all_files = []
   if filter_station is not None and filter_date is not None:
      wild = filter_station + "*" + filter_date + "*"
      meteor_training_files = glob.glob(T_DIR + wild)
   elif filter_station is not None:
      wild = filter_station + "*" 
      meteor_training_files = glob.glob(T_DIR + wild)
   elif filter_date is not None:
      wild = "*" + filter_date + "*" 
      meteor_training_files = glob.glob(T_DIR + wild)
      print("WILD:", T_DIR + wild)
   else:
      wild = "*" 
      meteor_training_files = glob.glob(T_DIR + wild)
   #meteor_validation_files = glob.glob(V_DIR + "*")
   for lfile in meteor_training_files:
      all_files.append(lfile)
   #for lfile in meteor_validation_files:
   #   all_files.append(lfile)




   total = len(all_files)
   js_code = js_learn_funcs()
   out = "<script>" + js_code + "</script>"
   out += "<div id='main_container' class='container-fluid h-100 mt-4 lg-l'>"
   out += "<h1>Machine Learning Data Set " + str(total) + " " + label + "</h1>"

   all_files_score = []
   for file in sorted(all_files, reverse=True):
      roi_file = file.split("/")[-1]
      if roi_file in machine_data:
         mdata = machine_data[roi_file]
         score = round(float(mdata[1]),3)
      else:
         mdata = "UNKNOWN"
         score = "99" 
      print("ROI FILE:", roi_file, mdata)
      all_files_score.append((file, mdata, float(score)))
   # GERD DO YOU SEE THIS?
   if sort_by is None:
      all_files_score =  sorted(all_files_score, key=lambda x: (x[2]), reverse=True) 
   elif sort_by == "date":
      all_files_score =  sorted(all_files_score, key=lambda x: (x[0]), reverse=True) 
   all_files = []
   for data in all_files_score:
    
      all_files.append(data[0]) 

   for row in sorted(all_files_score, key=lambda x: (x[2]), reverse=True)[si:ei]:
      file, mlab, score = row
      vfile = file.replace("/mnt/ams2", "")
      fn, dir = fn_dir(vfile)
      if fn in machine_data:
         ml, ms = machine_data[fn]
      else:
         ml = ""
         ms = ""
      fn = fn.split("_obj")[0]
      fn += ".mp4"
      orig_meteor = fn
      crop_img = vfile.replace("VIDS", "IMGS")
      crop_vid = vfile.replace("VIDS", "CROPS")
      #crop_vid = crop_vid.replace(".mp4", "-crop-360p.mp4")
      #crop_img = crop_img.replace(".mp4", "-crop-360p-stacked.jpg")
      div_id = fn
      vid_id = crop_vid 
      roi_file = crop_img.split("/")[-1]
      print("ROI FILE:", roi_file)
      #if roi_file in machine_data:
      #   mdata = machine_data[roi_file]
      #   score = str(mdata[1])[0:4]
      #else:
      #   score = ""
      orig_meteor = fn.replace("-ROI.jpg", ".mp4")
      if "AMS" in orig_meteor:
         station_id = orig_meteor.split("_")[0]
         orig_meteor = orig_meteor.replace(station_id + "_", "")
      js_link = "<a href=\"javascript: SwapDivLearnDetail('" + div_id + "', '" + crop_img + "','" + orig_meteor + "', 1)\">"
      #out += "<div style='width: 150px; height:150px; float: left; display=none' id='details_" + div_id + "'>" + js_link + "<video src=" + crop_vid + "></a></div>\n"
      #out += "<div style='width: 150px; height: 150px; float: left' id='" + div_id + "'>" + js_link + "<img width=150 height=150 src=" + crop_img +"?r=" + str(rand) + "></a></div>\n"
      if label == "nonmeteors":
         controls = "<a href=javascript:ReLabel('" + div_id + "','" + crop_img + "','" + "METEORS" + "',2)>Label Meteor</a><br>"
      else:
         controls = "<a href=javascript:ReLabel('" + div_id + "','" + crop_img + "','" + "NONMETEORS" + "',2)>Label Non Meteor</a><br>"
      controls += "<a href=javascript:ReLabel('" + div_id + "','" + crop_img + "','" + "TRASH" + "',2)>Trash Learning File</a><br>"
      orig_meteor = orig_meteor.replace(".mp4.mp4", ".mp4")
      controls += "<a href=/goto/meteor/" + orig_meteor + ">Details</a><br>"
      controls += str(score) + "<br>"
      date_str = orig_meteor[5:7]
      controls += date_str
     
      out += """
             <div class="meteor_gallery" style="background-color: #000000; background-image: url('""" + crop_img + """?""" + rand + """'); background-repeat: no-repeat; background-size: 150px; width: 150px; height: 150px; border: 1px #000000 solid; float: left; color: #fcfcfc; margin:5px "> """ + controls + """ </div>
      """
   out += "</div>"
   extra_vars = "&"
   if filter_station is not None:
      extra_vars += "&filter_station=" + filter_station
   if filter_date is not None:
      extra_vars += "&filter_date=" + filter_date

   pagination = get_pagination(page, len(all_files), "/LEARNING/" + amsid + "/" + uc_label + "?ipp=" + str(items_per_page) + extra_vars, items_per_page)
   out += "<div style='clear: both'></div>" 
   out += pagination[0]

   #def learn_footer(url, items, cur_page, ipp):

   template = template.replace("{MAIN_TABLE}", out)
    
   return(template)

def make_trash_icon(roi_file,ocolor,size,selected=None) :
   color = ocolor
   items = ['meteor', 'trash'] 
   trash_icons = ""
   for item in items:
      if selected == item:
         if item == 'meteor':
            color = 'lime'
         else:
            color = 'red'
      else:
         color = ocolor
      trash_icons += """
        <a href="javascript:click_icon('reclass_""" + item + """', '""" + roi_file.replace(".jpg", "") + """')">
            <i style="padding: 5px; color: """ + color + """; font-size: """ + size + """px;" 
               class='fas fa-""" + item + """' title='confirm '""" + item + """' id='reclass_""" + item + """_""" + roi_file.replace(".jpg", "") + """'></i></a>

      """ 
   color = ocolor   
   trash_icons += """
        <a href="javascript:click_icon('expand', '""" + roi_file.replace(".jpg", "") + """')">
            <i style="padding: 5px; color: """ + color + """; font-size: """ + size + """px;" 
               class="bi bi-arrows-fullscreen" title="expand" id='expand_""" + roi_file.replace(".jpg", "") + """'></i></a>
        <a href="javascript:click_icon('play', '""" + roi_file.replace(".jpg", "") + """')">
            <i style="padding: 5px; color: """ + color + """; font-size: """ + size + """px;" 
               class="fas fa-play-circle" title="expand" id='play_""" + roi_file.replace(".jpg", "") + """'></i></a>
   """

   trash_icons_test = """
        <a href="javascript:click_icon('reclass_trash', '""" + roi_file.replace(".jpg", "") + """')">
            <i style="padding: 5px; color: """ + color + """; font-size: """ + size + """px;" 
               class="bi bi-trash" title="non-meteor" id='reclass_trash_""" + roi_file.replace(".jpg", "") + """'></i></a>

        <a class="show_hider" href="javascript:click_icon('reclass_meteor', '""" + roi_file.replace(".jpg", "") + """')">
            <i  
               class="fas fa-meteor " title="confirm meteor" id='reclass_meteor_""" + roi_file.replace(".jpg", "") + """'></i></a>

        <a href="javascript:click_icon('reclass_trash', '""" + roi_file.replace(".jpg", "") + """')">
            <i class="bi bi-trash" title="non-meteor" id='reclass_trash_""" + roi_file.replace(".jpg", "") + """'></i></a>
        <a href="javascript:click_icon('expand', '""" + roi_file.replace(".jpg", "") + """')">
            <i class="bi bi-arrows-fullscreen" title="expand" id='expand_""" + roi_file.replace(".jpg", "") + """'></i></a>
   """




   return(trash_icons)


def batch_confirm_non_meteors(station_id, data_str):
   data_list = data_str.split(",")[:-1]
   for dd in data_list:
      print(dd)


def confirm_non_meteor_label(station_id, root_fn,label):
   # confirm non meteor mc label
   if ".mp4" not in root_fn:
      root_fn += ".mp4"
   db_file = station_id + "_ALLSKY.db"
   con = sqlite3.connect(db_file )
   cur = con.cursor()
   date = root_fn[0:10]

   # find the mj file is it in the non_meteor dir or the non_meteor_confirmed_dir?
   nmdir = "/mnt/ams2/non_meteors/" + date + "/" 
   nmcdir = "/mnt/ams2/non_meteors_confirmed/" + date + "/" 
   nmfile = "/mnt/ams2/non_meteors/" + date + "/" + root_fn.replace(".mp4", ".json")
   nmcfile = "/mnt/ams2/non_meteors_confirmed/" + date + "/" + root_fn.replace(".mp4", ".json")
   roi = [0,0,0,0]
   sd_vid = ""
   hd_vid = ""
   if os.path.exists(nmfile) is True:
      mj = load_json_file(nmfile) 
      sd_vid = mj['sd_video_file'].split("/")[-1]
      if "hd_trim" in mj:
         if mj['hd_trim'] != 0 and mj['hd_trim'] != None:
            hd_vid = mj['hd_trim'].split("/")[-1]
         else:
            hd_vid = ""

      else:
         hd_vid = ""
      if "hd_roi" in mj:
         roi = mj['hd_roi']
      if "ai" in mj:
         meteor_yn = mj['ai']['meteor_yn']
         fireball_yn = mj['ai']['fireball_yn']
         mc_class = mj['ai']['mc_class']
         mc_class_conf = mj['ai']['mc_class_conf']
      else:
         meteor_yn = -1
         fireball_yn = -1
         mc_class = ""
         mc_class_conf = -1

      # move files to the confirmed dir
      if os.path.exists(nmcdir) is False:
         os.makedirs(nmcdir)

      cmd = "mv " + nmdir + sd_vid.replace(".mp4", "*") + " " + nmcdir
      print(cmd)
      os.system(cmd)
      cmd = "mv " + nmdir + hd_vid.replace(".mp4", "*") + " " + nmcdir
      print(cmd)
      os.system(cmd)


   elif os.path.exists(nmcfile) is True:
      try:
         mj = load_json_file(nmcfile) 
      except:
         mj = {}
         meteor_yn = -1
         fireball_yn = -1
         mc_class = ""
         mc_class_conf = -1
         sd_vid = ""
      if "sd_video_file" in mj:
         sd_vid = mj['sd_video_file'].split("/")[-1]
      else:
         sd_vid = "" 
      if "hd_trim" in mj:
         if "/" in mj['hd_trim']:
            hd_vid = mj['hd_trim'].split("/")[-1]
         else:
            hd_vid = ""
      else:
         hd_vid = ""
      meteor_yn = -1
      fireball_yn = -1
      mc_class = ""
      mc_class_conf = -1

   else:
      print("NO METEOR FN?", nmfile, nmcfile)
      sd_vid = ""
      meteor_yn = -1
      fireball_yn = -1
      mc_class = ""
      mc_class_conf = -1

   # if the record doesn't already exist we should insert it. 
   sql = "SELECT sd_vid from non_meteors_confirmed WHERE sd_vid like ?" 
   cur.execute(sql, [root_fn + "%"])
   rows = cur.fetchall()
   if len(rows) == 0:

      isql = """INSERT OR REPLACE INTO non_meteors_confirmed (sd_vid, hd_vid, roi, meteor_yn, fireball_yn, multi_class, multi_class_conf, human_confirmed, human_label, last_updated)
                                                               VALUES (?,?,?,?,?,?,?,?,?,?)"""

      ivals = [ sd_vid, hd_vid, json.dumps(roi), meteor_yn, fireball_yn, mc_class, mc_class_conf, 1, label, int(time.time()*1000)] 
      print(isql,ivals)
      cur.execute(isql, ivals)
      con.commit()
   else:

      sql = "UPDATE non_meteors_confirmed set human_label = ? WHERE sd_vid = ?"
      task = [label, root_fn]
      cur.execute(sql, task)
      con.commit()
   return("Human confirmed label for non meteor " + root_fn + " " + label)

def confirm_non_meteor(station_id, root_fn):
   db_file = station_id + "_ALLSKY.db"
   con = sqlite3.connect(db_file)
   cur = con.cursor()
   date = root_fn[0:10]
   mfile = "/mnt/ams2/meteors/" + date + "/" + root_fn + ".json"
   nmfile = "/mnt/ams2/non_meteors/" + date + "/" + root_fn + ".json"

   print("MFILE:", mfile)
   if os.path.exists(mfile):
      try:
         mj = load_json_file(mfile)
      except:
         mj = {}
         mj['sd_vid'] = root_fn + ".mp4"
      mj['hc'] = 1
      save_json_file(mfile, mj)
      sql = "UPDATE meteors set human_confirmed = '-1' WHERE root_fn = ?"
      task = [root_fn]
      print(sql, task)
      cur.execute(sql, task)
      con.commit()

      # moving / del should happen by purge script
   elif os.path.exists(nmfile):
      # in non_meteor dir?
      mj = load_json_file(nmfile)
      sd_vid = mj['sd_video_file'].split("/")[-1]
      if "hd_trim" in mj:
         if mj['hd_trim'] is not None and mj['hd_trim'] != 0:
            hd_vid = mj['hd_trim'].split("/")[-1]
         else:
            hd_vid = sd_vid
      else:
         hd_vid = sd_vid

      nm_conf_dir = "/mnt/ams2/non_meteors_confirmed/" + sd_vid[0:10] + "/" 
      nm_dir = "/mnt/ams2/non_meteors/" + sd_vid[0:10] + "/" 

      sd_wild = nm_dir + sd_vid.replace(".mp4", "*")
      hd_wild = nm_dir + hd_vid.replace(".mp4", "*")
      human_confirmed = -1 
      if os.path.exists(nm_conf_dir) is False:
         os.makedirs(nm_conf_dir)

      cmd = "mv " + sd_wild + " " + nm_conf_dir
      print(cmd)
      os.system(cmd)
      cmd = "mv " + hd_wild + " " + nm_conf_dir
      print(cmd)
      os.system(cmd)
      #isql = """INSERT OR REPLACE INTO non_meteors_confirmed (sd_vid, hd_vid, roi, meteor_yn, fireball_yn, multi_class,
      #                                                         multi_class_conf, human_confirmed, last_updated)
      #                                                 VALUES (?,?,?,?, ?, ?, ?, ?, ?)"""

      isql = """INSERT OR REPLACE INTO non_meteors_confirmed (sd_vid, hd_vid, human_confirmed, last_updated)
                                                               VALUES (?,?,?,?)"""

      ivals = [ sd_vid, hd_vid, 1, time.time()] 
      cur.execute(isql, ivals)
      print(isql,ivals)
      con.commit()
   return("Human confirmed NON meteor " + root_fn)


def confirm_meteor(station_id, root_fn):
   db_file = station_id + "_ALLSKY.db"
   con = sqlite3.connect(db_file)
   cur = con.cursor()
   date = root_fn[0:10]
   hd_root = None
   out = ""
   mdir = "/mnt/ams2/meteors/" + date + "/" 
   nmdir = "/mnt/ams2/non_meteors/" + date + "/" 
   nmcdir = "/mnt/ams2/non_meteors_confirmed/" + date  + "/"
   print("Confirm", root_fn)


   mfile = "/mnt/ams2/meteors/" + date + "/" + root_fn + ".json"
   nmfile = "/mnt/ams2/non_meteors/" + date + "/" + root_fn + ".json"
   nmcfile = "/mnt/ams2/non_meteors_confirmed/" + date + "/" + root_fn + ".json"

   # Meteor files are in non meteor dir
   if os.path.exists(nmfile):
      print("FILE FOUND IN NON METEOR DIR!", nmfile)
      # TAG AND MOVE BACK
      try:
         mj = load_json_file(nmfile)
      except:
         # the mj is corrupted try to fix it. 
         print("MJ BAD:", nmfile)
         wild = nmfile.replace(".json", "*")
         cmd = "mv " + wild + " " + mdir
         os.system(cmd)
         mfn = mfile.split("/")[-1]
         cmd = "./Process.py fireball " + mfn + " &"
         print(cmd)
         os.system(cmd)


      mj['hc'] = 1
      if "hd_trim" in mj:
         if mj['hd_trim'] is not None and mj['hd_trim'] != "" and mj['hd_trim'] != 0:
            hd_root = mj['hd_trim'].split("/")[-1].replace(".mp4", "")
      sd_root = root_fn
      save_json_file(nmfile, mj)

      cmd = "mv " + nmdir  + root_fn + "* " + mdir 
      out += cmd + "<br>"
      print(cmd)
      os.system(cmd)

      sql = "UPDATE meteors set human_confirmed = '1' WHERE root_fn = ?"
      task = [root_fn]
      cur.execute(sql, task)


      if hd_root is not None:
         cmd = "mv " + nmdir  + hd_root + "* " + mdir 
         out += cmd + "<br>"
         print(cmd)
         os.system(cmd)
      print("SAVED JSON FILE WITH HC", mfile)


   elif os.path.exists(nmcfile):
      # TAG AND MOVE BACK
      try:
        mj = load_json_file(nmcfile)
      except:
        mj = {}
      mj['hc'] = 1
      save_json_file(mfile, mj)
      # RELOAD SQL / DELETE NMC

      cmd = "mv " + nmcdir  + root_fn + "* " + mdir 
      out += cmd + "<br>"
      print(cmd)
      os.system(cmd)

      if hd_root is not None:
         cmd = "mv " + nmcdir  + hd_root + "* " + mdir 
         out += cmd + "<br>"
         print(cmd)
         os.system(cmd)


      #move!
   elif os.path.exists(mfile):
      try:
         mj = load_json_file(mfile)
      except:
         mj = {}
         mj['sd_vid'] = mfile.replace(".json", ".mp4") 
         mfn = mfile.split("/")[-1]
         cmd = "./Process.py fireball " + mfn + " &"
         print(cmd)
         os.system(cmd)

      # XXX 
      mj['hc'] = 1
      save_json_file(mfile, mj)
      sql = "UPDATE meteors set human_confirmed = '1' WHERE root_fn = ?"
      task = [root_fn]
      cur.execute(sql, task)

   else:
      return("ERROR: NO METEOR FILE! " + root_fn)

   if True:
      # DELETE DELETED RECORDS / METEOR WILL BE RE_inserted on the next run
      sql = "delete from non_meteors WHERE meteor_fn like ?"
      task = [root_fn + "%"]
      cur.execute(sql, task)

      sql = "delete from non_meteors_confirmed WHERE sd_vid like ?"
      task = [root_fn + "%"]
      cur.execute(sql, task)

      sql = "delete from deleted_meteors WHERE sd_vid like ?"
      task = [root_fn + "%"]
      cur.execute(sql, task)


   con.commit()
   print("CONFIRM", root_fn)
   return("Human confirmed meteor " + root_fn)

def stats_by_month(cur):
   mon_stats = {}

   #total_meteors
   sql = """
            SELECT substr(root_fn,0,8) as month, count(*)
              FROM meteors
             WHERE deleted != 1
          GROUP BY month
          ORDER BY month desc
         """
   cur.execute(sql)
   rows = cur.fetchall()
   for row in rows:
      month, count = row
      if month not in mon_stats:
         mon_stats[month] = {}
         mon_stats[month]['confirmed'] = 0
         mon_stats[month]['non_confirmed'] = 0
         mon_stats[month]['total'] = 0
      mon_stats[month]['total'] = count

   sql = """
            SELECT substr(root_fn,0,8) as month, count(*)
              FROM meteors
             WHERE human_confirmed = 1 or human_confirmed = -1 
               AND deleted != 1
          GROUP BY month
          ORDER BY month desc
         """
   cur.execute(sql)
   rows = cur.fetchall()
   for row in rows:
      month, count = row
      if month not in mon_stats:
         mon_stats[month] = {}
         mon_stats[month]['confirmed'] = 0
         mon_stats[month]['non_confirmed'] = 0
         mon_stats[month]['total'] = 0
      mon_stats[month]['confirmed'] = count

   sql = """
            SELECT substr(root_fn,0,8) as month, count(*)
              FROM meteors
             WHERE (human_confirmed != 1 and human_confirmed != -1 )
               AND (deleted != 1 or deleted is NULL)
          GROUP BY month
          ORDER BY month desc
         """
   cur.execute(sql)
   rows = cur.fetchall()
   for row in rows:
      month, count = row
      if month not in mon_stats:
         mon_stats[month] = {}
         mon_stats[month]['confirmed'] = 0
         mon_stats[month]['non_confirmed'] = 0
         mon_stats[month]['total'] = 0
      mon_stats[month]['non_confirmed'] = count


   return(mon_stats)


def ai_dict(station_id, date, options, json_conf):
   print("AI DICT FOR :", station_id, date)
   ai_dict_file = "/mnt/ams2/meteors/" + date + "/" + station_id + "_" + date + "_AI_DICT.info"
   mdir = "/mnt/ams2/meteors/" + date + "/" 
   mvdir = "/meteors/" + date + "/" 
   msdir = "/mnt/ams2/METEOR_SCAN/" + date + "/" 
   template = make_default_template(station_id, "meteors_main.html", json_conf)

   out = ui_javascript()
   out += """
      <div id='main_container' class='container-fluid h-100 mt-4 ' style="border: 1px #000000 solid">
      """
   out += "<h1 >AI Dictionary for {} on {} </h1>".format(station_id, date)
   out += """
   """

   if os.path.exists(ai_dict_file) is True:

      ai_dict = load_json_file(ai_dict_file)
      ai_data = []
      for key in ai_dict:
         resp = ai_dict[key]
         resp['key'] = key
         ai_data.append(resp)

      ai_data = sorted(ai_data, key=lambda x: x['mc_class_conf'], reverse = True)

      groups = {}
      for row in ai_data:
         key = row['key']
         resp = ai_dict[key]
         mc_class = resp['mc_class']
         if mc_class not in groups:
            groups[mc_class] = ""
         root_fn = key.replace(".json", "")
         thumb_url = mvdir + root_fn + "-stacked-tn.jpg"
         multi_station = 0
         ico = None
         ctype = "meteor" 
         ai_info = "Meteor YN: {} Fireball YN: {} Auto Label: {} {}".format(round(resp['meteor_yn'],1), round(resp['fireball_yn'],1), resp['mc_class'], round(resp['mc_class_conf'],2))

         color = get_color(100-float(resp['meteor_yn']))

         cell = meteor_cell_html(root_fn, thumb_url, ai_info,ico, ctype, color, multi_station)
         img = resp['img']
         if "http://localhost" in img:
             img = img.replace("http://localhost/", "")
         if "https://localhost" in img:
             img = img.replace("https://localhost/", "")
         groups[mc_class] += cell
         #out += cell 
         #img

   else:
      out = "NO dict" + ai_dict_file

   for group in groups:
      out += """ 
         <h1>{}</h1>
         <div class='gallery gal-resize reg row text-center text-lg-left'>
      """.format(group)
      out += groups[group]
      out += "</div>"

   out += "</div></div>"
   template = template.replace("{MAIN_TABLE}", out)
   return(template)

def ai_stats_summary(cur):

   stats = {}

   #total_meteors
   sql = """
            SELECT count(*) 
              FROM meteors
         """
   cur.execute(sql)
   rows = cur.fetchall()
   for row in rows:
      count = row[0]
      stats['sql_meteors'] = count

   #conf status
   sql = """
            SELECT count(*), human_confirmed
              FROM meteors
          GROUP BY human_confirmed
         """
   cur.execute(sql)
   rows = cur.fetchall()
   stats['conf_status'] = {}
   stats['conf_status'][1] = 0
   stats['conf_status'][-1] = 0
   stats['conf_status'][0] = 0
   for row in rows:
      count, conf_status = row
      stats['conf_status'][conf_status] = count

   #low conf meteors <50%
   sql = """
            SELECT count(*) 
              FROM meteors
             WHERE meteor_yn_conf < 50
               AND fireball_yn_conf < 50
         """
   cur.execute(sql)
   rows = cur.fetchall()
   for row in rows:
      count = row
      stats['low_conf_meteors'] = count

   #high conf meteors >50%
   sql = """
            SELECT count(*) 
              FROM meteors
             WHERE meteor_yn_conf > 50
                OR fireball_yn_conf > 50
         """
   cur.execute(sql)
   rows = cur.fetchall()
   for row in rows:
      count = row
      stats['high_conf_meteors'] = count


   # by class
   sql = """
            SELECT count(*) , mc_class
              FROM meteors
             WHERE human_confirmed != -1
               AND human_confirmed != 1
               AND (deleted is null or deleted != 1)
          GROUP BY mc_class
         """
   cur.execute(sql)
   rows = cur.fetchall()
   stats['by_class'] = {}
   for row in rows:
      count,mc_class = row
      stats['by_class'][mc_class] = count

   # non confirmed non meteors by class
   sql = """
            SELECT count(*) , multi_class
              FROM non_meteors_confirmed
             WHERE human_label = ""  
               OR human_label is NULL
          GROUP BY multi_class 
         """
   cur.execute(sql)
   rows = cur.fetchall()
   stats['nc_non_meteors_by_class'] = {}
   for row in rows:
      count,mc_class = row
      if mc_class is None:
         mc_class = ""
      stats['nc_non_meteors_by_class'][mc_class] = count

   # non_meteors human confirmed and labeled by class
   sql = """
            SELECT count(*) , human_label 
              FROM non_meteors_confirmed
             WHERE human_label != ""  
               AND human_label is not NULL
          GROUP BY human_label 
         """
   cur.execute(sql)
   rows = cur.fetchall()
   stats['confirmed_non_meteors_by_class'] = {}
   for row in rows:
      count,mc_class = row
      if mc_class is None:
         mc_class = ""
      stats['confirmed_non_meteors_by_class'][mc_class] = count

      if mc_class not in stats['nc_non_meteors_by_class']: 
         stats['nc_non_meteors_by_class'][mc_class] = 0
   return(stats)

def ui_javascript():
   out = """
   <script>
         $(function() {
            $('.confirm_bird').click(function() {
               confirm_multi_class($(this).attr('data-meteor'), "birds")
            })
         })
         $(function() {
            $('.confirm_car').click(function() {
               confirm_multi_class($(this).attr('data-meteor'), "cars")
            })
         })
         $(function() {
            $('.confirm_cloud').click(function() {
               confirm_multi_class($(this).attr('data-meteor'), "cloud")
            })
         })
         $(function() {
            $('.confirm_ground').click(function() {
               confirm_multi_class($(this).attr('data-meteor'), "ground")
            })
         })
         $(function() {
            $('.confirm_moon').click(function() {
               confirm_multi_class($(this).attr('data-meteor'), "moon")
            })
         })
         $(function() {
            $('.confirm_plane').click(function() {
               confirm_multi_class($(this).attr('data-meteor'), "planes")
            })
         })
         $(function() {
            $('.confirm_rain').click(function() {
               confirm_multi_class($(this).attr('data-meteor'), "rain")
            })
         })
         $(function() {
            $('.confirm_satellite').click(function() {
               confirm_multi_class($(this).attr('data-meteor'), "satellite")
            })
         })
         $(function() {
            $('.confirm_snow').click(function() {
               confirm_multi_class($(this).attr('data-meteor'), "snow")
            })
         })


         $(function() {
            $('.confirm_bug').click(function() {
               confirm_multi_class($(this).attr('data-meteor'), "bug")
            })
         })
         $(function() {
            $('.confirm_non_meteor').click(function() {
               confirm_non_meteor($(this).attr('data-meteor'))
            })
         })
         $(function() {
            $('.confirm_meteor').click(function() {
               confirm_meteor($(this).attr('data-meteor'))
            })
         })
         $(function() {
            $('.confirm_fireball').click(function() {
               confirm_meteor($(this).attr('data-meteor'))
            })
         })

         $(function() {
            $('.confirm_spectra').click(function() {
               confirm_multi_class($(this).attr('data-meteor'), "spectra")
            })
         })
         $(function() {
            $('.confirm_rocket').click(function() {
               confirm_multi_class($(this).attr('data-meteor'), "rocket")
            })
         })
         $(function() {
            $('.confirm_noise').click(function() {
               confirm_multi_class($(this).attr('data-meteor'), "noise")
            })
         })
         $(function() {
            $('.confirm_chimney_smoke').click(function() {
               confirm_multi_class($(this).attr('data-meteor'), "chimney_smoke")
            })
         })
         $(function() {
            $('.confirm_smoke').click(function() {
               confirm_multi_class($(this).attr('data-meteor'), "smoke")
            })
         })
         $(function() {
            $('.confirm_empty').click(function() {
               confirm_multi_class($(this).attr('data-meteor'), "empty")
            })
         })
         $(function() {
            $('.confirm_unsure').click(function() {
               confirm_multi_class($(this).attr('data-meteor'), "unsure")
            })
         })



         function confirm_multi_class(data, label) {
             msg = data + " is " + label
             api_url = "/confirm_non_meteor_label/" + data + "?label=" + label
             method="GET"
             $.ajax({
                url: api_url,
                type: method,
                crossDomain: true,
                contentType: "application/json",

                success: function(response){
                   div_id = data.replaceAll("_", "") 
                   $("#" + div_id).fadeOut(1000, function() { $("#" + div_id).remove(); });
                    console.log(response)
                 },
                 error: function(response){
                    console.log(response)
                    //alert("ERR with confirm meteor")
                 },
              })
         }

         function show_sample_info(label, sample_id) {
            alert(sample_id)
         }

         function move_ai_sample(label, sample_id) {
             api_url = "/move_ai_sample?label=" + label + "&sample_id=" + sample_id
             var div_id = sample_id
             method="GET"
             $.ajax({
                url: api_url,
                type: method,
                crossDomain: true,
                contentType: "application/json",

                success: function(response){
                   var el = sample_id.split("/")
                   var idx = el.length - 1
                   var div_id = el[idx]
                   div_id = div_id.replace(".", "_")
                   $("#" + div_id).fadeOut(1000, function() { $("#" + div_id).remove(); });
                    console.log(response)
                 },
                 error: function(response){
                    console.log(response)
                    alert("ERR with mv meteor")
                 },
              })
         }


         function confirm_meteor(data) {
             api_url = "/confirm_meteor/" + data
             method="GET"
             $.ajax({
                url: api_url,
                type: method,
                crossDomain: true,
                contentType: "application/json",

                success: function(response){
                   div_id = data.replaceAll("_", "") 
                   $("#" + div_id).fadeOut(1000, function() { $("#" + div_id).remove(); });
                    console.log(response)
                 },
                 error: function(response){
                    console.log(response)
                    //alert("ERR with confirm meteor")
                 },
              })
         }
         function confirm_non_meteor(data) {
             api_url = "/confirm_non_meteor/" + data
             method="GET"
             $.ajax({
                url: api_url,
                type: method,
                crossDomain: true,
                contentType: "application/json",

                success: function(response){
                   div_id = data.replaceAll("_", "") 
                   $("#" + div_id).fadeOut(1000, function() { $("#" + div_id).remove(); });
                    console.log(response)
                    //console.log($(".mtt").length)

                 },

                 error: function(response){
                    console.log(response)
                    //alert("FAILED")
                 },
              })
         }
      function batch_all(con_type) {
         $(".mtt").each(function(i,item) {
            temp = $(item).data("obj")
            root_fn = temp.split(/[/]+/).pop();
            root_fn = root_fn.replace("-stacked-obj-tn.jpg","")
            if (con_type == 'non_meteors') { 
               confirm_non_meteor(root_fn)
            }
            else if (con_type == 'meteors') { 
               confirm_meteor(root_fn)
            }
            else {
               confirm_multi_class(root_fn, con_type)
            }
            console.log(root_fn, con_type)
         })
         //alert("ok")
      }
   </script>
   """
   return(out) 


def options_form(station_id, options):

   javascript = """
        <script>
        $(document).ready(function(){
           var form = document.querySelector('#search_form');
           form.addEventListener('change', function() {
               var station_id = $("#station_id").val()
               var hc = $("#hc").prop('checked')
               var ctype = $("#ctype").prop('checked')
               var rc = $("#rc").val()
               var db = $("#db").val()
               var in_date = $("#in_date").val().replace(/-/g, "_")
               var order_by = $("#order_by").val()
               var label = $("#label").val()
               var msg = station_id + " " + in_date + " " + hc + " " + db + " " + rc 
               var url = "/AIREJECTS/" + station_id + "/?"
               if (in_date == "") {
                  in_date = "20"
               }


               if (db == "meteor_db") {
                  url += "db=meteor_db&list=by_date&in_date=" + in_date + "&"
               }
               else {
                  url += "db=non_meteor_db&list=non_meteor_confirmed&in_date=" + in_date + "&"

               }
               if (hc === true) {

                  if (db == "meteor_db") {
                     url += "hc=1&"
                  } 
                  else {
                     url += "hc=-1&"

                  }
               }
               if (label != "" && label !== undefined) {
                  url += "label=" + label + "&"
           
               }
               url += "rc=" + rc + "&"
               url += "order_by=" + order_by + "&"
               var temp = window.location.href.split("/")
               var proto = temp[0] + "//"
               //alert(proto + location.hostname + url)
               window.location.replace(proto + location.hostname + url)

           })
        })
        </script>
   """
   lb_types, icons = mc_types()
   lb_types = sorted(lb_types)
   label_opt = ""
   if "label" not in options:
      options['label'] = ""
   label_opt += "<option selected value=''>AI Label</option>"
   for i in range(0, len(lb_types)):
      code = lb_types[i]
      icon = icons[i]
      if code == options['label']:
         label_opt += "<option selected value='{}'>{}</option>".format(code,code)
      else:
         label_opt += "<option value='{}'>{}</option>".format(code,code)


   ord_op = [
         ['meteor_yn_asc', "Meteor YN Score Asc (low to high)"],
         ['meteor_yn_desc', "Meteor YN Score Desc (high to low)"],
         ['fireball_yn_asc', "Fireball YN Score Asc (low to high)"],
         ['fireball_yn_desc', "Fireball YN Score Desc (high to low)"],
         ['mc_class_conf_asc', "Label Confidence Asc (low to high)"],
         ['mc_class_conf_desc', "Label Confidence Desc (high to low)"],
         ['date_asc', "Date Asc (old to new)"],
         ['date_desc', "Date Desc (new to old)"],
      ]
   ord_opt = ""
   if "order_by" not in options:
      options['order_by'] = "mc_class_conf"
   for code, desc in ord_op:
      print(code, desc)
      if code == options['order_by']:
         ord_opt += "<option selected value='{}'>{}</option>".format(code,desc)
      else:
         ord_opt += "<option value='{}'>{}</option>".format(code, desc)

   db_op = [
         ['meteor_db', 'Meteor DB'],
         ['non_meteor_db', 'Non Meteor DB'],
      ]
   db_opt = ""
   for code, desc in db_op:
      if code == options['db']:
         db_opt += "<option selected value='{}'>{}</option>".format(code,desc)
      else:
         db_opt += "<option value='{}'>{}</option>".format(code, desc)



   oc = [25,50,100,200,500]

   if "rc" in options:
      rc = int(options['rc'])
   else:
      rc = 25

   rc_opt = ""
   for oo in oc:
      if rc == oo:
         rc_opt += "<option selected value=" + str(oo) + ">" + str(oo) + "</option>"
      else:
         rc_opt += "<option value=" + str(oo) + ">" + str(oo) + "</option>"

   if "hc" in options: 
      hc_switch = """
      <div class="custom-control custom-switch">
          <input type="checkbox" class="custom-control-input" id="hc" checked>
          <label class="custom-control-label" for="hc"></label>
      </div>
      """
   else:
      hc_switch = """
      <div class="custom-control custom-switch">
          <input type="checkbox" class="custom-control-input" id="hc">
          <label class="custom-control-label" for="hc"></label>
      </div>
      """

   if "in_date" in options: 
      in_date = options['in_date']
      in_date_str = in_date.replace("_", "-")
   else:
      in_date = ""
      in_date_str = ""

   form = """
   <form id="search_form">
      <input type=hidden name=station_id value={} id="station_id">
      <div class="container">
      <div class="row " >
         <div class="col-2">
            Database 
         </div>
         <div class="col-2">
            Date     
         </div>
         <div class="col-2">
            Label 
         </div>
         <div class="col-2">
            Human Confirmed 
         </div>
         <div class="col-2">
            Items Per Page
         </div>
         <div class="col-1">
            Sort 
         </div>
      </div>
      <div class="row">
         <div class="col-2">
            <select name=db id="db">
               {}
            </select>
         </div>
         <div class="col-2">
            <input type=date name=in_date value={} id="in_date">
         </div>

         <div class="col-2">
            <select name=label id="label">
            {}
            </select>
         </div>

         <div class="col-2">
            {}
         </div>
         <div class="col-2">
            <select name=rc id="rc">
               {}
            </select>
         </div>
         <div class="col-1">
            <select name=order_by id="order_by">
            {}
            </select>
         </div>
      </div>
      </div>

   </form>
   {}

   """.format(station_id, db_opt, in_date_str, label_opt, hc_switch, rc_opt, ord_opt, javascript )
   return(form)

def build_query(options, cur):

   header_msg = ""
   order_msg = ""
   where_items = []
   where_vals = []

   # determine the underlying table first
   if "db" not in options:
      options['db'] = "meteor_db"

   if options['db'] == "meteor_db":

      table = "meteors"
      sql = """SELECT sd_vid,hd_vid, meteor_yn_conf, fireball_yn_conf,mc_class,mc_class_conf,ai_resp,camera_id, start_datetime, 
                      human_confirmed, multi_station, ang_velocity, duration, peak_intensity FROM meteors"""


   else:
      table = "non_meteors_confirmed"
      sql = """SELECT sd_vid, roi, meteor_yn, fireball_yn, multi_class, multi_class_conf, human_label, last_updated  
                 FROM non_meteors_confirmed"""

   if "in_date" in options:
      if table == "meteors":
         where_item = "root_fn like ?"
         where_items.append(where_item)
         where_item = "(deleted is null or deleted != 1)"
         where_items.append(where_item)
         where_vals.append(options['in_date'] + "%")
      elif table == "non_meteors_confirmed":
         where_item = "sd_vid like ?"
         where_items.append(where_item)
         where_vals.append(options['in_date'] + "%")

   if "label" in options:
      if table == "meteors":
         where_item = "mc_class like ?"
         where_items.append(where_item)
      else:
         # non_meteors
         
         if "hc" in options:
            where_item = "human_label like ?"
            where_items.append(where_item)
         else:
            where_item = "multi_class like ?"
            where_items.append(where_item)

      where_vals.append(options['label'] + "%" )


   if "hc" in options:
      if table == "meteors":
         where_item = """
            (human_confirmed == 1
            OR human_confirmed == -1)
         """
      else:
         where_item = """
            (human_label is not null 
            AND human_label != "")
         """
      where_items.append(where_item)
   else:
      if table == "meteors":
         where_item = """
            (human_confirmed is not null AND 
            (human_confirmed != 1
            AND human_confirmed != -1))

         """
      else:
         where_item = """
            (human_label is null 
            OR human_label == "")
         """
      where_items.append(where_item)


   # determine the order by

   if "order_by" in options:
      order_short = options['order_by']
      order_msg = "ordering by " + order_short
      order_by = options['order_by']
   else:
      order_by = "ORDER BY sd_vid desc"
      order_msg = "ordering by date desc (new to old)" 

   if order_by == "date_desc":
      order_by = "ORDER BY sd_vid desc"
      order_msg = "ordering by date desc (new to old)" 
   if order_by == "date_asc":
      order_by = "ORDER BY sd_vid asc"
      order_msg = "ordering by date asc (old to new)" 

   if order_by == "mc_class_conf_desc":
      order_by = "ORDER BY mc_class_conf desc"
      order_msg = "ordering by multi class confidence descending (best to worst)" 
   if order_by == "mc_class_conf_asc":
      order_by = "ORDER BY mc_class_conf asc"
      order_msg = "ordering by multi class confidence descending (best to worst)" 

   if order_by == "meteor_yn_desc":
      order_by = "ORDER BY meteor_yn_conf desc"
      order_msg = "ordering by meteor yn confidence descending (best to worst)" 
   if order_by == "meteor_yn_asc":
      order_by = "ORDER BY meteor_yn_conf asc"
      order_msg = "ordering by meteor yn confidence ascending (worst to best)" 
   if order_by == "fireball_yn_desc":
      order_by = "ORDER BY fireball_yn_conf desc"
      order_msg = "ordering by fireball yn confidence descending (best to worst)" 
   if order_by == "fireball_yn_asc":
      order_by = "ORDER BY fireball_yn_conf asc"
      order_msg = "ordering by meteor yn confidence ascending (worst to best)" 

   if table != "meteors":
      order_by = order_by.replace("meteor_yn_conf", "meteor_yn")
      order_by = order_by.replace("fireball_yn_conf", "fireball_yn")
      order_by = order_by.replace("mc_class_conf", "multi_class_conf")
      order_by = order_by.replace("mc_class", "multi_class")

   # determine limit / page 
   if "p" in options:
      page = int(options['p'])
   else:
      page = 1
   lpage = page - 1

   if "rc" in options:
      row_count = int(options['rc'])
   else:
      row_count = 25

   offset = row_count * lpage

   if len(where_items) > 0:
      sql_where = ""
      prefix = "WHERE" 
      for item in where_items:
         sql_where += " " + prefix + " " + item
         prefix = "AND"


   sql_end = """
          {}
          LIMIT {},{}
      """.format(str(order_by), str(offset), str(row_count))


   sql_stmt = sql + sql_where 

   if len(where_vals) == 0:
      cur.execute(sql_stmt)
   else:
      cur.execute(sql_stmt, where_vals)
   rows = cur.fetchall()
   total_rows = len(rows)

   
   sql_stmt += sql_end
   print("SQL:", sql)

   return(sql_stmt, where_vals, total_rows, order_msg)

def ai_scan_review(station_id, options, json_conf):
   out = ""
   good_ai = ""
   bad_ai = ""
   if "date" not in options:
      out = "add &date= to querry!"
      return(out)
   ai_file = "/mnt/ams2/SD/proc2/{}/data/".format(options['date']) + "/AI_DATA.json"
   roi_dir = "/mnt/ams2/SD/proc2/{}/images/".format(options['date'])
   files = glob.glob(roi_dir + "*ROI*")
   bad_files = []
   print("AIFILE:", ai_file)
   if os.path.exists(ai_file ) is True:
      ai_data = load_json_file(ai_file) 
   else:
      ai_data = {}

   for ff in files:
      vf = ff.replace("/mnt/ams2", "")
      vfn = vf.split("/")[-1]
      root_fn = vfn.split("-ROI")[0]
      if vfn in ai_data:
         ai_resp = ai_data[vfn]
      else:
         ai_resp = {}

      if "mc_class" in ai_resp:
          ai_info = str(int(ai_resp['meteor_yn'])) + " " + str(int(ai_resp['fireball_yn'])) + " " + str((ai_resp['mc_class'])) + " " + str(int(ai_resp['mc_class_conf']))
          ai_data[vfn] = ai_resp
          status = 1
          if ("meteor" not in ai_resp['mc_class'] and (ai_resp['mc_class_conf'] > ai_resp['meteor_yn'] and ai_resp['mc_class_conf'] > ai_resp['fireball_yn'])) and ai_resp['meteor_yn'] < 50:
             status = 0
          if ai_resp['meteor_yn'] > 50 or ai_resp['fireball_yn'] > 50:
             status = 1
          if status == 0:
             bad_ai += "<div style='float:left; border: 1px #FF0000 solid;'><img src={} alt='{}'><br>{}</div>".format(vf, ai_info, ai_info)
             bad_files.append(root_fn)
          else:
             good_ai += "<div style='float:left; border: 1px #00FF00 solid;'><img src={} alt='{}'><br>{}</div>".format(vf, ai_info, ai_info)
         
   out = good_ai + "<hr>" + bad_ai

   return(out)



def ai_rejects(station_id, options, json_conf):
   db_file = station_id + "_ALLSKY.db"
   con = sqlite3.connect(db_file)
   cur = con.cursor()

   if "in_date" not in options:
      options['in_date'] = "20"
   if "db" not in options:
      options['db'] = "meteor_db"

   if options['db'] == "meteor_db":
      ctype = "meteor"
   else:
      ctype = "non_meteors_confirmed"
   if "hc" in options:
      hc_msg = "confirmed"
   else:
      hc_msg = "non-confirmed"

   sql_stmt, sql_vals,total_rows, order_msg = build_query(options, cur)

   header_msg = """<div class="alert alert-secondary">Showing TC of {} {} {} matching date {} {} </div>""".format(total_rows, hc_msg, ctype, options['in_date'], order_msg)
   header_msg += options_form(station_id, options)

   # KEEP

   out = ui_javascript()
   out += """
      <div id='main_container' class='container-fluid h-100 mt-4 ' style="border: 1px #000000 solid">
      {}
      <div class='gallery gal-resize reg row text-center text-lg-left'>
      <div class='list-onl'>
      <div class='filter-header d-flex flex-row-reverse '>
      <button id="sel-all" title="Select All" class="btn btn-primary ml-3"><i class="icon-checkbox-checked"></i></button>
      <button id="del-all" class="del-all btn btn-danger"><i class="icon-delete"></i> Delete <span class="sel-ctn">All</span> Selected</button>
     </div>
     </div>
   """.format(header_msg)
   template = make_default_template(station_id, "meteors_main.html", json_conf)

   stats = ai_stats_summary(cur)
   non_confirmed_meteors = stats['sql_meteors'] - stats['conf_status'][1]
   ai_out = """
      <div class="container" style='border: 1px #000000 solid'>
      <div>
      <table>
      <tr><td colspan=2>Active Meteor Database</td></tr>
      <tr><td><i class="fas fa-meteor"></i>Total Detections</td><td> {} </i> </td></tr>
      <tr><td><i class="fas fa-meteor"></i>Confirmed Meteors</td><td> {} </i> </td></tr>
      <tr><td><i class="fas fa-meteor"></i>Non-Confirmed Meteors</td><td> {} </i> </td></tr>
      <tr><td><i class="fas fa-ban"></i>Confirmed Non Meteors</td><td> {} </i> </td></tr>
   """.format(stats['sql_meteors'], stats['conf_status'][1], non_confirmed_meteors, stats['conf_status'][-1])
   ai_out += """<tr><td>Non Confirmed Detections By AI Classification</td><td>   </td></tr>"""
   for bc in stats['by_class']:
      ai_out += """
      <tr><td><i class="fas fa-ban"></i><a href=/AIREJECTS/{}/?list=by_class&label={}>{}</a></td><td> {} </i> </td></tr>

      """.format(station_id, bc, bc, stats['by_class'][bc])

   ai_out += """
      </table>
      <div>
      <div>
      <table>
      <tr><td colspan=2>Non-Meteor Database Pending Confirmation</td></tr>
   """
   for bc in sorted(stats['nc_non_meteors_by_class']):
      if bc in  stats['confirmed_non_meteors_by_class']:
         conf_labeled = str(stats['confirmed_non_meteors_by_class'][bc])
      else:
         conf_labeled = "0"
      ai_out += """
      <tr><td><i class="fas fa-ban"></i> {} </td><td><a href=/AIREJECTS/{}/?ctype=non_meteor_confirmed&list=non_meteors_by_class&label={}>{}</a> </td><td><a href=/AIREJECTS/{}/?hc=1&ctype=non_meteor_confirmed&list=non_meteors_by_class&label={}>{}</a></td></tr>

      """.format(bc, station_id, bc, stats['nc_non_meteors_by_class'][bc] , station_id, bc, conf_labeled)
   ai_out += """
      </table>
      <table>
   """

   month_stats = stats_by_month(cur)
   for month in month_stats:
      ai_out += """
           <tr><td>{}</td><td><a href=/AIREJECTS/{}/?list=by_date&in_date={}>{}</a> </td><td> {} </td></tr>
      """.format(month, station_id, month, month_stats[month]['confirmed'], month_stats[month]['non_confirmed'])


   ai_out += """
      </table>
      </div>
   """
   # select and reject rows matching the MC reject case
   reject_dir = "/mnt/ams2/non_meteors/classes/"

   ### KEEP KEEP ###


   print("---------------------------------------------------------")
   print("SQL:", sql_stmt)
   print("---------------------------------------------------------")

   if len(sql_vals) == 0:
      cur.execute(sql_stmt)
   else:
      cur.execute(sql_stmt, sql_vals)

   rows = cur.fetchall()
   ai_info = []
   tc = 0
   data_str = ""
   for row in rows:
      if options['db'] == "non_meteor_db":
         sd_vid, roi, meteor_yn, fireball_yn, mc_class, mc_class_conf, human_label, last_updated = row
         camera_id = ""
         start_datetime = ""
         hd_vid = ""
         if human_label != "" and human_label is not None: 
            human_confirmed = -1 
         else:
            human_label = "none"
            human_confirmed = None
      else:
         print("ROW:", row)
         sd_vid,hd_vid,meteor_yn,fireball_yn, mc_class,mc_class_conf,ai_resp,camera_id,start_datetime, human_confirmed,multi_station,ang_velocity,duration,peak_intensity = row
         if human_confirmed == 1 :
            human_label = "meteor"
         elif human_confirmed == -1:
            human_label = "non_meteor"
         else:
            human_label = "no_human_label"
      if options['db'] == "non_meteor_db":
         mdir = "/mnt/ams2/non_meteors_confirmed/" + sd_vid[0:10] + "/"
      else:
         mdir = "/mnt/ams2/meteors/" + sd_vid[0:10] + "/"



      if os.path.exists(mdir  + sd_vid) is True:
         print("MEDIA GOOD:", sd_vid, hd_vid, meteor_yn, fireball_yn, mc_class, mc_class_conf)
      else:
         print("MEDIA BAD:", sd_vid, hd_vid, meteor_yn , fireball_yn, mc_class, mc_class_conf)

      if True:
         root_fn = sd_vid.replace(".mp4", "")
         data_str += root_fn + ","
         if options['db'] == "non_meteor_db":
            thumb_url = "/non_meteors_confirmed/" + root_fn[0:10] + "/" + root_fn + "-stacked-tn.jpg"
            json_file = "/mnt/ams2/non_meteors_confirmed/" + root_fn[0:10] + "/" + root_fn + ".json"
         else:
            thumb_url = "/meteors/" + root_fn[0:10] + "/" + root_fn + "-stacked-tn.jpg"
            json_file = "/mnt/ams2/meteors/" + root_fn[0:10] + "/" + root_fn + ".json"
         if os.path.exists(mdir + sd_vid):
            if meteor_yn is None or meteor_yn == "":
               meteor_yn = -1
            if fireball_yn is None or fireball_yn == "":
               fireball_yn = -1
            if mc_class_conf is None or mc_class_conf == "":
               mc_class_conf = -1
            if mc_class is None :
               mc_class = "unknown"

            if human_confirmed == 1:
               ico = """<i class="fas fa-meteor success" style="size: 16px; color: lime"></i>"""
               conf_color = "lime"
            elif human_confirmed == -1:
               conf_color = "red"
               ico = """<i class="fas fa-ban" style="size: 16px; color: red;"></i>"""
               if human_label != 'non_meteor':  
                  if human_label != "" and human_label != None:
                     ico = find_ico(human_label, 1)
                  else:
                     ico = find_ico(human_label, 0)
            else:
               conf_color = None
               #ico = "no_icon"
               ico = """<i class="fas fa-question">"""
            print("HUMAN CONFIRMED,LABEL IS:", human_confirmed, human_label)
            print("ICO:", ico)
            try:
               ai_info = str(int(float(meteor_yn))) + "% Meteor / "
            except:
               ai_info = "ai problem"
            try:
               ai_info += str(int(float(fireball_yn))) + "% Fireball / "
            except:
               ai_info = "ai problem"

            try:
               ai_info += str(int(float(mc_class_conf))) + "% " + mc_class + "<br>"
            except:
               ai_info = "ai problem"

            ai_info += start_datetime  #+ " vel:" + str(round(ang_velocity,2)) + " dur:" + str(round(duration,2)) 
            if conf_color is None:
               color = get_color(100-float(meteor_yn))
            else:
               color = conf_color

            multi_station = "HC: " + str(human_confirmed)

            print("DEBUIG:(ctype, color, human_confirmed, human_label)", ctype, color, human_confirmed, human_label, ico)
            cell = meteor_cell_html(root_fn, thumb_url, ai_info,ico, ctype, color, multi_station, human_confirmed, human_label )
            out += cell

            tc += 1
         else:
            print("PROBLEM: THE VIDEO IS NOT FOUND!!!", sd_vid)
            #out += "MISSING:" + sd_vid
            # if meteor no longer exists on file system update it as deleted
            # the purge will later remove it. 
            if options['db'] != "non_meteor_db":
               sql = "UPDATE meteors set deleted = '1' WHERE root_fn = ?"
               task = [root_fn]
               print(sql, root_fn)
               cur.execute(sql, task)
            #out += "Done already" + str(tc)
   con.commit()
   out = out.replace("TC", str(tc)) 
   
   print("Done mc rejects.", tc)
   if tc == 0:
      out2 = """
      <div id='main_container' class='container-fluid h-100 mt-4 ' style="border: 1px #000000 solid">
         {}
         <div class='gallery gal-resize reg row text-center text-lg-left'>
         <div class='list-onl'>
         <div class='filter-header d-flex flex-row-reverse '>
         <button id="sel-all" title="Select All" class="btn btn-primary ml-3"><i class="icon-checkbox-checked"></i></button>
         <button id="del-all" class="del-all btn btn-danger"><i class="icon-delete"></i> Delete <span class="sel-ctn">All</span> Selected</button>
        </div>
        </div>
      """.format(header_msg)
    
      old = """
            <div class="alert alert-primary" role="alert">You have confirmed all captures for this watchlist. Select another list or come back later for more confirmations.</div>
      """ 
   elif options['db'] == "non_meteor_db":
      lb_types, icons = mc_types()
      out += """
         <h2 style='width: 100%'>Mark ALL on this page as</h2>
         <form method=post action=/batch_confirm/{}>
         <input type="hidden" name=data_str value="{}">
      """ 

      for i in range(0, len(lb_types)):
         out += """
            <button type="button" class="btn btn-dark" onclick="javascript:batch_all('{}')">
            <i class='fas fa-{}'> </i> 
             Mark all on page as: {}
            </button>

            <br>
         """.format(lb_types[i], icons[i], lb_types[i])

      out += """
         <input type="button" name=button value="Load New Items" onclick="javascript:location.reload()">
         </form>
      """

   else:
      out += """
      <h2 style='width: 100%'>Mark ALL on this page as</h2>
      <form method=post action=/batch_confirm/{}>
      <input type="hidden" name=data_str value="{}">
      <input type="button" name=button value="Mark ALL As NON Meteors" onclick="javascript:batch_all('non_meteors')">
       <br>
      <input type="button" name=button value="Mark ALL As Meteors" onclick="javascript:batch_all('meteors')">
       <br>

      <input type="button" name=button value="Reload" onclick="javascript:location.reload()">
      </form>
      """.format(station_id, data_str)

   ym_nav = year_mon_nav(con,cur)

   out += ai_out  
   template = template.replace("{MAIN_TABLE}", out)
   return(template)

def find_ico(this_label, hc=0):
   lb_types, icons = mc_types()
   ico = "no icon found for " + this_label
   print("FIND ICO HC=", hc)

   for i in range(0, len(lb_types)):
      icon = icons[i]
      if lb_types[i] in this_label:
         if hc == 0:
            ico = """<i class="fas fa-{}" style="size: 16px; "></i>""".format(icon)
         else:
            ico = """<i class="fas fa-{}" style="size: 16px; color: red"></i>""".format(icon)

         return(ico)
      #print(lb_types[i], this_label, ico)
   return(ico)



def ai_non_meteors(station_id, options, json_conf):
   data_file = "/mnt/ams2/non_meteors/nm.info"
   ai_data_file = "/mnt/ams2/non_meteors/NM_AI_DATA.info"

   summary = {}
   if os.path.exists(ai_data_file) is True:
      ai_data = load_json_file(ai_data_file)
   else:
      ai_data = {}

   cmd = "cd /mnt/ams2/non_meteors/; find . |grep json |grep -v redu | grep -v star | sort -r > " + data_file
   os.system(cmd)
   header_msg = "These detections have been auto rejected and should be reviewed and confirmed as non meteors or restored as real meteors."
   #If you see good meteors here use the button to restore them. Once there are NO good meteors on the page, press the button 'Confirm All As Non-Meteors'."
   out = ui_javascript()
   out += """
      <div id='main_container' class='container-fluid h-100 mt-4 ' style="border: 1px #000000 solid">
      {}
      <div class='gallery gal-resize reg row text-center text-lg-left'>
      <div class='list-onl'>
      <div class='filter-header d-flex flex-row-reverse '>
      <button id="sel-all" title="Select All" class="btn btn-primary ml-3"><i class="icon-checkbox-checked"></i></button>
      <button id="del-all" class="del-all btn btn-danger"><i class="icon-delete"></i> Delete <span class="sel-ctn">All</span> Selected</button>
     </div>
     </div>
   """.format(header_msg)

   lc = 0
   if "start" in options:
      start = int(options['start']) 
   else:
      start = 0
   if "end" in options:
      end = int(options['end'])
   else:
      end = 25
   if "label" in options:
      label = options['label']
   else:
      label = None


   if os.path.exists(data_file) :
      fp = open(data_file, "r")
      data = []

      for line in fp:
         if "non_meteors_confirm.json" in line :
            continue
         line = line.replace("\n", "")
         line = line.replace("./", "")
         data.append(line)
         root_fn = line.split("/")[-1].replace(".json", "")

         check_file = "/mnt/ams2/non_meteors/" + root_fn[0:10] + "/" + root_fn + ".json"
         if os.path.exists(check_file) is False:
            print("CHECK FILE NOT THERE:", check_file)
            continue
         else:
            print("CHECK FILE GOOD:", check_file)

         if station_id + "_" + root_fn in ai_data:
            resp = ai_data[station_id + "_" + root_fn]
            if resp is not None:
                tlabel = resp['mc_class']
            if tlabel not in summary:
               summary[tlabel] = 1
            else:
               summary[tlabel] += 1

      for line in data:
         if start <= lc <= end:
            vurl = "/non_meteors/" + line.replace(".json", "-stacked-tn.jpg")
            root_fn = line.split("/")[-1].replace(".json", "")
            #if "AMS" not in root_fn:
            #   root_fn = station_id + "_" + root_fn
            if station_id + "_" + root_fn in ai_data:
               resp = ai_data[station_id + "_" + root_fn]
               ai_info = "{}% Meteor {}% Fireball {} {}%".format(round(resp['meteor_yn'],1), round(resp['fireball_yn'],1), resp['mc_class'], round(resp['mc_class_conf'],2))
               color = get_color(100-float(resp['meteor_yn']))
               #ai_info = ai_resp
            else:
               color = "#FCFCFC"
               #print("ROOT FN NOT FOUND IN AI DATA:", station_id + "_" + root_fn , len(ai_data.keys()))
               ai_info = ""
            if label is not None: 
               if label not in resp['mc_class']:
                  continue


            #cell = meteor_cell_html(root_fn, vurl, ai_info)

            #meteor_cell_html(root_fn, thumb_url, ai_info, ico=None, ctype="meteor", color="#ffffff",multi=0, human_confirmed=None, human_label=None):
            cell = meteor_cell_html(root_fn, vurl, ai_info + " " + root_fn[0:10] ,None, "non_meteors_confirmed", color, 0, None, None )


            out += cell 
            #"<img src=" + vurl + ">" + vurl + "<br>"
         if lc > end:
            break
         lc += 1
      
   if True:
      out += "</div>"

      out += "<h2>Auto Rejected Meteors Needing Review</h2>"
      out += str(len(data)) + " non-meteor auto rejects remain in the non-meteor queue.<br>"
      for label in summary:
         out += "<a href=/AI/NON_METEORS/{}/?label={}&start=0&end=25>{}</a> ({}) ".format(station_id, label, label, str(summary[label]))

      lb_types, icons = mc_types()
      out += """
         <h2 style='width: 100%'>Mark ALL on this page as</h2>
         <form method=post action=/batch_confirm/{}>
         <input type="hidden" name=data_str value="{}">
      """

      for i in range(0, len(lb_types)):
         out += """
            <button type="button" class="btn btn-dark" onclick="javascript:batch_all('{}')">
            <i class='fas fa-{}'> </i>
             Mark all on page as: {}
            </button>

            <br>
         """.format(lb_types[i], icons[i], lb_types[i])

      out += """
         <input type="button" name=button value="Load New Items" onclick="javascript:location.reload()">
         </form>
      """


   template = make_default_template(station_id, "meteors_main.html", json_conf)
   template = template.replace("{MAIN_TABLE}", out)
   return(template)


def ai_stats(station_id, json_conf):

   con = sqlite3.connect(station_id + "_ALLSKY.db")
   con.row_factory = sqlite3.Row
   cur = con.cursor()

   # get total meteors in the system
   sql = "SELECT count(*) from meteors"
   cur.execute(sql)
   rows = cur.fetchall()
   total_meteors_in_db = rows[0][0]
   print("TOTAL METS:", total_meteors_in_db)

def ai_main(station_id, json_conf):

   ai_stats(station_id, json_conf)

   template = make_default_template(station_id, "meteors_main.html", json_conf)
   out = "<h1>AllSkyAI Dashboard</h1>"
   if "ml" not in json_conf:
      out = "It looks like the AllSkyAI package has not been installed on your system yet."
   else:
      out += "<div class=container>AllSkyAI has been installed and is running."
      out += "<ul>"
      out += "<li><a href=/AIREJECTS/{}>AI Confirm</a> ".format(station_id) 
      out += "Use this tool to confirm meteors and non-meteors " 
      out += "<li><a href=/AI/NON_METEORS/{}>AI Auto Rejected Meteor Review</a> ".format(station_id) 
      out += "Use this tool to review auto rejected meteors before they are purged from the system" 
#      out += "<li><a href=/LEARNING/{}/METEOR?>AI Search</a> ".format(station_id)
#      out += "Use this tool to search the meteor archive." 

      out += "</ul>"

      out += "</div>"
   template = template.replace("{MAIN_TABLE}", out)
   return(template)

def ai_review(station_id, options,json_conf):
   out = """
      <div id='main_container' class='container-fluid h-100 mt-4 lg-l'>
      <div class='gallery gal-resize reg row text-center text-lg-left'>
      <div class='list-onl'>
      <div class='filter-header d-flex flex-row-reverse '>
      <button id="sel-all" title="Select All" class="btn btn-primary ml-3"><i class="icon-checkbox-checked"></i></button>
      <button id="del-all" class="del-all btn btn-danger"><i class="icon-delete"></i> Delete <span class="sel-ctn">All</span> Selected</button>
     </div>
     </div>
   """
   template = make_default_template(station_id, "meteors_main.html", json_conf)
   con = sqlite3.connect(station_id + "_ALLSKY.db")
   con.row_factory = sqlite3.Row
   cur = con.cursor()

   if "mc_class" not in options:
      sql = """
         SELECT mc_class, count(*) 
           FROM meteors
          WHERE (
                mc_class != 'meteor'
            AND mc_class != 'fireball')
            AND (
                mc_class_conf >  meteor_yn_conf
             OR mc_class_conf > fireball_yn_conf)
            AND mc_class_conf >= 98
            AND meteor_yn_conf <= 70
            AND fireball_yn_conf <= 70
            AND mc_class not like 'meteor%'
            AND human_confirmed != 1
            GROUP BY mc_class
      """
      cur.execute(sql)
      rows = cur.fetchall()
      out += "<div style='width: 100%'>We've detected the following entries and suspect they could be non-meteors. Please review and purge as needed.</div>"
      out += "<ul>"
      for row in rows:
         mc_class, ccc = row
         out += "<li><a href=/AIREVIEW/" + station_id + "/?mc_class=" + mc_class + ">" + mc_class + "</a> (" + str(ccc) + ")</li>"
   else:
      out += "<div style='width: 100%'><p>The following captures are classified as low confidence meteors and are more likely " + options['mc_class'] + " or something else."
      out += "<br>To reconcile this list, first review and human confirm any meteors you see in the list."
      out += "<br>When complete, select the button at the bottom that says, 'confirm all as NON-METEOR.'</div>"

      order_by = " ORDER BY mc_class, mc_class_conf desc"
      sql = """
            SELECT station_id, sd_vid, meteor_yn_conf, fireball_yn_conf, mc_class, mc_class_conf 
              FROM meteors 
             WHERE mc_class = ? 
               AND (
                   mc_class_conf >  meteor_yn_conf
                OR mc_class_conf > fireball_yn_conf)
               AND mc_class_conf >= 98
               AND meteor_yn_conf <= 70
               AND fireball_yn_conf <= 70
               AND human_confirmed != 1
               {}
      """.format(order_by)
      print(sql)
      cur.execute(sql, [options['mc_class']])
      rows = cur.fetchall()
      need_to_del = [] 
      for row in rows:
         station_id, sd_vid, meteor_yn, fireball_yn, mc_class, mc_class_conf = row
         root_fn = sd_vid.replace(".mp4", "")
         thumb_url = "/meteors/" + root_fn[0:10] + "/" + root_fn + "-stacked-tn.jpg"
         json_file = "/mnt/ams2/meteors/" + root_fn[0:10] + "/" + root_fn + ".json"
         if os.path.exists(json_file):
            ai_info = str(int(meteor_yn)) + "% Meteor"
            ai_info += str(int(fireball_yn)) + "% Fireball - "
            ai_info += str(int(mc_class_conf)) + "% " + mc_class
            cell = meteor_cell_html(root_fn, thumb_url, ai_info)
            out += cell
         else:
            print("record no longer exists. already deleted?")
            need_to_del.append(sd_vid)
         #out += "<li>" + sd_vid + " " + str(meteor_yn) + " " + str(fireball_yn) + " " + mc_class + " " + str(mc_class_conf)
   template = template.replace("{MAIN_TABLE}", out)
   return(template)

def mc_types():
   labels = ['bird', 'bug', 'car', 'cloud', 'ground', 'moon', 'meteor', 'meteor_fireball', 'non_meteor', 'plane', 'rain', 'satellite', 'snow', 'star', 'unsure', 'rocket', 'noise', 'chimney-smoke', 'smoke', 'empty', 'spectra']
   icons = ['crow', 'bug', 'car', 'cloud', 'tree', 'moon', 'meteor', 'meteor', 'ban', 'plane', 'cloud-rain', 'satellite', 'snowflake', 'star', 'question-circle', 'rocket-launch', 'noise', 'chimney' , 'fire-smoke', 'empty', 'arrow-up-wide-short']
   return(labels, icons)

def meteor_cell_html(root_fn, thumb_url, ai_info, ico=None, ctype="meteor", color="#ffffff",multi=0, human_confirmed=None, human_label=None):
   print("CTYPE:", ctype)
   if ico is None:
      ico = ""
   if human_confirmed is None or human_confirmed == 0:
      hc_color = "white"
   elif human_confirmed == -1:
      hc_color = "red"
   elif human_confirmed == 1:
      hc_color = "lime"

   thumb_ourl = thumb_url.replace("-tn.jpg", "-obj-tn.jpg")
   if os.path.exists("/mnt/ams2/" + thumb_ourl) is False:
      thumb_ourl = thumb_url
   jsid = root_fn.replace("_", "")
   datecam = """
    <div><table width=100%><tr><td>{}</td><td>{}</td></tr> </table></div>
   """.format(ico, ai_info)
   click_link = thumb_url.replace("-stacked-tn.jpg", ".mp4")
   video_url = thumb_url.replace("-stacked-tn.jpg",".mp4")
   if multi == 1:
      ms_style = "border-bottom: 4px lime solid;"
   else:
      ms_style = ""
   if human_confirmed is None or human_confirmed == 0:
      border_style = "border-top: 4px {} dashed;".format(color)
   else:
      border_style = "border-top: 4px {} solid;".format(color)
   
   met_html = """
         <div id='{:s}' class='preview select-to norm' style="{}">
            <a class='vid_link_gal mtt' href='/dist/video_player.html?video={:s}' data-obj='{:s}' title='Go to Info Page'>
               <img alt='{:s}' class='img-fluid ns lz' src='{:s}' style="{}">
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
           {} 

   """.format(jsid ,border_style, video_url, thumb_ourl, datecam , thumb_url, ms_style, datecam, datecam, jsid, jsid,jsid, multi)
   if ctype == "meteor":
      met_html += """
               <!-- only display this if we are on the meteor page-->

               <div class='btn-group'>
                  <a class='vid_link_gal col btn btn-primary btn-sm' title='Play Video' href='/dist/video_player.html?video={:s}'>
                  <i class='icon-play'></i></a>
                  <a class='confirm_non_meteor col btn btn-danger btn-sm' title='Confirm NON Meteor' data-meteor='{:s}'><i class='fas fa-ban' "></i></a>
                  <a class='confirm_meteor col btn btn-success btn-sm' title='Confirm Meteor' data-meteor='{:s}'><i class="fas fa-meteor"></i></a>
               </div>
      """.format(video_url, root_fn, root_fn )

   labels = ['bird', 'bug', 'car', 'cloud', 'ground', 'moon', 'meteor', 'meteor_fireball', 'non_meteor', 'plane', 'rain', 'satellite', 'snow', 'star', 'unsure']
   icons = ['crow', 'bug', 'car', 'cloud', 'tree', 'moon', 'meteor', 'meteor', 'ban', 'plane', 'cloud-rain', 'satellite', 'snowflake', 'star', 'question-circle']

   if ctype == "non_meteors_confirmed":
      met_html += """
               <div class='btn-group'>
                  <a class='confirm_bird col btn btn-secondary btn-sm' title='Bird' data-meteor='{:s}'><i class='fas fa-crow'></i></a>
                  <a class='confirm_bug col btn btn-secondary btn-sm' title='Bug' data-meteor='{:s}'><i class='fas fa-bug'></i></a>
                  <a class='confirm_car col btn btn-secondary btn-sm' title='Car' data-meteor='{:s}'><i class='fas fa-car'></i></a>
                  <a class='confirm_plane col btn btn-secondary btn-sm' title='Plane' data-meteor='{:s}'><i class='fas fa-plane'></i></a>
                  <a class='confirm_satellite col btn btn-secondary btn-sm' title='Satellite' data-meteor='{:s}'><i class='fas fa-satellite'></i></a>
                  <a class='confirm_meteor col btn btn-secondary btn-sm' title='Meteor' data-meteor='{:s}'><i class="fa-solid fa-comet"></i></a>
                  <a class='confirm_meteor col btn btn-secondary btn-sm' title='Fireball' data-meteor='{:s}'><i class='fas fa-meteor'></i></a>
               </div>
               <div class='btn-group'>
                  <a class='confirm_cloud col btn btn-secondary btn-sm' title='Cloud' data-meteor='{:s}'><i class='fas fa-cloud'></i></a>
                  <a class='confirm_rain col btn btn-secondary btn-sm' title='Rain' data-meteor='{:s}'><i class='fas fa-cloud-rain'></i></a>
                  <a class='confirm_ground col btn btn-secondary btn-sm' title='Ground' data-meteor='{:s}'><i class='fas fa-tree'></i></a>
                  <a class='confirm_snow col btn btn-secondary btn-sm' title='Snow ' data-meteor='{:s}'><i class='fas fa-snowflake'></i></a>
                  <a class='confirm_moon col btn btn-secondary btn-sm' title='Moon' data-meteor='{:s}'><i class='fas fa-moon'></i></a>
                  <a class='confirm_star col btn btn-secondary btn-sm' title='Star' data-meteor='{:s}'><i class='fas fa-star'></i></a>
                  <a class='confirm_unsure col btn btn-secondary btn-sm' title='Unsure' data-meteor='{:s}'><i class='fas fa-question-circle'></i></a>
               </div>
               <div class='btn-group'>
                  <a class='confirm_trash col btn btn-secondary btn-sm' title='Trash/Delete' data-meteor='{:s}'><i class='fas fa-trash'></i></a>
                  <a class='confirm_spectra col btn btn-secondary btn-sm' title='Spectra' data-meteor='{:s}'><i class="fa-solid fa-arrow-up-wide-short"></i></a>
                  <a class='confirm_rocket col btn btn-secondary btn-sm' title='Rocket' data-meteor='{:s}'><i class="fa-solid fa-rocket-launch"></i></a>
                  <a class='confirm_noise col btn btn-secondary btn-sm' title='Noise' data-meteor='{:s}'><i class="fa-solid fa-speakers"></i></a>
                  <a class='confirm_chimney_smoke col btn btn-secondary btn-sm' title='Chimney Smoke' data-meteor='{:s}'><i class="fa-solid fa-chimney"></i></a>
                  <a class='confirm_smoke col btn btn-secondary btn-sm' title='Fire Smoke' data-meteor='{:s}'><i class="fa-solid fa-fire-smoke"></i></a>
                  <a class='confirm_empty col btn btn-secondary btn-sm' title='Empty' data-meteor='{:s}'><i class="fa-solid fa-empty-set"></i></a>
               </div>


      """.format(root_fn, root_fn, root_fn, root_fn, root_fn, root_fn, root_fn, root_fn, root_fn, root_fn, root_fn, root_fn, root_fn, root_fn, root_fn, root_fn, root_fn, root_fn, root_fn, root_fn, root_fn, root_fn)

   met_html += """
            </div>
      </div>
   """
   
   return(met_html)


def get_color(n):
   #print("COLOR FOR N:", n)
   R = int((255 * n) / 100)
   G = int((255 * (100 - n)) / 100 )
   B = int(0)
   rgb = (R,G,B)
   return '#%02x%02x%02x' % rgb

def year_mon_nav(con,cur):
   sql = """
      SELECT substr(root_fn, 0,8) as mdd, count(*) 
        FROM meteors 
    GROUP BY mdd
    ORDER BY mdd desc
   """
   cur.execute(sql)
   rows = cur.fetchall()
   for row in rows:
      date = row[0]
      count = row[1]
      el = date.split("_")
      if len(el) == 2:
         year, month = el
         print(year, month, count)
