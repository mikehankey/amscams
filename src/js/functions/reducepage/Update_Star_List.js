// FOR THE POS IN THE JSON
// Ex:  "i_pos": [719,769], => x= 719, y=769
POS_X = 0
POS_Y = 1
CIRCLE_RADIUS=5

function update_stars_on_canvas_and_table(json_resp) {
    
   // Add AZ/EL of center camera
   if(typeof json_resp['calib']!== 'undefined' &&
      typeof json_resp['calib']['center'] !== 'undefined' &&
      typeof json_resp['calib']['center']['az'] !== 'undefined' &&
      typeof json_resp['calib']['center']['el'] !== 'undefined'  
   ) { 
      console.log("AZ EL OK");
      canvas.add(new fabric.Text( "Center Az: " + json_resp['calib']['center']['az'] + "° / El:" + json_resp['calib']['center']['el'] + " el" , {
         fontFamily: 'Arial',
         fontSize: 12,
         left: 5,
         top: 505,
         fill: 'rgba(255,255,255,.75)',
         selectable: false
     })); 
   }

   if(typeof json_resp['calib']!== 'undefined' &&  typeof json_resp['calib']['stars'] !== 'undefined') {
      var cat_stars = json_resp['calib']['stars']; 
      var name_pos = []; // Store the name positions
   
      if(typeof cat_stars == 'undefined') {
         return; 
      }
   
       var table_tbody_html = ''; 
   
       //console.log(" json_resp['calib']['device']['total_res_deg'] " +  json_resp['calib']['device']['total_res_deg'])
       //console.log(" json_resp['calib']['device']['total_res_px'] " +  json_resp['calib']['device']['total_res_px'])
    
       if(typeof json_resp['calib']!=='undefined' && typeof json_resp['calib']['device']!=='undefined' && typeof json_resp['calib']['device']['total_res_deg']!=='undefined' && typeof json_resp['calib']['device']['total_res_px']!=='undefined') {
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
           }
       }
   
       $('#str_cnt').text(cat_stars.length);
   
       if(!jQuery.isEmptyObject(cat_stars)) { 
            cat_stars.sort((a,b) => (a.name > b.name) ? 1 : ((b.name > a.name) ? -1 : 0))
       } 
          
   
       // Table - tbody (in #stars-tab) & draw on canvas
       $.each(cat_stars,function(i,v) {
    
            // Add to circle canvas
            circle =  new fabric.Circle({
               radius: CIRCLE_RADIUS, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(100,200,200,.5)', 
               left: (v["i_pos"][POS_X] - 11)/2, 
               top: (v["i_pos"][POS_Y] - 11)/2,
               selectable: false,
               gp_id: v['name'],
               type: 'star_info',
            })
            
            canvas.add(circle); 
   
            // Add Rectangle
            rect = new fabric.Rect({
               fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(230,100,200,.5)', 
               left: ((v["cat_und_pos"][POS_X] - 11)/2),   
               top: ((v["cat_und_pos"][POS_Y] - 11)/2),     
               width: 10,
               height: 10 ,
               selectable: false,
               gp_id: v['name'],
               type: 'star_info', 
            })
            canvas.add(rect);
      
           // Add "+" on canvas
           plus = new fabric.Text("+", {
            fontFamily: 'Arial', 
            fontSize: 12,  
            left:  (v['cat_dist_pos'][POS_X] - 11)/2+4,   // +4 = shift text
            top: (v['cat_dist_pos'][POS_Y]  - 11)/2-4, // -4 = shift text
            fill:'rgba(255,0,0,.75)',
            selectable: false ,
            gp_id: v['name'],
            type: 'star_info',
           })
           
           canvas.add(plus);
   
           name_pos.push(circle);
           name_pos.push(rect);
           name_pos.push(plus);
           
           name_pos_x = (v['i_pos'][POS_X] - 11)/2
           name_pos_y = (v['i_pos'][POS_Y] - 11)/2+17
    
           test_object = new fabric.Text(v['name'],{
              fontFamily: 'Arial', 
              fontSize: 12, 
              top: name_pos_y,
              left: name_pos_x,
              fill:'rgba(255,255,255,.55)',
              selectable: false,
              gp_id: v['name'],
              type: 'star_info',
              ui_type:'text' 
           });
           
            
           // Add Star Name on canvas
           canvas.add(test_object); 
           //name_pos.push(test_object);
   
   
           // Add the corresponding row 
           table_tbody_html+= '<tr><td><b>'+v['name']+'</b></td>\
                               <td>'+v['mag']+'</td>\
                               <td>'+v['ra'].toFixed(2) +'&deg; / '+v['dec'].toFixed(2)+'&deg;</td>\
                               <td>'+v['i_pos'][POS_X].toFixed(2) + ' / '+ v['i_pos'][POS_Y].toFixed(2) + '</td>\
                               <td>'+v['cat_und_pos'][POS_X].toFixed(2)  + ' / '+ v['cat_und_pos'][POS_Y].toFixed(2) +'</td>\
                               <td>'+v['cat_dist_pos'][POS_X].toFixed(2)  + ' / '+ v['cat_dist_pos'][POS_Y].toFixed(2) +'</td>\
                               <td>'+v['dist_px'].toFixed(4)+'</td>\
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

  
}


function update_star_list() {

    var cmd_data = {
        video_file:          main_vid,                         // Defined on the page
        hd_stack_file:       my_image,                         // Defined on the page
        cmd: 'update_cat_stars',                 
        type: typeof type !== 'undefined' ? type : 'nopick',   // 'nopick' is the default option
        points: '',
        json_file: json_file
    }
 
    // Get Stars from canvas
    var canvas_stars = canvas.getObjects();
    $.each(canvas_stars, function(i,v) {
         if (v.radius == CIRCLE_RADIUS) { 
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
            if(json_resp['res']=='true') {

            }
            
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
