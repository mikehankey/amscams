function update_star_and_reduction(callback) {
    var cmd_data = {
        video_file: main_vid,          // Defined on the page 
        cmd: 'update_red_info_ajax'
    }

    loading({text:'Updating star list and reduction data...', overlay:true}); 
    
    // Remove All objects from Canvas
    remove_objects();

    
    $.ajax({ 
        url:  "/pycgi/webUI.py",
        data: cmd_data,
        success: function(data) {
        
            var json_resp = $.parseJSON(data); 

            //console.log('IN update_star_and_reduction')
            //console.log(json_resp)
            //console.log(cmd_data)

            if(json_resp['status']!==0) {
                // Remove All objects from Canvas
                remove_objects();
                
                // Update Stars
                update_stars_on_canvas_and_table(json_resp);

                // Update Reduction
                update_reduction_on_canvas_and_table(json_resp);
                
                // Update Add frames
                setup_add_frames();

                // Reload the actions
                reduction_table_actions();

                // Callback (optional)
                typeof callback === 'function' && callback();
            }

            loading_done();
           
 
        }, error: function(data) {
            
            loading_done();
            bootbox.alert({
                message: "Something went wrong with this detection.",
                className: 'rubberBand animated error',
                centerVertical: true 
            });
        }
    });

}

$(function() {
    // Manual
    $('#refresh_data').click(function(){
        update_star_and_reduction();
    });
})
