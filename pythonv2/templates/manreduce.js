var current_frame = 0
var frame_base = ""
var points = new Array()
// points is same as frame hist: frame_num,x,y,w,h,mx,my,max_px

var canvas = new fabric.Canvas('cnv', {
         hoverCursor: 'default',
         selection: true
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
   console.log("mike:" + orig_file + ":" + cal_params_file)
   pin_point(x_val,y_val,current_frame,orig_file,cal_params_file)


   document.getElementById('info_panel').innerHTML = "star added"
   //document.getElementById('star_panel').innerHTML = "Total Stars: " + user_stars.length;
});

function del_point(fn,orig_file) {
   var ajax_url = "/pycgi/webUI.py?cmd=del_manual_points&frame_num=" + fn + "&orig_file=" + orig_file
   console.log(ajax_url) 
   $.get(ajax_url, function(data) {
      $(".result").html(data);
      var json_resp = $.parseJSON(data);
      var manual_frame_data = json_resp['manual_frame_data']
      refresh_points(manual_frame_data)

         var objects = canvas.getObjects('circle')
         for (let i in objects) {
            canvas.remove(objects[i]);
         }
    });



}

function refresh_points(manual_frame_data) {
         var objects = canvas.getObjects('rect')
         for (let i in objects) {
            canvas.remove(objects[i]);
         }
         out_html = "<div class='divTable' style='border: 1px solid #000;' ><div class='divTableBody'>"
         out_html = out_html + " <div class='divTableRow'><div class='divTableCell'>FN</div><div class='divTableCell'>Frame Time</div><div class='divTableCell'>X/Y - W/H</div><div class='divTableCell'>Max PX</div><div class='divTableCell'>RA/DEC</div><div class='divTableCell'>AZ/EL</div></div>"

         for (let s in manual_frame_data) {
            ft = manual_frame_data[s][0]
            fn = manual_frame_data[s][1]
            x = parseInt(manual_frame_data[s][2] )
            y = parseInt(manual_frame_data[s][3] )
            w = manual_frame_data[s][4]
            h = manual_frame_data[s][5]
            mpv = manual_frame_data[s][6]
            ra = manual_frame_data[s][7]
            dec = manual_frame_data[s][8]
            az = manual_frame_data[s][9]
            el = manual_frame_data[s][10]
            radec = ra + "," + dec
            azel = az + "," + el
            del_link = "<a href=\"javascript:del_point('" + fn + "','" +orig_file + "')\">X</a>"
            out_html = out_html + " <div class='divTableRow'><div class='divTableCell'>" + del_link + " " + fn + "</div><div class='divTableCell'>" + ft + "</div><div class='divTableCell'>" + x + "," + y + " " + w + "/" + h + "</div>"
            out_html = out_html + "<div class='divTableCell'>" + mpv + "</div><div class='divTableCell'>" + radec + "</div><div class='divTableCell'>" + azel + "</div></div>"
            var starrect = new fabric.Rect({
               fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(230,100,200,.25)', left: x-5, top: y-5,
                    width: 10,
                    height: 10 ,
                    selectable: false
               });
               canvas.add(starrect);


         }
      out_html = out_html + "</div>"
      document.getElementById('info_panel').innerHTML = out_html


}


