import glob
import os
import json
from lib.PipeAutoCal import XYtoRADec
from lib.PipeUtil import load_json_file, save_json_file, cfe, fn_dir

def fast_roi_frames(file, mj=None):
   hd_cache_dir = ""
   sd_cache_dir = ""

   hd_files = ""
   sd_files = ""

#   if len(hd_file) > 0:
      # use HD
#   else:
      # use SD
   # only for the frames that have changed, create a new ROI thumbnail for that frame.
   # get the AZ/EL/RA/DEC for the changed frames and update the hd_mfd values
   # then update the sd mfd to mirror the hd_mfd
   # then save the mj

def save_points(file, station, in_data, json_conf):
   cloud_file = file
   day = file[0:10]
   if station == json_conf['site']['ams_id']:
      my_station = 1
      # we are editing the local station (my file), so we should save the local file 
      # and also update the cloud json version. 
      # we should also apply the calib and update az etc vals
   else:
      my_station = 0
      # we are editing a remote file and should save this only to the cloud (somewhere). 
      # we should also calculate the new az,el vals when but we need the remote station's json_conf
      # and lens distortion models to do this. 

   if my_station == 1:

      fn, dir = fn_dir(file)
      day = fn[0:10]
      ff = "/mnt/ams2/meteors/" + day + "/final/" + fn 
      if "?" in ff:
         el = ff.split("?")
         ff = el[0]

      print("FF:", ff)
      fj = load_json_file(ff)
      sd_vid = fj['media']['sd_vid'] 
      mf = sd_vid.replace(".mp4", ".json")
      mf = "/mnt/ams2/meteors/" + day + "/" + mf 
      print("MF:", mf)
      mj = load_json_file(mf)

   else:
      fn, dir = fn_dir(file)
      if "?" in fn:
         el = fn.split("?")
         fn = el[0]
      day = fn[0:10]
      year = fn[0:4]
      ff_cloud = "/mnt/archive.allsky.tv/" + station + "/METEORS/" + year + "/" + day + "/" + fn 
      ff_local_dir = "/mnt/ams2/meteor_archive/" + station + "/METEORS/" + year + "/" + day 
      if cfe(ff_local_dir, 1) == 0:
         os.makedirs(ff_local_dir)
      ff_local = "/mnt/ams2/meteor_archive/" + station + "/METEORS/" + year + "/" + day + "/" + fn 
      os.system("cp " + ff_cloud + " " + ff_local)
      print("cp " + ff_cloud + " " + ff_local)
      fj = load_json_file(ff_local)
      mj = {}

   admin_changes = {}
   if in_data is not None:
      for data in in_data:
         print("IN DATA:", data)

         fn, x, y = data
         fn = int(fn)
         x = int(x)
         y = int(y)
    
         if my_station == 1:
            # this is our local station so we can update the az,el easily
            tx, ty, ra ,dec , az, el = XYtoRADec(x,y,file,mj['cp'],json_conf)
            admin_changes[fn] = {}
            admin_changes[fn]['x'] = x
            admin_changes[fn]['y'] = y
            admin_changes[fn]['ra'] = ra
            admin_changes[fn]['dec'] = dec
            admin_changes[fn]['az'] = az
            admin_changes[fn]['el'] = el
         else:
            # this is a remote site so we need to think about this more
            # Just update the cloud file and also leave behind a .admin-changes version
            admin_changes[fn] = {}
            admin_changes[fn]['x'] = x
            admin_changes[fn]['y'] = y

      fj['admin_changes'] = admin_changes 
      mj['admin_changes'] = admin_changes 

      # update the final frame data
      new_final_frames = []
      for fd in fj['frames']:
         fn = fd['fn']
         if fn in admin_changes:
            fd['x'] = admin_changes[fn]['x']
            fd['y'] = admin_changes[fn]['y']
            if my_station == 1:
               fd['ra'] = admin_changes[fn]['ra']
               fd['dec'] = admin_changes[fn]['dec']
               fd['az'] = admin_changes[fn]['az']
               fd['el'] = admin_changes[fn]['el']
         new_final_frames.append(fd)
      fj['frames'] = new_final_frames

      if my_station == 0:
         save_json_file(ff_local, fj)
         if len(fj['admin_changes'].keys()) > 0:
            ac_local = ff_local.replace(".json", ".admin_changes")
            ac_cloud = ff_cloud.replace(".json", ".admin_changes")
            save_json_file(ac_local, fj['admin_changes'])
            
            os.system("cp " + ac_local + " " + ac_cloud)
            os.system("cp " + ff_local + " " + ff_cloud)
            print("Saved:", ac_cloud)
 
      # deal with legacy json files (push admin changes to relevant local files)
      # BUT ONLY FOR OUR OWN FILES. ??? 
      if my_station == 1:
         sd_changes = {}
         print("ADMIN CHANGES:", admin_changes)
         if my_station == 1: 
            new_hd_mfd = {}
            if "hd_red" in mj:
               for hd_fn in mj['hd_red']['hd_mfd']:
                  hd_fni = int(hd_fn)
                  print("HDMFD FN:", hd_fn, type(hd_fn))
                  data =  mj['hd_red']['hd_mfd'][hd_fn]
                  sd_fn = int(data['sd_fn'])
                  if hd_fni in admin_changes:
                     print("UPDATE HD_MFD:", hd_fn, hd_fni, type(hd_fn), type(hd_fni))
                     data['ad_x'] = admin_changes[hd_fni]['x']
                     data['ad_y'] = admin_changes[hd_fni]['y']
                     data['hd_lx'] = admin_changes[hd_fni]['x']
                     data['hd_ly'] = admin_changes[hd_fni]['y']
                     data['ra'] = admin_changes[hd_fni]['ra']
                     data['dec'] = admin_changes[hd_fni]['dec']
                     data['az'] = admin_changes[hd_fni]['az']
                     data['el'] = admin_changes[hd_fni]['el']
                     sd_changes[sd_fn] = {}
                     sd_changes[sd_fn]['ad_x'] = admin_changes[hd_fni]['x']
                     sd_changes[sd_fn]['ad_y'] = admin_changes[hd_fni]['y']
                     sd_changes[sd_fn]['x'] = admin_changes[hd_fni]['x']
                     sd_changes[sd_fn]['y'] = admin_changes[hd_fni]['y']
                     sd_changes[sd_fn]['ra'] = admin_changes[hd_fni]['ra']
                     sd_changes[sd_fn]['dec'] = admin_changes[hd_fni]['dec']
                     sd_changes[sd_fn]['az'] = admin_changes[hd_fni]['az']
                     sd_changes[sd_fn]['el'] = admin_changes[hd_fni]['el']
                     mj['hd_red']['hd_mfd'][hd_fn]  = data
         
            print("END HD_MFD UPDATE")  
            # reduced file meteor_frame_data (need SD frame mapping for this?!?!
            mfr = mf.replace(".json", "-reduced.json")
            mjr = load_json_file(mfr)
            new_sd_mfd = []
            for frame_data in mjr['meteor_frame_data']:
               dt, fnum, x, y, w, h, oint, ra, dec, az, el = frame_data 
               fnum = int(fnum)
               if fnum in sd_changes:
                  new_sd_mfd.append(( dt, fnum, sd_changes[fnum]['x'], sd_changes[fnum]['y'], w, h, oint, sd_changes[fnum]['ra'], sd_changes[fnum]['dec'], sd_changes[fnum]['az'], sd_changes[fnum]['el'] ))
               else:
                  new_sd_mfd.append(dt, fnum, x, y, w, h, oint, ra, dec, az, el)
            mjr['meteor_frame_data'] = new_sd_mfd

            save_json_file(mfr, mjr)
            save_json_file(mf, mj)
            save_json_file(ff, fj)
            print("Saved:", mfr)
            print("Saved:", mf)
            print("Saved:", ff)
            if "https://archive.allsky.tv" in cloud_file:
               cloud_file = cloud_file.replace("https://archive.allsky.tv", "")
            if "http://archive.allsky.tv" in cloud_file:
               cloud_file = cloud_file.replace("http://archive.allsky.tv", "")
            if "?" in cloud_file:
               el = cloud_file.split("?")
               cloud_file = el[0]

            # copy updated local file to the cloud
            cloud_file = "/mnt/archive.allsky.tv" + cloud_file
            cmd = "cp " + ff + " " + cloud_file
            print("CLOUD FILE:", cloud_file)
            print(cmd)
            os.system(cmd)
            #cloud_file 


         else:
            # we are working on a remote station file..
            # we should save admin changes in its own file with suffix (_ac) in the final dir
            # OR maybe we just use a shared? "admin_changes" dir
            print("REMOTE DATA SAVE NOT IMPLEMENTED YET!")
        


     


      return("saved ")


   else:
      return("no save needed. " + mf)

