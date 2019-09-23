var HAVE_START = false;
var HAVE_END = false;

// Update selector position and corresponding data
function update_select_preview(top,left,margins,W_factor,H_factor,cursor_dim, cur_step_start,cursor_border_width,show_pos) {
   
   // Move Selector
   $("#selector").css({
      top: top - cursor_dim/2,
      left: left - cursor_dim/2
   });

   sel_x = Math.floor(left)+margins - cursor_dim/2;
   sel_y = Math.floor(top)+margins - cursor_dim/2;

   if(show_pos) {
      cur_step_start = !cur_step_start

      if(cur_step_start) {
         // Update START X/Y
         $('#res .start').html('<b style="color:green">START</b> x:' + Math.floor(sel_x*W_factor)+ 'px ' + 'y:'+  Math.floor(sel_y*H_factor) +'px');
         $('#selector').css('border-color','red');

         // Put the static square on the view
         if($('#sel_start_static').length==0) {
            $('<div id="sel_start_static" style="width:'+cursor_dim+'px; height:'+cursor_dim+'px;position:absolute; border:'+cursor_border_width+'px solid green">').appendTo($('#main_view'));
         }
         
         $('#sel_start_static').css({
            top: top - cursor_dim/2,
            left: left - cursor_dim/2
         });
 
         $('input[name=x_img_start]').val(Math.floor(sel_x*W_factor));
         $('input[name=y_img_start]').val(Math.floor(sel_y*H_factor));
        /* $('input[name=x_start]').val(Math.floor(sel_x*W_factor));
         $('input[name=y_start]').val(Math.floor(sel_y*H_factor));
         */

         HAVE_START = true;
      } else {
         // Update END X/Y
         $('#res .end').html('<b style="color:red">END</b> x:' + Math.floor(sel_x*W_factor)+ 'px ' + 'y:'+  Math.floor(sel_y*H_factor) +'px');
         $('#selector').css('border-color','green');

          // Put the static square on the view
          if($('#sel_end_static').length==0) {
            $('<div id="sel_end_static" style="width:'+cursor_dim+'px; height:'+cursor_dim+'px;position:absolute; border:'+cursor_border_width+'px solid red">').appendTo($('#main_view'));
          }

          $('#sel_end_static').css({
            top: top - cursor_dim/2,
            left: left - cursor_dim/2
         });
        
         $('input[name=x_img_end]').val(Math.floor(sel_x*W_factor));
         $('input[name=y_img_end]').val(Math.floor(sel_y*H_factor));
         /* $('input[name=x_end]').val(Math.floor(sel_x*W_factor));
         $('input[name=y_end]').val(Math.floor(sel_y*H_factor));
         */

         HAVE_END = true;
      } 
   }

   // Enable continue button 
   if(HAVE_END && HAVE_START) {
      $('#step1_btn').removeAttr('disabled').removeClass('disabled');

      // We draw a rectangle 
      /*
      if($('#sel_rectangle_static').length==0) {
         $('<div id="sel_rectangle_static" style="position:absolute; border:1px solid rgba(255,255,255,.6)">').appendTo($('#main_view'));
      }

      $('#sel_rectangle_static').css({
         'top': parseInt($('input[name=x_img_start]').val()),
         'left': parseInt($('input[name=y_img_start]').val()),
         'width':  Math.abs(parseInt($('input[name=x_img_start]').val())  - parseInt($('input[name=x_img_end]').val())) ,
         'height': Math.abs(parseInt($('input[name=y_img_start]').val())  - parseInt($('input[name=y_img_end]').val())) 
      });
      */
   }
   
   return cur_step_start
}


// Create  select meteor position from stack
function create_meteor_selector_from_stack(image_src) {
   var cursor_dim = 24;            // Cursor dimension
   var margins = 12;                // Max position (x,y) of the meteor inside the cursor

   var real_W = 1920;
   var real_H = 1080;

   var prev_W = 1075;              // Preview
   var prev_H = 605;
     
   var cursor_border_width  = 2; 
   
   var sel_x = prev_W/2-cursor_dim/2;
   var sel_y = prev_H/2-cursor_dim/2;

   var W_factor = real_W/prev_W;
   var H_factor = real_H/prev_H; 

   var cur_step_start = false;
 
   var init_top = prev_H/2-cursor_dim/2;
   var init_left = prev_W/2-cursor_dim/2;

 
   $('<h1>Manual Reduction Step 1</h1>\
      <input type="hidden" name="x_start"/><input type="hidden" name="y_start"/>\
      <input type="hidden" name="x_end"/><input type="hidden" name="y_end"/>\
      <input type="hidden" name="x_img_start"/><input type="hidden" name="y_img_start"/>\
      <input type="hidden" name="x_img_end"/><input type="hidden" name="y_img_end"/>\
     <div class="box">\
     <div class="modal-header p-0" style="border:none!important">\
      <div class="alert alert-info mb-3 p-1 pr-1 pl-2">Select the <b style="color:green">STARTING</b> point and the <b style="color:red">ENDING</b> point of the meteor path.</div>\
      <div id="res" class="text-right"><span class="start"></span><br/><span class="end" ></span></div>\
     </div>\
     <div id="draggable_area" style="width:'+(prev_W+margins*2) + 'px; height:' +( prev_H+margins*2) + 'px;margin:0 auto;">\
     <div id="main_view" style="background-color:#000;background-image:url('+image_src+'); width:'+prev_W+'px; height:'+prev_H+'px; margin: 0 auto; position:relative; background-size: contain;">\
      <div id="selector" class="ng pa" style="top:-9999px; left:-9999px;width:'+cursor_dim+'px; height:'+cursor_dim+'px; border:'+cursor_border_width+'px solid green;"></div>\
   </div></div><div class="text-right"><button id="step1_btn" class="btn btn-lg btn-primary disabled" disabled>Continue</button></div>').appendTo($('#step1'));
   
   
   offset = $('#main_view').offset();

   // Move on click
   $('#main_view').click(function(e) {
      var top =  e.pageY - offset.top;
      var left = e.pageX - offset.left;
      cur_step_start = update_select_preview(top,left,margins,W_factor,H_factor,cursor_dim,cur_step_start,cursor_border_width,true);
      e.stopImmediatePropagation();
      return false;
   });
   

   // Go to next step
   $('#step1_btn').click(function() {
      var cmd_data = {
         cmd: 'manual_reduction_cropper',
         stack: stack, // Defined on the page
         json_file: json_file, // Defined on the page

      };
    
      loading({text: "Generating Full Frame #"+ cur_fn, overlay:true});
    
      $.ajax({ 
           url:  "/pycgi/webUI.py",
           data: cmd_data, 
           success: function(data) { 
               loading_done();  
               data = JSON.parse(data); 
               
               // Hide the modal below (it will be reopened anyway)
               $('#select_meteor_modal').modal('hide');
               
               create_meteor_selector_from_frame(data.id,data.full_fr); 
           }, 
           error:function() { 
               bootbox.alert({
                   message: "The process returned an error",
                   className: 'rubberBand animated error',
                   centerVertical: true 
               });
           }
       });
   })

}
