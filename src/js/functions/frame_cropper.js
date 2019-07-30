   var image_src = '/mnt/ams2/TMP/2019_03_06_06_47_25_000_010038-trim0072_23.png';
   var cursor_dim = 50;
   var cursor_border_width = 1; 
   var prev_W = 1280;
   var prev_H = 720;
   var transp_val = 15; // Transparency of white area
   var preview_dim = 300; // Only squares!!


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


   $('#cropper_modal').remove();

    $('<div class="modal fade" id="cropper_modal" tabindex="-1">\
    <div class="modal-dialog modal-lg" style="max-width:1350px">\
      <div class="modal-content">\
        <div class="modal-header">\
          <h5 class="modal-title" id="modalLabel">Frame cropper</h5>\
          <button type="button" class="close" data-dismiss="modal" aria-label="Close">\
            <span aria-hidden="true">×</span>\
          </button>\
        </div>\
        <div class="modal-body">\
          <div class="d-flex justify-content-between">\
            <p>Move the white square to the meteor location</p>\
          </div>\
           <div id="main_view" style="background-image:url('+image_src+'); width:'+prev_W+'px; height:'+prev_H+'px; margin: 0 auto; position:relative">\
             <div id="dl"></div><div id="dt"></div><div id="dr"></div><div id="db"></div>\
             <div id="selector" style="width:'+cursor_dim+'px; height:'+cursor_dim+'px; border:'+cursor_border_width+'px solid #fff;"></div>\
           </div>\
           <div id="select_f_tools" style="width:350px">\
              <div class="drag-h" style="height:20px; background:grey"></div>\
              <div style="padding:1rem">\
              <div>Mask Transparency  <input type="range" value="'+transp_val+'" id="transp" min="0"  max="60" ></div>\
              <div id="select_preview" style="width:'+preview_dim+'px; height:'+preview_dim+'px"></div>\
              </div>\
           </div>\
        </div>\
        <div class="modal-footer">\
          <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>\
        </div>\
      </div>\
    </div>\
  </div>').appendTo('body');



  $('#dl,#dr,#dt,#db').css({background:"rgba(255,255,255,."+transp_val+")","position":"absolute"}); 
  $('#selector').css({top:prev_H/2-cursor_dim/2,left:prev_W/2-cursor_dim/2 });

  // Update Mask position
  update_mask_position(prev_H/2-cursor_dim/2,prev_W/2-cursor_dim/2,prev_W,prev_H,cursor_dim)

  $('#cropper_modal').modal('show'); 


 

  var w_preview_dim = $('#select_preview').innerWidth()/2;
  var h_preview_dim = $('#select_preview').innerHeight()/2;
  var h_canvas_w = $('#main_view').innerWidth()/2;
  var h_canvas_h = $('#main_view').innerHeight()/2;
  
  var xRatio =  w_preview_dim / h_canvas_w;
  var yRatio =  h_preview_dim / h_canvas_h;
  
  var zoom = 4;

   // PREVIEW SETUP
   $('#select_preview').css({
    'background': 'url('+image_src+') 50% 50% #000 no-repeat',
    'background-size': h_canvas_w*zoom + 'px ' + h_canvas_h*zoom + 'px'
  });

  

  // Move the Selector
  $( "#selector" ).draggable(
    { containment: "parent",
      drag:function(e,u) {  

        var top = u.position.top;
        var left = u.position.left;
        var $zoom =  $('#select_preview');

        // Mask
        update_mask_position(top,left,prev_W,prev_H,cursor_dim);

        // Preview Center
        top = top + cursor_dim/2;
        left = left + cursor_dim/2;
       
        var y_val = top*zoom/2-w_preview_dim;
        var x_val = left*zoom/2-h_preview_dim;
      
        if(x_val<0) {
          if(y_val<0) {
            $zoom.css('background-position',Math.abs(x_val)  + 'px ' + Math.abs(y_val) + 'px');
          } else {
            $zoom.css('background-position', Math.abs(x_val)  + 'px -' + y_val  + 'px');
          }
        } else if(y_val<0) {
            $zoom.css('background-position','-' +  x_val  + 'px ' + Math.abs(y_val)  + 'px');
        } else {
          
            $zoom.css('background-position', '-'+x_val  + 'px -' + y_val  + 'px');
        }
    }
  });
 
  
  // Change Transparency
    $('#transp').on('input', function () { 
      var val = parseInt($(this).val());
      $('#dl,#dr,#dt,#db').css({background:"rgba(255,255,255,"+val/100+")"});
    });


  // Drag tools
  $( "#select_f_tools" ).draggable({ handle: ".drag-h", containment: "parent" });  

  

  
 