def pp_js(all_files):

   point_picker_js = """

<html lang="en">
<head>



    <meta charset="UTF-8">
    <title>Test frames to videos</title>
</head>
<body>
<script src="https://archive.allsky.tv/APPS/src/js/plugins/fabric.js?{RAND}"></script>
<canvas id='c' width=1920 height=1080 style="border:1px solid #000000;"></canvas>
<p>
<a href=javascript:goto_prev_file()>Prev</a> - 
<a href=javascript:goto_next_file()>Next</a>  
</p>
<span id="file_counter"></span>



<script src="/video2frames/index.js"></script>
<script>
   //var startTime = performance.now();
   var endTime;
   var all_files = """ + str(sorted(all_files)) + """
   var frameImgs = []
   var frame_num = 0
   const params = new URLSearchParams(window.location.search)

   df = params.get("file")
   st = params.get("station")
   date = df.substring(0,10) 
   year = df.substring(0,4) 
   data_file = df 
   odata_file = data_file
   prev_data_file = all_files[0]
   next_data_file = all_files[all_files.length[-1]]
   
    next_file = "none"
    total_files = all_files.length
    lf = "none"
    next_data_file = all_files[0]
    this_index = 0
    for (i in all_files) {
      af = all_files[i]
      console.log(data_file, af) 
      if (next_file == "next") {
         next_data_file = af
         next_file = "none"
      }
      if (af == data_file) {
         this_index = i
         next_file = "next"
         prev_data_file = lf
      }
      lf = af
    }
   console.log(prev_data_file, data_file, next_data_file)
   ti = parseInt(this_index) + 1
   count_html = "File " + ti + " of " + total_files
   //"/meteors/2021_02_09/2021_02_09_02_42_01_000_010001-trim-0005.json"
   span = document.getElementById("file_counter").innerHTML = count_html

   var Direction = {
      LEFT: 0,
      UP: 1,
      RIGHT: 2,
      DOWN: 3
   };

   var canvas = new fabric.Canvas("c", {
         hoverCursor: 'pointer',
         selection: true,
         selectionBorderColor: 'green',
         backgroundColor: null
   });

function moveSelected(direction,scale) {
            var activeObject = canvas.getActiveObject();
            var STEP = scale
            //var activeGroup = canvas.getActiveGroup();

            if (activeObject) {
                switch (direction) {
                case Direction.LEFT:
                    activeObject.left -= STEP;
                    break;
                case Direction.UP:
                    activeObject.top -= STEP;
                    break;
                case Direction.RIGHT:
                    activeObject.left += STEP;
                    break;
                case Direction.DOWN:
                    activeObject.top += STEP;
                    break;
                }
                activeObject.setCoords();
                canvas.renderAll();
                console.log('selected objects was moved');
            } 
            else {
                console.log('no object selected');
            }

        }


      function set_image() {

         frame = frameImgs[frame_num]
         fimg = imagedata_to_image(frame)
         console.log( 0, 0,crop_x,crop_y,crop_w,crop_h);

         canvas.getContext('2d').putImageData(frame, 0,0);


      }

      function goto_next_file() {

         console.log( "CROP AREA:" ,crop_x,crop_y,crop_w,crop_h);
         console.log( "SCALE:" ,scale);
         var objects = canvas.getObjects()
         var changed_frames = []
         for (let i in objects) {
            console.log(objects[i].type)
            if (objects[i].type == 'group') {
            id = objects[i].id 
            console.log("MOD:", i, i % 2)
            if (i % 2 == 1) {
               // for odd IDs we need the left side without extra length
               cx = objects[i].left
               cy = objects[i].top
               nlx = (cx / scale) + crop_x
               nly = (cy / scale) + crop_y

               var circ = new fabric.Circle({
                  top: cy - 2,
                  left: cx - 2,
                  radius: 4,
                  stroke: 'red'
               })
               canvas.add(circ)

               //var line = new fabric.Line([cx, cy, cx+ 15, cy], { 
               //   stroke: 'red' 
               //}); 
               //canvas.add(line)

            }
            else {
             //  nlx = ((objects[i].left + mx_val * -1) / scale) + crop_x
             //  nly = ((objects[i].top + my_val * -1) / scale) + crop_y
             // for even frames add the length to the left value

               cx = objects[i].left + mx_val
               cy = objects[i].top + my_val

               nlx = (cx / scale) + crop_x
               nly = (cy / scale) + crop_y

               var circ = new fabric.Circle({
                  top: cy - 2,
                  left: cx - 2,
                  radius: 4,
                  stroke: 'red'
               })
               canvas.add(circ)


               //var line = new fabric.Line([cx, cy, cx + 15, cy  ], { 
               //   stroke: 'red' 
               //}); 
               //canvas.add(line)

            }
            ox = orig_frames[id][0]
            oy = orig_frames[id][1]
            if (ox - nlx != 0 || oy - nly != 0) {
               console.log("CHANGED FRAME! (id, big crop xy, new xy, orig xy):", id, nlx, nly,orig_frames[id]) 
               changed_frames.push([id,nlx,nly])
            }
            else {
               console.log("FINE (id, big crop xy, new xy, orig xy):", id, nlx, nly,orig_frames[id]) 
            }
            //console.log(objects[i])
            }
        }

        //http://192.168.1.4/save_points/2021_02_09/?file=/meteors/2021_02_09/2021_02_09_03_54_00_000_010005-trim-1156.json&data={%22data%22:[[1,5,5]]}&station=st
        const url = "/save_points/"
        var jdata = new Object();
        jdata.file = data_file ; // level is key and levelVal is value
        jdata.data = changed_frames; // level is key and levelVal is value
        jdata.station = st ; // station id for this file
        var xhttp = new XMLHttpRequest();
        xhttp.open("POST", url, true);
        xhttp.setRequestHeader('Content-Type', 'application/json');
        xhttp.send(JSON.stringify(jdata));

        xhttp.onreadystatechange = function() {
           if (this.readyState == 4 && this.status == 200) {
              console.log(this.responseText);
           }
        }




         this_url= window.location.href
         new_url = this_url.replace(odata_file, next_data_file)

         //window.location.replace(new_url);
      }

      function goto_prev_file() {
         this_url= window.location.href
         new_url = this_url.replace(odata_file, prev_data_file)

         window.location.replace(new_url);
      }

   data_file = "https://archive.allsky.tv/" + st + "/METEORS/" + year + "/" + date + "/" + df + "?" + Date.now()
   fetch(data_file)
      .then((resp) => resp.json())
      .then(function(data) {
         vf = data['media']['final_vid'].split("/")
         
         video_file = vf[vf.length-1] 
         rand = Math.random()
         stack_file = video_file.replace(".mp4", "_stacked.jpg?" + rand)
         stack_file = "https://archive.allsky.tv/" + st + "/METEORS/" + year + "/" + date + "/" + stack_file 

         hd_mfd = data['frames']
         vf = data['media']['final_vid'].split("/")


         frame_buf = 0
         frame_num = hd_mfd[0]['fn']
         frame_buf = frame_num
         crop_area= data['hd_crop_info']
         //crop_area = data['hd_red']['crop_area']
         crop_x = crop_area[0] 
         crop_y = crop_area[1] 
         if (crop_y < 0) {
            crop_y = 0
         }
         crop_w = crop_area[2] - crop_area[0]
         crop_h = crop_area[3] - crop_area[1]







    //canvas.setBackgroundImage(stack_file, canvas.renderAll.bind(canvas), {
    //  backgroundImageOpacity: 0.5,
    //  backgroundImageStretch: false
    //});


    fabric.Image.fromURL(stack_file, function(myImg) {
       //i create an extra var for to change some image properties
       scale = 1920 / crop_w
       var img1 = myImg.set({ left: 0, top: 0 , scaleX: scale, scaleY: scale, cropX: crop_x, cropY: crop_y, width:crop_w,height:crop_h, selectable: false});
       canvas.add(img1); 
       canvas.sendToBack(img1);
    });

    scale = 1920 / crop_w



    // add points
    orig_frames = {}
    console.log(frame_buf)
     first_x = 0
     for (i in hd_mfd) {
       data = hd_mfd[i]
       lx = Math.floor((data['x']-crop_x) * scale)
       ly = Math.floor((data['y']-crop_y) * scale)
       fn = data['fn']
       orig_frames[fn] = [data['x'],data['y']]
       if (first_x == 0) {
          first_x = lx
          first_y = ly
       }
     }
        x_dist = first_x - lx
        y_dist = first_y - ly
        if (Math.abs(x_dist) > Math.abs(y_dist)) {
           dom_dir = "x"
           mx_val = 0 
           my_val = 100
        }
        else {
           dom_dir = "y"
           mx_val = 100
           my_val = 0
        }

     for (i in hd_mfd) {
       
       data = hd_mfd[i]
       lx = Math.floor((data['x']-crop_x) * scale)
       ly = Math.floor((data['y']-crop_y) * scale)
       fn = data['fn']

       console.log(data)
       if (i % 2 == 0) {
          mx = mx_val 
          my = my_val 
       }
       else {
          mx = mx_val * -1
          my = my_val * -1
       }
       console.log("LINE:", lx, ly)
       var line = new fabric.Line([lx, ly, lx + mx, ly + my], { 
            id: fn,
            stroke: 'green' 
       }); 
       var tid = "text" + fn.toString();
       var desc = fn.toString();
       //desc = "HIHI"
       var text = new fabric.Text(desc, { 
            id: "text" + fn,
            fontSize: 12 ,
            fill: "white" ,
            left: lx + mx ,
            top: ly + my

       }); 
       console.log("Add text for ", fn, lx+mx, ly+my)
       var group = new fabric.Group([ line, text ], {
          id: fn
       });

       //canvas.add(line)
       canvas.add(group)
       console.log(group)
       console.log("LINE:", lx,ly,lx+mx,ly+my)
     }


        fabric.util.addListener(document.body, 'keydown', function (options) {
            if (options.repeat) {
                return;
            }
            var key = options.which || options.keyCode; // key detection
            if (key === 37) { // handle Left key
                moveSelected(Direction.LEFT,scale);
            } else if (key === 38) { // handle Up key
                moveSelected(Direction.UP,scale);
            } else if (key === 39) { // handle Right key
                moveSelected(Direction.RIGHT,scale);
            } else if (key === 40) { // handle Down key
                moveSelected(Direction.DOWN,scale);
            }
        });





   });

</script>
</body>
</html>

   """
   return(point_picker_js)

