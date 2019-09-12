function setup_delete_frame() {
    // Delete Frame
    $('.delete_frame').click(function() {
        var  $row = $(this).closest('tr'); 
        var  frame_id = $row.attr('data-fn');
 
        loading({"text":"Deleting frame #"+frame_id,"overlay":true});
  
        $.ajax({ 
            url:  "/pycgi/webUI.py?cmd=delete_frame&json_file=" + json_file + "&fn=" + frame_id,
            success: function(response) {

                // Remove the related square on the canvas
                var objects = canvas.getObjects('reduc_rect');
                for(i=0; i<objects.length; i++) { 
                    if(objects[i].id !== undefined && objects[i].id == "fr_"+frame_id) { 
                        canvas.remove(objects[i]);
                    }
                }

                loading_done();
                $row.fadeOut(150, function() {$row.remove();})
            } 
        });
    
    });

}


function delete_frame_from_crop_modal(fn) {

    var  $row = $('tr#fr_'+fn); 
    loading({"text":"Deleting frame #"+fn,"overlay":true});
    $row.css('opacity',0.5).find('a').hide();

    $.ajax({ 
        url:  "/pycgi/webUI.py?cmd=delete_frame&meteor_json_file=" + json_file + "&fn=" + fn,
        success: function(response) { 
                var tr_fn = false;
                var tr_id = fn; 
                update_reduction_only(function() {
                    $('.modal-backdrop').remove();
                    $('#select_meteor_modal').modal('hide').remove();
                    tr_fn = false;
    
                    // Try to find first next frame
                    for(var i=fn+1;i<fn+20;i++) {
                        if($('tr#fr_'+i).length!=0 && !tr_fn) {
                            tr_id = i;
                            tr_fn = true;
                            break;
                        }
                    }
    
                    if(!tr_fn) {
                        for(var i=fn-1;i>fn-20;i--) {
                            if($('tr#fr_'+i).length!=0 &&  !tr_fn) {
                                tr_id = i;
                                tr_fn = true;
                                break;
                            }
                        }
                    }

                    if(tr_fn) {
                        $('tr#fr_'+tr_id+' .select_meteor').click(); 
                    }

 
    
                });
               
                
             
        } 
    });



}
 