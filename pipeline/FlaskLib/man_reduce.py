from lib.PipeUtil import load_json_file, save_json_file, cfe, bound_cnt, convert_filename_to_date_cam
from lib.PipeDetect import analyze_object, get_trim_num, make_base_meteor_json
from lib.PipeAutoCal import get_image_stars, get_catalog_stars , pair_stars, eval_cnt, update_center_radec, fn_dir
from lib.PipeDetect import fireball, apply_frame_deletes, find_object, analyze_object, make_base_meteor_json, fireball_fill_frame_data, calib_image, apply_calib, grid_intensity_center
from lib.PipeVideo import ffprobe, load_frames_fast
from lib.PipeImage import restack_meteor
import datetime
import os
import cv2
from FlaskLib.FlaskUtils import parse_jsid, make_default_template
import glob
import numpy as np


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


def save_man_reduce(data):
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


def meteor_man_reduce(meteor_file, x,y,w,h, step, first_frame,last_frame,ScaleFactor):
   json_conf = load_json_file("../conf/as6.json")
   amsid = json_conf['site']['ams_id']
   template = make_default_template(amsid, "live.html", json_conf)
   fn,dir = fn_dir(meteor_file)
   prefix = fn.replace(".mp4", "")
   year = prefix[0:4]
   day = prefix[0:10]
   vid_file = "/mnt/ams2/meteors/" + day + "/" + prefix + ".mp4"
   cache_dir = "/mnt/ams2/CACHE/" + year + "/" + prefix + "/crop_frames/"
   cache_dir_f = "/mnt/ams2/CACHE/" + year + "/" + prefix + "/sd_frames/"

   if True:
      hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(vid_file, json_conf, 0, 0, 1, 1,[])
      vh,vw = hd_frames[0].shape[:2]
      vw,vh = int(vw),int(vh)
      hdm_x = 960 / int(vw)
      hdm_y = 540/ int(vh)
      if step is None:
         nx = int(int(x) / hdm_x)
         ny = int(int(y) / hdm_y)
         nw  = int(int(w)  )
         nh  = int(int(h) )
      else:
         nx = int(x)
         ny = int(y)
         nw = int(w)
         nh = int(h)
      sfile = vid_file.replace(".mp4", "-stacked.jpg")
      dimg = cv2.imread(sfile)
      cv2.rectangle(dimg, (int(nx), int(ny)), (int(nx+nw) , int(ny+nh) ), (150, 150, 150), 1) 
      cv2.imwrite("/mnt/ams2/debug.jpg", dimg)
      print("ORIG SD CROP:", nx, ny)

   if cfe(cache_dir, 1) == 0:
      os.makedirs(cache_dir)
   if cfe(cache_dir_f, 1) == 0:
      os.makedirs(cache_dir_f)
   vid_fn,vid_dir = fn_dir(vid_file)
   day = vid_fn[0:10]
   out = """
   <style>
      .frame {
         float: left;
      }
      .hidden {
         display: none;
      }
   </style>
   <script>
      amsid = '""" + amsid + """'
      frames = []
      points = []
      file = '""" + vid_file + """'
      file_fn = '""" + vid_fn+ """'
      day = '""" + day + """'
      crop_x = """ + str(nx) + """
      crop_y = """ + str(ny) + """
      crop_w = """ + str(nw) + """
      crop_h = """ + str(nh) + """
      ow = """ + str(vw) + """
      oh = """ + str(vh) + """
      function select_frame(fn) {
         //<a href=javascript:select_frame(" + str(c) + ")>
         frames.push(fn)
         if (frames.length == 2) {
            // goto step 2
            next_step_url = "/meteor_man_reduce/?file=" + file + "&x=" + crop_x + "&y=" + crop_y + "&w=" + crop_w + "&h=" + crop_h + "&step=2&first_frame=" + frames[0] + "&last_frame=" + frames[1] 
            window.location.href = next_step_url 
         }
      }
   </script>
   """

   print("REDIR SD CROP:", nx, ny)
   print("STEPP:", step)

   if step is None:
      out += "<h2>Select the first and last frame containing the meteor.</h2>"

   elif step == 2:
      print("STEPP2:", step)
      out += "<h2>Select leading edge of each meteor frame.</h2>"
      hd_color_frames = glob.glob(cache_dir + "*.jpg")

   c = 0
   crop_files = []
   crop_frames = []
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

         cf = frame[ny:ny+nh, nx:nx+nw]
         crop_frames.append(cf)
         cv2.imwrite(cf_file, cf)
         cv2.rectangle(frame, (int(nx), int(ny)), (int(nx+nw) , int(ny+nh) ), (150, 150, 150), 1) 
         cv2.imwrite(ff_file, frame)
      crop_files.append(cf_file)
      c += 1 
   c = 0
   if step == None:
      for cf in crop_files:
         cf = cf.replace("/mnt/ams2", "")
      
         out += "<div class='frame' id='" + str(c) + "'><a href=javascript:select_frame(" + str(c) + ")><img src=" + cf + "></a></div>"
         c += 1
   else:
      # show 1 frame at a time capturing the x,y selected from the previous frame
      first_frame = int(first_frame)
      frame = crop_files[first_frame] 
      img = cv2.imread(frame)
      h,w = img.shape[:2]
      if h < 150 and w < 150:
         ScaleFactor = 5
         h = int(h * ScaleFactor)
         w = int(w * ScaleFactor)
         multi = ScaleFactor
      else:
         ScaleFactor = 1
         multi = 1
 
      v_crop_files = []
      for cf in crop_files:
         vf = cf.replace("/mnt/ams2", "")
         v_crop_files.append(vf)

      frame = frame.replace("/mnt/ams2", "") 
      out += "<div style='display:none'><img id='source' src=" + frame + " width=" + str(w) + " height=" + str(h) + "></a></div>"
      out += """

            <div class="canvas-container">
                 <canvas id="c" width='""" + str(w) + """' height='""" + str(h) + """'></canvas>
            </div>
      <div id="info"></div>
      <input type=button onClick='javascript:save_manual_reduce()' value=" Save ">
<script src="https://archive.allsky.tv/APPS/dist/js/amscam.min.js"></script>

<script src="/src/js/plugins/fabric.js?{RAND}"></script>

      <script> 
         var ScaleFactor = """ + str(ScaleFactor) + """
         function save_manual_reduce() {
            items = frame_data.length
            msg  = "save " + items.toString() + " items"
            alert(msg)
            dlist = ""
            for (i = 0; i<=frame_data.length-1; i++)
            {
               dlist = dlist + frame_data[i] + ";"
            }

            $.ajax({
               type:"POST",
               url:  "/save_man_reduce/",
               data: {
                  frame_data: dlist,
                  sd_video_file: file,
                  x: crop_x,
                  y: crop_y,
                  w: crop_w,
                  h: crop_h,
                  ScaleFactor: ScaleFactor,
                  oh: oh,
                  ow: ow

               },
               success: function(data) {

                  meteor_page_url = "/meteors/" + amsid + "/" + day + "/" + file_fn + "/"
                  window.location.href = meteor_page_url 
                  top.window.location.href=meteor_page_url
                  //$.each(ids, function(i,v){
                        //meteor_is_deleted(v);
                  //});
               },
               error: function() {
                  alert('Error saving. Please, reload the page and try again later.')
                  //loading_done();
               }
            });

         }

         var debug_info = ""
         var images = """ + str(v_crop_files) + """
         var frame_num = """ + str(first_frame) + """;
         var frame_data = []
         var canvas = new fabric.Canvas('c', {
            hoverCursor: 'default',
            selection: true
         });
         var imageUrl = '""" + frame + """';
 
         //fabric.Image.fromURL('""" + frame + """', function(img) {
         //   canvas.add(img).setActiveObject(img)
         //});
         canvas.setBackgroundImage(imageUrl, canvas.renderAll.bind(canvas), {
            top: 0,
            left: 0,
            originX: 'left',
            originY: 'top',
            scaleX: ScaleFactor,
            scaleY: ScaleFactor 
         });

         canvas.on('mouse:down', function(e) {
            var pointer = canvas.getPointer(event.e);
            x_val = pointer.x | 0;
            y_val = pointer.y | 0;
            frame_data.push([frame_num,x_val,y_val])
            debug_info = frame_data.length.toString() + " frames selected"
            //for (i in frame_data) {
            //   debug_info = debug_info + frame_data[i][0].toString() + ":" + frame_data[i][1].toString() + "," + frame_data[i][2].toString() + "<BR>"
            //}
            var circle = new fabric.Circle({
               radius: 5,
               fill: 'rgba(0,0,0,0)',
               strokeWidth: 1,
               stroke: 'rgba(100,200,200,.85)',
               left: x_val-5,
               top: y_val-5,
               selectable: false
            });
            //canvas.add(circle);
            document.getElementById('info').innerHTML = debug_info
            frame_num = frame_num + 1
            imageUrl = images[frame_num]
            //alert(imageUrl)
            canvas.setBackgroundImage(imageUrl, canvas.renderAll.bind(canvas), {
               top: 0,
               left: 0,
               originX: 'left',
               originY: 'top',
               scaleX: ScaleFactor,
               scaleY: ScaleFactor 
            });
         });
      </script>
      """
   template = template.replace("{MAIN_TABLE}", out)   
   return(out)
