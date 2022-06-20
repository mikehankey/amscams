from lib.PipeUtil import load_json_file, save_json_file, cfe, bound_cnt, convert_filename_to_date_cam
from lib.PipeDetect import analyze_object, get_trim_num, make_base_meteor_json
from lib.PipeAutoCal import get_image_stars, get_catalog_stars , pair_stars, eval_cnt, update_center_radec, fn_dir
from lib.PipeDetect import fireball, apply_frame_deletes, find_object, analyze_object, make_base_meteor_json, fireball_fill_frame_data, calib_image, apply_calib, grid_intensity_center
from lib.PipeVideo import ffprobe, load_frames_fast
from lib.PipeImage import restack_meteor
from Classes.Detector import Detector
import datetime
import os
import cv2
from FlaskLib.FlaskUtils import parse_jsid, make_default_template
import glob
import numpy as np

def detect_in_crop(nx,ny,crop_frames, hd_color_frames):
   det = Detector()
   sub_frames = []
   last_frame = None
   fc = 0
   SD_W = 704 #hd_color_frames[0].shape[1]
   objects = {}
   for frame in crop_frames:
      if last_frame is None:
         last_frame = frame
      sub = cv2.subtract(frame, last_frame)
      sub = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
      _, thresh_img = cv2.threshold(sub, 15, 255, cv2.THRESH_BINARY)
      conts = get_contours(thresh_img)
      print(fc, conts)
      for cnt in conts:  
         x,y,w,h = cnt
         cx = nx + x + (w/2)
         cy = ny + y + (h/2)
         intensity = np.sum(sub[y:y+h,x:x+w])
         print("INT:", intensity)
         oid, objects = Detector.find_objects(fc,x+nx,y+ny,w,h,cx,cy,intensity,objects, SD_W * .1)

      last_frame = frame
      fc += 1 
   print("OBJECTS:", len(objects))
   for oid in objects:
      print(oid, objects[oid])
      status, report = Detector.analyze_object(objects[oid])
      objects[oid]['report'] = report
   return(objects)

def default_red_json(sd_video_file, hd_video_file=None, user_mods=None): 
   js = {}
   js['sd_video_file'] = sd_video_file
   sd_stacked = hd_video_file.replace(".mp4", "-stacked.jpg")
   js['sd_stacked'] = hd_stacked
   if hd_video_file is not None:
      js['hd_video_file'] = hd_video_file
      js['hd_trim'] = hd_trim
      hd_stacked = hd_video_file.replace(".mp4", "-stacked.jpg")
      js['hd_stacked'] = hd_stacked

