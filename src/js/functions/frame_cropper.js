    
       var image_src = '/mnt/ams2/TMP/2019_03_06_06_47_25_000_010038-trim0072_23.png';
       var cursor_dim = 50; 
       /*
       $('<div class="modal fade" id="cropper_modal" tabindex="-1">\
       <div class="modal-dialog modal-lg" style="max-width:1300px">\
         <div class="modal-content">\
           <div class="modal-header">\
             <h5 class="modal-title" id="modalLabel">Frame cropper</h5>\
             <button type="button" class="close" data-dismiss="modal" aria-label="Close">\
               <span aria-hidden="true">×</span>\
             </button>\
           </div>\
           <div class="modal-body">\
              <p>Select the area of the meteor location</p>\
              <div>\
                <div id="selector" style="width:50px; height:50px; border:2px solid #fff"></div>\
                <img id="frame_to_crop" src="'+image_src+'" alt="Select the area of the meteor" class="img-fluid" >\
              </div>\
           </div>\
           <div class="modal-footer">\
             <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>\
           </div>\
         </div>\
       </div>\
     </div>').appendTo('body');

     $('#cropper_modal').modal('show'); 
    */
    
   var image_src = '/mnt/ams2/TMP/2019_03_06_06_47_25_000_010038-trim0072_23.png';
   var cursor_dim = 50; 

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
           <p>Move the white square to the meteor location</p>\
           <div style="background-image:url('+image_src+'); width:1280px; height:720px; margin: 0 auto; position:relative">\
             <div id="dl"></div><div id="dt"></div><div id="dr"></div><div id="db"></div>\
             <div id="selector" style="width:'+cursor_dim+'px; height:'+cursor_dim+'px; border:1px solid #fff; top:50%; left:50%"></div>\
           </div>\
        </div>\
        <div class="modal-footer">\
          <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>\
        </div>\
      </div>\
    </div>\
  </div>').appendTo('body');



  $('#dl,#dr,#dt,#db').css({background:"rgba(255,255,255,.3)","position":"absolute"});

  $('#cropper_modal').modal('show'); 
  $( "#selector" ).draggable(
    { containment: "parent",
      drag:function(e,u) { 
        var top = u.position.top;
        var left = u.position.left;

        $('#dl').css({
          'top':0,
          'left':0,
          'width': left,
          'height': '720px',
        });


        $('#dr').css({
          'top':0,
          'left':left,
          'width': left,
          'height': '720px',
        })
      }
    });
 
  



  // ZOOM
  // Hide/Show zoom when necessary
  $('.canvas-container canvas').mouseenter(function(){ 
    out_timer = setTimeout(function() { $('.canvas_zoom_holder').slideDown(300);},350);
  }).mouseleave(function() { 
    clearTimeout(out_timer);
    out_timer = setTimeout(function() {
      $('.canvas_zoom_holder').slideUp(300); 
      $('#canvas_zoom').css('background-position','50% 50%');
    }, 350); 
  }); 

  canvas.on('mouse:move', function(e) { 
      var pointer = canvas.getPointer(event.e);
      var $zoom   = $('#canvas_zoom');
      var x_val = pointer.x | 0;
      var y_val = pointer.y | 0;

      x_val = x_val*zoom/2-w_preview_dim;
      y_val = y_val*zoom/2-h_preview_dim;
    
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
      //$('#canvas_pointer_info').text(x_val +', '+ y_val); 
      $('#canvas_pointer_info').text(Math.round(pointer.x) +', '+ Math.round(pointer.y)); 
  }); 
  