function pin_point(x,y,current_frame,orig_file,cal_params_file) {
   msg = x + "," + y + "," + current_frame + " " + frame_base + " " + orig_file + " " + cal_params_file
   console.log("mike2" + msg)

   var frame_file = frame_base + "frames" + ("00000" + current_frame).slice(-5) + ".png"
   console.log(frame_file) 

   var ajax_url = "/pycgi/webUI.py?cmd=pin_point&frame_file=" + frame_file + "&x=" + x + "&y=" + y + "&orig_file=" + orig_file + "&cal_params_file=" + cal_params_file
   console.log(ajax_url) 
      $.get(ajax_url, function(data) {
         $(".result").html(data);
         var json_resp = $.parseJSON(data);
         var pp_x = json_resp['pp_x']
         var pp_y = json_resp['pp_y']
         var pp_w = json_resp['pp_w']
         var pp_h = json_resp['pp_h']
         var pp_mx = json_resp['pp_mx']
         var pp_my = json_resp['pp_my']
         var pp_maxp = json_resp['pp_maxp']
         var manual_frame_data = json_resp['manual_frame_data']
         console.log(pp_x, pp_y, pp_w, pp_h, pp_mx, pp_my, pp_maxp) 
         console.log(manual_frame_data)
         lc = 0
         x = x + pp_mx
         y = y + pp_my

         var objects = canvas.getObjects('circle')
         for (let i in objects) {
            canvas.remove(objects[i]);
         }

         var circle = new fabric.Circle({
            radius: 5, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(255,255,255,.5)', left: x-10, top: y-10,
            selectable: false
         });
            canvas.add(circle);

         var objects = canvas.getObjects('rect')
         for (let i in objects) {
            canvas.remove(objects[i]);
         }
         out_html = "<div class='divTable' style='border: 1px solid #000;' ><div class='divTableBody'>"
         out_html = out_html + " <div class='divTableRow'><div class='divTableCell'>FN</div><div class='divTableCell'>Frame Time</div><div class='divTableCell'>X/Y - W/H</div><div class='divTableCell'>Max PX</div><div class='divTableCell'>RA/DEC</div><div class='divTableCell'>AZ/EL</div></div>"

         for (let s in manual_frame_data) {
            ft = manual_frame_data[s][0]
            fn = manual_frame_data[s][1]
            x = parseInt(manual_frame_data[s][2] )
            y = parseInt(manual_frame_data[s][3] )
            w = manual_frame_data[s][4]
            h = manual_frame_data[s][5]
            mpv = manual_frame_data[s][6]
            ra = manual_frame_data[s][7]
            dec = manual_frame_data[s][8]
            az = manual_frame_data[s][9]
            el = manual_frame_data[s][10]

            radec = ra + "," + dec
            azel = az + "," + el
            del_link = "<a href=\"javascript:del_point('" + fn + "','" +orig_file + "')\">X</a>"
            out_html = out_html + " <div class='divTableRow'><div class='divTableCell'>" + del_link + " " + fn + "</div><div class='divTableCell'>" + ft + "</div><div class='divTableCell'>" + x + "," + y + " " + w + "/" + h + "</div>"
            out_html = out_html + "<div class='divTableCell'>" + mpv + "</div><div class='divTableCell'>" + radec + "</div><div class='divTableCell'>" + azel + "</div></div>"
            var starrect = new fabric.Rect({
               fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(230,100,200,.25)', left: x-5, top: y-5,
                    width: 10,
                    height: 10 ,
                    selectable: false
               });
               canvas.add(starrect);


         }
      out_html = out_html + "</div>"
      document.getElementById('info_panel').innerHTML = out_html 
         


      });
}

function pin_point_from_last(current_frame,orig_file,cal_params_file) {
   var objects = canvas.getObjects('circle')
   for (let i in objects) {
      var x = objects[i].left + 5
      var y = objects[i].top + 5
      console.log("points " + x + " " + y)
      pin_point(x,y,current_frame,orig_file,cal_params_file)
   }

}

function show_frame_image(frame_num,img_base,action,orig_file,cal_params_file) {
   frame_base = img_base 
   if (current_frame == 0) {
      current_frame = frame_num
   }
   else {
      frame_num = current_frame
   }

   if (action == "next") {
      frame_num = parseInt(frame_num) + 1
   }
   if (action == "prev") {
      frame_num = parseInt(frame_num) - 1
   }
   current_frame = frame_num

   var img1 = img_base + "frames" + ("00000" + frame_num).slice(-5) + ".png"
       
   canvas.setBackgroundImage(img1, canvas.renderAll.bind(canvas));
   pin_point_from_last(frame_num,orig_file,cal_params_file)

}