def default_best_meteor(sd_video_file, user_mods, ow,oh): 


   hdm_x_720 = 1920 / 1280
   hdm_y_720 = 1080 / 720


   hdm_x = 1920 / ow
   hdm_y = 1080 / oh
   js = {}
   js['ofns'] = []
   js['oxs'] = []
   js['oys'] = []
   js['ows'] = []
   js['ohs'] = []
   js['ccxs'] = []
   js['ccys'] = []
   js['oint'] = []
   js['dt'] = []
   print("DEFAULT BEST:")
   (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(sd_video_file)

   trim_num = get_trim_num(sd_video_file)
   extra_sec = int(trim_num) / 25
   start_trim_frame_time = f_datetime + datetime.timedelta(0,extra_sec)

   for fn in sorted(user_mods['frames'].keys()):
      mx,my = user_mods['frames'][fn]
      print("UMF:", fn,mx,my)
      js['obj_id'] = 1
      js['ofns'].append(int(fn))
      js['oxs'].append(int(mx/hdm_x)-5)
      js['oys'].append(int(my/hdm_y)-5)
      js['ows'].append(5)
      js['ohs'].append(5)
      
      js['ccxs'].append(int(mx/hdm_x_720))
      js['ccys'].append(int(my/hdm_y_720))
      js['oint'].append(0)
      extra_sec = fn / 25
      frame_time = start_trim_frame_time + datetime.timedelta(0,extra_sec)
      frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

      js['dt'].append(frame_time_str)
   js = analyze_object(js)
   return(js)

def default_meteor_json(sd_video_file, hd_video_file=None, user_mods=None): 
   js = {}


def ajax_js() :

   js = """

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

   """
   return(js)




def save_man_reduce_v2(data):
   """ 
      here we need to:
         - rescale the points to match the original SD file and then scale them up to HD
         - if json already exists
            - save points in man_red in main json
            - run mfd job
         - if json doesn't exist create and save in meteor dir 
            - if file is not already in meteor dir move it there
            - link up HD file (and trim if needeed) as part of this process
   """
   json_conf = load_json_file("../conf/as6.json")
   sd_video_file = data['sd_video_file'] 
   mjf = sd_video_file.replace(".mp4", ".json")
   if cfe(mjf) == 1:
      mj = load_json_file(mjf)
   else:
      mj = None
   frame_data = data['frame_data'] 
   crop_x = int(data['x'])
   crop_y = int(data['y'])
   crop_w = int(data['w'])
   crop_h = int(data['h'])
   ow = int(data['ow'])
   oh = int(data['oh'])
   ScaleFactor = int(data['ScaleFactor'])


   hdm_x = 1920 / int(ow) 
   hdm_y = 1080 / int(oh) 
   print("OWH", ow, oh, hdm_x, hdm_y)
   print("CROPXY", crop_x, crop_y)

   temp = frame_data.split(";")

   fd = []
   for row in temp:
      print("ROW:", row)
      data = row.split(",")
      if len(data) != 3:
         continue
      fn,x,y = data
      fn,x,y = int(fn),int(x),int(y)
      fd.append((fn,x,y))
   fd = sorted(fd, key=lambda x: x[0], reverse=False)

   print("FD IS:", fd)
   

   hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(sd_video_file, json_conf, 0, 0, 1, 1,[])

   sfile = sd_video_file.replace(".mp4", "-stacked.jpg")
   dimg = cv2.imread(sfile)
   print("CROP:", crop_x, crop_y, crop_w, crop_h)
   cv2.rectangle(dimg, (int(crop_x), int(crop_y)), (int(crop_x+crop_w) , int(crop_y+crop_h) ), (150, 150, 150), 1) 
   cv2.imwrite("/mnt/ams2/debug.jpg", dimg)
   if mj is not None:
      if "user_mods" not in mj:
         mj['user_mods'] = {}
      mj['user_mods']['frames'] = {}

      for data in fd:
         #print("ROW:", row)
         #data = row.split(",")
         if len(data) != 3:
            continue
         fn,x,y = data
         print(fn,x,y)
         fn = int(fn) 
         x = int(x) 
         y = int(y) 
         # scale incoming xy. 
         x = (x / ScaleFactor) + crop_x
         y = (y / ScaleFactor) + crop_y
         print("SD XY:", x,y)
         x = int(x * hdm_x)
         y = int(y * hdm_y)
         print("HD XY:", x,y)
         mj['user_mods']['frames'][fn] = [x,y]

      best_meteor = default_best_meteor(sd_video_file, mj['user_mods'], ow,oh)

      hd_img = cv2.resize(hd_color_frames[0],(1920,1080))
      cp = calib_image(sd_video_file, hd_img, json_conf)
      if cp is not None:
         best_meteor = apply_calib(sd_video_file, best_meteor, cp, json_conf)
      if "hd_trim" in mj:
         hd_trim = mj['hd_trim']
      else:
         hd_trim = None
      base_js, base_jsr = make_base_meteor_json(sd_video_file, hd_trim,best_meteor)
 
      base_jsr['cal_params'] = cp 


      mj['best_meteor'] = best_meteor
      mj['cp'] = cp 

      save_json_file(mjf, mj)
      mjrf = mjf.replace(".json", "-reduced.json")
      save_json_file(mjrf, base_jsr)


      cmd = "./Process.py roi_mfd " + sd_video_file + " >/mnt/ams2/tmp/api.points 2>&1"
      print("COMMAND:", cmd)
      os.system(cmd)
   return("OK") 

def export_frames(vid_file, json_conf, x,y,w,h, cache_dir, cache_dir_f, prefix):
   print("EXPORTING FRAMES!!!!")
   if True:
      hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(vid_file, json_conf, 0, 0, 1, 1,[])
      vh,vw = hd_frames[0].shape[:2]
      vw,vh = int(vw),int(vh)
      hdm_x = 960 / int(vw)
      hdm_y = 540/ int(vh)
      nx = int(int(x) / hdm_x)
      ny = int(int(y) / hdm_y)
      nw  = int(int(w))
      nh  = int(int(h))
      if nh > nw:
         nw = nh
      else:
         nh = nw 
      size = nh
      sfile = vid_file.replace(".mp4", "-stacked.jpg")
      dimg = cv2.imread(sfile)
      #cv2.rectangle(dimg, (int(nx), int(ny)), (int(nx+nw) , int(ny+nh) ), (150, 150, 150), 1) 
      cv2.imwrite("/mnt/ams2/debug.jpg", dimg)
      print("ORIG SD CROP:", nx, ny)

   crop_files = []
   crop_frames = []
   c = 0
   step = None
   for frame in hd_color_frames:
      num = "{:04d}".format(c) 
      cf_file = cache_dir + prefix + "_" + num + ".jpg"
      ff_file = cache_dir_f + prefix + "_" + num + ".jpg"
      if step is None:

         if nx < 0:
            nx = 0
         if ny < 0:
            ny = 0
         if nx > frame.shape[1] :
            nx = frame.shape[1] - 1 
         if ny > frame.shape[0] :
            ny = frame.shape[0] - 1 


         print("NXY:", nx, ny, nx+nw, ny+nh)
         cf = frame[ny:ny+nh, nx:nx+nw]
         crop_frames.append(cf)
         if nw <= 800 or nh <= 800:
            cv2.imwrite(cf_file, cf)
         else:
            cv2.imwrite(cf_file, frame)
         cv2.imwrite(ff_file, frame)
         print("CF:", cf_file)
      crop_files.append(cf_file)
      c += 1 
   c = 0

   return(crop_files)


def meteor_man_reduce_v2(meteor_file, x,y,w,h, step, first_frame,last_frame,ScaleFactor):
   # setup vals
   out = ""
   json_conf = load_json_file("../conf/as6.json")
   amsid = json_conf['site']['ams_id']
   template = make_default_template(amsid, "modal.html", json_conf)
   fn,dir = fn_dir(meteor_file)
   prefix = fn.replace(".mp4", "")
   root_fn = prefix
   year = prefix[0:4]
   day = prefix[0:10]
   vid_file = "/mnt/ams2/meteors/" + day + "/" + prefix + ".mp4"
   cache_dir = "/mnt/ams2/CACHE/" + year + "/" + prefix + "/crop_frames/"
   cache_dir_f = "/mnt/ams2/CACHE/" + year + "/" + prefix + "/sd_frames/"
   if cfe(cache_dir, 1) == 0:
      os.makedirs(cache_dir)
   if cfe(cache_dir_f, 1) == 0:
      os.makedirs(cache_dir_f)

   if w * 2 > 800 or h * 2 > 800:
      full_frame = True
      cwidth = 1920
      cheight = 1080
   else:
      full_frame = False
      cwidth = 800
      cheight = 800

   crop_files = export_frames(vid_file, json_conf, x,y,w,h, cache_dir, cache_dir_f, prefix)

   first_frame = crop_files[0].replace("/mnt/ams2", "")

   js_img_array = """
      <script>
      var frame_data = {}
      var canvas = new fabric.Canvas("c");
      var img_c = 0
      var js_img_array = [
   """
   c = 0

   for cf in crop_files:
      vcf = cf.replace("/mnt/ams2", "")
      if c > 0:
         js_img_array += ","
      c += 1
      js_img_array += "'{}'".format(vcf)
   js_img_array += "]\n</script>\n"


   canvas = """
   <div style="width:{}px;">""".format(cwidth) 

   canvas += """
      <style>
       .pull-right {
          border: 1px #000000 solid;
       }
      </style>
      <h1>Manual Reduction</h1>
      <p>Pick the meteor points in each frame.</p>
      <canvas style="border: 1px #ffffff solid;" id="c"></canvas>
      <div class="row d-flex">
         <div  class="col-sm">
            <span id="next"><a href="javascript:refresh_pic('next')"><i class="fa-solid fa-2xl fa-angle-left"></i></a>
            <span id="next"><a href="javascript:refresh_pic('next')"><i class="fa-solid fa-2xl fa-angles-left"></i></a>
         </div>
         <div  class="col-sm">
            <span id="current"></span>
         </div>
         <div  class="col-sm">
            <span id="next"><a href="javascript:refresh_pic('next')"><i class="fa-solid fa-angle-right"></i></a>
            <span id="next"><a href="javascript:refresh_pic('next')"><i class="fa-solid fa-angles-right"></i></a>
         </div>
      </div>
      <div  class="row d-flex">
         <div class="col-sm-4">

            <div class="custom-control custom-switch">
               <input type="checkbox" class="custom-control-input" id="advance">
               <label class="custom-control-label" for="advance">Advance frame on point click</label>
            </div>  
         </div>
         <div  class="col-sm-4">
            <span id="middle"></span>
         </div>
         <div  class="col-sm-4 align-items-end">
            <span id="reset"><a href="javascript:reset()">X - Clear point on this frame</a></span>
         </div>
      </div>
      <div  class="row">
         <div id="submit_area" class="col-sm-12">
            <button type="button" class="btn btn-primary" id="submit_points">Save Points</button>
         </div>
      </div>

   </div>
   """
   can_script = """
     <script>
        $(document).ready(function () {
           $( "#submit_points" ). click(function() {
              alert( "Handler for .click() called." );
           });
        });


     function reset() {
        if (frame_data[img_c] !== undefined) {
           delete frame_data[img_c]
        }
        for (i = 0; i < canvas._objects.length; i++) {
            canvas.remove(canvas._objects[i])
        }

     }
     function refresh_pic(input) {
        // remove all items
        for (i = 0; i < canvas._objects.length; i++) {
            canvas.remove(canvas._objects[i])
        }

        if (input == "next") {
           img_c += 1
        }
        else if (input == "prev") {
           img_c -= 1
        }
        else {
           img_c = input
        }
        if (img_c <= 0) {
           img_c = 0
        }
        if (img_c >= js_img_array.length) {
           img_c = 0
        }
        var counter = "<b>" + img_c + "</b>"
        $("#current").html(img_c)
        new_url = js_img_array[img_c]
        fabric.Image.fromURL(new_url, function (img) {    
           canvas.setBackgroundImage(img, canvas.renderAll.bind(canvas), {
           scaleX: canvas.width / img.width,
           scaleY: canvas.height / img.height
           });
        });

        console.log("FD:", frame_data)
        if (frame_data[img_c] !== undefined) {
           x_val = frame_data[img_c][0]
           y_val = frame_data[img_c][1]
           var circle = new fabric.Circle({
              radius: 5,
              fill: 'rgba(0,0,0,0)',
              strokeWidth: 1,
              stroke: 'rgba(200,50,50,.99)',
              left: x_val-5,
              top: y_val-5,
              selectable: false
           });
           canvas.add(circle);
        }
     }


     // Define the URL where your background image is located
   """
   can_script += """

   scale_x = {} 
   scale_y = {} """.format(cwidth / w, cheight / h)

   can_script += """

   // Define 
   fabric.Image.fromURL('""" + first_frame + """', function (img) {
     canvas.setBackgroundImage(img, canvas.renderAll.bind(canvas), {
        backgroundImageOpacity: 1,
        backgroundImageStretch: true,
   """
   can_script += """
        scaleX: scale_x,
        scaleY: scale_y
   """

   can_script += """
        });
   });
   canvas.setDimensions({width:""" + str(cwidth) + """, height:""" + str(cheight) + """});

   canvas.on('mouse:down', function(e) {
      for (i = 0; i < canvas._objects.length; i++) {
         canvas.remove(canvas._objects[i])
      }


      var pointer = canvas.getPointer(event.e);
      x_val = pointer.x | 0;
      y_val = pointer.y | 0;
      frame_data[img_c] = []
      frame_data[img_c].push(x_val)
      frame_data[img_c].push(y_val)
      //debug_info = frame_data.length.toString() + " frames selected"
      var circle = new fabric.Circle({
         radius: 5,
         fill: 'rgba(0,0,0,0)',
         strokeWidth: 1,
         stroke: 'rgba(200,50,50,.99)',
         left: x_val-5,
         top: y_val-5,
         selectable: false
      });
      canvas.add(circle);

      var isChecked=document.getElementById("advance").checked;
      if (isChecked == true) {
         refresh_pic("next") 
      }
      //document.getElementById('info').innerHTML = debug_info
      //img_c = img_c + 1
      imageUrl = js_img_array[img_c]

      /*
      alert(imageUrl)
      canvas.setBackgroundImage(imageUrl, canvas.renderAll.bind(canvas), {
         top: 0,
         left: 0,
         originX: 'left',
         originY: 'top',
         scaleX: scale_x,
         scaleY: scale_y
      });
      */
   });


   </script>
   """

   out = """
      <div id='main_container' class='container-fluid' style="border: 1px #000000 solid; width:{}px;">
   """.format(cwidth + 20)

   out += canvas


   out += "</div>"

   template = template.replace("{MAIN_TABLE}", out)   
   template += js_img_array 
   template += can_script

   return(template)



def get_contours(sub):
   if True:
      print("AllSkyAI get contours...")
      cont = []
      cnt_res = cv2.findContours(sub.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      noise = 0
      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         if w > 1 and h > 1:
            cont.append((x,y,w,h))
      return(cont)
