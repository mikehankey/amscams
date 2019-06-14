function add_reduc_row(data) {
    //{"msg": "new frame added.", 
    //"newframe": {"fn": "63", "hd_x": 887, "hd_y": 762, "w": 5, "h": 5,
    // "ra": 63.13939392539605, "dec": 67.7292367055501, "az": 11.588535096776218, 
    //"el": 13.753721430435006, "max_px": 0, "est_x": 890, "est_y": 762, 
    //"len_from_last": 1.4142135623730951, "b_10": NaN, "x1": 837, "y1": 712, "x2": 937, "y2": 812}}

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

 
