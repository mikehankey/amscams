// Mask on selector
function update_mask_position(top,left,prev_W,prev_H,cursor_dim) {
   $('#dl').css({
     'top':0,
     'left':0,
     'width': left,
     'height': prev_H 
   });


   $('#dr').css({
     'top':0,
     'left':left+cursor_dim,
     'width': prev_W-left-cursor_dim,
     'height': prev_H 
   })


   $('#dt').css({
     'top':0,
     'left':left,
     'width': cursor_dim,
     'height':top 
   })


   $('#db').css({
     'top': top + cursor_dim,
     'left':left,
     'width': cursor_dim,
     'height':prev_H-top-cursor_dim 
   })
}

// Create  select meteor position from stack
function create_meteor_selector_from_stack(image_src) {
   var cursor_dim = 25;            // Cursor dimension
   
   var real_W = 1920;
   var real_H = 1080;

   var prev_W = 1280;              // Full view
   var prev_H = 720;
   
   var transp_val = 15;            // Transparency of white area
   var preview_dim = 300;          // Only squares for preview
   var cursor_border_width  = 1; 
   
   var sel_x = prev_W/2-cursor_dim/2;
   var sel_y = prev_H/2-cursor_dim/2;

   var W_factor = real_W/prev_W;
   var H_factor = real_H/prev_H; 

   var cur_step_start = true;
 

   $('<h1>Manual Reduction Step 1</h1>\
     <div class="box"><div class="alert alert-info mb-0 p-1 pr-1 pl-2">Move the white square to the meteor location</div><div id="main_view" style="background-color:#000;background-image:url('+image_src+'); width:'+prev_W+'px; height:'+prev_H+'px; margin: 0 auto; position:relative; background-size: contain;">\
                <div id="dl"></div><div id="dt"></div><div id="dr"></div><div id="db"></div>\
                <div id="selector" style="width:'+cursor_dim+'px; height:'+cursor_dim+'px; border:'+cursor_border_width+'px solid #fff;"></div>\
   </div><div id="pos_x"></div><div id="pos_y"></div></div>').appendTo($('#step1'));
   
   // Mask
   $('#dl,#dr,#dt,#db').css({background:"rgba(255,255,255,."+transp_val+")","position":"absolute"}); 

   // Selector Default Location (center)
   $('#selector').css({top:prev_H/2-cursor_dim/2,left:prev_W/2-cursor_dim/2 });
   $('#pos_x').text(parseInt((prev_W/2-cursor_dim/2)*W_factor));
   $('#pos_y').text(parseInt((prev_H/2-cursor_dim/2)*H_factor));  

   // Update Mask position
   update_mask_position(prev_H/2-cursor_dim/2,prev_W/2-cursor_dim/2,prev_W,prev_H,cursor_dim)

    // Move the Selector
    $( "#selector" ).draggable(
      { containment: "parent",
          drag:function(e,u) {  

              var top = u.position.top;
              var left = u.position.left;
              
              sel_x = left;
              sel_y = top;

              // Update X/Y
              $('#pos_x').text(parseInt(sel_x*W_factor-cursor_dim/2));
              $('#pos_y').text(parseInt(sel_y*H_factor-cursor_dim/2));
 
              // Mask
              update_mask_position(top,left,prev_W,prev_H,cursor_dim);
  
          }
  });
}
