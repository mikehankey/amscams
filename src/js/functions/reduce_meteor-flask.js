function reduce_meteor() {
    meteor_file = meteor_json_file.substring(meteor_json_file.lastIndexOf('/')+1);
    var cmd_data = {
        meteor_json_file:   meteor_file          // Defined on the page 
    };
 
 
    loading({text:'Reducing meteor...', overlay:true}); 
    
    // Remove All objects from Canvas
    remove_objects();

    $.ajax({ 
        url:  "/api/reduce_meteor/" + meteor_file + "/",
        data: cmd_data,
        success: function(data) {
            //alert(data['msg'])
            var json_resp = data
           
            if(json_resp['status']!==0) {
                window.location.reload();
                //update_reduction_on_canvas_and_table(json_resp);

                // Open proper tab
                $('#reduc-tab-l').click();
                
               
            }  else {

               if(typeof json_resp['error'] !='undefined') {
                  bootbox.alert({
                     message: json_resp['error'],
                     className: 'rubberBand animated error',
                     centerVertical: true
                 });
               } else {
                  bootbox.alert({
                     message: "The reduction failed.",
                     className: 'rubberBand animated error',
                     centerVertical: true
                 });
               }
               
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
