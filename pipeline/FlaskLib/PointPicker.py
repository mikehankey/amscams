import glob
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

def save_points(file, in_data, json_conf):

   if "/meteors/" not in file:
      day = file[0:10]
      mf = "/mnt/ams2/meteors/" + day + "/" + file 
   else :
      fn, dir = fn_dir(file)
      day = fn[0:10]
      mf = "/mnt/ams2/meteors/" + day + "/" + fn 

   if cfe(mf) == 1:
      mj = load_json_file(mf)
   else:
      return("No meteor file." + mf)

   hd_mfd = mj['hd_red']['hd_mfd']

   temp_mfd = {}
   for key in hd_mfd:
      ikey = int(key)
      temp_mfd[ikey] = hd_mfd[key]
      print("HDMFD:", key,type(key), hd_mfd[key])
   hd_mfd = dict(temp_mfd)

   admin_changes = {}
   if in_data is not None:
      #js_data = json.loads(in_data)

      for data in in_data:
         print(data)
         fn, x, y = data
         tx, ty, ra ,dec , az, el = XYtoRADec(x,y,file,mj['cp'],json_conf)
         #fn = int(fn)
         if fn in hd_mfd:
            print("HD MFD FOUND", hd_mfd[fn])
            hd_mfd[fn]['hd_lx'] = x
            hd_mfd[fn]['hd_ly'] = y
            hd_mfd[fn]['ra'] = ra
            hd_mfd[fn]['dec'] = dec
            hd_mfd[fn]['az'] = az
            hd_mfd[fn]['el'] = el 
            admin_changes[fn] = [x,y,ra,dec,az,el]
         else:
            print("CAN'T FIND KEY IN HD_MFD!", fn, type(fn))
            for key in hd_mfd:
               print("HDMFD:", key, type(key))
      print(file)

      mj['admin_changes'] = admin_changes 
      mj['hd_red']['hd_mfd'] = hd_mfd
      # fast_roi_frames(file, mj)
      print(mj)

      save_json_file("/mnt/ams2" + file, mj)
      print("saved " + mf)


      return("saved " + mf)


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
   //video_file = "/meteors/2021_02_09/final/2021_02_09_02_42_03_120_AMS1_010001.mp4"
   const params = new URLSearchParams(window.location.search)

   data_file = params.get("file")


    next_file = "none"
    total_files = all_files.length
    lf = "none"
    next_data_file = all_files[0]
    for (i in all_files) {
      af = all_files[i]
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
            if (id % 2 == 0) {
               cx = objects[i].left
               cy = objects[i].top
               nlx = (cx / scale) + crop_x
               nly = (cy / scale) + crop_y

               var line = new fabric.Line([cx, cy, cx+ 15, cy], { 
                  stroke: 'red' 
               }); 
               canvas.add(line)

            }
            else {
             //  nlx = ((objects[i].left + mx_val * -1) / scale) + crop_x
             //  nly = ((objects[i].top + my_val * -1) / scale) + crop_y


               cx = objects[i].left + mx_val
               cy = objects[i].top + my_val

               nlx = (cx / scale) + crop_x
               nly = (cy / scale) + crop_y
               var line = new fabric.Line([cx, cy, cx + 15, cy  ], { 
                  stroke: 'red' 
               }); 
               canvas.add(line)

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

        //http://192.168.1.4/save_points/2021_02_09/?file=/meteors/2021_02_09/2021_02_09_03_54_00_000_010005-trim-1156.json&data={%22data%22:[[1,5,5]]}
        const url = "/save_points/"
        var jdata = new Object();
        jdata.file = data_file ; // level is key and levelVal is value
        jdata.data = changed_frames; // level is key and levelVal is value
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
         new_url = this_url.replace(data_file, next_data_file)
         window.location.replace(new_url);
      }

      function goto_prev_file() {
         this_url= window.location.href
         new_url = this_url.replace(data_file, prev_data_file)
         window.location.replace(new_url);
      }


   fetch(data_file)
      .then((resp) => resp.json())
      .then(function(data) {
         video_file = data['final_vid'].replace("/mnt/ams2", "")
         stack_file = video_file.replace(".mp4", "_stacked.jpg")

         hd_mfd = data['hd_red']['hd_mfd']
         frame_buf = data['hd_red']['frame_buf']
         frame_num = frame_buf
         crop_area= data['hd_red']['hd_crop_info']
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
       lx = Math.floor((data['hd_lx']-crop_x) * scale)
       ly = Math.floor((data['hd_ly']-crop_y) * scale)
       fn = data['fn']
       orig_frames[fn] = [data['hd_lx'],data['hd_ly']]
       if (first_x == 0) {
          first_x =lx
          first_y =ly
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
       lx = Math.floor((data['hd_lx']-crop_x) * scale)
       ly = Math.floor((data['hd_ly']-crop_y) * scale)
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
       var line = new fabric.Line([lx, ly, lx + mx, ly + my], { 
            id: fn,
            stroke: 'green' 
       }); 
       var tid = "text" + fn.toString();
       var desc = fn.toString();
       var text = new fabric.Text(desc, { 
            id: tid,
            fontSize: 15 ,
            fill: "white" ,
            left: lx + mx,
            top: ly + my,

       }); 
       var group = new fabric.Group([ line, text ], {
          id: fn
       });

       //canvas.add(line)
       canvas.add(group)
       //console.log("LINE:", lx,ly,lx+mx,ly+my)
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

def point_picker(day, json_conf):
   files = glob.glob("/mnt/ams2/meteors/" + day + "/*.json"  )
   all_files = []
   for file in files:
      if "reduced" not in file:
         file = file.replace("/mnt/ams2", "")
         all_files.append(file)
   html = pp_js(all_files)

   return(html)
