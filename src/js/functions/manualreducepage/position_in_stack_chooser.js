// Create  select meteor position from stack
function create_meteor_selector_from_frame(image_src) {
   var cursor_dim = 50;            // Cursor dimension
   
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

   $('<h2>Manual Reduction Step 1</h2><p>Select the first and last point of the visible path of the meteor.</p></p><div id="main_view" style="background-color:#000;background-image:url('+image_src+'); width:'+prev_W+'px; height:'+prev_H+'px; margin: 0 auto; position:relative; background-size: contain;">\
                <div id="dl"></div><div id="dt"></div><div id="dr"></div><div id="db"></div>\
                <div id="selector" style="width:'+cursor_dim+'px; height:'+cursor_dim+'px; border:'+cursor_border_width+'px solid #fff;"></div>\
                 <div id="select_f_tools">\
                    <div class="drag-h d-flex justify-content-between  pt-1">\
                        <div><small>Preview</small></div>\
                        <div class="pr-2"><small>X:<span id="pos_x"></span> / Y:<span id="pos_y"></span></small></div>\
                    </div>\
                </div>\
   </div>').appendTo($('#step1'));
}
