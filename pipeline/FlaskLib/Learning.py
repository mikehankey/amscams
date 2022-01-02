import glob
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
      print("UPDATE FILES ON THIS DAY:", date)
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
      out += key + " " + str(ai_sum[key]) +  "<br>"
   print(ai_summary_file)
   print("MD:", len(machine_data)) 
   print("HD:", len(human_data)) 
   print("OBS IDS:", len(obs_ids)) 

   return(out)

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

      <script src="https://kit.fontawesome.com/25faff154f.js" crossorigin="anonymous"></script>
      <!-- Bootstrap CSS -->
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-eOJMYsd53ii+scO/bJGFsiCZc+5NDVN2yr8+0RDqr0Ql0h+rP48ckxlpbzKgwra6" crossorigin="anonymous">
      <link rel="alternate" type="application/rss+xml" title="RSS 2.0" href="https://www.datatables.net/rss.xml">
      <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/js/bootstrap.bundle.min.js" integrity="sha384-JEW9xMcG8R+pH31jmWH6WWP0WintQrMb4s7ZOdauHnUtxwoG2vI5DkLtS3qm9Ekf" crossorigin="anonymous"></script>
      <script type="text/javascript" language="javascript" src="https://cdn.datatables.net/1.10.24/js/jquery.dataTables.min.js"></script>

      <script>

      all_classes = ['meteor', 'cloud', 'bolt', 'cloud-moon', 'cloud-rain',  'tree', 'plane', 'car-side', 'satellite', 'crow', 'bug','chess-board','question']
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
         alert("Saving data...")
         api_url = "/LEARNING/" + station_id + "/BATCH_UPDATE/" 
         alert(api_url)
         method = "POST"
         api_data = {}
         api_data['label_data'] = data
         callAPI(api_url, method, api_data, callbackBatchUpdate,error_callback)
      }

   function callbackBatchUpdate(resp) {
      alert(resp)
   }
   function error_callback(resp) {
      alert(resp)
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
      buttons = make_buttons(fn,main_class)
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

def recrop_roi(station_id, stack_fn, div_id, click_x, click_y,size=150,margin=.2):

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


def learning_meteors_tag(label, req):
   learning_file = "/mnt/ams2" + req['learning_file']
   lfn = learning_file.split("/")[-1]
   new_dir = "/mnt/ams2/datasets/images/repo/" + label.lower() + "/"
   human_data_file = "/mnt/ams2/datasets/human_data.json"
   if os.path.exists(human_data_file) is True:
      human_data = load_json_file(human_data_file)
   else:
      human_data = {}
   human_data[lfn] = label
   save_json_file(human_data_file, human_data)
   cmd = "mv " + learning_file + " " + new_dir 
   print(cmd)
   os.system(cmd)
   resp = {}
   resp['msg'] = "OK"

   return(resp)

def js_learn_funcs():

   #vid_html = vid_html + " - <a href=javascript:SwapDivLearnDetail('" + div1 + "','" + learn_img + "','" + crop_vid + "',2)>Full</a>"

   JS_SWAP_DIV_WITH_CLICK = """

   $(document).ready(function() {
    $("img").on("click", function(event) {
        //var id = this.data("id");
        //alert(id)
        //var x = event.pageX - this.offsetLeft;
        //var y = event.pageY - this.offsetTop;
        //alert("X Coordinate: " + x + " Y Coordinate: " + y);

    });
   });
   function make_trash_icons(roi_file, size, color) {
      trash_icons = `
        <a href="javascript:click_icon('reclass_meteor', '` + roi_file + `')">
            <i style="padding: 5px; color: ` + color + `; font-size: ` + size + `px;"
               class="fas fa-meteor" title="confirm meteor" id="reclass_meteor_roi_file"></i>
        </a>
        <a href="javascript:click_icon('reclass_trash', '` + roi_file + `')">
            <i style="padding: 5px; color: ` + color + `; font-size: ` + size + `px;"
               class="bi bi-trash" title="non-meteor" id='reclass_nonmeteor_` + roi_file + `'></i>
        </a>
        <a href="javascript:click_icon('expand', '` + roi_file + `')">
            <i style="padding: 5px; color: ` + color + `; font-size: ` + size + `px;"
               class="bi bi-arrows-fullscreen" title="expand" id='expand_` + roi_file + `'></i>
        </a>
      `
   return (trash_icons)
   }




   function click_icon(cmd, roi_file) {
      div_id = "#" + roi_file.replace("-ROI.jpg", "")
      div_id = div_id.replace(/-/g, "")
      div_id = div_id.replace(/_/g, "")
      cur_html = $(div_id).html()
      el = roi_file.split("_")
      station_id = el[0]
      stack_fn = roi_file.replace(station_id + "_", "")
      stack_fn = stack_fn.replace("-ROI.jpg", "-stacked.jpg")
      date = stack_fn.substr(0,10)
      stack_url = "/meteors/" + date + "/" + stack_fn

      $(div_id).css("width", "640px");
      $(div_id).css("height", "360px");
      $(div_id).css("background-size", "640px 360px");
      $(div_id).css("background-image", "url(" + stack_url + ")");
      new_html = `<a href="#` + stack_fn + `"><img data-id="` + stack_fn + `" class="ximg" width=640 height=360 src="` + stack_url + `" ismap></a>`


      $(div_id).html(new_html)

      $("img").on("click", function(event) {
        var id = $(this).data("id");
        alert(id)
        var x = event.pageX - this.offsetLeft;
        var y = event.pageY - this.offsetTop;
        alert("X Coordinate: " + x + " Y Coordinate: " + y);
        //api_data = "stack_fn=" + id + "click_x=" + x + "&click_y=" + y 
        api_data = {}
        api_data['cmd'] = "recrop_roi"
        api_data['stack_fn'] = id
        api_data['click_x'] = x
        api_data['click_y'] = y
        api_data['div_id'] = div_id
        console.log(api_data)
        api_url = "/LEARNING/" + station_id + "/RECROP/" 
        alert(api_url)
        method = "POST"
        callAPI(api_url, method, api_data, callbackROI,error_callback)

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

   function callbackBatchUpdate(resp) {
      alert(resp)
   }

   function callbackROI(resp) {
      alert(resp['roi_url'])
      alert(resp['div_id'])
      el = resp['roi_url'].split("/")
      roi_file = el.at(-1)

      controls = make_trash_icons(roi_file,"#FFFFFF","20") 
      div_id = resp['div_id']
      $(div_id).css("width", "180px");
      $(div_id).css("height", "180px");
      $(div_id).css("background-size", "180px 180px");
      $(div_id).css("background-image", "url(" + resp['roi_url'] + ")");
      new_html = controls
       //`<a href="#` + stack_fn + `"><img data-id="` + stack_fn + `" class="ximg" width=150 height=150 src="` + stack_url + `" ismap></a>`


      $(div_id).html(new_html)


      console.log(resp)
   }

 
   function callback(resp) {
      alert(resp)
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
   all_meteors = load_json_file("/mnt/ams2/meteors/" + ams_id + "_OBS_IDS.json")

   page = in_data['p']
   uc_label = in_data['label']
   label = in_data['label'].lower()
   items_per_page = in_data['ipp']
   template = make_default_template(ams_id, "live.html", json_conf)
   print("IPP:", items_per_page)
   out = ""

   js_code = js_learn_funcs()
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


   print("ALLFILES:", len(all_files), label)
   out += str(len(all_files)) + " AI items classified as " + label
   out += "<div>"
   for row in sorted(all_files, key=lambda x: (x[2]), reverse=True)[si:ei]:
      lfile, tlabel, tscore = row
      crop_img = "/METEOR_SCAN/" + lfile[5:15] + "/" + lfile.replace(".json", "-ROI.jpg")
      controls = ""

      controls = make_trash_icon(lfile,"#FFFFFF","20") 
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

def make_trash_icon(roi_file,color,size) :
               #class="bi bi-dash-square" title="confirm meteor" id="reclass_meteor_roi_file"></i>
   trash_icons = """
        <a href="javascript:click_icon('reclass_meteor', '""" + roi_file + """')">
            <i style="padding: 5px; color: """ + color + """; font-size: """ + size + """px;" 
               class="fas fa-meteor" title="confirm meteor" id="reclass_meteor_roi_file"></i>
        </a>
        <a href="javascript:click_icon('reclass_trash', '""" + roi_file + """')">
            <i style="padding: 5px; color: """ + color + """; font-size: """ + size + """px;" 
               class="bi bi-trash" title="non-meteor" id='reclass_nonmeteor_""" + roi_file + """'></i>
        </a>
        <a href="javascript:click_icon('expand', '""" + roi_file + """')">
            <i style="padding: 5px; color: """ + color + """; font-size: """ + size + """px;" 
               class="bi bi-arrows-fullscreen" title="expand" id='expand_""" + roi_file + """'></i>
        </a>
   """



   return(trash_icons)

