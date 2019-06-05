 $(function() {

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
      
    })

})

 