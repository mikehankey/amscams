function init_load(cfile) {
   update_hd_cal_ajax(cfile)
}

function update_hd_cal_ajax(cfile) {
   ajax_url = "/pycgi/webUI.py?cmd=update_hd_cal_ajax&cfile=" + cfile 
   console.log(ajax_url)
   remove_objects()
   $.get(ajax_url, function(data) {
      $(".result").html(data);
      var json_resp = $.parseJSON(data);
      cat_stars = json_resp['cat_image_stars']
      total_res_px = json_resp['total_res_px']
      total_res_deg = json_resp['total_res_deg']
      total_res_px = json_resp['total_res_px']
      total_res_deg = json_resp['total_res_deg']
      total_stars = json_resp['total_stars']

            // ADD TEXT TO IMAGE
            //total_res_deg total_res_px cat_stars.length
            res_desc = "Residual Star Error: " + Math.round(total_res_deg * 100) / 100 + " degrees / " + Math.round(total_res_px *100) / 100 + " pixels"
            //res_desc = "Residual Star Error: " + total_res_deg  + " degrees / " + Math.round(total_res_px *100) / 100 + " pixels"
            var text_p = new fabric.Text(res_desc , {
               fontFamily: 'Arial',
               fontSize: 10,
               left: 5 ,
               top: 5
            });
           text_p.setColor('rgba(255,255,255,.75)')
           canvas.add(text_p)

           star_desc = "Total Stars :" + cat_stars.length
           var text_p = new fabric.Text(star_desc, {
              fontFamily: 'Arial',
              fontSize: 10,
              left: 5 ,
              top: 20
           });
           text_p.setColor('rgba(255,255,255,.75)')
           canvas.add(text_p)


      for (let s in cat_stars) {
         cx = cat_stars[s][13] - 11
         cy = cat_stars[s][14] - 11
         var circle = new fabric.Circle({
            radius: 5, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(100,200,200,.5)', left: cx/2, top: cy/2,
            selectable: false
         });
         canvas.add(circle);
      }
      cnt = 0
      out_html = ""
      for (let s in cat_stars) {
         cx = cat_stars[s][11] - 11
         cy = cat_stars[s][12] - 11
         icx = cat_stars[s][7] - 11
         icy = cat_stars[s][8] - 11

         name = cat_stars[s][0]

         out_html = out_html + " <div class='divTableRow'><div class='divTableCell'>" + cat_stars[s][0] + "</div><div class='divTableCell'>" + cat_stars[s][1] + "</div>"
         out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][2] * 100) / 100 + "/" + Math.round(cat_stars[s][3] * 100) / 100 + "</div>"
         out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][4] * 100) / 100 + "/" + Math.round(cat_stars[s][5] * 100) / 100+ "</div>"
         out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][6] * 100) / 100 + "</div>"
         out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][11] * 100) / 100 + "/" + Math.round(cat_stars[s][12] * 100) / 100 + "</div>"
         out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][13] * 100) / 100 + "/" + Math.round(cat_stars[s][14] * 100) / 100 + "</div>"
         out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][7] * 100) / 100 + "/" + Math.round(cat_stars[s][8] * 100) / 100 + "</div>"
         out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][15] * 100)/ 100 + "</div></div>"

         var text_p = new fabric.Text("+", {
            fontFamily: 'Arial',
            fontSize: 12,
            left: (icx/2)+2,
            top: (icy/2)-2
         });
         text_p.setColor('rgba(255,0,0,.75)')
         canvas.add(text_p)

         var text = new fabric.Text(name, {
            fontFamily: 'Arial',
            fontSize: 12,
            left: cx/2,
            top: cy/2+5
         });
         text.setColor('rgba(255,255,255,.25)')
         canvas.add(text)

         var starrect = new fabric.Rect({
            fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(230,100,200,.5)', left: cx/2, top: cy/2,
            width: 10,
            height: 10 ,
            selectable: false
         });
         canvas.add(starrect);
         cnt = cnt + 1
     }

   });


}


