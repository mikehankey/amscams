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
            /*update_reduction_only();
            if($.trim(data)!=='') {
                add_reduc_row($.parseJSON(data),before);
            } else {
                bootbox.alert({
                    message: "Something went wrong: please contact us.",
                    className: 'rubberBand animated error',
                    centerVertical: true 
                });
                
            }
            */
          
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