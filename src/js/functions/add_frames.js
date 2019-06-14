function add_reduc_row(data) {
    /*
          {"msg": "new frame added.", 
           "newframe": 
            {"fn": "121",
             "hd_x": 969,
             "hd_y": 878,
             "w": 5,
             "h": 5,
             "ra": 61.78094346203922,
             "dec": 61.674271792893386,
             "az": 14.87728474941026,
             "el": 8.596841983793604,
             "max_px": 0,
             "est_x": 973,
             "est_y": 879,
             "len_from_last": 7.280109889280518,
             "b_10": NaN,
             "frame_time": "2019-06-11 08:23:35.320",
             "x1": 919, "y1": 828, "x2": 1019, "y2": 928}}
    */
    if(data.msg=='new frame added') {
        var new_frame_id = parseInt(data.newframe.fn);

        // Try to find the row after first 
        var $tr_after = $('tr#'+ (new_frame_id-1));

        // If it doesn't exist
        if($tr_before.length==0) {
            // Add on first position
            $tr_before = $('#reduc-tab table tbody tr')[0];
        }

        

   

    }

    var row = "<tr>";

    // Test if path_image exist -> replace with processing thumb in case it doesn't 

    row += '<img alt="Thumb #'+id+'" src="'+path_image+'" width="50" height="50" class="img-fluid select_meteor"></td>';

    // Create row
    var $row = $('<tr><td></td><td></td><td></td></tr>');


    // Reload all actions on reduct table!!!
    
}

function add_a_frame(cur_fn) {
    loading({text: "Generating Frame #"+ cur_fn});
 
    var cmd_data = {
		cmd: 'add_frame',
        sd_video_file: sd_video_file, // Defined on the page
        fn: cur_fn
    };

    $.ajax({ 
        url:  "/pycgi/webUI.py",
        data: cmd_data, 
        success: function(data) { 
            loading_done();
            add_reduc_row(data);
            
            bootbox.alert({
                message: "FRAME CREATED " + data,
                className: 'rubberBand animated',
                centerVertical: true 
            });
            
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

function setup_add_frames() {
    $('.add_f').click(function() {
        add_a_frame($(this).attr('data-rel'));
    }); 
}

 
