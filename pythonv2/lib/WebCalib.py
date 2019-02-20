import numpy as np
import cv2
import cgi
import time
import glob
import os
from lib.FileIO import get_proc_days, get_day_stats, get_day_files , load_json_file, get_trims_for_file, get_days, save_json_file, cfe
from lib.VideoLib import get_masks, convert_filename_to_date_cam, find_hd_file_new, load_video_frames
from lib.ImageLib import mask_frame,stack_frames
from lib.CalibLib import radec_to_azel, clean_star_bg
from lib.UtilLib import check_running

def check_solve_status(json_conf,form):
   hd_stack_file = form.getvalue("hd_stack_file")
   debug = "DEBUG: "
   if "-stacked.png" in hd_stack_file:
      # CASE 1
      debug = debug + "case=1;"
      solved_file = hd_stack_file.replace("-stacked.png", ".solved")
      solved_file = solved_file.replace("HD/", "cal/tmp/")
      grid_file = solved_file.replace(".solved", "-grid.png")
   if ".jpg" in hd_stack_file:
      # CASE 2
      debug = debug + "case=2;"
      solved_file = hd_stack_file.replace(".jpg", ".solved")
      solved_file = solved_file.replace("HD/", "cal/tmp/")
      grid_file = solved_file.replace(".solved", "-grid.png")
   if "SD" in hd_stack_file:
      # CASE 3
      debug = debug + "case=3;"
      el = hd_stack_file.split("/")
      fn = el[-1]
      hd_stack_file = "/mnt/ams2/cal/tmp/" + fn
      solved_file = hd_stack_file.replace("-stacked.png", ".solved")
      grid_file = solved_file.replace(".solved", "-grid.png")

   


   #print(solved_file)
   running = check_running("solve-field")
   status = ""
   if running > 0:
      status = "running"
   elif running == 0 and cfe(solved_file) == 1:
      status = "success" 
   elif running == 0 and cfe(solved_file) == 0:
      status = "failed"
   #status = solved_file 
   debug = debug + " hd_stack_file=" + hd_stack_file + ";" + "solved_file=" + solved_file + ";" + "status=" + status
   
   if cfe(grid_file) == 1:
      tmp_img = cv2.imread(grid_file)
      tmp_img_tn = cv2.resize(tmp_img, (0,0),fx=.5, fy=.5)
      grid_file_half = grid_file.replace(".png", "-half.png")
      cv2.imwrite(grid_file_half, tmp_img_tn)
   else:
      grid_file_half = ""

   response = """
   {
      "status": """ + "\"" + status + "\"," + """ 
      "grid_file": """ + "\"" + grid_file_half + "\"," + """ 
      "solved_file": """ + "\"" + solved_file + "\"," + """ 
      "debug": """ + "\"" + debug + "\"" + """ 
      
   }
   """

   print(response)



def solve_field(json_conf, form):

   hd_stack_file = form.getvalue("hd_stack_file")
   fn,tdir = get_hd_filenames(hd_stack_file)
   plate_file = fn.replace("-stacked.png", "-stacked-an.png")
   plate_file = tdir + plate_file
   cmd = "cp " + plate_file + " /mnt/ams2/cal/tmp/"
   os.system(cmd)

   cmd = "cp " + hd_stack_file + " /mnt/ams2/cal/tmp/"
   os.system(cmd)
   new_fn = fn.replace("-stacked.png", ".jpg")
   temp = cv2.imread(plate_file, 0)
   cv2.imwrite("/mnt/ams2/cal/tmp/" + new_fn, temp)
   cmd = "cd /home/ams/amscams/pythonv2; ./plateSolve.py " + "/mnt/ams2/cal/tmp/" + new_fn + " > /tmp/plt.txt 2>&1 &"
   os.system(cmd)
   #plate_solve("/mnt/ams2/cal/tmp/" + new_fn, json_conf)
   status = "running"
   debug = "DEBUG: hd_stack_file" + hd_stack_file + "; cmd =" + cmd + "; status = " + status
   response = """
   {
      "status": """ + "\"" + status + "\"," + """ 
      "debug": """ + "\"" + debug + "\"" + """ 
   }
   """
   print(response)


