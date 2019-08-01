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


// Create modal to select meteor from full frame
function create_meteor_selector_from_frame(frame_id, image_src) {
    var cursor_dim = 50;            // Cursor dimension
    var prev_W = 1280;              // Full view
    var prev_H = 720;
    var transp_val = 15;            // Transparency of white area
    var preview_dim = 300;          // Only squares for preview
    var cursor_border_width  = 1; 
    var sel_x = 1280/2-cursor_dim/2;
    var sel_y = 720/2-cursor_dim/2;

    //loading({text: "Creating frame picker", overlay:true});

    // Create Modal
    $('<div class="modal fade" id="cropper_modal" tabindex="-1">\
        <div class="modal-dialog modal-lg" style="max-width:1350px">\
        <div class="modal-content">\
            <div class="modal-header">\
            <h5 class="modal-title" id="modalLabel">Frame #'+  frame_id + ' cropper</h5>\
            <div class="alert alert-info ml-4 p-1 pr-3 pl-3 mb-0">Move the white square to the meteor location</div>\
            <button type="button" class="close" data-dismiss="modal" aria-label="Close">\
                <span aria-hidden="true">×</span>\
            </button>\
            </div>\
            <div class="modal-body">\
            <div id="main_view" style="background-color:#000;background-image:url('+image_src+'); width:'+prev_W+'px; height:'+prev_H+'px; margin: 0 auto; position:relative">\
                <div id="dl"></div><div id="dt"></div><div id="dr"></div><div id="db"></div>\
                <div id="selector" style="width:'+cursor_dim+'px; height:'+cursor_dim+'px; border:'+cursor_border_width+'px solid #fff;"></div>\
                 <div id="select_f_tools">\
                    <div class="drag-h d-flex justify-content-between  pt-1">\
                        <div><small>Preview</small></div>\
                        <div><small>X:<span id="pos_x"></span> / Y:<span id="pos_y"></span></small></div>\
                    </div>\
                    <div class="p-1">\
                    <div id="select_preview" style="width:'+preview_dim+'px; height:'+preview_dim+'px"></div>\
                    <div><input type="range" value="'+transp_val+'" id="transp" min="0"  max="60" ></div>\
                    </div>\
                </div>\
            </div>\
            </div>\
            <div class="modal-footer">\
            <img id="tmp_img_ld" hidden src="'+image_src+'"/>\
            <button type="button" class="btn btn-primary" id="create_frame">Create Frame</button>\
            <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>\
            </div>\
        </div>\
        </div>\
    </div>').appendTo('body');

   
     
    // Mask
    $('#dl,#dr,#dt,#db').css({background:"rgba(255,255,255,."+transp_val+")","position":"absolute"}); 

    // Selector Default Location
    $('#selector').css({top:prev_H/2-cursor_dim/2,left:prev_W/2-cursor_dim/2 });

    // Update Mask position
    update_mask_position(prev_H/2-cursor_dim/2,prev_W/2-cursor_dim/2,prev_W,prev_H,cursor_dim)
  
    // Show Modal
    $('#cropper_modal').modal('show'); 
    loading_done();   
    
    //$("#tmp_img_ld").ready(function() { 
        
        // Setup Preview
        var w_preview_dim = $('#select_preview').innerWidth()/2;
        var h_preview_dim = $('#select_preview').innerHeight()/2;
        var h_canvas_w = $('#main_view').innerWidth()/2;
        var h_canvas_h = $('#main_view').innerHeight()/2;
        
        var xRatio =  w_preview_dim / h_canvas_w;
        var yRatio =  h_preview_dim / h_canvas_h;
        
        var zoom = 8;
     
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

                    
                    sel_x = left;
                    sel_y = top;


                    // Update X/Y
                    $('#pos_x').text(sel_x);
                    $('#pos_y').text(sel_y);

    
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
        $('#select_f_tools').css({"bottom":'2rem',"right":'2rem','position':'absolute'});
        $( "#select_f_tools" ).draggable(
            { handle: ".drag-h", 
              containment: "parent",
            drag:function(e,u) {  
                $(this).css('position','relative');

            },
            start: function( event, ui ) {
                $(this).css('opacity',0.3);
            },
            stop: function( event, ui ) {
                $(this).css('opacity',1);
            }
            }
        );

     
    
    //})

     
    
     
    // Create frame
    $('#create_frame').click(function() {

        loading({'text':'Creating frame #' + frame_id,'overlay':true}); 

        // Create cropped frame
        $.ajax({ 
            url:  "/pycgi/webUI.py",
            data: {
                cmd: 'crop_frame',
                fr_id: frame_id,
                src: image_src,
                sd_video_file: sd_video_file,
                x: parseFloat(sel_x),
                y: parseFloat(sel_y)
            }, 
            success: function(data) {
                data = JSON.parse(data); 
                if(typeof data.error !== undefined ) {
                    loading_done();

                    // Remove modal
                    $('#cropper_modal').modal('hide').remove();


                    // Everything went fine
                    update_star_and_reduction(function() {
                        $('#fr_'+frame_id+' .select_meteor').click();
                    });
                    

                } else {
                    loading_done();
                    bootbox.alert({
                        message: "The process returned an error:<br/>"+ data.error,
                        className: 'rubberBand animated error',
                        centerVertical: true 
                    });
                }
            }
        });
    });
      

}



// Get a frame based on #
function get_frame(cur_fn) {
    var cmd_data = {
		cmd: 'get_frame',
        sd_video_file: sd_video_file, // Defined on the page
        fr: cur_fn
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

}