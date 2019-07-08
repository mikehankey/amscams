function add_reduc_row(data,before) {
  
    if(typeof data.newframe !=="undefined") {
        var new_frame_id = parseInt(data.newframe.fn);
        var next_id = parseInt(new_frame_id)-1;

        var new_frame = data.newframe;

        // Try to find the row after first 
        var $tr_before = $('tr#fr_'+ next_id);

        // If it doesn't exist
        if($tr_before.length==0) {
            // Add on first position
            $tr_before = $('#reduc-tab table tbody tr')[0];
        }

        var _time = new_frame.frame_time;
        _time = _time.split(' ');
        _time = _time[1];

        // Build new row
        var row = "<tr id='fr_' "+ new_frame_id +" data-org-x='"+new_frame.hd_x+"' data-org-y='"+new_frame.hd_y+"'>";
        row += '<td><img alt="Thumb #'+new_frame_id+'" src="'+new_frame.cnt_thumb +'" width="50" height="50" class="img-fluid select_meteor">';
        row += '<td>' + new_frame_id + '</td>';
        row += '<td>' + _time + '</td>'; 
        row += '<td>' + new_frame.ra.toFixed(3) + "&deg;/" + new_frame.dec.toFixed(3) + '&deg</td>';              
        row += '<td>' + new_frame.az.toFixed(3) + "&deg;/" + new_frame.el.toFixed(3) + '&deg</td>';               
        row += '<td>' + new_frame.hd_x + "/" + new_frame.hd_y + '</td>';              
        row += '<td>' + new_frame.w + "/" + new_frame.h + '</td>';            
        row += '<td>' + new_frame.max_px + '</td>';       
        row += '<td><a class="btn btn-danger btn-sm delete_frame"><i class="icon-delete"></i></a></td>';
        row += '<td class="position-relative"><a class="btn btn-success btn-sm select_meteor"><i class="icon-target"></i></a></td>';
 
        if(before) {
            $(row).insertBefore($tr_before);
        } else {
            $(row).insertAfter($tr_before);
        }

        // Reload all actions on reduct table!!!
        bootbox.alert({
            message: "FRAME CREATED ",
            className: 'rubberBand animated',
            centerVertical: true 
        });
        
        // Reload the actions
        reduction_table_actions();

    } else {
        bootbox.alert({
            message: "This frame already exists. Please, refresh the page if you don't see it.",
            className: 'rubberBand animated error',
            centerVertical: true 
        });
    }

    loading_done();
}

function add_a_frame(cur_fn, before) {
    var cmd_data = {
		cmd: 'add_frame',
        sd_video_file: sd_video_file, // Defined on the page
        fn: cur_fn
    };
 
    loading({text: "Generating Frame #"+ cur_fn, overlay:true});
 
    $.ajax({ 
        url:  "/pycgi/webUI.py",
        data: cmd_data, 
        success: function(data) { 
            loading_done();
            if($.trim(data)!=='') {
                add_reduc_row($.parseJSON(data),before);
            } else {
                bootbox.alert({
                    message: "Something went wrong: please contact us.",
                    className: 'rubberBand animated error',
                    centerVertical: true 
                });
                
            }
          
        }, 
        error:function() { 
            console.log('ERROR');
            bootbox.alert({
                message: "The process returned an error",
                className: 'rubberBand animated error',
                centerVertical: true 
            });
        }
    });
}

function setup_add_frames() {
    $('.add_f').click(function() {
        add_a_frame($(this).attr('data-rel'),$(this).hasClass('.btn-mm')?true:false);
    }); 
}

 