def cnt_max_px(cnt_img):
   cnt_img = cv2.GaussianBlur(cnt_img, (7, 7), 0)
   min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)

   return(max_loc, min_val, max_val)

def make_plate_from_points(json_conf, form):
   hd_stack_file = form.getvalue("hd_stack_file")
   hd_stack_img = cv2.imread(hd_stack_file, 0)
   ih,iw = hd_stack_img.shape
   plate_img = np.zeros((ih,iw),dtype=np.uint8)
   hd_stack_file_an = hd_stack_file.replace(".png", "-an.png")
   half_stack_file_an = hd_stack_file.replace("-stacked.png", "-half-stack-an.png")
   #print(half_stack_file_an)
   pin = form.getvalue("points")
   points = []
   temps = pin.split("|")
   for temp in temps:
      if len(temp) > 0:
         (x,y) = temp.split(",")
         x,y = int(float(x)),int(float(y))
         x,y = int(x)+5,int(y)+5
         x,y = x*2,y*2
         points.append((x,y))
     

   hd_stack_img = cv2.imread(hd_stack_file,0);
   hd_stack_img_an = hd_stack_img.copy()
   star_points = []
   for x,y in points:
      x,y = int(x),int(y)
      #cv2.circle(hd_stack_img_an, (int(x),int(y)), 5, (128,128,128), 1)
      y1 = y - 15
      y2 = y + 15
      x1 = x - 15
      x2 = x + 15
      cnt_img = hd_stack_img[y1:y2,x1:x2]
      ch,cw = cnt_img.shape
      max_pnt,max_val,min_val = cnt_max_px(cnt_img) 
      mx,my = max_pnt 
      mx = mx - 15
      my = my - 15

      cy1 = y + my - 15
      cy2 = y + my +15
      cx1 = x + mx -15
      cx2 = x + mx +15
      if ch > 0 and cw > 0:
         cnt_img = hd_stack_img[cy1:cy2,cx1:cx2]
         bgavg = np.mean(cnt_img)
         cnt_img = clean_star_bg(cnt_img, bgavg + 3)

      #cv2.rectangle(hd_stack_img_an, (x1,y1), (x2,y2), (90, 90, 90), 1)
         cv2.rectangle(hd_stack_img_an, (x+mx-5-15, y+my-5-15), (x+mx+5-15, y+my+5-15), (128, 128, 128), 1)
         cv2.rectangle(hd_stack_img_an, (x+mx-15-15, y+my-15-15), (x+mx+15-15, y+my+15-15), (128, 128, 128), 1)
         star_points.append([x+mx,y+my])
         plate_img[cy1:cy2,cx1:cx2] = cnt_img


   #cv2.imwrite(hd_stack_file_an, hd_stack_img_an)
   cv2.imwrite(hd_stack_file_an, plate_img)
   half_stack_img_an = cv2.resize(hd_stack_img_an, (0,0),fx=.5, fy=.5)
   half_stack_plate = cv2.resize(plate_img, (0,0),fx=.5, fy=.5)
   #cv2.imwrite(half_stack_file_an, half_stack_img_an)
   cv2.imwrite(half_stack_file_an, half_stack_plate)
   response = """
   {
      "hd_stack_file_an": """ + "\"" + hd_stack_file_an + "\"," + """ 
      "half_stack_file_an": """ + "\"" + half_stack_file_an + "\"," + """
      "stars": """ + "" + str(star_points) + "" + """ 
   }
   """
   print(response)

def get_sd_filenames(sd_video_file):
   el = sd_video_file.split("/")
   fn = el[-1]
   tdir = sd_video_file.replace(fn, "")
   sd_img_dir = tdir + "images/"
   sd_stack = sd_img_dir + fn.replace(".mp4", "-stacked.png")
   return(sd_stack)

def get_hd_filenames(hd_video_file):
   el = hd_video_file.split("/")
   fn = el[-1]
   tdir = hd_video_file.replace(fn, "")
   return(fn,tdir)


