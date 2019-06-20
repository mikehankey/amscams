function select_meteor_ajax(fn,x,y) {
    var cmd_data = {
		cmd: 'update_frame_ajax',
        sd_video_file: sd_video_file, // Defined on the page
        fn: fn,
        new_x: x/2,
        new_y: y/2 
    };

    loading({text:"Updating the frame", overlay:true});

    $.ajax({ 
        url:  "/pycgi/webUI.py",
        data: cmd_data, 
        success: function(data) {
            var nf = data.new_frame; 
            var new_row = "";
            var t = nf.frame_time;
            t = t.split(' ');
            t = t[1];
            loading_done(); 

            var hd_x = nf.hd_x;
            hd_x = hd_x/2;

            var hd_y = nf.hd_y;
            hd_y = hd_y/2;

            // Build new table row
            new_row += '<tr id="fn_'+fn+'" data-org-x="'+x+'" data-org-y="'+y+'"><td><img src="'+nf.cnt_thumb+'" width="50" height="50" class="img-fluid select_meteor"/></td>';
            new_row += '<td>'+fn+'</td>';
            new_row += '<td>'+t+'</td>';
            new_row += '<td>'+nf.ra.tofixed(2) + "&deg/" + nf.dec.tofixed(2) +'&deg</td>';
            new_row += '<td>'+nf.az.tofixed(2) + "&deg/" + nf.el.tofixed(2) +'&deg</td>';
            new_row += '<td>'+hd_x.tofixed(2) + "/" + hd_y.tofixed(2) +'</td>';
            new_row += '<td>'+nf.w.tofixed(2) + "x" + nf.h.tofixed(2) +'</td>';
            new_row += '<td>'+nf.max_px +'</td>';
            new_row += '<td><a class="btn btn-danger btn-sm delete_frame"><i class="icon-delete"></i></a></td>';
            new_row += '<td class="position-relative"><a class="btn btn-success btn-sm select_meteor"><i class="icon-target"></i></a><a title="Add a frame" class="btn btn-primary btn-sm btn-mm add_f" data-rel="4"><i class="icon-plus"></i></a></td>';
            $('tr#fn_'+fn).replaceWidth($(new_row));

            loading_done();
            
        }, 
        error:function() {
            loading_done();

            bootbox.alert({
                message: "The process returned an error",
                className: 'rubberBand animated error',
                centerVertical: true 
            });
        }
    });
}


// Select a meteor (next/prev)
function meteor_select(dir,all_frames_ids) {
    var next_id;
    var cur_id = parseInt($('#sel_frame_id').text());
    var cur_index = all_frames_ids.indexOf(cur_id);
      
    if(dir=="prev") {
        if(cur_index==0) {
            next_id = all_frames_ids.length-1;
        } else {
            next_id = cur_index - 1;
        }
    } else {
        if(cur_index==all_frames_ids.length-1) {
            next_id = 0;
        } else {
            next_id = cur_index + 1;
        }
    } 

    // Open the next or previous one
    $('#reduc-tab table tbody tr#fr_' + all_frames_ids[next_id] + " .select_meteor").click();
}


// Modal for selector
function addModalTemplate() {
    if($('#select_meteor_modal').length==0) {
        $('<div id="select_meteor_modal" class="modal fade" tabindex="-1"><input type="hidden" name="thumb_w"/><input type="hidden" name="thumb_h"/><div class="modal-dialog  modal-lg modal-dialog-centered" role="document"><div class="modal-content"><div class="modal-body"><button id="met-sel-next" title="Next" type="button" class="mfp-arrow mfp-arrow-right mfp-prevent-close"></button><button id="met-sel-prev" title="Prev" type="button" class="mfp-arrow mfp-arrow-left mfp-prevent-close"></button><p><strong>FRAME #<span id="sel_frame_id"></span> - Click the center of the meteor.</strong> <span id="meteor_org_pos" class="float-right pl-3"><b>Org:</b></span> <span id="meteor_pos" class="float-right"></span></p><div style="box-shadow: 0 0px 8px rgba(0,0,0,.6);" class="meteor_chooser"><div id="org_lh"></div><div id="org_lv"></div><div id="lh"></div><div id="lv"></div></div></div><div class="modal-footer p-0 pb-2 pr-2"><button type="button" class="btn btn-primary" id="Save Meteor Center">Save</button><button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button></div></div></div></div>').appendTo('body');
    }
}

