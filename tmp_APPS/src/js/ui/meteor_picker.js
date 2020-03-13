var multiple_select = true;
var meteor_select_updates = [];



function select_multiple_meteors_ajax() {
    var cmd_data = {
        cmd: 'update_multiple_frames_ajax',
        sd_video_file: sd_video_file, // Defined on the page
    };

    meteor_select_updates = jQuery.grep(meteor_select_updates, function(n, i){
        return (n !== "" && n != null);
    });

    cmd_data.frames = JSON.stringify(meteor_select_updates);

    loading({text:"Updating the " + meteor_select_updates.length  + " frames", overlay:true});


    $.ajax({ 
        url:  "/pycgi/webUI.py",
        data: cmd_data, 
        success: function(data) {
            
            if($.trim(data)!='') { 

                update_reduction_only();
                loading_done();

                // Anti cache?
                //console.log('ANTI CACHE on ' + fn)
                $.each(meteor_select_updates,function(i,v) {
                    $('tr#fr_'+i+' img.select_meteor').attr('src', $('tr#fr_'+i+' img.select_meteor').attr('src')+'&w='+Math.round(Math.random(10000)*10000));
                })


                $('.modal-backdrop').remove();
                $('#select_meteor_modal').modal('hide').remove();

                // Reset Selection
                meteor_select_updates = [];
                
          
                  
            } else {
                loading_done();

                 // Reset Selection
    
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


function select_meteor_ajax(fn,x,y) {
    if(!multiple_select) {
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
    
                    // Anti cache?
                    //console.log('ANTI CACHE on ' + fn)
                    $('tr#fr_'+fn+' img.select_meteor').attr('src', $('tr#fr_'+fn+' img.select_meteor').attr('src')+'&w='+Math.round(Math.random(10000)*10000));
                    $('.modal-backdrop').remove();
                    $('#select_meteor_modal').modal('hide').remove();
                    
                    // Reopen the modal at the proper place
                    $('tr#fr_'+fn+' .select_meteor').click();
                      
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
    } else {
        
        // We add the info to meteor_select_updates
        meteor_select_updates[fn] = {
            fn: fn,
            x:parseInt(x),
            y:parseInt(y)
        };

        // Update list 
        update_meteor_info_list(fn);

        // Go to next available
        $('#met-sel-next').click();
      
    }

    
}


function update_meteor_info_list(fn) {

    $('.meteor_thumb_pos_list').html('');
            
    $.each(meteor_select_updates, function(i,v){
        var _class;
        if(v !== undefined) {
            if(fn == i) {
                _class="cur_m_s";
            } else {
                _class="";
            }
            $('<p class="'+_class+'"><strong>Frame #'+i+'</strong> new position: x=' + v.x.toFixed(0) + ', ' + 'y=' + v.y.toFixed(0) +'</p>').appendTo($('.meteor_thumb_pos_list'));
        } 
    });

    // Scroll bottom of list
    var d = $('.meteor_thumb_pos_list');
    d.scrollTop(d.prop("scrollHeight"));
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




 

// GET HELPERS
function get_help_pos(nextprev, org_id) {

    var tr_fn = false;
    org_id = parseInt(org_id);

    if(nextprev == 'next') {
        // Find next
        for(var i=org_id+1;i<org_id+10;i++) {
            if($('tr#fr_'+i).length!=0 && tr_fn==false && i!=org_id) {
                tr_id = i;
                tr_fn = true;
                break;
            }
        }
    } else {
        // Find prev
        for(var i=org_id-1;i>org_id-10;i++) {
            if($('tr#fr_'+i).length!=0 && tr_fn==false && i!=org_id) {
                tr_id = i;
                tr_fn = true;
                break;
            }
        }
    }
    

    if(tr_fn) {
        // Get the info: color & position
        var $tr = $('tr#fr_'+ tr_id);
        var x = parseFloat($tr.attr('data-org-x'));
        var y =  parseFloat($tr.attr('data-org-y'));
        var color = $tr.find('.st').css('background-color');

        return {
            x:x,
            y:y,
            color:color,
            id:tr_id
        }
        
    } else {
        return null;
    }
}


 




 