function update_red_info_ajax(video_file) {
         ajax_url = "/pycgi/webUI.py?cmd=update_red_info_ajax&video_file=" + video_file
         console.log(ajax_url)
         remove_objects()
         $.get(ajax_url, function(data) {
            $(".result").html(data);
            var json_resp = $.parseJSON(data);
            var cnt = 0
            cat_stars = json_resp['cat_image_stars']
            total_res_px = json_resp['total_res_px']
            total_res_deg = json_resp['total_res_deg']
            crop_box = json_resp['crop_box']
            status = json_resp['status']
            if (status == 1) {
            smf = json_resp['meteor_frame_data']
            box_x = crop_box[0] / 2
            box_y = crop_box[1] / 2
            box_w = (crop_box[2] - crop_box[0]) / 2
            box_h = (crop_box[3] - crop_box[1]) / 2
            cal_params_file = json_resp['cal_params_file']
            stml = ""
            rtml = ""
            out_html = ""
            lc= 0
            // CROP BOX
            var cropb = new fabric.Rect({
                  fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(128,128,128,.5)', left: box_x, top: box_y,
                  width: box_w,
                  height: box_h,
                  selectable: false
               });
            canvas.add(cropb);

            // ADD TEXT TO IMAGE
            //total_res_deg total_res_px cat_stars.length
            res_desc = "Residual Star Error: " + Math.round(total_res_deg * 100) / 100 + " degrees / " + Math.round(total_res_px *100) / 100 + " pixels"
            var text_p = new fabric.Text(res_desc , {
               fontFamily: 'Arial',
               fontSize: 10,
               left: 5 ,
               top: 5
            });
           text_p.setColor('rgba(255,255,255,.75)')
           canvas.add(text_p)
           if (typeof cat_stars != 'undefined') {
              star_desc = "Total Stars :" + cat_stars.length
              var text_p = new fabric.Text(star_desc, {
                 fontFamily: 'Arial',
                 fontSize: 10,
                 left: 5 ,
                 top: 20
              });
              text_p.setColor('rgba(255,255,255,.75)')
              canvas.add(text_p)
           }




            // REDUCTION FRAMES
            for (let s in smf) {
              //((meteor_frame_time_str,fn,int(x),int(y),int(w),int(h),int(max_px),float(ra),float(dec),float(az),float(el)))
              if (lc == 0) {
                 start_y = smf[s][3];
              }
              text_y = (start_y/2) - (lc * 12);

               ft = smf[s][0] ;
               fn = smf[s][1] ;
               x = smf[s][2] / 2 ;
               y = smf[s][3] / 2;
               w = smf[s][4] ;
               h = smf[s][5] ;
               max_px = smf[s][6] ;
               ra = smf[s][7] ;
               dec = smf[s][8] ;
               az = smf[s][9] ;
               el = smf[s][10] ;
               if (w > h) {
                  rad = 6;
               }
               else {
                  rad = 6;

               }
               fr_id = "fr_row" + fn;
               meteor_json_file = ""
               prefix = ""
               del_frame_link = "<a href=javascript:del_frame('" + fn + "','" + meteor_json_file +"')>X</a> ";
               cmp_img_url = prefix + fn + ".png";
               cmp_img = "<img src=" + cmp_img_url + ">";
               rtml = rtml + " <div class='divTableRow' id='" + fr_id + "'><div class='divTableCell'>" + cmp_img + "</div><div class='divTableCell'>" + fn + "</div><div class='divTableCell'>" + ft + "</div>";
               rtml = rtml + " <div class='divTableCell'>" + x + "/" + y + " - " + w + "/" + h + "</div>";
               rtml = rtml + " <div class='divTableCell'>" + max_px + "</div>";
               rtml = rtml + " <div class='divTableCell'>" + ra + "/" + dec + "</div>";
               rtml = rtml + " <div class='divTableCell'>" + az + "/" + el+ "</div>";
               rtml = rtml + " <div class='divTableCell'>" + del_frame_link + "</div></div>";

               var starrect = new fabric.Rect({
                  fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(230,100,200,.5)', left: x-rad, top: y-rad,
                  width: 10,
                  height: 10 ,
                  selectable: false
               });
               canvas.add(starrect);
               /*
               var circle = new fabric.Circle({
                   radius: rad, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(255,255,255,.5)', left: x-rad, top: y-rad,
                   selectable: false
               });
               canvas.add(circle);
               */
               /*
               az_desc = lc + " -  " + az + " / " + el
               var text_p = new fabric.Text(az_desc, {
                  fontFamily: 'Arial',
                  fontSize: 10,
                  left: (x)+25,
                  top: text_y+25
               });
               text_p.setColor('rgba(255,255,255,.75)')
               canvas.add(text_p)
               */
               lc += 1;
          }




             for (let s in cat_stars) {
                cx = cat_stars[s][13] - 11
                cy = cat_stars[s][14] - 11

                var circle = new fabric.Circle({
                   radius: 5, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(100,200,200,.5)', left: cx/2, top: cy/2,
                   selectable: false
                });
                canvas.add(circle);
             }


            for (let s in cat_stars) {
               cx = cat_stars[s][11] - 11
               cy = cat_stars[s][12] - 11
               icx = cat_stars[s][7] - 11
               icy = cat_stars[s][8] - 11

               name = cat_stars[s][0]

               out_html = out_html + " <div class='divTableRow'><div class='divTableCell'>" + cat_stars[s][0] + "</div><div class='divTableCell'>" + cat_stars[s][1] + "</div>"
               out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][2] * 100) / 100 + "/" + Math.round(cat_stars[s][3] * 100) / 100 + "</div>"
               out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][4] * 100) / 100 + "/" + Math.round(cat_stars[s][5] * 100) / 100+ "</div>"
               out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][6] * 100) / 100 + "</div>"
               out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][11] * 100) / 100 + "/" + Math.round(cat_stars[s][12] * 100) / 100 + "</div>"
               out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][13] * 100) / 100 + "/" + Math.round(cat_stars[s][14] * 100) / 100 + "</div>"
               out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][7] * 100) / 100 + "/" + Math.round(cat_stars[s][8] * 100) / 100 + "</div>"
               out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][15] * 100)/ 100 + "</div></div>"

               var text_p = new fabric.Text("+", {
                  fontFamily: 'Arial',
                  fontSize: 12,
                  left: (icx/2)+2,
                  top: (icy/2)-2
               });
               text_p.setColor('rgba(255,0,0,.75)')
               canvas.add(text_p)

               var text = new fabric.Text(name, {
                  fontFamily: 'Arial',
                  fontSize: 12,
                  left: cx/2,
                  top: cy/2+5
               });
               text.setColor('rgba(255,255,255,.25)')
               canvas.add(text)

               var starrect = new fabric.Rect({
                  fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(230,100,200,.5)', left: cx/2, top: cy/2,
                  width: 10,
                  height: 10 ,
                  selectable: false
               });
               canvas.add(starrect);
               cnt = cnt + 1
           }
   } // end status if
        });

}








