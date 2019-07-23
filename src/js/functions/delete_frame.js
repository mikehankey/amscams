function setup_delete_frame() {
    // Delete Frame
    $('.delete_frame').click(function() {
        var  $row = $(this).closest('tr');
        var  id = $row.attr('id');

        // Get the frame ID
        // the id should be fr_{ID}
        var d = id.split('_');
  
        $.ajax({ 
            url:  "/pycgi/webUI.py?cmd=del_frame&meteor_json_file=" + meteor_json_file + "&fn=" + d[1],
            success: function(response) {
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
        url:  "/pycgi/webUI.py?cmd=del_frame&meteor_json_file=" + meteor_json_file + "&fn=" + fn,
        success: function(response) { 
                update_reduction_only();
                $('.modal-backdrop').remove();
                $('#select_meteor_modal').modal('hide').remove();
                fn = fn + 1;
                if($('tr#fr_'+fn).length()!=0) {
                    $('tr#fr_'+fn+' .select_meteor').click();
                } else {
                    fn = fn -2;
                    $('tr#fr_'+fn+' .select_meteor').click();
                }

                
             
        } 
    });



}
 