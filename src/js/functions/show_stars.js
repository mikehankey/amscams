function show_cat_stars(type) {
   var cmd_data = {
        video_file: main_vid,
        hd_stack_file: hd_stack_file,
        cmd: show_cat_stars,
        cal_params_file:  $('#cal_param_selected').val(),
        type: typeof type !== 'undefined' ? type : 'nopick'
   }
 
    // Get user stars from array
    cmd_data.point_str = user_stars.join("|");

    // Get Stars from canvas???
    var canvas_stars = canvas.getObjects('circle');
    $.each(canvas_stars, function(i,v) {
        if (objects[i].get('type') == "circle" && objects[i].get('radius') == 5) {
            cmd_data.point_str= cmd_data.point_str + objects[i].left.toString() + "," + objects[i].top.toString() + "|";
         }
    }); 

    $.ajax({ 
        url:  "/pycgi/webUI.py",
        data: cmd_data,  
        success: function(data) {
            var json_resp = $.parseJSON(data);
            var cnt = 0
            cat_stars       = json_resp['close_stars']
            total_res_px    = json_resp['total_res_px']
            total_res_deg   = json_resp['total_res_deg']
            crop_box        = json_resp['crop_box']
            box_x = crop_box[0] / 2
            box_y = crop_box[1] / 2
            box_w = (crop_box[2] - crop_box[0]) / 2 
            box_h = (crop_box[3] - crop_box[1]) / 2
            cal_params_file = json_resp['cal_params_file']
            console.log(cal_params_file)
        } 
    });


    if (type != "first_load") {
       remove_objects();
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
       document.getElementById('star_list').innerHTML = out_html.toString() ;
    if (type != "first_load") {
    }

       });
    });


 }