// Actions on modal 
function setup_modal_actions(fn_id,x,y) {
    
    // Warning: preview  = 500x500
    //    thumb real dim = 50x50
    var thumb_prev = 500;
    var thumb_dim  = 50;
    var factor = 500/50;

    x = parseInt(x);
    y = parseInt(y);

    // Update Info
    $('#meteor_org_pos').html('<b>Org:</b> '+x+'/'+y);
    $('#meteor_pos').text(x+'/'+y);

    $(".meteor_chooser").unbind('click').click(function(e){
        var parentOffset = $(this).offset(); 
        var relX = parseFloat(e.pageX - parentOffset.left);
        var relY = parseFloat(e.pageY - parentOffset.top);

        //WARNING ONLY WORKS WITH SQUARES
        var realX = relX/factor+x-thumb_dim/2;
        var realY = relY/factor+y-thumb_dim/2;

        // Transform values
        if(!$(this).hasClass('done')) {
            $(this).addClass('done');
        } else {
            $('#lh').css('top',relY);
            $('#lv').css('left',relX);
            $('#meteor_pos').text(parseInt(realX)+'/'+parseInt(realY));
        }

        select_meteor_ajax(fn_id,realX,realY);
 
    }).unbind('mousemove').mousemove(function(e) {
        
        var parentOffset = $(this).offset(); 
        var relX = e.pageX - parentOffset.left;
        var relY = e.pageY - parentOffset.top;

        //WARNING ONLY WORKS WITH SQUARES
        var realX = relX/factor+x-thumb_dim/2;
        var realY = relY/factor+y-thumb_dim/2;

        // Cross
        if(!$(this).hasClass('done')) {
            $('#lh').css('top',relY);
            $('#lv').css('left',relX);
            $('#meteor_pos').text(parseInt(realX)+'/'+parseInt(realY));
        }
    });
}


function setup_select_meteor() {
    var viewer_dim = 500;
    var all_frames_ids = [];

    // Get all the frame ids
    $('#reduc-tab table tbody tr').each(function() {
        var id = $(this).attr('id');
        id = id.split('_');
        all_frames_ids.push(parseInt(id[1]));
    });

    // Click on selector (button & thumb)
    $('.select_meteor').click(function() {
        var $tr = $(this).closest('tr');

        // Get meteor id
        var meteor_id = $tr.attr('id');
        meteor_id = meteor_id.split('_')[1];
      
        // Get Image
        var $img = $tr.find('img'); 

        var real_width, real_height;

        // Add template if necessary
        addModalTemplate();

        // Prev Button
        $('#met-sel-prev').unbind('click').click(function() {
            meteor_select("prev",all_frames_ids);
        });

        // Next Button
        $('#met-sel-next').unbind('click').click(function() {
            meteor_select("next",all_frames_ids);
        });

        // Add image 
        $('.meteor_chooser').css('background-image','url('+$img.attr('src')+')');

        // Add current ID
        $('#sel_frame_id').text(meteor_id);
  
        // Update image real dimensions 
        var img = new Image();
        var imgSrc = $img.attr('src');

        $(img).on('load',function () {
            real_width = img.width;
            real_height = img.height;
            $('input[name=thumb_w]').val(real_width);
            $('input[name=thumb_h]').val(real_height); 
            // garbage collect img
            delete img;

            // Redefine viewer depending on the thumb dimension
            if(real_width !== real_height) {
            
                if(real_width > real_height) {
                    $('.meteor_chooser').css('height',  real_height/real_width * viewer_dim);
                } else {
                    $('.meteor_chooser').css('width', real_width/real_height * viewer_dim);
                }

            } else {
                $('.meteor_chooser').css({'height': viewer_dim + 'px', 'width':viewer_dim + 'px'});
            }
             
            // Reset Cross position
            $('#lh').css('top','50%');
            $('#lv').css('left','50%');
            
            // Open Modal
            $('#select_meteor_modal').modal('show');
    
            // Reset
            $(".meteor_chooser").removeClass('done');

            setup_modal_actions(meteor_id, $tr.attr('data-org-x'),$tr.attr('data-org-y'));
        
        }).attr({ src: imgSrc }); 

        

    });
}

 