def point_picker(day, station, json_conf):
   if station != json_conf['site']['ams_id']:
      local_cache = []
      year = day[0:4]
      local_dir = "/mnt/archive.allsky.tv/" + station + "/METEORS/" + year + "/" + day + "/"

      local_cloud_index = local_dir + "cloud_files.txt"
      if cfe(local_cloud_index) == 0:
         files = glob.glob("/mnt/archive.allsky.tv/" + station + "/METEORS/" + year + "/" + day + "/*.json"  )
         save_json_file(local_cloud_index, files)
      else:
         files = load_json_file(local_cloud_index)
      print("REMOTE STATION:", files)   
   else:
      files = glob.glob("/mnt/ams2/meteors/" + day + "/*.json"  )
   all_files = []

   if station != json_conf['site']['ams_id']:
      for file in files:
         print("ALL:", file)
         if "trim" not in file:

            file = file.split("/")[-1]
            print("ALL:", file)
            all_files.append(file)
   else:
      for file in files:
         if "reduced" not in file and "trim" not in file:
            print(file)
            mj = load_json_file(file)
            if "final_vid" in mj:
               final_file = mj['final_vid'].replace(".mp4", ".json")
               final_file = final_file.split("/")[-1]
               if "multi_station_event" in mj:
                  all_files.append(final_file)
   html = pp_js(all_files)

   return(html)
