// Update selector position and corresponding data
function update_select_preview(top,left,margins,W_factor,H_factor,cursor_dim) {
   $("#selector").css({
      left: top - cursor_dim/2,
      top: left - cursor_dim/2
   });
 
}


// Create  select meteor position from stack
function create_meteor_selector_from_stack(image_src) {
   var cursor_dim = 24;            // Cursor dimension
   var margins = 12;                // Max position (x,y) of the meteor inside the cursor

   var real_W = 1920;
   var real_H = 1080;

   var prev_W = 1075;              // Preview
   var prev_H = 605;
   
   var transp_val = 15;            // Transparency of white area
   var preview_dim = 300;          // Only squares for preview
   var cursor_border_width  = 1; 
   
   var sel_x = prev_W/2-cursor_dim/2;
   var sel_y = prev_H/2-cursor_dim/2;

   var W_factor = real_W/prev_W;
   var H_factor = real_H/prev_H; 

   var cur_step_start = true;
 

   $('<h1>Manual Reduction Step 1</h1>\
     <div class="box"><div class="alert alert-info mb-3 p-1 pr-1 pl-2">Select the STARTING point of the meteor path.</div>\
     <div id="draggable_area" style="width:'+(prev_W+margins*2) + 'px; height:' +( prev_H+margins*2) + 'px;margin:0 auto;">\
     <div id="main_view" style="background-color:#000;background-image:url('+image_src+'); width:'+prev_W+'px; height:'+prev_H+'px; margin: 0 auto; position:relative; background-size: contain;">\
      <div id="selector" style="position:absolute;width:'+cursor_dim+'px; height:'+cursor_dim+'px; border:'+cursor_border_width+'px solid green;"></div>\
   </div><p class="mt-2 mb-0"><span id="pos_x"></span> <span id="pos_y"></span></p></div>').appendTo($('#step1'));
   
   // Mask
   $('#dl,#dr,#dt,#db').css({background:"rgba(255,255,255,."+transp_val+")","position":"absolute"}); 

   // Selector Default Location (center)
   $('#selector').css({top:prev_H/2-cursor_dim/2,left:prev_W/2-cursor_dim/2 });
   $('#pos_x').text("x: " + parseInt((prev_W/2-cursor_dim/2)*W_factor));
   $('#pos_y').text("y: " + parseInt((prev_H/2-cursor_dim/2)*H_factor));  

   // Update Mask position
   update_mask_position(prev_H/2-cursor_dim/2,prev_W/2-cursor_dim/2,prev_W,prev_H,cursor_dim)

   offset = $('#main_view').offset();

   // Move on click
   $('#main_view').click(function(e) {

      var top =  e.pageY - offset.top;
      var left = e.pageX - offset.left;
      update_select_preview(top,left,margins,W_factor,H_factor,cursor_dim);

      
   });
   

}
