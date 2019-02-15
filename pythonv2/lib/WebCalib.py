import numpy as np
import cv2
import cgi
import time
import glob
import os
from lib.FileIO import get_proc_days, get_day_stats, get_day_files , load_json_file, get_trims_for_file, get_days, save_json_file, cfe
from lib.VideoLib import get_masks, convert_filename_to_date_cam, find_hd_file_new, load_video_frames
from lib.ImageLib import mask_frame,stack_frames
from lib.CalibLib import radec_to_azel

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
      max_pnt,max_val,min_val = cnt_max_px(cnt_img) 
      mx,my = max_pnt 
      mx = mx - 15
      my = my - 15

      cy1 = y + my - 15
      cy2 = y + my +15
      cx1 = x + mx -15
      cx2 = x + mx +15
      cnt_img = hd_stack_img[cy1:cy2,cx1:cx2]

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


def calibrate_pic(json_conf,form):
   sd_video_file = form.getvalue("sd_video_file")
   sd_stack_file = get_sd_filenames(sd_video_file)
   stack_img = cv2.imread(sd_stack_file,0)
   ih,iw = stack_img.shape
   hd_file, hd_trim = find_hd_file_new(sd_video_file, 250, 10, 0)   
   if hd_file is not None:
      print(hd_file,"<BR>")
      hd_stack_file = hd_file.replace(".mp4", "-stacked.png")
      half_stack_file = hd_file.replace(".mp4", "-half-stack.png")
      if cfe(hd_stack_file) == 0: 
         frames = load_video_frames(hd_file, json_conf, 20)
         hd_stack_file, hd_stack_img = stack_frames(frames, hd_file)
         half_stack_img = cv2.resize(hd_stack_img, (0,0),fx=.5, fy=.5)
         cv2.imwrite(half_stack_file, half_stack_img)
         ih,iw = half_stack_img.shape
         print("HD FILE Exists :", half_stack_file) 
      else:
         half_stack_img = cv2.imread(half_stack_file,0)
         ih,iw = half_stack_img.shape

   canvas_js = """
      <script>

      var hd_stack_file = '""" + hd_stack_file + """'

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
         document.getElementById('info_panel').innerHTML = x_val.toString() + " , " + y_val.toString()
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
      <canvas id="c" width="{:d}" height="{:d} style="border:2px solid #000000;"></canvas>
   """.format(iw,ih)

   canvas_html = canvas_html + """ 
      <div id=info_panel>Info: </div>
      <div id=star_panel>Stars: </div>
      <div id=action_buttons>
         <input type=button id="button1" value="Make Plate" onclick="javascript:make_plate('""" + hd_stack_file + """')"> 
         <input type=button id="button1" value="Find Stars"> 
         <input type=button id="button1" value="Solve Field"> 
         <input type=button id="button1" value="Fit Field"> 
      </div>
   """

   print(canvas_html)
   print(canvas_js)