def calibrate_pic(json_conf,form):
   override = form.getvalue("override") 
   #override = "/mnt/ams2/sirko/2019_02_14_23_44_57_000_010001-stacked.png"
   if override is None or override == "":
      print("looking for HD file.")
      sd_video_file = form.getvalue("sd_video_file")
      sd_stack_file = get_sd_filenames(sd_video_file)
      stack_img = cv2.imread(sd_stack_file,0)
      ih,iw = stack_img.shape
      hd_file, hd_trim = find_hd_file_new(sd_video_file, 250, 10, 0)   
   if hd_file is None:
      print("NO HD FILE FOUND. Using SD image instead.")
      # no HD file exists..
      hdm_x = 2.7272
      hdm_y = 1.875
 
      hd_stack_img = cv2.resize(stack_img, (1920,1080))
      half_stack_img = cv2.resize(hd_stack_img, (0,0),fx=.5, fy=.5)
      sd_stack_file = sd_stack_file.replace("_000_", "_007_")
      half_stack_file = sd_stack_file.replace("-stacked.png", "half-stack.png")
      hd_stack_file = sd_stack_file.replace("-stacked.png", "-stacked.png")
      override = hd_stack_file 
      cv2.imwrite(half_stack_file, half_stack_img)
      cv2.imwrite(hd_stack_file, hd_stack_img)

   if override is None or override == "":
      #print(hd_file,"<BR>")
      hd_stack_file = hd_file.replace(".mp4", "-stacked.png")
      half_stack_file = hd_file.replace(".mp4", "-half-stack.png")
      if cfe(hd_stack_file) == 0: 
         frames = load_video_frames(hd_file, json_conf, 20)
         hd_stack_file, hd_stack_img = stack_frames(frames, hd_file)
         half_stack_img = cv2.resize(hd_stack_img, (0,0),fx=.5, fy=.5)
         cv2.imwrite(half_stack_file, half_stack_img)
         ih,iw = half_stack_img.shape
         #print("HD FILE Exists :", half_stack_file) 
      else:
         half_stack_img = cv2.imread(half_stack_file,0)
         ih,iw = half_stack_img.shape
   if override is not None:
      hd_stack_file = override
      #print(hd_stack_file)
      hd_stack_img = cv2.imread(hd_stack_file, 0)
      half_stack_file = hd_stack_file.replace("-stacked.png", "-half-stack.png")
      half_stack_img = cv2.resize(hd_stack_img, (0,0),fx=.5, fy=.5)
      cv2.imwrite(half_stack_file, half_stack_img)
      ih,iw = half_stack_img.shape

   canvas_js = """
      <script>

      var hd_stack_file = '""" + hd_stack_file + """'
      var waiting = false

      function sleep (time) {
         return new Promise((resolve) => setTimeout(resolve, time));
      }

      function solve_field(hd_stack_file) {

         check_solve_status(1)


      }

      function send_ajax_solve() { 
         ajax_url = "/pycgi/webUI.py?cmd=solve_field&hd_stack_file=" + hd_stack_file 
         alert(ajax_url)
         $.get(ajax_url, function(data) {
            $(".result").html(data);
            var json_resp = $.parseJSON(data);
            alert(json_resp['debug'])
            sleep(5000).then(() => {
               alert("time to wake up!")
               check_solve_status(0)
            });
         });


      }

      function check_solve_status(then_run) {
         ajax_url = "/pycgi/webUI.py?cmd=check_solve_status&hd_stack_file=" + hd_stack_file 
         alert(ajax_url)
         waiting = true
         $.get(ajax_url, function(data) {
            $(".result").html(data);
            var json_resp = $.parseJSON(data);
            waiting = false
            alert(json_resp['debug']) 
            if (json_resp['status'] == 'failed' && then_run == 1) {
               send_ajax_solve()
            }
            if (json_resp['status'] == 'running' && then_run == 0) {
               alert("still running")
            }
            if (json_resp['status'] == 'success' && then_run == 0) {
               alert("solved")
            }
            if (json_resp['status'] == 'success' && then_run == 1) {
               grid_img = json_resp['grid_file']
               canvas.setBackgroundImage(grid_img, canvas.renderAll.bind(canvas));
               alert("GRID IMAGE:" + grid_img)
               alert(json_resp['debug'])
            }
            if (json_resp['status'] == 'failed' && then_run == 0) {
               alert(json_resp['solved_file'])
               alert("failed")
            }

         });
      }

      function make_plate(img_url) {
         var point_str = ""
         for (i in user_stars) {
            point_str = point_str + user_stars[i].toString()  + "|"
         }

         var point_str = ""
         var objects = canvas.getObjects('circle')
         for (let i in objects) {
            x = objects[i].left
            y = objects[i].top
            point_str = point_str + x.toString() + "," + y.toString() + "|"
         }

         ajax_url = "/pycgi/webUI.py?cmd=make_plate_from_points&hd_stack_file=" + hd_stack_file + "&points=" + point_str 
         alert(ajax_url)
 
         $.get(ajax_url, function(data) {
            $(".result").html(data);
            var json_resp = $.parseJSON(data);
            alert(json_resp['half_stack_file_an']) 
            var new_img = json_resp['half_stack_file_an'] + "?r=" + Math.random().toString()
            var stars = json_resp['stars'];

            for (let s in stars) {
              
              cx = stars[s][0] - 11 
              cy = stars[s][1] - 11

              var circle = new fabric.Circle({
                 radius: 5, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(100,200,200,.5)', left: cx/2, top: cy/2,
                 selectable: false
              });
              canvas.add(circle);

            }            

            alert(stars)
            canvas.setBackgroundImage(new_img, canvas.renderAll.bind(canvas));
            // remove existing objects & replace with pin pointed stars
            for (let i in objects) {
               canvas.remove(objects[i]);
            }


            //alert(json_resp.error)
            //alert(data)
         });


      }


      var canvas = new fabric.Canvas('c', {
         hoverCursor: 'default', 
         selection: true 
      });
      var my_image = " """ + half_stack_file + """"
      var user_stars = []

      canvas.setBackgroundImage(my_image, canvas.renderAll.bind(canvas));

      canvas.on('mouse:move', function(e) {
         var pointer = canvas.getPointer(event.e);
         x_val = pointer.x | 0;
         y_val = pointer.y | 0;
         cx = 2
         cy = 2
         document.getElementById('info_panel').innerHTML = x_val.toString() + " , " + y_val.toString()
         myresult = document.getElementById('myresult')
         myresult.style.backgroundImage = "url('" + hd_stack_file + "')";
         myresult.style.backgroundPosition = "-" + ((x_val*cx)-75) + "px -" + ((y_val * cy)-75)  + "px" 
      });

      canvas.on('mouse:down', function(e) {
         var pointer = canvas.getPointer(event.e);
         x_val = pointer.x | 0;
         y_val = pointer.y | 0;
         user_stars.push([x_val,y_val])

         var circle = new fabric.Circle({
            radius: 5, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(100,200,200,.5)', left: x_val-5, top: y_val-5,
            selectable: false
         });

         var objFound = false
         var clickPoint = new fabric.Point(x_val,y_val);

         //canvas.forEachObject(function (obj) {
         var objects = canvas.getObjects('circle')
         for (let i in objects) {
            if (!objFound && objects[i].containsPoint(clickPoint)) {
               objFound = true
               canvas.remove(objects[i]);
            }
         }
         if (objFound == false) {
            canvas.add(circle);
         }


         document.getElementById('info_panel').innerHTML = "star added"
         document.getElementById('star_panel').innerHTML = "Total Stars: " + user_stars.length;
      });

      </script>
   """


   canvas_html = """
      <div style="float:left"><canvas id="c" width="{:d}" height="{:d} style="border:2px solid #000000;"></canvas></div><div style="float:left"><div style="position: relative; height: 150px; width: 150px" id="myresult" class="img-zoom-result"> </div></div><div style="clear: both"></div>
   """.format(iw,ih)

   canvas_html = canvas_html + """ 
      <div id=info_panel>Info: </div>
      <div id=star_panel>Stars: </div>
      <div id=action_buttons>
         <input type=button id="button1" value="Make Plate" onclick="javascript:make_plate('""" + hd_stack_file + """')"> 
         <input type=button id="button1" value="Find Stars"> 
         <input type=button id="button1" value="Solve Field" onclick="javascript:solve_field('""" + hd_stack_file + """')"> 
         <input type=button id="button1" value="Fit Field" onclick="javascript:fit_field('""" + hd_stack_file + """')"> 
      </div>
       <BR><BR>
   """

   print(canvas_html)
   print(canvas_js)
