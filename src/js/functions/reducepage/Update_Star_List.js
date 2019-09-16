// FOR THE POS IN THE JSON
// Ex:  "i_pos": [719,769], => x= 719, y=769
POS_X = 0
POS_Y = 1


function update_stars_on_canvas_and_table(json_resp) {

    
 
   var cat_stars = json_resp['calib']['stars']; 

   if(typeof cat_stars == 'undefined') {
      return;
   }

    var table_tbody_html = '';
 
    if(typeof json_resp['calib']['device']['total_res_deg']!=='undefined' && typeof json_resp['calib']['device']['total_res_px']!=='undefined') {
        // Updating star table info 
        // Residual Error
        var total_res_deg = (Math.round( json_resp['calib']['device']['total_res_deg'] * 100) / 100);
        var total_res_px = (Math.round( json_resp['calib']['device']['total_res_px'] *100) / 100);
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
                left: (v["i_pos"][POS_X] - 11)/2, 
                top: (v["i_pos"][POS_Y] - 11)/2,
                selectable: false,
                gp_id: v[0]
        }));

        // Add "+" on canvas
        canvas.add(
            new fabric.Text("+", {
                fontFamily: 'Arial', 
                fontSize: 12, 
                left: ((v["cat_dist_pos"][POS_X] - 11)/2)+4,   // +4 = shift text
                top: ((v["cat_dist_pos"][POS_Y] - 11)/2) -4,    // -4 = shift text
                fill:'rgba(255,0,0,.75)',
                selectable: false ,
                gp_id: v[0]
        }));

        // Add Star Name on canvas
        canvas.add(new fabric.Text(v['name'], {
                fontFamily: 'Arial', 
                fontSize: 12, 
                left: (v['cat_und_pos'][POS_X] - 11)/2+5,
                top: (v['cat_und_pos'][POS_Y] - 11)/2+8,
                fill:'rgba(255,255,255,.45)',
                selectable: false,
                gp_id: v[0] 
        }));

        // Add Rectangle
        canvas.add(new fabric.Rect({
            fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(230,100,200,.5)', 
            left:  (v['cat_und_pos'][POS_X] - 11)/2, 
            top: (v['cat_und_pos'][POS_Y]  - 11)/2,
            width: 10,
            height: 10 ,
            selectable: false,
            gp_id: v[0] 
         }));

        // Add the corresponding row
        // Name	mag	Cat RA/Dec	Res °	Res. Pixels 
        table_tbody_html+= '<tr><td>'+v['name']+'</td>\
                            <td>'+v['mag']+'</td>\
                            <td>'+v['ra'].toFixed(4) +'&deg; / '+v['dec'].toFixed(4)+'&deg;</td>\
                            <td>'+v['dist_px'].toFixed(4)+'</td>\
                            <td>'+v['cat_dist_pos'][X].toFixed(4)+'</td><td>'+v['cat_dist_pos'][Y].toFixed(4)+'</td>\
                            <td>'+v['cat_und_pos'][X].toFixed(4)+'</td><td>'+v['cat_und_pos'][Y].toFixed(4)+'</td>\
                            </tr>';

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
    var cmd_data = {
        video_file:          main_vid,          // Defined on the page
        hd_stack_file:       hd_stack_file,     // Defined on the page
        cmd: 'show_cat_stars',                 
        cal_params_file:  $('#cal_param_selected').val(),   // The one selected 
        type: typeof type !== 'undefined' ? type : 'nopick', // 'nopick' is the default option
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

    loading({text:'Updating star list...', overlay:true});

    // Remove All objects from Canvas but the reduction squares
    var objects = canvas.getObjects()
    for (let i in objects) {
        if(objects[i].type!=='reduc_rect') {
            canvas.remove(objects[i]);
        }
    }
 
    $.ajax({ 
        url:  "/pycgi/webUI.py",
        data: cmd_data,
        success: function(data) {
            var json_resp = $.parseJSON(data);
            if(json_resp['status']!==0) {
                update_stars_on_canvas_and_table(json_resp);

                // Open proper tab
                $('#stars-tab-l').click();
                
                loading_done();
            }  
 
        } 
    });
 
}



$(function () {

    // Click on button
    $('#update_stars').click(function() {
        update_star_list();
    });

});
