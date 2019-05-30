function update_star_and_reduction() {
    var cmd_data = {
        video_file:       main_vid,          // Defined on the page 
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

            // Remove All objects from Canvas
            remove_objects();
 
            // Update Stars
            update_stars_on_canvas_and_table(json_resp);

            // Update Reduction
            update_reduction_on_canvas_and_table(json_resp);

            // Open proper tab
            $('#stars-tab-l').click();
            
            loading_done();
 
        } 
    });

}