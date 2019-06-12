function add_a_frame(cur_fn) {
    loading({text: "Generating Frame #"+ cur_fn});


    var cmd_data = {
		cmd: 'add_frame',
        sd_video_file: sd_video_file, // Defined on the page
        fn: cur_fn
    };

    $.ajax({ 
        url:  "/pycgi/WebUI.py",
        data: cmd_data, 
        success: function(data) { 
            loading_done();
            
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

$(function() {
    $('.add_f').click(function() {
        add_a_frame($(this).attr('data-rel'));
    }); 
})