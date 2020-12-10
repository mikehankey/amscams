import glob
from lib.PipeAutoCal import fn_dir
from FlaskLib.Pagination import get_pagination
from flask import Flask, request
from FlaskLib.FlaskUtils import get_template, make_default_template

import glob
from lib.PipeUtil import load_json_file, save_json_file, cfe
from lib.PipeAutoCal import fn_dir

TEST = """
      /*
      */
"""

def js_learn_funcs():

   #vid_html = vid_html + " - <a href=javascript:SwapDivLearnDetail('" + div1 + "','" + crop_img + "','" + crop_vid + "',2)>Full</a>"

   JS_SWAP_DIV_WITH_CLICK = """

   // call : javascript:SwapDivsWithClick('div_id1','crop_img', 'vid_url',play_vid)
   function SwapDivLearnDetail(div1,crop_img, crop_vid,play_vid)
   {
    
      js_link = "<a href=\\"javascript:SwapDivLearnDetail('" + div1 + "','" + crop_img + "','" + crop_vid + "', 1)\\"> "
      orig_html = js_link + "<img src=" + crop_img + "></a>"
      d1 = document.getElementById(div1);
      if (play_vid == 1) {
         vid_html = "<video width=160 height=90 controls autoplay loop><source src='"+ crop_vid + "'></video>"
         vid_html = vid_html + "<br><a href=javascript:SwapDivLearnDetail('" + div1 + "','" + crop_img + "','" + crop_vid + "',0)>Close</a>"
         vid_html = vid_html + " - <a href=javascript:SwapDivLearnDetail('" + div1 + "','" + crop_img + "','" + crop_vid + "',2)>Full</a>"
         vid_html = vid_html + " - <a href=/goto/meteor/" + div1 + ">Details</a>"
         //alert(div1)
         d1.innerHTML = vid_html
      
         //vid.play()
      }
      if (play_vid == 0) {
         div_item = document.getElementById(div1)
         div_item.innerHTML = orig_html 
      }
      if (play_vid == 2) {
         full_vid = crop_vid.replace("CROPS", "VIDS")
         full_vid = full_vid.replace("-crop-360p", "")
         vid_html = "<video width=640 height=360 controls autoplay loop><source src='"+ full_vid + "'></video>"
         vid_html = vid_html + "<br><a href=javascript:SwapDivLearnDetail('" + div1 + "','" + crop_img + "','" + crop_vid + "',0)>Close</a>"
         //vid_html = vid_html + " - <a href=javascript:SwapDivLearnDetail('" + div1 + "','" + crop_img + "','" + crop_vid + "',2)>Full</a>"
         div_item = document.getElementById(div1)
         div_item.innerHTML = vid_html
      }

   }
   """

   return(JS_SWAP_DIV_WITH_CLICK)



def learning_meteors_dataset(amsid, in_data):
   json_conf = load_json_file("../conf/as6.json")
   template = make_default_template(amsid, "live.html", json_conf)
   js_code = js_learn_funcs()
   page = in_data['p']
   items_per_page = in_data['ipp']
   if page is None:
      page = 1
   else:
      page = int(page)
   if items_per_page is None:
      items_per_page = 100
   else:
      items_per_page = int(items_per_page) 
   si = (page-1) * items_per_page
   ei = si + items_per_page
   
   LEARNING_VID_DIR = "/mnt/ams2/LEARNING/METEORS/2020/VIDS/"
   files = glob.glob(LEARNING_VID_DIR + "*.mp4")
   out = "<script>" + js_code + "</script>"
   out += "<div id='main_container' class='container-fluid h-100 mt-4 lg-l'>"
   for file in sorted(files, reverse=True)[si:ei]:
      vfile = file.replace("/mnt/ams2", "")
      fn, dir = fn_dir(vfile)
      crop_img = vfile.replace("VIDS", "IMGS")
      crop_vid = vfile.replace("VIDS", "CROPS")
      crop_vid = crop_vid.replace(".mp4", "-crop-360p.mp4")
      crop_img = crop_img.replace(".mp4", "-crop-360p-stacked.jpg")
      div_id = fn
      vid_id = crop_vid 

      js_link = "<a href=\"javascript: SwapDivLearnDetail('" + div_id + "', '" + crop_img + "','" + crop_vid + "', 1)\">"
      #out += "<div style='float: left; display=none' id='details_" + div_id + "'>" + js_link + "<video src=" + crop_vid + "></a></div>\n"
      out += "<div style='float: left' id='" + div_id + "'>" + js_link + "<img src=" + crop_img + "></a></div>\n"
   out += "</div>"

   pagination = get_pagination(page, len(files), "/LEARNING/METEORS/" + amsid + "?ipp=" + str(items_per_page) , items_per_page)
   out += "<div style='clear: both'></div>" 
   out += pagination[0]


   template = template.replace("{MAIN_TABLE}", out)
    
   return(template)
