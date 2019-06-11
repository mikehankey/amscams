function reduce_meteor() {
    var cmd_data = {
        meteor_json_file:   meteor_json_file,          // Defined on the page 
        cal_params_file:   $('#cal_param_selected').val(), 
        cmd: 'reduce_meteor_ajax'
    };
 
 
    loading({text:'Reducing meteor...', overlay:true}); 
    
    // Remove All objects from Canvas
    remove_objects();

    $.ajax({ 
        url:  "/pycgi/webUI.py",
        data: cmd_data,
        success: function(data) {
            var json_resp = $.parseJSON(data);
            if(json_resp['status']!==0) {
                update_reduction_on_canvas_and_table(json_resp);

                // Open proper tab
                $('#reduc-tab-l').click();
                
               
            }  else {
                bootbox.alert({
                    message: "The reduction failed.",
                    className: 'rubberBand animated error',
                    centerVertical: true
                });
            }
            loading_done();
        }, 
        error:function() {
            bootbox.alert({
                message: "The reduction returned an error.",
                className: 'rubberBand animated error',
                centerVertical: true
            });
            loading_done();
        }
    });
}


 

$(function () {

    // Click on button
    $('#reduce_meteor').click(function() {
        reduce_meteor();
    });

});
