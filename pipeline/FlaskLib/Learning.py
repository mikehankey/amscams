import glob
import os
from lib.PipeAutoCal import fn_dir
from FlaskLib.Pagination import get_pagination
from flask import Flask, request
from FlaskLib.FlaskUtils import get_template, make_default_template
import time
import glob
from lib.PipeUtil import load_json_file, save_json_file, cfe
from lib.PipeAutoCal import fn_dir

TEST = """
      /*
      */
"""

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
   human_data = load_json_file(human_data_file)
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
        var x = event.pageX - this.offsetLeft;
        var y = event.pageY - this.offsetTop;
        alert("X Coordinate: " + x + " Y Coordinate: " + y);
    });
   });
   function click_pic(event) {
       alert(event)
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
      new_html = `<a href="#"><img class="ximg" width=640 height=360 src="` + stack_url + `" ismap></a>`


      $(div_id).html(new_html)

      $("img").on("click", function(event) {
        var x = event.pageX - this.offsetLeft;
        var y = event.pageY - this.offsetTop;
        alert("X Coordinate: " + x + " Y Coordinate: " + y);
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
             <div id='""" + div_id + """' class="meteor_gallery" style="background-color: #000000; background-image: url('""" + crop_img + """?ad1'); background-repeat: no-repeat; background-size: 180px; width: 180px; height: 180px; border: 1px #000000 solid; float: left; color: #fcfcfc; margin:5px "> """ + controls + """ </div>
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
   meteor_training_files = glob.glob(T_DIR + "*")
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
      print("ROI FILE:", roi_file)
      if roi_file in machine_data:
         mdata = machine_data[roi_file]
         score = str(mdata[1])[0:4]
      else:
         mdata = "UNKNOWN"
         score = "99" 
      all_files_score.append((file, mdata, float(score)))
   all_files_score =  sorted(all_files_score, key=lambda x: (x[2]), reverse=True) 
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
             <div class="meteor_gallery" style="background-color: #000000; background-image: url('""" + crop_img + """?ad1'); background-repeat: no-repeat; background-size: 150px; width: 150px; height: 150px; border: 1px #000000 solid; float: left; color: #fcfcfc; margin:5px "> """ + controls + """ </div>
      """
   out += "</div>"

   pagination = get_pagination(page, len(all_files), "/LEARNING/" + amsid + "/" + uc_label + "?ipp=" + str(items_per_page) , items_per_page)
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

