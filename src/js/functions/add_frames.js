function add_reduc_row(data) {

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

 
