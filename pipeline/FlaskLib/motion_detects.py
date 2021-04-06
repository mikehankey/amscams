import glob
from lib.UIJavaScript import * 
from lib.PipeUtil import load_json_file, save_json_file, cfe


def make_img_html(jpg, text):
   html = "<img src=" + jpg + "><br>" + text
   return(html)

def make_img_html_with_video(jpg, text, start, end):
   start_sec = int(start) / 25
   end_sec = int(end) / 25
   vid = jpg.replace("-stacked-tn.jpg", ".mp4")
   vid = vid.replace("images/", "")
   base = jpg.split("/")[-1].replace("-stacked-tn.jpg", "")
   cdiv_id = base
   vdiv_id = base + "-vid"
   ddiv_id = base + "-del"
   ms = text 
   js_link = "\"javascript:SwapDivsWithClick('" + cdiv_id + "', '" + vdiv_id + "',1)\""
   js_undo_link = "\"javascript:SwapDivsWithClick('" + ddiv_id + "', '" + cdiv_id + "',0)\""
   vjs_link = "\"javascript:SwapDivsWithClick('" + vdiv_id + "', '" + cdiv_id + "',0)\""

   #<source src='""" + vid + """#t=""" + str(start_sec) + "," + str(end_sec) + """' type="video/mp4">
   detect_html = """

         <div class='container' id='""" + vdiv_id + """' style="display: None">
            <a href=""" + vjs_link + """>
            <video autoplay loop controls id='video_""" + cdiv_id + """'>
               <source src='""" + vid + """' type="video/mp4">
            </video> 
            </a>
         </div>
         <div class='container' id='""" + cdiv_id + """'>
            <a href=""" + js_link + """><img class='image' src='""" + jpg + """'></a>
            <div class='middle'><div class='text'>""" + ms + """</div></div>
         </div>
         <div class='container' id='""" + ddiv_id + """' style="display: None">
            <a href=""" + js_link + """><img class='image-deactive' src='""" + jpg + """'></a>
            <div class='deactive'><div class='text'><a href=""" + js_undo_link + """>undo</a></div></div>
         </div>
      """

   return(detect_html)


def motion_detects(day):
   motion_files = glob.glob("/mnt/ams2/SD/proc2/" + day + "/odata/*moving*.json")
   out = "<script>" + JS_SWAP_DIV_WITH_CLICK + "</script>"
   out += "<h1>Moving Objects " + day + "</h1>\n"
   for mf in sorted(motion_files, reverse=True):
      objects = load_json_file(mf)
      text = "Objects:"
      ic = 1
      for obj in objects:
      
         #print(obj)
         if text != "Objects:":
            text += ","
         #text += " " + str(obj['ofns'][0]) + "-" + str(obj['ofns'][-1]) + ""
         text += str(ic)
         ic += 1
      jpg = mf.replace("_moving.json", "-stacked-tn.jpg")
      jpg = jpg.replace("odata", "images")
      jpg = jpg.replace("/mnt/ams2", "")
      jpg_html = make_img_html(jpg, text) #, str(obj['ofns'][0]),str(obj['ofns'][-1]))
      out += "<div style='border:1px solid black; float: left; padding: 5px; margin: 5px'>" + jpg_html + "</div>"
   return(out)
