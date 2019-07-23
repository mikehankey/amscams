function select_meteor_ajax(fn,x,y) {
    var cmd_data = {
		cmd: 'update_frame_ajax',
        sd_video_file: sd_video_file, // Defined on the page
        fn: fn,
        new_x: x,
        new_y: y 
    };

    loading({text:"Updating the frame", overlay:true});

    $.ajax({ 
        url:  "/pycgi/webUI.py",
        data: cmd_data, 
        success: function(data) {
            
            if($.trim(data)!='') { 

                update_reduction_only();
               
                loading_done();
    
                bootbox.alert({
                    message: "The frame as well as the corresponding reduction table row have been updated.",
                    className: 'rubberBand animated',
                    centerVertical: true 
                });
            } else {
                loading_done();
    
                bootbox.alert({
                    message: "Something went wrong: please contact us.",
                    className: 'rubberBand animated error',
                    centerVertical: true 
                });
            }

            
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
function addModalTemplate(meteor_id,neighbor) {
    var c; 
    if($('#select_meteor_modal').length==0) {

        c = '<div id="select_meteor_modal" class="modal fade" tabindex="-1">\
        <input type="hidden" name="thumb_w"/><input type="hidden" name="thumb_h"/>\
        <div class="modal-dialog  modal-lg modal-dialog-centered" role="document">\
        <div class="modal-content">\
        <div class="modal-header"><div style="width:100%"><strong>FRAME #<span class="sel_frame_id"></span> - Click the center of the meteor.</strong> \
        <span id="meteor_org_pos" class="float-right pl-3"><b>Org:</b></span> \
        <span id="meteor_pos" class="float-right"></span></div></div>\
        <div class="modal-body"><button id="met-sel-next" title="Next" type="button" class="mfp-arrow mfp-arrow-right mfp-prevent-close"></button>\
        <button id="met-sel-prev" title="Prev" type="button" class="mfp-arrow mfp-arrow-left mfp-prevent-close"></button>\
        <div class="d-flex justify-content-center" id="nav_prev">\
        </div><div style="box-shadow: 0 0px 8px rgba(0,0,0,.6);" class="meteor_chooser">\
        <div id="org_lh"></div><div id="org_lv"></div><div id="lh"></div><div id="lv"></div></div></div>\
        <div class="text-center pt-2"><a class="btn btn-danger delete_frame_from_modal"><i class="icon-delete"></i> Delete the frame#<span class="sel_frame_id"></span></a></div>\
        <div class="modal-footer p-0 pb-2 pr-2"><button type="button" hidden>Save</button>\
        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button></div></div></div></div>';
 
        $(c).appendTo('body');
    }  
 
    // We update the preview
    $('#nav_prev').html('');
    $.each(neighbor, function(i,v)  {
        if(v.id==meteor_id) {
            _class = 'prev-th cur';
        } else {
            _class = 'prev-th ';
        } 
        $('<div><img src="'+v.img+'" id="'+v.id+'" style="border-color:'+v.color+';" class="'+_class+'" ></div>').appendTo($('#nav_prev'));
    });


    
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


function get_neighbor_frames(cur_id) {
    // Get the thumbs & colors or -5 +5 frames
    // IN #nav_prev
    var all_thb = []; 
    cur_id = parseInt(cur_id)
    for(var i = cur_id-3; i < cur_id+4; i++) {
        var $cur_tr = $('#fr_'+i);
        var img =  $cur_tr.find('img').attr('src');
        var color = $cur_tr.find('.st').css('background-color');
        var id = i;

        if(typeof img == "undefined"){
            img = './dist/img/no-sm.png';
            id = 0;
        }

        if(typeof color == "undefined"){
            color = 'rgb(15,15,15)';
        } 

        all_thb.push({
            img: img,
            color:color,
            id:id
        });
    }

    return all_thb;

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

        // Get Color
        var color = $tr.find('.st').css('background-color');

        var real_width, real_height;

        // Get Neightbors
        var neighbor = get_neighbor_frames(meteor_id); 
        // Add template if necessary
        addModalTemplate(meteor_id,neighbor);

        // Prev Button
        $('#met-sel-prev').unbind('click').click(function() {
            meteor_select("prev",all_frames_ids);
        });

        // Next Button
        $('#met-sel-next').unbind('click').click(function() {
            meteor_select("next",all_frames_ids);
        });

        // Add image 
        $('.meteor_chooser').css('background-image','url('+$img.attr('src')+')').css('border','2px solid ' + color);

        // Add current ID
        $('.sel_frame_id').text(meteor_id);
  
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

 