function custom_fit(meteor_json_file, hd_video_file, cal_params_file) {
    new_cp_file = meteor_json_file.replace(".mp4", "-calparams.json")
    ajax_url = "/pycgi/webUI.py?cmd=custom_fit&cal_params_file=" + new_cp_file 
    console.log(ajax_url)
    $.get(ajax_url, function(data) {
       var json_resp = $.parseJSON(data);
       //var auto_stars = json_resp['stars']
       console.log("Running custom fit. Please wait 1 minute then show catalog stars again to check.")
    });
 }



 function find_stars(stack_file) {
    var ajax_url = "/pycgi/webUI.py?cmd=find_stars_ajax&stack_file=" + stack_file;
    console.log(ajax_url)  ;
    $.get(ajax_url, function(data) {
       $(".result").html(data);
       var json_resp = $.parseJSON(data);
       var auto_stars = json_resp['stars'];
       console.log(auto_stars);
       lc = 0;
       $.each(auto_stars,function(s,v) {
            x = auto_stars[s][0] / 2 ;
            y = auto_stars[s][1] / 2;
            var circle = new fabric.Circle({
            radius: 5, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(255,255,255,.5)', left: x-5, top: y-5,
            selectable: false
            });
            canvas.add(circle);
       })
 


    });
 }


    function del_frame(fn, meteor_json_file) {
       ajax_url = "/pycgi/webUI.py?cmd=del_frame&meteor_json_file=" + meteor_json_file + "&fn=" + fn 
       fr_id = "fr_" + fn
       //alert(fr_id)
       document.getElementById(fr_id).remove()
       console.log(ajax_url)
       $.get(ajax_url, function(data) {
          $(".result").html(data);
          var json_resp = $.parseJSON(data);
          alert(json_resp['message'])
       });
    }

    function reduce_meteor_ajax(meteor_json_file,cal_params_file) {
       ajax_url = "/pycgi/webUI.py?cmd=reduce_meteor_ajax&meteor_json_file=" + meteor_json_file + "&cal_params_file=" + cal_params_file;
       console.log(ajax_url);
       $.get(ajax_url, function(data) {
          $(".result").html(data);
          var json_resp = $.parseJSON(data);
          console.log(json_resp['sd_meteor_frame_data']);
          var smf = json_resp['sd_meteor_frame_data'];
          var prefix = json_resp['prefix'];
          console.log(prefix);

           //((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist))
          out_html = "<div class='divTable' style='border: 1px solid #000;' ><div class='divTableBody'>";
          out_html = out_html + " <div class='divTableRow'><div class='divTableCell'>IMG</div><div class='divTableCell'>FN</div><div class='divTableCell'>Frame Time</div><div class='divTableCell'>X/Y - W/H</div><div class='divTableCell'>Max PX</div><div class='divTableCell'>RA/DEC</div><div class='divTableCell'>AZ/EL</div><div class='divTableCell'>Del</div></div>";

          lc = 0
          for (let s in smf) {
              //((meteor_frame_time_str,fn,int(x),int(y),int(w),int(h),int(max_px),float(ra),float(dec),float(az),float(el)))
              if (lc == 0) {
                 start_y = smf[s][3];
              }
              text_y = (start_y/2) - (lc * 12);

               ft = smf[s][0] ;
               fn = smf[s][1] ;
               x = smf[s][2] / 2 ;
               y = smf[s][3] / 2;
               w = smf[s][4] ;
               h = smf[s][5] ;
               max_px = smf[s][6] ;
               ra = smf[s][7] ;
               dec = smf[s][8] ;
               az = smf[s][9] ;
               el = smf[s][10] ;
               if (w > h) {
                  rad = 6;
               }
               else {
                  rad = 6;

               }
               fr_id = "fr_row" + fn;
               del_frame_link = "<a href=javascript:del_frame('" + fn + "','" + meteor_json_file +"')>X</a> ";
               cmp_img_url = prefix + fn + ".png";
               cmp_img = "<img src=" + cmp_img_url + ">";
               out_html = out_html + " <div class='divTableRow' id='" + fr_id + "'><div class='divTableCell'>" + cmp_img + "</div><div class='divTableCell'>" + fn + "</div><div class='divTableCell'>" + ft + "</div>";
               out_html = out_html + " <div class='divTableCell'>" + x + "/" + y + " - " + w + "/" + h + "</div>";
               out_html = out_html + " <div class='divTableCell'>" + max_px + "</div>";
               out_html = out_html + " <div class='divTableCell'>" + ra + "/" + dec + "</div>";
               out_html = out_html + " <div class='divTableCell'>" + az + "/" + el+ "</div>";
               out_html = out_html + " <div class='divTableCell'>" + del_frame_link + "</div></div>";

               var starrect = new fabric.Rect({
                  fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(230,100,200,.5)', left: x-rad, top: y-rad,
                  width: 10,
                  height: 10 ,
                  selectable: false
               });
               canvas.add(starrect);
               /*
               var circle = new fabric.Circle({
                   radius: rad, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(255,255,255,.5)', left: x-rad, top: y-rad,
                   selectable: false
               });
               canvas.add(circle);
               */
               /* 
               az_desc = lc + " -  " + az + " / " + el
               var text_p = new fabric.Text(az_desc, {
                  fontFamily: 'Arial', 
                  fontSize: 10, 
                  left: (x)+25,
                  top: text_y+25
               });
               text_p.setColor('rgba(255,255,255,.75)')
               canvas.add(text_p)
               */
               lc += 1;
          }



          document.getElementById('meteor_frame_list').innerHTML = out_html.toString() ;
          sleep(1000).then(() => {
             var img1 = document.getElementById('half_stack_file')
             img1.src = json_resp['reduce_img_file']

             var canvas = document.getElementById("c");
             var cntx= canvas.getContext("2d"); 
             //cntx.drawImage(img1, 0, 0);


          });
       });

    }





    function sleep (time) {
       return new Promise((resolve) => setTimeout(resolve, time));
    }

    function solve_field(hd_stack_file) {
       check_solve_status(1)
    }



    function check_fit_status(json_resp) {
       if (json_resp['status'] == 'done') {
          rusure = confirm("Click ok to run the fit again.")
          if (rusure == true) {
             ajax_url = "/pycgi/webUI.py?cmd=fit_field&override=1&hd_stack_file=" + hd_stack_file
             console.log(ajax_url)
             $.get(ajax_url, function(data) {
                $(".result").html(data);
                var json_resp = $.parseJSON(data);
                alert(json_resp['message'])
                document.getElementById('star_panel').innerHTML = json_resp['message']
                //sleep(5000).then(() => {
                   //alert("time to wake up!")
                   //check_fit_status(json_resp)
                   //});
             });
           }
       }
       else {
          alert(json_resp['message'])
       }
    }

    function add_to_fit_pool() {
       ajax_url = "/pycgi/webUI.py?cmd=save_add_stars_to_fit_pool&hd_stack_file=" + hd_stack_file
       //alert(ajax_url)
       $.get(ajax_url, function(data) {
          $(".result").html(data);
          var json_resp = $.parseJSON(data);
          alert(json_resp['message'])
       });

    }

    function delete_cal() {

       rusure = confirm("Click ok to delete job or cancel.")
       if (rusure == true) {

          ajax_url = "/pycgi/webUI.py?cmd=delete_cal&hd_stack_file=" + hd_stack_file
          //alert(ajax_url)
          $.get(ajax_url, function(data) {
             $(".result").html(data);
             var json_resp = $.parseJSON(data);
             alert("job files deleted")
             //alert(json_resp['debug'])
          });
       }
 

    }
    function fit_field() {
       ajax_url = "/pycgi/webUI.py?cmd=fit_field&hd_stack_file=" + hd_stack_file
       console.log(ajax_url)
       $.get(ajax_url, function(data) {
          $(".result").html(data);
          var json_resp = $.parseJSON(data);
          alert(json_resp['message'])
          document.getElementById('star_panel').innerHTML = json_resp['message']
          sleep(5000).then(() => {
             //alert("time to wake up!")
             check_fit_status(json_resp)
          });
       });

    }

    function send_ajax_solve() {
       ajax_url = "/pycgi/webUI.py?cmd=solve_field&hd_stack_file=" + hd_stack_file
       $.get(ajax_url, function(data) {
          $(".result").html(data);
          var json_resp = $.parseJSON(data);
          sleep(5000).then(() => {
             check_solve_status(0)
          });
       });
    }



    function show_cat_stars(video_file, stack_file, cal_params_file, type) {
       var point_str = ""
          for (i in user_stars) {
             point_str = point_str + user_stars[i].toString()  + "|"
          }

          var point_str = ""
          var objects = canvas.getObjects('circle')
          for (let i in objects) {
             x = objects[i].left
             y = objects[i].top
             rad = objects[i].get('radius')
             if (objects[i].get('type') == "circle" && rad == 5) {
                point_str = point_str + x.toString() + "," + y.toString() + "|"
             }
          }
       if (type != "nopick") {
       }
       
       ajax_url = "/pycgi/webUI.py?cmd=show_cat_stars&type=" + type + "&video_file=" + video_file + "&hd_stack_file=" + hd_stack_file + "&points=" + point_str + "&cal_params_file=" + cal_params_file
       console.log(ajax_url)
       if (type != "first_load") {
          remove_objects() 
       }
       $.get(ajax_url, function(data) {
          $(".result").html(data);
          var json_resp = $.parseJSON(data);
          var cnt = 0
          cat_stars = json_resp['close_stars']
          total_res_px = json_resp['total_res_px']
          total_res_deg = json_resp['total_res_deg']
          crop_box = json_resp['crop_box']
          box_x = crop_box[0] / 2
          box_y = crop_box[1] / 2
          box_w = (crop_box[2] - crop_box[0]) / 2 
          box_h = (crop_box[3] - crop_box[1]) / 2
          cal_params_file = json_resp['cal_params_file']
          console.log(cal_params_file)

       var roi_rect = new fabric.Rect({
          fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(230,230,230,.2)',  left: box_x, top: box_y,
          width: box_w,
          height: box_h ,
          selectable: false
       });
       canvas.add(roi_rect);




          sleep(1000).then(() => {

             out_html = "Residual error : " + Math.round(total_res_deg * 100) / 100 + " degrees / " + Math.round(total_res_px *100) / 100 + " pixels"
             out_html = out_html + "<div class='divTable' style='border: 1px solid #000;' ><div class='divTableBody'>"
             out_html = out_html + " <div class='divTableRow'><div class='divTableCell'>Star</div><div class='divTableCell'>Mag</div><div class='divTableCell'>Cat RA/DEC</div><div class='divTableCell'>Img RA/DEC</div><div class='divTableCell'>Residual (Degrees)</div><div class='divTableCell'>Cat X,Y</div><div class='divTableCell'>Img X,Y,</div><div class='divTableCell'>Corrected Img X,Y,</div><div class='divTableCell'>Residual Pixels</div></div>"
             var user_stars = json_resp['user_stars'];

             for (let s in cat_stars) {
                cx = cat_stars[s][13] - 11 
                cy = cat_stars[s][14] - 11 

                var circle = new fabric.Circle({
                   radius: 5, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(100,200,200,.5)', left: cx/2, top: cy/2,
                   selectable: false
                });
                canvas.add(circle);
             }

             for (let s in cat_stars) {
               cx = cat_stars[s][11] - 11
               cy = cat_stars[s][12] - 11
               icx = cat_stars[s][7] - 11
               icy = cat_stars[s][8] - 11

               name = cat_stars[s][0]
               if (cnt < 5) {
               }
              //((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist))

               out_html = out_html + " <div class='divTableRow'><div class='divTableCell'>" + cat_stars[s][0] + "</div><div class='divTableCell'>" + cat_stars[s][1] + "</div>"
               out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][2] * 100) / 100 + "/" + Math.round(cat_stars[s][3] * 100) / 100 + "</div>"
               out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][4] * 100) / 100 + "/" + Math.round(cat_stars[s][5] * 100) / 100+ "</div>"
               out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][6] * 100) / 100 + "</div>"
               out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][11] * 100) / 100 + "/" + Math.round(cat_stars[s][12] * 100) / 100 + "</div>"
               out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][13] * 100) / 100 + "/" + Math.round(cat_stars[s][14] * 100) / 100 + "</div>"
               out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][7] * 100) / 100 + "/" + Math.round(cat_stars[s][8] * 100) / 100 + "</div>"
               out_html = out_html + " <div class='divTableCell'>" + Math.round(cat_stars[s][15] * 100)/ 100 + "</div></div>"




               var text_p = new fabric.Text("+", {
                  fontFamily: 'Arial', 
                  fontSize: 12, 
                  left: (icx/2)+2,
                  top: (icy/2)-2
               });
               text_p.setColor('rgba(255,0,0,.75)')
               canvas.add(text_p)

               var text = new fabric.Text(name, {
                  fontFamily: 'Arial', 
                  fontSize: 12, 
                  left: cx/2,
                  top: cy/2+5
               });
               text.setColor('rgba(255,255,255,.25)')
               canvas.add(text)

            
               var starrect = new fabric.Rect({
                  fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(230,100,200,.5)', left: cx/2, top: cy/2,
                  width: 10,
                  height: 10 ,
                  selectable: false
               });
               canvas.add(starrect);
               cnt = cnt + 1

          } 

          // ADD TEXT TO IMAGE
       //total_res_deg total_res_px cat_stars.length
       res_desc = "Residual Star Error: " + Math.round(total_res_deg * 100) / 100 + " degrees / " + Math.round(total_res_px *100) / 100 + " pixels"
       var text_p = new fabric.Text(res_desc , {
          fontFamily: 'Arial',
          fontSize: 10,
          left: 5 ,
          top: 5
       });
       text_p.setColor('rgba(255,255,255,.75)')
       canvas.add(text_p)

       star_desc = "Total Stars :" + cat_stars.length
       var text_p = new fabric.Text(star_desc, {
          fontFamily: 'Arial',
          fontSize: 10,
          left: 5 ,
          top: 20
       });
       text_p.setColor('rgba(255,255,255,.75)')
       canvas.add(text_p)


          out_html = out_html + "</div></div>"
          //document.getElementById('star_list').innerHTML = out_html.toString() ;
       if (type != "first_load") {
       }

          });
       });


    }

    function check_solve_status(then_run) {
       ajax_url = "/pycgi/webUI.py?cmd=check_solve_status&hd_stack_file=" + hd_stack_file
       waiting = true
       $.get(ajax_url, function(data) {
          $(".result").html(data);
          var json_resp = $.parseJSON(data);
          waiting = false

          document.getElementById('star_panel').innerHTML = json_resp['status']

          if (json_resp['status'] == 'new' && then_run == 1) {
             rusure = confirm("Click OK to run Astrometry.net plate solve on selected stars.")
             if (rusure == true) { 
                send_ajax_solve()
             }
          }

          if (json_resp['status'] == 'failed' && then_run == 1) {
             rusure = confirm("This job already ran and failed. Click OK to re-run.")
             if (rusure == true) { 
                send_ajax_solve()
             }
          }
          if (json_resp['status'] == 'running' && then_run == 0) {
             document.getElementById('star_panel').innerHTML = "Plate solve is running..."

             sleep(5000).then(() => {
                check_fit_status(json_resp)
             });

          }
          if (json_resp['status'] == 'success' && then_run == 0) {
             alert("Astrometry.net successfully solved the plate.")
             document.getElementById('star_panel').innerHTML = "Astrometry.net successfully solved the plate."

             sleep(1000).then(() => {
                grid_img = json_resp['grid_file'];
                canvas.setBackgroundImage(grid_img, canvas.renderAll.bind(canvas));
             });
          }
          if (json_resp['status'] == 'success' && then_run == 1) {
             grid_img = json_resp['grid_file']
             alert("Astrometry.net successfully solved the plate.")
             document.getElementById('star_panel').innerHTML = "Astrometry.net successfully solved the plate."
             canvas.setBackgroundImage(grid_img, canvas.renderAll.bind(canvas));
             //alert(json_resp['debug'])
          }
          if (json_resp['status'] == 'failed' && then_run == 0) {
             alert("Astrometry.net failed to solved the plate.")
             document.getElementById('star_panel').innerHTML = "Astrometry.net failed to solved the plate."
             //alert(json_resp['solved_file'])
             alert("failed")
          }
       });
    }

    function upscale_HD(img_url) {
       var point_str = ""
       for (i in user_stars) {
          point_str = point_str + user_stars[i].toString()  + "|"
       }

       var point_str = ""
       var objects = canvas.getObjects('circle')
       for (let i in objects) {
          x = objects[i].left
          y = objects[i].top
          if (objects[i].get('type') == "circle") {
          point_str = point_str + x.toString() + "," + y.toString() + "|"
          }
       }

       ajax_url = "/pycgi/webUI.py?cmd=upscale_2HD&hd_stack_file=" + hd_stack_file + "&points=" + point_str
       console.log(ajax_url)
       $.get(ajax_url, function(data) {
          $(".result").html(data);
          var json_resp = $.parseJSON(data);
          var new_img = json_resp['hd_stack_file'] 
          var new_url = "webUI.py?cmd=free_cal&input_file=" + new_img
          alert("Upscale Complete!")
          window.location.replace(new_url);

       });
    }

    function az_grid(az_grid_file) {
          canvas.setBackgroundImage(az_grid_file, canvas.renderAll.bind(canvas));
    }


    function show_image(orig_image, scaleX,scaleY) {
       if (scaleX == undefined) {
           scaleX = 1;
           scaleY = 1;
       }

       canvas.setBackgroundImage(orig_image, canvas.renderAll.bind(canvas), {
       scaleX: scaleX,
       scaleY: scaleY

       });


    }






    function add_to_fit(img_url) {
       var point_str = ""
       for (i in user_stars) {
          point_str = point_str + user_stars[i].toString()  + "|"
       }

       var point_str = ""
       var objects = canvas.getObjects('circle')
       for (let i in objects) {
          x = objects[i].left
          y = objects[i].top
          if (objects[i].get('type') == "circle") {
          point_str = point_str + x.toString() + "," + y.toString() + "|"
          }
       }

       ajax_url = "/pycgi/webUI.py?cmd=save_add_stars_to_fit_pool&hd_stack_file=" + hd_stack_file + "&points=" + point_str
       console.log(ajax_url)



    }

    function remove_objects() {
       var objects = canvas.getObjects()
       for (let i in objects) {
          canvas.remove(objects[i]);
       }
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
          if (objects[i].get('type') == "circle") {
          point_str = point_str + x.toString() + "," + y.toString() + "|"
          }
       }

       ajax_url = "/pycgi/webUI.py?cmd=make_plate_from_points&hd_stack_file=" + hd_stack_file + "&points=" + point_str
       console.log(ajax_url)
       $.get(ajax_url, function(data) {
          $(".result").html(data);
          var json_resp = $.parseJSON(data);
          //alert(json_resp['half_stack_file_an'])
          var new_img = json_resp['half_stack_file_an'] + "?r=" + Math.random().toString()
          document.getElementById('c').width=960
          document.getElementById('c').height=540
          document.getElementById('c').style.width=960
          document.getElementById('c').style.height=540
          new_img.height=960
          new_img.width=540
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

          //alert(stars)
          canvas.setBackgroundImage(new_img, canvas.renderAll.bind(canvas));
          // remove existing objects & replace with pin pointed stars
          for (let i in objects) {
             canvas.remove(objects[i]);
          }


          //alert(json_resp.error)
          //alert(data)
       });


    }
