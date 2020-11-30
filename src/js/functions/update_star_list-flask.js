function update_stars_on_canvas_and_table(cp, crop_box) {

   console.log("IN update_stars_on_canvas_and_table")
   var table_tbody_html = '';
   cat_stars = cp['cat_image_stars']
   console.log(cat_stars)
  
    // Draw New Box
   if(typeof crop_box !== 'undefined') {
        canvas.add(
            new fabric.Rect({
                fill: 'rgba(0,0,0,0)', 
                strokeWidth: 1, 
                stroke: 'rgba(230,230,230,.2)',  
                left: crop_box[0] / 2, 
                top: crop_box[1] / 2,
                width: (crop_box[2] - crop_box[0]) / 2,
                height: (crop_box[3] - crop_box[1]) / 2,
                selectable: false
             })
        );
    }
   
    if(typeof cp['total_res_deg']!=='undefined' && typeof cp['total_res_px']!=='undefined') {
        // Updating star table info 
        // Residual Error
        var total_res_deg = (Math.round(cp['total_res_deg'] * 100) / 100);
        var total_res_px = (Math.round(cp['total_res_px'] *100) / 100);
        $('#star_res_p').remove();

        // Add same text to image 
        if(typeof cat_stars !== 'undefined') { 
            res_desc = "Res. Star Error: " + total_res_deg + "° / " + total_res_px + " px";
            $('<p id="star_res_p" class="mt-2"><b>Residual Error:</b> '+  total_res_deg + '&deg; / ' + total_res_px + 'px.</p>').insertBefore('#stars-tab table');
            canvas.add(new fabric.Text(res_desc , {
                fontFamily: 'Arial',
                fontSize: 12,
                left: 5,
                top: 518,
                fill: 'rgba(255,255,255,.75)',
                selectable: false
            })); 
            $('#str_cnt').text(cat_stars.length);
        }
    }

    // Table - tbody (in #stars-tab) & draw on canvas
    
    $.each(cat_stars,function(i,v) {

        // Add to circle canvas
        canvas.add(
            new fabric.Circle({
                radius: 5, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(100,200,200,.5)', 
                left: (v[13] - 11)/2, 
                top: (v[14] - 11)/2,
                selectable: false,
                gp_id: v[0]
        }));

        // Add "+" on canvas
        canvas.add(
            new fabric.Text("+", {
                fontFamily: 'Arial', 
                fontSize: 12, 
                left: ((v[7] - 11)/2)+4,   // +4 = shift text
                top: ((v[8] - 11)/2) -4,    // -4 = shift text
                fill:'rgba(255,0,0,.75)',
                selectable: false ,
                gp_id: v[0]
        }));

        // Add Star Name on canvas
        canvas.add(new fabric.Text(v[0], {
                fontFamily: 'Arial', 
                fontSize: 12, 
                left: (v[11] - 11)/2+5,
                top: (v[12] - 11)/2+8,
                fill:'rgba(255,255,255,.45)',
                selectable: false,
                gp_id: v[0] 
        }));

        // Add Rectangle
        canvas.add(new fabric.Rect({
            fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(230,100,200,.5)', 
            left:  (v[11] - 11)/2, 
            top:(v[12] - 11)/2,
            width: 10,
            height: 10 ,
            selectable: false,
            gp_id: v[0] 
         }));

        // Add the corresponding row
        // Name	mag	Cat RA/Dec	Res °	Res. Pixels 
        table_tbody_html+= '<tr><td>'+v[0]+'</td><td>'+v[1]+'</td><td>'+v[2]+'/'+v[3]+'</td><td>'+v[6]+'</td><td>'+v[15]+'</td></tr>';

    });

    // Replace current table content
    $('#stars-tab tbody').html(table_tbody_html);

    // Remove star counter message & beforeunload
    $('#star_counter').text('');
    $(window).unbind('beforeunload');
    stars_added = 0;
    stars_removed = 0;
}


function update_star_list() {
   console.log("IN update_star_list")
        //cal_params_file:  $('#cal_param_selected').val(),   // The one selected 
        //type: typeof type !== 'undefined' ? type : 'nopick', // 'nopick' is the default option
    var cmd_data = {
        video_file:          main_vid,          // Defined on the page
        hd_stack_file:       hd_stack_file,     // Defined on the page
        cmd: 'show_cat_stars',                 
        points: ''
    }
 
    // Get user stars from array
    // cmd_data.points = user_stars.join("|")+"|";

    // Get Stars from canvas
    var canvas_stars = canvas.getObjects('circle');
    $.each(canvas_stars, function(i,v) {
        if (v.get('type') == "circle" && v.get('radius') == 5) {
            cmd_data.points= cmd_data.points + v.left.toString() + "," + v.top.toString() + "|";
         }
    }); 

    //loading({text:'Updating star list...', overlay:true});

    console.log("IN update_star_list remove previous objs")
    // Remove All objects from Canvas but the reduction squares
    var objects = canvas.getObjects()
    for (let i in objects) {
        if(objects[i].type!=='reduc_rect') {
            canvas.remove(objects[i]);
        }
    }
    console.log("IN update_star_list call ajax")
    $.ajax({ 
        url:  "/API/show_cat_stars",
        data: cmd_data,
        success: function(data) {
            //var json_resp = $.parseJSON(data);
            console.log("IN update_star_list response ", data)
            update_stars_on_canvas_and_table(data['cp'], data['crop_box']);
            //if(data['status']!==0) {
                //update_stars_on_canvas_and_table(json_resp['cat_image_stars'], json_resp['crop_box']);
                // Open proper tab
                //$('#stars-tab-l').click();
             //   loading_done();
            //}  
            //else {
            //    alert("error update stars on canvas status = 0!")
            //    loading_done();
            //}
        },
        error: function(data) {
           console.log("ERROR") 
           //loading_done();
        }
    });
   console.log("DONE UPDATE") 
}



$(function () {

    // Click on button
    $('#update_stars').click(function() {
        update_star_list();
    });

});
